from rest_framework.parsers import MultiPartParser, FormParser
from adrf.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from django.http import StreamingHttpResponse
import json
from ..schemas import GymResponseSchema
from ..services import StreamGenerator, get_gemini_client
from ..models import GymQuestions, GymSesh
from .auth import get_user_session_info, filter_by_owner

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY


class GymSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs):
        """Handles POST requests from the gym page"""
        
        # Get shared client instance
        client = get_gemini_client()

        owner_info = get_user_session_info(request)

        system_prompt = """
        You are an expert math problem solver. Provide step-by-step solutions in LaTeX format and compare it to the attempt.
        """
        
        # Step 1: Validation & Retrieval
        data = request.POST.dict()
        gym_sesh_id = data.get('gym_sesh_id', '')
        gym_question_id = data.get('gym_question_id', '')
        question_number = int(data.get('question_number', 1))

        if not gym_sesh_id:
            return Response({'error': 'Gym session not found'}, status=404)
        if not gym_question_id:
            return Response({'error': 'Gym question not found'}, status=404)
        
        try:
            # Create queryset to filter the database by ownership
            query_set = GymSesh.objects.filter(id=gym_sesh_id)
            query_set = filter_by_owner(query_set, owner_info)
            gym_sesh = await query_set.aget()
            
            # Update the gym session status if not already active
            if gym_sesh.status == GymSesh.Status.PENDING:
                gym_sesh.started_at = timezone.now()
                gym_sesh.status = GymSesh.Status.ACTIVE
                await gym_sesh.asave()
            
            # Get the question
            gym_question = await GymQuestions.objects.aget(gym_sesh=gym_sesh, question_number=question_number)

            # Check if the question has been answered  
            if gym_question.is_answered:
                return Response({'error': 'Question has been answered'}, status=400)

            # Update the records
            gym_question.status = GymQuestions.Status.EVALUATING
            gym_question.attempt = data['attempt']
            gym_question.answered_at = timezone.now()
            gym_question.is_answered = True
            await gym_question.asave()

        except GymQuestions.DoesNotExist:
            return Response({'error': 'Question does not exist'}, status=404)
        except GymSesh.DoesNotExist:
            return Response({'error': 'Gym Session does not exist'}, status=404)
        
        prompt_parts = []

        prompt_parts.append({'text': 'Solve the following math problem: '})

        if data.get('problem'):
            prompt_parts.append({'text': data['problem']})
        else:
            return Response({'error': 'No problem context'}, status=400)
        
        prompt_parts.append({'text': 'Here is the student attempt: '})

        if data.get('attempt'):
            prompt_parts.append({'text': data['attempt']})
        else:
            return Response({'error': 'Input attempt context'}, status=400)

        # Async generator for streaming and saving to the database
        async def stream_with_db_save():
            """Stream the response to the user then save the accumulated result to the database"""
            accumulated_result = {
                'is_correct': None,
                'feedback': '',
                'solution': '',
                'next_question': ''
            }

            stream_generator = StreamGenerator(
                client=client,
                system_prompt=system_prompt,
                prompt_parts=prompt_parts,
                response_schema=GymResponseSchema
            )

            # Stream and accumulate the result
            async for chunk in stream_generator.generate():
                yield chunk

                try:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        json_str = chunk_str[6:].strip()
                        event_data = json.loads(json_str)

                        # Accumulate based on event type
                        if event_data['type'] == 'partial':
                            field = event_data['field']
                            content = event_data['content']
                            accumulated_result[field] += content
                        elif event_data['type'] == 'boolean':
                            field = event_data['field']
                            accumulated_result[field] = event_data['content']
                        elif event_data['type'] == 'complete':
                            if isinstance(event_data['content'], dict):
                                accumulated_result.update(event_data['content'])
                except:
                    pass

            # Save to the database AFTER streaming is complete
            try:
                gym_sesh.num_questions += 1
                if accumulated_result['is_correct']:
                    gym_sesh.score += 1
                await gym_sesh.asave()

                gym_question.status = GymQuestions.Status.EVALUATED
                gym_question.is_correct = accumulated_result.get('is_correct', False)
                gym_question.feedback = accumulated_result.get('feedback', '')
                gym_question.solution = accumulated_result.get('solution', '')
                await gym_question.asave()

                next_question = await GymQuestions.objects.acreate(
                    gym_sesh=gym_sesh,
                    question=accumulated_result.get('next_question', ''),
                    question_number=question_number + 1
                )

                request.session['next_question_id'] = next_question.id

                # Send the final event with the necessary ids
                final_event = {
                    'type': 'gym_evaluation_saved',
                    'gym_sesh_id': str(gym_sesh_id),
                    'next_question_id': next_question.id,
                    'question_number': question_number + 1,
                    'is_complete': True
                }
                yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')
            except Exception as e:
                final_event = {
                    'type': 'save_error',
                    'content': f'Failed to save gym evaluation, {str(e)} occurred',
                    'is_complete': True
                }
                yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')

        response = StreamingHttpResponse(
            stream_with_db_save(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'

        return response
    
    async def get(self, request):
        """GET request - Retrieve the current question for a gym session"""
        gym_sesh_id = request.query_params.get('gym_sesh_id')
        analysis_id = request.query_params.get('analysis_id')
        question_num = int(request.query_params.get('question_num', 1))

        if not gym_sesh_id and not analysis_id:
            return Response({'error': 'Provide gym_sesh_id or analysis_id'}, status=400)
        
        # Get user/session info for ownership verification
        owner_info = get_user_session_info(request)
        
        # Build the queryset - support lookup by gym_sesh_id or by analysis_id
        if gym_sesh_id:
            queryset = GymQuestions.objects.filter(
                gym_sesh__id=gym_sesh_id,
                question_number=question_num
            )
        else:
            # Look up through the analysis relationship
            queryset = GymQuestions.objects.filter(
                gym_sesh__analysis__id=analysis_id,
                question_number=question_num
            )
        
        # Apply ownership filter through the relationship
        if owner_info['user']:
            queryset = queryset.filter(gym_sesh__user=owner_info['user'])
        elif owner_info['session_key']:
            queryset = queryset.filter(gym_sesh__session_key=owner_info['session_key'])

        try:
            gym_question = await queryset.select_related('gym_sesh').aget()
            return Response(gym_question.to_dict(), status=200)
        
        except GymQuestions.DoesNotExist:
            return Response({'error': 'Question not found or access denied'}, status=404)


class GymCompleteView(APIView):
    """Handles completing a gym session"""

    async def post(self, request, *args, **kwargs):
        """Mark a gym session as completed"""
        data = request.data
        gym_sesh_id = data.get('gym_sesh_id')

        if not gym_sesh_id:
            return Response({'error': 'gym_sesh_id is required'}, status=400)

        owner_info = get_user_session_info(request)

        try:
            query_set = GymSesh.objects.filter(id=gym_sesh_id)
            query_set = filter_by_owner(query_set, owner_info)
            gym_sesh = await query_set.aget()

            gym_sesh.status = GymSesh.Status.COMPLETED
            gym_sesh.completed_at = timezone.now()
            await gym_sesh.asave()

            return Response({
                'status': 'completed',
                'score': gym_sesh.score,
                'num_questions': gym_sesh.num_questions,
                'percentage': gym_sesh.to_percentage,
            }, status=200)

        except GymSesh.DoesNotExist:
            return Response({'error': 'Gym session not found or access denied'}, status=404)
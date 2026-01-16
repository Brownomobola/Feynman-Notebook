from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from  google import genai
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.shortcuts import aget_object_or_404, redirect
from django.http import StreamingHttpResponse
import json
from typing import Optional
from ..schemas import GymResponseSchema
from ..services import ImageTranscriber, StreamGenerator
from ..models import GymTranscript, GymQuestions, GymSesh




GEMINI_API_KEY=settings.GEMINI_API_KEY

class GymSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)

    async def transcribe_gym_image(self, request, enhance: bool = True, *args, **kwargs) -> Optional[str] | Response:
        """
        Transcribes handwritten math from an uploaded image.
        
        Args:
            request: The HTTP request containing the image file
            enhance: Whether to enhance contrast and sharpness
            
        Returns:
            Transcribed text in LaTeX/Markdown format, or error Response
        """
        # Get image and text from request
        image_file = request.FILES.get('image')
        text_fallback = request.POST.get('text', '')
        
        # Create transcriber instance
        transcriber = ImageTranscriber(client=self.client)
        
        try:
            result = await transcriber.transcribe(
                image_file=image_file,
                text_fallback=text_fallback,
                enhance=enhance
            )

            gym_transcript = GymTranscript.objects.create(
                image_obj=image_file,
                text_obj=text_fallback,
                transcript = result
            )

            request.session['gym_transcript'] = gym_transcript.id

            return result
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @require_http_methods(['GET', 'POST'])
    async def gym_solution(self, request, *args, **kwargs):
        """"Implementation of the gym solution logic"""
        system_prompt = """
        You are an expert math problem solver. Provide step-by-step solutions in LaTeX format and compare it to the attempt.
        """
        if request.method == 'POST':
            # Step 1: Validation & Retrieval
            data = request.POST.dict()
            gym_sesh_id = data.get('gym_sesh_id', '')
            gym_question_id = data.get('gym_question_id', '')
            question_number = data.get('question_number', 1)

            if not gym_sesh_id:
                return Response({'error': 'Gym session not found'}, status=404)
            if not gym_question_id:
                return Response({'error': 'Gym question not found'}, status=404)
            
            try:
                gym_sesh = await GymSesh.objects.aget(id=gym_sesh_id)
                gym_sesh.started_at = timezone.now()
                gym_sesh.status = GymSesh.Status.ACTIVE

                gym_question = await GymQuestions.objects.aget(id=gym_question_id)
                if gym_question.is_answered == True:
                    return Response({'error': 'Question has been answered'}, status=400)

                gym_question.status = GymQuestions.Status.EVALUATING
                gym_question.attempt = data['attempt']
                gym_question.answered_at = timezone.now()
                gym_question.is_answered = True
                await gym_question.asave()

            except GymQuestions.DoesNotExist:
                return redirect('feynman:analysis')
            except GymSesh.DoesNotExist:
                return redirect('feynman:analysis')
            
            
            prompt_parts = []

            prompt_parts.append({'text': 'Solve the following math problem: '})

            if data.get('problem'):
                prompt_parts.append({'problem text': data['problem']})
            else:
                return Response({'error': 'No problem context'}, status=500)
            
            if data.get('attempt'):
                prompt_parts.append({'attempt text': data['attempt']})
            else:
                return Response({'error': 'Input attempt context'}, status=400)


            async def stream_with_db_save():
                """Stream the reponse to the user then save the accumulated result to the database"""
                accumulated_result = {
                    'is_correct': None,
                    'feedback': '',
                    'solution': '',
                    'next_question': ''
                }

                stream_generator = StreamGenerator(
                    client=self.client,
                    system_prompt=system_prompt,
                    prompt_parts=prompt_parts,
                    response_schema=GymResponseSchema
                )

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
                            elif event_data['type'] == 'array':
                                field = event_data['field']
                                accumulated_result[field] = event_data['content']
                            elif event_data['type'] == 'boolean':
                                field = event_data['field']
                                accumulated_result[field] = event_data['content']
                            elif event_data['type'] == 'complete':
                                if isinstance(event_data['content'], dict):
                                    accumulated_result.update(event_data['content']) # Final update with complete JSON

                    except:
                        pass
                    
                    # Update and save the gym question object
                    try:
                        gym_sesh.num_questions += 1
                        gym_sesh.score += 1 if accumulated_result['is_correct'] == True else 0

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

                        next_question_id = next_question.id
                        request.session['next_question_id'] = next_question.id

                        # Send the final event with the necessary ids
                        final_event = {
                            'type': 'gym_evaluation_saved',
                            'gym_sesh_id': gym_sesh_id,
                            'next_question_id': next_question_id,
                            'question_number': question_number + 1,
                            'is_complete': True
                        }
                        yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')
                    except Exception as e:
                        final_event = {
                            'type': 'save_error',
                            'content': f'Failed to save gym evaluation, {str(e)} occured',
                            'is_complete': True
                        }
                        yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')

            response = StreamingHttpResponse(
                stream_with_db_save(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production

            return response
        
        # GET request - Display the current question
        gym_sesh_id = request.session['gym_sesh_id']
        if not gym_sesh_id:
            return Response({'error': 'Could not find the Gym Session'}, status=404)
        
        gym_question_id = request.session['gym_question_id']
        if not gym_question_id:
            return Response({'error': 'Could not find the Gym Question'}, status=404)

        try:
            gym_sesh = await GymSesh.objects.aget(id=gym_sesh_id)
            gym_question = await GymQuestions.objects.aget(id=gym_question_id)
            if gym_question.is_answered:
                return Response({'error': 'Question has been answered'}, status=400)

            return Response(gym_question.to_dict(), status = 200)
        except GymSesh.DoesNotExist:
            return redirect('feynman:analysis')
        except GymQuestions.DoesNotExist:
            return redirect('feynman:analysis')
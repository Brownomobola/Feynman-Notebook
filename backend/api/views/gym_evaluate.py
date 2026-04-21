from rest_framework.parsers import MultiPartParser, FormParser
from adrf.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.http import StreamingHttpResponse
import json, logging
from ..schemas import GymEvaluateOpenEndedResponseSchema
from ..services import get_gemini_client, StreamGenerator
from ..models import Analysis, GymSesh, Question, Attempt
from .auth import get_user_session_info, filter_by_owner

logger = logging.getLogger(__name__)

class GymEvaluateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs):
        """Handles all POST request for evaluating questions sent from the Gym page"""
        
        client = get_gemini_client()
        owner_info = get_user_session_info(request)
        
        data = request.POST.dict()

        gym_sesh_id = data.get('gym_sesh_id')
        question_id = data.get('question_id')
        user_response = data.get('user_response')

        if not gym_sesh_id:
            return Response({'error': 'gym_sesh_id is required'}, status=400)
        if not question_id:
            return Response({'error': 'question_id is required'}, status=400)
        if not user_response:
            return Response({'error': 'user_response is required'}, status=400)
        
        try:
            # We don't filter by owner on GymSesh here since session matching might use session_key
            # The structure for Gym is similar to Analysis owner logic
            gym_sesh = await GymSesh.objects.aget(id=gym_sesh_id) 
            
            question = await Question.objects.aget(id=question_id, gym_sesh=gym_sesh)
        except GymSesh.DoesNotExist:
            return Response({'error': 'Gym session with the provided ID does not exist for this user'}, status=404)
        except Question.DoesNotExist:
            return Response({'error': 'Question does not exist in this session'}, status=404)

        if question.question_type == Question.QUESTION_TYPE.MCQ:
            logger.info(f"Evaluating MCQ answer for question {question.id}")
            
            is_correct = (user_response.strip().lower() == question.correct_answer.strip().lower())
            
            attempt = await Attempt.objects.acreate(
                question=question,
                status=Attempt.STATUS.EVALUATED,
                user_response=user_response,
                is_correct=is_correct,
                score=100.0 if is_correct else 0.0,
                feedback="Correct!" if is_correct else f"Incorrect. The correct answer was {question.correct_answer}."
            )
            
            if is_correct:
                gym_sesh.score += 1
                await gym_sesh.asave(update_fields=['score'])
                
            return Response({
                'is_correct': is_correct,
                'score': attempt.score,
                'feedback': attempt.feedback
            })

        elif question.question_type == Question.QUESTION_TYPE.OPEN_ENDED:
            logger.info(f"Evaluating Open-Ended answer for question {question.id}")
            
            system_prompt = """You are an unbiased, strict, and precise grader for university-level problems.
            Your goal is to evaluate the student's open-ended answer against the provided rubric.
            Determine if the answer is conceptually correct and award a score out of 100 based on how well they met the rubric's requirements.
            A feedback should be provided detailing what they did well and where they can improve."""
            
            prompt_parts = []
            prompt_parts.append({'text': f"Question: {question.question_text}"})
            prompt_parts.append({'text': f"Rubric / Answer Guide: {question.theory_rubric}"})
            prompt_parts.append({'text': f"Student's Answer: {user_response}"})

            async def stream_with_db_save():
                stream_generator = StreamGenerator(
                    client=client,
                    system_prompt=system_prompt,
                    prompt_parts=prompt_parts,
                    response_schema=GymEvaluateOpenEndedResponseSchema
                )

                accumulated_result = {
                    'is_correct': False,
                    'score': 0.0,
                    'feedback': ''
                }

                async for chunk in stream_generator.generate():
                    yield chunk

                    try:
                        chunk_str = chunk.decode('utf-8')
                        if chunk_str.startswith('data: '):
                            json_str = chunk_str[6:].strip()
                            event_data = json.loads(json_str)

                            if event_data['type'] == 'boolean' and event_data['field'] == 'is_correct':
                                accumulated_result['is_correct'] = event_data['content']
                            elif event_data['type'] == 'partial' and event_data['field'] == 'feedback':
                                accumulated_result['feedback'] += event_data['content']
                            elif event_data['type'] == 'complete':
                                if isinstance(event_data['content'], dict):
                                    accumulated_result.update(event_data['content'])
                    except Exception as e:
                        logger.error(f"Error parsing stream chunk: {e}", exc_info=True)
                
                try:
                    is_correct = accumulated_result.get('is_correct', False)
                    try:
                        score = float(accumulated_result.get('score', 0.0))
                    except (ValueError, TypeError):
                        score = 0.0
                    feedback = accumulated_result.get('feedback', '')
                    
                    attempt = await Attempt.objects.acreate(
                        question=question,
                        status=Attempt.STATUS.EVALUATED,
                        user_response=user_response,
                        is_correct=is_correct,
                        score=score,
                        feedback=feedback
                    )
                    
                    if is_correct or score >= 50.0:
                        # Give partial or full credit based on threshold (e.g. if is_correct is marked True)
                        gym_sesh.score += 1
                        await gym_sesh.asave(update_fields=['score'])
                    
                    final_event = {
                        'type': 'evaluated',
                        'is_correct': is_correct,
                        'score': score,
                        'is_complete': True
                    }
                    yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')
                except Exception as e:
                    logger.error(f"Save error for open-ended evaluation: {e}", exc_info=True)
                    final_event = {
                        'type': 'save_error',
                        'content': f'Failed to save evaluation: {str(e)}',
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
        
        return Response({'error': 'Invalid question type'}, status=400)

from rest_framework.parsers import MultiPartParser, FormParser
from adrf.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.http import StreamingHttpResponse
import json, logging
from ..schemas import GymGenerateMCQListSchema, GymGenerateOpenEndedListSchema
from ..services import StreamGenerator, get_gemini_client
from ..models import Analysis, GymSesh, Question, Answer
from .auth import get_user_session_info, filter_by_owner

logger = logging.getLogger(__name__)

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY

class GymGenerateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs):
        """Handles all POST request for generating questions sent from the Gym page"""
        
        # Get shared client instance
        client = get_gemini_client()
        
        # Get user/session info for ownership
        owner_info = get_user_session_info(request)
        
        data = request.POST.dict()

        analysis_id = data.get('analysis_id')

        # Validate the user
        if owner_info['user'] is None:
            return Response({'error': 'User authentication required'}, status=401)
        if not analysis_id:
            return Response({'error': 'analysis_id is required'}, status=400)
        
        try:
            analysis = await Analysis.objects.aget(id=analysis_id)
            if analysis.user != owner_info['user']:
                return Response({'error': 'Unauthorized access to this analysis'}, status=403)
            elif analysis.session_key != owner_info['session_key']:
                return Response({'error': 'Unauthorized access to this analysis'}, status=403)
        except Analysis.DoesNotExist:
            return Response({'error': 'Analysis with the provided ID does not exist'}, status=404)

        system_prompt = """You are a "Feynman Tutor." 
        Your goal is to generate a new question that is similar in style and topic to the original question, but with a different context and numbers. 
        The new question should be designed to test the same underlying concepts and problem-solving skills as the original question, 
        but in a way that requires the student to apply their knowledge in a new and creative way. 
        The question should be clear, concise, and unambiguous, and should include all necessary information for the student to solve it. 
        The question should also be appropriately challenging for a student who has just completed the original question, 
        pushing them to deepen their understanding of the material and apply it in new ways."""

        prompt_parts = []

        prompt_parts.append({'text': 'Generate this number of questions on the topic discussed in the analysis section. '
                                    'Use the original question and the analysis as context.'
                                    'Focus on creatinng questions that target the things the student got wrong in the analysis.'})

        prompt_parts.append({'text': f'The original question was: {analysis.problem}'})
        prompt_parts.append({'text': f"The student's attempt was: {analysis.attempt}"})
        prompt_parts.append({'text': f"The things the student got right were: {analysis.praise}"})
        prompt_parts.append({'text': f"The things the student got wrong were: {analysis.diagnosis}"})

        if data.get('type'):
            if data.get('type') == "MCQ":
                prompt_parts.append({'text': 'The question type is multiple choice.'})
                prompt_parts.append({'text': f'Generate {data.get("num_questions", 10)} questions.'})

            if data.get('type') == "Open-Ended":
                prompt_parts.append({'text': 'The question type is open-ended.'})
                prompt_parts.append({'text': f'Generate {data.get("num_questions", 5)} questions.'})
        else:
            return Response({'error': 'Input question type'}, status=400)

        # MCQ Branch
        if data.get('type') == 'MCQ':
            logger.info("Generating MCQ questions")
            try:
                result = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    config={
                        'system_instruction': system_prompt,
                        'response_mime_type': 'application/json',
                        'response_schema': GymGenerateMCQListSchema
                    },
                    contents={'parts': prompt_parts}
                )
                response_data = json.loads(result.text)
                
                questions_data = response_data.get('questions', [])
                
                gym_sesh = await GymSesh.objects.acreate(
                    analysis=analysis,
                    status=GymSesh.Status.PENDING,
                    num_questions=len(questions_data)
                )
                
                frontend_questions = []
                for q_data in questions_data:
                    question = await Question.objects.acreate(
                        gym_sesh=gym_sesh,
                        question_type=Question.QUESTION_TYPE.MCQ,
                        question_text=q_data['question_text'],
                        mcq_options=q_data['options'],
                        correct_answer=q_data['correct_answer']
                    )
                    frontend_questions.append({
                        'id': question.id,
                        'question_text': question.question_text,
                        'options': question.mcq_options
                    })
                
                return Response({
                    'gym_sesh_id': gym_sesh.id,
                    'questions': frontend_questions
                })
            except Exception as e:
                logger.error(f"Failed to generate MCQ questions: {e}", exc_info=True)
                return Response({'error': f'Failed to generate questions: {str(e)}'}, status=500)
                
        # Open-Ended Branch
        elif data.get('type') == 'Open-Ended':
            logger.info("Generating Open-Ended questions stream")
            
            async def stream_with_db_save():
                stream_generator = StreamGenerator(
                    client=client,
                    system_prompt=system_prompt,
                    prompt_parts=prompt_parts,
                    response_schema=GymGenerateOpenEndedListSchema
                )
                
                accumulated_questions = []
                
                async for chunk in stream_generator.generate():
                    yield chunk
                    
                    try:
                        chunk_str = chunk.decode('utf-8')
                        if chunk_str.startswith('data: '):
                            json_str = chunk_str[6:].strip()
                            event_data = json.loads(json_str)
                            
                            if event_data['type'] == 'array' and event_data['field'] == 'questions':
                                accumulated_questions = event_data['content']
                            elif event_data['type'] == 'complete':
                                if isinstance(event_data['content'], dict) and 'questions' in event_data['content']:
                                    accumulated_questions = event_data['content']['questions']
                    except Exception as e:
                        pass
                
                try:
                    gym_sesh = await GymSesh.objects.acreate(
                        analysis=analysis,
                        status=GymSesh.Status.PENDING,
                        num_questions=len(accumulated_questions)
                    )
                    
                    for q_data in accumulated_questions:
                        await Question.objects.acreate(
                            gym_sesh=gym_sesh,
                            question_type=Question.QUESTION_TYPE.OPEN_ENDED,
                            question_text=q_data.get('question_text', ''),
                            theory_rubric=q_data.get('answer_guide', '')
                        )
                        
                    final_event = {
                        'type': 'questions_saved',
                        'gym_sesh_id': gym_sesh.id,
                        'is_complete': True
                    }
                    yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')
                except Exception as e:
                    logger.error(f"Save error for open-ended questions: {e}", exc_info=True)
                    final_event = {
                        'type': 'save_error',
                        'content': f'Failed to save questions: {str(e)}',
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

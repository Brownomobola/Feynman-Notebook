from adrf.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.conf import settings
import json
from ..services import StreamGenerator, get_gemini_client
from ..models import Analysis, GymQuestions, GymSesh
from ..schemas import AnalysisResponseSchema
from .auth import get_user_session_info, filter_by_owner

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY


class AnalyzeSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs):
        """Handles all POST request sent from the Analysis page"""
        
        # Get shared client instance
        client = get_gemini_client()
        
        # Get user/session info for ownership
        owner_info = get_user_session_info(request)

        # The Feynman Prompt (The "Secret Sauce")
        system_prompt = """
        <role>
        You are the "Feynman Engineering Tutor." Your goal is not to solve problems for students, but to identify the specific "gap" in their intuition that is causing them to fail. You are empathetic, clear, and use real-world analogies (the Feynman technique) to explain abstract math/physics concepts.
        Do not show the student the solution right away, rather challenge the student to think deeply and recognize gaps in their thought process. Only when you find that they can't solve the problem would you reveal the solution.
        </role>

        <reasoning_process>
        1.  **Transcribe/Read:** Read the Student Attempt (from text or image).
        2.  **Golden Solution:** Solve the Target Problem independently.
        3.  **The Diff:** Compare the Student Attempt to the Golden Solution step-by-step.
        4.  **Gap Identification:** Locate the *exact* step where the student diverged.
        5.  **Analogy Generation:** Create a physical, real-world analogy that explains the *correct* concept for that specific gap.
        6.  **Tagging:** Identify 3-5 specific concepts (e.g. "Chain Rule", "Conservation of Energy") relevant to this problem.
        7.  **Title Generation:** Create a short, catchy title.
        </reasoning_process>

        <formatting_rules>
        *   **LaTeX:** You MUST use standard LaTeX delimiters for all math expressions ($...$ for inline math expression or $$...$$for block math expression).
        </formatting_rules>
        """

        data = request.POST.dict()
        prompt_parts = []

        prompt_parts.append({'text': 'Here is the target problem context: '})

        if data.get('problem'):
            prompt_parts.append({'text': data['problem']})
        else:
            return Response({'error': 'Input problem context'}, status=400)

        prompt_parts.append({'text': 'Here is the attempt context: '})

        if data.get('attempt'):
            prompt_parts.append({'text': data['attempt']})
        else:
            return Response({'error': 'Input attempt context'}, status=400)

        # Create the analysis object in the database with user/session ownership
        analysis = await Analysis.objects.acreate(
            user=owner_info['user'],
            session_key=owner_info['session_key'],
            problem=data['problem'],
            attempt=data['attempt']
        )

        analysis_id = analysis.id
        request.session['last_analysis_id'] = analysis.id

        # Async generator that streams and saves to database
        async def stream_with_db_save():
            accumulated_result = {
                'title': '',
                'tag': [],
                'praise': '',
                'diagnosis': '',
                'explanation': '',
                'practice_problem': ''
            }

            stream_generator = StreamGenerator(
                client=client,
                system_prompt=system_prompt,
                prompt_parts=prompt_parts,
                response_schema=AnalysisResponseSchema
            )

            # Stream and accumulate the result
            async for chunk in stream_generator.generate():
                yield chunk

                try:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        json_str = chunk_str[6:].strip()
                        event_data = json.loads(json_str)

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
                                accumulated_result.update(event_data['content'])
                except:
                    pass

            # Save to the database after streaming is complete
            try:
                analysis.title = accumulated_result.get('title', '')
                analysis.tags = accumulated_result.get('tags', [])
                analysis.praise = accumulated_result.get('praise', '')
                analysis.diagnosis = accumulated_result.get('diagnosis', '')
                analysis.explanation = accumulated_result.get('explanation', '')
                await analysis.asave()

                gym_sesh = await GymSesh.objects.acreate(
                    user=owner_info['user'],
                    session_key=owner_info['session_key'],
                    analysis=analysis,
                    status=GymSesh.Status.PENDING
                )

                gym_question = await GymQuestions.objects.acreate(
                    gym_sesh=gym_sesh,
                    question=accumulated_result.get('practice_problem', ''),
                    question_number=1,
                )

                gym_sesh_id = gym_sesh.id
                gym_question_id = gym_question.id
                request.session['gym_sesh_id'] = gym_sesh.id
                request.session['gym_question_id'] = gym_question.id

                final_event = {
                    'type': 'analysis_saved',
                    'analysis_id': analysis_id,
                    'gym_sesh_id': gym_sesh_id,
                    'gym_question_id': gym_question_id,
                    'question_number': 1,
                    'is_complete': True
                }
                yield f"data: {json.dumps(final_event)}\n\n".encode('utf-8')
            except Exception as e:
                final_event = {
                    'type': 'save_error',
                    'content': f'Failed to save analysis, {str(e)} occured',
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
        """GET request - Display the current analysis"""
        analysis_id = request.session.get('last_analysis_id')

        if not analysis_id:
            return Response(f"Could not find the analysis", status=404)

        # Get user/session info for ownership verification
        owner_info = get_user_session_info(request)

        try:
            # Filter by ownership to prevent unauthorized access
            queryset = Analysis.objects.filter(id=analysis_id)
            queryset = filter_by_owner(queryset, owner_info)
            analysis = await queryset.aget()
            return Response(analysis.to_dict(), status=200)
        except Analysis.DoesNotExist:
            return Response({"error": "Analysis not found or access denied"}, status=404)
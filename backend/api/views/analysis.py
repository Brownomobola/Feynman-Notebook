from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from google import genai
from django.views.decorators.http import require_http_methods
from django.http import StreamingHttpResponse
from django.conf import settings
from django.shortcuts import aget_object_or_404, redirect
from typing import Optional
import json
from ..services import ImageTranscriber, StreamGenerator
from ..models import AnalysisTranscript, Analysis, GymQuestions, GymSesh
from ..schemas import AnalysisResponseSchema 

GEMINI_API_KEY = settings.GEMINI_API_KEY

class AnalyzeSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    @require_http_methods(["POST"])
    async def transcribe_image(self, request, enhance: bool = True, *args, **kwargs) -> Optional[str] | Response:
        """
        Transcribes handwritten math from an uploaded image.
        
        Args:
            request: The HTTP request containing the image file
            enhance: Whether to enhance contrast and sharpness
            
        Returns:
            Transcribed text in LaTeX/Markdown format, or error Response
        """
        if request.method == 'POST':
            # Get image and text from request
            image_file = request.FILES.get('image')
            text_fallback = request.POST.get('text', '')
            is_question = 'is_question' in request.POST
            
            # Create transcriber instance
            transcriber = ImageTranscriber(client=self.client)
            
            try:
                result = await transcriber.transcribe(
                    image_file=image_file,
                    text_fallback=text_fallback,
                    enhance=enhance
                )

                analysis_transcript = AnalysisTranscript.objects.create(
                    image_obj = image_file,
                    text_obj = text_fallback,
                    is_question = is_question,
                    transcript = result
                )

                request.session['analysis_transcript'] = analysis_transcript.id

                return result
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
            
    @require_http_methods(['POST', 'GET'])
    async def analyze(self, request, *args, **kwargs):
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

        if request.method == 'POST':
            data = request.POST.dict()
            # The prompt containing the user's question and attempt
            prompt_parts = []

            # Add problem context
            prompt_parts.append({'text': 'Here is the target problem context: '})

            if data.get('problem'):
                prompt_parts.append({'text': data['problem']})
            else:
                return Response({'error': 'Input problem context'}, status=400)
            
            # Add attempt context
            prompt_parts.append({'text': 'Here is the attempt context: '})

            if data.get('attempt'):
                prompt_parts.append({'text': data['attempt']})
            else:
                return Response({'error': 'Input attempt context'}, status=400)

            # Create the analysis object in the database
            analysis = await Analysis.objects.acreate(
                problem=data['problem'],
                attempt=data['attempt']
            )

            analysis_id = analysis.id
            request.session['last_analysis_id'] = analysis.id

            # Create wrapper generator that saves to database
            async def stream_with_db_save():
                accumulated_result = {
                    'title': '',
                    'tag': [],
                    'praise': '',
                    'diagnosis': '',
                    'explanation': '',
                    'practice_problem': ''
                }

                # Create the stream generator instance
                stream_generator = StreamGenerator(
                    client=self.client,
                    system_prompt=system_prompt,
                    prompt_parts=prompt_parts,
                    response_schema=AnalysisResponseSchema
                )
                
                # Stream and accumulate the result
                async for chunk in stream_generator.generate():
                    yield chunk
                
                    # Parse the chunks and accumulate them
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

                # Save to the database after streaming is complete
                try:
                    analysis.title = accumulated_result.get('title', '')
                    analysis.tags = accumulated_result.get('tags', [])
                    analysis.praise = accumulated_result.get('praise', '')
                    analysis.diagnosis = accumulated_result.get('diagnosis', '')
                    analysis.explanation = accumulated_result.get('explanation', '')
                    await analysis.asave()

                    gym_sesh = await GymSesh.objects.acreate(
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
                    # Send final event with analysis ID
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

            # Return StreamingHttpResponse with SSE headers
            response = StreamingHttpResponse(
                stream_with_db_save(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production
            return response
        
        # GET request - Display the current analysis
        analysis_id = request.session.get('last_analysis_id')

        if not analysis_id:
            return Response(f"Could not find the analysis", status=404)
        
        analysis = await aget_object_or_404(Analysis, id=analysis_id)   

        return Response(analysis.to_dict(), status=200)
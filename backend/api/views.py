from django.shortcuts import render, aget_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from google import genai
from io import BytesIO
import base64
from PIL import Image, ImageEnhance
from backend.backend.settings import GEMINI_API_KEY
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import re
from django.utils import timezone
from .models import AnalysisTranscript, GymTranscript, Analysis, GymSesh, GymQuestions

class ImageTranscriber:
    """
    Handles transcription of handwritten math from images to LaTeX/Markdown format.
    Includes image preprocessing capabilities for better OCR results.
    """
    
    def __init__(self, client: genai.Client):
        """
        Initialize the image transcriber.
        
        Args:
            client: The Gemini AI client instance
        """
        self.client = client
    
    async def transcribe(self, image_file, text_fallback: Optional[str] = None, enhance: bool = True) -> str:
        """
        Transcribes handwritten math with optional image preprocessing.
        
        Args:
            image_file: The image file to transcribe
            text_fallback: Optional fallback text if transcription fails
            enhance: Whether to enhance contrast and sharpness
            
        Returns:
            Transcribed text in LaTeX/Markdown format
            
        Raises:
            ValueError: If image_file is None and no text_fallback is provided
            Exception: If transcription fails
        """
        if not image_file:
            if text_fallback:
                return text_fallback
            raise ValueError('You must input at least an image or text')
        
        try:
            # Open the image using the PIL library
            image = Image.open(image_file)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Enhance image for better OCR
            if enhance:
                # Increase contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)

                # Increase sharpness
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.0)

            # Convert image to Bytes
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=95)
            image_bytes = buffer.getvalue()

            # Encode to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Add the images for OCR
            prompt_parts = [
                {
                    'text': 'Transcribe the handwritten maths in this image to LaTex/Markdown.' 
                    'Return ONLY the text, no explanations.'
                },
                {
                    'inline_data': {
                        'mime_type': 'image/jpeg',
                        'data': image_base64
                    }
                }
            ]

            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents={'parts': prompt_parts}
            )
            
            # Return transcribed text or fallback to text_fallback
            return response.text if response.text else (text_fallback or "")
        
        except Exception as e:
            raise Exception(f'Error {str(e)} occurred during transcription')

class AnalysisStreamGenerator:
    """
    Handles streaming of AI analysis responses in Server-Sent Events (SSE) format.
    Progressively parses and streams JSON fields as they're generated.
    """
    
    def __init__(self, client: genai.Client, system_prompt: str, prompt_parts: list, response_schema: type[BaseModel]):
        """
        Initialize the stream generator.
        
        Args:
            client: The Gemini AI client instance
            system_prompt: The system instruction for the AI
            prompt_parts: The prompt content to send to the AI
            response_schema: The Pydantic schema defining the expected response structure
        """
        self.client = client
        self.system_prompt = system_prompt
        self.prompt_parts = prompt_parts
        self.response_schema = response_schema
    
    async def generate(self):
        """
        Async generator that streams the AI response in SSE format.
        Yields chunks of data as they become available.
        Handles string, array, and boolean field types.
        """
        accumulated_text = ""
        field_positions = {}
        
        # Get schema properties
        schema_properties = self.response_schema.model_json_schema().get('properties', {})
        
        # Initialize field positions for string fields
        for field_name, field_info in schema_properties.items():
            field_type = field_info.get('type', '')
            if field_type == 'string':
                field_positions[field_name] = 0
        
        # Track array field separately
        array_field_name = None
        for field_name, field_info in schema_properties.items():
            if field_info.get('type') == 'array':
                array_field_name = field_name
                break
        
        # Track boolean fields
        boolean_fields = []
        boolean_fields_sent = {}
        for field_name, field_info in schema_properties.items():
            if field_info.get('type') == 'boolean':
                boolean_fields.append(field_name)
                boolean_fields_sent[field_name] = False
        
        try:
            response = await self.client.aio.models.generate_content_stream(
                model="gemini-2.0-flash-exp",
                config={
                    'system_instruction': self.system_prompt,
                    'response_mime_type': 'application/json',
                    'response_schema': self.response_schema
                },
                contents={'parts': self.prompt_parts}
            )
            
            last_array_content = ""
            
            async for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    # Extract and stream string fields progressively
                    for field_name in field_positions.keys():
                        pattern = rf'"{field_name}"\s*:\s*"([^"]*(?:\\"[^"]*)*)'
                        match = re.search(pattern, accumulated_text)
                        
                        if match:
                            current_value = match.group(1)
                            # Unescape JSON strings
                            current_value = current_value.replace('\\"', '"')
                            current_value = current_value.replace('\\n', '\n')
                            current_value = current_value.replace('\\t', '\t')
                            
                            # Get only new content for this field
                            last_pos = field_positions[field_name]
                            new_content = current_value[last_pos:]
                            
                            if new_content:
                                # Send SSE formatted data
                                event_data = {
                                    'type': 'partial',
                                    'field': field_name,
                                    'content': new_content,
                                    'is_complete': False
                                }
                                yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
                                field_positions[field_name] = len(current_value)
                    
                    # Handle boolean fields
                    for field_name in boolean_fields:
                        if not boolean_fields_sent[field_name]:
                            # Pattern to match boolean values (true or false)
                            bool_pattern = rf'"{field_name}"\s*:\s*(true|false)'
                            bool_match = re.search(bool_pattern, accumulated_text)
                            
                            if bool_match:
                                bool_value = bool_match.group(1) == 'true'
                                event_data = {
                                    'type': 'boolean',
                                    'field': field_name,
                                    'content': bool_value,
                                    'is_complete': False
                                }
                                yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
                                boolean_fields_sent[field_name] = True
                    
                    # Handle array field if it exists
                    if array_field_name:
                        # Extract array content
                        array_pattern = rf'"{array_field_name}"\s*:\s*\[(.*?)(?:\]|$)'
                        array_match = re.search(array_pattern, accumulated_text, re.DOTALL)
                        
                        if array_match:
                            array_content = array_match.group(1)
                            
                            # Check if there's new array content
                            if array_content != last_array_content:
                                # Extract individual array items
                                items = re.findall(r'"([^"]*(?:\\"[^"]*)*)"', array_content)
                                
                                if items:
                                    # Unescape items
                                    unescaped_items = [
                                        item.replace('\\"', '"').replace('\\n', '\n')
                                        for item in items
                                    ]
                                    
                                    event_data = {
                                        'type': 'array',
                                        'field': array_field_name,
                                        'content': unescaped_items,
                                        'is_complete': False
                                    }
                                    yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
                                    last_array_content = array_content
            
            # Try to parse complete JSON at the end
            try:
                complete_json = json.loads(accumulated_text)
                completion_data = {
                    'type': 'complete',
                    'field': 'all',
                    'content': complete_json,
                    'is_complete': True
                }
                yield f"data: {json.dumps(completion_data)}\n\n".encode('utf-8')
            except json.JSONDecodeError:
                # Send accumulated text as fallback
                completion_data = {
                    'type': 'complete',
                    'field': 'all',
                    'content': accumulated_text,
                    'is_complete': True
                }
                yield f"data: {json.dumps(completion_data)}\n\n".encode('utf-8')
            
        except Exception as e:
            error_data = {
                'type': 'error',
                'field': 'error',
                'content': str(e),
                'is_complete': True
            }
            yield f"data: {json.dumps(error_data)}\n\n".encode('utf-8')

class ChatStreamGenerator:
    """
    Handles streaming of conversational AI responses in Server-Sent Events (SSE) format.
    Uses conversation history to provide context-aware responses.
    """
    
    def __init__(self, client: genai.Client, system_prompt: str, conversation_history: List[Dict[str, Any]], user_message: str):
        """
        Initialize the chat stream generator.
        
        Args:
            client: The Gemini AI client instance
            system_prompt: The system instruction for the AI
            conversation_history: List of previous messages in the conversation
            user_message: The current user message
        """
        self.client = client
        self.system_prompt = system_prompt
        self.conversation_history = conversation_history
        self.user_message = user_message
    
    def _build_conversation_contents(self) -> List[Dict[str, Any]]:
        """
        Builds the conversation contents from history and current message.
        
        Returns:
            List of content dictionaries formatted for the Gemini API
        """
        contents = []
        
        # Add conversation history
        for message in self.conversation_history:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'user':
                contents.append({
                    'role': 'user',
                    'parts': [{'text': content}]
                })
            elif role == 'assistant' or role == 'model':
                contents.append({
                    'role': 'model',
                    'parts': [{'text': content}]
                })
        
        # Add current user message
        contents.append({
            'role': 'user',
            'parts': [{'text': self.user_message}]
        })
        
        return contents
    
    async def generate(self):
        """
        Async generator that streams the AI chat response in SSE format.
        Yields text chunks as they become available.
        """
        accumulated_text = ""
        
        try:
            # Build conversation contents
            contents = self._build_conversation_contents()
            
            # Stream the response
            response = await self.client.aio.models.generate_content_stream(
                model="gemini-2.0-flash-exp",
                config={
                    'system_instruction': self.system_prompt
                },
                contents=contents
            )
            
            async for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    # Send the new text chunk
                    event_data = {
                        'type': 'text',
                        'content': chunk.text,
                        'is_complete': False
                    }
                    yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
            
            # Send completion signal
            completion_data = {
                'type': 'complete',
                'content': accumulated_text,
                'is_complete': True
            }
            yield f"data: {json.dumps(completion_data)}\n\n".encode('utf-8')
            
        except Exception as e:
            error_data = {
                'type': 'error',
                'content': str(e),
                'is_complete': True
            }
            yield f"data: {json.dumps(error_data)}\n\n".encode('utf-8')

class AnalysisResponseSchema(BaseModel):
        """Defines the json response schema for the model"""
        title: str = Field(description="A short descriptive title for the analysis")
        tags: list[str] = Field(description="A list of 3-5 relevant tags for the problem solved")
        praise: str = Field(description="A short text commending the student on the things they got right")
        diagnosis: str = Field(description="A short text highlighting what the student got wrong")
        explanation: str = Field(description="An explanation of what the student got wrong using a real-world analogy")
        practice_problem: str = Field(description="A practice problem similar to the original problem")

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
                stream_generator = AnalysisStreamGenerator(
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

class ChatView(APIView):
    """
    Handles conversational chat interactions with the AI tutor.
    Can incorporate analysis history for context-aware responses.
    """
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    async def chat(self, data, *args, **kwargs):
        """
        Streams a conversational response based on the user's message and conversation history.
        
        Args:
            data: Dictionary containing:
                - message: The user's current message (required)
                - history: List of previous conversation messages (optional)
                - analysis_context: Previous analysis result for context (optional)
                - system_prompt: Custom system prompt (optional)
        
        Returns:
            StreamingHttpResponse with SSE formatted chat messages
        """
        # Validate user message
        user_message = data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)
        
        # Get conversation history (default to empty list)
        conversation_history = data.get('history', [])
        
        # Get optional analysis context
        analysis_context = data.get('analysis_context')
        
        # Build system prompt
        base_system_prompt = """
        <role>
        You are the "Feynman Engineering Tutor." Your goal is to help students understand concepts deeply through the Socratic method.
        Use real-world analogies and guide students to discover answers themselves rather than simply providing solutions.
        You are empathetic, encouraging, and focused on building genuine understanding.
        </role>
        
        <conversation_style>
        - Ask probing questions to reveal gaps in understanding
        - Use the Feynman technique: explain complex concepts through simple analogies
        - Be patient and adjust your teaching style based on student responses
        - Celebrate progress and breakthroughs
        - Use LaTeX for math expressions: $...$ for inline, $$...$$ for block equations
        </conversation_style>
        
        <guidelines>
        - Never just give the answer - guide the student to discover it
        - If a student is stuck, break the problem into smaller steps
        - Connect new concepts to things the student already understands
        - Encourage critical thinking with "why" and "what if" questions
        </guidelines>
        """
        
        # Add analysis context if provided
        if analysis_context:
            context_prompt = f"""
        
        <previous_analysis>
        You previously analyzed this student's work with the following context:
        Problem: {analysis_context.get('problem', 'N/A')}
        Student Attempt: {analysis_context.get('attempt', 'N/A')}
        
        Your previous analysis:
        Title: {analysis_context.get('title', 'N/A')}
        Tags: {', '.join(analysis_context.get('tags', []))}
        Diagnosis: {analysis_context.get('diagnosis', 'N/A')}
        Explanation: {analysis_context.get('explanation', 'N/A')}
        
        Use this context to provide more relevant and personalized guidance.
        </previous_analysis>
        """
            system_prompt = base_system_prompt + context_prompt
        else:
            system_prompt = base_system_prompt
        
        # Allow custom system prompt override
        if data.get('system_prompt'):
            system_prompt = data['system_prompt']
        
        # Create chat stream generator
        chat_generator = ChatStreamGenerator(
            client=self.client,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=user_message
        )
        
        # Return streaming response
        response = StreamingHttpResponse(
            chat_generator.generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production
        
        return response

class GymResponseSchema(BaseModel):
    """Defines the json response schema for the gym solution"""
    is_correct: bool = Field(description="Indicates if the attempt is correct")
    feedback: str = Field(description="Feedback on the provided attempt")
    solution: str = Field(description="The step-by-step solution in LaTeX format")
    next_question: str = Field(description="A follow-up question to further challenge the student. Make it harder if is_correct is true, easier if false.")

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
                    return Response({'error': 'Question has been answered'})

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

                stream_generator = AnalysisStreamGenerator(
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
        

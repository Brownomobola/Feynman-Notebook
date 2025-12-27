from django.shortcuts import render
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from google import genai
from google.genai import types
from io import BytesIO
import base64
from PIL import Image, ImageEnhance
from backend.backend.settings import GEMINI_API_KEY
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import re

class AnalysisResponseSchema(BaseModel):
        """Defines the json response schema for the model"""
        title: str = Field(description="A short descriptive title for the analysis")
        tags: list[str] = Field(description="A list of 3-5 relevant tags for the problem solved")
        praise: str = Field(description="A short text commending the student on the things they got right")
        diagnosis: str = Field(description="A short text highlighting what the student got wrong")
        explanation: str = Field(description="An explanation of what the student got wrong using a real-world analogy")
        practice_problem: str = Field(description="A practice problem similar to the original problem")


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


class AnalyzeSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)

    async def transcribe_image(self, request, enhance: bool = True, *args, **kwargs) -> Optional[str] | Response:
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
        text_fallback = request.FILES.get('text')
        
        # Create transcriber instance
        transcriber = ImageTranscriber(client=self.client)
        
        try:
            result = await transcriber.transcribe(
                image_file=image_file,
                text_fallback=text_fallback,
                enhance=enhance
            )
            return result
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
            

    async def analyze(self, data, *args, **kwargs):
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

        # Create the stream generator instance
        stream_generator = AnalysisStreamGenerator(
            client=self.client,
            system_prompt=system_prompt,
            prompt_parts=prompt_parts,
            response_schema=AnalysisResponseSchema
        )
        
        # Return StreamingHttpResponse with SSE headers
        response = StreamingHttpResponse(
            stream_generator.generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production
        return response


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
    is_correct: bool = Field(description="Indicates if the solution is correct")
    feedback: str = Field(description="Feedback on the provided solution")
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
        text_fallback = request.FILES.get('text')
        
        # Create transcriber instance
        transcriber = ImageTranscriber(client=self.client)
        
        try:
            result = await transcriber.transcribe(
                image_file=image_file,
                text_fallback=text_fallback,
                enhance=enhance
            )
            return result
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    async def gym_solution(self, data, *args, **kwargs):
        """"Implementation of the gym solution logic"""
        system_prompt = """
        You are an expert math problem solver. Provide step-by-step solutions in LaTeX format.
        """

        prompt_parts = []

        prompt_parts.append({'text': 'Solve the following math problem: '})

        if data.get('problem'):
            prompt_parts.append({'text': data['problem']})
        else:
            return Response({'error': 'Input problem context'}, status=400)

        stream_generator = AnalysisStreamGenerator(
            client=self.client,
            system_prompt=system_prompt,
            prompt_parts=prompt_parts,
            response_schema=GymResponseSchema
        )

        response = StreamingHttpResponse(
            stream_generator.generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production

        return response
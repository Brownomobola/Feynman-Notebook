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

class AnalyzeSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)

    async def transcribe_image(self, request, enhance: bool= True, *args, **kwargs)-> Optional[str] | Response:
        """
        Transcribes handwritten math with optional image preprocessing.
        
        Args:
            image_path: Path to the image file
            enhance: Whether to enhance contrast and sharpness
            resize: Optional tuple (width, height) to resize image
            
        Returns:
            Transcribed text in LaTeX/Markdown format, or error message
        """
        # Check if the image was inputted by the user
        if not request.FILES.get('image'): 
            return request.FILES.get('text') if request.FILES.get('text') else Response({'error': 'You must input at least an image or text'}, status=400)
        
        data = request.FILES.get('image')
        try:
            # Open the image using the PIL library
            image = Image.open(data)

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image.convert('RGB')

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
                model = "gemini-2.5-flash",
                contents= {'parts': prompt_parts}
            )
            return response.text if response.text else request.FILES.get('text')
        
        # Handle exceptions that may occur
        except Exception as e:
            return Response({'error': f'Error {str(e)} occured during transcription'}, status=500)
            

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

        # Async generator to stream the response
        async def stream_generator():
            accumulated_text = ""
            field_positions = {}
            
            # Get schema properties
            schema_properties = AnalysisResponseSchema.model_json_schema().get('properties', {})
            
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
            
            try:
                response = await self.client.aio.models.generate_content_stream(
                    model="gemini-2.0-flash-exp",
                    config={
                        'system_instruction': system_prompt,
                        'response_mime_type': 'application/json',
                        'response_schema': AnalysisResponseSchema
                    },
                    contents={'parts': prompt_parts}
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
        
        # Return StreamingHttpResponse with SSE headers
        response = StreamingHttpResponse(
            stream_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production
        return response
                
                
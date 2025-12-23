from django.shortcuts import render
from rest_framework.views import APIView
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
            return f"Error {str(e)} occurred during transcription"
            
        
            

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

        if data['problem']:
            prompt_parts.append({'text': data['problem']})
        else:
            return Response({'error': 'Input problem context'}, status=400)
        
        # Add attempt context
        prompt_parts.append({'text': 'Here is the attempt context: '})

        if data['attempt']:
            prompt_parts.append({'text': data['attempt']})
        else:
            return Response({'error': 'Input attempt context'}, status=400)



        # 5. Generate Content
        try:
            response = await self.client.aio.models.generate_content_stream(
                model = "gemini-2.5-flash",
                config = {
                    'system_instruction': system_prompt,
                    'response_mime_type': 'application/json',
                    'response_json_schema': AnalysisResponseSchema.model_json_schema()
                },
                contents={'parts': prompt_parts}
            )

            response_parsed = json.loads(response)
            
            
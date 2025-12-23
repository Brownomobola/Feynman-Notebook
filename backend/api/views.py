from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from google import genai
from google.genai import types
import os
from PIL import Image
from backend.backend.settings import GEMINI_API_KEY
from typing import List, Dict, Any, Optional

class AnalyzeSolutionView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)

    async def transcribe_image(self, data, *args, **kwargs)-> str | None:
        """Uses the gemini model for OCR on the problem and attempts image"""
        if not data['image']:
            return data['text']
        
        try:
            # Add the images for OCR
            prompt = [{'text': 'Transcribe the handwritten maths in this image to LaTex/Markdown. Return ONLY the text, no explanations.'},
            {'inline_data': {
                'mime_type': 'image/jpeg',
                'data': data['image']
            }}]

            response = await self.client.aio.models.generate_content(
                model = "gemini-2.5-flash",
                contents= {'parts': prompt}
            )
            return response.text if response.text else None
        except Exception as e:
            return f"Error {str(e)} occurred during transcription"
            
        
            

    def post(self, request, *args, **kwargs):
        # 1. Setup Gemini (client is a class attribute)
        # Using Gemini 1.5 Pro (latest stable equivalent to 3 for API access)
        model = 'gemini-2.5-flash-lite'

        # 2. Get Images from Request
        problem_img_file = request.FILES.get('problem_image')
        attempt_img_file = request.FILES.get('attempt_image')

        if not problem_img_file or not attempt_img_file:
            return Response({"error": "Both images are required"}, status=400)

        # 3. Convert to PIL Images for Gemini
        problem_img = Image.open(problem_img_file)
        attempt_img = Image.open(attempt_img_file)

        # 4. The Feynman Prompt (The "Secret Sauce")
        prompt = """
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
        *   **LaTeX:** You MUST use standard LaTeX delimiters for all math expressions ($...$ or $$...$$).
        </formatting_rules>
        """

        # 5. Generate Content
        try:
            chat = self.client.chats.create(
                model=model,
                config=types.GenerateContentConfig(
                    system_instruction=prompt,)
            )
            response = chat.send_message_stream([prompts])
            return Response(response.text) # Returning raw text (JSON string)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
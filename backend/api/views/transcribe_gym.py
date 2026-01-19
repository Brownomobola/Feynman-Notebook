from rest_framework.response import Response
from adrf.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from google import genai
from typing import Optional
from ..services import ImageTranscriber
from ..models import GymTranscript

GEMINI_API_KEY = settings.GEMINI_API_KEY

class TranscribeGymImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)


    async def post(self, request, enhance: bool = True, *args, **kwargs) -> Optional[str] | Response:
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

                gym_transcript = await GymTranscript.objects.acreate(
                image_obj=image_file,
                text_obj=text_fallback,
                transcript = result
                )

                request.session['gym_transcript'] = gym_transcript.id

                return Response(result)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
            except Exception as e:
                return Response({'error': str(e)}, status=500)
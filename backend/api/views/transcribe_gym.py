from rest_framework.response import Response
from adrf.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from google import genai
from typing import Optional
from ..services import ImageTranscriber, get_gemini_client
from ..models import GymTranscript

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY

class TranscribeGymImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)


    async def post(self, request, enhance: bool = True, *args, **kwargs) -> Response:
            """
            Transcribes handwritten math from an uploaded image.
            
            Args:
                request: The HTTP request containing the image file
                enhance: Whether to enhance contrast and sharpness
                
            Returns:
                Transcribed text in LaTeX/Markdown format, or error Response
            """
            # Get shared client instance
            client = get_gemini_client()
            
            # Get image and text from request
            image_file = request.FILES.get('data_image')
            text_fallback = request.POST.get('data_text', '')
            
            # Create transcriber instance
            transcriber = ImageTranscriber(client=client)
            
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
from rest_framework.response import Response
from adrf.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from django.conf import settings
from google import genai
from ..services import ImageTranscriber
from ..models import AnalysisTranscript

GEMINI_API_KEY = settings.GEMINI_API_KEY


class TranscribeAnalysisImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)

    async def post(self, request, enhance: bool = True, *args, **kwargs) -> HttpResponse | Response:
        """
        Transcribes handwritten math from an uploaded image.

        Args:
            request: The HTTP request containing the image file
            enhance: Whether to enhance contrast and sharpness

        Returns:
            Transcribed text in LaTeX/Markdown format, or error Response
        """
        image_file = request.FILES.get('data_image')
        text_fallback = request.POST.get('data_text', '')
        is_question = 'is_question' in request.POST

        transcriber = ImageTranscriber(client=self.client)

        try:
            result = await transcriber.transcribe(
                image_file=image_file,
                text_fallback=text_fallback,
                enhance=enhance
            )

            analysis_transcript = await AnalysisTranscript.objects.acreate(
                image_obj=image_file,
                text_obj=text_fallback,
                is_question=is_question,
                transcript=result
            )

            request.session['analysis_transcript'] = analysis_transcript.id

            return HttpResponse(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
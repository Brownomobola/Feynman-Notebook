from rest_framework.response import Response
from adrf.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from ..services import ImageTranscriber, get_gemini_client
from ..models import AnalysisTranscript
from .auth import get_user_session_info

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY


class TranscribeAnalysisImageView(APIView):
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

        # Retrieve the data from the request
        image_file = request.FILES.get('data_image')
        text_fallback = request.POST.get('data_text', '')
        is_question = 'is_question' in request.POST

        # Get owner info
        owner_info = get_user_session_info(request)

        transcriber = ImageTranscriber(client=client)

        try:
            result = await transcriber.transcribe(
                image_file=image_file,
                text_fallback=text_fallback,
                enhance=enhance
            )

            analysis_transcript = await AnalysisTranscript.objects.acreate(
                user=owner_info['user'],
                session_key=owner_info['session_key'],
                image_obj=image_file,
                text_obj=text_fallback,
                is_question=is_question,
                transcript=result
            )

            request.session['analysis_transcript'] = analysis_transcript.id

            return Response(result, status=200)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
from rest_framework.parsers import MultiPartParser, FormParser
from adrf.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from django.http import StreamingHttpResponse
import json, logging
from ..schemas import GymGenerateMCQResponseSchema, GymGenerateOpenEndedResponseSchema
from ..services import StreamGenerator, get_gemini_client
from ..models import Analysis, GymQuestions, GymSesh
from .auth import get_user_session_info, filter_by_owner

logger = logging.getLogger(__name__)

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY

class GymGenerateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    async def post(self, request, *args, **kwargs):
        """Handles all POST request for generating questions sent from the Gym page"""
        
        # Get shared client instance
        client = get_gemini_client()
        
        # Get user/session info for ownership
        owner_info = get_user_session_info(request)

        system_prompt = """You are a "Feynman Tutor." 
        Your goal is to generate a new question that is similar in style and topic to the original question, but with a different context and numbers. 
        The new question should be designed to test the same underlying concepts and problem-solving skills as the original question, 
        but in a way that requires the student to apply their knowledge in a new and creative way. 
        The question should be clear, concise, and unambiguous, and should include all necessary information for the student to solve it. 
        The question should also be appropriately challenging for a student who has just completed the original question, 
        pushing them to deepen their understanding of the material and apply it in new ways."""

        data = request.POST.dict()
        prompt_parts = []

        prompt_parts.append({'text': 'Generate this number of questions on the topic discussed in the analysis section. '
                                    'Use the original question and the analysis as context.'})

        analysis_id = data.get('analysis_id')

        try:
            analysis = await Analysis.objects.aget(id=analysis_id)
            prompt_parts.append({'text': f'The original question was: {analysis.problem}'})
            prompt_parts.append({'text': f"The student's attempt was: {analysis.attempt}"})
            prompt_parts.append({'text': f"The things the student got right were: {analysis.praise}"})
            prompt_parts.append({'text': f"The things the student got wrong were: {analysis.diagnosis}"})
        except Analysis.DoesNotExist:
            return Response({'error': 'Analysis with the provided ID does not exist'}, status=404)

        if data.get('type'):
            if data.get('type') == "MCQ":
                prompt_parts.append({'text': 'The question type is multiple choice.'})
                prompt_parts.append({'text': f'Generate {data.get("num_questions", 10)} questions.'})

            if data.get('type') == "Open-Ended":
                prompt_parts.append({'text': 'The question type is open-ended.'})
                prompt_parts.append({'text': f'Generate {data.get("num_questions", 5)} questions.'})
        else:
            return Response({'error': 'Input question type'}, status=400)
        

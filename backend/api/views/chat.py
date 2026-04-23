from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from adrf.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.http import StreamingHttpResponse
import json
from ..models import Chat, Analysis, Question, Attempt
from ..services import ChatStreamGenerator, get_gemini_client
from .auth import get_user_session_info

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY


async def build_conversation_history(origin, db_object):
    """
    Builds the conversation history list based on the origin of the chat.

    Origins:
        - analysis: Prepends analysis context (problem, attempt, praise, diagnosis,
                    explanation) as a model turn, then appends all stored chat messages.
        - gym:      Prepends question/attempt context (question_text, theory_rubric,
                    user_response, feedback) as a model turn, then appends all stored
                    chat messages.
        - learn:    Appends all stored chat messages with no additional context.

    Returns:
        list[dict]: Conversation history in {'role': ..., 'content': ...} format,
                    ready to pass to ChatStreamGenerator.
    """
    conversation_history = []

    if origin == 'analysis':
        context_block = (
            f"[Context] I have reviewed the student's work:\n"
            f"Problem: {db_object.problem}\n"
            f"Student Attempt: {db_object.attempt}\n\n"
            f"My analysis:\n"
            f"Praise: {db_object.praise}\n"
            f"Diagnosis: {db_object.diagnosis}\n"
            f"Explanation: {db_object.explanation}"
        )
        conversation_history.append({
            'role': 'model',
            'content': context_block
        })

        chat_messages = db_object.chats.all().order_by('created_at')
        async for msg in chat_messages:
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })

    elif origin == 'gym':
        context_block = (
            f"[Context] The student attempted the following practice question:\n"
            f"Question: {db_object.question.question_text}\n"
            f"Theory Rubric: {db_object.question.theory_rubric}\n\n"
            f"Student Response: {db_object.user_response}\n"
            f"Feedback: {db_object.feedback}"
        )
        conversation_history.append({
            'role': 'model',
            'content': context_block
        })

        chat_messages = db_object.analysis.chats.all().order_by('created_at')
        async for msg in chat_messages:
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })

    else:
        chat_messages = db_object.chats.all().order_by('created_at')
        async for msg in chat_messages:
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })

    return conversation_history


class ChatView(APIView):
    """
    Handles conversational chat interactions with the AI tutor.
    Builds context dynamically based on the origin of the chat session.
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    async def post(self, request, *args, **kwargs):
        """
        Streams a conversational response based on the user's message,
        conversation history, and origin-specific context.

        Request body:
            - message:     The user's current message (required)
            - origin:      Source of the chat — 'analysis', 'gym', or 'learn' (required)
            - analysis_id: Required when origin is 'analysis' or 'learn'
            - attempt_id:  Required when origin is 'gym'

        Returns:
            StreamingHttpResponse with SSE formatted chat messages
        """
        client = get_gemini_client()
        owner_info = get_user_session_info(request)

        # Parse request data
        if request.content_type and 'application/json' in request.content_type:
            data = request.data
        else:
            data = request.POST.dict()

        # Validate required fields
        user_message = data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)

        origin = data.get('origin')
        if not origin or origin not in ('analysis', 'gym', 'learn'):
            return Response(
                {'error': "origin is required and must be one of: 'analysis', 'gym', 'learn'"},
                status=400
            )

        # --- Resolve the primary object and verify ownership ---
        db_object = None

        if origin == 'analysis':
            analysis_id = data.get('analysis_id')
            if not analysis_id:
                return Response({'error': 'analysis_id is required for analysis origin'}, status=400)

            request.session['analysis_id'] = analysis_id

            try:
                analysis = await Analysis.objects.aget(id=analysis_id)
            except Analysis.DoesNotExist:
                return Response({'error': 'Analysis not found'}, status=404)

            if owner_info['user']:
                if analysis.user != owner_info['user']:
                    return Response({'error': 'Access denied'}, status=403)
            elif owner_info['session_key']:
                if analysis.session_key != owner_info['session_key']:
                    return Response({'error': 'Access denied'}, status=403)
            db_object = analysis

        elif origin == 'gym':
            attempt_id  = data.get('attempt_id')
            if not attempt_id:
                return Response({'error': 'attempt_id is required for gym origin'}, status=400)

            try:
                attempt = await Attempt.objects.select_related('analysis', 'question').aget(id=attempt_id)
            except Attempt.DoesNotExist:
                return Response({'error': 'Question not found'}, status=404)

            if owner_info['user']:
                if attempt.owner_info != owner_info['user']:
                    return Response({'error': 'Access denied'}, status=403)
            elif owner_info['session_key']:
                if attempt.session_info != owner_info['session_key']:
                    return Response({'error': 'Access denied'}, status=403)
            db_object = attempt

        elif origin == 'learn':
            analysis_id = data.get('analysis_id')
            if not analysis_id:
                return Response({'error': 'analysis_id is required for learn origin'}, status=400)

            request.session['analysis_id'] = analysis_id

            try:
                analysis = await Analysis.objects.aget(id=analysis_id)
            except Analysis.DoesNotExist:
                return Response({'error': 'Analysis not found'}, status=404)

            if owner_info['user']:
                if analysis.user != owner_info['user']:
                    return Response({'error': 'Access denied'}, status=403)
            elif owner_info['session_key']:
                if analysis.session_key != owner_info['session_key']:
                    return Response({'error': 'Access denied'}, status=403)
            db_object = analysis

        # --- Build conversation history based on origin ---
        try:
            conversation_history = await build_conversation_history(
                origin=origin,
                db_object=db_object
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        # --- System prompt (no origin-specific context here — that lives in history) ---
        system_prompt = """
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

        # --- Persist the incoming user message ---
        chat_create_kwargs = {
            'role': Chat.Role.USER,
            'content': user_message,
        }
        if origin == 'analysis':
            chat_create_kwargs['analysis'] = db_object
        if origin == 'gym':
            chat_create_kwargs['analysis'] = db_object.analysis

        await Chat.objects.acreate(**chat_create_kwargs)

        # --- Stream response and persist the model reply ---
        async def stream_with_db_save():
            accumulated_response = ""

            chat_generator = ChatStreamGenerator(
                client=client,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )

            async for chunk in chat_generator.generate():
                yield chunk

                try:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        json_str = chunk_str[6:].strip()
                        event_data = json.loads(json_str)

                        if event_data['type'] == 'text':
                            accumulated_response += event_data['content']
                        elif event_data['type'] == 'complete':
                            model_create_kwargs = {
                                'role': Chat.Role.MODEL,
                                'content': accumulated_response,
                            }
                            if origin == 'analysis':
                                model_create_kwargs['analysis'] = db_object
                            if origin == 'gym':
                                model_create_kwargs['analysis'] = db_object.analysis

                            await Chat.objects.acreate(**model_create_kwargs)
                except Exception:
                    pass

        response = StreamingHttpResponse(
            stream_with_db_save(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'

        return response

    async def get(self, request, *args, **kwargs):
        """
        Retrieves all chat messages for a given analysis.

        Query params:
            - analysis_id: ID of the analysis (required)

        Returns:
            List of chat messages
        """
        owner_info = get_user_session_info(request)

        analysis_id = request.GET.get('analysis_id')
        if not analysis_id:
            return Response({'error': 'analysis_id is required'}, status=400)

        try:
            analysis = await Analysis.objects.aget(id=analysis_id)
            if owner_info['user']:
                if analysis.user != owner_info['user']:
                    return Response({'error': 'Access denied'}, status=403)
            elif owner_info['session_key']:
                if analysis.session_key != owner_info['session_key']:
                    return Response({'error': 'Access denied'}, status=403)
        except Analysis.DoesNotExist:
            return Response({'error': 'Analysis not found'}, status=404)

        chat_messages = analysis.chats.all()
        messages = []
        async for msg in chat_messages:
            messages.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat()
            })

        return Response({
            'analysis_id': analysis_id,
            'messages': messages
        })
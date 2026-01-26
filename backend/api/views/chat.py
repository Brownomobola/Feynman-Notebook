from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from adrf.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.http import StreamingHttpResponse
from google import genai
import json
from ..models import Chat, Analysis
from ..services import ChatStreamGenerator, get_gemini_client
from .auth import get_user_session_info, filter_by_owner

FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY

class ChatView(APIView):
    """
    Handles conversational chat interactions with the AI tutor.
    Can incorporate analysis history for context-aware responses.
    """
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    async def post(self, request, *args, **kwargs):
        """
        Streams a conversational response based on the user's message and conversation history.
        
        Request body:
            - message: The user's current message (required)
            - analysis_id: ID of the analysis for context (required)
        
        Returns:
            StreamingHttpResponse with SSE formatted chat messages
        """
        # Get shared client instance
        client = get_gemini_client()
        
        # Get user/session info for ownership
        owner_info = get_user_session_info(request)
        
        # Parse data from request
        if request.content_type and 'application/json' in request.content_type:
            data = request.data
        else:
            data = request.POST.dict()
        
        # Validate user message
        user_message = data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)
        
        # Get analysis_id (required for context and DB storage)
        analysis_id = data.get('analysis_id')
        if not analysis_id:
            return Response({'error': 'analysis_id is required'}, status=400)
        
        request.session['analysis_id'] = analysis_id
        
        # Fetch the analysis for context (and verify ownership)
        try:
            analysis = await Analysis.objects.aget(id=analysis_id)
            # Verify ownership
            if owner_info['user']:
                if analysis.user != owner_info['user']:
                    return Response({'error': 'Access denied'}, status=403)
            elif owner_info['session_key']:
                if analysis.session_key != owner_info['session_key']:
                    return Response({'error': 'Access denied'}, status=403)
        except Analysis.DoesNotExist:
            return Response({'error': 'Analysis not found'}, status=404)
        
        # Load conversation history from database
        chat_messages = Chat.objects.filter(analysis_id=analysis_id).order_by('created_at')
        conversation_history = []
        async for msg in chat_messages:
            conversation_history.append({
                'role': msg.role,
                'content': msg.content
            })
        
        # Build system prompt with analysis context
        system_prompt = f"""
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
        
        <previous_analysis>
        You previously analyzed this student's work with the following context:
        Problem: {analysis.problem}
        Student Attempt: {analysis.attempt}
        
        Your previous analysis:
        Title: {analysis.title}
        Tags: {', '.join(analysis.tags) if analysis.tags else 'N/A'}
        Praise: {analysis.praise}
        Diagnosis: {analysis.diagnosis}
        Explanation: {analysis.explanation}
        
        Use this context to provide more relevant and personalized guidance.
        </previous_analysis>
        """
        
        # Save the user message to the database first
        await Chat.objects.acreate(
            user=owner_info['user'],
            session_key=owner_info['session_key'],
            analysis=analysis,
            role=Chat.Role.USER,
            content=user_message
        )
        
        async def stream_with_db_save():
            """Async generator for streaming chat and saving to database"""
            accumulated_response = ""

            # Create chat stream generator
            chat_generator = ChatStreamGenerator(
                client=client,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_message=user_message
            )

            async for chunk in chat_generator.generate():
                yield chunk
                
                # Parse chunk to accumulate the response
                try:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        json_str = chunk_str[6:].strip()
                        event_data = json.loads(json_str)
                        
                        if event_data['type'] == 'text':
                            accumulated_response += event_data['content']
                        elif event_data['type'] == 'complete':
                            # Save the complete AI response to the database
                            await Chat.objects.acreate(
                                user=owner_info['user'],
                                session_key=owner_info['session_key'],
                                analysis=analysis,
                                role=Chat.Role.MODEL,
                                content=accumulated_response
                            )
                except Exception:
                    pass
        
        # Return streaming response
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
        # Get user/session info for ownership verification
        owner_info = get_user_session_info(request)
        
        analysis_id = request.GET.get('analysis_id')
        if not analysis_id:
            return Response({'error': 'analysis_id is required'}, status=400)
        
        # Verify analysis ownership
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
        
        # Fetch all chat messages for this analysis
        chat_messages = Chat.objects.filter(analysis_id=analysis_id).order_by('created_at')
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
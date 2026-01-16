from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.http import StreamingHttpResponse
from google import genai
from ..services import ChatStreamGenerator

GEMINI_API_KEY = settings.GEMINI_API_KEY

class ChatView(APIView):
    """
    Handles conversational chat interactions with the AI tutor.
    Can incorporate analysis history for context-aware responses.
    """
    parser_classes = (MultiPartParser, FormParser)
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    async def chat(self, data, *args, **kwargs):
        """
        Streams a conversational response based on the user's message and conversation history.
        
        Args:
            data: Dictionary containing:
                - message: The user's current message (required)
                - history: List of previous conversation messages (optional)
                - analysis_context: Previous analysis result for context (optional)
                - system_prompt: Custom system prompt (optional)
        
        Returns:
            StreamingHttpResponse with SSE formatted chat messages
        """
        # Validate user message
        user_message = data.get('message')
        if not user_message:
            return Response({'error': 'Message is required'}, status=400)
        
        # Get conversation history (default to empty list)
        conversation_history = data.get('history', [])
        
        # Get optional analysis context
        analysis_context = data.get('analysis_context')
        
        # Build system prompt
        base_system_prompt = """
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
        
        # Add analysis context if provided
        if analysis_context:
            context_prompt = f"""
        
        <previous_analysis>
        You previously analyzed this student's work with the following context:
        Problem: {analysis_context.get('problem', 'N/A')}
        Student Attempt: {analysis_context.get('attempt', 'N/A')}
        
        Your previous analysis:
        Title: {analysis_context.get('title', 'N/A')}
        Tags: {', '.join(analysis_context.get('tags', []))}
        Diagnosis: {analysis_context.get('diagnosis', 'N/A')}
        Explanation: {analysis_context.get('explanation', 'N/A')}
        
        Use this context to provide more relevant and personalized guidance.
        </previous_analysis>
        """
            system_prompt = base_system_prompt + context_prompt
        else:
            system_prompt = base_system_prompt
        
        # Allow custom system prompt override
        if data.get('system_prompt'):
            system_prompt = data['system_prompt']
        
        # Create chat stream generator
        chat_generator = ChatStreamGenerator(
            client=self.client,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=user_message
        )
        
        # Return streaming response
        response = StreamingHttpResponse(
            chat_generator.generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'  # Adjust for your CORS policy when releasing for production
        
        return response
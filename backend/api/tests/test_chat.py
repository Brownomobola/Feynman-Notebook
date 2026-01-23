"""
Test script for ChatView

This script tests the chat functionality including:
- Chat requests with valid messages
- Chat requests with conversation history
- Chat requests with analysis context
- Error handling for missing required fields
- Custom system prompt support
- Streaming response format

Usage:
    python -m api.tests.test_chat
"""
import os
import sys
import django
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Now we can import Django-dependent modules
from django.test import RequestFactory
from django.conf import settings
from django.http import StreamingHttpResponse
from api.views.chat import ChatView
from api.services.streaming import ChatStreamGenerator


class MockSession(dict):
    """Mock session object that behaves like a dict but can store session data."""
    pass


def create_mock_request(method='POST', data=None, files=None):
    """
    Create a mock Django request object.
    
    Args:
        method: HTTP method ('POST' or 'GET')
        data: POST data dictionary
        files: FILES dictionary
    
    Returns:
        A mock request object
    """
    factory = RequestFactory()
    
    if method == 'POST':
        request = factory.post('/api/chat/', data or {})
    else:
        request = factory.get('/api/chat/')
    
    request.session = MockSession()
    
    if files:
        for key, value in files.items():
            request.FILES[key] = value
    
    return request


def create_mock_chat_stream_response():
    """
    Create mock SSE stream events that simulate the AI chat response.
    
    Returns:
        List of encoded SSE event bytes
    """
    events = [
        {'type': 'text', 'content': 'That\'s a great question! ', 'is_complete': False},
        {'type': 'text', 'content': 'Let me help you understand ', 'is_complete': False},
        {'type': 'text', 'content': 'the chain rule better.\n\n', 'is_complete': False},
        {'type': 'text', 'content': 'Think of it like opening ', 'is_complete': False},
        {'type': 'text', 'content': 'nested boxes - you work from ', 'is_complete': False},
        {'type': 'text', 'content': 'the outside in.\n\n', 'is_complete': False},
        {'type': 'text', 'content': 'The formula is: ', 'is_complete': False},
        {'type': 'text', 'content': '$\\frac{d}{dx}[f(g(x))] = f\'(g(x)) \\cdot g\'(x)$', 'is_complete': False},
        {
            'type': 'complete',
            'content': 'That\'s a great question! Let me help you understand the chain rule better.\n\nThink of it like opening nested boxes - you work from the outside in.\n\nThe formula is: $\\frac{d}{dx}[f(g(x))] = f\'(g(x)) \\cdot g\'(x)$',
            'is_complete': True
        }
    ]
    
    return [f"data: {json.dumps(event)}\n\n".encode('utf-8') for event in events]


async def mock_chat_stream_generator():
    """Async generator that yields mock chat stream events."""
    for chunk in create_mock_chat_stream_response():
        yield chunk


async def test_chat_missing_message():
    """
    Test chat request without message (should fail with 400).
    """
    print("\n" + "=" * 60)
    print("Testing chat without message (should fail)...")
    print("=" * 60)
    
    view = ChatView()
    
    try:
        response = await view.chat(data={})
        print(f"\nStatus Code: {response.status_code}")
        
        if hasattr(response, 'data'):
            print(f"Response Data: {response.data}")
        
        if response.status_code == 400:
            print("\n✓ Test PASSED: Properly rejected request without message")
        else:
            print(f"\n✗ Test FAILED: Expected status 400, got {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_chat_with_valid_message():
    """
    Test chat request with valid message (mocked AI response).
    """
    print("\n" + "=" * 60)
    print("Testing chat with valid message (mocked AI)...")
    print("=" * 60)
    
    data = {
        'message': 'Can you explain the chain rule to me?'
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            print(f"\nResponse Type: {type(response).__name__}")
            print(f"Content Type: {response.get('Content-Type', 'N/A')}")
            
            if isinstance(response, StreamingHttpResponse):
                print("\n✓ Test PASSED: Got streaming response")
                
                # Verify headers
                assert response['Content-Type'] == 'text/event-stream'
                print("✓ Content-Type header is correct")
                
                assert response['Cache-Control'] == 'no-cache'
                print("✓ Cache-Control header is correct")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_with_conversation_history():
    """
    Test chat request with conversation history.
    """
    print("\n" + "=" * 60)
    print("Testing chat with conversation history (mocked AI)...")
    print("=" * 60)
    
    data = {
        'message': 'What about the power rule?',
        'history': [
            {'role': 'user', 'content': 'Can you explain the chain rule to me?'},
            {'role': 'assistant', 'content': 'The chain rule is used for composite functions...'},
            {'role': 'user', 'content': 'I see, that makes sense!'},
            {'role': 'assistant', 'content': 'Great! Do you have any other questions?'}
        ]
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            print(f"\nResponse Type: {type(response).__name__}")
            
            if isinstance(response, StreamingHttpResponse):
                print("\n✓ Test PASSED: Got streaming response with history")
                
                # Verify that ChatStreamGenerator was called with correct history
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                
                assert 'conversation_history' in call_kwargs
                assert len(call_kwargs['conversation_history']) == 4
                print(f"✓ History passed with {len(call_kwargs['conversation_history'])} messages")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_with_analysis_context():
    """
    Test chat request with analysis context for personalized responses.
    """
    print("\n" + "=" * 60)
    print("Testing chat with analysis context (mocked AI)...")
    print("=" * 60)
    
    data = {
        'message': 'Can you help me understand my mistake better?',
        'analysis_context': {
            'problem': 'Find the derivative of f(x) = sin(x^2)',
            'attempt': 'f\'(x) = cos(x^2)',
            'title': 'Chain Rule Application',
            'tags': ['Calculus', 'Chain Rule', 'Trigonometry'],
            'diagnosis': 'You forgot to apply the chain rule to the inner function.',
            'explanation': 'When you have a composite function, you need to differentiate both the outer and inner functions.'
        }
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            print(f"\nResponse Type: {type(response).__name__}")
            
            if isinstance(response, StreamingHttpResponse):
                print("\n✓ Test PASSED: Got streaming response with analysis context")
                
                # Verify that ChatStreamGenerator was called with context in system prompt
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                
                assert 'system_prompt' in call_kwargs
                system_prompt = call_kwargs['system_prompt']
                
                # Check that analysis context is included in the system prompt
                assert 'previous_analysis' in system_prompt.lower()
                print("✓ Analysis context included in system prompt")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_with_custom_system_prompt():
    """
    Test chat request with custom system prompt override.
    """
    print("\n" + "=" * 60)
    print("Testing chat with custom system prompt (mocked AI)...")
    print("=" * 60)
    
    custom_prompt = """
    You are a strict math tutor. Only answer math-related questions.
    Be concise and direct in your responses.
    """
    
    data = {
        'message': 'What is 2 + 2?',
        'system_prompt': custom_prompt
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            print(f"\nResponse Type: {type(response).__name__}")
            
            if isinstance(response, StreamingHttpResponse):
                print("\n✓ Test PASSED: Got streaming response with custom prompt")
                
                # Verify that ChatStreamGenerator was called with custom system prompt
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                
                assert 'system_prompt' in call_kwargs
                assert call_kwargs['system_prompt'] == custom_prompt
                print("✓ Custom system prompt used correctly")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_with_empty_history():
    """
    Test chat request with empty conversation history.
    """
    print("\n" + "=" * 60)
    print("Testing chat with empty history (mocked AI)...")
    print("=" * 60)
    
    data = {
        'message': 'Hello, I need help with calculus.',
        'history': []
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            print(f"\nResponse Type: {type(response).__name__}")
            
            if isinstance(response, StreamingHttpResponse):
                print("\n✓ Test PASSED: Got streaming response with empty history")
                
                # Verify that ChatStreamGenerator was called with empty history
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                
                assert 'conversation_history' in call_kwargs
                assert len(call_kwargs['conversation_history']) == 0
                print("✓ Empty history handled correctly")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_stream_generator_build_contents():
    """
    Test the ChatStreamGenerator's _build_conversation_contents method.
    """
    print("\n" + "=" * 60)
    print("Testing ChatStreamGenerator._build_conversation_contents()...")
    print("=" * 60)
    
    # Create a mock client
    mock_client = MagicMock()
    
    history = [
        {'role': 'user', 'content': 'First message'},
        {'role': 'assistant', 'content': 'First response'},
        {'role': 'user', 'content': 'Second message'},
        {'role': 'model', 'content': 'Second response'},  # Test 'model' role alias
    ]
    
    generator = ChatStreamGenerator(
        client=mock_client,
        system_prompt='Test prompt',
        conversation_history=history,
        user_message='Current message'
    )
    
    try:
        contents = generator._build_conversation_contents()
        
        print(f"\nBuilt contents with {len(contents)} items")
        
        # Should have 4 history items + 1 current message = 5 total
        assert len(contents) == 5
        print("✓ Correct number of content items")
        
        # Verify roles are correctly mapped
        assert contents[0]['role'] == 'user'
        assert contents[1]['role'] == 'model'
        assert contents[2]['role'] == 'user'
        assert contents[3]['role'] == 'model'
        assert contents[4]['role'] == 'user'  # Current message
        print("✓ Roles correctly mapped (assistant -> model)")
        
        # Verify current message is last
        assert contents[4]['parts'][0]['text'] == 'Current message'
        print("✓ Current message is last in contents")
        
        print("\n✓ Test PASSED: _build_conversation_contents works correctly")
        
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {str(e)}")
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_chat_response_headers():
    """
    Test that chat responses have correct SSE headers.
    """
    print("\n" + "=" * 60)
    print("Testing chat response headers...")
    print("=" * 60)
    
    data = {
        'message': 'Test message'
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            if isinstance(response, StreamingHttpResponse):
                # Check all required headers
                headers_to_check = {
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*'
                }
                
                all_correct = True
                for header, expected_value in headers_to_check.items():
                    actual_value = response.get(header)
                    if actual_value == expected_value:
                        print(f"✓ {header}: {actual_value}")
                    else:
                        print(f"✗ {header}: expected '{expected_value}', got '{actual_value}'")
                        all_correct = False
                
                if all_correct:
                    print("\n✓ Test PASSED: All headers are correct")
                else:
                    print("\n✗ Test FAILED: Some headers are incorrect")
                    
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_with_latex_content():
    """
    Test chat handling of LaTeX content in messages.
    """
    print("\n" + "=" * 60)
    print("Testing chat with LaTeX content...")
    print("=" * 60)
    
    data = {
        'message': 'How do I solve $\\int x^2 dx$?'
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            if isinstance(response, StreamingHttpResponse):
                # Verify that ChatStreamGenerator received the LaTeX content correctly
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                
                assert call_kwargs['user_message'] == 'How do I solve $\\int x^2 dx$?'
                print("✓ LaTeX content preserved in message")
                
                print("\n✓ Test PASSED: LaTeX content handled correctly")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_with_long_message():
    """
    Test chat handling of longer messages.
    """
    print("\n" + "=" * 60)
    print("Testing chat with long message...")
    print("=" * 60)
    
    long_message = """
    I've been trying to understand calculus for weeks now, and I'm particularly 
    struggling with the concept of limits. When I look at the formal definition:
    
    $$\\lim_{x \\to a} f(x) = L$$
    
    I understand that it means as x approaches a, f(x) approaches L, but I don't 
    understand why we need such a formal definition. Can you explain it in simpler 
    terms? Also, how does this relate to continuity? And when would I use the 
    epsilon-delta definition vs. just evaluating the limit directly?
    
    I've tried reading textbooks but they're all so confusing. Please help!
    """
    
    data = {
        'message': long_message
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            if isinstance(response, StreamingHttpResponse):
                # Verify that ChatStreamGenerator received the long message
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                
                assert call_kwargs['user_message'] == long_message
                print(f"✓ Long message ({len(long_message)} chars) handled correctly")
                
                print("\n✓ Test PASSED: Long message handled correctly")
                
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_chat_default_system_prompt_content():
    """
    Test that the default system prompt contains expected content.
    """
    print("\n" + "=" * 60)
    print("Testing default system prompt content...")
    print("=" * 60)
    
    data = {
        'message': 'Hello'
    }
    
    view = ChatView()
    
    # Mock the ChatStreamGenerator
    with patch('api.views.chat.ChatStreamGenerator') as MockChatStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_chat_stream_generator
        MockChatStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.chat(data=data)
            
            if isinstance(response, StreamingHttpResponse):
                MockChatStreamGenerator.assert_called_once()
                call_kwargs = MockChatStreamGenerator.call_args[1]
                system_prompt = call_kwargs['system_prompt']
                
                # Check for expected content in default system prompt
                expected_elements = [
                    'Feynman',
                    'tutor',
                    'Socratic',
                    'LaTeX'
                ]
                
                # Optional elements that may or may not be present
                optional_elements = ['analogy', 'analogies']
                
                all_present = True
                for element in expected_elements:
                    if element.lower() in system_prompt.lower():
                        print(f"✓ System prompt contains '{element}'")
                    else:
                        print(f"✗ System prompt missing '{element}'")
                        all_present = False
                
                # Check optional elements (just for info, won't fail test)
                for element in optional_elements:
                    if element.lower() in system_prompt.lower():
                        print(f"✓ System prompt contains optional '{element}'")
                
                if all_present:
                    print("\n✓ Test PASSED: Default system prompt has all expected elements")
                else:
                    print("\n✗ Test FAILED: Default system prompt missing some elements")
                    
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def main():
    """
    Run all tests.
    """
    print("\n" + "=" * 60)
    print("CHAT VIEW TEST SUITE")
    print("=" * 60)
    print(f"\nDjango Settings: {settings.SETTINGS_MODULE}")
    print(f"Database: {settings.DATABASES['default']['ENGINE']}")
    
    # Check if FEYNMAN_GEMINI_API_KEY is configured
    if not hasattr(settings, 'FEYNMAN_GEMINI_API_KEY') or not settings.FEYNMAN_GEMINI_API_KEY:
        print("\n⚠ WARNING: FEYNMAN_GEMINI_API_KEY not configured in settings!")
        print("Tests will use mocked AI responses.")
    
    try:
        # Run validation tests
        await test_chat_missing_message()
        
        # Run chat tests with mocked AI
        await test_chat_with_valid_message()
        await test_chat_with_conversation_history()
        await test_chat_with_analysis_context()
        await test_chat_with_custom_system_prompt()
        await test_chat_with_empty_history()
        
        # Run generator tests
        await test_chat_stream_generator_build_contents()
        
        # Run response tests
        await test_chat_response_headers()
        await test_chat_with_latex_content()
        await test_chat_with_long_message()
        await test_chat_default_system_prompt_content()
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())

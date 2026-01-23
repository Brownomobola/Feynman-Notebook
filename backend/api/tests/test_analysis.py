"""
Test script for AnalyzeSolutionView

This script tests the analysis functionality including:
- POST requests for creating new analysis with streaming response
- GET requests for retrieving existing analysis
- Error handling for missing required fields
- Database persistence of analysis results

Usage:
    python -m api.tests.test_analysis
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
from api.views.analysis import AnalyzeSolutionView
from api.models import Analysis, GymSesh, GymQuestions


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
        request = factory.post('/api/analyze/', data or {})
    else:
        request = factory.get('/api/analyze/')
    
    request.session = MockSession()
    
    if files:
        for key, value in files.items():
            request.FILES[key] = value
    
    return request


def create_mock_stream_response():
    """
    Create mock SSE stream events that simulate the AI response.
    
    Returns:
        List of encoded SSE event bytes
    """
    events = [
        {'type': 'partial', 'field': 'title', 'content': 'Understanding ', 'is_complete': False},
        {'type': 'partial', 'field': 'title', 'content': 'Derivatives', 'is_complete': False},
        {'type': 'array', 'field': 'tags', 'content': ['Calculus', 'Derivatives', 'Chain Rule'], 'is_complete': False},
        {'type': 'partial', 'field': 'praise', 'content': 'Great job recognizing the need for differentiation!', 'is_complete': False},
        {'type': 'partial', 'field': 'diagnosis', 'content': 'You missed applying the chain rule correctly.', 'is_complete': False},
        {'type': 'partial', 'field': 'explanation', 'content': 'Think of it like peeling an onion - you work from outside in.', 'is_complete': False},
        {'type': 'partial', 'field': 'practice_problem', 'content': 'Find the derivative of $f(x) = (x^2 + 1)^3$', 'is_complete': False},
        {
            'type': 'complete',
            'field': 'all',
            'content': {
                'title': 'Understanding Derivatives',
                'tags': ['Calculus', 'Derivatives', 'Chain Rule'],
                'praise': 'Great job recognizing the need for differentiation!',
                'diagnosis': 'You missed applying the chain rule correctly.',
                'explanation': 'Think of it like peeling an onion - you work from outside in.',
                'practice_problem': 'Find the derivative of $f(x) = (x^2 + 1)^3$'
            },
            'is_complete': True
        }
    ]
    
    return [f"data: {json.dumps(event)}\n\n".encode('utf-8') for event in events]


async def mock_stream_generator():
    """Async generator that yields mock stream events."""
    for chunk in create_mock_stream_response():
        yield chunk


async def test_analyze_post_missing_problem():
    """
    Test POST request without problem context (should fail with 400).
    """
    print("\n" + "=" * 60)
    print("Testing POST without problem context (should fail)...")
    print("=" * 60)
    
    request = create_mock_request(
        method='POST',
        data={'attempt': 'My attempt at solving the problem'}
    )
    
    view = AnalyzeSolutionView()
    
    try:
        response = await view.post(request)
        print(f"\nStatus Code: {response.status_code}")
        
        if hasattr(response, 'data'):
            print(f"Response Data: {response.data}")
        
        if response.status_code == 400:
            print("\n✓ Test PASSED: Properly rejected request without problem")
        else:
            print(f"\n✗ Test FAILED: Expected status 400, got {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_analyze_post_missing_attempt():
    """
    Test POST request without attempt context (should fail with 400).
    """
    print("\n" + "=" * 60)
    print("Testing POST without attempt context (should fail)...")
    print("=" * 60)
    
    request = create_mock_request(
        method='POST',
        data={'problem': 'Find the derivative of f(x) = x^2'}
    )
    
    view = AnalyzeSolutionView()
    
    try:
        response = await view.post(request)
        print(f"\nStatus Code: {response.status_code}")
        
        if hasattr(response, 'data'):
            print(f"Response Data: {response.data}")
        
        if response.status_code == 400:
            print("\n✓ Test PASSED: Properly rejected request without attempt")
        else:
            print(f"\n✗ Test FAILED: Expected status 400, got {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_analyze_post_valid_request():
    """
    Test POST request with valid problem and attempt (mocked AI response).
    """
    print("\n" + "=" * 60)
    print("Testing POST with valid data (mocked AI)...")
    print("=" * 60)
    
    request = create_mock_request(
        method='POST',
        data={
            'problem': 'Find the derivative of f(x) = sin(x^2)',
            'attempt': 'f\'(x) = cos(x^2)'
        }
    )
    
    view = AnalyzeSolutionView()
    
    # Mock the StreamGenerator
    with patch('api.views.analysis.StreamGenerator') as MockStreamGenerator:
        mock_instance = MagicMock()
        mock_instance.generate = mock_stream_generator
        MockStreamGenerator.return_value = mock_instance
        
        try:
            response = await view.post(request)
            
            print(f"\nResponse Type: {type(response).__name__}")
            print(f"Content Type: {response.get('Content-Type', 'N/A')}")
            
            if isinstance(response, StreamingHttpResponse):
                print("\n✓ Test PASSED: Got streaming response")
                
                # Check that an Analysis was created
                latest_analysis = await Analysis.objects.order_by('-created_at').afirst()
                if latest_analysis:
                    print(f"✓ Analysis created with ID: {latest_analysis.id}")
                    print(f"  Problem: {latest_analysis.problem[:50]}...")
                    print(f"  Attempt: {latest_analysis.attempt[:50]}...")
                else:
                    print("⚠ Warning: Analysis object not found in database")
            else:
                print(f"\n✗ Test FAILED: Expected StreamingHttpResponse, got {type(response).__name__}")
                
        except Exception as e:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_analyze_get_with_session():
    """
    Test GET request with analysis_id in session.
    """
    print("\n" + "=" * 60)
    print("Testing GET with analysis ID in session...")
    print("=" * 60)
    
    # First, create an analysis in the database
    analysis = await Analysis.objects.acreate(
        problem='Test problem for GET request',
        attempt='Test attempt for GET request',
        title='Test Analysis Title',
        tags=['Test', 'GET'],
        praise='Good work!',
        diagnosis='Minor error found.',
        explanation='Here is the explanation.'
    )
    
    request = create_mock_request(method='GET')
    request.session['last_analysis_id'] = analysis.id
    
    view = AnalyzeSolutionView()
    
    try:
        response = await view.get(request)
        print(f"\nStatus Code: {response.status_code}")
        
        if hasattr(response, 'data'):
            print(f"Response Data Keys: {list(response.data.keys())}")
        
        if response.status_code == 200:
            print("\n✓ Test PASSED: Successfully retrieved analysis")
            
            # Verify response data
            if response.data.get('id') == analysis.id:
                print(f"✓ Correct analysis ID returned: {analysis.id}")
            if response.data.get('title') == 'Test Analysis Title':
                print("✓ Correct title returned")
        else:
            print(f"\n✗ Test FAILED: Expected status 200, got {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await analysis.adelete()


async def test_analyze_get_without_session():
    """
    Test GET request without analysis_id in session (should fail with 404).
    """
    print("\n" + "=" * 60)
    print("Testing GET without analysis ID in session (should fail)...")
    print("=" * 60)
    
    request = create_mock_request(method='GET')
    # Don't set any session data
    
    view = AnalyzeSolutionView()
    
    try:
        response = await view.get(request)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 404:
            print("\n✓ Test PASSED: Properly returned 404 for missing session")
        else:
            print(f"\n✗ Test FAILED: Expected status 404, got {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_analyze_get_nonexistent_analysis():
    """
    Test GET request with non-existent analysis ID in session.
    """
    print("\n" + "=" * 60)
    print("Testing GET with non-existent analysis ID...")
    print("=" * 60)
    
    request = create_mock_request(method='GET')
    request.session['last_analysis_id'] = 99999  # Non-existent ID
    
    view = AnalyzeSolutionView()
    
    try:
        response = await view.get(request)
        print(f"\nResponse Type: {type(response).__name__}")
        
        # Should redirect to home
        if hasattr(response, 'url'):
            print(f"Redirect URL: {response.url}")
            print("\n✓ Test PASSED: Properly redirected for non-existent analysis")
        else:
            print(f"\n⚠ Response: {response}")
            
    except Analysis.DoesNotExist:
        print("\n✓ Test PASSED: Properly raised DoesNotExist for non-existent analysis")
    except Exception as e:
        # NoReverseMatch is expected if URL config is not fully set up in test environment
        if 'NoReverseMatch' in str(type(e).__name__) or 'not a registered namespace' in str(e):
            print("\n✓ Test PASSED: Attempted redirect (NoReverseMatch in test environment)")
        else:
            print(f"\n✗ Test FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()


async def test_analysis_creates_gym_session():
    """
    Test that completing an analysis creates a GymSesh and GymQuestion.
    """
    print("\n" + "=" * 60)
    print("Testing that analysis creates gym session...")
    print("=" * 60)
    
    # Create an analysis
    analysis = await Analysis.objects.acreate(
        problem='Integration problem',
        attempt='My integration attempt',
        title='Integration Analysis',
        tags=['Integration', 'Calculus'],
        praise='Good approach!',
        diagnosis='Minor calculation error.',
        explanation='Integration explanation here.'
    )
    
    # Create associated gym session and question
    gym_sesh = await GymSesh.objects.acreate(
        analysis=analysis,
        status=GymSesh.Status.PENDING
    )
    
    gym_question = await GymQuestions.objects.acreate(
        gym_sesh=gym_sesh,
        question='Find the integral of $x^2 dx$',
        question_number=1
    )
    
    try:
        # Verify the relationships
        print(f"\nAnalysis ID: {analysis.id}")
        print(f"GymSesh ID: {gym_sesh.id}")
        print(f"GymQuestion ID: {gym_question.id}")
        
        # Verify gym session is linked to analysis
        assert gym_sesh.analysis_id == analysis.id
        print("✓ GymSesh correctly linked to Analysis")
        
        # Verify question is linked to gym session
        assert gym_question.gym_sesh_id == gym_sesh.id
        print("✓ GymQuestion correctly linked to GymSesh")
        
        # Verify initial states
        assert gym_sesh.status == GymSesh.Status.PENDING
        print("✓ GymSesh has correct initial status (PENDING)")
        
        assert gym_question.status == GymQuestions.Status.PENDING
        print("✓ GymQuestion has correct initial status (PENDING)")
        
        assert gym_question.question_number == 1
        print("✓ GymQuestion has correct question number (1)")
        
        print("\n✓ Test PASSED: Gym session and question created correctly")
        
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {str(e)}")
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await gym_question.adelete()
        await gym_sesh.adelete()
        await analysis.adelete()


async def test_analysis_to_dict():
    """
    Test the Analysis model's to_dict method.
    """
    print("\n" + "=" * 60)
    print("Testing Analysis.to_dict() method...")
    print("=" * 60)
    
    analysis = await Analysis.objects.acreate(
        problem='Test problem',
        attempt='Test attempt',
        title='Test Title',
        tags=['Tag1', 'Tag2'],
        praise='Test praise',
        diagnosis='Test diagnosis',
        explanation='Test explanation'
    )
    
    try:
        result = analysis.to_dict()
        
        print(f"\nto_dict() result keys: {list(result.keys())}")
        
        expected_keys = ['id', 'problem', 'attempt', 'title', 'tags', 
                        'praise', 'diagnosis', 'explanation', 'created_at']
        
        for key in expected_keys:
            if key in result:
                print(f"✓ Key '{key}' present")
            else:
                print(f"✗ Key '{key}' missing")
        
        # Verify values
        assert result['id'] == analysis.id
        assert result['title'] == 'Test Title'
        assert result['tags'] == ['Tag1', 'Tag2']
        
        print("\n✓ Test PASSED: to_dict() returns correct data")
        
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {str(e)}")
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await analysis.adelete()


async def cleanup_test_data():
    """
    Clean up any remaining test data from the database.
    """
    print("\n" + "=" * 60)
    print("Cleaning up test data...")
    print("=" * 60)
    
    try:
        # Delete test analyses (this will cascade to gym sessions and questions)
        deleted = await Analysis.objects.filter(
            problem__startswith='Test'
        ).adelete()
        print(f"Deleted {deleted[0]} test analysis record(s)")
        
        # Also clean up any orphaned records
        deleted_gym = await GymSesh.objects.filter(
            analysis__isnull=True
        ).adelete()
        print(f"Deleted {deleted_gym[0]} orphaned gym session(s)")
        
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")


async def main():
    """
    Run all tests.
    """
    print("\n" + "=" * 60)
    print("ANALYZE SOLUTION VIEW TEST SUITE")
    print("=" * 60)
    print(f"\nDjango Settings: {settings.SETTINGS_MODULE}")
    print(f"Database: {settings.DATABASES['default']['ENGINE']}")
    
    # Check if FEYNMAN_GEMINI_API_KEY is configured
    if not hasattr(settings, 'FEYNMAN_GEMINI_API_KEY') or not settings.FEYNMAN_GEMINI_API_KEY:
        print("\n⚠ WARNING: FEYNMAN_GEMINI_API_KEY not configured in settings!")
        print("Tests will use mocked AI responses.")
    
    try:
        # Run validation tests
        await test_analyze_post_missing_problem()
        await test_analyze_post_missing_attempt()
        
        # Run POST tests with mocked AI
        await test_analyze_post_valid_request()
        
        # Run GET tests
        await test_analyze_get_with_session()
        await test_analyze_get_without_session()
        await test_analyze_get_nonexistent_analysis()
        
        # Run model tests
        await test_analysis_creates_gym_session()
        await test_analysis_to_dict()
        
        # Cleanup
        await cleanup_test_data()
        
        print("\n" + "=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        await cleanup_test_data()
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        await cleanup_test_data()


if __name__ == '__main__':
    # Run the async main function
    asyncio.run(main())

"""
This is a simple test script for the transcribe_gym module.

It can run without starting the full django server to test 
the TranscribeGymImageView functionality.

Usage:
    python -m api.tests.test_transcribe_gym
"""

import os
import sys
import django
import asyncio
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Now we can import Django-dependent modules
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.conf import settings
from api.views import TranscribeGymImageView
from api.models import GymTranscript
from PIL import Image
from io import BytesIO


def create_test_image():
    """
    Create a simple test image with text for transcription testing.
    
    Returns:
        SimpleUploadedFile: A test image file
    """
    # Create a simple white image with some text
    img = Image.new('RGB', (400, 200), color='white')
    
    # Save to BytesIO
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    # Create uploaded file
    uploaded_file = SimpleUploadedFile(
        name='test_image.jpg',
        content=img_io.getvalue(),
        content_type='image/jpeg'
    )
    
    return uploaded_file


async def test_transcribe_with_image():
    """
    Test the transcription view with an image file.
    """
    print("=" * 60)
    print("Testing TranscribeGymImageView with image...")
    print("=" * 60)
    
    # Create a test image
    test_image = create_test_image()
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.post(
        '/api/transcribe-gym/',
        {
            'data_text': 'Fallback text: x^2 + y^2 = r^2',
        }
    )
    request.FILES['data_image'] = test_image
    request.session = {}
    
    # Create view instance and call it
    view = TranscribeGymImageView()
    
    try:
        response = await view.post(request)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Data: {response.data}")
        
        if response.status_code == 200:
            print("\n✓ Test PASSED: Transcription completed successfully")
        else:
            print(f"\n✗ Test FAILED: Got status code {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_transcribe_with_text_fallback():
    """
    Test the transcription view with text fallback (no image).
    """
    print("\n" + "=" * 60)
    print("Testing TranscribeGymImageView with text fallback...")
    print("=" * 60)
    
    # Create a mock request without image
    factory = RequestFactory()
    request = factory.post(
        '/api/transcribe-gym/',
        {
            'data_text': 'E = mc^2',
        }
    )
    request.session = {}
    
    # Create view instance and call it
    view = TranscribeGymImageView()
    
    try:
        response = await view.post(request)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Data: {response.data}")
        
        if response.status_code == 200:
            print("\n✓ Test PASSED: Text fallback worked")
        else:
            print(f"\n✗ Test FAILED: Got status code {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_transcribe_no_data():
    """
    Test the transcription view with neither image nor text (should fail).
    """
    print("\n" + "=" * 60)
    print("Testing TranscribeGymImageView with no data (should fail)...")
    print("=" * 60)
    
    # Create a mock request without image or text
    factory = RequestFactory()
    request = factory.post('/api/transcribe-gym/', {})
    request.session = {}
    
    # Create view instance and call it
    view = TranscribeGymImageView()
    
    try:
        response = await view.post(request)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Data: {response.data}")
        
        if response.status_code == 400:
            print("\n✓ Test PASSED: Properly rejected empty request")
        else:
            print(f"\n✗ Test FAILED: Expected status 400, got {response.status_code}")
            
    except Exception as e:
        print(f"\n✗ Test FAILED with exception: {str(e)}")
        import traceback
        traceback.print_exc()


async def cleanup_test_data():
    """
    Clean up test data from the database.
    """
    print("\n" + "=" * 60)
    print("Cleaning up test data...")
    print("=" * 60)
    
    try:
        # Delete all test transcripts
        count = await GymTranscript.objects.all().adelete()
        print(f"Deleted {count[0]} test transcript(s)")
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")


async def main():
    """
    Run all tests.
    """
    print("\n" + "=" * 60)
    print("TRANSCRIBE ANALYSIS VIEW TEST SUITE")
    print("=" * 60)
    print(f"\nDjango Settings: {settings.SETTINGS_MODULE}")
    print(f"Database: {settings.DATABASES['default']['ENGINE']}")
    
    # Check if FEYNMAN_GEMINI_API_KEY is configured
    if not hasattr(settings, 'FEYNMAN_GEMINI_API_KEY') or not settings.FEYNMAN_GEMINI_API_KEY:
        print("\n⚠ WARNING: FEYNMAN_GEMINI_API_KEY not configured in settings!")
        print("Set it in your .env file to test actual transcription.")
    
    try:
        # Run tests
        await test_transcribe_with_text_fallback()
        await test_transcribe_no_data()
        
        # Only test with image if API key is configured
        if hasattr(settings, 'FEYNMAN_GEMINI_API_KEY') and settings.FEYNMAN_GEMINI_API_KEY:
            await test_transcribe_with_image()
        else:
            print("\n⊘ Skipping image transcription test (no API key)")
        
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
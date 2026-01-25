"""
Shared Gemini AI client instance to avoid creating multiple clients.
This helps with connection pooling and rate limiting.
"""
from google import genai
from django.conf import settings

# ____EAGER INSTANTION____
# This runs once when the server starts
# It creates a single shared Gemini AI client instance
FEYNMAN_GEMINI_API_KEY = settings.FEYNMAN_GEMINI_API_KEY

_client_instance = genai.Client(api_key=FEYNMAN_GEMINI_API_KEY)

def get_gemini_client() -> genai.Client:
    """
    Returns the shared Gemini AI client instance.
    
    Returns:
        genai.Client: Shared Gemini AI client
    """
    return _client_instance

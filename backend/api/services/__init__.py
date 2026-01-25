"""
Services package for the Feynman Notebook application

This package contains logic and utilities services:
- ChatStreamGenerator: Streams conversational AI response
- StreamGenerator: Streams Analysis and Gym response in SSE format
- ImageTranscriber: Transcribe handwritten math solution to LaTex/Markdown
"""

from .streaming import ChatStreamGenerator, StreamGenerator
from .transcription import ImageTranscriber
from .gemini_client import get_gemini_client

__all__ = [
    'ChatStreamGenerator',
    'ImageTranscriber',
    'StreamGenerator',
    'get_gemini_client'
]
"""
API views for the Feynman Notebook application

This package contains all the views:
- AnalyzeSolutionView: Analyzes the student math solution
- ChatView: Provides a conversational-like tutoring experience
- GymSolutionView: Provides similar questions for extra practice
"""

from .analysis import AnalyzeSolutionView
from .chat import ChatView
from .gym import GymSolutionView

__all__ = [
    'AnalyzeSolutionView',
    'ChatView',
    'GymSolutionView'
]
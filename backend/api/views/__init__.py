"""
API views for the Feynman Notebook application

This package contains all the views:
- AnalyzeSolutionView: Analyzes the student math solution
- ChatView: Provides a conversational-like tutoring experience
- GymSolutionView: Provides similar questions for extra practice
- Auth views: User registration, login, logout, and session management
"""

from .analysis import AnalyzeSolutionView
from .chat import ChatView
from .gym import GymSolutionView
from .transcribe_analysis import TranscribeAnalysisImageView
from .transcribe_gym import TranscribeGymImageView
from .auth import (
    CSRFTokenView,
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    get_user_session_info,
    filter_by_owner
)

__all__ = [
    'AnalyzeSolutionView',
    'ChatView',
    'GymSolutionView',
    'TranscribeAnalysisImageView',
    'TranscribeGymImageView',
    'CSRFTokenView',
    'RegisterView',
    'LoginView',
    'LogoutView',
    'MeView',
    'get_user_session_info',
    'filter_by_owner'
]
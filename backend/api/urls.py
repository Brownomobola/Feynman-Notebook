from django.urls import path
from .views import (
    AnalyzeSolutionView,
    ChatView,
    GymSolutionView,
    TranscribeAnalysisImageView,
    TranscribeGymImageView,
    CSRFTokenView,
    RegisterView,
    LoginView,
    LogoutView,
    MeView
)

urlpatterns = [
    # Auth endpoints
    path('auth/csrf/', CSRFTokenView.as_view(), name='csrf_token'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    
    # Analysis endpoints
    path('analysis/', AnalyzeSolutionView.as_view(), name='analyze'),
    path('analysis/transcribe/', TranscribeAnalysisImageView.as_view(), name='transcribe_analysis'),
    
    # Chat endpoint
    path('chat/', ChatView.as_view(), name='chat'),
    
    # Gym endpoints
    path('gym/transcribe/', TranscribeGymImageView.as_view(), name='transcribe_gym'),
    path('gym/submit/', GymSolutionView.as_view(), name='gym_submit'),
]
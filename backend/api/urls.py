from django.urls import path
from .views import AnalyzeSolutionView, ChatView, GymSolutionView, TranscribeAnalysisImageView, TranscribeGymImageView

urlpatterns = [
    path('analysis/', AnalyzeSolutionView.as_view(), name='analyze'),
    path('analysis/transcribe/', TranscribeAnalysisImageView.as_view(), name='transcribe_analysis'),
    path('gym/transcribe/', TranscribeGymImageView.as_view(), name='transcribe_gym'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('gym/submit/', GymSolutionView.as_view(), name='gym_submit'),
]
from django.urls import path
from .views import AnalyzeSolutionView, ChatView, GymSolutionView  

urlpatterns = [
    path('analyze/', AnalyzeSolutionView.as_view(), name='analyze'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('gym/submit/', GymSolutionView.as_view(), name='gym_submit'),
]
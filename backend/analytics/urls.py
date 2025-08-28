from django.urls import path
from .views import VideoUploadView, YouTubeAnalysisView, RegisterVideoView, VideoDetailView, VideoListView # Add YouTubeAnalysisView

urlpatterns = [
    path('videos/', VideoListView.as_view(), name='video-list'),
    path('upload/', VideoUploadView.as_view(), name='video-upload'),
    path('analyze-youtube/', YouTubeAnalysisView.as_view(), name='youtube-analyze'), # Add this line
    path('register-video/', RegisterVideoView.as_view(), name='video-register'),
    path('video/<str:video_id>/', VideoDetailView.as_view(), name='video-detail'),
]
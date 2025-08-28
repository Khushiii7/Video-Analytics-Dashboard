# --- Imports for BOTH views ---
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Video
from .serializers import VideoSerializer
import ffmpeg
import uuid
import os
from googleapiclient.discovery import build
from django.conf import settings
import uuid
from rest_framework.generics import RetrieveAPIView, ListAPIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Helper function to extract a thumbnail from a video file
def extract_thumbnail(video_path, thumbnail_path, time_offset=1):
    try:
        (
            ffmpeg
            .input(video_path, ss=time_offset)
            .output(thumbnail_path, vframes=1)
            .overwrite_output()
            .run(quiet=True)
        )
        return True
    except Exception as e:
        print(f"Failed to extract thumbnail: {e}")
        return False

# --- View 1: For User Uploads (Your original code) ---
class VideoUploadView(APIView):
    def post(self, request):
        file = request.FILES['video']
        file_extension = os.path.splitext(file.name)[1]
        if not file_extension: file_extension = ".mp4" # default to mp4
        # We'll use the file name as a unique identifier for path check
        save_path = os.path.join('media', 'videos', f"{file.name}")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Check for existing video with the same path
        existing_video = Video.objects.filter(path=save_path, source='upload').first()
        if existing_video:
            video_url = request.build_absolute_uri(settings.MEDIA_URL + 'videos/' + f"{file.name}")
            return Response({
                "video_id": existing_video.video_id,
                "video_url": video_url,
                "thumbnail": existing_video.thumbnail
            })

        vid = str(uuid.uuid4())
        save_path = os.path.join('media', 'videos', f"{vid}{file_extension}")
        with open(save_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        meta = ffmpeg.probe(save_path)
        duration = float(meta['format']['duration'])
        thumbnail_dir = os.path.join('media', 'thumbnails')
        os.makedirs(thumbnail_dir, exist_ok=True)
        thumbnail_path = os.path.join(thumbnail_dir, f"{vid}.jpg")
        thumbnail_url = None
        if extract_thumbnail(save_path, thumbnail_path):
            thumbnail_url = request.build_absolute_uri(settings.MEDIA_URL + f"thumbnails/{vid}.jpg")
        video = Video.objects.create(
            video_id=vid,
            path=save_path,
            duration=duration,
            source='upload',
            thumbnail=thumbnail_url
        )
        video_url = request.build_absolute_uri(settings.MEDIA_URL + 'videos/' + f"{vid}{file_extension}")
        return Response({
            "video_id": vid,
            "video_url": video_url,
            "thumbnail": thumbnail_url
        })


# --- View 2: For YouTube Analysis (The new code) ---
class YouTubeAnalysisView(APIView):
    def post(self, request):
        youtube_video_id = request.data.get('video_id')
        if not youtube_video_id:
            return Response({"error": "video_id is required"}, status=400)

        # IMPORTANT: Replace with your actual YouTube Data API Key
        # For security, load this from an environment variable in a real application
        YOUTUBE_API_KEY = 'API-KEY' 

        try:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            video_response = youtube.videos().list(
                part='snippet,statistics',
                id=youtube_video_id
            ).execute()

            if not video_response['items']:
                return Response({"error": "YouTube video not found"}, status=404)

            video_data = video_response['items'][0]
            snippet = video_data['snippet']
            stats = video_data['statistics']

            # YouTube thumbnail URL
            youtube_thumbnail_url = f"https://img.youtube.com/vi/{youtube_video_id}/hqdefault.jpg"

            # Create or update the video record in the database
            video, created = Video.objects.update_or_create(
                video_id=youtube_video_id,
                defaults={
                    'source': 'youtube',
                    'title': snippet['title'],
                    'view_count': stats.get('viewCount', 0),
                    'like_count': stats.get('likeCount', 0),
                    'comment_count': stats.get('commentCount', 0),
                    'thumbnail': youtube_thumbnail_url
                }
            )
            
            serializer = VideoSerializer(video)
            return Response(serializer.data)

        except Exception as e:
            # It's good practice to log the error here
            print(f"An error occurred: {e}")
            return Response({"error": "An internal error occurred. See server logs for details."}, status=500)

class RegisterVideoView(APIView):
    def post(self, request):
        video_url = request.data.get('video_url')
        if not video_url:
            return Response({"error": "video_url is required"}, status=400)
        # Check for existing video with the same path (direct link)
        existing_video = Video.objects.filter(path=video_url, source='direct').first()
        if existing_video:
            return Response({
                "video_id": existing_video.video_id,
                "video_url": existing_video.path,
                "thumbnail": existing_video.thumbnail
            })
        try:
            vid = str(uuid.uuid4())
            thumbnail_dir = os.path.join('media', 'thumbnails')
            os.makedirs(thumbnail_dir, exist_ok=True)
            thumbnail_path = os.path.join(thumbnail_dir, f"{vid}.jpg")
            thumbnail_url = None
            try:
                if extract_thumbnail(video_url, thumbnail_path):
                    thumbnail_url = request.build_absolute_uri(settings.MEDIA_URL + f"thumbnails/{vid}.jpg")
            except Exception as e:
                print(f"Failed to extract thumbnail from direct link: {e}")
            video = Video.objects.create(
                video_id=vid,
                source='direct',
                path=video_url,
                title=video_url.split('/')[-1],
                thumbnail=thumbnail_url
            )
            return Response({"video_id": video.video_id, "video_url": video.path, "thumbnail": thumbnail_url})
        except Exception as e:
            print(f"Error registering video: {e}")
            return Response({"error": "Failed to register video."}, status=500)

class VideoListView(ListAPIView):
    """
    Provides a list of all videos in the database.
    """
    queryset = Video.objects.all().order_by('-pk') # Order by most recent
    serializer_class = VideoSerializer
    
class VideoDetailView(RetrieveAPIView):
    """
    Provides all stored data for a single video.
    """
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    lookup_field = 'video_id' # Tells the view to find videos by their video_id

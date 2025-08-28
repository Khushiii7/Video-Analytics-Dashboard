from django.db import models

class Video(models.Model):
    # Existing fields for all video types
    video_id = models.CharField(max_length=100, primary_key=True)
    source = models.CharField(max_length=10, default='upload') # 'upload', 'youtube', etc.
    
    # Fields for uploaded videos
    path = models.TextField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    
    # Thumbnail for the video (local path or URL)
    thumbnail = models.TextField(null=True, blank=True)

    # New fields for YouTube videos
    title = models.CharField(max_length=255, null=True, blank=True)
    view_count = models.PositiveIntegerField(null=True, blank=True)
    like_count = models.PositiveIntegerField(null=True, blank=True)
    comment_count = models.PositiveIntegerField(null=True, blank=True)

    total_watch_time = models.FloatField(default=0.0)
    engagement_data = models.JSONField(default=dict)
    play_count = models.PositiveIntegerField(default=0)  # Number of times the video was played
    engagement_event_count = models.PositiveIntegerField(default=0)  # Number of engagement events (play, pause, etc.)

    def __str__(self):
        return self.title or self.video_id
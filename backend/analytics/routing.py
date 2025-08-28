from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # This pattern correctly captures UUIDs with hyphens
    re_path(r'ws/engage/(?P<video_id>[\w-]+)/$', consumers.EngagementConsumer.as_asgi()),
]
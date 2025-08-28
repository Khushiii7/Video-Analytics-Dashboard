import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Video
from .ml_model import predict_revenue # Import our new ML model
import math

class EngagementConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.video_id = self.scope['url_route']['kwargs']['video_id']
        self.video_group_name = f'video_{self.video_id}'

        await self.channel_layer.group_add(
            self.video_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"WebSocket connected for video: {self.video_id}")

        # Increment play_count when a new connection is made
        await self.increment_play_count()

        # Start a background task to periodically send updates
        self.updater_task = asyncio.create_task(self.send_live_updates())

    async def disconnect(self, close_code):
        # Stop the background task when the user disconnects
        self.updater_task.cancel()
        await self.channel_layer.group_discard(
            self.video_group_name,
            self.channel_name
        )
        print(f"WebSocket disconnected for video: {self.video_id}")

    async def receive(self, text_data):
        event = json.loads(text_data)
        event_type = event.get("event")

        if event_type == "timeupdate":
            current_time = event.get("currentTime", 0)
            # Add this line to get duration from the event
            duration = event.get("duration", 0)
            # Pass duration to the update function
            await self.update_engagement_data(current_time, duration)
            
    # --- New Methods for Broadcasting ---

    async def send_live_updates(self):
        """Periodically fetches data and sends it to the group."""
        while True:
            await asyncio.sleep(2) # Send updates every 2 seconds
            
            # Get the latest data from the database
            video_data = await self.get_video_data()
            
            # Get an ML prediction
            prediction = predict_revenue({
                'total_watch_time': video_data.get('total_watch_time', 0),
                'heatmap': video_data.get('engagement_data', {}).get('heatmap', {})
            })

            payload = {
                'type': 'live_update', # This is a custom event type for our handler
                'total_watch_time': round(video_data.get('total_watch_time', 0), 2),
                'predicted_revenue': prediction,
                # In a real app, you could add more (e.g., live viewer count)
            }
            
            # Send the payload to the entire group
            await self.channel_layer.group_send(
                self.video_group_name,
                {
                    'type': 'broadcast_stats',
                    'payload': payload
                }
            )

    async def broadcast_stats(self, event):
        """Handler for the group_send call. Sends a message to the WebSocket."""
        await self.send(text_data=json.dumps(event['payload']))
        
    # --- Database Methods ---

    @database_sync_to_async
    def get_video_data(self):
        """Fetches the latest video data from the DB."""
        try:
            video = Video.objects.get(video_id=self.video_id)
            return {
                'total_watch_time': video.total_watch_time,
                'engagement_data': video.engagement_data
            }
        except Video.DoesNotExist:
            return None

    @database_sync_to_async
    def increment_play_count(self):
        try:
            video, _ = Video.objects.get_or_create(video_id=self.video_id)
            video.play_count = (video.play_count or 0) + 1
            video.save()
        except Exception as e:
            print(f"Error incrementing play count: {e}")

    @database_sync_to_async
    def update_engagement_data(self, current_time, duration): # Add duration to the signature
        """Updates watch time and the engagement heatmap in the DB."""
        try:
            # Use get_or_create to handle new videos gracefully
            video, created = Video.objects.get_or_create(video_id=self.video_id)
            
            # --- NEW: Update duration if it's not set and is valid ---
            if video.duration is None and duration > 0:
                video.duration = duration

            # Increment watch time (assuming 1-second interval updates)
            video.total_watch_time = (video.total_watch_time or 0) + 1

            # Increment engagement event count
            video.engagement_event_count = (video.engagement_event_count or 0) + 1

            # Update heatmap
            time_key = str(math.floor(current_time))
            heatmap = video.engagement_data.get('heatmap', {})
            heatmap[time_key] = heatmap.get(time_key, 0) + 1
            video.engagement_data['heatmap'] = heatmap
            
            video.save()

        except Exception as e:
            print(f"Error updating engagement data: {e}")
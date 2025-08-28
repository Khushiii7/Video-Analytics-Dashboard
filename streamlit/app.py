import streamlit as st
import requests
import re
import pandas as pd
import streamlit.components.v1 as components

# --- Configuration ---
BACKEND_API_URL = "http://localhost:8000/api"
BACKEND_WS_URL = "ws://localhost:8000/ws"

# --- Page Navigation State ---
# This is a cleaner way to manage which page is currently viewed.
if 'page' not in st.session_state:
    st.session_state.page = 'gallery'
if 'selected_video_id' not in st.session_state:
    st.session_state.selected_video_id = None

# --- Helper Functions ---
def get_youtube_id(url):
    """Extracts video ID from a YouTube URL."""
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    if 'youtube.com' in url:
        match = re.search(r'v=([\w-]+)', url)
        if match:
            return match.group(1)
    return None

def navigate_to(page, video_id=None):
    """Callback to change the page in session state. Streamlit reruns automatically."""
    st.session_state.page = page
    st.session_state.selected_video_id = video_id

# --- Data Calculation Functions (from your code) ---
def average_watch_duration(total_watch_time, play_count):
    return total_watch_time / play_count if play_count else 0

def retention_rate(avg_watch_duration, duration):
    return (avg_watch_duration / duration) * 100 if duration else 0

def engagement_rate(engagement_event_count, play_count):
    return engagement_event_count / play_count if play_count else 0

# --- Page Rendering Functions ---

def render_gallery_page():
    """Renders the main gallery page with a list of all videos."""
    st.header("🎬 Video Gallery & History")

    # --- Fetch and Display Videos ---
    try:
        res = requests.get(f"{BACKEND_API_URL}/videos/")
        res.raise_for_status()
        videos = res.json()

        if not videos:
            st.info("No videos analyzed yet. Add one using the sidebar!")
            return

        st.subheader("📊 Video Performance Comparison")
        comp_data = [
            {
                'Title': v.get('title', v.get('video_id')),
                'Source': v.get('source', 'N/A').capitalize(),
                'Plays': v.get('play_count', 0),
                'Avg. Duration (s)': round(average_watch_duration(v.get('total_watch_time', 0), v.get('play_count', 0)), 2),
                'Retention (%)': round(retention_rate(average_watch_duration(v.get('total_watch_time', 0), v.get('play_count', 0)), v.get('duration', 0)), 1),
                'Interactions/Play': round(engagement_rate(v.get('engagement_event_count', 0), v.get('play_count', 0)), 2),
            } for v in videos
        ]
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True)
        st.divider()

        for video in videos:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(video.get("thumbnail") or "https://via.placeholder.com/200x112?text=No+Thumbnail", width=200)
            with col2:
                st.subheader(video.get('title') or video.get('video_id'))
                st.caption(f"Source: {video.get('source', 'N/A').capitalize()} | ID: {video.get('video_id')}")
                st.button("View Full Analysis", key=video['video_id'], on_click=navigate_to, args=('detail', video['video_id']))
            st.divider()

    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")


def render_detail_page():
    """Renders the detailed analysis page for a single selected video."""
    video_id = st.session_state.selected_video_id
    st.button("← Back to Gallery", on_click=navigate_to, args=('gallery',))

    try:
        info = None
        res = requests.get(f"{BACKEND_API_URL}/video/{video_id}/")

        if res.status_code == 200:
            info = res.json()
        elif res.status_code == 404:
            with st.spinner("Video not found in database, analyzing with YouTube..."):
                yt_res = requests.post(f"{BACKEND_API_URL}/analyze-youtube/", json={"video_id": video_id})
                yt_res.raise_for_status()
                info = yt_res.json()
        else:
            res.raise_for_status()

        if not info:
            st.error(f"Could not retrieve or create data for video {video_id}.")
            return

    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while communicating with the backend: {e}")
        return

    st.header(info.get('title') or info.get('video_id'))
    source = info.get("source")

    if source == "youtube":
        youtube_player_component(video_id)
        st.subheader("YouTube Stats")
        col1, col2, col3 = st.columns(3)
        col1.metric("Views", f"{int(info.get('view_count', 0)):,}")
        col2.metric("Likes", f"{int(info.get('like_count', 0)):,}")
        col3.metric("Comments", f"{int(info.get('comment_count', 0)):,}")
    else:
        # CORRECTED: Properly construct the URL for uploaded videos
        video_url = info.get("path") if source == 'direct' else f"http://localhost:8000/{info.get('path')}"
        video_player_component(video_url, video_id)
        
        st.divider()
        st.subheader("📈 Historical Engagement Dashboard")
        heatmap_data = info.get('engagement_data', {}).get('heatmap', {})
        if not heatmap_data:
            st.info("No engagement data yet. Play the video to generate data.")
        else:
            play_count = info.get('play_count', 0)
            avg_watch = average_watch_duration(info.get('total_watch_time', 0), play_count)
            retention = retention_rate(avg_watch, info.get('duration', 0))
            engage_rate = engagement_rate(info.get('engagement_event_count', 0), play_count)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Avg. Watch Duration", f"{int(avg_watch)}s")
            col2.metric("Retention Rate", f"{int(retention)}%")
            col3.metric("Total Plays", play_count)
            col4.metric("Interactions / Play", f"{engage_rate:.2f}")

            df = pd.DataFrame(heatmap_data.items(), columns=['Second', 'Views'])
            df['Second'] = pd.to_numeric(df['Second'])
            df = df.sort_values(by='Second').set_index('Second')
            st.area_chart(df['Views'], use_container_width=True)


# --- Reusable HTML/JS Components ---
def video_player_component(video_url, video_id):
    websocket_url = f"{BACKEND_WS_URL}/engage/{video_id}/"
    component_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Player</title>
        <style>
            body {{ margin: 0; background-color: #000; font-family: sans-serif; }}
            .container {{ display: flex; flex-direction: column; gap: 16px; }}
            .video-wrapper {{ width: 100%; background-color: #000; border-radius: 8px; overflow: hidden; }}
            video {{ width: 100%; height: auto; display: block; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px; }}
            .stat-card {{ background-color: black; padding: 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(255,255,255,0);border: 1px solid #ffffff;}}
            .stat-card h3 {{ margin: 0 0 8px 0; font-size: 16px; color: #fafafa; }}
            .stat-card p {{ margin: 0; font-size: 28px; font-weight: 600; color: #ffffff; }}
            .status {{ font-size: 14px; text-align: center; padding: 8px; border-radius: 8px; color: #fff; }}
            .connected {{ background-color: #1c3b23; color: #d4edda; }}
            .disconnected {{ background-color: #4a2125; color: #f8d7da; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div id="status" class="status">Connecting...</div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Watch Time</h3>
                    <p id="watch-time">0s</p>
                </div>
                <div class="stat-card">
                    <h3>Predicted Revenue</h3>
                    <p id="revenue">$0.00</p>
                </div>
            </div>

            <div class="video-wrapper"><video id="videoPlayer" controls autoplay><source src="{video_url}" type="video/mp4"></video></div>
        </div>
        <script>
            const video = document.getElementById('videoPlayer');
            const statusDiv = document.getElementById('status');
            const watchTimeEl = document.getElementById('watch-time');
            const revenueEl = document.getElementById('revenue');
            const websocketUrl = "{websocket_url}";
            let ws;

            function connect() {{
                ws = new WebSocket(websocketUrl);
                ws.onopen = () => {{ statusDiv.textContent = "🟢 Real-Time Connection Active"; statusDiv.className = "status connected"; }};
                
                ws.onmessage = (event) => {{
                    const data = JSON.parse(event.data);
                    if (data.type === 'live_update') {{
                        watchTimeEl.textContent = data.total_watch_time + 's';
                        revenueEl.textContent = '$' + data.predicted_revenue.toFixed(2);
                    }}
                }};

                ws.onclose = () => {{ statusDiv.textContent = "🔴 Disconnected. Retrying..."; statusDiv.className = "status disconnected"; setTimeout(connect, 3000); }};
                ws.onerror = (error) => {{ console.error("WebSocket Error:", error); ws.close(); }};
            }}

            function sendEvent(eventType) {{
                if (ws && ws.readyState === WebSocket.OPEN) {{
                    const eventData = {{ "event": eventType, "currentTime": video.currentTime, "duration": video.duration }};
                    ws.send(JSON.stringify(eventData));
                    console.log("Sent event:", eventType);
                }}
            }}

            let lastUpdateTime = 0;
            video.addEventListener('timeupdate', () => {{
                if (new Date().getTime() - lastUpdateTime < 1000) return;
                lastUpdateTime = new Date().getTime();
                sendEvent('timeupdate');
            }});
            
            video.addEventListener('play', () => sendEvent('play'));
            video.addEventListener('pause', () => sendEvent('pause'));
            video.addEventListener('seeked', () => sendEvent('seeked'));

            connect();
        </script>
    </body>
    </html>
    """
    components.html(component_html, height=750)

def youtube_player_component(youtube_id):
    websocket_url = f"{BACKEND_WS_URL}/engage/{youtube_id}/"
    component_html = f'''
    <div id="player"></div>
    <script src="https://www.youtube.com/iframe_api"></script>
    <script>
      var player;
      var ws;
      
      function connectWebSocket() {{
          ws = new WebSocket('{websocket_url}');
          ws.onopen = () => console.log("YouTube WS Connected");
          ws.onclose = () => setTimeout(connectWebSocket, 3000);
          ws.onerror = (err) => console.error("YouTube WS Error:", err);
      }}

      function sendYouTubeEvent(eventType) {{
        if (ws && ws.readyState === WebSocket.OPEN) {{
          const eventData = {{
            "event": eventType,
            "currentTime": player.getCurrentTime(),
            "duration": player.getDuration()
          }};
          ws.send(JSON.stringify(eventData));
          console.log("Sent YouTube Event:", eventType);
        }}
      }}

      function onYouTubeIframeAPIReady() {{
        player = new YT.Player('player', {{
          height: '390',
          width: '100%',
          videoId: '{youtube_id}',
          events: {{ 'onReady': onPlayerReady, 'onStateChange': onPlayerStateChange }}
        }});
      }}

      function onPlayerReady(event) {{
        connectWebSocket();
        // Send a 'play' event when the video starts ready
        sendYouTubeEvent('play'); 
        setInterval(() => {{
            // Send timeupdate only when playing
            if(player.getPlayerState() === 1) {{
                sendYouTubeEvent('timeupdate');
            }}
        }}, 1000);
      }}

      function onPlayerStateChange(event) {{
        if (event.data === YT.PlayerState.PLAYING) {{
          sendYouTubeEvent('play');
        }} else if (event.data === YT.PlayerState.PAUSED) {{
          sendYouTubeEvent('pause');
        }}
      }}
    </script>
    '''
    components.html(component_html, height=400)


# --- Main App Router ---
st.set_page_config(layout="wide")
st.title("Video Analysis Platform")

# --- Sidebar for Adding New Videos ---
with st.sidebar:
    st.title("Add New Video")
    st.button("Video Gallery", on_click=navigate_to, args=('gallery',), use_container_width=True)
    st.divider()

    upload_expander = st.expander("Upload Your Own Video", expanded=True)
    with upload_expander:
        file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi"], label_visibility="collapsed")
        if file and st.button("Analyze Uploaded Video"):
            with st.spinner("Uploading..."):
                files = {"video": (file.name, file.getvalue(), file.type)}
                res = requests.post(f"{BACKEND_API_URL}/upload/", files=files)
                if res.status_code == 200:
                    navigate_to('detail', res.json()['video_id'])
                else:
                    st.error("Upload failed.")

    direct_link_expander = st.expander("Analyze by Direct Link")
    with direct_link_expander:
        direct_url = st.text_input("Paste direct video URL here", label_visibility="collapsed")
        if st.button("Analyze Direct Link"):
            if direct_url:
                with st.spinner("Registering..."):
                    res = requests.post(f"{BACKEND_API_URL}/register-video/", json={"video_url": direct_url})
                    if res.status_code == 200:
                        navigate_to('detail', res.json()['video_id'])
                    else:
                        st.error("Failed to register URL.")
            else:
                st.warning("Please enter a URL.")

    youtube_expander = st.expander("Analyze a YouTube Video")
    with youtube_expander:
        yt_url = st.text_input("Paste YouTube URL here", label_visibility="collapsed")
        if st.button("Analyze YouTube Video"):
            video_id = get_youtube_id(yt_url)
            if video_id:
                navigate_to('detail', video_id)
            else:
                st.warning("Invalid YouTube URL.")

# --- Content Area based on Page State ---
if st.session_state.page == 'gallery':
    render_gallery_page()
elif st.session_state.page == 'detail':
    render_detail_page()

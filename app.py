import streamlit as st
import os
import json
import time
import subprocess
import threading
import psutil
from datetime import datetime, timedelta
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import requests
from livesesion import get_session_manager
from advanced_settings import render_advanced_settings

# Jakarta timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

# Configuration files
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'
CHANNEL_CONFIG_FILE = 'channel_config.json'
THUMBNAIL_UPLOAD_LOG = 'thumbnail_uploads.json'

# Streamlit page config
st.set_page_config(
    page_title="YouTube Live Stream Manager",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def check_authentication():
    """Check if user is authenticated with YouTube API"""
    try:
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                return True, creds
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                return True, creds
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None

def get_youtube_service():
    """Get authenticated YouTube service"""
    try:
        is_auth, creds = check_authentication()
        if is_auth:
            return build('youtube', 'v3', credentials=creds)
        return None
    except Exception as e:
        st.error(f"Error getting YouTube service: {e}")
        return None

def authenticate_youtube():
    """Authenticate with YouTube API"""
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            st.error("❌ credentials.json file not found. Please upload it first.")
            return False
        
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        st.success("✅ Authentication successful!")
        return True
    except Exception as e:
        st.error(f"❌ Authentication failed: {e}")
        return False

def test_api_connection():
    """Test YouTube API connection"""
    try:
        youtube = get_youtube_service()
        if youtube:
            request = youtube.channels().list(part="snippet,statistics", mine=True)
            response = request.execute()
            
            if response.get('items'):
                channel = response['items'][0]
                st.success("✅ API connection successful!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Subscribers", channel['statistics'].get('subscriberCount', 'N/A'))
                with col2:
                    st.metric("Videos", channel['statistics'].get('videoCount', 'N/A'))
                with col3:
                    st.metric("Views", channel['statistics'].get('viewCount', 'N/A'))
                
                return True
            else:
                st.error("❌ No channel found")
                return False
        else:
            st.error("❌ Failed to get YouTube service")
            return False
    except Exception as e:
        st.error(f"❌ API test failed: {e}")
        return False

def show_api_quota_info():
    """Show API quota information"""
    st.info("""
    📊 **YouTube API Quota Information:**
    - Daily quota: 10,000 units
    - Live broadcast creation: ~50 units
    - Thumbnail upload: ~50 units
    - Channel info: ~1 unit
    """)

def can_upload_thumbnail():
    """Check if thumbnail upload is allowed based on quota"""
    try:
        if os.path.exists(THUMBNAIL_UPLOAD_LOG):
            with open(THUMBNAIL_UPLOAD_LOG, 'r') as f:
                upload_log = json.load(f)
        else:
            upload_log = {'daily': {}, 'hourly': {}}
        
        now = datetime.now(JAKARTA_TZ)
        today = now.strftime('%Y-%m-%d')
        current_hour = now.strftime('%Y-%m-%d-%H')
        
        daily_count = upload_log['daily'].get(today, 0)
        hourly_count = upload_log['hourly'].get(current_hour, 0)
        
        # YouTube limits: 50 per day, 10 per hour (conservative estimates)
        can_upload = daily_count < 50 and hourly_count < 10
        
        return can_upload, daily_count, hourly_count
    except Exception as e:
        st.error(f"Error checking upload quota: {e}")
        return True, 0, 0

def log_thumbnail_upload():
    """Log thumbnail upload for quota tracking"""
    try:
        if os.path.exists(THUMBNAIL_UPLOAD_LOG):
            with open(THUMBNAIL_UPLOAD_LOG, 'r') as f:
                upload_log = json.load(f)
        else:
            upload_log = {'daily': {}, 'hourly': {}}
        
        now = datetime.now(JAKARTA_TZ)
        today = now.strftime('%Y-%m-%d')
        current_hour = now.strftime('%Y-%m-%d-%H')
        
        upload_log['daily'][today] = upload_log['daily'].get(today, 0) + 1
        upload_log['hourly'][current_hour] = upload_log['hourly'].get(current_hour, 0) + 1
        
        # Clean old entries (keep only last 7 days)
        cutoff_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        upload_log['daily'] = {k: v for k, v in upload_log['daily'].items() if k >= cutoff_date}
        
        # Clean old hourly entries (keep only last 24 hours)
        cutoff_hour = (now - timedelta(hours=24)).strftime('%Y-%m-%d-%H')
        upload_log['hourly'] = {k: v for k, v in upload_log['hourly'].items() if k >= cutoff_hour}
        
        with open(THUMBNAIL_UPLOAD_LOG, 'w') as f:
            json.dump(upload_log, f, indent=2)
            
    except Exception as e:
        st.error(f"Error logging upload: {e}")

def render_stream_manager():
    """Render Stream Manager tab"""
    st.header("🎬 Stream Manager")
    
    # Check if there's an active stream
    session_manager = get_session_manager()
    current_broadcast = session_manager.get_current_broadcast()
    
    if current_broadcast:
        st.success("✅ Active Stream Found!")
        
        broadcast_data = current_broadcast['data']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📺 Stream Information")
            st.write(f"**Title:** {broadcast_data.get('title', 'N/A')}")
            st.write(f"**Description:** {broadcast_data.get('description', 'N/A')[:100]}...")
            st.write(f"**Privacy:** {broadcast_data.get('privacy', 'N/A')}")
            st.write(f"**Created:** {current_broadcast.get('created_at', 'N/A')}")
        
        with col2:
            st.subheader("🔧 Stream Controls")
            
            if st.button("🚀 Start Streaming", type="primary", use_container_width=True):
                st.success("🎬 Stream started! Use your streaming software with the RTMP details.")
            
            if st.button("⏹️ Stop Streaming", use_container_width=True):
                st.info("⏹️ Stream stopped.")
            
            if st.button("🗑️ Delete Stream", use_container_width=True):
                session_manager.clear_current_broadcast()
                st.success("🗑️ Stream deleted from session.")
                st.rerun()
        
        # Show RTMP details
        st.divider()
        st.subheader("📡 RTMP Configuration")
        
        rtmp_url = broadcast_data.get('rtmp_url', 'rtmp://a.rtmp.youtube.com/live2')
        stream_key = broadcast_data.get('stream_key', 'your-stream-key')
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("📡 RTMP URL", value=rtmp_url, disabled=True)
        with col2:
            st.text_input("🔑 Stream Key", value=stream_key, type="password")
        
        # Quick actions
        st.divider()
        st.subheader("⚡ Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Copy RTMP URL", use_container_width=True):
                st.code(rtmp_url)
        with col2:
            if st.button("🔑 Copy Stream Key", use_container_width=True):
                st.code(stream_key)
        with col3:
            if st.button("📊 View Analytics", use_container_width=True):
                st.info("Analytics feature coming soon!")
    
    else:
        st.info("ℹ️ No active stream found. Create a new stream to get started.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Create New Stream", type="primary", use_container_width=True):
                st.switch_page("Add New Stream")
        
        with col2:
            if st.button("📚 Load Recent Config", use_container_width=True):
                configs = session_manager.get_stream_configs()
                if configs:
                    st.success(f"Found {len(configs)} saved configurations")
                else:
                    st.info("No saved configurations found")

def render_add_new_stream():
    """Render Add New Stream tab"""
    st.header("➕ Add New Stream")
    
    # Check authentication first
    is_auth, creds = check_authentication()
    if not is_auth:
        st.warning("⚠️ Please authenticate with YouTube API first in the YouTube API tab.")
        return
    
    session_manager = get_session_manager()
    
    # Load saved form data
    saved_form = session_manager.get_form_data('new_stream_form')
    
    with st.form("new_stream_form"):
        st.subheader("📝 Stream Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input(
                "🎬 Stream Title",
                value=saved_form.get('title', '') if saved_form else '',
                placeholder="Enter your stream title"
            )
            
            description = st.text_area(
                "📝 Description",
                value=saved_form.get('description', '') if saved_form else '',
                placeholder="Describe your stream...",
                height=100
            )
            
            privacy = st.selectbox(
                "🔒 Privacy",
                options=['public', 'unlisted', 'private'],
                index=['public', 'unlisted', 'private'].index(saved_form.get('privacy', 'public')) if saved_form else 0
            )
        
        with col2:
            category = st.selectbox(
                "📂 Category",
                options=['Gaming', 'Music', 'Education', 'Entertainment', 'Sports', 'Technology', 'Other'],
                index=['Gaming', 'Music', 'Education', 'Entertainment', 'Sports', 'Technology', 'Other'].index(saved_form.get('category', 'Gaming')) if saved_form else 0
            )
            
            tags = st.text_input(
                "🏷️ Tags (comma separated)",
                value=saved_form.get('tags', '') if saved_form else '',
                placeholder="gaming, live, stream, youtube"
            )
            
            language = st.selectbox(
                "🌐 Language",
                options=['en', 'id', 'es', 'fr', 'de', 'ja', 'ko', 'zh'],
                index=['en', 'id', 'es', 'fr', 'de', 'ja', 'ko', 'zh'].index(saved_form.get('language', 'en')) if saved_form else 0
            )
        
        # Thumbnail upload
        st.divider()
        st.subheader("📸 Custom Thumbnail")
        
        can_upload, daily_count, hourly_count = can_upload_thumbnail()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            thumbnail_file = st.file_uploader(
                "Upload Custom Thumbnail",
                type=['jpg', 'jpeg', 'png'],
                help="Recommended size: 1280x720 pixels",
                disabled=not can_upload
            )
        
        with col2:
            st.metric("Daily Uploads", f"{daily_count}/50")
            st.metric("Hourly Uploads", f"{hourly_count}/10")
            
            if not can_upload:
                st.error("❌ Upload quota exceeded")
        
        # Advanced settings
        st.divider()
        st.subheader("⚙️ Advanced Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_dvr = st.checkbox(
                "📹 Enable DVR",
                value=saved_form.get('enable_dvr', True) if saved_form else True,
                help="Allow viewers to rewind and replay"
            )
            
            enable_auto_start = st.checkbox(
                "🚀 Auto Start",
                value=saved_form.get('enable_auto_start', True) if saved_form else True,
                help="Start broadcast automatically when streaming begins"
            )
        
        with col2:
            enable_content_encryption = st.checkbox(
                "🔐 Enable Content Encryption",
                value=saved_form.get('enable_content_encryption', False) if saved_form else False,
                help="Encrypt stream content"
            )
            
            custom_rtmp = st.text_input(
                "📡 Custom RTMP URL (optional)",
                value=saved_form.get('custom_rtmp', '') if saved_form else '',
                placeholder="rtmp://your-custom-server.com/live"
            )
        
        # Submit button
        submitted = st.form_submit_button("🎬 Create Live Stream", type="primary", use_container_width=True)
        
        if submitted:
            # Save form data
            form_data = {
                'title': title,
                'description': description,
                'privacy': privacy,
                'category': category,
                'tags': tags,
                'language': language,
                'enable_dvr': enable_dvr,
                'enable_auto_start': enable_auto_start,
                'enable_content_encryption': enable_content_encryption,
                'custom_rtmp': custom_rtmp
            }
            session_manager.save_form_data('new_stream_form', form_data)
            
            # Validate required fields
            if not title:
                st.error("❌ Stream title is required!")
                return
            
            # Create the stream
            with st.spinner("🎬 Creating live stream..."):
                success = create_live_stream(
                    title=title,
                    description=description,
                    privacy=privacy,
                    category=category,
                    tags=tags.split(',') if tags else [],
                    language=language,
                    thumbnail_file=thumbnail_file,
                    enable_dvr=enable_dvr,
                    enable_auto_start=enable_auto_start,
                    enable_content_encryption=enable_content_encryption,
                    custom_rtmp=custom_rtmp
                )
                
                if success:
                    st.success("✅ Live stream created successfully!")
                    # Clear form data after successful creation
                    session_manager.save_form_data('new_stream_form', {})
                    st.rerun()

def create_live_stream(title, description, privacy, category, tags, language, 
                      thumbnail_file=None, enable_dvr=True, enable_auto_start=True,
                      enable_content_encryption=False, custom_rtmp=''):
    """Create a new live stream"""
    try:
        youtube = get_youtube_service()
        if not youtube:
            st.error("❌ Failed to get YouTube service")
            return False
        
        # Create broadcast
        broadcast_body = {
            'snippet': {
                'title': title,
                'description': description,
                'scheduledStartTime': datetime.now(JAKARTA_TZ).isoformat(),
            },
            'status': {
                'privacyStatus': privacy
            },
            'contentDetails': {
                'enableAutoStart': enable_auto_start,
                'enableDvr': enable_dvr,
                'enableContentEncryption': enable_content_encryption,
                'recordFromStart': True,
                'enableEmbed': True
            }
        }
        
        # Apply advanced settings
        from advanced_settings import apply_advanced_settings_to_broadcast
        broadcast_body = apply_advanced_settings_to_broadcast(broadcast_body)
        
        broadcast_response = youtube.liveBroadcasts().insert(
            part='snippet,status,contentDetails',
            body=broadcast_body
        ).execute()
        
        broadcast_id = broadcast_response['id']
        
        # Create stream
        stream_body = {
            'snippet': {
                'title': f"{title} - Stream"
            },
            'cdn': {
                'format': '1080p',
                'ingestionType': 'rtmp'
            }
        }
        
        stream_response = youtube.liveStreams().insert(
            part='snippet,cdn',
            body=stream_body
        ).execute()
        
        stream_id = stream_response['id']
        
        # Bind broadcast to stream
        youtube.liveBroadcasts().bind(
            part='id,contentDetails',
            id=broadcast_id,
            streamId=stream_id
        ).execute()
        
        # Upload thumbnail if provided
        if thumbnail_file and can_upload_thumbnail()[0]:
            upload_thumbnail(youtube, broadcast_id, thumbnail_file)
        
        # Save stream data to session
        stream_data = {
            'broadcast_id': broadcast_id,
            'stream_id': stream_id,
            'title': title,
            'description': description,
            'privacy': privacy,
            'rtmp_url': stream_response['cdn']['ingestionInfo']['ingestionAddress'],
            'stream_key': stream_response['cdn']['ingestionInfo']['streamName'],
            'watch_url': f"https://www.youtube.com/watch?v={broadcast_id}",
            'created_at': datetime.now(JAKARTA_TZ).isoformat()
        }
        
        session_manager = get_session_manager()
        session_manager.save_broadcast_data(stream_data)
        
        # Send notification
        from advanced_settings import send_stream_notification
        send_stream_notification('stream_start', f'Live stream "{title}" created successfully', stream_data)
        
        return True
        
    except Exception as e:
        st.error(f"❌ Failed to create live stream: {e}")
        return False

def upload_thumbnail(youtube, video_id, thumbnail_file):
    """Upload custom thumbnail"""
    try:
        # Save uploaded file temporarily
        temp_path = f"temp_thumbnail_{int(time.time())}.jpg"
        with open(temp_path, "wb") as f:
            f.write(thumbnail_file.getbuffer())
        
        # Upload thumbnail
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(temp_path, mimetype='image/jpeg')
        ).execute()
        
        # Log the upload
        log_thumbnail_upload()
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        st.success("✅ Custom thumbnail uploaded successfully!")
        
    except Exception as e:
        st.error(f"❌ Failed to upload thumbnail: {e}")

def render_youtube_api():
    """Render YouTube API tab"""
    st.header("📺 YouTube API Configuration")
    
    # Authentication status
    is_auth, creds = check_authentication()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Authentication Status")
        if is_auth:
            st.success("✅ Authenticated with YouTube API")
            
            if st.button("🔄 Refresh Authentication", use_container_width=True):
                if authenticate_youtube():
                    st.rerun()
            
            if st.button("🧪 Test API Connection", use_container_width=True):
                test_api_connection()
        else:
            st.error("❌ Not authenticated")
            
            if st.button("🔐 Authenticate Now", type="primary", use_container_width=True):
                if authenticate_youtube():
                    st.rerun()
    
    with col2:
        st.subheader("📊 API Information")
        show_api_quota_info()
    
    # Upload credentials
    st.divider()
    st.subheader("📁 Upload OAuth Credentials")
    
    uploaded_file = st.file_uploader(
        "Upload credentials.json",
        type=['json'],
        help="Download this file from Google Cloud Console"
    )
    
    if uploaded_file:
        try:
            credentials_content = json.load(uploaded_file)
            
            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump(credentials_content, f, indent=2)
            
            st.success("✅ Credentials file uploaded successfully!")
            
            if st.button("🔐 Authenticate with New Credentials"):
                if authenticate_youtube():
                    st.rerun()
                    
        except Exception as e:
            st.error(f"❌ Invalid credentials file: {e}")
    
    # Channel information
    if is_auth:
        st.divider()
        st.subheader("📺 Channel Information")
        
        try:
            youtube = get_youtube_service()
            if youtube:
                request = youtube.channels().list(part="snippet,statistics", mine=True)
                response = request.execute()
                
                if response.get('items'):
                    channel = response['items'][0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Channel Name:** {channel['snippet']['title']}")
                        st.write(f"**Channel ID:** {channel['id']}")
                        st.write(f"**Description:** {channel['snippet']['description'][:100]}...")
                    
                    with col2:
                        stats = channel['statistics']
                        st.metric("Subscribers", stats.get('subscriberCount', 'N/A'))
                        st.metric("Videos", stats.get('videoCount', 'N/A'))
                        st.metric("Total Views", stats.get('viewCount', 'N/A'))
                        
        except Exception as e:
            st.error(f"❌ Failed to get channel info: {e}")

def render_logs():
    """Render Logs tab"""
    st.header("📊 System Logs & Information")
    
    # Session information
    session_manager = get_session_manager()
    session_info = session_manager.get_session_info()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Session Information")
        st.write(f"**Session ID:** {session_info['session_id']}")
        st.write(f"**Has Active Broadcast:** {'✅' if session_info['has_broadcast'] else '❌'}")
        st.write(f"**Stream Configs:** {session_info['stream_configs_count']}")
        st.write(f"**Form Data:** {session_info['form_data_count']}")
        
        if session_info.get('last_updated'):
            last_updated = datetime.fromtimestamp(session_info['last_updated'])
            st.write(f"**Last Updated:** {last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
    
    with col2:
        st.subheader("💻 System Information")
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        st.metric("CPU Usage", f"{cpu_percent}%")
        
        # Memory usage
        memory = psutil.virtual_memory()
        st.metric("Memory Usage", f"{memory.percent}%")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        st.metric("Disk Usage", f"{disk.percent}%")
    
    # Application logs
    st.divider()
    st.subheader("📝 Application Logs")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto-refresh logs", value=False)
    
    if auto_refresh:
        # Auto-refresh every 5 seconds
        time.sleep(5)
        st.rerun()
    
    # Log levels
    log_level = st.selectbox("📊 Log Level", ['INFO', 'WARNING', 'ERROR', 'DEBUG'])
    
    # Sample logs (in a real app, you'd read from actual log files)
    logs = [
        f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Application started",
        f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Session manager initialized",
        f"[{datetime.now().strftime('%H:%M:%S')}] INFO: YouTube API service ready",
    ]
    
    # Display logs
    log_container = st.container()
    with log_container:
        for log in logs[-10:]:  # Show last 10 logs
            if log_level in log:
                if 'ERROR' in log:
                    st.error(log)
                elif 'WARNING' in log:
                    st.warning(log)
                else:
                    st.info(log)
    
    # Log management
    st.divider()
    st.subheader("🗂️ Log Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Logs", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Session Logs", use_container_width=True):
            # Clear session data
            cleaned = session_manager.cleanup_old_sessions(0)  # Clear all
            st.success(f"✅ Cleared {cleaned} old sessions")
    
    with col3:
        if st.button("📥 Export Logs", use_container_width=True):
            # Export session data
            export_data = session_manager.export_session()
            if export_data:
                st.download_button(
                    "📥 Download Session Data",
                    data=export_data,
                    file_name=f"session_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

def main():
    """Main application function"""
    
    # Initialize session manager
    session_manager = get_session_manager()
    session_manager.restore_session_state()
    
    # Sidebar
    with st.sidebar:
        st.title("🎬 YouTube Live Stream Manager")
        
        # Configuration section
        st.header("📁 Configuration")
        
        # Session info
        session_info = session_manager.get_session_info()
        st.info(f"📋 Session: {session_info['session_id'][-8:]}")
        
        # Saved channels
        st.header("📺 Saved Channels")
        st.write("Previously authenticated channels:")
        
        # Sample channel (replace with actual saved channels)
        with st.expander("🎮 Tombo Alternatif"):
            st.write("Last used: 2025-07-06")
            if st.button("🔄 Use", key="use_channel"):
                st.success("Channel selected!")
        
        # Google OAuth Setup
        st.header("🔐 Google OAuth Setup")
        
        uploaded_oauth = st.file_uploader(
            "Upload Google OAuth JSON",
            type=['json'],
            help="Limit 200MB per file • JSON"
        )
        
        if uploaded_oauth:
            try:
                oauth_content = json.load(uploaded_oauth)
                with open(CREDENTIALS_FILE, 'w') as f:
                    json.dump(oauth_content, f, indent=2)
                st.success("✅ OAuth file uploaded!")
            except Exception as e:
                st.error(f"❌ Invalid OAuth file: {e}")
        
        if st.button("📁 Browse files"):
            st.info("Use the file uploader above")
        
        # Channel Configuration
        st.header("📺 Channel Configuration")
        
        uploaded_config = st.file_uploader(
            "Upload JSON Configuration",
            type=['json'],
            help="Limit 200MB per file • JSON",
            key="config_upload"
        )
        
        if uploaded_config:
            try:
                config_content = json.load(uploaded_config)
                with open(CHANNEL_CONFIG_FILE, 'w') as f:
                    json.dump(config_content, f, indent=2)
                st.success("✅ Configuration uploaded!")
            except Exception as e:
                st.error(f"❌ Invalid configuration: {e}")
        
        if st.button("📁 Browse files", key="config_browse"):
            st.info("Use the file uploader above")
        
        # Log Management
        st.header("📊 Log Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Logs"):
                st.rerun()
        with col2:
            if st.button("🗑️ Clear Session Logs"):
                cleaned = session_manager.cleanup_old_sessions(0)
                st.success(f"✅ Cleared {cleaned} sessions")
    
    # Main content area
    st.title("🎬 YouTube Live Stream Manager")
    
    # Create tabs
    tabs = st.tabs(["🎬 Stream Manager", "➕ Add New Stream", "📺 YouTube API", "📊 Logs", "⚙️ Advanced Settings"])
    
    # Tab 1: Stream Manager
    with tabs[0]:
        render_stream_manager()
    
    # Tab 2: Add New Stream
    with tabs[1]:
        render_add_new_stream()
    
    # Tab 3: YouTube API
    with tabs[2]:
        render_youtube_api()
    
    # Tab 4: Logs
    with tabs[3]:
        render_logs()
    
    # Tab 5: Advanced Settings
    with tabs[4]:
        render_advanced_settings()

if __name__ == "__main__":
    main()

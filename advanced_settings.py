import streamlit as st
import os
import json
import time
from datetime import datetime
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import requests
from livesesion import get_session_manager

# Jakarta timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Advanced settings file
ADVANCED_SETTINGS_FILE = 'advanced_settings.json'

class AdvancedSettings:
    """Advanced Settings Manager untuk YouTube Live Streaming"""
    
    def __init__(self):
        self.settings = self.load_settings()
        self.session_manager = get_session_manager()
    
    def load_settings(self):
        """Load advanced settings dari file"""
        try:
            if os.path.exists(ADVANCED_SETTINGS_FILE):
                with open(ADVANCED_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self.get_default_settings()
        except Exception as e:
            st.error(f"Error loading advanced settings: {e}")
            return self.get_default_settings()
    
    def save_settings(self):
        """Save advanced settings ke file"""
        try:
            with open(ADVANCED_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            # Save to session as well
            self.session_manager.save_form_data('advanced_settings', self.settings)
            
        except Exception as e:
            st.error(f"Error saving advanced settings: {e}")
    
    def get_default_settings(self):
        """Default advanced settings"""
        return {
            'stream_settings': {
                'enable_dvr': True,
                'enable_content_encryption': False,
                'enable_embed': True,
                'enable_auto_start': True,
                'enable_auto_stop': True,
                'record_from_start': True,
                'monitor_stream': False,
                'broadcast_delay_ms': 0,
                'custom_rtmp_url': '',
                'stream_latency': 'normal'  # normal, low, ultra_low
            },
            'thumbnail_settings': {
                'auto_upload': True,
                'resize_thumbnail': True,
                'thumbnail_quality': 85,
                'backup_thumbnails': True
            },
            'monetization': {
                'enable_monetization': False,
                'enable_super_chat': False,
                'enable_channel_memberships': False,
                'enable_merchandise': False
            },
            'technical_settings': {
                'video_codec': 'h264',
                'audio_codec': 'aac',
                'keyframe_interval': 2,
                'b_frames': 0,
                'audio_sample_rate': 44100,
                'audio_channels': 2,
                'enable_hardware_encoding': False
            },
            'notification_settings': {
                'notify_stream_start': True,
                'notify_stream_end': True,
                'notify_errors': True,
                'webhook_url': ''
            },
            'security_settings': {
                'enable_stream_key_rotation': False,
                'allowed_encoders': [],
                'ip_whitelist': [],
                'enable_https_only': True
            }
        }
    
    def render_advanced_settings_ui(self):
        """Render UI untuk advanced settings"""
        st.header("⚙️ Advanced Settings")
        
        # Load current settings
        current_settings = self.settings.copy()
        
        # Create tabs for different setting categories
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🎬 Stream Settings", 
            "📸 Thumbnail", 
            "💰 Monetization", 
            "🔧 Technical", 
            "🔔 Notifications",
            "🔒 Security"
        ])
        
        # Tab 1: Stream Settings
        with tab1:
            st.subheader("🎬 Stream Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📺 Basic Stream Settings**")
                
                current_settings['stream_settings']['enable_dvr'] = st.checkbox(
                    "📹 Enable DVR",
                    value=current_settings['stream_settings']['enable_dvr'],
                    help="Allow viewers to rewind and replay the stream"
                )
                
                current_settings['stream_settings']['enable_embed'] = st.checkbox(
                    "🔗 Enable Embed",
                    value=current_settings['stream_settings']['enable_embed'],
                    help="Allow the stream to be embedded on other websites"
                )
                
                current_settings['stream_settings']['enable_auto_start'] = st.checkbox(
                    "🚀 Auto Start",
                    value=current_settings['stream_settings']['enable_auto_start'],
                    help="Automatically start the broadcast when streaming begins"
                )
                
                current_settings['stream_settings']['enable_auto_stop'] = st.checkbox(
                    "⏹️ Auto Stop",
                    value=current_settings['stream_settings']['enable_auto_stop'],
                    help="Automatically stop the broadcast when streaming ends"
                )
                
                current_settings['stream_settings']['record_from_start'] = st.checkbox(
                    "🎥 Record from Start",
                    value=current_settings['stream_settings']['record_from_start'],
                    help="Start recording as soon as the stream begins"
                )
            
            with col2:
                st.write("**🔧 Advanced Stream Settings**")
                
                current_settings['stream_settings']['enable_content_encryption'] = st.checkbox(
                    "🔐 Enable Content Encryption",
                    value=current_settings['stream_settings']['enable_content_encryption'],
                    help="Encrypt the stream content for additional security"
                )
                
                current_settings['stream_settings']['monitor_stream'] = st.checkbox(
                    "📊 Monitor Stream",
                    value=current_settings['stream_settings']['monitor_stream'],
                    help="Enable stream health monitoring"
                )
                
                current_settings['stream_settings']['stream_latency'] = st.selectbox(
                    "⚡ Stream Latency",
                    options=['normal', 'low', 'ultra_low'],
                    index=['normal', 'low', 'ultra_low'].index(current_settings['stream_settings']['stream_latency']),
                    help="Choose stream latency mode"
                )
                
                current_settings['stream_settings']['broadcast_delay_ms'] = st.number_input(
                    "⏱️ Broadcast Delay (ms)",
                    min_value=0,
                    max_value=30000,
                    value=current_settings['stream_settings']['broadcast_delay_ms'],
                    help="Add delay to the broadcast in milliseconds"
                )
            
            st.divider()
            
            st.write("**🌐 Custom RTMP Settings**")
            current_settings['stream_settings']['custom_rtmp_url'] = st.text_input(
                "📡 Custom RTMP URL (Optional)",
                value=current_settings['stream_settings']['custom_rtmp_url'],
                help="Use custom RTMP server instead of YouTube's default",
                placeholder="rtmp://your-custom-server.com/live"
            )
        
        # Tab 2: Thumbnail Settings
        with tab2:
            st.subheader("📸 Thumbnail Management")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📸 Thumbnail Upload Settings**")
                
                current_settings['thumbnail_settings']['auto_upload'] = st.checkbox(
                    "🚀 Auto Upload Thumbnails",
                    value=current_settings['thumbnail_settings']['auto_upload'],
                    help="Automatically upload thumbnails when creating broadcasts"
                )
                
                current_settings['thumbnail_settings']['resize_thumbnail'] = st.checkbox(
                    "📏 Auto Resize Thumbnails",
                    value=current_settings['thumbnail_settings']['resize_thumbnail'],
                    help="Automatically resize thumbnails to YouTube's recommended size (1280x720)"
                )
                
                current_settings['thumbnail_settings']['thumbnail_quality'] = st.slider(
                    "🎨 Thumbnail Quality",
                    min_value=50,
                    max_value=100,
                    value=current_settings['thumbnail_settings']['thumbnail_quality'],
                    help="JPEG quality for thumbnail compression"
                )
                
                current_settings['thumbnail_settings']['backup_thumbnails'] = st.checkbox(
                    "💾 Backup Thumbnails",
                    value=current_settings['thumbnail_settings']['backup_thumbnails'],
                    help="Keep local backup copies of uploaded thumbnails"
                )
            
            with col2:
                st.write("**📊 Thumbnail Upload Status**")
                
                # Show thumbnail upload quota
                from app import can_upload_thumbnail
                can_upload, daily_count, hourly_count = can_upload_thumbnail()
                
                st.metric("📅 Daily Uploads", f"{daily_count}/50")
                st.metric("⏰ Hourly Uploads", f"{hourly_count}/10")
                
                if can_upload:
                    st.success("✅ Upload quota available")
                else:
                    st.error("❌ Upload quota exceeded")
                
                # Thumbnail upload test
                st.write("**🧪 Test Thumbnail Upload**")
                test_thumbnail = st.file_uploader(
                    "Upload Test Thumbnail",
                    type=['jpg', 'jpeg', 'png'],
                    help="Test thumbnail upload functionality"
                )
                
                if test_thumbnail and st.button("🧪 Test Upload"):
                    self.test_thumbnail_upload(test_thumbnail)
        
        # Tab 3: Monetization
        with tab3:
            st.subheader("💰 Monetization Settings")
            
            st.warning("⚠️ Monetization features require YouTube Partner Program eligibility")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**💰 Revenue Features**")
                
                current_settings['monetization']['enable_monetization'] = st.checkbox(
                    "💰 Enable Monetization",
                    value=current_settings['monetization']['enable_monetization'],
                    help="Enable ads and monetization for the stream"
                )
                
                current_settings['monetization']['enable_super_chat'] = st.checkbox(
                    "💬 Enable Super Chat",
                    value=current_settings['monetization']['enable_super_chat'],
                    help="Allow viewers to pay to highlight their messages"
                )
                
                current_settings['monetization']['enable_channel_memberships'] = st.checkbox(
                    "👥 Enable Channel Memberships",
                    value=current_settings['monetization']['enable_channel_memberships'],
                    help="Allow viewers to become channel members"
                )
            
            with col2:
                st.write("**🛍️ Additional Features**")
                
                current_settings['monetization']['enable_merchandise'] = st.checkbox(
                    "🛍️ Enable Merchandise Shelf",
                    value=current_settings['monetization']['enable_merchandise'],
                    help="Show merchandise below the stream"
                )
                
                if current_settings['monetization']['enable_monetization']:
                    st.info("💡 Monetization enabled - ads will be shown during stream")
                else:
                    st.info("ℹ️ Monetization disabled - no ads will be shown")
        
        # Tab 4: Technical Settings
        with tab4:
            st.subheader("🔧 Technical Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🎥 Video Settings**")
                
                current_settings['technical_settings']['video_codec'] = st.selectbox(
                    "📹 Video Codec",
                    options=['h264', 'h265'],
                    index=['h264', 'h265'].index(current_settings['technical_settings']['video_codec']),
                    help="Video encoding codec"
                )
                
                current_settings['technical_settings']['keyframe_interval'] = st.number_input(
                    "🔑 Keyframe Interval (seconds)",
                    min_value=1,
                    max_value=10,
                    value=current_settings['technical_settings']['keyframe_interval'],
                    help="Interval between keyframes"
                )
                
                current_settings['technical_settings']['b_frames'] = st.number_input(
                    "🎬 B-Frames",
                    min_value=0,
                    max_value=3,
                    value=current_settings['technical_settings']['b_frames'],
                    help="Number of B-frames between keyframes"
                )
                
                current_settings['technical_settings']['enable_hardware_encoding'] = st.checkbox(
                    "⚡ Hardware Encoding",
                    value=current_settings['technical_settings']['enable_hardware_encoding'],
                    help="Use hardware acceleration for encoding (if available)"
                )
            
            with col2:
                st.write("**🎵 Audio Settings**")
                
                current_settings['technical_settings']['audio_codec'] = st.selectbox(
                    "🎵 Audio Codec",
                    options=['aac', 'mp3'],
                    index=['aac', 'mp3'].index(current_settings['technical_settings']['audio_codec']),
                    help="Audio encoding codec"
                )
                
                current_settings['technical_settings']['audio_sample_rate'] = st.selectbox(
                    "📊 Sample Rate (Hz)",
                    options=[22050, 44100, 48000],
                    index=[22050, 44100, 48000].index(current_settings['technical_settings']['audio_sample_rate']),
                    help="Audio sample rate"
                )
                
                current_settings['technical_settings']['audio_channels'] = st.selectbox(
                    "🔊 Audio Channels",
                    options=[1, 2],
                    index=[1, 2].index(current_settings['technical_settings']['audio_channels']),
                    help="Number of audio channels (1=Mono, 2=Stereo)"
                )
        
        # Tab 5: Notifications
        with tab5:
            st.subheader("🔔 Notification Settings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📢 Stream Notifications**")
                
                current_settings['notification_settings']['notify_stream_start'] = st.checkbox(
                    "🚀 Notify on Stream Start",
                    value=current_settings['notification_settings']['notify_stream_start'],
                    help="Send notification when stream starts"
                )
                
                current_settings['notification_settings']['notify_stream_end'] = st.checkbox(
                    "⏹️ Notify on Stream End",
                    value=current_settings['notification_settings']['notify_stream_end'],
                    help="Send notification when stream ends"
                )
                
                current_settings['notification_settings']['notify_errors'] = st.checkbox(
                    "❌ Notify on Errors",
                    value=current_settings['notification_settings']['notify_errors'],
                    help="Send notification when errors occur"
                )
            
            with col2:
                st.write("**🌐 Webhook Settings**")
                
                current_settings['notification_settings']['webhook_url'] = st.text_input(
                    "🔗 Webhook URL",
                    value=current_settings['notification_settings']['webhook_url'],
                    help="URL to send webhook notifications",
                    placeholder="https://your-webhook-url.com/notify"
                )
                
                if current_settings['notification_settings']['webhook_url']:
                    if st.button("🧪 Test Webhook"):
                        self.test_webhook(current_settings['notification_settings']['webhook_url'])
        
        # Tab 6: Security
        with tab6:
            st.subheader("🔒 Security Settings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**🔐 Stream Security**")
                
                current_settings['security_settings']['enable_stream_key_rotation'] = st.checkbox(
                    "🔄 Enable Stream Key Rotation",
                    value=current_settings['security_settings']['enable_stream_key_rotation'],
                    help="Automatically rotate stream keys periodically"
                )
                
                current_settings['security_settings']['enable_https_only'] = st.checkbox(
                    "🔒 HTTPS Only",
                    value=current_settings['security_settings']['enable_https_only'],
                    help="Force HTTPS for all connections"
                )
                
                # IP Whitelist
                st.write("**🌐 IP Whitelist**")
                ip_whitelist_text = st.text_area(
                    "Allowed IP Addresses (one per line)",
                    value='\n'.join(current_settings['security_settings']['ip_whitelist']),
                    help="Only allow streaming from these IP addresses"
                )
                current_settings['security_settings']['ip_whitelist'] = [
                    ip.strip() for ip in ip_whitelist_text.split('\n') if ip.strip()
                ]
            
            with col2:
                st.write("**🎥 Encoder Restrictions**")
                
                # Allowed Encoders
                encoder_options = ['OBS Studio', 'XSplit', 'FFmpeg', 'Wirecast', 'Custom']
                selected_encoders = st.multiselect(
                    "Allowed Encoders",
                    options=encoder_options,
                    default=current_settings['security_settings']['allowed_encoders'],
                    help="Restrict which encoders can connect to your stream"
                )
                current_settings['security_settings']['allowed_encoders'] = selected_encoders
        
        # Save Settings Button
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save All Settings", type="primary", use_container_width=True):
                self.settings = current_settings
                self.save_settings()
                st.success("✅ Advanced settings saved successfully!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Reset to Defaults", use_container_width=True):
                if st.session_state.get('confirm_reset', False):
                    self.settings = self.get_default_settings()
                    self.save_settings()
                    st.success("✅ Settings reset to defaults!")
                    st.session_state.confirm_reset = False
                    st.rerun()
                else:
                    st.session_state.confirm_reset = True
                    st.warning("⚠️ Click again to confirm reset")
        
        with col3:
            if st.button("📥 Export Settings", use_container_width=True):
                self.export_settings()
        
        # Import Settings
        st.divider()
        st.subheader("📤 Import/Export Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_settings = st.file_uploader(
                "📥 Import Settings File",
                type=['json'],
                help="Upload a previously exported settings file"
            )
            
            if uploaded_settings and st.button("📥 Import Settings"):
                self.import_settings(uploaded_settings)
        
        with col2:
            # Show current settings summary
            st.write("**📊 Current Settings Summary**")
            settings_summary = self.get_settings_summary()
            for category, count in settings_summary.items():
                st.write(f"• {category}: {count} enabled")
    
    def test_thumbnail_upload(self, thumbnail_file):
        """Test thumbnail upload functionality"""
        try:
            # Save temporary file
            temp_path = f"temp_test_thumbnail_{int(time.time())}.jpg"
            with open(temp_path, "wb") as f:
                f.write(thumbnail_file.getbuffer())
            
            st.success("✅ Thumbnail file saved successfully for testing")
            st.info(f"📁 File size: {os.path.getsize(temp_path) / 1024:.1f} KB")
            
            # Show thumbnail preview
            st.image(thumbnail_file, caption="Thumbnail Preview", width=300)
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as e:
            st.error(f"❌ Thumbnail test failed: {e}")
    
    def test_webhook(self, webhook_url):
        """Test webhook notification"""
        try:
            test_payload = {
                'event': 'test',
                'message': 'Test notification from YouTube Live Stream Manager',
                'timestamp': datetime.now(JAKARTA_TZ).isoformat(),
                'source': 'advanced_settings'
            }
            
            response = requests.post(
                webhook_url,
                json=test_payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                st.success("✅ Webhook test successful!")
            else:
                st.error(f"❌ Webhook test failed: HTTP {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Webhook test error: {e}")
    
    def export_settings(self):
        """Export settings to downloadable file"""
        try:
            export_data = {
                'exported_at': datetime.now(JAKARTA_TZ).isoformat(),
                'version': '1.0',
                'settings': self.settings
            }
            
            export_json = json.dumps(export_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📥 Download Settings File",
                data=export_json,
                file_name=f"youtube_live_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"❌ Export failed: {e}")
    
    def import_settings(self, uploaded_file):
        """Import settings from uploaded file"""
        try:
            import_data = json.load(uploaded_file)
            
            if 'settings' in import_data:
                self.settings = import_data['settings']
                self.save_settings()
                st.success("✅ Settings imported successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid settings file format")
                
        except Exception as e:
            st.error(f"❌ Import failed: {e}")
    
    def get_settings_summary(self):
        """Get summary of enabled settings"""
        summary = {}
        
        # Count enabled stream settings
        stream_enabled = sum(1 for v in self.settings['stream_settings'].values() if isinstance(v, bool) and v)
        summary['Stream Settings'] = stream_enabled
        
        # Count enabled thumbnail settings
        thumbnail_enabled = sum(1 for v in self.settings['thumbnail_settings'].values() if isinstance(v, bool) and v)
        summary['Thumbnail Settings'] = thumbnail_enabled
        
        # Count enabled monetization settings
        monetization_enabled = sum(1 for v in self.settings['monetization'].values() if isinstance(v, bool) and v)
        summary['Monetization'] = monetization_enabled
        
        # Count enabled notification settings
        notification_enabled = sum(1 for v in self.settings['notification_settings'].values() if isinstance(v, bool) and v)
        summary['Notifications'] = notification_enabled
        
        # Count enabled security settings
        security_enabled = sum(1 for v in self.settings['security_settings'].values() if isinstance(v, bool) and v)
        summary['Security'] = security_enabled
        
        return summary
    
    def apply_settings_to_broadcast(self, broadcast_body):
        """Apply advanced settings to broadcast creation"""
        try:
            # Apply stream settings
            if 'contentDetails' not in broadcast_body:
                broadcast_body['contentDetails'] = {}
            
            stream_settings = self.settings['stream_settings']
            
            broadcast_body['contentDetails'].update({
                'enableAutoStart': stream_settings['enable_auto_start'],
                'enableAutoStop': stream_settings['enable_auto_stop'],
                'recordFromStart': stream_settings['record_from_start'],
                'enableDvr': stream_settings['enable_dvr'],
                'enableContentEncryption': stream_settings['enable_content_encryption'],
                'enableEmbed': stream_settings['enable_embed']
            })
            
            # Apply monitor stream settings
            if stream_settings['monitor_stream']:
                broadcast_body['contentDetails']['monitorStream'] = {
                    'enableMonitorStream': True,
                    'broadcastStreamDelayMs': stream_settings['broadcast_delay_ms']
                }
            else:
                broadcast_body['contentDetails']['monitorStream'] = {
                    'enableMonitorStream': False,
                    'broadcastStreamDelayMs': 0
                }
            
            # Apply latency settings
            if stream_settings['stream_latency'] == 'low':
                broadcast_body['contentDetails']['latencyPreference'] = 'low'
            elif stream_settings['stream_latency'] == 'ultra_low':
                broadcast_body['contentDetails']['latencyPreference'] = 'ultraLow'
            else:
                broadcast_body['contentDetails']['latencyPreference'] = 'normal'
            
            return broadcast_body
            
        except Exception as e:
            st.error(f"❌ Error applying advanced settings: {e}")
            return broadcast_body
    
    def get_ffmpeg_advanced_params(self, base_quality_settings):
        """Get advanced FFmpeg parameters based on settings"""
        try:
            technical_settings = self.settings['technical_settings']
            advanced_params = []
            
            # Video codec settings
            if technical_settings['video_codec'] == 'h265':
                advanced_params.extend(['-c:v', 'libx265'])
            
            # Keyframe interval
            keyframe_interval = technical_settings['keyframe_interval']
            advanced_params.extend(['-g', str(keyframe_interval * 30)])  # 30 fps assumed
            
            # B-frames
            if technical_settings['b_frames'] > 0:
                advanced_params.extend(['-bf', str(technical_settings['b_frames'])])
            
            # Audio codec
            if technical_settings['audio_codec'] == 'mp3':
                advanced_params.extend(['-c:a', 'libmp3lame'])
            
            # Audio settings
            advanced_params.extend([
                '-ar', str(technical_settings['audio_sample_rate']),
                '-ac', str(technical_settings['audio_channels'])
            ])
            
            # Hardware encoding
            if technical_settings['enable_hardware_encoding']:
                advanced_params.extend(['-hwaccel', 'auto'])
            
            return advanced_params
            
        except Exception as e:
            st.error(f"❌ Error getting FFmpeg parameters: {e}")
            return []
    
    def send_notification(self, event_type, message, additional_data=None):
        """Send notification based on settings"""
        try:
            notification_settings = self.settings['notification_settings']
            
            # Check if notifications are enabled for this event type
            should_notify = False
            if event_type == 'stream_start' and notification_settings['notify_stream_start']:
                should_notify = True
            elif event_type == 'stream_end' and notification_settings['notify_stream_end']:
                should_notify = True
            elif event_type == 'error' and notification_settings['notify_errors']:
                should_notify = True
            
            if not should_notify:
                return
            
            # Send webhook notification if URL is configured
            webhook_url = notification_settings['webhook_url']
            if webhook_url:
                payload = {
                    'event': event_type,
                    'message': message,
                    'timestamp': datetime.now(JAKARTA_TZ).isoformat(),
                    'source': 'youtube_live_stream_manager'
                }
                
                if additional_data:
                    payload['data'] = additional_data
                
                response = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=5,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    st.success(f"📢 Notification sent: {message}")
                else:
                    st.warning(f"⚠️ Notification failed: HTTP {response.status_code}")
            
            # Show in-app notification
            if event_type == 'error':
                st.error(f"🔔 {message}")
            else:
                st.info(f"🔔 {message}")
                
        except Exception as e:
            st.error(f"❌ Notification error: {e}")

# Global advanced settings instance
def get_advanced_settings():
    """Get atau create advanced settings instance"""
    if 'advanced_settings' not in st.session_state:
        st.session_state.advanced_settings = AdvancedSettings()
    return st.session_state.advanced_settings

# Helper functions
def render_advanced_settings():
    """Helper function untuk render advanced settings UI"""
    advanced_settings = get_advanced_settings()
    advanced_settings.render_advanced_settings_ui()

def apply_advanced_settings_to_broadcast(broadcast_body):
    """Helper function untuk apply settings ke broadcast"""
    advanced_settings = get_advanced_settings()
    return advanced_settings.apply_settings_to_broadcast(broadcast_body)

def get_advanced_ffmpeg_params(base_quality_settings):
    """Helper function untuk get advanced FFmpeg parameters"""
    advanced_settings = get_advanced_settings()
    return advanced_settings.get_ffmpeg_advanced_params(base_quality_settings)

def send_stream_notification(event_type, message, additional_data=None):
    """Helper function untuk send notifications"""
    advanced_settings = get_advanced_settings()
    advanced_settings.send_notification(event_type, message, additional_data)

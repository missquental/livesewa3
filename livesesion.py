import streamlit as st
import json
import os
import time
from datetime import datetime, timedelta
import pytz

# Jakarta timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Session files
SESSION_FILE = 'live_session.json'
TEMP_SESSION_FILE = 'temp_session.json'

class LiveSession:
    """Live Session Manager untuk menyimpan data persistent"""
    
    def __init__(self):
        self.session_id = self._get_or_create_session_id()
        self.session_data = self._load_session()
        
    def _get_or_create_session_id(self):
        """Generate atau ambil session ID yang unik"""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = f"session_{int(time.time())}_{hash(str(datetime.now()))}"
        return st.session_state.session_id
    
    def _load_session(self):
        """Load session data dari file"""
        try:
            if os.path.exists(SESSION_FILE):
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Clean old sessions (older than 24 hours)
                    current_time = time.time()
                    cleaned_data = {}
                    for session_id, session_info in data.items():
                        if current_time - session_info.get('last_updated', 0) < 86400:  # 24 hours
                            cleaned_data[session_id] = session_info
                    return cleaned_data
            return {}
        except Exception as e:
            st.error(f"Error loading session: {e}")
            return {}
    
    def _save_session(self):
        """Save session data ke file"""
        try:
            # Update timestamp
            if self.session_id not in self.session_data:
                self.session_data[self.session_id] = {}
            
            self.session_data[self.session_id]['last_updated'] = time.time()
            self.session_data[self.session_id]['session_id'] = self.session_id
            
            # Save to main file
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
                
            # Save backup
            with open(TEMP_SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            st.error(f"Error saving session: {e}")
    
    def save_broadcast_data(self, broadcast_data):
        """Simpan data broadcast yang baru dibuat"""
        if self.session_id not in self.session_data:
            self.session_data[self.session_id] = {}
        
        self.session_data[self.session_id]['current_broadcast'] = {
            'data': broadcast_data,
            'created_at': datetime.now(JAKARTA_TZ).isoformat(),
            'status': 'created'
        }
        self._save_session()
        
        # Update session state
        st.session_state.new_stream_data = broadcast_data
    
    def get_current_broadcast(self):
        """Ambil data broadcast yang sedang aktif"""
        if self.session_id in self.session_data:
            return self.session_data[self.session_id].get('current_broadcast')
        return None
    
    def save_stream_config(self, stream_config):
        """Simpan konfigurasi stream"""
        if self.session_id not in self.session_data:
            self.session_data[self.session_id] = {}
        
        if 'stream_configs' not in self.session_data[self.session_id]:
            self.session_data[self.session_id]['stream_configs'] = []
        
        # Add timestamp
        stream_config['saved_at'] = datetime.now(JAKARTA_TZ).isoformat()
        stream_config['session_id'] = self.session_id
        
        self.session_data[self.session_id]['stream_configs'].append(stream_config)
        self._save_session()
    
    def get_stream_configs(self):
        """Ambil semua konfigurasi stream untuk session ini"""
        if self.session_id in self.session_data:
            return self.session_data[self.session_id].get('stream_configs', [])
        return []
    
    def save_streaming_status(self, status_data):
        """Simpan status streaming"""
        if self.session_id not in self.session_data:
            self.session_data[self.session_id] = {}
        
        self.session_data[self.session_id]['streaming_status'] = {
            'status': status_data,
            'updated_at': datetime.now(JAKARTA_TZ).isoformat()
        }
        self._save_session()
    
    def get_streaming_status(self):
        """Ambil status streaming"""
        if self.session_id in self.session_data:
            return self.session_data[self.session_id].get('streaming_status')
        return None
    
    def save_form_data(self, form_name, form_data):
        """Simpan data form untuk recovery"""
        if self.session_id not in self.session_data:
            self.session_data[self.session_id] = {}
        
        if 'form_data' not in self.session_data[self.session_id]:
            self.session_data[self.session_id]['form_data'] = {}
        
        self.session_data[self.session_id]['form_data'][form_name] = {
            'data': form_data,
            'saved_at': datetime.now(JAKARTA_TZ).isoformat()
        }
        self._save_session()
    
    def get_form_data(self, form_name):
        """Ambil data form yang tersimpan"""
        if self.session_id in self.session_data:
            form_data = self.session_data[self.session_id].get('form_data', {})
            return form_data.get(form_name, {}).get('data')
        return None
    
    def clear_current_broadcast(self):
        """Hapus data broadcast yang sedang aktif"""
        if self.session_id in self.session_data:
            if 'current_broadcast' in self.session_data[self.session_id]:
                del self.session_data[self.session_id]['current_broadcast']
            self._save_session()
        
        # Clear from session state
        if 'new_stream_data' in st.session_state:
            del st.session_state.new_stream_data
    
    def restore_session_state(self):
        """Restore session state dari data yang tersimpan"""
        try:
            # Restore broadcast data
            current_broadcast = self.get_current_broadcast()
            if current_broadcast and 'new_stream_data' not in st.session_state:
                st.session_state.new_stream_data = current_broadcast['data']
            
            # Restore streaming status
            streaming_status = self.get_streaming_status()
            if streaming_status:
                status = streaming_status['status']
                st.session_state.streaming_active = status.get('active', False)
                
        except Exception as e:
            st.error(f"Error restoring session: {e}")
    
    def get_session_info(self):
        """Ambil informasi session"""
        if self.session_id in self.session_data:
            session_info = self.session_data[self.session_id]
            return {
                'session_id': self.session_id,
                'last_updated': session_info.get('last_updated'),
                'has_broadcast': 'current_broadcast' in session_info,
                'stream_configs_count': len(session_info.get('stream_configs', [])),
                'has_streaming_status': 'streaming_status' in session_info,
                'form_data_count': len(session_info.get('form_data', {}))
            }
        return {'session_id': self.session_id}
    
    def cleanup_old_sessions(self, hours=24):
        """Bersihkan session lama"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            cleaned_data = {}
            cleaned_count = 0
            
            for session_id, session_info in self.session_data.items():
                if session_info.get('last_updated', 0) >= cutoff_time:
                    cleaned_data[session_id] = session_info
                else:
                    cleaned_count += 1
            
            self.session_data = cleaned_data
            self._save_session()
            
            return cleaned_count
            
        except Exception as e:
            st.error(f"Error cleaning sessions: {e}")
            return 0
    
    def export_session(self):
        """Export session data untuk backup"""
        try:
            if self.session_id in self.session_data:
                export_data = {
                    'session_id': self.session_id,
                    'exported_at': datetime.now(JAKARTA_TZ).isoformat(),
                    'data': self.session_data[self.session_id]
                }
                return json.dumps(export_data, indent=2, ensure_ascii=False)
            return None
        except Exception as e:
            st.error(f"Error exporting session: {e}")
            return None
    
    def import_session(self, session_json):
        """Import session data dari backup"""
        try:
            import_data = json.loads(session_json)
            imported_session_id = import_data['session_id']
            
            self.session_data[imported_session_id] = import_data['data']
            self._save_session()
            
            return imported_session_id
            
        except Exception as e:
            st.error(f"Error importing session: {e}")
            return None

# Global session manager instance
def get_session_manager():
    """Get atau create session manager instance"""
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = LiveSession()
    return st.session_state.session_manager

# Helper functions untuk integrasi mudah
def save_broadcast_to_session(broadcast_data):
    """Helper function untuk save broadcast data"""
    session_manager = get_session_manager()
    session_manager.save_broadcast_data(broadcast_data)

def get_broadcast_from_session():
    """Helper function untuk get broadcast data"""
    session_manager = get_session_manager()
    return session_manager.get_current_broadcast()

def clear_broadcast_from_session():
    """Helper function untuk clear broadcast data"""
    session_manager = get_session_manager()
    session_manager.clear_current_broadcast()

def restore_session():
    """Helper function untuk restore session state"""
    session_manager = get_session_manager()
    session_manager.restore_session_state()

def save_form_to_session(form_name, form_data):
    """Helper function untuk save form data"""
    session_manager = get_session_manager()
    session_manager.save_form_data(form_name, form_data)

def get_form_from_session(form_name):
    """Helper function untuk get form data"""
    session_manager = get_session_manager()
    return session_manager.get_form_data(form_name)

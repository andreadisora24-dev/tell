import json
import time
import secrets
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)

class SecureSessionManager:
    """Secure session management with database storage and timeout handling"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.session_timeout = config.SESSION_TIMEOUT
        
    def create_session(self, user_id: int, session_data: Dict[str, Any] = None) -> str:
        """Create a new secure session for user"""
        session_token = secrets.token_urlsafe(32)
        session_data = session_data or {}
        
        # Add session metadata
        session_data.update({
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'session_token': session_token,
            'user_id': user_id
        })
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_sessions 
                    (user_id, session_data, last_activity)
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    json.dumps(session_data),
                    datetime.now()
                ))
                conn.commit()
                
            logger.info(f"Created secure session for user {user_id}")
            return session_token
            
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}")
            return None
    
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user session if valid and not expired"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT session_data, last_activity 
                    FROM user_sessions 
                    WHERE user_id = ?
                """, (user_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                session_data_str, last_activity = result
                session_data = json.loads(session_data_str)
                
                # Check if session is expired
                last_activity_time = datetime.fromisoformat(session_data.get('last_activity'))
                if datetime.now() - last_activity_time > timedelta(seconds=self.session_timeout):
                    # Session expired, remove it
                    self.destroy_session(user_id)
                    logger.info(f"Session expired for user {user_id}")
                    return None
                
                # Update last activity
                self.update_session_activity(user_id)
                return session_data
                
        except Exception as e:
            logger.error(f"Error getting session for user {user_id}: {e}")
            return None
    
    def update_session(self, user_id: int, session_data: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            # Update last activity
            session_data['last_activity'] = datetime.now().isoformat()
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions 
                    SET session_data = ?, last_activity = ?
                    WHERE user_id = ?
                """, (
                    json.dumps(session_data),
                    datetime.now(),
                    user_id
                ))
                conn.commit()
                
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error updating session for user {user_id}: {e}")
            return False
    
    def update_session_activity(self, user_id: int) -> bool:
        """Update session last activity timestamp"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions 
                    SET last_activity = ?
                    WHERE user_id = ?
                """, (datetime.now(), user_id))
                conn.commit()
                
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error updating session activity for user {user_id}: {e}")
            return False
    
    def destroy_session(self, user_id: int) -> bool:
        """Destroy user session"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                
            logger.info(f"Destroyed session for user {user_id}")
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error destroying session for user {user_id}: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from database"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.session_timeout)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE last_activity < ?
                """, (cutoff_time,))
                conn.commit()
                
            cleaned_count = cursor.rowcount
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    def get_session_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get session information for admin purposes"""
        session = self.get_session(user_id)
        if not session:
            return None
        
        return {
            'user_id': user_id,
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity'),
            'session_age': str(datetime.now() - datetime.fromisoformat(session.get('created_at', datetime.now().isoformat()))),
            'time_until_expiry': str(timedelta(seconds=self.session_timeout) - (datetime.now() - datetime.fromisoformat(session.get('last_activity', datetime.now().isoformat()))))
        }
    
    def validate_session_token(self, user_id: int, token: str) -> bool:
        """Validate session token for additional security"""
        session = self.get_session(user_id)
        if not session:
            return False
        
        stored_token = session.get('session_token')
        if not stored_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(stored_token, token)
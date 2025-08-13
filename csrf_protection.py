import secrets
import hashlib
import time
from typing import Dict, Optional, Set
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from secure_logging import SecureLogger

class CSRFProtection:
    """CSRF protection for admin functions"""
    
    def __init__(self, token_expiry: int = 3600):  # 1 hour default
        self.tokens: Dict[str, Dict] = {}  # token -> {user_id, created_at, action}
        self.user_tokens: Dict[int, Set[str]] = {}  # user_id -> set of tokens
        self.token_expiry = token_expiry
    
    def generate_token(self, user_id: int, action: str) -> str:
        """Generate a CSRF token for a specific user and action"""
        # Create a unique token
        token_data = f"{user_id}:{action}:{time.time()}:{secrets.token_hex(16)}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        # Store token information
        self.tokens[token] = {
            'user_id': user_id,
            'action': action,
            'created_at': time.time()
        }
        
        # Track user tokens
        if user_id not in self.user_tokens:
            self.user_tokens[user_id] = set()
        self.user_tokens[user_id].add(token)
        
        # Clean up expired tokens
        self._cleanup_expired_tokens()
        
        SecureLogger.log_security_event(
            'csrf_token_generated',
            user_id=user_id,
            details={'action': action}
        )
        
        return token
    
    def validate_token(self, token: str, user_id: int, action: str) -> bool:
        """Validate a CSRF token"""
        if not token or token not in self.tokens:
            SecureLogger.log_security_event(
                'csrf_token_invalid',
                user_id=user_id,
                details={'action': action, 'reason': 'token_not_found'},
                severity='WARNING'
            )
            return False
        
        token_info = self.tokens[token]
        
        # Check if token belongs to the user
        if token_info['user_id'] != user_id:
            SecureLogger.log_security_event(
                'csrf_token_invalid',
                user_id=user_id,
                details={'action': action, 'reason': 'user_mismatch'},
                severity='WARNING'
            )
            return False
        
        # Check if token is for the correct action
        if token_info['action'] != action:
            SecureLogger.log_security_event(
                'csrf_token_invalid',
                user_id=user_id,
                details={'action': action, 'reason': 'action_mismatch'},
                severity='WARNING'
            )
            return False
        
        # Check if token has expired
        if time.time() - token_info['created_at'] > self.token_expiry:
            SecureLogger.log_security_event(
                'csrf_token_invalid',
                user_id=user_id,
                details={'action': action, 'reason': 'expired'},
                severity='INFO'
            )
            self._remove_token(token)
            return False
        
        # Token is valid - remove it (one-time use)
        self._remove_token(token)
        
        SecureLogger.log_security_event(
            'csrf_token_validated',
            user_id=user_id,
            details={'action': action}
        )
        
        return True
    
    def _remove_token(self, token: str):
        """Remove a token from storage"""
        if token in self.tokens:
            user_id = self.tokens[token]['user_id']
            del self.tokens[token]
            
            if user_id in self.user_tokens:
                self.user_tokens[user_id].discard(token)
                if not self.user_tokens[user_id]:
                    del self.user_tokens[user_id]
    
    def _cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        current_time = time.time()
        expired_tokens = [
            token for token, info in self.tokens.items()
            if current_time - info['created_at'] > self.token_expiry
        ]
        
        for token in expired_tokens:
            self._remove_token(token)
    
    def invalidate_user_tokens(self, user_id: int):
        """Invalidate all tokens for a specific user"""
        if user_id in self.user_tokens:
            tokens_to_remove = list(self.user_tokens[user_id])
            for token in tokens_to_remove:
                self._remove_token(token)
            
            SecureLogger.log_security_event(
                'csrf_tokens_invalidated',
                user_id=user_id,
                details={'count': len(tokens_to_remove)}
            )
    
    def create_protected_keyboard(self, user_id: int, buttons_config: list) -> InlineKeyboardMarkup:
        """Create an inline keyboard with CSRF protection"""
        keyboard = []
        
        for row in buttons_config:
            button_row = []
            for button_config in row:
                action = button_config['action']
                text = button_config['text']
                
                # Generate CSRF token for this action
                csrf_token = self.generate_token(user_id, action)
                
                # Create callback data with CSRF token
                callback_data = f"{action}:{csrf_token}"
                
                button_row.append(InlineKeyboardButton(text, callback_data=callback_data))
            
            keyboard.append(button_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def parse_callback_data(self, callback_data: str) -> tuple[str, str]:
        """Parse callback data to extract action and CSRF token"""
        if ':' not in callback_data:
            return callback_data, ''
        
        parts = callback_data.split(':', 1)
        return parts[0], parts[1] if len(parts) > 1 else ''

# Global CSRF protection instance
csrf_protection = CSRFProtection()

def csrf_protected(action: str):
    """Decorator to protect admin functions with CSRF tokens"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Check if user is admin
            if not self.is_admin(user_id):
                SecureLogger.log_security_event(
                    'csrf_unauthorized_access',
                    user_id=user_id,
                    details={'action': action},
                    severity='WARNING'
                )
                await update.callback_query.answer("❌ Unauthorized access", show_alert=True)
                return
            
            # Extract CSRF token from callback data
            if update.callback_query:
                callback_data = update.callback_query.data
                parsed_action, csrf_token = csrf_protection.parse_callback_data(callback_data)
                
                # Validate CSRF token
                if not csrf_protection.validate_token(csrf_token, user_id, action):
                    await update.callback_query.answer(
                        "❌ Security token invalid or expired. Please try again.", 
                        show_alert=True
                    )
                    return
            
            # Log admin action
            SecureLogger.log_admin_action(
                action=action,
                admin_id=user_id,
                details={'protected': True}
            )
            
            # Execute the protected function
            return await func(self, update, context, *args, **kwargs)
        
        return wrapper
    return decorator

def create_admin_keyboard(user_id: int, admin_actions: list) -> InlineKeyboardMarkup:
    """Create admin keyboard with CSRF protection"""
    buttons_config = []
    
    for action_config in admin_actions:
        if isinstance(action_config, list):
            # Row of buttons
            buttons_config.append(action_config)
        else:
            # Single button
            buttons_config.append([action_config])
    
    return csrf_protection.create_protected_keyboard(user_id, buttons_config)

def validate_admin_action(update: Update, expected_action: str) -> bool:
    """Validate admin action with CSRF protection"""
    if not update.callback_query:
        return False
    
    user_id = update.effective_user.id
    callback_data = update.callback_query.data
    
    action, csrf_token = csrf_protection.parse_callback_data(callback_data)
    
    if action != expected_action:
        return False
    
    return csrf_protection.validate_token(csrf_token, user_id, expected_action)

# Security monitoring functions
def monitor_csrf_attacks():
    """Monitor for potential CSRF attacks"""
    # This could be expanded to detect patterns of CSRF failures
    pass

def get_csrf_stats() -> Dict:
    """Get CSRF protection statistics"""
    return {
        'active_tokens': len(csrf_protection.tokens),
        'users_with_tokens': len(csrf_protection.user_tokens),
        'token_expiry': csrf_protection.token_expiry
    }
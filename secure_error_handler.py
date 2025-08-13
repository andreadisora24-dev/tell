import logging
import traceback
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from translations import get_text

logger = logging.getLogger(__name__)

class SecureErrorHandler:
    """Secure error handling to prevent information disclosure"""
    
    # Safe error messages that don't reveal system information
    SAFE_ERROR_MESSAGES = {
        'generic': '❌ An unexpected error occurred. Please try again later.',
        'database': '❌ Database temporarily unavailable. Please try again.',
        'network': '❌ Network error. Please check your connection.',
        'validation': '❌ Invalid input provided. Please check your data.',
        'permission': '❌ You don\'t have permission to perform this action.',
        'rate_limit': '⚠️ Too many requests. Please wait before trying again.',
        'session': '❌ Your session has expired. Please start again with /start',
        'maintenance': '🔧 System is under maintenance. Please try again later.',
        'file_upload': '❌ File upload failed. Please try again with a valid file.',
        'payment': '❌ Payment processing error. Please try again or contact support.'
    }
    
    # Sensitive keywords that should never appear in user-facing messages
    SENSITIVE_KEYWORDS = [
        'traceback', 'exception', 'stack trace', 'internal error',
        'database error', 'sql', 'connection string', 'password',
        'token', 'secret', 'key', 'credential', 'auth', 'debug',
        'file path', 'directory', 'system', 'server', 'localhost',
        'admin', 'root', 'config', 'environment', 'variable'
    ]
    
    @staticmethod
    def sanitize_error_message(error_message: str, error_type: str = 'generic') -> str:
        """Sanitize error message to prevent information disclosure"""
        if not error_message:
            return SecureErrorHandler.SAFE_ERROR_MESSAGES['generic']
        
        # Convert to lowercase for checking
        error_lower = error_message.lower()
        
        # Check for sensitive keywords
        for keyword in SecureErrorHandler.SENSITIVE_KEYWORDS:
            if keyword in error_lower:
                logger.warning(f"Sensitive keyword '{keyword}' found in error message, sanitizing")
                return SecureErrorHandler.SAFE_ERROR_MESSAGES.get(error_type, 
                                                                SecureErrorHandler.SAFE_ERROR_MESSAGES['generic'])
        
        # If message seems safe, return sanitized version
        if len(error_message) > 100:  # Truncate very long messages
            return SecureErrorHandler.SAFE_ERROR_MESSAGES.get(error_type, 
                                                            SecureErrorHandler.SAFE_ERROR_MESSAGES['generic'])
        
        return error_message
    
    @staticmethod
    def log_error_securely(error: Exception, context: Dict[str, Any] = None, user_id: int = None):
        """Log error with full details for debugging while keeping user messages safe"""
        context = context or {}
        
        # Create detailed log entry for developers
        log_entry = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user_id': user_id,
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        # Log full error details for debugging
        logger.error(f"Secure Error Log: {log_entry}")
        
        # Also log to a separate security log if needed
        security_logger = logging.getLogger('security')
        security_logger.error(f"Error for user {user_id}: {type(error).__name__}")
    
    @staticmethod
    async def handle_bot_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             error: Exception, error_type: str = 'generic') -> bool:
        """Handle bot errors securely"""
        user_id = update.effective_user.id if update.effective_user else None
        
        # Log the full error details securely
        SecureErrorHandler.log_error_securely(
            error, 
            context={'update_type': type(update).__name__}, 
            user_id=user_id
        )
        
        # Get safe error message
        safe_message = SecureErrorHandler.SAFE_ERROR_MESSAGES.get(error_type, 
                                                                SecureErrorHandler.SAFE_ERROR_MESSAGES['generic'])
        
        # Try to send error message to user
        try:
            if update.callback_query:
                await update.callback_query.answer(safe_message, show_alert=True)
            elif update.message:
                await update.message.reply_text(safe_message)
            else:
                # Fallback for other update types
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=safe_message
                )
            return True
        except Exception as send_error:
            # If we can't send the error message, log it
            logger.error(f"Failed to send error message to user {user_id}: {send_error}")
            return False
    
    @staticmethod
    def create_safe_response(success: bool, message: str = None, data: Any = None, 
                           error_type: str = 'generic') -> Dict[str, Any]:
        """Create a safe API response that doesn't leak information"""
        if success:
            return {
                'success': True,
                'message': message or 'Operation completed successfully',
                'data': data
            }
        else:
            safe_message = SecureErrorHandler.sanitize_error_message(message or '', error_type)
            return {
                'success': False,
                'message': safe_message,
                'data': None
            }
    
    @staticmethod
    def is_admin_context(user_id: int, admin_ids: list) -> bool:
        """Check if user is admin for detailed error reporting"""
        return user_id in admin_ids
    
    @staticmethod
    async def handle_database_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  error: Exception, user_id: int = None, admin_ids: list = None) -> bool:
        """Handle database errors with appropriate detail level"""
        admin_ids = admin_ids or []
        user_id = user_id or (update.effective_user.id if update.effective_user else None)
        
        # Log full error details
        SecureErrorHandler.log_error_securely(error, {'operation': 'database'}, user_id)
        
        # Provide different messages for admins vs regular users
        if user_id and SecureErrorHandler.is_admin_context(user_id, admin_ids):
            message = f"🔧 Database Error (Admin): {type(error).__name__}\nCheck logs for details."
        else:
            message = SecureErrorHandler.SAFE_ERROR_MESSAGES['database']
        
        return await SecureErrorHandler._send_error_message(update, message)
    
    @staticmethod
    async def _send_error_message(update: Update, message: str) -> bool:
        """Internal method to send error message"""
        try:
            if update.callback_query:
                await update.callback_query.answer(message, show_alert=True)
            elif update.message:
                await update.message.reply_text(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
            return False

# Decorator for secure error handling
def secure_error_handler(error_type: str = 'generic'):
    """Decorator to add secure error handling to bot methods"""
    def decorator(func):
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                return await func(self, update, context, *args, **kwargs)
            except Exception as e:
                await SecureErrorHandler.handle_bot_error(update, context, e, error_type)
                return None
        return wrapper
    return decorator
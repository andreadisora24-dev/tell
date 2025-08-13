"""Base handler class with common functionality for TeleShop Bot."""

import logging
from typing import Dict, Optional
from telegram import Update, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import DatabaseManager
from captcha import CaptchaManager
from translations import get_text
from utils import format_currency, validate_coordinates
from promo_image_generator import promo_generator
from rate_limiter import rate_limit_check
from session_manager import SecureSessionManager
from secure_error_handler import secure_error_handler
from secure_logging import SecureLogger
from csrf_protection import csrf_protected, create_admin_keyboard
from secure_config import get_config
from auto_cleanup import AutoCleanupManager

logger = logging.getLogger(__name__)

class BaseHandler:
    """Base handler class with common functionality."""
    
    def __init__(self, db: DatabaseManager, captcha: CaptchaManager, 
                 session_manager: SecureSessionManager, auto_cleanup: AutoCleanupManager,
                 config: Dict, bot_instance=None):
        self.db = db
        self.captcha = captcha
        self.session_manager = session_manager
        self.auto_cleanup = auto_cleanup
        self.config = config
        self.bot_instance = bot_instance
        self.application = None  # Will be set by main bot
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        import config
        return user_id in config.ADMIN_IDS
    
    async def clear_chat_and_send_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     text: str, reply_markup: InlineKeyboardMarkup, 
                                     use_banner: bool = False):
        """Helper function to clear chat and send menu with or without banner"""
        try:
            # Delete the last 100 messages to clear chat
            for i in range(100):
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=update.callback_query.message.message_id - i
                    )
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error clearing chat: {e}")
        
        # Send new menu
        await self.send_menu_with_banner(update, context, text, reply_markup, use_banner)
    
    async def _clear_previous_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear previous messages to prevent chat clutter - optimized to avoid unnecessary API calls"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Delete tracked messages first
            if hasattr(self, 'auto_cleanup') and user_id in self.auto_cleanup.user_messages:
                for message_id in self.auto_cleanup.user_messages[user_id].copy():
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=message_id
                        )
                    except Exception:
                        pass
                # Clear the tracked messages list
                self.auto_cleanup.user_messages[user_id].clear()
            
            # Smart deletion: stop after consecutive failures to avoid lag
            if hasattr(update, 'callback_query') and update.callback_query:
                current_message_id = update.callback_query.message.message_id
                consecutive_failures = 0
                max_consecutive_failures = 3  # Stop after 3 consecutive failures
                max_messages_to_check = 20    # Limit total messages to check
                
                for i in range(max_messages_to_check):
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=current_message_id - i
                        )
                        consecutive_failures = 0  # Reset counter on success
                    except Exception:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            # Stop trying if we hit too many consecutive failures
                            break
                        
        except Exception as e:
            logger.warning(f"Error clearing previous messages: {e}")
    
    async def send_menu_with_banner(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, 
                                  reply_markup: InlineKeyboardMarkup, use_banner: bool = True):
        """Send menu with optional banner - always clears previous messages"""
        try:
            # Always clear previous messages to prevent chat clutter
            await self._clear_previous_messages(update, context)
            
            if use_banner:
                try:
                    with open('banner.jpg', 'rb') as banner_file:
                        message = await update.effective_chat.send_photo(
                            photo=banner_file,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                        )
                        
                        # Track message for auto-cleanup
                        if hasattr(self, 'auto_cleanup'):
                            self.auto_cleanup.track_message(
                                update.effective_user.id,
                                update.effective_chat.id,
                                message.message_id
                            )
                        return
                except FileNotFoundError:
                    logger.warning("Banner file not found, sending text message instead")
            
            # Send text message if banner not available or not requested
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            # Track message for auto-cleanup
            if hasattr(self, 'auto_cleanup'):
                self.auto_cleanup.track_message(
                    update.effective_user.id,
                    update.effective_chat.id,
                    message.message_id
                )
                    
        except Exception as e:
            logger.error(f"Error sending menu: {e}")
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer("❌ Error sending menu", show_alert=True)
    
    async def send_message_with_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                      text: str, reply_markup: InlineKeyboardMarkup = None, 
                                      photo_path: str = None, caption: str = None):
        """Send message with automatic cleanup of previous messages"""
        try:
            # Clear previous messages first
            await self._clear_previous_messages(update, context)
            
            user_id = update.effective_user.id
            
            if photo_path:
                # Send photo message
                try:
                    with open(photo_path, 'rb') as photo:
                        message = await update.effective_chat.send_photo(
                            photo=photo,
                            caption=caption or text,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                        )
                except FileNotFoundError:
                    logger.warning(f"Photo file not found: {photo_path}, sending text instead")
                    message = await update.effective_chat.send_message(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
            else:
                # Send text message
                message = await update.effective_chat.send_message(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            
            # Track message for auto-cleanup
            self.auto_cleanup.track_message(user_id, update.effective_chat.id, message.message_id, update)
            return message
            
        except Exception as e:
            logger.error(f"Error in send_message_with_cleanup: {e}")
            raise

    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language"""
        user = self.db.get_user(user_id)
        return user.get('language', self.config.get('default_language', 'en')) if user else 'en'
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception):
        """Handle errors with secure logging"""
        SecureLogger.log_security_event(
            'handler_error',
            details={
                'error': str(error),
                'user_id': update.effective_user.id if update.effective_user else None,
                'handler': self.__class__.__name__
            }
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.answer("❌ An error occurred", show_alert=True)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ An error occurred. Please try again."
            )
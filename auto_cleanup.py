import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden

import config
from translations import get_text
from secure_config import get_config

logger = logging.getLogger(__name__)

class AutoCleanupManager:
    """Manages automatic chat cleanup after user inactivity"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        self.user_messages: Dict[int, List[int]] = {}  # user_id -> [message_ids]
        self.user_last_activity: Dict[int, datetime] = {}  # user_id -> last_activity_time
        self.cleanup_tasks: Dict[int, asyncio.Task] = {}  # user_id -> cleanup_task
        self.cleanup_timeout = int(get_config('AUTO_CLEANUP_TIMEOUT', config.AUTO_CLEANUP_TIMEOUT))
        self.enabled = get_config('WELCOME_CLEANUP_ENABLED', config.WELCOME_CLEANUP_ENABLED)
        
        # Customizable welcome content
        self.public_chat_link = get_config('PUBLIC_CHAT_LINK', 'https://t.me/your_public_chat')
        self.news_channel_link = get_config('NEWS_CHANNEL_LINK', 'https://t.me/your_news_channel')
        self.custom_news = get_config('CUSTOM_NEWS', '📢 Check out our latest updates!')
        
    def track_message(self, user_id: int, chat_id: int, message_id: int, update: Update = None):
        """Track a message for potential cleanup"""
        if not self.enabled:
            return
            
        # Initialize user tracking if not exists
        if user_id not in self.user_messages:
            self.user_messages[user_id] = []
            
        # Add message to tracking
        self.user_messages[user_id].append(message_id)
        
        # Update last activity
        self.user_last_activity[user_id] = datetime.now()
        
        # Cancel existing cleanup task if any
        if user_id in self.cleanup_tasks:
            self.cleanup_tasks[user_id].cancel()
            
        # Schedule new cleanup task
        if update:
            task = asyncio.create_task(
                self._schedule_cleanup(user_id, update.effective_chat.id)
            )
            self.cleanup_tasks[user_id] = task
            
    def update_activity(self, user_id: int, update: Update = None):
        """Update user activity without tracking a specific message"""
        if not self.enabled:
            return
            
        self.user_last_activity[user_id] = datetime.now()
        
        # Cancel existing cleanup task
        if user_id in self.cleanup_tasks:
            self.cleanup_tasks[user_id].cancel()
            
        # Schedule new cleanup task
        if update:
            task = asyncio.create_task(
                self._schedule_cleanup(user_id, update.effective_chat.id)
            )
            self.cleanup_tasks[user_id] = task
            
    async def _schedule_cleanup(self, user_id: int, chat_id: int):
        """Schedule cleanup after timeout period"""
        try:
            await asyncio.sleep(self.cleanup_timeout)
            
            # Check if user is still inactive
            last_activity = self.user_last_activity.get(user_id)
            if last_activity and datetime.now() - last_activity >= timedelta(seconds=self.cleanup_timeout):
                await self._perform_cleanup(user_id, chat_id)
                
        except asyncio.CancelledError:
            # Task was cancelled due to user activity
            pass
        except Exception as e:
            logger.error(f"Error in cleanup scheduler for user {user_id}: {e}")
            
    async def _perform_cleanup(self, user_id: int, chat_id: int):
        """Perform the actual cleanup and send welcome message"""
        try:
            # Delete tracked messages
            if user_id in self.user_messages:
                for message_id in self.user_messages[user_id]:
                    try:
                        await self.bot.application.bot.delete_message(
                            chat_id=chat_id,
                            message_id=message_id
                        )
                    except (BadRequest, Forbidden):
                        # Message might already be deleted or bot lacks permissions
                        pass
                        
                # Clear tracked messages
                self.user_messages[user_id] = []
                
            # Check if user exists in database
            user = self.db.get_user(user_id)
            
            if user:
                # Send welcome back message for existing user
                await self._send_welcome_back_message(chat_id, user)
            else:
                # Send new user welcome with captcha
                await self._send_new_user_welcome(chat_id, user_id)
                
            # Clean up tracking data
            if user_id in self.cleanup_tasks:
                del self.cleanup_tasks[user_id]
            if user_id in self.user_last_activity:
                del self.user_last_activity[user_id]
                
        except Exception as e:
            logger.error(f"Error performing cleanup for user {user_id}: {e}")
            
    async def _send_welcome_back_message(self, chat_id: int, user: Dict):
        """Send welcome back message for existing users"""
        lang = user.get('language', 'en')
        username = user.get('username', 'User')
        bot_name = self.bot.config.get('bot_name', 'TeleShop')
        
        # Clear chat first
        await self._clear_chat(chat_id)
        
        # Create welcome message
        welcome_text = f"""
🎉 <b>Hi {username}!</b>

🏪 Welcome back to <b>{bot_name}</b>!

{self.custom_news}

🔗 <b>Quick Links:</b>
• 💬 <a href="{self.public_chat_link}">Join our Public Chat</a>
• 📢 <a href="{self.news_channel_link}">News & Updates</a>

💰 Your Balance: {user.get('balance', 0)} PLN
🎯 Your Discount: {user.get('discount', 0)}%

👆 Click START to access the main menu!
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 START", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Try to send with banner
            try:
                with open('banner.jpg', 'rb') as banner:
                    await self.bot.application.bot.send_photo(
                        chat_id=chat_id,
                        photo=banner,
                        caption=welcome_text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
            except FileNotFoundError:
                # Fallback without banner
                await self.bot.application.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error sending welcome back message: {e}")
    
    async def _clear_chat(self, chat_id: int):
        """Clear chat by deleting recent messages"""
        try:
            user_id = chat_id  # In private chats, chat_id equals user_id
            
            # Get tracked messages for this user
            if user_id in self.user_messages:
                messages_to_delete = list(self.user_messages[user_id])
                
                # Delete tracked messages
                for message_id in messages_to_delete:
                    try:
                        await self.bot.application.bot.delete_message(
                            chat_id=chat_id,
                            message_id=message_id
                        )
                    except Exception:
                        # Continue if message doesn't exist or can't be deleted
                        continue
                
                # Clear the tracked messages
                self.user_messages[user_id].clear()
            
            # Also try to delete recent messages by attempting a range
            # Get a reasonable starting point by sending a test message and deleting it
            try:
                test_msg = await self.bot.application.bot.send_message(
                    chat_id=chat_id,
                    text="."
                )
                current_msg_id = test_msg.message_id
                await self.bot.application.bot.delete_message(chat_id, current_msg_id)
                
                # Delete previous 50 messages from current position
                for i in range(1, 51):
                    try:
                        await self.bot.application.bot.delete_message(
                            chat_id=chat_id,
                            message_id=current_msg_id - i
                        )
                    except Exception:
                        continue
            except Exception:
                pass
                
        except Exception as e:
            logger.debug(f"Chat clearing completed: {e}")
            
    async def _send_new_user_welcome(self, chat_id: int, user_id: int):
        """Send welcome message for new users with captcha requirement"""
        bot_name = self.bot.config.get('bot_name', 'TeleShop')
        
        welcome_text = f"""
🎉 <b>Welcome to {bot_name}!</b>

{self.custom_news}

🔗 <b>Quick Links:</b>
• 💬 <a href="{self.public_chat_link}">Join our Public Chat</a>
• 📢 <a href="{self.news_channel_link}">News & Updates</a>

🔐 <b>Security Check Required</b>
To get started, you'll need to complete a quick verification.

👆 Click START to begin!
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 START", callback_data="start_verification")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Try to send with banner
            try:
                with open('banner.jpg', 'rb') as banner:
                    await self.bot.application.bot.send_photo(
                        chat_id=chat_id,
                        photo=banner,
                        caption=welcome_text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
            except FileNotFoundError:
                # Fallback without banner
                await self.bot.application.bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error sending new user welcome message: {e}")
            
    def cancel_cleanup(self, user_id: int):
        """Cancel cleanup task for a user"""
        if user_id in self.cleanup_tasks:
            self.cleanup_tasks[user_id].cancel()
            del self.cleanup_tasks[user_id]
            
    def clear_user_data(self, user_id: int):
        """Clear all tracking data for a user"""
        if user_id in self.user_messages:
            del self.user_messages[user_id]
        if user_id in self.user_last_activity:
            del self.user_last_activity[user_id]
        self.cancel_cleanup(user_id)
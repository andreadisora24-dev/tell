"""User handler module for TeleShop Bot.

Handles user-related functionality including:
- Start command and user registration
- Captcha verification
- Main menu display
- Promo code processing
"""

import asyncio
import logging
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .base_handler import BaseHandler
from translations import get_text
from utils import format_currency
from rate_limiter import rate_limit_check

logger = logging.getLogger(__name__)

class UserHandler(BaseHandler):
    """Handler for user-related functionality."""
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, data: str):
        """Handle user-related callbacks"""
        if data == "menu_main":
            await self.show_main_menu(update, context, user)
        elif data == "start_verification":
            await self.show_captcha(update, context)
        else:
            logger.warning(f"Unhandled user callback: {data}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Update user activity for auto-cleanup
        self.auto_cleanup.update_activity(user_id, update)
        
        # Check if user exists in database
        user = self.db.get_user(user_id)
        
        if not user:
            # New user - show captcha
            await self.show_captcha(update, context)
        else:
            # Existing user - show main menu
            await self.show_main_menu(update, context, user)
    
    async def show_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show captcha challenge for new users"""
        user_id = update.effective_user.id
        captcha_data = self.captcha.generate_captcha()
        
        # Update user activity for auto-cleanup
        self.auto_cleanup.update_activity(user_id, update)
        
        # Store captcha in secure session
        session_data = {
            'captcha_answer': captcha_data['correct_answer'],
            'captcha_type': captcha_data['type']
        }
        self.session_manager.create_session(user_id, session_data)
        
        # Send captcha image with instructions
        message = await update.message.reply_photo(
            photo=captcha_data['image_data'],
            caption=get_text('security_verification', 'en') + "\n\n" + captcha_data['question'] + "\n\n" + get_text('captcha_hint', 'en'),
            parse_mode=ParseMode.HTML
        )
        # Track message for auto-cleanup
        self.auto_cleanup.track_message(user_id, message.message_id, update)
    
    async def handle_captcha_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle captcha response"""
        user_id = update.effective_user.id
        
        # Update user activity for auto-cleanup
        self.auto_cleanup.update_activity(user_id, update)
        
        # Handle captcha response
        session = self.session_manager.get_session(user_id)
        if not session:
            message = await update.message.reply_text(get_text('session_expired', 'en'))
            self.auto_cleanup.track_message(user_id, message.message_id, update)
            return
        user_answer = update.message.text.strip()
        
        # Verify captcha using the new method
        if self.captcha.verify_answer(user_answer, session['captcha_answer']):
            # Correct answer - create user and show menu
            self.session_manager.destroy_session(user_id)  # Clean up session
            await self.create_user_and_show_menu(update, context)
        else:
            # Wrong answer - show new captcha
            message = await update.message.reply_text(get_text('captcha_incorrect', 'en'))
            self.auto_cleanup.track_message(user_id, message.message_id, update)
            await self.show_captcha(update, context)
    
    async def create_user_and_show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create new user and show main menu with loading animation"""
        user_id = update.effective_user.id
        username = update.effective_user.username or get_text('unknown_user', 'en')
        
        # Update user activity for auto-cleanup
        self.auto_cleanup.update_activity(user_id, update)
        
        # Delete all previous messages
        try:
            for i in range(10):  # Delete last 10 messages
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.effective_message.message_id - i
                )
        except:
            pass
        
        # Create user in database
        success = self.db.create_user(user_id, username)
        if not success:
            await self.send_message_with_cleanup(update, context, get_text('error_creating_user', 'en'))
            return
            
        user = self.db.get_user(user_id)
        if not user:
            await self.send_message_with_cleanup(update, context, get_text('error_user_not_found', 'en'))
            return
        
        # Clean up session
        self.session_manager.destroy_session(user_id)
        
        await self.show_main_menu(update, context, user)
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, force_new_message: bool = False):
        """Show main menu with user info and options"""
        lang = user.get('language', 'en')
        user_id = user['user_id']
        
        # Update user activity for auto-cleanup
        self.auto_cleanup.update_activity(user_id, update)
        
        # Create beautiful main menu with dynamic bot name
        bot_name = self.config.get('bot_name', 'TELESHOP')
        menu_text = f"""
🏪 <b>{bot_name.upper()}</b> 🏪
{get_text('main_menu_separator', lang)}

{get_text('user_info', lang)}
{get_text('user_id', lang).format(user['user_id'])}
{get_text('balance', lang).format(format_currency(user['balance']))}
{get_text('discount', lang).format(user['discount'])}
{get_text('member_since', lang).format(user['created_at'][:10])}

{get_text('main_menu_separator', lang)}
{get_text('choose_option', lang)}
        """
        
        keyboard = [
             [InlineKeyboardButton(get_text('btn_buy', lang), callback_data="menu_buy")],
             [InlineKeyboardButton(get_text('btn_wallet', lang), callback_data="menu_wallet")],
             [InlineKeyboardButton(get_text('btn_history', lang), callback_data="menu_history")],
             [InlineKeyboardButton(get_text('btn_help', lang), callback_data="menu_help")],
             [InlineKeyboardButton(get_text('btn_language', lang), callback_data="menu_language")]
         ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Use centralized message sending with auto-cleanup
        await self.send_message_with_cleanup(
            update, context, menu_text, reply_markup, 
            photo_path='banner.jpg', caption=menu_text
        )
    
    async def process_promo_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str):
        """Process promo code redemption"""
        lang = user.get('language', 'en')
        
        # First check if promo code exists and get its type
        promo_info = self.db.get_promo_code_info(promo_code)
        
        if not promo_info:
            error_text = f"{get_text('invalid_promo_title', lang)}\n\n{get_text('promo_error_default', lang)}"
            await update.message.reply_text(error_text, parse_mode=ParseMode.HTML)
            # Return to wallet menu
            await self.show_wallet(update, context, user)
            return
        
        # Handle different promo types
        if promo_info['type'] == 'discount':
            # Store discount code for use during checkout
            context.user_data['saved_discount_code'] = {
                'code': promo_code,
                'percentage': promo_info['value'],
                'expires_at': promo_info['expires_at']
            }
            
            success_text = f"🎫 <b>Discount Code Saved!</b>\n\n💸 {promo_info['value']}% discount code saved successfully!\n\n✅ This code is now ready to use during checkout.\n\n💡 When making a purchase, click 'Use Promo Code' to apply your {promo_info['value']}% discount!"
            await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
            # Return to wallet menu
            await self.show_wallet(update, context, user)
            return
        
        # Handle balance promo codes (existing logic)
        result = self.db.redeem_promo_code(user['user_id'], promo_code, lang)
        
        if result['success']:
            # Update user balance
            new_balance = user['balance'] + result['amount']
            self.db.set_user_balance(user['user_id'], new_balance)
            
            success_text = f"""{get_text('promo_redeemed_title', lang)}

{get_text('promo_code_label', lang).format(promo_code)}
{get_text('promo_amount_label', lang).format(format_currency(result['amount']))}
{get_text('promo_new_balance', lang).format(format_currency(new_balance))}"""
            
            await update.message.reply_text(success_text, parse_mode=ParseMode.HTML)
            user['balance'] = new_balance
        else:
            error_text = f"{get_text('invalid_promo_title', lang)}\n\n{result.get('error', get_text('promo_error_default', lang))}"
            await update.message.reply_text(error_text, parse_mode=ParseMode.HTML)
        
        # Return to wallet menu after a delay
        await asyncio.sleep(0.5)
        await self.show_wallet(update, context, user)
    
    # Note: show_wallet method will be implemented in a separate handler or moved to appropriate module
    async def show_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Placeholder for wallet functionality - to be implemented in wallet handler"""
        pass
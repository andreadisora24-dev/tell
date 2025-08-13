import logging
import asyncio
import json
import os
import random
import string
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

import config
from database import DatabaseManager
from captcha import CaptchaManager
from session_manager import SecureSessionManager
from secure_error_handler import SecureErrorHandler, secure_error_handler
from secure_logging import SecureLogger, monitor_performance
from secure_config import secure_config, get_secret, get_config
from auto_cleanup import AutoCleanupManager
from rate_limiter import rate_limit_check
from translations import get_text
from utils import format_currency
from promo_image_generator import promo_generator

# Import modular handlers
from handlers.user_handler import UserHandler
from handlers.admin_handler import AdminHandler
from handlers.shop_handler import ShopHandler
from handlers.crypto_handler import CryptoPaymentHandler
from handlers.order_handler import OrderHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TeleShopBot:
    def __init__(self):
        # Initialize secure configuration
        self._init_security()
        
        # Initialize core components with secure config
        database_path = get_config('DATABASE_PATH', config.DATABASE_PATH)
        self.db = DatabaseManager(database_path)
        self.captcha = CaptchaManager()
        self.session_manager = SecureSessionManager(self.db)
        self.auto_cleanup = AutoCleanupManager(self)
        
        # Bot configuration with secure defaults
        self.config = {
            "bot_name": get_config('BOT_NAME', "TeleShop"),
            "bot_description": get_config('BOT_DESCRIPTION', "Digital Store"),
            "admin_username": get_config('ADMIN_USERNAME', config.ADMIN_USERNAME),
            "support_contact": f"@{get_config('ADMIN_USERNAME', config.ADMIN_USERNAME)}",
            "welcome_message": get_config('WELCOME_MESSAGE', "Welcome to TeleShop!"),
            "currency_symbol": get_config('CURRENCY_SYMBOL', "zł"),
            "default_language": get_config('DEFAULT_LANGUAGE', config.DEFAULT_LANGUAGE),
            "maintenance_mode": get_config('MAINTENANCE_MODE', False),
            "max_orders_per_user": get_config('MAX_ORDERS_PER_USER', 10),
            "min_balance_required": get_config('MIN_BALANCE_REQUIRED', 0.0)
        }
        
        # Initialize modular handlers
        handler_config = {
            'admin_username': self.config['admin_username'],
            'support_contact': self.config['support_contact'],
            'currency_symbol': self.config['currency_symbol'],
            'default_language': self.config['default_language']
        }
        self.user_handler = UserHandler(self.db, self.captcha, self.session_manager, self.auto_cleanup, handler_config, self)
        self.admin_handler = AdminHandler(self.db, self.captcha, self.session_manager, self.auto_cleanup, handler_config, self)
        self.shop_handler = ShopHandler(self.db, self.captcha, self.session_manager, self.auto_cleanup, handler_config, self)
        self.order_handler = OrderHandler(self.db, self.captcha, self.session_manager, self.auto_cleanup, handler_config, self)
        self.crypto_handler = CryptoPaymentHandler(self)
        
        # Initialize security monitoring
        SecureLogger.log_security_event(
            'bot_initialized',
            details={'config_keys': list(self.config.keys())}
        )
    
    def _init_security(self):
        """Initialize security components"""
        try:
            # Setup secure logging
            SecureLogger.setup_secure_logging(
                log_level=get_config('LOG_LEVEL', 'INFO'),
                log_dir=get_config('LOG_DIR', 'logs')
            )
            
            # Log security initialization
            SecureLogger.log_security_event(
                'security_initialized',
                details={'environment': get_config('ENVIRONMENT', 'development')}
            )
            
        except Exception as e:
            logger.error(f"Security initialization failed: {e}")
            raise
    
    def save_bot_config(self):
        """Save bot configuration to bot_config.json"""
        try:
            with open('bot_config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving bot config: {e}")
            return False
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in config.ADMIN_IDS
    
    async def generate_promo_image_with_timeout(self, promo_code: str, discount_type: str, value: str, promo_type: str = "discount", bot_name: str = "TELESHOP", timeout: int = 5):
        """Generate promo image with timeout to prevent hanging"""
        try:
            # Run the image generation in a thread pool with timeout
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    promo_generator.create_promo_image,
                    promo_code,
                    discount_type,
                    value,
                    promo_type,
                    bot_name
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise Exception("Timed out")
        except Exception as e:
            raise e
    
    async def clear_chat_and_send_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup, use_banner: bool = False):
        """Helper function to clear chat and send menu with or without banner"""
        try:
            # Clear the entire chat by deleting recent messages
            chat_id = update.effective_chat.id
            current_message_id = None
            
            if update.callback_query and update.callback_query.message:
                current_message_id = update.callback_query.message.message_id
            
            # Delete the last 100 messages if we have a reference point
            if current_message_id:
                for i in range(100):
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=current_message_id - i)
                    except Exception as e:
                        # Stop when we can't delete more messages
                        logger.debug(f"Could not delete message {current_message_id - i}: {e}")
                        break
            
            if use_banner:
                try:
                    with open('banner.jpg', 'rb') as banner:
                        await update.effective_chat.send_photo(
                            photo=banner,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                         )
                except FileNotFoundError:
                    logger.warning("Banner file not found, sending text message instead")
                    # Fallback if banner doesn't exist
                    await update.effective_chat.send_message(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Error sending banner photo: {e}")
                    # Fallback to text message
                    await update.effective_chat.send_message(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await update.effective_chat.send_message(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error in clear_chat_and_send_menu: {e}")
            # Final fallback: try to send just the message
            try:
                await update.effective_chat.send_message(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
            except Exception as fallback_error:
                logger.error(f"Fallback message send failed: {fallback_error}")
                raise
    
    async def _clear_previous_messages(self, update: Update):
        """Clear previous messages to prevent chat clutter - optimized to avoid unnecessary API calls"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Delete tracked messages first
            if user_id in self.auto_cleanup.user_messages:
                for message_id in self.auto_cleanup.user_messages[user_id].copy():
                    try:
                        await self.application.bot.delete_message(
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
                        await self.application.bot.delete_message(
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

    async def send_menu_with_banner(self, update: Update, text: str, reply_markup: InlineKeyboardMarkup, use_banner: bool = False):
        """Helper function to send menu with or without banner - always clears previous messages"""
        user_id = update.effective_user.id
        
        try:
            # Always clear previous messages to prevent chat clutter
            await self._clear_previous_messages(update)
            
            if use_banner:
                try:
                    with open('banner.jpg', 'rb') as banner:
                        message = await update.effective_chat.send_photo(
                            photo=banner,
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                         )
                        # Track message for auto-cleanup
                        self.auto_cleanup.track_message(user_id, update.effective_chat.id, message.message_id, update)
                        return
                except FileNotFoundError:
                    logger.warning("Banner file not found, sending text message instead")
                except Exception as e:
                    logger.error(f"Error sending banner photo: {e}")
            
            # Send text message if banner not available or not requested
            message = await update.effective_chat.send_message(
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            # Track message for auto-cleanup
            self.auto_cleanup.track_message(user_id, update.effective_chat.id, message.message_id, update)
            
        except Exception as e:
            logger.error(f"Error in send_menu_with_banner: {e}")
            # Final fallback: try to send just the message
            try:
                message = await update.effective_chat.send_message(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
                # Track message for auto-cleanup
                self.auto_cleanup.track_message(user_id, update.effective_chat.id, message.message_id, update)
            except Exception as fallback_error:
                logger.error(f"Fallback message send failed: {fallback_error}")
                raise
        
    @rate_limit_check
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
    
    async def process_promo_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str):
        """Process promo code redemption"""
        lang = user.get('language', 'en')
        
        # First check if promo code exists and get its type
        promo_info = self.db.get_promo_code_info(promo_code)
        
        if not promo_info:
            error_text = f"{get_text('invalid_promo_title', lang)}\n\n{get_text('promo_error_default', lang)}"
            await update.message.reply_text(error_text, parse_mode=ParseMode.HTML)
            # Removed unnecessary sleep
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
            # Removed unnecessary sleep
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
            message = await update.effective_chat.send_message(get_text('error_creating_user', 'en'))
            self.auto_cleanup.track_message(user_id, message.message_id, update)
            return
            
        user = self.db.get_user(user_id)
        if not user:
            message = await update.effective_chat.send_message(get_text('error_user_not_found', 'en'))
            self.auto_cleanup.track_message(user_id, message.message_id, update)
            return
        
        # Clean up session
        # Clean up any existing session
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
        
        if force_new_message:
            # Send as new message (for navigation back)
            try:
                with open('banner.jpg', 'rb') as banner:
                    message = await update.effective_chat.send_photo(
                        photo=banner,
                        caption=menu_text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                    # Track message for auto-cleanup
                    self.auto_cleanup.track_message(user_id, message.message_id, update)
            except FileNotFoundError:
                message = await update.effective_chat.send_message(
                    text=menu_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
                # Track message for auto-cleanup
                self.auto_cleanup.track_message(user_id, message.message_id, update)
        else:
            # Send banner image with menu
            try:
                with open('banner.jpg', 'rb') as banner:
                    message = await update.effective_chat.send_photo(
                        photo=banner,
                        caption=menu_text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                    # Track message for auto-cleanup
                    self.auto_cleanup.track_message(user_id, message.message_id, update)
            except FileNotFoundError:
                # Fallback if banner doesn't exist
                message = await update.effective_chat.send_message(
                    text=menu_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
                # Track message for auto-cleanup
                self.auto_cleanup.track_message(user_id, message.message_id, update)
    

    
    @rate_limit_check
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries and route to appropriate handlers"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        # Update user activity for auto-cleanup
        self.auto_cleanup.update_activity(user_id, update)
        
        data = query.data
        
        # Handle start verification for new users
        if data == "start_verification":
            await self.user_handler.show_captcha(update, context)
            return
            
        if not user:
            from translations import get_text
            await query.edit_message_text(get_text('session_expired', 'en'))
            return
        
        lang = user.get('language', 'en')
        
        # Route callbacks to appropriate handlers
        
        # User-related callbacks
        if data in ["menu_main", "start_verification"]:
            await self.user_handler.handle_callback(update, context, user, data)
        
        # Shop-related callbacks
        elif data in ["menu_buy", "menu_wallet", "wallet", "menu_history", "menu_help", "menu_language"] or \
             data.startswith(("city_", "category_", "product_", "strain_", "quantity_", "location_", "wallet_", "lang_", "crypto_", "verify_btc_")):
            await self.shop_handler.handle_callback(update, context, user, data)
        
        # Order-related callbacks
        elif data.startswith(("order_", "confirm_purchase_", "track_order_", "cancel_order_", "receipt_")):
            await self.order_handler.handle_callback(update, context, user, data)
        
        # Admin-related callbacks
        elif data == "menu_admin" or data.startswith(("admin_", "setting_")) or \
             data in ["admin_add_product", "admin_add_inventory", "admin_create_promo", "admin_create_discount", 
                     "admin_stats", "admin_user_management", "admin_system_settings", "admin_database_tools"]:
            if self.is_admin(user_id):
                await self.admin_handler.handle_callback(update, context, user, data)
            else:
                from translations import get_text
                await query.edit_message_text(get_text('access_denied', lang))
        
        # Navigation and miscellaneous callbacks
        elif data.startswith(("back_", "use_promo_", "help_", "close_menu", "download_image_")):
            await self.shop_handler.handle_callback(update, context, user, data)
        
        # Default fallback
        else:
            logger.warning(f"Unhandled callback data: {data}")
            await self.user_handler.show_main_menu(update, context, user)
        
        # All callback routing is now handled by the modular handlers above
    
    # Shopping methods moved to ShopHandler
    
    async def show_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, city_id: str, category_id: str = None):
        """Show available products in selected city and category"""
        if category_id:
            products = self.db.get_products_by_category_and_city(int(category_id), int(city_id))
            context.user_data['selected_category'] = category_id
        else:
            products = self.db.get_products_by_city(int(city_id))
        
        lang = user.get('language', 'en')
        
        # Store selected city in user data
        context.user_data['selected_city'] = city_id
        
        keyboard = []
        for product in products:
            keyboard.append([InlineKeyboardButton(
                f"{product.get('emoji', '🌿')} {product['name']}", 
                callback_data=f"product_{product['id']}"
            )])
        
        back_callback = "back_categories" if category_id else "back_cities"
        keyboard.append([InlineKeyboardButton(get_text('btn_back', lang), callback_data=back_callback)])
        keyboard.append([InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            get_text('select_product', lang),
            reply_markup,
            use_banner=False
        )
    
    async def show_product_strains(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, product_id: str, city_id: str):
        """Show available strains for selected product"""
        strains = self.db.get_product_strains(product_id, city_id)
        lang = user.get('language', 'en')
        
        # Store selected product in user data
        context.user_data['selected_product'] = product_id
        
        if not strains:
            keyboard = [
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_products")],
                [InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "❌ No strains available for this product in your city.",
                reply_markup,
                use_banner=False
            )
            return
        
        # If there's only one strain available, skip strain selection and go directly to quantity selection
        if len(strains) == 1:
            strain_id = str(strains[0]['id'])
            await self.show_quantity_options(update, context, user, strain_id)
            return
        
        keyboard = []
        for strain in strains:
            keyboard.append([InlineKeyboardButton(
                f"🧬 {strain['name']}", 
                callback_data=f"strain_{strain['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_products")])
        keyboard.append([InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            get_text('select_strain', lang),
            reply_markup,
            use_banner=False
        )
    
    # Quantity and location methods moved to ShopHandler
    
    async def show_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show wallet options"""
        lang = user.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_bitcoin_payment', lang), callback_data="wallet_btc")],
            [InlineKeyboardButton(get_text('btn_blik_unavailable', lang), callback_data="wallet_blik")],
            [InlineKeyboardButton(get_text('btn_promo_code', lang), callback_data="wallet_promo")],
            [InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        balance_text = format_currency(user.get('balance', 0))
        discount_text = f"{user.get('discount', 0)}%"
        
        wallet_text = f"""{get_text('wallet_title', lang)}

{get_text('wallet_balance_label', lang).format(balance_text)}
{get_text('wallet_discount_label', lang).format(discount_text)}

{get_text('wallet_select_option', lang)}"""
        
        await self.send_menu_with_banner(update, wallet_text, reply_markup, use_banner=False)
    
    async def show_order_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show user's order history"""
        orders = self.db.get_user_orders(user['user_id'])
        lang = user.get('language', 'en')
        
        if not orders:
            keyboard = [[InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            order_history_text = f"{get_text('order_history', lang)}\n\n{get_text('no_orders', lang)}"
            await self.send_menu_with_banner(update, order_history_text, reply_markup, use_banner=False)
            return
        
        keyboard = []
        for order in orders:
            order_date = order['created_at'][:10]  # Simple date format
            order_text = f"Order #{str(order['id'])[:8]} - {order_date}"
            keyboard.append([InlineKeyboardButton(order_text, callback_data=f"order_{order['id']}")])
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        order_history_with_details = f"{get_text('order_history', lang)}\n\n{get_text('select_order_details', lang)}"
        await self.send_menu_with_banner(update, order_history_with_details, reply_markup, use_banner=False)
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show help options"""
        lang = user.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_contact_admin', lang), callback_data="help_admin")],
            [InlineKeyboardButton(get_text('btn_how_to_use', lang), callback_data="help_howto")],
            [InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, get_text('help_title', lang), reply_markup, use_banner=False)
    
    async def show_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show language selection menu"""
        current_lang = user.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton(f"🇬🇧 English {'✓' if current_lang == 'en' else ''}", callback_data="lang_en")],
            [InlineKeyboardButton(f"🇵🇱 Polski {'✓' if current_lang == 'pl' else ''}", callback_data="lang_pl")],
            [InlineKeyboardButton(f"🇷🇺 Русский {'✓' if current_lang == 'ru' else ''}", callback_data="lang_ru")],
            [InlineKeyboardButton(get_text('btn_back_menu', current_lang), callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, "🌐 <b>Language / Język / Язык</b>\n\nSelect your language:", reply_markup, use_banner=False)
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show admin panel"""
        if not self.is_admin(user['user_id']):
            await update.callback_query.answer("❌ Access denied. Admin privileges required.", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Product", callback_data="admin_add_product"),
             InlineKeyboardButton("📦 Add Inventory", callback_data="admin_add_inventory")],
            [InlineKeyboardButton("🎫 Create Promo Code", callback_data="admin_create_promo"),
             InlineKeyboardButton("💰 Create Discount", callback_data="admin_create_discount")],
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
             InlineKeyboardButton("👥 User Management", callback_data="admin_user_management")],
            [InlineKeyboardButton("⚙️ System Settings", callback_data="admin_system_settings"),
             InlineKeyboardButton("🗄️ Database Tools", callback_data="admin_database_tools")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Clear chat and send admin panel
        await self.clear_chat_and_send_menu(
            update,
            context,
            "👑 <b>Admin Panel</b>\n\nSelect an action:",
            reply_markup,
            use_banner=False
        )
    
    async def handle_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, inventory_id: str):
        """Handle purchase confirmation"""
        lang = user.get('language', 'en')
        logger.info(f"handle_purchase called with inventory_id: {inventory_id} for user: {user.get('user_id')}")
        
        try:
            # Get inventory details
            inventory = self.db.get_inventory_details(int(inventory_id))
            logger.info(f"Retrieved inventory details: {inventory is not None}")
            if inventory:
                logger.info(f"Inventory keys: {list(inventory.keys())}")
                logger.info(f"Category ID: {inventory.get('category_id', 'NOT_FOUND')}")
            if not inventory:
                logger.error(f"Inventory not found for ID: {inventory_id}")
                await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
                return
        except ValueError as e:
            logger.error(f"Invalid inventory_id format: {inventory_id}, error: {e}")
            await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
            return
        except Exception as e:
            logger.error(f"Error getting inventory details for ID {inventory_id}: {e}")
            await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
            return
        
        # Get selected quantity from context, fallback to inventory quantity
        selected_quantity = context.user_data.get('selected_quantity', inventory['quantity'])
        
        # Calculate price based on selected quantity
        # Get strain details to calculate proper price
        strain_data = self.db.get_strain_with_price(inventory['strain_id'])
        if strain_data:
            original_price = strain_data['base_price'] * strain_data['price_modifier'] * selected_quantity
        else:
            # Fallback to inventory price if strain data not available
            original_price = inventory['price'] * (selected_quantity / inventory['quantity'])
        
        # Check for automatic discounts (category, product, global) - apply the highest one
        final_price = original_price
        discount_info = None
        best_discount = None
        
        # Check for category discount
        category_id = inventory.get('category_id')
        if category_id:
            category_discount = self.db.get_category_discount(category_id)
            if category_discount and (not best_discount or category_discount['percentage'] > best_discount['percentage']):
                best_discount = category_discount
                best_discount['type'] = 'category'
        
        # Check for product discount
        product_discount = self.db.get_product_discount(inventory['product_id'])
        if product_discount and (not best_discount or product_discount['percentage'] > best_discount['percentage']):
            best_discount = product_discount
            best_discount['type'] = 'product'
        
        # Check for global discount
        global_discount = self.db.get_global_discount()
        if global_discount and (not best_discount or global_discount['percentage'] > best_discount['percentage']):
            best_discount = global_discount
            best_discount['type'] = 'global'
        
        # Apply the best discount found
        if best_discount:
            from utils import calculate_discount
            discounted_price, discount_amount = calculate_discount(original_price, best_discount['percentage'])
            final_price = discounted_price
            discount_info = {
                'type': best_discount['type'],
                'name': best_discount['name'],
                'percentage': best_discount['percentage'],
                'amount': discount_amount
            }
        
        # Use final_price for balance check
        price = final_price
        
        user_balance = user.get('balance', 0)
        logger.info(f"Selected quantity: {selected_quantity}, Calculated price: {price}, User balance: {user_balance}")
        
        if user_balance < price:
            logger.info(f"Insufficient balance. Required: {price}, Available: {user_balance}")
            
            # Create insufficient balance message with wallet button
            insufficient_balance_text = f"""❌ <b>Insufficient Balance</b>

💰 Required: {format_currency(price)}
💳 Your balance: {format_currency(user_balance)}
💸 Need: {format_currency(price - user_balance)}

📍 Location: {inventory['location_name']}
🧬 Product: {inventory['product_name']} - {inventory['strain_name']}
⚖️ Quantity: {inventory['quantity']}{inventory['unit']}

Please add funds to your wallet to complete this purchase."""
            
            keyboard = [
                [InlineKeyboardButton("💳 Go to Wallet", callback_data="wallet")],
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_quantities")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                insufficient_balance_text,
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_confirm_purchase', lang), callback_data=f"confirm_purchase_{inventory_id}")],
            [InlineKeyboardButton("🎫 Use Promo Code", callback_data=f"use_promo_{inventory_id}")],
            [InlineKeyboardButton(get_text('btn_cancel', lang), callback_data="back_quantities")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Build purchase text with discount info
        discount_text = ""
        if discount_info:
            discount_text = f"\n🎉 <b>{discount_info['name']}</b> (-{discount_info['percentage']}%)\n💸 You save: {format_currency(discount_info['amount'])}"
        
        purchase_text = f"""{get_text('purchase_confirmation_title', lang)}

📍 Location: {inventory['location_name']}
🧬 Product: {inventory['product_name']} - {inventory['strain_name']}
⚖️ Quantity: {selected_quantity}{inventory['unit']}
🏙️ City: {inventory['city_name']}{discount_text}

💰 Original Price: {format_currency(original_price)}
💰 Final Price: {format_currency(price)}
💳 Your balance: {format_currency(user_balance)}
💳 After purchase: {format_currency(user_balance - price)}

❓ Confirm this purchase?
💡 Have a discount code? Use the promo button below!"""
        
        # Send purchase confirmation without banner image (security measure)
        # Banner image will be shown only after successful payment
        logger.info("Sending purchase confirmation without banner image for security")
        try:
            await self.send_menu_with_banner(
                update,
                purchase_text,
                reply_markup,
                use_banner=False
            )
            logger.info("Successfully sent purchase confirmation without banner")
        except Exception as e:
            logger.error(f"Failed to send purchase confirmation: {e}")
    
    async def handle_pooled_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, location_id: str, inventory_ids: str):
        """Handle purchase confirmation for pooled inventory items"""
        lang = user.get('language', 'en')
        logger.info(f"handle_pooled_purchase called with location_id: {location_id}, inventory_ids: {inventory_ids} for user: {user.get('user_id')}")
        
        try:
            # Parse inventory IDs
            inventory_id_list = inventory_ids.split(',')
            
            # Get selected quantity from context
            selected_quantity = context.user_data.get('selected_quantity', 0)
            
            # Get inventory details for all items in the pool
            pool_items = []
            total_available = 0
            
            for inv_id in inventory_id_list:
                inventory = self.db.get_inventory_details(int(inv_id.strip()))
                if inventory:
                    pool_items.append(inventory)
                    total_available += inventory['quantity']
            
            if not pool_items:
                logger.error(f"No valid inventory items found for IDs: {inventory_ids}")
                await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
                return
            
            # Check if we have enough quantity in the pool
            if selected_quantity > total_available:
                logger.error(f"Insufficient quantity in pool. Requested: {selected_quantity}, Available: {total_available}")
                await update.callback_query.answer("❌ Insufficient quantity available", show_alert=True)
                return
            
            # Select items from pool to fulfill the order (FIFO approach)
            selected_items = []
            remaining_quantity = selected_quantity
            
            for item in pool_items:
                if remaining_quantity <= 0:
                    break
                
                if item['quantity'] <= remaining_quantity:
                    # Take the entire item
                    # Safety check to prevent division by zero
                    if item['quantity'] > 0:
                        price_per_unit = item['price'] / item['quantity']
                        selected_items.append({
                            'inventory_id': item['id'],
                            'quantity': item['quantity'],
                            'price_per_unit': price_per_unit
                        })
                        remaining_quantity -= item['quantity']
                    else:
                        logger.warning(f"Item {item['id']} has zero quantity, skipping")
                        continue
                else:
                    # Take partial quantity from this item
                    # Safety check to prevent division by zero
                    if item['quantity'] > 0:
                        price_per_unit = item['price'] / item['quantity']
                    else:
                        logger.warning(f"Item {item['id']} has zero quantity, skipping")
                        continue
                    
                    selected_items.append({
                        'inventory_id': item['id'],
                        'quantity': remaining_quantity,
                        'price_per_unit': price_per_unit
                    })
                    remaining_quantity = 0
            
            # Calculate total price
            total_price = sum(item['quantity'] * item['price_per_unit'] for item in selected_items)
            
            # Use the first item for display information
            primary_item = pool_items[0]
            
            # Store pooled purchase info in context
            context.user_data['pooled_purchase'] = {
                'location_id': location_id,
                'selected_items': selected_items,
                'total_quantity': selected_quantity,
                'total_price': total_price,
                'primary_item': primary_item
            }
            
            # Check user balance
            user_balance = user.get('balance', 0)
            
            if user_balance < total_price:
                logger.info(f"Insufficient balance. Required: {total_price}, Available: {user_balance}")
                
                insufficient_balance_text = f"""❌ <b>Insufficient Balance</b>

💰 Required: {format_currency(total_price)}
💳 Your balance: {format_currency(user_balance)}
💸 Need: {format_currency(total_price - user_balance)}

📍 Location: {primary_item['location_name']}
🧬 Product: {primary_item['product_name']} - {primary_item['strain_name']}
⚖️ Quantity: {selected_quantity}{primary_item['unit']}

Please add funds to your wallet to complete this purchase."""
                
                keyboard = [
                    [InlineKeyboardButton("💳 Go to Wallet", callback_data="wallet")],
                    [InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_quantities")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.send_menu_with_banner(
                    update,
                    insufficient_balance_text,
                    reply_markup,
                    use_banner=False
                )
                return
            
            # Show purchase confirmation
            keyboard = [
                [InlineKeyboardButton(get_text('btn_confirm_purchase', lang), callback_data="confirm_pooled_purchase")],
                [InlineKeyboardButton("🎫 Use Promo Code", callback_data="use_promo_pooled")],
                [InlineKeyboardButton(get_text('btn_cancel', lang), callback_data="back_quantities")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            purchase_text = f"""{get_text('purchase_confirmation_title', lang)}

📍 Location: {primary_item['location_name']}
🧬 Product: {primary_item['product_name']} - {primary_item['strain_name']}
⚖️ Quantity: {selected_quantity}{primary_item['unit']} (from {len(selected_items)} item(s))
🏙️ City: {primary_item['city_name']}

💰 Total Price: {format_currency(total_price)}
💳 Your balance: {format_currency(user_balance)}
💳 After purchase: {format_currency(user_balance - total_price)}

❓ Confirm this purchase?
💡 Have a discount code? Use the promo button below!"""
            
            await self.send_menu_with_banner(
                update,
                purchase_text,
                reply_markup,
                use_banner=False
            )
            
        except Exception as e:
            logger.error(f"Error in handle_pooled_purchase: {e}")
            await update.callback_query.answer("❌ Error processing purchase", show_alert=True)
    
    async def process_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, inventory_id: str):
        """Process the actual purchase transaction"""
        lang = user.get('language', 'en')
        user_id = user['user_id']
        
        # Get inventory details
        inventory = self.db.get_inventory_details(int(inventory_id))
        if not inventory:
            await update.callback_query.answer("❌ Item not found!", show_alert=True)
            return
        
        # Get selected quantity from context, fallback to inventory quantity
        selected_quantity = context.user_data.get('selected_quantity', inventory['quantity'])
        
        # Calculate price based on selected quantity
        strain_data = self.db.get_strain_with_price(inventory['strain_id'])
        if strain_data:
            original_price = strain_data['base_price'] * strain_data['price_modifier'] * selected_quantity
        else:
            # Fallback to inventory price if strain data not available
            original_price = inventory['price'] * (selected_quantity / inventory['quantity'])
        
        # Check for automatic discounts first (category, product, global) - apply the highest one
        final_price = original_price
        auto_discount_info = None
        best_discount = None
        
        # Check for category discount
        category_id = inventory.get('category_id')
        if category_id:
            category_discount = self.db.get_category_discount(category_id)
            if category_discount and (not best_discount or category_discount['percentage'] > best_discount['percentage']):
                best_discount = category_discount
                best_discount['type'] = 'category'
        
        # Check for product discount
        product_discount = self.db.get_product_discount(inventory['product_id'])
        if product_discount and (not best_discount or product_discount['percentage'] > best_discount['percentage']):
            best_discount = product_discount
            best_discount['type'] = 'product'
        
        # Check for global discount
        global_discount = self.db.get_global_discount()
        if global_discount and (not best_discount or global_discount['percentage'] > best_discount['percentage']):
            best_discount = global_discount
            best_discount['type'] = 'global'
        
        # Apply the best discount found
        if best_discount:
            from utils import calculate_discount
            discounted_price, discount_amount = calculate_discount(original_price, best_discount['percentage'])
            final_price = discounted_price
            auto_discount_info = {
                'type': best_discount['type'],
                'name': best_discount['name'],
                'percentage': best_discount['percentage'],
                'amount': discount_amount
            }
        
        # Check for applied promo code and calculate additional discount
        applied_promo = context.user_data.get('applied_promo')
        promo_code_used = None
        total_discount_amount = auto_discount_info['amount'] if auto_discount_info else 0
        
        if applied_promo:
            # Apply promo code discount on top of automatic discount
            promo_discount_percentage = applied_promo['discount_percentage']
            promo_discount_amount = final_price * (promo_discount_percentage / 100)
            final_price = final_price - promo_discount_amount
            total_discount_amount += promo_discount_amount
            promo_code_used = applied_promo['code']
        
        user_balance = user.get('balance', 0)
        
        # Check balance again with final price
        if user_balance < final_price:
            await update.callback_query.answer("❌ Insufficient balance!", show_alert=True)
            return
        
        # Process the purchase
        try:
            # Redeem promo code if one was applied
            if promo_code_used:
                promo_result = self.db.redeem_promo_code(user_id, promo_code_used)
                if not promo_result['success']:
                    await update.callback_query.answer(f"❌ Promo code error: {promo_result['message']}", show_alert=True)
                    return
            
            # Update user balance with final price
            new_balance = user_balance - final_price
            # Use the correct update_user_balance method (set new balance, not add amount)
            success = self.db.set_user_balance(user_id, new_balance)
            if not success:
                await update.callback_query.answer("❌ Failed to update balance!", show_alert=True)
                return
            
            # Create order record using correct method signature
            order_id = self.db.create_order(
                user_id=user_id,
                inventory_id=int(inventory_id),
                quantity=selected_quantity,
                total_price=final_price,
                coordinates=inventory['coordinates'],
                payment_method='balance'
            )
            
            # Mark inventory item as unavailable
            self.db.update_inventory_availability(int(inventory_id), False)
            
            # Clear applied promo from context
            if 'applied_promo' in context.user_data:
                del context.user_data['applied_promo']
            
            # Minimalistic success message
            success_text = f"""✅ **Purchase Confirmed**

🧬 {inventory['product_name']} - {inventory['strain_name']}
⚖️ {selected_quantity}{inventory['unit']} • {format_currency(final_price)}
📍 {inventory['coordinates']}
📋 Order #{order_id}"""
            
            # Add discount info if any discount was applied
            if auto_discount_info:
                success_text += f"\n🎉 {auto_discount_info['name']}: -{format_currency(auto_discount_info['amount'])}"
            
            if promo_code_used:
                promo_discount_amount = total_discount_amount - (auto_discount_info['amount'] if auto_discount_info else 0)
                success_text += f"\n🎫 Promo Code: -{format_currency(promo_discount_amount)}"
            
            if total_discount_amount > 0:
                success_text += f"\n💰 Original Price: {format_currency(original_price)}"
            
            # Show banner image with coordinates after successful payment
            if inventory.get('banner_image'):
                try:
                    await update.callback_query.edit_message_media(
                        media=InputMediaPhoto(
                            media=inventory['banner_image'],
                            caption=success_text,
                            parse_mode=ParseMode.HTML
                        )
                    )
                    logger.info("Successfully sent purchase success with banner image")
                    
                    # Automatically send the location image as a separate message with buttons
                    keyboard = [
                        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"receipt_{order_id}")],
                        [InlineKeyboardButton("💬 Support", callback_data="contact_admin")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=inventory['download_image'],
                            caption=f"📍 **Location Map**\n\n🏙️ {inventory['city_name']}\n📍 {inventory['coordinates']}\n\n🗺️ **Open in Maps:**\n🌍 [Google Maps](https://maps.google.com/?q={inventory['coordinates']})\n🍎 [Apple Maps](https://maps.apple.com/?q={inventory['coordinates']})\n🗺️ [OpenStreetMap](https://www.openstreetmap.org/?mlat={inventory['coordinates'].split(',')[0]}&mlon={inventory['coordinates'].split(',')[1]}&zoom=15)",
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup
                        )
                        logger.info(f"Automatically sent location image for order {order_id}")
                    except Exception as img_error:
                        logger.error(f"Failed to send location image: {img_error}")
                        
                except Exception as e:
                    logger.error(f"Failed to send photo: {e}")
                    await self.send_menu_with_banner(
                        update,
                        success_text,
                        reply_markup,
                        use_banner=False
                    )
            else:
                await self.send_menu_with_banner(
                    update,
                    success_text,
                    reply_markup,
                    use_banner=False
                )
            
        except Exception as e:
            logger.error(f"Purchase processing error: {e}")
            await update.callback_query.answer("❌ Purchase failed. Please try again.", show_alert=True)
    
    async def handle_promo_code_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Handle promo code entry"""
        lang = user.get('language', 'en')
        
        keyboard = [[InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            f"🎫 <b>{get_text('promo_code', lang)}</b>\n\n{get_text('enter_promo_code', lang)}",
            reply_markup,
            use_banner=False
        )
        
        # Set user state for promo code entry
        context.user_data['awaiting_promo'] = True
    
    async def handle_purchase_promo_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Handle promo code entry during purchase"""
        lang = user.get('language', 'en')
        inventory_id = context.user_data.get('pending_purchase')
        
        # Check if user has a saved discount code
        saved_discount = context.user_data.get('saved_discount_code')
        
        if saved_discount:
            # Check if saved code is still valid (not expired)
            from datetime import datetime
            if saved_discount['expires_at'] and datetime.now().isoformat() > saved_discount['expires_at']:
                # Code expired, remove it
                del context.user_data['saved_discount_code']
                saved_discount = None
        
        if saved_discount:
            # Offer to use saved discount code
            keyboard = [
                [InlineKeyboardButton(f"✅ Use Saved {saved_discount['percentage']}% Code", callback_data=f"use_saved_discount_{inventory_id}")],
                [InlineKeyboardButton("🆕 Enter New Code", callback_data=f"enter_new_discount_{inventory_id}")],
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data=f"location_{inventory_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"🎫 <b>Discount Promo Code</b>\n\n✅ You have a saved {saved_discount['percentage']}% discount code!\n\n💡 Choose an option:"
        else:
            # No saved code, prompt for entry
            keyboard = [[InlineKeyboardButton(get_text('btn_back', lang), callback_data=f"location_{inventory_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"🎫 <b>Discount Promo Code</b>\n\nEnter your discount promo code to apply it to this purchase:"
            # Set user state for purchase promo code entry
            context.user_data['awaiting_purchase_promo'] = True
        
        await self.send_menu_with_banner(
            update,
            text,
            reply_markup,
            use_banner=False
        )
    
    async def process_purchase_promo_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str):
        """Process discount promo code during purchase"""
        lang = user.get('language', 'en')
        inventory_id = context.user_data.get('pending_purchase')
        
        try:
            # Get promo code info without redeeming it
            promo_data = self.db.get_promo_code_info(promo_code)
            
            if not promo_data:
                await update.message.reply_text("❌ Invalid or expired promo code.")
                # Go back to purchase confirmation
                await self.handle_purchase(update, context, user, inventory_id)
                return
            
            # Check if it's a discount promo
            if promo_data['type'] != 'discount':
                await update.message.reply_text("❌ This promo code is not a discount code. Only discount codes can be used during checkout.")
                # Go back to purchase confirmation
                await self.handle_purchase(update, context, user, inventory_id)
                return
            
            # Store the promo code for the purchase
            context.user_data['applied_promo'] = {
                'code': promo_code,
                'discount_percentage': promo_data['value']
            }
            
            # Show updated purchase confirmation with discount
            await self.show_purchase_with_discount(update, context, user, inventory_id, promo_data['value'])
            
        except Exception as e:
            logger.error(f"Error processing purchase promo code: {e}")
            await update.message.reply_text("❌ Error processing promo code. Please try again.")
            await self.handle_purchase(update, context, user, inventory_id)
    
    async def show_purchase_with_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, inventory_id: str, discount_percentage: float):
        """Show purchase confirmation with applied discount"""
        lang = user.get('language', 'en')
        
        try:
            # Get inventory details
            inventory = self.db.get_inventory_details(inventory_id)
            if not inventory:
                await update.message.reply_text("❌ Product not found.")
                return
            
            # Calculate prices
            original_price = float(inventory['price'])
            discount_amount = original_price * (discount_percentage / 100)
            final_price = original_price - discount_amount
            
            # Get product details
            strain_data = self.db.get_strain_with_price(inventory['strain_id'])
            product_name = strain_data['product_name'] if strain_data else "Unknown Product"
            strain_name = strain_data['name'] if strain_data else "Unknown Strain"
            
            # Get location details
            location = self.db.get_location_details(inventory['location_id'])
            location_name = location['name'] if location else f"Location {inventory['location_id']}"
            
            message = f"🛒 <b>Purchase Confirmation</b>\n\n"
            message += f"📦 <b>Product:</b> {product_name}\n"
            message += f"🌿 <b>Strain:</b> {strain_name}\n"
            message += f"📍 <b>Location:</b> {location_name}\n\n"
            message += f"💰 <b>Original Price:</b> {original_price:.2f} zł\n"
            message += f"🎫 <b>Discount ({discount_percentage}%):</b> -{discount_amount:.2f} zł\n"
            message += f"💳 <b>Final Price:</b> {final_price:.2f} zł\n\n"
            message += f"💼 <b>Your Balance:</b> {user['balance']:.2f} zł\n\n"
            
            if final_price > user['balance']:
                message += "❌ <b>Insufficient balance!</b>"
                keyboard = [
                    [InlineKeyboardButton("💰 Add Funds", callback_data="menu_wallet")],
                    [InlineKeyboardButton(get_text('btn_back', lang), callback_data=f"location_{inventory_id}")]
                ]
            else:
                message += "✅ <b>Ready to purchase!</b>"
                keyboard = [
                    [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_purchase_{inventory_id}")],
                    [InlineKeyboardButton("🗑️ Remove Discount", callback_data=f"location_{inventory_id}")],
                    [InlineKeyboardButton(get_text('btn_back', lang), callback_data=f"location_{inventory_id}")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                message,
                reply_markup,
                use_banner=False
            )
            
        except Exception as e:
            logger.error(f"Error showing purchase with discount: {e}")
            await update.message.reply_text("❌ Error displaying purchase details.")
     
    async def show_order_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, order_id: str):
        """Show detailed order information"""
        order = self.db.get_order_details(order_id)
        lang = user.get('language', 'en')
        
        if not order:
            await update.callback_query.answer(get_text('order_not_found', lang), show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_download_receipt', lang), callback_data=f"receipt_{order_id}")],
            [InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_history")],
            [InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        order_date = order['created_at'][:10]  # Simple date format
        receipt_text = f"""{get_text('order_receipt_title', lang)}

{get_text('order_id_label', lang).format(order['id'])}
{get_text('order_date', lang).format(order_date)}
{get_text('order_location', lang).format(order.get('location_name', 'N/A'))}
{get_text('order_product', lang).format(order.get('product_name', 'N/A'))}
{get_text('total_paid', lang).format(format_currency(order.get('amount', 0)))}
{get_text('order_status', lang).format(order.get('status', 'Completed'))}

{get_text('thank_you_purchase', lang)}"""
        
        # Send with download image if available
        if order.get('download_image'):
            try:
                await update.callback_query.edit_message_media(
                    media=InputMediaPhoto(
                        media=order['download_image'],
                        caption=receipt_text,
                        parse_mode=ParseMode.HTML
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send order photo: {e}")
                await self.send_menu_with_banner(
                    update,
                    receipt_text,
                    reply_markup,
                    use_banner=False
                )
        else:
            await self.send_menu_with_banner(
                update,
                receipt_text,
                reply_markup,
                use_banner=False
            )
    
    async def contact_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Redirect user to admin DMs with smart admin selection"""
        from config import ADMINS_WITH_HOURS
        from utils import get_available_admin
        
        lang = user.get('language', 'en')
        
        # Get currently available admin
        available_admin = get_available_admin(ADMINS_WITH_HOURS)
        
        if available_admin:
            admin_username = available_admin['username']
            admin_name = available_admin.get('name', 'Admin')
            
            # Create contact button that opens admin's chat
            keyboard = [
                [InlineKeyboardButton(f"💬 {get_text('contact_admin_button', lang).format(admin_name)}", url=f"https://t.me/{admin_username}")],
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_help")]
            ]
        else:
            # Fallback to original admin
            keyboard = [
                [InlineKeyboardButton(f"💬 {get_text('contact_admin_button', lang).format('Admin')}", url=f"https://t.me/{config.ADMIN_USERNAME}")],
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_help")]
            ]
            admin_username = config.ADMIN_USERNAME
            admin_name = 'Admin'
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        contact_text = f"""{get_text('contact_admin_title', lang)}

{get_text('contact_admin_smart_text', lang).format(admin_name, admin_username)}"""
        
        await self.send_menu_with_banner(update, contact_text, reply_markup, use_banner=False)
    
    async def process_pooled_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process the actual pooled purchase transaction"""
        lang = user.get('language', 'en')
        user_id = user['user_id']
        
        # Get pooled purchase data from context
        pooled_data = context.user_data.get('pooled_purchase')
        if not pooled_data:
            await update.callback_query.answer("❌ Purchase data not found!", show_alert=True)
            return
        
        selected_items = pooled_data['selected_items']
        total_price = pooled_data['total_price']
        total_quantity = pooled_data['total_quantity']
        primary_item = pooled_data['primary_item']
        
        # Check user balance
        if user['balance'] < total_price:
            await update.callback_query.answer("❌ Insufficient balance!", show_alert=True)
            return
        
        try:
            # Randomly select one item from the pool instead of processing all
            import random
            selected_item = random.choice(selected_items)
            
            # Get full inventory details for coordinates
            inventory_details = self.db.get_inventory_details(selected_item['inventory_id'])
            if not inventory_details:
                await update.callback_query.answer("❌ Item not found!", show_alert=True)
                return
            
            # Use the requested total quantity for the single selected item
            order_quantity = total_quantity
            order_price = total_price
            
            # Create single order
            order_id = self.db.create_order(
                user_id=user_id,
                inventory_id=selected_item['inventory_id'],
                quantity=order_quantity,
                total_price=order_price,
                coordinates=inventory_details['coordinates'],
                payment_method='balance'
            )
            
            if not order_id:
                logger.error(f"Failed to create order for inventory {selected_item['inventory_id']}")
                await update.callback_query.answer("❌ Purchase failed!", show_alert=True)
                return
            
            # Update inventory quantity for the selected item
            self.db.update_inventory_quantity(selected_item['inventory_id'], order_quantity)
            order_ids = [order_id]
            
            # Deduct balance
            new_balance = user['balance'] - total_price
            self.db.set_user_balance(user_id, new_balance)
            
            # Clear pooled purchase data
            context.user_data.pop('pooled_purchase', None)
            context.user_data.pop('selected_quantity', None)
            
            # Show success message without buttons
            success_text = f"""✅ <b>Purchase Successful!</b>

📍 Location: {primary_item['location_name']}
🧬 Product: {primary_item['product_name']} - {primary_item['strain_name']}
⚖️ Quantity: {total_quantity}{primary_item['unit']}
💰 Total Paid: {format_currency(total_price)}
💳 New Balance: {format_currency(new_balance)}

📦 Order ID: #{order_id}

🎉 Thank you for your purchase!"""
            
            # Show banner image if available
            if primary_item.get('banner_image'):
                try:
                    await update.callback_query.edit_message_media(
                        media=InputMediaPhoto(
                            media=primary_item['banner_image'],
                            caption=success_text,
                            parse_mode=ParseMode.HTML
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to send banner image: {e}")
                    await self.send_menu_with_banner(
                        update,
                        success_text,
                        use_banner=False
                    )
            else:
                await self.send_menu_with_banner(
                    update,
                    success_text,
                    use_banner=False
                )
            
            # Automatically send download image with buttons if available
            if inventory_details.get('download_image'):
                try:
                    coordinates_text = f"📍 **Location Coordinates:**\n`{inventory_details['coordinates']}`\n\n🗺️ [Open in Google Maps](https://www.google.com/maps?q={inventory_details['coordinates']})"
                    
                    # Create keyboard with download receipt and main menu buttons
                    keyboard = [
                        [InlineKeyboardButton("🧾 Download Receipt", callback_data=f"receipt_{order_id}")],
                        [InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="menu_main")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=inventory_details['download_image'],
                        caption=coordinates_text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Failed to send download image automatically: {e}")
                
        except Exception as e:
            logger.error(f"Error processing pooled purchase: {e}")
            await update.callback_query.answer("❌ Purchase failed!", show_alert=True)
    
    async def handle_pooled_promo_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Handle promo code entry for pooled purchases"""
        lang = user.get('language', 'en')
        
        # Get pooled purchase data
        pooled_data = context.user_data.get('pooled_purchase')
        if not pooled_data:
            await update.callback_query.answer("❌ Purchase data not found!", show_alert=True)
            return
        
        keyboard = [[InlineKeyboardButton(get_text('btn_cancel', lang), callback_data="confirm_pooled_purchase")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"🎫 <b>Discount Promo Code</b>\n\nEnter your discount promo code to apply it to this pooled purchase:"
        
        # Set user state for pooled purchase promo code entry
        context.user_data['awaiting_pooled_purchase_promo'] = True
        
        await self.send_menu_with_banner(
            update,
            text,
            reply_markup,
            use_banner=False
        )
    
    async def show_how_to_use(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show how to use guide"""
        lang = user.get('language', 'en')
        
        keyboard = [[InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        how_to_text = f"""{get_text('how_to_use_title', lang)}

{get_text('how_to_use_content', lang)}"""
        
        await self.send_menu_with_banner(update, how_to_text, reply_markup, use_banner=False)
    
    async def change_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, lang_code: str):
        """Change user language"""
        supported_languages = ['en', 'pl', 'ru']
        if lang_code not in supported_languages:
            await update.callback_query.answer(get_text('unsupported_language', 'en'), show_alert=True)
            return
        
        # Update user language in database
        self.db.update_user_language(user['user_id'], lang_code)
        
        # Refresh user data from database to get updated language
        updated_user = self.db.get_user(user['user_id'])
        if updated_user:
            user.update(updated_user)
        
        await update.callback_query.answer(get_text('language_changed', lang_code))
        # Delete current message and show main menu with banner
        await update.callback_query.delete_message()
        await self.show_main_menu(update, context, user, force_new_message=True)
    
    async def handle_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, action: str):
        """Handle admin panel actions"""
        if not self.is_admin(user['user_id']):
            await update.callback_query.answer(get_text('access_denied', 'en'), show_alert=True)
            return
        
        if action == "admin_add_product":
            await self.admin_add_product(update, context, user)
        elif action == "admin_add_inventory":
            await self.admin_add_inventory(update, context, user)
        elif action == "admin_create_promo":
            await self.admin_create_promo(update, context, user)
        elif action == "admin_create_discount":
            await self.admin_create_discount(update, context, user)
        elif action == "admin_new_discount":
            await self.admin_new_discount(update, context, user)
        elif action == "admin_view_discounts":
            await self.admin_view_discounts(update, context, user)
        elif action.startswith("admin_discount_details_"):
            discount_id = action.split("_")[-1]
            await self.admin_discount_details(update, context, user, discount_id)
        elif action.startswith("admin_delete_discount_"):
            discount_id = action.split("_")[-1]
            await self.admin_delete_discount(update, context, user, discount_id)
        elif action == "admin_discount_type_category":
            await self.admin_discount_select_category(update, context, user)
        elif action == "admin_discount_type_product":
            await self.admin_discount_select_product(update, context, user)
        elif action == "admin_discount_type_global":
            await self.admin_discount_create_global(update, context, user)
        elif action.startswith("admin_discount_cat_"):
            category_id = action.split("_")[-1]
            await self.admin_discount_create_category(update, context, user, category_id)
        elif action.startswith("admin_discount_prod_"):
            product_id = action.split("_")[-1]
            await self.admin_discount_create_product(update, context, user, product_id)
        
        # Global discount creation
        elif action.startswith("admin_create_global_discount_"):
            percentage = action.split("_")[-1]
            await self.admin_finalize_global_discount(update, context, user, int(percentage))
        
        # Category discount creation
        elif action.startswith("admin_create_category_discount_"):
            percentage = action.split("_")[-1]
            await self.admin_finalize_category_discount(update, context, user, int(percentage))
        
        # Product discount creation
        elif action.startswith("admin_create_product_discount_"):
            percentage = action.split("_")[-1]
            await self.admin_finalize_product_discount(update, context, user, int(percentage))
        
        # Custom discount handlers
        elif action == "admin_custom_global_discount":
            await self.admin_request_custom_global_discount(update, context, user)
        elif action == "admin_custom_category_discount":
            await self.admin_request_custom_category_discount(update, context, user)
        elif action == "admin_custom_product_discount":
            await self.admin_request_custom_product_discount(update, context, user)
        elif action == "admin_stats":
            await self.admin_show_stats(update, context, user)
        elif action.startswith("admin_add_to_cat_"):
            category_id = action.split("_")[-1]
            await self.admin_add_product_to_category(update, context, user, category_id)
        elif action == "admin_add_category":
            await self.admin_add_new_category(update, context, user)
        elif action.startswith("admin_inv_strain_"):
            strain_id = action.split("_")[-1]
            await self.admin_add_inventory_for_strain(update, context, user, strain_id)
        elif action.startswith("admin_inv_city_"):
            city_id = action.split("_")[-1]
            await self.admin_select_city_for_inventory(update, context, user, city_id)
        elif action.startswith("admin_inv_loc_"):
            location_id = action.split("_")[-1]
            await self.admin_select_location_for_inventory(update, context, user, location_id)
        elif action == "admin_promo_balance":
            await self.admin_create_balance_promo(update, context, user)
        elif action == "admin_promo_discount":
            await self.admin_create_discount_promo(update, context, user)
        elif action == "admin_promo_free":
            await self.admin_create_free_promo(update, context, user)
        elif action == "admin_view_promos":
            await self.admin_view_active_promos(update, context, user)
        elif action == "admin_user_management":
            await self.admin_user_management(update, context, user)
        elif action == "admin_system_settings":
            await self.admin_system_settings(update, context, user)
        elif action == "admin_database_tools":
            await self.admin_database_tools(update, context, user)
        elif action.startswith("admin_create_bal_promo_"):
            parts = action.split("_")
            promo_code = parts[4]
            amount = parts[5]
            await self.admin_confirm_balance_promo(update, context, user, promo_code, amount)
        elif action.startswith("admin_create_disc_promo_"):
            parts = action.split("_")
            promo_code = parts[4]
            percentage = parts[5]
            await self.admin_confirm_discount_promo(update, context, user, promo_code, percentage)
        elif action.startswith("admin_custom_bal_promo_"):
            parts = action.split("_")
            promo_code = parts[4]
            await self.admin_custom_balance_promo(update, context, user, promo_code)
        elif action.startswith("admin_custom_disc_promo_"):
            parts = action.split("_")
            promo_code = parts[4]
            await self.admin_custom_discount_promo(update, context, user, promo_code)
        elif action == "menu_admin":
            await self.show_admin_panel(update, context, user)
        # User Management sub-actions
        elif action == "admin_view_users":
            await self.admin_view_users(update, context, user)
        elif action == "admin_search_user":
            await self.admin_search_user(update, context, user)
        elif action == "admin_add_balance":
            await self.admin_add_balance(update, context, user)
        elif action == "admin_ban_user":
            await self.admin_ban_user(update, context, user)
        elif action == "admin_user_stats":
            await self.admin_user_stats(update, context, user)
        # User Management pagination and actions
        elif action.startswith("admin_users_page_"):
            page = int(action.split("_")[-1])
            context.user_data['users_page'] = page
            await self.admin_view_users(update, context, user)
        elif action.startswith("admin_confirm_ban_"):
            parts = action.split("_")
            target_user_id = int(parts[3])
            ban_status = parts[4] == "True"
            await self.admin_confirm_ban_action(update, context, user, target_user_id, ban_status)
        # System Settings sub-actions
        elif action == "admin_bot_settings":
            await self.admin_bot_settings(update, context, user)
        elif action == "admin_manage_cities":
            await self.admin_manage_cities(update, context, user)
        elif action == "admin_manage_locations":
            await self.admin_manage_locations(update, context, user)
        elif action == "admin_maintenance":
            await self.admin_maintenance(update, context, user)
        elif action == "admin_view_logs":
            await self.admin_view_logs(update, context, user)
        elif action == "admin_test_cleanup":
            await self.admin_test_cleanup(update, context, user)
        # Database Tools sub-actions
        elif action == "admin_db_stats":
            await self.admin_db_stats(update, context, user)
        elif action == "admin_clean_data":
            await self.admin_clean_data(update, context, user)
        elif action == "admin_confirm_clean_data":
            context.user_data['confirm_clean_data'] = True
            await self.admin_clean_data(update, context, user)
        elif action == "admin_backup_db":
            await self.admin_backup_db(update, context, user)
        elif action == "admin_reset_test":
            await self.admin_reset_test(update, context, user)
        elif action == "admin_confirm_reset_test":
            context.user_data['confirm_reset_test'] = True
            await self.admin_reset_test(update, context, user)
        # Promo code sub-actions
        elif action == "admin_delete_promo":
            await self.admin_delete_promo(update, context, user)
        elif action == "admin_confirm_delete_promo":
            context.user_data['promo_to_delete'] = context.user_data.get('promo_to_delete')
            await self.admin_delete_promo(update, context, user)
        # City Management sub-actions
        elif action == "admin_add_city":
            await self.admin_add_city(update, context, user)
        elif action == "admin_edit_city_status":
            await self.admin_edit_city_status(update, context, user)
        elif action == "admin_delete_city":
            await self.admin_delete_city(update, context, user)
        elif action.startswith("admin_toggle_city_"):
            city_id = int(action.split("_")[-1])
            await self.admin_toggle_city_status(update, context, user, city_id)
        elif action.startswith("admin_confirm_delete_city_"):
            city_id = int(action.split("_")[-1])
            await self.admin_confirm_delete_city(update, context, user, city_id)
        
        elif action == "admin_add_location":
            await self.admin_add_location(update, context, user)
        elif action == "admin_edit_location_status":
            await self.admin_edit_location_status(update, context, user)
        elif action == "admin_delete_location":
            await self.admin_delete_location(update, context, user)
        elif action.startswith("admin_toggle_location_"):
            location_id = int(action.split("_")[-1])
            await self.admin_toggle_location_status(update, context, user, location_id)
        elif action.startswith("admin_confirm_delete_location_"):
            location_id = int(action.split("_")[-1])
            await self.admin_confirm_delete_location(update, context, user, location_id)
        elif action.startswith("admin_select_city_for_location_"):
            city_id = int(action.split("_")[-1])
            context.user_data['selected_city_for_location'] = city_id
            context.user_data['awaiting_location_name'] = True
            await update.callback_query.edit_message_text(
                "📍 <b>Add New Location</b>\n\nEnter the name for the new location:",
                parse_mode=ParseMode.HTML
            )
        elif action == "admin_toggle_maintenance":
            await self.admin_toggle_maintenance(update, context, user)
        # Bot Settings sub-actions
        elif action.startswith("setting_"):
            await self.handle_setting_change(update, context, user, action)
        elif action == "admin_system_settings":
            await self.admin_system_settings(update, context, user)
    
    async def admin_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Add new product"""
        lang = user.get('language', 'en')
        
        # Get available categories
        categories = self.db.get_all_categories()
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(
                f"{category.get('emoji', '📦')} {category['name']}", 
                callback_data=f"admin_add_to_cat_{category['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Add New Category", callback_data="admin_add_category")])
        keyboard.append([InlineKeyboardButton(get_text('btn_back_admin', lang), callback_data="menu_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            f"📦 <b>Add Product</b>\n\nSelect a category to add product to:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_add_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Add inventory item"""
        lang = user.get('language', 'en')
        
        # Get available strains
        strains = self.db.get_all_strains()
        
        if not strains:
            keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "📦 <b>Add Inventory</b>\n\n❌ No product strains available. Please add products first.",
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = []
        for strain in strains:
            keyboard.append([InlineKeyboardButton(
                f"{strain['product_name']} - {strain['name']}", 
                callback_data=f"admin_inv_strain_{strain['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "📦 <b>Add Inventory</b>\n\nSelect a product strain to add inventory for:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_create_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create promo code"""
        lang = user.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton("💰 Balance Promo (Add Money)", callback_data="admin_promo_balance")],
            [InlineKeyboardButton("💸 Discount Promo (% Off)", callback_data="admin_promo_discount")],
            [InlineKeyboardButton("🆓 Free Product Promo", callback_data="admin_promo_free")],
            [InlineKeyboardButton("📋 View Active Promos", callback_data="admin_view_promos")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🎫 <b>Create Promo Code</b>\n\nSelect promo code type:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_create_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create discount - Main menu"""
        keyboard = [
            [InlineKeyboardButton("🏷️ Create New Discount", callback_data="admin_new_discount")],
            [InlineKeyboardButton("📋 View All Discounts", callback_data="admin_view_discounts")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "💰 <b>Discount Management</b>\n\nSelect an option:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_new_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create new discount - Step 1: Choose type"""
        keyboard = [
            [InlineKeyboardButton("🏷️ Category Discount", callback_data="admin_discount_type_category")],
            [InlineKeyboardButton("🌿 Product Discount", callback_data="admin_discount_type_product")],
            [InlineKeyboardButton("🌐 Global Discount", callback_data="admin_discount_type_global")],
            [InlineKeyboardButton("🔙 Back to Discounts", callback_data="admin_create_discount")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🏷️ <b>Create New Discount</b>\n\nSelect discount type:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_view_discounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: View all discounts"""
        discounts = self.db.get_all_discounts()
        
        if not discounts:
            keyboard = [[InlineKeyboardButton("🔙 Back to Discounts", callback_data="admin_create_discount")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "📋 <b>All Discounts</b>\n\n❌ No active discounts found.",
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = []
        discount_text = "📋 <b>All Discounts</b>\n\n"
        
        for discount in discounts:
            # Determine discount scope
            if discount['category_id']:
                scope = f"Category: {discount['category_name']}"
            elif discount['product_id']:
                scope = f"Product: {discount['product_name']}"
            else:
                scope = "Global"
            
            discount_text += f"🏷️ <b>{discount['name']}</b>\n"
            discount_text += f"   💸 {discount['percentage']}% off\n"
            discount_text += f"   📊 {scope}\n"
            if discount['min_order_amount'] > 0:
                discount_text += f"   💰 Min order: {discount['min_order_amount']:.2f} PLN\n"
            discount_text += f"   📅 Created: {discount['created_at'][:10]}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"📝 {discount['name']}", 
                callback_data=f"admin_discount_details_{discount['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Discounts", callback_data="admin_create_discount")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            discount_text,
            reply_markup,
            use_banner=False
        )
    
    async def admin_discount_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, discount_id: str):
        """Admin: View discount details"""
        discount = self.db.get_discount_by_id(int(discount_id))
        
        if not discount:
            keyboard = [[InlineKeyboardButton("🔙 Back to Discounts", callback_data="admin_view_discounts")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "❌ <b>Discount Not Found</b>\n\nThe discount may have been deleted.",
                reply_markup,
                use_banner=False
            )
            return
        
        # Determine discount scope
        if discount['category_id']:
            scope = f"Category: {discount['category_name']}"
        elif discount['product_id']:
            scope = f"Product: {discount['product_name']}"
        else:
            scope = "Global (All Products)"
        
        details_text = f"""📝 <b>Discount Details</b>

🏷️ <b>Name:</b> {discount['name']}
💸 <b>Percentage:</b> {discount['percentage']}%
📊 <b>Scope:</b> {scope}
💰 <b>Min Order:</b> {discount['min_order_amount']:.2f} PLN"""
        
        if discount['max_discount_amount']:
            details_text += f"\n🔝 <b>Max Discount:</b> {discount['max_discount_amount']:.2f} PLN"
        
        if discount['expires_at']:
            details_text += f"\n⏰ <b>Expires:</b> {discount['expires_at'][:10]}"
        
        details_text += f"\n📅 <b>Created:</b> {discount['created_at'][:10]}"
        details_text += f"\n✅ <b>Status:</b> {'Active' if discount['is_active'] else 'Inactive'}"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete Discount", callback_data=f"admin_delete_discount_{discount_id}")],
            [InlineKeyboardButton("🔙 Back to Discounts", callback_data="admin_view_discounts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            details_text,
            reply_markup,
            use_banner=False
        )
    
    async def admin_delete_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, discount_id: str):
        """Admin: Delete discount"""
        success = self.db.delete_discount(int(discount_id))
        
        if success:
            message = "✅ <b>Discount Deleted</b>\n\nThe discount has been successfully deleted."
        else:
            message = "❌ <b>Error</b>\n\nFailed to delete the discount. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Discounts", callback_data="admin_view_discounts")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_discount_select_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Select category for discount"""
        categories = self.db.get_all_categories()
        
        if not categories:
            keyboard = [[InlineKeyboardButton("🔙 Back to New Discount", callback_data="admin_new_discount")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "❌ <b>No Categories Found</b>\n\nPlease create categories first.",
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(
                f"{category['emoji']} {category['name']}",
                callback_data=f"admin_discount_cat_{category['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to New Discount", callback_data="admin_new_discount")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🏷️ <b>Select Category</b>\n\nChoose a category for the discount:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_discount_select_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Select product for discount"""
        products = self.db.get_all_products()
        
        if not products:
            keyboard = [[InlineKeyboardButton("🔙 Back to New Discount", callback_data="admin_new_discount")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "❌ <b>No Products Found</b>\n\nPlease create products first.",
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = []
        for product in products:
            keyboard.append([InlineKeyboardButton(
                f"{product['emoji']} {product['name']}",
                callback_data=f"admin_discount_prod_{product['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to New Discount", callback_data="admin_new_discount")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🌿 <b>Select Product</b>\n\nChoose a product for the discount:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_discount_create_global(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create global discount"""
        keyboard = [
            [InlineKeyboardButton("💸 10% Off", callback_data="admin_create_global_discount_10")],
            [InlineKeyboardButton("💸 15% Off", callback_data="admin_create_global_discount_15")],
            [InlineKeyboardButton("💸 20% Off", callback_data="admin_create_global_discount_20")],
            [InlineKeyboardButton("💸 25% Off", callback_data="admin_create_global_discount_25")],
            [InlineKeyboardButton("💸 30% Off", callback_data="admin_create_global_discount_30")],
            [InlineKeyboardButton("✏️ Custom %", callback_data="admin_custom_global_discount")],
            [InlineKeyboardButton("🔙 Back to New Discount", callback_data="admin_new_discount")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🌐 <b>Create Global Discount</b>\n\nSelect discount percentage:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_discount_create_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, category_id: str):
        """Admin: Create category discount"""
        # Store category_id for later use
        context.user_data['discount_category_id'] = category_id
        
        keyboard = [
            [InlineKeyboardButton("💸 10% Off", callback_data="admin_create_category_discount_10")],
            [InlineKeyboardButton("💸 15% Off", callback_data="admin_create_category_discount_15")],
            [InlineKeyboardButton("💸 20% Off", callback_data="admin_create_category_discount_20")],
            [InlineKeyboardButton("💸 25% Off", callback_data="admin_create_category_discount_25")],
            [InlineKeyboardButton("💸 30% Off", callback_data="admin_create_category_discount_30")],
            [InlineKeyboardButton("✏️ Custom %", callback_data="admin_custom_category_discount")],
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="admin_discount_type_category")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🏷️ <b>Create Category Discount</b>\n\nSelect discount percentage:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_discount_create_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, product_id: str):
        """Admin: Create product discount"""
        # Store product_id for later use
        context.user_data['discount_product_id'] = product_id
        
        keyboard = [
            [InlineKeyboardButton("💸 10% Off", callback_data="admin_create_product_discount_10")],
            [InlineKeyboardButton("💸 15% Off", callback_data="admin_create_product_discount_15")],
            [InlineKeyboardButton("💸 20% Off", callback_data="admin_create_product_discount_20")],
            [InlineKeyboardButton("💸 25% Off", callback_data="admin_create_product_discount_25")],
            [InlineKeyboardButton("💸 30% Off", callback_data="admin_create_product_discount_30")],
            [InlineKeyboardButton("✏️ Custom %", callback_data="admin_custom_product_discount")],
            [InlineKeyboardButton("🔙 Back to Products", callback_data="admin_discount_type_product")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🌿 <b>Create Product Discount</b>\n\nSelect discount percentage:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_finalize_global_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, percentage: int):
        """Admin: Finalize global discount creation"""
        import datetime
        
        # Generate discount name
        discount_name = f"Global {percentage}% Off"
        
        # Create discount
        success = self.db.create_discount(
            name=discount_name,
            percentage=percentage,
            category_id=None,
            product_id=None,
            min_order_amount=0,
            max_discount_amount=None,
            expires_at=None,
            created_by=user['user_id']
        )
        
        if success:
            message = f"✅ <b>Global Discount Created!</b>\n\n🌐 <b>Name:</b> {discount_name}\n💸 <b>Percentage:</b> {percentage}%\n🎯 <b>Scope:</b> All Products\n📅 <b>Status:</b> Active"
        else:
            message = "❌ <b>Failed to create discount</b>\n\nPlease try again."
        
        keyboard = [
            [InlineKeyboardButton("➕ Create Another", callback_data="admin_new_discount")],
            [InlineKeyboardButton("📋 View All Discounts", callback_data="admin_view_discounts")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_finalize_category_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, percentage: int):
        """Admin: Finalize category discount creation"""
        import datetime
        
        category_id = context.user_data.get('discount_category_id')
        if not category_id:
            await self.admin_new_discount(update, context, user)
            return
        
        # Get category info
        categories = self.db.get_all_categories()
        category = next((cat for cat in categories if str(cat['id']) == str(category_id)), None)
        
        if not category:
            await self.admin_new_discount(update, context, user)
            return
        
        # Generate discount name
        discount_name = f"{category['name']} {percentage}% Off"
        
        # Create discount
        success = self.db.create_discount(
            name=discount_name,
            percentage=percentage,
            category_id=category_id,
            product_id=None,
            min_order_amount=0,
            max_discount_amount=None,
            expires_at=None,
            created_by=user['user_id']
        )
        
        if success:
            message = f"✅ <b>Category Discount Created!</b>\n\n🏷️ <b>Name:</b> {discount_name}\n💸 <b>Percentage:</b> {percentage}%\n🎯 <b>Category:</b> {category['emoji']} {category['name']}\n📅 <b>Status:</b> Active"
        else:
            message = "❌ <b>Failed to create discount</b>\n\nPlease try again."
        
        keyboard = [
            [InlineKeyboardButton("➕ Create Another", callback_data="admin_new_discount")],
            [InlineKeyboardButton("📋 View All Discounts", callback_data="admin_view_discounts")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
        
        # Clear stored data
        context.user_data.pop('discount_category_id', None)
    
    async def admin_finalize_product_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, percentage: int):
        """Admin: Finalize product discount creation"""
        import datetime
        
        product_id = context.user_data.get('discount_product_id')
        if not product_id:
            await self.admin_new_discount(update, context, user)
            return
        
        # Get product info
        products = self.db.get_all_products()
        product = next((prod for prod in products if str(prod['id']) == str(product_id)), None)
        
        if not product:
            await self.admin_new_discount(update, context, user)
            return
        
        # Generate discount name
        discount_name = f"{product['name']} {percentage}% Off"
        
        # Create discount
        success = self.db.create_discount(
            name=discount_name,
            percentage=percentage,
            category_id=None,
            product_id=product_id,
            min_order_amount=0,
            max_discount_amount=None,
            expires_at=None,
            created_by=user['user_id']
        )
        
        if success:
            message = f"✅ <b>Product Discount Created!</b>\n\n🌿 <b>Name:</b> {discount_name}\n💸 <b>Percentage:</b> {percentage}%\n🎯 <b>Product:</b> {product['emoji']} {product['name']}\n📅 <b>Status:</b> Active"
        else:
            message = "❌ <b>Failed to create discount</b>\n\nPlease try again."
        
        keyboard = [
            [InlineKeyboardButton("➕ Create Another", callback_data="admin_new_discount")],
            [InlineKeyboardButton("📋 View All Discounts", callback_data="admin_view_discounts")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
        
        # Clear stored data
        context.user_data.pop('discount_product_id', None)
    
    async def admin_request_custom_global_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Request custom percentage for global discount"""
        context.user_data['awaiting_custom_global_discount'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_global")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "✏️ <b>Custom Global Discount</b>\n\nPlease enter the discount percentage (1-99):\n\nExample: 35",
            reply_markup,
            use_banner=False
        )
    
    async def admin_request_custom_category_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Request custom percentage for category discount"""
        context.user_data['awaiting_custom_category_discount'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_category")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "✏️ <b>Custom Category Discount</b>\n\nPlease enter the discount percentage (1-99):\n\nExample: 35",
            reply_markup,
            use_banner=False
        )
    
    async def admin_request_custom_product_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Request custom percentage for product discount"""
        context.user_data['awaiting_custom_product_discount'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_product")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "✏️ <b>Custom Product Discount</b>\n\nPlease enter the discount percentage (1-99):\n\nExample: 35",
            reply_markup,
            use_banner=False
        )
    
    async def process_custom_global_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, percentage_text: str):
        """Process custom global discount percentage input"""
        try:
            percentage = int(percentage_text.strip())
            if 1 <= percentage <= 99:
                await self.admin_finalize_global_discount(update, context, user, percentage)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_global")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ <b>Invalid Percentage</b>\n\nPlease enter a number between 1 and 99.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except ValueError:
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_global")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ <b>Invalid Input</b>\n\nPlease enter a valid number between 1 and 99.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    
    async def process_custom_category_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, percentage_text: str):
        """Process custom category discount percentage input"""
        try:
            percentage = int(percentage_text.strip())
            if 1 <= percentage <= 99:
                await self.admin_finalize_category_discount(update, context, user, percentage)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_category")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ <b>Invalid Percentage</b>\n\nPlease enter a number between 1 and 99.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except ValueError:
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_category")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ <b>Invalid Input</b>\n\nPlease enter a valid number between 1 and 99.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    
    async def process_custom_product_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, percentage_text: str):
        """Process custom product discount percentage input"""
        try:
            percentage = int(percentage_text.strip())
            if 1 <= percentage <= 99:
                await self.admin_finalize_product_discount(update, context, user, percentage)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_product")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ <b>Invalid Percentage</b>\n\nPlease enter a number between 1 and 99.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML
                )
        except ValueError:
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_discount_type_product")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ <b>Invalid Input</b>\n\nPlease enter a valid number between 1 and 99.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    
    async def admin_show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Show detailed statistics"""
        stats = self.db.get_detailed_statistics()
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        stats_text = f"""📊 <b>Detailed Statistics</b>

👥 Total Users: {stats.get('total_users', 0)}
📦 Total Orders: {stats.get('total_orders', 0)}
💰 Total Revenue: {format_currency(stats.get('total_revenue', 0))}
🎫 Active Promo Codes: {stats.get('active_promos', 0)}
📍 Total Locations: {stats.get('total_locations', 0)}
🏙️ Cities: {stats.get('total_cities', 0)}
🌿 Products: {stats.get('total_products', 0)}

📈 Today's Orders: {stats.get('today_orders', 0)}
💵 Today's Revenue: {format_currency(stats.get('today_revenue', 0))}

🔥 Most Popular Product: {stats.get('popular_product', 'N/A')}
🏆 Top City: {stats.get('top_city', 'N/A')}"""
        
        await self.send_menu_with_banner(
            update,
            stats_text,
            reply_markup,
            use_banner=False
        )
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ Access denied. You are not authorized.")
            return
        
        # Get user data for consistency with show_admin_panel
        user = self.db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found in database.")
            return
        
        # Clear the entire chat by deleting all recent messages
        chat_id = update.effective_chat.id
        current_message_id = update.message.message_id
        
        # Delete the last 100 messages (including the /admin command itself)
        for i in range(100):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=current_message_id - i)
            except Exception:
                # Stop when we can't delete more messages (reached the limit or old messages)
                break
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Product", callback_data="admin_add_product"),
             InlineKeyboardButton("📦 Add Inventory", callback_data="admin_add_inventory")],
            [InlineKeyboardButton("🎫 Create Promo Code", callback_data="admin_create_promo"),
             InlineKeyboardButton("💰 Create Discount", callback_data="admin_create_discount")],
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
             InlineKeyboardButton("👥 User Management", callback_data="admin_user_management")],
            [InlineKeyboardButton("⚙️ System Settings", callback_data="admin_system_settings"),
             InlineKeyboardButton("🗄️ Database Tools", callback_data="admin_database_tools")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the admin panel after clearing the chat
        await update.effective_chat.send_message(
            text="👑 <b>Admin Panel</b>\n\nSelect an action:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def admin_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: User management panel"""
        keyboard = [
            [InlineKeyboardButton("👥 View All Users", callback_data="admin_view_users")],
            [InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
            [InlineKeyboardButton("💰 Add Balance to User", callback_data="admin_add_balance")],
            [InlineKeyboardButton("🚫 Ban/Unban User", callback_data="admin_ban_user")],
            [InlineKeyboardButton("📊 User Statistics", callback_data="admin_user_stats")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "👥 <b>User Management</b>\n\nSelect an option:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_system_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: System settings panel"""
        keyboard = [
            [InlineKeyboardButton("🌐 Bot Settings", callback_data="admin_bot_settings")],
            [InlineKeyboardButton("🏙️ Manage Cities", callback_data="admin_manage_cities")],
            [InlineKeyboardButton("📍 Manage Locations", callback_data="admin_manage_locations")],
            [InlineKeyboardButton("🔧 Maintenance Mode", callback_data="admin_maintenance")],
            [InlineKeyboardButton("📝 Bot Logs", callback_data="admin_view_logs")],
            [InlineKeyboardButton("🧹 Test Cleanup", callback_data="admin_test_cleanup")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "⚙️ <b>System Settings</b>\n\nSelect an option:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_bot_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Bot settings management"""
        config = self.config
        maintenance_status = "🔴 ON" if config.get('maintenance_mode', False) else "🟢 OFF"
        
        settings_text = f"""🌐 <b>Bot Settings</b>

📝 <b>Current Configuration:</b>
• Bot Name: {config.get('bot_name', 'TeleShop')}
• Description: {config.get('bot_description', 'Digital Store')}
• Currency: {config.get('currency_symbol', '$')}
• Default Language: {config.get('default_language', 'en').upper()}
• Maintenance Mode: {maintenance_status}
• Max Orders/User: {config.get('max_orders_per_user', 10)}
• Min Balance Required: {config.get('currency_symbol', '$')}{config.get('min_balance_required', 0.0)}
• Support Contact: {config.get('support_contact', '@admin')}

🔧 <b>Select setting to modify:</b>"""
        
        keyboard = [
            [InlineKeyboardButton("📝 Bot Name", callback_data="setting_bot_name"),
             InlineKeyboardButton("📄 Description", callback_data="setting_description")],
            [InlineKeyboardButton("💰 Currency Symbol", callback_data="setting_currency"),
             InlineKeyboardButton("🌍 Default Language", callback_data="setting_language")],
            [InlineKeyboardButton("🔧 Maintenance Mode", callback_data="setting_maintenance"),
             InlineKeyboardButton("📊 Max Orders/User", callback_data="setting_max_orders")],
            [InlineKeyboardButton("💳 Min Balance", callback_data="setting_min_balance"),
             InlineKeyboardButton("📞 Support Contact", callback_data="setting_support")],
            [InlineKeyboardButton("💬 Welcome Message", callback_data="setting_welcome")],
            [InlineKeyboardButton("💾 Save & Restart Bot", callback_data="setting_save_restart")],
            [InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            settings_text,
            reply_markup,
            use_banner=False
        )
    
    async def handle_setting_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, action: str):
        """Handle bot setting changes"""
        setting_type = action.replace("setting_", "")
        
        if setting_type == "maintenance":
            # Toggle maintenance mode
            current_mode = self.config.get('maintenance_mode', False)
            self.config['maintenance_mode'] = not current_mode
            self.save_bot_config()
            
            status = "🔴 ENABLED" if self.config['maintenance_mode'] else "🟢 DISABLED"
            await update.callback_query.answer(f"Maintenance mode {status}", show_alert=True)
            await self.admin_bot_settings(update, context, user)
            
        elif setting_type == "save_restart":
            # Save configuration and show restart message
            if self.save_bot_config():
                await update.callback_query.edit_message_text(
                    "💾 <b>Configuration Saved!</b>\n\n"
                    "⚠️ <b>Important:</b> Some changes require a bot restart to take effect.\n\n"
                    "Please restart the bot manually to apply all changes.\n\n"
                    "Use /admin to return to admin panel."
                )
            else:
                await update.callback_query.answer("❌ Error saving configuration!", show_alert=True)
                
        else:
            # For text input settings, set up the input state
            context.user_data['setting_to_change'] = setting_type
            context.user_data['awaiting_setting_input'] = True
            
            setting_prompts = {
                'bot_name': '📝 Enter new bot name:',
                'description': '📄 Enter new bot description:',
                'currency': '💰 Enter new currency symbol:',
                'language': '🌍 Enter new default language code (en, es, fr, etc.):',
                'max_orders': '📊 Enter maximum orders per user:',
                'min_balance': '💳 Enter minimum balance required:',
                'support': '📞 Enter new support contact:',
                'welcome': '💬 Enter new welcome message:'
            }
            
            prompt = setting_prompts.get(setting_type, 'Enter new value:')
            current_value = self.config.get({
                'bot_name': 'bot_name',
                'description': 'bot_description', 
                'currency': 'currency_symbol',
                'language': 'default_language',
                'max_orders': 'max_orders_per_user',
                'min_balance': 'min_balance_required',
                'support': 'support_contact',
                'welcome': 'welcome_message'
            }.get(setting_type, setting_type), 'Not set')
            
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_bot_settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                 f"🔧 <b>Change Setting</b>\n\n"
                 f"{prompt}\n\n"
                 f"<b>Current value:</b> {current_value}\n\n"
                 f"Send your new value as a message.",
                 reply_markup=reply_markup
             )
    
    async def process_setting_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process setting input from admin"""
        setting_type = context.user_data.get('setting_to_change')
        new_value = update.message.text.strip()
        
        if not setting_type:
            return
        
        # Validate and convert input based on setting type
        try:
            if setting_type == 'max_orders':
                new_value = int(new_value)
                if new_value < 1:
                    await update.message.reply_text("❌ Max orders must be at least 1.")
                    return
                self.config['max_orders_per_user'] = new_value
                
            elif setting_type == 'min_balance':
                new_value = float(new_value)
                if new_value < 0:
                    await update.message.reply_text("❌ Minimum balance cannot be negative.")
                    return
                self.config['min_balance_required'] = new_value
                
            elif setting_type == 'language':
                if len(new_value) != 2:
                    await update.message.reply_text("❌ Language code must be 2 characters (e.g., 'en', 'es').")
                    return
                self.config['default_language'] = new_value.lower()
                
            elif setting_type == 'currency':
                if len(new_value) > 5:
                    await update.message.reply_text("❌ Currency symbol too long (max 5 characters).")
                    return
                self.config['currency_symbol'] = new_value
                
            elif setting_type == 'bot_name':
                if len(new_value) > 50:
                    await update.message.reply_text("❌ Bot name too long (max 50 characters).")
                    return
                self.config['bot_name'] = new_value
                
            elif setting_type == 'description':
                if len(new_value) > 100:
                    await update.message.reply_text("❌ Description too long (max 100 characters).")
                    return
                self.config['bot_description'] = new_value
                
            elif setting_type == 'support':
                if not new_value.startswith('@') and not new_value.startswith('http'):
                    await update.message.reply_text("❌ Support contact should start with @ or be a URL.")
                    return
                self.config['support_contact'] = new_value
                
            elif setting_type == 'welcome':
                if len(new_value) > 200:
                    await update.message.reply_text("❌ Welcome message too long (max 200 characters).")
                    return
                self.config['welcome_message'] = new_value
            
            # Save configuration
            if self.save_bot_config():
                await update.message.reply_text(
                    f"✅ <b>Setting Updated!</b>\n\n"
                    f"<b>{setting_type.replace('_', ' ').title()}:</b> {new_value}\n\n"
                    f"Configuration saved successfully.",
                    parse_mode=ParseMode.HTML
                )
                
                # Clear the input state
                context.user_data.pop('awaiting_setting_input', None)
                context.user_data.pop('setting_to_change', None)
                
                # Show updated bot settings
                await self.admin_bot_settings_new_message(update, context, user)
            else:
                await update.message.reply_text("❌ Error saving configuration. Please try again.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid input format. Please enter a valid value.")
        except Exception as e:
            logger.error(f"Error processing setting input: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def admin_bot_settings_new_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show bot settings in a new message (for after text input)"""
        config = self.config
        maintenance_status = "🔴 ON" if config.get('maintenance_mode', False) else "🟢 OFF"
        
        settings_text = f"""🌐 <b>Bot Settings</b>\n\n📝 <b>Current Configuration:</b>\n• Bot Name: {config.get('bot_name', 'TeleShop')}\n• Description: {config.get('bot_description', 'Digital Store')}\n• Currency: {config.get('currency_symbol', '$')}\n• Default Language: {config.get('default_language', 'en').upper()}\n• Maintenance Mode: {maintenance_status}\n• Max Orders/User: {config.get('max_orders_per_user', 10)}\n• Min Balance Required: {config.get('currency_symbol', '$')}{config.get('min_balance_required', 0.0)}\n• Support Contact: {config.get('support_contact', '@admin')}\n\n🔧 <b>Select setting to modify:</b>"""
        
        keyboard = [
            [InlineKeyboardButton("📝 Bot Name", callback_data="setting_bot_name"),
             InlineKeyboardButton("📄 Description", callback_data="setting_description")],
            [InlineKeyboardButton("💰 Currency Symbol", callback_data="setting_currency"),
             InlineKeyboardButton("🌍 Default Language", callback_data="setting_language")],
            [InlineKeyboardButton("🔧 Maintenance Mode", callback_data="setting_maintenance"),
             InlineKeyboardButton("📊 Max Orders/User", callback_data="setting_max_orders")],
            [InlineKeyboardButton("💳 Min Balance", callback_data="setting_min_balance"),
             InlineKeyboardButton("📞 Support Contact", callback_data="setting_support")],
            [InlineKeyboardButton("💬 Welcome Message", callback_data="setting_welcome")],
            [InlineKeyboardButton("💾 Save & Restart Bot", callback_data="setting_save_restart")],
            [InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
     
    async def admin_view_active_promos(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: View active promo codes"""
        promos = self.db.get_active_promo_codes()
        
        if not promos:
            promo_text = "📋 <b>Active Promo Codes</b>\n\n❌ No active promo codes found."
        else:
            promo_text = "📋 <b>Active Promo Codes</b>\n\n"
            for promo in promos:
                promo_text += f"🎫 <code>{promo['code']}</code>\n"
                promo_text += f"   💰 Value: {promo['value']} {promo['type']}\n"
                promo_text += f"   📊 Uses: {promo['current_uses']}/{promo['max_uses']}\n"
                promo_text += f"   📅 Created: {promo['created_at'][:10]}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete Promo", callback_data="admin_delete_promo")],
            [InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            promo_text,
            reply_markup,
            use_banner=False
        )
    
    async def admin_create_balance_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create balance promo code"""
        # Generate random promo code
        import string
        promo_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        keyboard = [
            [InlineKeyboardButton("💰 10 PLN", callback_data=f"admin_create_bal_promo_{promo_code}_10")],
            [InlineKeyboardButton("💰 25 PLN", callback_data=f"admin_create_bal_promo_{promo_code}_25")],
            [InlineKeyboardButton("💰 50 PLN", callback_data=f"admin_create_bal_promo_{promo_code}_50")],
            [InlineKeyboardButton("💰 100 PLN", callback_data=f"admin_create_bal_promo_{promo_code}_100")],
            [InlineKeyboardButton("✏️ Custom Amount", callback_data=f"admin_custom_bal_promo_{promo_code}")],
            [InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            f"💰 <b>Create Balance Promo</b>\n\nGenerated Code: <code>{promo_code}</code>\n\nSelect amount to add:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_create_discount_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create discount promo code"""
        # Generate random promo code
        import string
        promo_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        keyboard = [
            [InlineKeyboardButton("💸 10% Off", callback_data=f"admin_create_disc_promo_{promo_code}_10")],
            [InlineKeyboardButton("💸 25% Off", callback_data=f"admin_create_disc_promo_{promo_code}_25")],
            [InlineKeyboardButton("💸 50% Off", callback_data=f"admin_create_disc_promo_{promo_code}_50")],
            [InlineKeyboardButton("💸 75% Off", callback_data=f"admin_create_disc_promo_{promo_code}_75")],
            [InlineKeyboardButton("✏️ Custom %", callback_data=f"admin_custom_disc_promo_{promo_code}")],
            [InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            f"💸 <b>Create Discount Promo</b>\n\nGenerated Code: <code>{promo_code}</code>\n\nSelect discount percentage:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_create_free_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create free product promo code"""
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🆓 <b>Free Product Promo</b>\n\n🚧 This feature will be implemented soon.\nIt will allow creating promo codes for free products.",
            reply_markup,
            use_banner=False
        )
    
    async def admin_database_tools(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Database management tools"""
        keyboard = [
            [InlineKeyboardButton("📊 Database Stats", callback_data="admin_db_stats")],
            [InlineKeyboardButton("🧹 Clean Old Data", callback_data="admin_clean_data")],
            [InlineKeyboardButton("💾 Backup Database", callback_data="admin_backup_db")],
            [InlineKeyboardButton("🔄 Reset Test Data", callback_data="admin_reset_test")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "🗄️ <b>Database Tools</b>\n\nSelect an option:",
            reply_markup,
            use_banner=False
        )
    
    async def admin_confirm_balance_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str, amount: str):
        """Admin: Confirm balance promo creation"""
        try:
            amount_value = float(amount)
            success = self.db.create_promo_code(
                code=promo_code,
                value=amount_value,
                code_type='balance',
                max_uses=1,
                created_by=user['user_id']
            )
            
            if success:
                # Generate promotional image
                try:
                    promo_image = await self.generate_promo_image_with_timeout(
                        promo_code=promo_code,
                        discount_type="Balance",
                        value=f"{amount_value} PLN",
                        promo_type="balance",
                        bot_name=self.config.get('bot_name', 'TELESHOP')
                    )
                    
                    # Send the promotional image
                    await update.callback_query.message.reply_photo(
                        photo=promo_image,
                        caption=f"✅ <b>Balance Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💰 Value: {amount_value} PLN\n📊 Max Uses: 1\n\n<i>Share this beautiful promo image with your customers!</i>",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Also send text message with buttons
                    message = f"🎉 <b>Promo Image Generated!</b>\n\nThe promotional image has been created and sent above. You can now share this attractive promo code image with your customers!"
                    
                except Exception as e:
                    logger.error(f"Failed to generate promo image: {e}")
                    message = f"✅ <b>Balance Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💰 Value: {amount_value} PLN\n📊 Max Uses: 1\n\n⚠️ <i>Image generation failed, but promo code was created successfully.</i>"
            else:
                message = f"❌ <b>Failed to create promo code</b>\n\nCode might already exist."
            
        except ValueError:
            message = f"❌ <b>Invalid amount</b>\n\nPlease try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_confirm_discount_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str, percentage: str):
        """Admin: Confirm discount promo creation"""
        try:
            percentage_value = float(percentage)
            success = self.db.create_promo_code(
                code=promo_code,
                value=percentage_value,
                code_type='discount',
                max_uses=1,
                created_by=user['user_id']
            )
            
            if success:
                # Generate promotional image
                try:
                    promo_image = await self.generate_promo_image_with_timeout(
                        promo_code=promo_code,
                        discount_type="Discount",
                        value=f"{percentage_value}%",
                        promo_type="discount",
                        bot_name=self.config.get('bot_name', 'TELESHOP')
                    )
                    
                    # Send the promotional image
                    await update.callback_query.message.reply_photo(
                        photo=promo_image,
                        caption=f"✅ <b>Discount Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💸 Discount: {percentage_value}%\n📊 Max Uses: 1\n\n<i>Share this beautiful promo image with your customers!</i>",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Also send text message with buttons
                    message = f"🎉 <b>Promo Image Generated!</b>\n\nThe promotional image has been created and sent above. You can now share this attractive promo code image with your customers!"
                    
                except Exception as e:
                    logger.error(f"Failed to generate promo image: {e}")
                    message = f"✅ <b>Discount Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💸 Discount: {percentage_value}%\n📊 Max Uses: 1\n\n⚠️ <i>Image generation failed, but promo code was created successfully.</i>"
            else:
                message = f"❌ <b>Failed to create promo code</b>\n\nCode might already exist."
            
        except ValueError:
            message = f"❌ <b>Invalid percentage</b>\n\nPlease try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_custom_balance_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str):
        """Admin: Handle custom balance promo amount input"""
        context.user_data['admin_action'] = 'custom_balance_promo'
        context.user_data['promo_code'] = promo_code
        
        message = f"💰 <b>Custom Balance Promo</b>\n\n🎫 Code: <code>{promo_code}</code>\n\nPlease enter the custom balance amount (in PLN):\n\n<i>Example: 25.50</i>"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_custom_discount_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str):
        """Admin: Handle custom discount promo percentage input"""
        context.user_data['admin_action'] = 'custom_discount_promo'
        context.user_data['promo_code'] = promo_code
        
        message = f"💸 <b>Custom Discount Promo</b>\n\n🎫 Code: <code>{promo_code}</code>\n\nPlease enter the custom discount percentage:\n\n<i>Example: 15 (for 15% discount)</i>"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_add_product_to_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, category_id: str):
        """Admin: Add product to specific category"""
        lang = user.get('language', 'en')
        
        # Store category_id in context for later use
        context.user_data['admin_category_id'] = category_id
        context.user_data['admin_action'] = 'add_product'
        
        message = f"📦 <b>Add New Product</b>\n\nPlease enter the product details in the following format:\n\n<code>Name | Description | Base Price | Emoji</code>\n\nExample:\n<code>Premium Weed | High quality cannabis | 50.0 | 🌿</code>\n\n<i>Note: Emoji is optional (default: 🌿)</i>"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Categories", callback_data="admin_add_product")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_add_new_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Add new product category"""
        lang = user.get('language', 'en')
        
        # Store action in context for later use
        context.user_data['admin_action'] = 'add_category'
        
        message = "📦 <b>Add New Category</b>\n\nPlease enter the category details in the following format:\n\n<code>Name | Description | Emoji</code>\n\nExample:\n<code>Cannabis | High-quality cannabis products | 🌿</code>\n\n<i>Note: Description and Emoji are optional (default emoji: 📦)</i>"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Categories", callback_data="admin_add_product")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def admin_add_inventory_for_strain(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, strain_id: str):
        """Admin: Add inventory for specific strain - first ask for city"""
        # Get available cities
        cities = self.db.get_cities()
        
        if not cities:
            keyboard = [[InlineKeyboardButton("🔙 Back to Strains", callback_data="admin_add_inventory")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "📦 <b>Add Inventory</b>\n\n❌ No cities available. Please add cities first.",
                reply_markup,
                use_banner=False
            )
            return
        
        # Store strain_id in context
        context.user_data['admin_strain_id'] = strain_id
        context.user_data['admin_action'] = 'add_inventory_select_city'
        
        keyboard = []
        for city in cities:
            keyboard.append([InlineKeyboardButton(
                f"🏙️ {city['name']}", 
                callback_data=f"admin_inv_city_{city['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Strains", callback_data="admin_add_inventory")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            "📦 <b>Add Inventory</b>\n\nFirst, select a city:",
            reply_markup,
            use_banner=False
        )

    async def admin_select_city_for_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, city_id: str):
        """Admin: Select city and show locations for inventory"""
        # Get locations in the selected city
        locations = self.db.get_locations_by_city(int(city_id))
        
        if not locations:
            keyboard = [[InlineKeyboardButton("🔙 Back to Cities", callback_data=f"admin_inv_strain_{context.user_data.get('admin_strain_id', '0')}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                "📦 <b>Add Inventory</b>\n\n❌ No locations available in this city. Please add locations first.",
                reply_markup,
                use_banner=False
            )
            return
        
        # Store city_id in context
        context.user_data['admin_city_id'] = city_id
        context.user_data['admin_action'] = 'add_inventory'
        
        # Get city name for display
        city_name = locations[0]['city_name'] if locations else f"City {city_id}"
        
        keyboard = []
        for location in locations:
            keyboard.append([InlineKeyboardButton(
                f"📍 {location['name']}", 
                callback_data=f"admin_inv_loc_{location['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Cities", callback_data=f"admin_inv_strain_{context.user_data.get('admin_strain_id', '0')}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            f"📦 <b>Add Inventory</b>\n\nCity: <b>{city_name}</b>\n\nSelect a location to add inventory for:",
            reply_markup,
            use_banner=False
        )

    async def admin_select_location_for_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, location_id: str):
        """Admin: Select location and ask for inventory details"""
        # Store location_id in context
        context.user_data['admin_location_id'] = location_id
        context.user_data['admin_action'] = 'add_inventory_banner_photo'
        
        # Get location details
        location = self.db.get_location_details(int(location_id))
        location_name = location['name'] if location else f"Location {location_id}"
        
        # Get strain details to show the calculated price
        strain_data = self.db.get_strain_with_price(int(context.user_data.get('admin_strain_id', 0)))
        price_info = f"\n\n💰 <b>Price:</b> {strain_data['calculated_price']:.2f} (calculated from product base price)" if strain_data else ""
        
        message = f"📦 <b>Add Inventory</b>\n\nLocation: <b>{location_name}</b>{price_info}\n\n📸 <b>Step 1: Product Photos</b>\n\nPlease send a banner image for this product (this will be shown to users when they purchase).\n\nYou can also type 'skip' to proceed without adding photos."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Locations", callback_data=f"admin_inv_strain_{context.user_data.get('admin_strain_id', '0')}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    @rate_limit_check
    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all text input - captcha responses, promo codes, and admin text input"""
        user_id = update.effective_user.id
        
        # First check if this is a captcha response
        session = self.session_manager.get_session(user_id)
        if session:
            await self.handle_captcha_response(update, context)
            return
        
        # Check if user is awaiting promo code
        if context.user_data.get('awaiting_promo'):
            user = self.db.get_user(user_id)
            if user:
                await self.process_promo_code(update, context, user, update.message.text)
            context.user_data['awaiting_promo'] = False
            return
        
        # Check if user is awaiting purchase promo code
        if context.user_data.get('awaiting_purchase_promo'):
            user = self.db.get_user(user_id)
            if user:
                await self.process_purchase_promo_code(update, context, user, update.message.text)
            context.user_data['awaiting_purchase_promo'] = False
            return
        
        # Check if admin is awaiting custom discount percentage
        if context.user_data.get('awaiting_custom_global_discount'):
            user = self.db.get_user(user_id)
            if user and self.is_admin(user_id):
                await self.process_custom_global_discount(update, context, user, update.message.text)
            context.user_data['awaiting_custom_global_discount'] = False
            return
        
        if context.user_data.get('awaiting_custom_category_discount'):
            user = self.db.get_user(user_id)
            if user and self.is_admin(user_id):
                await self.process_custom_category_discount(update, context, user, update.message.text)
            context.user_data['awaiting_custom_category_discount'] = False
            return
        
        if context.user_data.get('awaiting_custom_product_discount'):
            user = self.db.get_user(user_id)
            if user and self.is_admin(user_id):
                await self.process_custom_product_discount(update, context, user, update.message.text)
            context.user_data['awaiting_custom_product_discount'] = False
            return
        
        # Check if user is awaiting crypto amount input
        if context.user_data.get('awaiting_crypto_amount'):
            user = self.db.get_user(user_id)
            if user:
                await self.crypto_handler.process_custom_amount_input(update, context, user, update.message.text)
            context.user_data.pop('awaiting_crypto_amount', None)
            return
        
        # Check if admin is awaiting custom balance promo amount
        if context.user_data.get('awaiting_custom_balance_amount'):
            user = self.db.get_user(user_id)
            if user and self.is_admin(user_id):
                await self.process_custom_balance_promo(update, context, user)
            context.user_data.pop('awaiting_custom_balance_amount', None)
            return
        
        # Check for user management text inputs
        user = self.db.get_user(user_id)
        if user and self.is_admin(user_id):
            # User search input
            if context.user_data.get('awaiting_user_search'):
                await self.admin_search_user(update, context, user)
                return
            
            # Balance management inputs
            if context.user_data.get('awaiting_balance_user_id') or context.user_data.get('awaiting_balance_amount'):
                await self.admin_add_balance(update, context, user)
                return
            
            # Ban management input
            if context.user_data.get('awaiting_ban_user_id'):
                await self.admin_ban_user(update, context, user)
                return
        
        # Then check if this is admin text input
        await self.handle_admin_text_input(update, context)
    
    async def handle_admin_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input for admin operations"""
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not self.is_admin(user_id):
            return
        
        # Get user data
        user = self.db.get_user(user_id)
        if not user:
            return
        
        # Check if admin is in the middle of an action
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'add_category':
            await self.process_add_category(update, context, user)
        elif admin_action == 'add_product':
            await self.process_add_product(update, context, user)
        elif admin_action == 'custom_balance_promo':
            await self.process_custom_balance_promo(update, context, user)
        elif admin_action == 'custom_discount_promo':
            await self.process_custom_discount_promo(update, context, user)
        elif admin_action == 'add_inventory_banner_photo':
            # Handle skip for banner photo
            if update.message.text.lower().strip() == 'skip':
                await update.message.reply_text(
                    "📸 Banner photo skipped.\n\n"
                    "Now please send a download image (optional - this can be a different angle or detail shot).\n\n"
                    "You can type 'skip' to proceed without a download image."
                )
                context.user_data['admin_action'] = 'add_inventory_download_photo'
            else:
                await update.message.reply_text("Please send a photo or type 'skip' to proceed without photos.")
        elif admin_action == 'add_inventory_download_photo':
            # Handle skip for download photo
            if update.message.text.lower().strip() == 'skip':
                await update.message.reply_text(
                    "📸 Download photo skipped.\n\n"
                    "Now please enter the inventory details in the following format:\n\n"
                    "<code>Coordinates | Quantity | Unit | Description</code>\n\n"
                    "Example:\n"
                    "<code>52.2297,21.0122 | 10.0 | g | Premium quality product</code>\n\n"
                    "<i>Note: Unit defaults to 'g' if not specified.</i>",
                    parse_mode=ParseMode.HTML
                )
                context.user_data['admin_action'] = 'add_inventory_details'
            else:
                await update.message.reply_text("Please send a photo or type 'skip' to proceed without a download image.")
        elif admin_action == 'add_inventory_details':
            await self.process_add_inventory(update, context, user)
        
        # Handle bot setting input
        elif context.user_data.get('awaiting_setting_input'):
            await self.process_setting_input(update, context, user)
    
    async def process_add_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process adding a new category"""
        text = update.message.text.strip()
        parts = [part.strip() for part in text.split('|')]
        
        if len(parts) < 1:
            await update.message.reply_text("❌ Invalid format. Please use: Name | Description | Emoji")
            return
        
        name = parts[0]
        description = parts[1] if len(parts) > 1 else None
        emoji = parts[2] if len(parts) > 2 else '📦'
        
        # Create category
        category_id = self.db.create_category(name, description, emoji)
        
        if category_id > 0:
            await update.message.reply_text(f"✅ Category '{name}' created successfully!")
            # Clear admin action
            context.user_data.pop('admin_action', None)
            # Show admin add product menu again
            await self.admin_add_product(update, context, user)
        else:
            await update.message.reply_text("❌ Failed to create category. Please try again.")
    
    async def process_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process adding a new product"""
        text = update.message.text.strip()
        parts = [part.strip() for part in text.split('|')]
        
        if len(parts) < 3:
            await update.message.reply_text("❌ Invalid format. Please use: Name | Description | Base Price | Emoji")
            return
        
        name = parts[0]
        description = parts[1]
        try:
            base_price = float(parts[2])
        except ValueError:
            await update.message.reply_text("❌ Invalid price format. Please enter a valid number.")
            return
        
        emoji = parts[3] if len(parts) > 3 else '🌿'
        category_id = context.user_data.get('admin_category_id')
        
        if not category_id:
            await update.message.reply_text("❌ Category not found. Please try again.")
            return
        
        # Create product
        product_id = self.db.create_product(int(category_id), name, description, base_price, emoji)
        
        if product_id > 0:
            # Create a default strain for the product
            strain_id = self.db.create_product_strain(
                product_id, 
                f"Standard {name}", 
                f"Standard variant of {name}",
                0.0, 0.0, "Standard effects"
            )
            
            if strain_id > 0:
                await update.message.reply_text(f"✅ Product '{name}' and default strain created successfully!")
            else:
                await update.message.reply_text(f"✅ Product '{name}' created successfully! (Warning: Default strain creation failed)")
            
            # Clear admin action and category_id
            context.user_data.pop('admin_action', None)
            context.user_data.pop('admin_category_id', None)
            # Show admin add product menu again
            await self.admin_add_product(update, context, user)
        else:
            await update.message.reply_text("❌ Failed to create product. Please try again.")
    
    async def process_add_inventory(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process adding inventory details"""
        text = update.message.text.strip()
        parts = [part.strip() for part in text.split('|')]
        
        if len(parts) < 2:
            await update.message.reply_text("❌ Invalid format. Please use: Coordinates | Quantity | Unit | Description")
            return
        
        coordinates = parts[0]
        try:
            quantity = float(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Invalid quantity format. Please enter a valid number.")
            return
        
        unit = parts[2] if len(parts) > 2 else 'g'
        description = parts[3] if len(parts) > 3 else None
        
        strain_id = context.user_data.get('admin_strain_id')
        location_id = context.user_data.get('admin_location_id')
        
        if not strain_id or not location_id:
            await update.message.reply_text("❌ Missing strain or location information. Please try again.")
            return
        
        # Get stored photo file_ids
        banner_image = context.user_data.get('banner_image')
        download_image = context.user_data.get('download_image')
        
        # Add inventory item (price is calculated automatically)
        inventory_id = self.db.add_inventory_item(
            int(strain_id), int(location_id), coordinates, 
            quantity, unit, banner_image, download_image, description
        )
        
        if inventory_id > 0:
            # Get the calculated price to show in confirmation
            strain_data = self.db.get_strain_with_price(int(strain_id))
            price_text = f" (Price: {strain_data['calculated_price']:.2f})" if strain_data else ""
            await update.message.reply_text(f"✅ Inventory added successfully! ID: {inventory_id}{price_text}")
            # Clear admin action data
            context.user_data.pop('admin_action', None)
            context.user_data.pop('admin_strain_id', None)
            context.user_data.pop('admin_location_id', None)
            context.user_data.pop('banner_image', None)
            context.user_data.pop('download_image', None)
            # Show admin inventory menu again
            await self.admin_add_inventory(update, context, user)
        else:
            await update.message.reply_text("❌ Failed to add inventory. Please try again.")

    async def process_custom_balance_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process custom balance promo amount input"""
        try:
            # Check if this is a callback query (initial call) or message (amount input)
            if update.callback_query:
                # This is the initial call from callback, prompt for amount
                promo_code = context.user_data.get('custom_balance_promo_code')
                if not promo_code:
                    await update.callback_query.answer("❌ Error: Promo code not found.")
                    return
                
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    f"💰 <b>Custom Balance Promo</b>\n\n🎫 Code: <code>{promo_code}</code>\n\n💵 Please enter the balance amount (in PLN):",
                    parse_mode=ParseMode.HTML
                )
                
                # Set state to wait for amount input
                context.user_data['awaiting_custom_balance_amount'] = True
                context.user_data['promo_code'] = promo_code
                return
            
            # This is a message with the amount
            if not update.message or not update.message.text:
                return
                
            amount_value = float(update.message.text.strip())
            promo_code = context.user_data.get('promo_code')
            
            if not promo_code:
                await update.message.reply_text("❌ Error: Promo code not found. Please try again.")
                return
            
            success = self.db.create_promo_code(
                code=promo_code,
                value=amount_value,
                code_type='balance',
                max_uses=1,
                created_by=user['user_id']
            )
            
            if success:
                # Generate promotional image
                try:
                    promo_image = await self.generate_promo_image_with_timeout(
                        promo_code=promo_code,
                        discount_type="Balance",
                        value=f"{amount_value} PLN",
                        promo_type="balance",
                        bot_name=self.config.get('bot_name', 'TELESHOP')
                    )
                    
                    # Send the promotional image
                    await update.message.reply_photo(
                        photo=promo_image,
                        caption=f"✅ <b>Custom Balance Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💰 Value: {amount_value} PLN\n📊 Max Uses: 1\n\n<i>Share this beautiful promo image with your customers!</i>",
                        parse_mode=ParseMode.HTML
                    )
                    
                    message = f"🎉 <b>Promo Image Generated!</b>\n\nThe promotional image has been created and sent above. You can now share this attractive promo code image with your customers!"
                    
                except Exception as e:
                    logger.error(f"Failed to generate promo image: {e}")
                    message = f"✅ <b>Custom Balance Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💰 Value: {amount_value} PLN\n📊 Max Uses: 1\n\n⚠️ <i>Image generation failed, but promo code was created successfully.</i>"
            else:
                message = f"❌ <b>Failed to create promo code</b>\n\nCode might already exist."
            
        except ValueError:
            message = f"❌ <b>Invalid amount</b>\n\nPlease enter a valid number."
        
        # Clear admin action
        context.user_data.pop('admin_action', None)
        context.user_data.pop('promo_code', None)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )
    
    async def process_preset_balance_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, promo_code: str, amount: float):
        """Process preset balance promo creation with predefined amount"""
        try:
            success = self.db.create_promo_code(
                code=promo_code,
                value=amount,
                code_type='balance',
                max_uses=1,
                created_by=user['user_id']
            )
            
            if success:
                # Generate promotional image
                try:
                    promo_image = await self.generate_promo_image_with_timeout(
                        promo_code=promo_code,
                        discount_type="Balance",
                        value=f"{amount} PLN",
                        promo_type="balance",
                        bot_name=self.config.get('bot_name', 'TELESHOP')
                    )
                    
                    # Send the promotional image
                    await update.callback_query.edit_message_media(
                        media=InputMediaPhoto(
                            media=promo_image,
                            caption=f"✅ <b>Balance Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💰 Value: {amount} PLN\n📊 Max Uses: 1\n\n<i>Share this beautiful promo image with your customers!</i>",
                            parse_mode=ParseMode.HTML
                        )
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to generate promo image: {e}")
                    await update.callback_query.edit_message_text(
                        f"✅ <b>Balance Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💰 Value: {amount} PLN\n📊 Max Uses: 1\n\n⚠️ <i>Image generation failed, but promo code was created successfully.</i>",
                        parse_mode=ParseMode.HTML
                    )
            else:
                await update.callback_query.edit_message_text(
                    f"❌ <b>Failed to create promo code</b>\n\nCode might already exist.",
                    parse_mode=ParseMode.HTML
                )
                
        except Exception as e:
            logger.error(f"Error creating preset balance promo: {e}")
            await update.callback_query.answer("❌ Error creating promo code")
    
    async def process_custom_discount_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Process custom discount promo percentage input"""
        try:
            percentage_value = float(update.message.text.strip())
            promo_code = context.user_data.get('promo_code')
            
            if not promo_code:
                await update.message.reply_text("❌ Error: Promo code not found. Please try again.")
                return
            
            success = self.db.create_promo_code(
                code=promo_code,
                value=percentage_value,
                code_type='discount',
                max_uses=1,
                created_by=user['user_id']
            )
            
            if success:
                # Generate promotional image
                try:
                    promo_image = await self.generate_promo_image_with_timeout(
                        promo_code=promo_code,
                        discount_type="Discount",
                        value=f"{percentage_value}%",
                        promo_type="discount",
                        bot_name=self.config.get('bot_name', 'TELESHOP')
                    )
                    
                    # Send the promotional image
                    await update.message.reply_photo(
                        photo=promo_image,
                        caption=f"✅ <b>Custom Discount Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💸 Discount: {percentage_value}%\n📊 Max Uses: 1\n\n<i>Share this beautiful promo image with your customers!</i>",
                        parse_mode=ParseMode.HTML
                    )
                    
                    message = f"🎉 <b>Promo Image Generated!</b>\n\nThe promotional image has been created and sent above. You can now share this attractive promo code image with your customers!"
                    
                except Exception as e:
                    logger.error(f"Failed to generate promo image: {e}")
                    message = f"✅ <b>Custom Discount Promo Created!</b>\n\n🎫 Code: <code>{promo_code}</code>\n💸 Discount: {percentage_value}%\n📊 Max Uses: 1\n\n⚠️ <i>Image generation failed, but promo code was created successfully.</i>"
            else:
                message = f"❌ <b>Failed to create promo code</b>\n\nCode might already exist."
            
        except ValueError:
            message = f"❌ <b>Invalid percentage</b>\n\nPlease enter a valid number."
        
        # Clear admin action
        context.user_data.pop('admin_action', None)
        context.user_data.pop('promo_code', None)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Promos", callback_data="admin_create_promo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        
        await self.send_menu_with_banner(
            update,
            message,
            reply_markup,
            use_banner=False
        )

    @rate_limit_check
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads from admin"""
        user = self.db.get_user(update.effective_user.id)
        if not user or not self.is_admin(user['user_id']):
            return
        
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'add_inventory_banner_photo':
            # Store banner photo file_id
            photo = update.message.photo[-1]  # Get highest resolution
            context.user_data['banner_image'] = photo.file_id
            
            await update.message.reply_text(
                "📸 Banner image received!\n\n"
                "Now please send a download image (optional - this can be a different angle or detail shot).\n\n"
                "You can type 'skip' to proceed without a download image."
            )
            context.user_data['admin_action'] = 'add_inventory_download_photo'
            
        elif admin_action == 'add_inventory_download_photo':
            # Store download photo file_id
            photo = update.message.photo[-1]  # Get highest resolution
            context.user_data['download_image'] = photo.file_id
            
            await update.message.reply_text(
                "📸 Download image received!\n\n"
                "Now please enter the inventory details in the following format:\n\n"
                "<code>Coordinates | Quantity | Unit | Description</code>\n\n"
                "Example:\n"
                "<code>52.2297,21.0122 | 10.0 | g | Premium quality product</code>\n\n"
                "<i>Note: Unit defaults to 'g' if not specified.</i>",
                parse_mode=ParseMode.HTML
            )
            context.user_data['admin_action'] = 'add_inventory_details'

    async def handle_image_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, inventory_id: str):
        """Handle image download request"""
        lang = user.get('language', 'en')
        
        # Get inventory details
        inventory = self.db.get_inventory_details(inventory_id)
        if not inventory:
            await update.callback_query.answer(get_text('product_not_found', lang), show_alert=True)
            return
        
        # Check if user has purchased this item
        has_purchased = self.db.check_user_purchase(user['user_id'], inventory_id)
        if not has_purchased:
            await update.callback_query.answer("❌ You must purchase this item first to download the image.", show_alert=True)
            return
        
        # Send the download image if available
        download_image = inventory.get('download_image')
        if download_image:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=download_image,
                    caption=f"📍 Location Image\n\n{inventory.get('description', '')}"
                )
                await update.callback_query.answer("✅ Image sent!", show_alert=False)
            except Exception as e:
                print(f"Error sending download image: {e}")
                await update.callback_query.answer("❌ Failed to send image.", show_alert=True)
        else:
            await update.callback_query.answer("❌ No download image available for this item.", show_alert=True)

    async def handle_receipt_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, order_id: str):
        """Handle receipt download request"""
        lang = user.get('language', 'en')
        
        # Get order details
        order = self.db.get_order_details(order_id)
        if not order:
            await update.callback_query.answer(get_text('order_not_found', lang), show_alert=True)
            return
        
        # Check if this order belongs to the user
        if order['user_id'] != user['user_id']:
            await update.callback_query.answer("❌ Access denied. This order doesn't belong to you.", show_alert=True)
            return
        
        try:
            # Import here to avoid circular imports
            from utils.helpers import generate_receipt_text
            
            # Generate receipt text
            receipt_text = generate_receipt_text(order, lang)
            
            # Create keyboard with Back to Main Menu button
            keyboard = [
                [InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show banner image (second photo) with receipt text when downloading receipt
            if order.get('banner_image'):
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=order['banner_image'],
                        caption=receipt_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    await update.callback_query.answer("✅ Receipt sent with banner image!", show_alert=False)
                except Exception as e:
                    logger.error(f"Failed to send banner image: {e}")
                    # Fallback to text-only receipt
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=receipt_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    await update.callback_query.answer("✅ Receipt sent!", show_alert=False)
            else:
                # Send receipt as a message with button if no banner image
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=receipt_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                await update.callback_query.answer("✅ Receipt sent!", show_alert=False)
            
        except Exception as e:
            logger.error(f"Error generating receipt: {e}")
            await update.callback_query.answer("❌ Failed to generate receipt.", show_alert=True)
    
    # Database Tools Functions
    async def admin_db_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Show database statistics"""
        try:
            stats = self.db.get_detailed_statistics()
            
            text = "📊 <b>Database Statistics</b>\n\n"
            
            # User Statistics
            text += "👥 <b>Users:</b>\n"
            text += f"   • Total Users: {stats['total_users']}\n"
            text += f"   • New Today: {stats['new_users_today']}\n\n"
            
            # Order Statistics
            text += "📦 <b>Orders:</b>\n"
            text += f"   • Total Orders: {stats['total_orders']}\n"
            text += f"   • Orders Today: {stats['orders_today']}\n"
            text += f"   • Average Order Value: {format_currency(stats['avg_order_value'])}\n\n"
            
            # Revenue Statistics
            text += "💰 <b>Revenue:</b>\n"
            text += f"   • Total Revenue: {format_currency(stats['total_revenue'])}\n"
            text += f"   • Revenue Today: {format_currency(stats['revenue_today'])}\n\n"
            
            # System Statistics
            text += "🏪 <b>System:</b>\n"
            text += f"   • Total Products: {stats['total_products']}\n"
            text += f"   • Total Cities: {stats['total_cities']}\n"
            text += f"   • Total Locations: {stats['total_locations']}\n"
            text += f"   • Active Promos: {stats['active_promos']}\n\n"
            
            # Most popular product
            if 'most_popular_product' in stats and stats['most_popular_product']:
                text += f"🏆 <b>Most Popular:</b> {stats['most_popular_product']}\n"
            
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            text = "📊 <b>Database Statistics</b>\n\n❌ Error loading statistics. Please try again later."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_db_stats")],
            [InlineKeyboardButton("🔙 Back to Database Tools", callback_data="admin_database_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_clean_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Clean old data from database"""
        # Show confirmation dialog first
        if not context.user_data.get('confirm_clean_data'):
            text = "🧹 <b>Clean Old Data</b>\n\n"
            text += "⚠️ <b>Warning:</b> This will permanently delete:\n"
            text += "• Completed orders older than 90 days\n"
            text += "• User sessions older than 30 days\n"
            text += "• Balance logs older than 90 days\n"
            text += "• Expired promo codes older than 90 days\n"
            text += "• Orphaned promo usage records\n\n"
            text += "❓ Are you sure you want to continue?"
            
            keyboard = [
                [InlineKeyboardButton("✅ Yes, Clean Data", callback_data="admin_confirm_clean_data")],
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_database_tools")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
            return
        
        # Perform the cleaning
        try:
            await update.callback_query.edit_message_text(
                "🧹 <b>Cleaning Data...</b>\n\n⏳ Please wait, this may take a moment..."
            )
            
            cleaned_counts = self.db.clean_old_data()
            
            if cleaned_counts:
                text = "🧹 <b>Data Cleaning Complete!</b>\n\n"
                text += "📊 <b>Cleaned Records:</b>\n"
                text += f"• Old Orders: {cleaned_counts.get('old_orders', 0)}\n"
                text += f"• Old Sessions: {cleaned_counts.get('old_sessions', 0)}\n"
                text += f"• Old Balance Logs: {cleaned_counts.get('old_balance_logs', 0)}\n"
                text += f"• Expired Promos: {cleaned_counts.get('expired_promos', 0)}\n"
                text += f"• Orphaned Records: {cleaned_counts.get('orphaned_promo_usage', 0)}\n\n"
                
                total_cleaned = sum(cleaned_counts.values())
                text += f"✅ <b>Total Cleaned:</b> {total_cleaned} records"
            else:
                text = "🧹 <b>Data Cleaning Complete!</b>\n\n❌ No old data found to clean."
                
        except Exception as e:
            logger.error(f"Error during data cleaning: {e}")
            text = "🧹 <b>Data Cleaning Failed!</b>\n\n❌ An error occurred during cleaning. Please check the logs."
        
        # Reset confirmation flag
        context.user_data['confirm_clean_data'] = False
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Database Tools", callback_data="admin_database_tools")],
            [InlineKeyboardButton("🏠 Back to Admin Menu", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ Close Menu", callback_data="close_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_backup_db(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Create database backup"""
        try:
            await update.callback_query.edit_message_text(
                "💾 <b>Creating Database Backup...</b>\n\n⏳ Please wait..."
            )
            
            backup_path = self.db.backup_database()
            
            # Get backup file size
            import os
            backup_size = os.path.getsize(backup_path)
            backup_size_mb = backup_size / (1024 * 1024)
            
            text = "💾 <b>Database Backup Complete!</b>\n\n"
            text += f"✅ <b>Backup Created:</b> {backup_path}\n"
            text += f"📊 <b>File Size:</b> {backup_size_mb:.2f} MB\n\n"
            text += "📁 The backup file has been saved in the bot directory.\n"
            text += "⚠️ <b>Important:</b> Download and store this backup in a secure location."
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            text = "💾 <b>Database Backup Failed!</b>\n\n❌ An error occurred while creating the backup. Please check the logs."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Create Another Backup", callback_data="admin_backup_db")],
            [InlineKeyboardButton("🔙 Back to Database Tools", callback_data="admin_database_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_reset_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Reset test data"""
        # Show confirmation dialog first
        if not context.user_data.get('confirm_reset_test'):
            text = "🔄 <b>Reset Test Data</b>\n\n"
            text += "⚠️ <b>DANGER:</b> This will permanently delete:\n"
            text += "• All orders and order history\n"
            text += "• All user sessions\n"
            text += "• All balance logs\n"
            text += "• All promo code usage records\n"
            text += "• All inactive promo codes\n"
            text += "• All active discounts\n"
            text += "• Reset all user balances and statistics\n\n"
            text += "🚨 <b>This action cannot be undone!</b>\n\n"
            text += "❓ Are you absolutely sure you want to continue?"
            
            keyboard = [
                [InlineKeyboardButton("⚠️ Yes, Reset All Data", callback_data="admin_confirm_reset_test")],
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_database_tools")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
            return
        
        # Perform the reset
        try:
            await update.callback_query.edit_message_text(
                "🔄 <b>Resetting Test Data...</b>\n\n⏳ Please wait, this may take a moment..."
            )
            
            reset_counts = self.db.reset_test_data()
            
            if reset_counts:
                text = "🔄 <b>Test Data Reset Complete!</b>\n\n"
                text += "📊 <b>Reset Records:</b>\n"
                text += f"• Orders: {reset_counts.get('orders', 0)}\n"
                text += f"• Sessions: {reset_counts.get('sessions', 0)}\n"
                text += f"• Balance Logs: {reset_counts.get('balance_logs', 0)}\n"
                text += f"• Promo Usage: {reset_counts.get('promo_usage', 0)}\n"
                text += f"• Inactive Promos: {reset_counts.get('inactive_promos', 0)}\n"
                text += f"• Discounts: {reset_counts.get('discounts', 0)}\n"
                text += f"• User Stats Reset: {reset_counts.get('user_stats_reset', 0)}\n\n"
                
                total_reset = sum(reset_counts.values())
                text += f"✅ <b>Total Reset:</b> {total_reset} records\n\n"
                text += "🎯 The system is now ready for fresh testing!"
            else:
                text = "🔄 <b>Test Data Reset Complete!</b>\n\n❌ No test data found to reset."
                
        except Exception as e:
            logger.error(f"Error during test data reset: {e}")
            text = "🔄 <b>Test Data Reset Failed!</b>\n\n❌ An error occurred during reset. Please check the logs."
        
        # Reset confirmation flag
        context.user_data['confirm_reset_test'] = False
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Database Tools", callback_data="admin_database_tools")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_delete_promo(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Delete promo code"""
        if context.user_data.get('awaiting_promo_code_to_delete'):
            # Process promo code input
            promo_code = update.message.text.strip().upper()
            
            # Get promo code details first
            promo_details = self.db.get_promo_code(promo_code)
            
            if not promo_details:
                await update.message.reply_text(
                    "❌ Promo code not found. Please try again or use /admin to return."
                )
                return
            
            if not promo_details.get('is_active', False):
                await update.message.reply_text(
                    "❌ This promo code is already inactive. Please try again or use /admin to return."
                )
                return
            
            # Show confirmation
            context.user_data['promo_to_delete'] = promo_code
            context.user_data['awaiting_promo_code_to_delete'] = False
            
            text = f"🗑️ <b>Delete Promo Code</b>\n\n"
            text += f"Code: <code>{promo_code}</code>\n"
            text += f"Value: {promo_details['value']}\n"
            text += f"Type: {promo_details['type']}\n"
            text += f"Uses: {promo_details['current_uses']}/{promo_details['max_uses']}\n\n"
            text += "⚠️ <b>Warning:</b> This will deactivate the promo code.\n"
            text += "Users will no longer be able to use it.\n\n"
            text += "❓ Are you sure you want to delete this promo code?"
            
            keyboard = [
                [InlineKeyboardButton("🗑️ Yes, Delete", callback_data="admin_confirm_delete_promo")],
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_promo_management")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        # Check if we have a promo code to delete from confirmation
        if context.user_data.get('promo_to_delete'):
            promo_code = context.user_data['promo_to_delete']
            
            try:
                success = self.db.delete_promo_code(promo_code)
                
                if success:
                    text = f"🗑️ <b>Promo Code Deleted!</b>\n\n"
                    text += f"✅ Promo code <code>{promo_code}</code> has been successfully deleted.\n"
                    text += "Users can no longer use this code."
                else:
                    text = f"🗑️ <b>Delete Failed!</b>\n\n"
                    text += f"❌ Could not delete promo code <code>{promo_code}</code>.\n"
                    text += "It may have already been deleted or doesn't exist."
                    
            except Exception as e:
                logger.error(f"Error deleting promo code {promo_code}: {e}")
                text = f"🗑️ <b>Delete Failed!</b>\n\n"
                text += "❌ An error occurred while deleting the promo code.\n"
                text += "Please check the logs and try again."
            
            # Clear the promo code from user data
            context.user_data.pop('promo_to_delete', None)
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Promo Management", callback_data="admin_promo_management")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
            return
        
        # Show promo code input prompt
        context.user_data['awaiting_promo_code_to_delete'] = True
        text = "🗑️ <b>Delete Promo Code</b>\n\n"
        text += "Enter the promo code you want to delete:"
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_promo_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_manage_cities(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Manage cities"""
        if context.user_data.get('awaiting_city_name'):
            # Process new city name input
            city_name = update.message.text.strip()
            
            if len(city_name) < 2:
                await update.message.reply_text(
                    "❌ City name must be at least 2 characters long. Please try again."
                )
                return
            
            success = self.db.add_city(city_name)
            
            if success:
                text = f"🏙️ <b>City Added!</b>\n\n"
                text += f"✅ City <b>{city_name}</b> has been successfully added."
            else:
                text = f"🏙️ <b>Add City Failed!</b>\n\n"
                text += f"❌ Could not add city <b>{city_name}</b>.\n"
                text += "It may already exist or there was a database error."
            
            context.user_data['awaiting_city_name'] = False
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        # Show cities management menu
        cities = self.db.get_all_cities_admin()
        
        text = "🏙️ <b>Manage Cities</b>\n\n"
        
        if cities:
            text += "📋 <b>Current Cities:</b>\n"
            for city in cities:
                status = "✅ Active" if city['is_active'] else "❌ Inactive"
                text += f"• <b>{city['name']}</b> - {status}\n"
        else:
            text += "❌ No cities found."
        
        keyboard = [
            [InlineKeyboardButton("➕ Add New City", callback_data="admin_add_city")]
        ]
        
        if cities:
            keyboard.extend([
                [InlineKeyboardButton("✏️ Edit City Status", callback_data="admin_edit_city_status")],
                [InlineKeyboardButton("🗑️ Delete City", callback_data="admin_delete_city")]
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_add_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Add new city"""
        context.user_data['awaiting_city_name'] = True
        text = "🏙️ <b>Add New City</b>\n\n"
        text += "Enter the name of the new city:"
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_manage_cities")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_edit_city_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Edit city status"""
        cities = self.db.get_all_cities_admin()
        
        if not cities:
            text = "🏙️ <b>Edit City Status</b>\n\n❌ No cities found."
            keyboard = [[InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
            return
        
        text = "🏙️ <b>Edit City Status</b>\n\n"
        text += "Select a city to toggle its status:\n\n"
        
        keyboard = []
        for city in cities:
            status_icon = "✅" if city['is_active'] else "❌"
            action_text = "Deactivate" if city['is_active'] else "Activate"
            keyboard.append([InlineKeyboardButton(
                f"{status_icon} {city['name']} - {action_text}",
                callback_data=f"admin_toggle_city_{city['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_delete_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Delete city"""
        cities = self.db.get_all_cities_admin()
        
        if not cities:
            text = "🏙️ <b>Delete City</b>\n\n❌ No cities found."
            keyboard = [[InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
            return
        
        text = "🏙️ <b>Delete City</b>\n\n"
        text += "⚠️ <b>Warning:</b> Deleting a city will also deactivate all its locations.\n\n"
        text += "Select a city to delete:\n\n"
        
        keyboard = []
        for city in cities:
            status_icon = "✅" if city['is_active'] else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status_icon} {city['name']}",
                callback_data=f"admin_confirm_delete_city_{city['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_toggle_city_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, city_id: int):
        """Admin: Toggle city status"""
        # Get current city info
        cities = self.db.get_all_cities_admin()
        city = next((c for c in cities if c['id'] == city_id), None)
        
        if not city:
            await update.callback_query.edit_message_text(
                "❌ City not found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")
                ]])
            )
            return
        
        new_status = not city['is_active']
        success = self.db.update_city_status(city_id, new_status)
        
        if success:
            status_text = "activated" if new_status else "deactivated"
            text = f"🏙️ <b>City Status Updated!</b>\n\n"
            text += f"✅ City <b>{city['name']}</b> has been {status_text}."
        else:
            text = f"🏙️ <b>Update Failed!</b>\n\n"
            text += f"❌ Could not update status for city <b>{city['name']}</b>."
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit More Cities", callback_data="admin_edit_city_status")],
            [InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_confirm_delete_city(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, city_id: int):
        """Admin: Confirm city deletion"""
        # Get current city info
        cities = self.db.get_all_cities_admin()
        city = next((c for c in cities if c['id'] == city_id), None)
        
        if not city:
            await update.callback_query.edit_message_text(
                "❌ City not found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")
                ]])
            )
            return
        
        # Check if city has locations
        locations = self.db.get_locations_by_city(city_id)
        
        success = self.db.delete_city(city_id)
        
        if success:
            text = f"🏙️ <b>City Deleted!</b>\n\n"
            text += f"✅ City <b>{city['name']}</b> has been deleted.\n"
            if locations:
                text += f"\n📍 {len(locations)} location(s) were also deactivated."
        else:
            text = f"🏙️ <b>Delete Failed!</b>\n\n"
            text += f"❌ Could not delete city <b>{city['name']}</b>."
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete More Cities", callback_data="admin_delete_city")],
            [InlineKeyboardButton("🔙 Back to Manage Cities", callback_data="admin_manage_cities")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_manage_locations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Manage locations"""
        if context.user_data.get('awaiting_location_name'):
            # Process new location name input
            location_name = update.message.text.strip()
            
            if len(location_name) < 2:
                await update.message.reply_text(
                    "❌ Location name must be at least 2 characters long. Please try again."
                )
                return
            
            context.user_data['location_name'] = location_name
            context.user_data['awaiting_location_name'] = False
            context.user_data['awaiting_location_description'] = True
            
            text = f"📍 <b>Add New Location</b>\n\n"
            text += f"Name: <b>{location_name}</b>\n\n"
            text += "Enter a description for this location:"
            
            keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_manage_locations")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        elif context.user_data.get('awaiting_location_description'):
            # Process location description input
            location_description = update.message.text.strip()
            location_name = context.user_data.get('location_name')
            city_id = context.user_data.get('selected_city_for_location')
            
            if not location_name or not city_id:
                await update.message.reply_text(
                    "❌ Missing location data. Please start over."
                )
                context.user_data.pop('awaiting_location_description', None)
                context.user_data.pop('location_name', None)
                context.user_data.pop('selected_city_for_location', None)
                return
            
            success = self.db.add_location(location_name, location_description, city_id)
            
            if success:
                text = f"📍 <b>Location Added!</b>\n\n"
                text += f"✅ Location <b>{location_name}</b> has been successfully added."
            else:
                text = f"📍 <b>Add Location Failed!</b>\n\n"
                text += f"❌ Could not add location <b>{location_name}</b>.\n"
                text += "There may have been a database error."
            
            # Clear user data
            context.user_data.pop('awaiting_location_description', None)
            context.user_data.pop('location_name', None)
            context.user_data.pop('selected_city_for_location', None)
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        # Show locations management menu
        locations = self.db.get_all_locations_admin()
        
        text = "📍 <b>Manage Locations</b>\n\n"
        
        if locations:
            text += "📋 <b>Current Locations:</b>\n"
            current_city = None
            for location in locations:
                if current_city != location['city_name']:
                    current_city = location['city_name']
                    text += f"\n🏙️ <b>{current_city}:</b>\n"
                
                status = "✅ Active" if location['is_active'] else "❌ Inactive"
                text += f"  • <b>{location['name']}</b> - {status}\n"
        else:
            text += "❌ No locations found."
        
        keyboard = [
            [InlineKeyboardButton("➕ Add New Location", callback_data="admin_add_location")]
        ]
        
        if locations:
            keyboard.extend([
                [InlineKeyboardButton("✏️ Edit Location Status", callback_data="admin_edit_location_status")],
                [InlineKeyboardButton("🗑️ Delete Location", callback_data="admin_delete_location")]
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)

    async def admin_add_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Add new location - show city selection"""
        cities = self.db.get_all_cities_admin()
        
        if not cities:
            text = "📍 <b>Add New Location</b>\n\n"
            text += "❌ No cities available. Please add cities first."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        text = "📍 <b>Add New Location</b>\n\n"
        text += "Select a city for the new location:\n\n"
        
        keyboard = []
        for city in cities:
            if city['is_active']:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏙️ {city['name']}", 
                        callback_data=f"admin_select_city_for_location_{city['id']}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_edit_location_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Edit location status"""
        locations = self.db.get_all_locations_admin()
        
        if not locations:
            text = "📍 <b>Edit Location Status</b>\n\n"
            text += "❌ No locations found."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        text = "📍 <b>Edit Location Status</b>\n\n"
        text += "Select a location to toggle its status:\n\n"
        
        keyboard = []
        current_city = None
        for location in locations:
            if current_city != location['city_name']:
                current_city = location['city_name']
                text += f"🏙️ <b>{current_city}:</b>\n"
            
            status_icon = "✅" if location['is_active'] else "❌"
            status_text = "Active" if location['is_active'] else "Inactive"
            text += f"  • {location['name']} - {status_text}\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon} {location['name']}", 
                    callback_data=f"admin_toggle_location_{location['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_delete_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Delete location"""
        locations = self.db.get_all_locations_admin()
        
        if not locations:
            text = "📍 <b>Delete Location</b>\n\n"
            text += "❌ No locations found."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        text = "📍 <b>Delete Location</b>\n\n"
        text += "⚠️ <b>Warning:</b> Deleting a location will permanently remove it from the system.\n\n"
        text += "Select a location to delete:\n\n"
        
        keyboard = []
        current_city = None
        for location in locations:
            if current_city != location['city_name']:
                current_city = location['city_name']
                text += f"🏙️ <b>{current_city}:</b>\n"
            
            status_icon = "✅" if location['is_active'] else "❌"
            text += f"  • {location['name']} - {status_icon}\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {location['name']}", 
                    callback_data=f"admin_confirm_delete_location_{location['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_toggle_location_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, location_id: int):
        """Admin: Toggle location status"""
        success = self.db.update_location_status(location_id)
        
        if success:
            text = "📍 <b>Location Status Updated!</b>\n\n"
            text += "✅ Location status has been successfully updated."
        else:
            text = "📍 <b>Update Failed!</b>\n\n"
            text += "❌ Could not update location status.\n"
            text += "There may have been a database error."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Edit Status", callback_data="admin_edit_location_status")],
            [InlineKeyboardButton("🏠 Back to Manage Locations", callback_data="admin_manage_locations")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_confirm_delete_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, location_id: int):
        """Admin: Confirm location deletion"""
        # Get location details
        locations = self.db.get_all_locations_admin()
        location = next((loc for loc in locations if loc['id'] == location_id), None)
        
        if not location:
            text = "📍 <b>Delete Location</b>\n\n"
            text += "❌ Location not found."
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        success = self.db.delete_location(location_id)
        
        if success:
            text = f"📍 <b>Location Deleted!</b>\n\n"
            text += f"✅ Location <b>{location['name']}</b> has been successfully deleted."
        else:
            text = f"📍 <b>Delete Failed!</b>\n\n"
            text += f"❌ Could not delete location <b>{location['name']}</b>.\n"
            text += "There may have been a database error."
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Manage Locations", callback_data="admin_manage_locations")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_maintenance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Maintenance mode management"""
        current_mode = self.config.get('maintenance_mode', False)
        
        text = "🔧 <b>Maintenance Mode</b>\n\n"
        
        if current_mode:
            text += "🔴 <b>Status:</b> ENABLED\n\n"
            text += "⚠️ The bot is currently in maintenance mode.\n"
            text += "Only administrators can use the bot.\n\n"
            text += "📋 <b>What maintenance mode does:</b>\n"
            text += "• Blocks all non-admin users\n"
            text += "• Shows maintenance message to users\n"
            text += "• Allows admins to work on the system\n"
            text += "• Prevents new orders and transactions\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🟢 Disable Maintenance Mode", callback_data="admin_toggle_maintenance")]
            ]
        else:
            text += "🟢 <b>Status:</b> DISABLED\n\n"
            text += "✅ The bot is operating normally.\n"
            text += "All users can access the bot functions.\n\n"
            text += "📋 <b>Enable maintenance mode to:</b>\n"
            text += "• Perform system updates\n"
            text += "• Fix critical issues\n"
            text += "• Prevent user interference during maintenance\n"
            text += "• Ensure data integrity during changes\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🔴 Enable Maintenance Mode", callback_data="admin_toggle_maintenance")]
            ]
        
        keyboard.append([InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_view_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: View bot logs"""
        import os
        import glob
        from datetime import datetime, timedelta
        
        text = "📝 <b>Bot Logs</b>\n\n"
        
        # Try to find log files
        log_files = []
        possible_log_paths = [
            "logs/*.log",
            "*.log",
            "bot.log",
            "teleshop.log",
            "app.log"
        ]
        
        for pattern in possible_log_paths:
            log_files.extend(glob.glob(pattern))
        
        if not log_files:
            text += "❌ No log files found.\n\n"
            text += "📋 <b>Expected log locations:</b>\n"
            text += "• logs/bot.log\n"
            text += "• bot.log\n"
            text += "• teleshop.log\n\n"
            text += "💡 <b>Note:</b> Log files are created automatically when the bot runs.\n"
            text += "If no logs are found, they may not be configured or the bot hasn't logged anything yet."
        else:
            text += f"📁 <b>Found {len(log_files)} log file(s):</b>\n\n"
            
            for log_file in log_files[:5]:  # Show max 5 files
                try:
                    stat = os.stat(log_file)
                    size_mb = stat.st_size / (1024 * 1024)
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    
                    text += f"📄 <b>{os.path.basename(log_file)}</b>\n"
                    text += f"   Size: {size_mb:.2f} MB\n"
                    text += f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                except Exception as e:
                    text += f"📄 <b>{os.path.basename(log_file)}</b> - Error reading file\n\n"
            
            # Try to show recent log entries
            try:
                with open(log_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    recent_lines = lines[-10:]  # Last 10 lines
                    
                    if recent_lines:
                        text += "📋 <b>Recent Log Entries:</b>\n"
                        text += "```\n"
                        for line in recent_lines:
                            # Truncate very long lines
                            if len(line) > 100:
                                line = line[:97] + "...\n"
                            text += line
                        text += "```\n\n"
                        
                        text += "💡 <b>Tip:</b> Check the full log files on the server for complete information."
            except Exception as e:
                text += f"❌ Could not read log content: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Logs", callback_data="admin_view_logs")],
            [InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def admin_toggle_maintenance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Toggle maintenance mode"""
        current_mode = self.config.get('maintenance_mode', False)
        new_mode = not current_mode
        
        # Update configuration
        self.config['maintenance_mode'] = new_mode
        self.save_bot_config()
        
        # Show confirmation
        if new_mode:
            text = "🔴 <b>Maintenance Mode ENABLED</b>\n\n"
            text += "⚠️ The bot is now in maintenance mode.\n"
            text += "Only administrators can use the bot.\n\n"
            text += "📋 <b>Active restrictions:</b>\n"
            text += "• Non-admin users are blocked\n"
            text += "• Maintenance message shown to users\n"
            text += "• New orders and transactions prevented\n"
            text += "• System ready for maintenance work\n\n"
            text += "💡 Remember to disable maintenance mode when done!"
        else:
            text = "🟢 <b>Maintenance Mode DISABLED</b>\n\n"
            text += "✅ The bot is now operating normally.\n"
            text += "All users can access bot functions again.\n\n"
            text += "📋 <b>Restored functionality:</b>\n"
            text += "• All users can use the bot\n"
            text += "• Orders and transactions enabled\n"
            text += "• Full system functionality restored\n"
            text += "• Normal operation resumed\n\n"
            text += "🎉 Maintenance completed successfully!"
        
        keyboard = [
            [InlineKeyboardButton("🔧 Back to Maintenance Settings", callback_data="admin_maintenance")],
            [InlineKeyboardButton("⚙️ Back to System Settings", callback_data="admin_system_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    # User Management Functions
    async def admin_view_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: View all users with pagination"""
        page = context.user_data.get('users_page', 0)
        limit = 10
        offset = page * limit
        
        users = self.db.get_all_users(limit=limit, offset=offset)
        total_users = self.db.get_user_statistics()['total_users']
        
        if not users:
            text = "👥 <b>All Users</b>\n\n❌ No users found."
        else:
            text = f"👥 <b>All Users</b> (Page {page + 1})\n\n"
            for i, u in enumerate(users, 1):
                status = "🚫 Banned" if u.get('is_banned') else "✅ Active"
                text += f"{offset + i}. <b>{u['username'] or 'Unknown'}</b>\n"
                text += f"   ID: <code>{u['user_id']}</code>\n"
                text += f"   Balance: {format_currency(u['balance'])}\n"
                text += f"   Orders: {u['total_orders']} | Status: {status}\n\n"
        
        keyboard = []
        
        # Pagination buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_users_page_{page-1}"))
        if len(users) == limit:  # More pages available
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_users_page_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Back to User Management", callback_data="admin_user_management")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_search_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Search for users"""
        if context.user_data.get('awaiting_user_search'):
            # Process search query
            query = update.message.text.strip()
            context.user_data['awaiting_user_search'] = False
            
            users = self.db.search_users(query, limit=20)
            
            if not users:
                text = f"🔍 <b>Search Results</b>\n\nNo users found for query: <code>{query}</code>"
            else:
                text = f"🔍 <b>Search Results</b> ({len(users)} found)\n\nQuery: <code>{query}</code>\n\n"
                for i, u in enumerate(users, 1):
                    status = "🚫 Banned" if u.get('is_banned') else "✅ Active"
                    text += f"{i}. <b>{u['username'] or 'Unknown'}</b>\n"
                    text += f"   ID: <code>{u['user_id']}</code>\n"
                    text += f"   Balance: {format_currency(u['balance'])}\n"
                    text += f"   Orders: {u['total_orders']} | Status: {status}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Back to User Management", callback_data="admin_user_management")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        
        # Show search prompt
        context.user_data['awaiting_user_search'] = True
        text = "🔍 <b>Search User</b>\n\nSend me a username or user ID to search for."
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_user_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_add_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Add balance to user"""
        if context.user_data.get('awaiting_balance_user_id'):
            # Process user ID input
            try:
                target_user_id = int(update.message.text.strip())
                target_user = self.db.get_user(target_user_id)
                
                if not target_user:
                    await update.message.reply_text("❌ User not found. Try again or use /admin to return.")
                    return
                
                context.user_data['balance_target_user'] = target_user
                context.user_data['awaiting_balance_user_id'] = False
                context.user_data['awaiting_balance_amount'] = True
                
                text = f"💰 <b>Add Balance</b>\n\nUser: <b>{target_user['username'] or 'Unknown'}</b>\n"
                text += f"ID: <code>{target_user['user_id']}</code>\n"
                text += f"Current Balance: {format_currency(target_user['balance'])}\n\n"
                text += "Enter the amount to add (can be negative to subtract):"
                
                keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_user_management")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                return
                
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID. Please enter a valid number.")
                return
        
        elif context.user_data.get('awaiting_balance_amount'):
            # Process amount input
            try:
                amount = float(update.message.text.strip())
                target_user = context.user_data['balance_target_user']
                
                # Add balance
                success = self.db.add_balance_to_user(target_user['user_id'], amount, user['user_id'])
                
                if success:
                    new_balance = target_user['balance'] + amount
                    text = f"✅ <b>Balance Updated</b>\n\n"
                    text += f"User: <b>{target_user['username'] or 'Unknown'}</b>\n"
                    text += f"Amount Added: {format_currency(amount)}\n"
                    text += f"New Balance: {format_currency(new_balance)}"
                else:
                    text = "❌ Failed to update balance. Please try again."
                
                context.user_data.pop('awaiting_balance_amount', None)
                context.user_data.pop('balance_target_user', None)
                
                keyboard = [[InlineKeyboardButton("🔙 Back to User Management", callback_data="admin_user_management")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                return
                
            except ValueError:
                await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")
                return
        
        # Show user ID prompt
        context.user_data['awaiting_balance_user_id'] = True
        text = "💰 <b>Add Balance to User</b>\n\nEnter the user ID:"
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_user_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Ban/Unban users"""
        if context.user_data.get('awaiting_ban_user_id'):
            # Process user ID input
            try:
                target_user_id = int(update.message.text.strip())
                target_user = self.db.get_user(target_user_id)
                
                if not target_user:
                    await update.message.reply_text("❌ User not found. Try again or use /admin to return.")
                    return
                
                context.user_data['ban_target_user'] = target_user
                context.user_data['awaiting_ban_user_id'] = False
                
                is_banned = target_user.get('is_banned', False)
                action = "Unban" if is_banned else "Ban"
                status = "🚫 Banned" if is_banned else "✅ Active"
                
                text = f"🚫 <b>{action} User</b>\n\n"
                text += f"User: <b>{target_user['username'] or 'Unknown'}</b>\n"
                text += f"ID: <code>{target_user['user_id']}</code>\n"
                text += f"Current Status: {status}\n\n"
                text += f"Are you sure you want to {action.lower()} this user?"
                
                keyboard = [
                    [InlineKeyboardButton(f"✅ Yes, {action}", callback_data=f"admin_confirm_ban_{target_user_id}_{not is_banned}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="admin_user_management")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                return
                
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID. Please enter a valid number.")
                return
        
        # Show user ID prompt
        context.user_data['awaiting_ban_user_id'] = True
        text = "🚫 <b>Ban/Unban User</b>\n\nEnter the user ID:"
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_user_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_user_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Show user statistics"""
        stats = self.db.get_user_statistics()
        
        text = "📊 <b>User Statistics</b>\n\n"
        text += f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        text += f"🟢 Active Users (30d): <b>{stats['active_users']}</b>\n"
        text += f"🆕 New Users (7d): <b>{stats['new_users']}</b>\n"
        text += f"🚫 Banned Users: <b>{stats['banned_users']}</b>\n\n"
        
        text += f"💰 Total Balance: <b>{format_currency(stats['total_balance'])}</b>\n"
        text += f"📊 Average Balance: <b>{format_currency(stats['average_balance'])}</b>\n\n"
        
        text += f"🛒 Total Orders: <b>{stats['total_orders']}</b>\n"
        text += f"💸 Total Spent: <b>{format_currency(stats['total_spent'])}</b>\n\n"
        
        # Top users by orders
        if stats['top_users_by_orders']:
            text += "🏆 <b>Top Users by Orders:</b>\n"
            for i, top_user in enumerate(stats['top_users_by_orders'][:5], 1):
                text += f"{i}. {top_user['username'] or 'Unknown'} - {top_user['total_orders']} orders\n"
            text += "\n"
        
        # Top users by spending
        if stats['top_users_by_spending']:
            text += "💎 <b>Top Users by Spending:</b>\n"
            for i, top_user in enumerate(stats['top_users_by_spending'][:5], 1):
                text += f"{i}. {top_user['username'] or 'Unknown'} - {format_currency(top_user['total_spent'])}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to User Management", callback_data="admin_user_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, text, reply_markup, use_banner=False)
    
    async def admin_confirm_ban_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, target_user_id: int, ban_status: bool):
        """Admin: Confirm ban/unban action"""
        target_user = self.db.get_user(target_user_id)
        
        if not target_user:
            await update.callback_query.answer("❌ User not found.", show_alert=True)
            return
        
        # Perform ban/unban action
        if ban_status:
            success = self.db.ban_user(target_user_id)
            action = "banned"
        else:
            success = self.db.unban_user(target_user_id)
            action = "unbanned"
        
        if success:
            text = f"✅ <b>User {action.title()}</b>\n\n"
            text += f"User: <b>{target_user['username'] or 'Unknown'}</b>\n"
            text += f"ID: <code>{target_user_id}</code>\n\n"
            text += f"The user has been successfully {action}."
            
            await update.callback_query.answer(f"✅ User {action}!", show_alert=True)
        else:
            text = f"❌ <b>Failed to {action.split('n')[0]} User</b>\n\n"
            text += f"An error occurred while trying to {action.split('n')[0]} the user. Please try again."
            
            await update.callback_query.answer(f"❌ Failed to {action.split('n')[0]} user.", show_alert=True)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to User Management", callback_data="admin_user_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        
        # Clear context data
        context.user_data.pop('ban_target_user', None)
    
    async def admin_test_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Test auto-cleanup functionality"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Delete the last 100 messages in the chat
        try:
            for i in range(100):
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=update.callback_query.message.message_id - i
                    )
                except Exception:
                    # Message might not exist or can't be deleted, continue
                    continue
        except Exception as e:
            pass  # Continue even if some deletions fail
        
        # Send cleanup confirmation message
        keyboard = [
            [InlineKeyboardButton("🔙 Back to System Settings", callback_data="admin_system_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="🧹 <b>Test Cleanup Executed</b>\n\n"
                 "✅ Chat has been cleaned - 100 messages deleted.\n"
                 "Auto-cleanup functionality tested successfully.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

async def session_cleanup_task(bot_instance):
    """Background task to clean up expired sessions periodically"""
    import asyncio
    from datetime import datetime
    
    cleanup_interval = int(os.getenv('SESSION_CLEANUP_INTERVAL', '300'))  # 5 minutes default
    
    while True:
        try:
            # Clean up expired sessions
            cleaned_count = bot_instance.session_manager.cleanup_expired_sessions()
            if cleaned_count > 0:
                logger.info(f"Session cleanup: Removed {cleaned_count} expired sessions")
            
            # Wait for next cleanup cycle
            await asyncio.sleep(cleanup_interval)
            
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying

def main():
    """Start the bot"""
    import asyncio
    
    # Create bot instance
    bot = TeleShopBot()
    
    # Create application with secure token loading
    bot_token = get_config('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables or secure config!")
        print("Please check your .env file or secure configuration.")
        return
    
    application = Application.builder().token(bot_token).build()
    
    # Store the application in the bot instance for auto-cleanup access
    bot.application = application
    
    # Add handlers using modular approach
    application.add_handler(CommandHandler("start", bot.user_handler.start))
    application.add_handler(CommandHandler("admin", bot.admin_handler.admin_panel))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_input))
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
    
    # Start session cleanup task
    async def start_cleanup_task(app):
        asyncio.create_task(session_cleanup_task(bot))
    
    # Add post_init hook to start cleanup task
    application.post_init = start_cleanup_task
    
    # Start the bot
    print("🤖 TeleShop Bot is starting...")
    print(f"📋 Session cleanup interval: {os.getenv('SESSION_CLEANUP_INTERVAL', '300')} seconds")
    application.run_polling()

if __name__ == '__main__':
    main()
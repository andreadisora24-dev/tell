"""Shop handler module for TeleShop Bot.

Handles shopping-related functionality including:
- Product browsing and selection
- Inventory management
- Purchase processing
- Wallet and balance management
- Order history
"""

import logging
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .base_handler import BaseHandler
from translations import get_text
from utils import format_currency, calculate_discount
from rate_limiter import rate_limit_check

logger = logging.getLogger(__name__)

class ShopHandler(BaseHandler):
    """Handler for shopping and inventory functionality."""
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, data: str):
        """Handle shop-related callbacks"""
        lang = user.get('language', 'en')
        
        # Main menu callbacks
        if data == "menu_buy":
            await self.show_cities(update, context, user)
        elif data in ["menu_wallet", "wallet"]:
            await self.show_wallet(update, context, user)
        elif data == "menu_history":
            await self.show_order_history(update, context, user)
        elif data == "menu_help":
            await self.show_help(update, context, user)
        elif data == "menu_language":
            await self.show_language_menu(update, context, user)
        
        # Shopping flow callbacks
        elif data.startswith("city_"):
            city_id = data.replace("city_", "")
            await self.show_categories(update, context, user, city_id)
        elif data.startswith("category_"):
            category_id = data.replace("category_", "")
            city_id = context.user_data.get('selected_city')
            await self.show_products_in_category(update, context, user, category_id)
        elif data.startswith("product_"):
            product_id = data.replace("product_", "")
            city_id = context.user_data.get('selected_city')
            await self.show_product_strains(update, context, user, product_id, city_id)
        elif data.startswith("strain_"):
            strain_id = data.replace("strain_", "")
            await self.show_quantity_options(update, context, user, strain_id)
        elif data.startswith("quantity_"):
            quantity = float(data.replace("quantity_", ""))
            strain_id = context.user_data.get('selected_strain')
            await self.show_locations(update, context, user, strain_id, quantity)
        elif data.startswith("location_"):
            inventory_id = data.replace("location_", "")
            await self.handle_purchase(update, context, user, inventory_id)
        
        # Wallet callbacks
        elif data == "wallet_promo":
            await self.handle_promo_code_entry(update, context, user)
        elif data == "wallet_btc":
            await self.bot_instance.crypto_handler.show_crypto_payment_options(update, context, user)
        elif data == "wallet_blik":
            await update.callback_query.answer(get_text('blik_unavailable', lang), show_alert=True)
        
        # Crypto payment callbacks
        elif data.startswith("verify_btc_"):
            payment_id = data.replace("verify_btc_", "")
            await self.bot_instance.crypto_handler.verify_payment_callback(update, context, user, payment_id)
        elif data.startswith("crypto_info_"):
            payment_id = data.replace("crypto_info_", "")
            await self.bot_instance.crypto_handler.show_payment_info(update, context, user, payment_id)
        elif data == "crypto_back":
            await self.bot_instance.crypto_handler.show_crypto_payment_options(update, context, user)
        elif data == "crypto_bitcoin":
            # Start a new crypto payment flow by asking for custom amount
            await self.bot_instance.crypto_handler.show_crypto_payment_options(update, context, user)
        elif data == "crypto_custom_amount":
            # Re-prompt user to enter a custom amount
            await self.bot_instance.crypto_handler.show_crypto_payment_options(update, context, user)
        elif data == "back_wallet":
            await self.show_wallet(update, context, user)
        elif data.startswith("crypto_pay_"):
            amount = float(data.replace("crypto_pay_", ""))
            await self.bot_instance.crypto_handler.process_bitcoin_payment(update, context, user, amount)
        elif data.startswith("crypto_confirm_"):
            payment_id = data.replace("crypto_confirm_", "")
            await self.bot_instance.crypto_handler.confirm_payment(update, context, payment_id)
        elif data.startswith("crypto_check_"):
            payment_id = data.replace("crypto_check_", "")
            await self.bot_instance.crypto_handler.check_payment_status(update, context, payment_id)
        elif data.startswith("crypto_cancel_"):
            payment_id = data.replace("crypto_cancel_", "")
            await self.bot_instance.crypto_handler.cancel_payment(update, context, payment_id)
        
        # Language callbacks
        elif data.startswith("lang_"):
            new_lang = data.replace("lang_", "")
            await self.bot_instance.change_language(update, context, user, new_lang)
        
        # Help callbacks
        elif data == "help_admin":
            await self.contact_admin(update, context, user)
        elif data == "help_howto":
            await self.show_how_to_use(update, context, user)
        
        # Navigation callbacks
        elif data.startswith("back_") or data == "close_menu":
            await self.handle_navigation(update, context, user, data)
        
        # Promo code callbacks
        elif data.startswith("use_promo_"):
            await self.process_purchase_promo_code(update, context, user, data)
        
        else:
            logger.warning(f"Unhandled shop callback: {data}")
    
    async def handle_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, data: str):
        """Handle navigation callbacks like back_ and close_menu"""
        lang = user.get('language', 'en')
        
        if data == "back_main":
            # Go back to main menu
            from handlers.user_handler import UserHandler
            user_handler = UserHandler(self.db, self.captcha, self.session_manager, self.auto_cleanup, self.config)
            await user_handler.show_main_menu(update, context, user)
        elif data == "back_cities":
            # Go back to cities menu
            await self.show_cities(update, context, user)
        elif data == "back_categories":
            # Go back to categories menu (need city_id from context)
            city_id = context.user_data.get('selected_city_id')
            await self.show_categories(update, context, user, city_id)
        elif data == "back_products":
            # Go back to products in category
            category_id = context.user_data.get('selected_category_id')
            if category_id:
                await self.show_products_in_category(update, context, user, category_id)
            else:
                await self.show_cities(update, context, user)
        elif data == "back_strains":
            # Go back to product strains
            product_id = context.user_data.get('selected_product_id')
            city_id = context.user_data.get('selected_city_id')
            if product_id and city_id:
                await self.show_product_strains(update, context, user, product_id, city_id)
            else:
                await self.show_cities(update, context, user)
        elif data == "back_quantities":
            # Go back to quantity options
            strain_id = context.user_data.get('selected_strain_id')
            if strain_id:
                await self.show_quantity_options(update, context, user, strain_id)
            else:
                await self.show_cities(update, context, user)
        elif data == "close_menu":
            # Close/delete the current menu
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                await update.callback_query.answer("Menu closed", show_alert=False)
        else:
            logger.warning(f"Unhandled navigation callback: {data}")
            # Default fallback to main menu
            from handlers.user_handler import UserHandler
            user_handler = UserHandler(self.db, self.captcha, self.session_manager, self.auto_cleanup, self.config)
            await user_handler.show_main_menu(update, context, user)
    
    async def show_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show wallet with balance and payment options"""
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
        
        await self.send_menu_with_banner(update, context, wallet_text, reply_markup, use_banner=False)
    
    async def show_order_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show user's order history"""
        orders = self.db.get_user_orders(user['user_id'])
        lang = user.get('language', 'en')
        
        if not orders:
            keyboard = [[InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            order_history_text = f"{get_text('order_history', lang)}\n\n{get_text('no_orders', lang)}"
            await self.send_menu_with_banner(update, context, order_history_text, reply_markup, use_banner=False)
            return
        
        keyboard = []
        for order in orders:
            order_date = order['created_at'][:10]  # Simple date format
            order_text = f"Order #{str(order['id'])[:8]} - {order_date}"
            keyboard.append([InlineKeyboardButton(order_text, callback_data=f"order_{order['id']}")])
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        order_history_with_details = f"{get_text('order_history', lang)}\n\n{get_text('select_order_details', lang)}"
        await self.send_menu_with_banner(update, context, order_history_with_details, reply_markup, use_banner=False)
    
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show help options"""
        lang = user.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_contact_admin', lang), callback_data="help_admin")],
            [InlineKeyboardButton(get_text('btn_how_to_use', lang), callback_data="help_howto")],
            [InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, context, get_text('help_title', lang), reply_markup, use_banner=False)
    
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
        
        await self.send_menu_with_banner(update, context, "🌐 <b>Language / Język / Язyk</b>\n\nSelect your language:", reply_markup, use_banner=False)
    
    async def show_cities(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show available cities"""
        cities = self.db.get_cities()
        lang = user.get('language', 'en')
        
        keyboard = []
        for city in cities:
            keyboard.append([InlineKeyboardButton(f"🏙️ {city['name']}", callback_data=f"city_{city['id']}")])
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            context,
            get_text('select_city', lang),
            reply_markup,
            use_banner=False
        )
    
    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, city_id: str = None):
        """Show available categories in selected city"""
        categories = self.db.get_all_categories()
        lang = user.get('language', 'en')
        
        # Store selected city in user data
        if city_id:
            context.user_data['selected_city'] = city_id
        
        if not categories:
            text = "📦 <b>Shop</b>\n\n❌ No categories available at the moment."
            keyboard = [[InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]]
        else:
            text = "📦 <b>Shop - Categories</b>\n\nSelect a category:"
            keyboard = []
            
            for category in categories:
                # Check if category has discount
                discount = self.db.get_category_discount(category['id'])
                category_text = f"{category.get('emoji', '📦')} {category['name']}"
                
                if discount:
                    category_text += f" - {discount['percentage']:.0f}%"
                
                keyboard.append([InlineKeyboardButton(
                    category_text,
                    callback_data=f"category_{category['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_cities")])
            keyboard.append([InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_menu_with_banner(update, context, text, reply_markup, use_banner=False)
    
    async def show_products_in_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, category_id: int):
        """Show products in a specific category"""
        lang = user.get('language', 'en')
        city_id = context.user_data.get('selected_city')
        products = self.db.get_products_by_category_and_city(category_id, city_id) if city_id else []
        category = self.db.get_category(category_id)
        
        if not products:
            text = f"📦 <b>{category['name'] if category else 'Category'}</b>\n\n❌ No products available in this category."
            keyboard = [[InlineKeyboardButton("🔙 Back to Categories", callback_data="menu_buy")]]
        else:
            text = f"📦 <b>{category['name'] if category else 'Category'}</b>\n\nSelect a product:"
            keyboard = []
            
            for product in products:
                # Check if product has inventory
                inventory_count = self.db.get_product_inventory_count(product['id'])
                status = "✅" if inventory_count > 0 else "❌"
                
                keyboard.append([InlineKeyboardButton(
                    f"{status} {product['name']} ({inventory_count} available)",
                    callback_data=f"product_{product['id']}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="menu_buy")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.send_menu_with_banner(update, context, text, reply_markup, use_banner=False)
    
    async def show_product_strains(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, product_id: str, city_id: str):
        """Show available strains for a product"""
        strains = self.db.get_product_strains(product_id, city_id)
        lang = user.get('language', 'en')
        
        # Store selected product in user data
        context.user_data['selected_product'] = product_id
        
        if not strains:
            await update.callback_query.answer(get_text('no_strains_available', lang), show_alert=True)
            return
        
        # If only one strain, skip strain selection and go directly to quantity
        if len(strains) == 1:
            strain = strains[0]
            await self.show_quantity_options(update, context, user, strain['id'])
            return
        
        keyboard = []
        for strain in strains:
            keyboard.append([InlineKeyboardButton(
                f"🌿 {strain['name']} - {format_currency(strain['price'])}",
                callback_data=f"strain_{strain['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_products")])
        keyboard.append([InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            context,
            get_text('select_strain', lang),
            reply_markup,
            use_banner=False
        )
    
    async def show_quantity_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, strain_id: str):
        """Show available quantity options for selected strain"""
        quantity_options = self.db.get_quantity_options_for_strain(strain_id)
        lang = user.get('language', 'en')
        
        # Store selected strain in user data
        context.user_data['selected_strain'] = strain_id
        
        # Determine correct back navigation based on whether strain selection was skipped
        product_id = context.user_data.get('selected_product')
        city_id = context.user_data.get('selected_city')
        back_callback = "back_strains"
        
        if product_id and city_id:
            # Check if this product has only one strain (strain selection was skipped)
            strains = self.db.get_product_strains(product_id, city_id)
            if len(strains) == 1:
                back_callback = "back_products"
        
        if not quantity_options:
            keyboard = [
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data=back_callback)],
                [InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                "❌ No quantities available for this strain.",
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = []
        for option in quantity_options:
            # Show discounted price if available
            if option.get('discount_info'):
                original_price_text = format_currency(option['total_price'])
                discounted_price_text = format_currency(option['discounted_price'])
                discount_percentage = option['discount_info']['percentage']
                price_text = f"~~{original_price_text}~~ {discounted_price_text} (-{discount_percentage}%)"
            else:
                price_text = format_currency(option['total_price'])
            
            location_text = f" ({option['location_count']} locations)" if option['location_count'] > 1 else ""
            keyboard.append([InlineKeyboardButton(
                f"⚖️ {option['quantity']}{option['unit']} - {price_text}{location_text}", 
                callback_data=f"quantity_{option['quantity']}"
            )])
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back', lang), callback_data=back_callback)])
        keyboard.append([InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            context,
            "🛒 Select quantity:",
            reply_markup,
            use_banner=False
        )
    
    async def show_locations(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, strain_id: str, quantity: float = None):
        """Show available locations for selected strain and quantity"""
        if quantity is not None:
            locations = self.db.get_locations_for_strain_quantity(strain_id, quantity)
        else:
            locations = self.db.get_locations_for_strain(strain_id)
        
        lang = user.get('language', 'en')
        
        # Store selected strain in user data
        context.user_data['selected_strain'] = strain_id
        if quantity is not None:
            context.user_data['selected_quantity'] = quantity
        
        if not locations:
            # Determine correct back navigation for error case
            if quantity:
                error_back_callback = "back_quantities"
            else:
                # Check if strain selection was skipped (only one strain available)
                product_id = context.user_data.get('selected_product')
                city_id = context.user_data.get('selected_city')
                error_back_callback = "back_strains"
                
                if product_id and city_id:
                    strains = self.db.get_product_strains(product_id, city_id)
                    if len(strains) == 1:
                        error_back_callback = "back_products"
            
            keyboard = [
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data=error_back_callback)],
                [InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                "❌ No locations available for this selection.",
                reply_markup,
                use_banner=False
            )
            return
        
        keyboard = []
        for location in locations:
            # Handle both individual inventory_id and pooled inventory_ids
            if 'inventory_ids' in location and location['inventory_ids']:
                callback_data = f"location_{location['inventory_ids'].split(',')[0]}"
            else:
                callback_data = f"location_{location['id']}"
            
            keyboard.append([InlineKeyboardButton(
                f"📍 {location['name']}", 
                callback_data=callback_data
            )])
        
        # Determine correct back navigation
        if quantity:
            back_callback = "back_quantities"
        else:
            # Check if strain selection was skipped (only one strain available)
            product_id = context.user_data.get('selected_product')
            city_id = context.user_data.get('selected_city')
            back_callback = "back_strains"
            
            if product_id and city_id:
                strains = self.db.get_product_strains(product_id, city_id)
                if len(strains) == 1:
                    back_callback = "back_products"
        
        keyboard.append([InlineKeyboardButton(get_text('btn_back', lang), callback_data=back_callback)])
        keyboard.append([InlineKeyboardButton(get_text('btn_main_menu', lang), callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            context,
            get_text('select_location', lang),
            reply_markup,
            use_banner=False
        )
    
    async def handle_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, inventory_id: str):
        """Handle purchase confirmation"""
        lang = user.get('language', 'en')
        
        try:
            # Get inventory details
            inventory = self.db.get_inventory_details(int(inventory_id))
            if not inventory:
                await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
                return
        except Exception as e:
            logger.error(f"Error getting inventory details: {e}")
            await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
            return
        
        # Get selected quantity from context, fallback to inventory quantity
        selected_quantity = context.user_data.get('selected_quantity', inventory['quantity'])
        
        # Calculate price
        price = inventory['price'] * (selected_quantity / inventory['quantity'])
        user_balance = user.get('balance', 0)
        
        if user_balance < price:
            # Show insufficient balance
            insufficient_balance_text = f"""❌ <b>Insufficient Balance</b>

💰 Required: {format_currency(price)}
💳 Your balance: {format_currency(user_balance)}
💸 Need: {format_currency(price - user_balance)}

📍 Location: {inventory['location_name']}
🧬 Product: {inventory['product_name']} - {inventory['strain_name']}
⚖️ Quantity: {selected_quantity}{inventory.get('unit', 'g')}

Please add funds to your wallet to complete this purchase."""
            
            keyboard = [
                [InlineKeyboardButton("💳 Go to Wallet", callback_data="wallet")],
                [InlineKeyboardButton(get_text('btn_back', lang), callback_data="back_quantities")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                insufficient_balance_text,
                reply_markup,
                use_banner=False
            )
            return
        
        # Show purchase confirmation
        confirmation_text = f"""🛒 <b>Purchase Confirmation</b>

📍 Location: {inventory['location_name']}
🧬 Product: {inventory['product_name']} - {inventory['strain_name']}
⚖️ Quantity: {selected_quantity}{inventory.get('unit', 'g')}
💰 Price: {format_currency(price)}

💳 Your balance: {format_currency(user_balance)}
💳 After purchase: {format_currency(user_balance - price)}

⚠️ Are you sure you want to proceed with this purchase?"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_purchase_{inventory_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_quantities")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            context,
            confirmation_text,
            reply_markup,
            use_banner=False
        )
    
    async def handle_promo_code_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Handle promo code entry request"""
        lang = user.get('language', 'en')
        
        promo_text = f"""{get_text('promo_code_title', lang)}

{get_text('promo_code_instructions', lang)}

Please type your promo code:"""
        
        keyboard = [[InlineKeyboardButton(get_text('btn_back', lang), callback_data="wallet")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, context, promo_text, reply_markup, use_banner=False)
        
        # Set state for text message handling
        context.user_data['awaiting_promo_code'] = True
    
    async def process_purchase_promo_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, data: str):
        """Process promo code during purchase"""
        lang = user.get('language', 'en')
        
        # Extract inventory_id from callback data
        inventory_id = data.replace("use_promo_", "")
        
        # Check if user has a saved promo code
        saved_code = context.user_data.get('saved_discount_code')
        if saved_code:
            # Apply the saved promo code
            context.user_data['purchase_promo_code'] = saved_code
            await update.callback_query.answer("🎫 Promo code applied!", show_alert=False)
            # Redirect back to purchase confirmation with discount applied
            await self.handle_purchase(update, context, user, inventory_id)
        else:
            await update.callback_query.answer("❌ No promo code available", show_alert=True)
    
    async def contact_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show admin contact information"""
        lang = user.get('language', 'en')
        
        admin_text = f"""{get_text('contact_admin_title', lang)}

{get_text('contact_admin_info', lang)}"""
        
        keyboard = [[InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, context, admin_text, reply_markup, use_banner=False)
    
    async def show_how_to_use(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show how to use the bot"""
        lang = user.get('language', 'en')
        
        howto_text = f"""{get_text('how_to_use_title', lang)}

{get_text('how_to_use_instructions', lang)}"""
        
        keyboard = [[InlineKeyboardButton(get_text('btn_back', lang), callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(update, context, howto_text, reply_markup, use_banner=False)
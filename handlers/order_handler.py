"""Order handler module for TeleShop Bot.

Handles order-related functionality including:
- Order processing and confirmation
- Order status tracking
- Order history management
- Payment processing
- Order completion and delivery
"""

import logging
import asyncio
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .base_handler import BaseHandler
from translations import get_text
from utils import format_currency, generate_order_id
from rate_limiter import rate_limit_check

logger = logging.getLogger(__name__)

class OrderHandler(BaseHandler):
    """Handler for order processing and management."""
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, data: str):
        """Handle order-related callbacks"""
        lang = user.get('language', 'en')
        
        # Order history callbacks
        if data.startswith("order_"):
            order_id = data.replace("order_", "")
            await self.show_order_details(update, context, user, order_id)
        
        # Purchase confirmation callbacks
        elif data.startswith("confirm_purchase_"):
            inventory_id = data.replace("confirm_purchase_", "")
            await self.confirm_purchase(update, context, user, inventory_id)
        
        # Order cancellation callbacks
        elif data.startswith("cancel_order_"):
            order_id = data.replace("cancel_order_", "")
            await self.cancel_order(update, context, user, order_id)
        
        # Download callbacks
        elif data.startswith("download_image_"):
            order_id = data.replace("download_image_", "")
            await self.download_order_image(update, context, user, order_id)
        elif data.startswith("download_receipt_"):
            order_id = data.replace("download_receipt_", "")
            await self.download_order_receipt(update, context, user, order_id)
        
        else:
            logger.warning(f"Unhandled order callback: {data}")
    
    async def confirm_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, inventory_id: str):
        """Confirm and process the purchase"""
        lang = user.get('language', 'en')
        user_id = user['user_id']
        
        try:
            # Get inventory details
            inventory = self.db.get_inventory_details(int(inventory_id))
            if not inventory:
                await update.callback_query.answer(get_text('location_not_found', lang), show_alert=True)
                return
            
            # Get selected quantity
            selected_quantity = context.user_data.get('selected_quantity', inventory['quantity'])
            
            # Calculate final price with any applicable discounts
            strain_data = self.db.get_strain_with_price(inventory['strain_id'])
            if strain_data:
                original_price = strain_data['base_price'] * strain_data['price_modifier'] * selected_quantity
            else:
                original_price = inventory['price'] * (selected_quantity / inventory['quantity'])
            
            final_price = original_price
            discount_applied = None
            
            # Check for promo code discount
            promo_code_data = context.user_data.get('purchase_promo_code')
            if promo_code_data:
                from utils import calculate_discount
                discounted_price, discount_amount = calculate_discount(original_price, promo_code_data['percentage'])
                final_price = discounted_price
                discount_applied = {
                    'type': 'promo_code',
                    'code': promo_code_data['code'],
                    'percentage': promo_code_data['percentage'],
                    'amount': discount_amount
                }
            
            # Check user balance
            if user['balance'] < final_price:
                await update.callback_query.answer("❌ Insufficient balance", show_alert=True)
                return
            
            # Process the purchase
            order_id = generate_order_id()
            
            # Create order in database
            order_data = {
                'id': order_id,
                'user_id': user_id,
                'inventory_id': int(inventory_id),
                'quantity': selected_quantity,
                'original_price': original_price,
                'final_price': final_price,
                'discount_info': discount_applied,
                'status': 'confirmed'
            }
            
            success = self.db.create_order(order_data)
            if not success:
                await update.callback_query.answer("❌ Error processing order", show_alert=True)
                return
            
            # Update user balance
            new_balance = user['balance'] - final_price
            self.db.set_user_balance(user_id, new_balance)
            
            # Update inventory quantity
            new_inventory_quantity = inventory['quantity'] - selected_quantity
            if new_inventory_quantity <= 0:
                # Remove inventory if quantity reaches zero
                self.db.remove_inventory(int(inventory_id))
            else:
                # Update inventory quantity
                self.db.update_inventory_quantity(int(inventory_id), new_inventory_quantity)
            
            # Clear user context data
            context.user_data.pop('selected_quantity', None)
            context.user_data.pop('purchase_promo_code', None)
            
            # Show order confirmation
            await self.show_order_confirmation(update, context, user, order_data, inventory)
            
        except Exception as e:
            logger.error(f"Error confirming purchase: {e}")
            await update.callback_query.answer("❌ Error processing purchase", show_alert=True)
    
    async def show_order_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    user: Dict, order_data: Dict, inventory: Dict):
        """Show order confirmation with details"""
        lang = user.get('language', 'en')
        
        confirmation_text = f"""✅ <b>Order Confirmed!</b>

🆔 Order ID: #{order_data['id']}
📍 Location: {inventory['location_name']}
🧬 Product: {inventory['product_name']} - {inventory['strain_name']}
⚖️ Quantity: {order_data['quantity']}{inventory['unit']}
"""
        
        if order_data.get('discount_info'):
            discount = order_data['discount_info']
            confirmation_text += f"\n💰 Original Price: {format_currency(order_data['original_price'])}"
            if discount['type'] == 'promo_code':
                confirmation_text += f"\n🎫 Promo Code ({discount['code']}): -{discount['percentage']}%"
            confirmation_text += f"\n💸 You Saved: {format_currency(discount['amount'])}"
            confirmation_text += f"\n✅ Final Price: {format_currency(order_data['final_price'])}"
        else:
            confirmation_text += f"\n💰 Total Paid: {format_currency(order_data['final_price'])}"
        
        # Add location coordinates if available
        if inventory.get('coordinates'):
            confirmation_text += f"\n\n📍 <b>Pickup Location:</b>\n{inventory['coordinates']}"
        
        if inventory.get('description'):
            confirmation_text += f"\n\n📝 <b>Description:</b>\n{inventory['description']}"
        
        confirmation_text += "\n\n🎉 Thank you for your purchase!"
        confirmation_text += "\n💡 You can view this order in your order history."
        
        keyboard = [
            [InlineKeyboardButton("📋 View Order History", callback_data="menu_history")],
            [InlineKeyboardButton("🏪 Continue Shopping", callback_data="menu_buy")],
            [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_menu_with_banner(
            update,
            context,
            confirmation_text,
            reply_markup,
            use_banner=False
        )
    
    async def show_order_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, order_id: str):
        """Show detailed information about a specific order"""
        lang = user.get('language', 'en')
        
        try:
            order = self.db.get_order_details(int(order_id))
            if not order or order['user_id'] != user['user_id']:
                await update.callback_query.answer("❌ Order not found", show_alert=True)
                return
            
            # Format order details
            order_text = f"""📋 <b>Order Details</b>

🆔 Order ID: #{order['id']}
📅 Date: {order['created_at'][:19].replace('T', ' ')}
📍 Location: {order.get('location_name', 'N/A')}
🧬 Product: {order.get('product_name', 'N/A')} - {order.get('strain_name', 'N/A')}
⚖️ Quantity: {order['quantity']}{order.get('unit', 'g')}
💰 Total Paid: {format_currency(order['final_price'])}
📊 Status: {order['status'].title()}
"""
            
            # Add discount information if applicable
            if order.get('discount_info'):
                discount = order['discount_info']
                order_text += f"\n💸 Original Price: {format_currency(order['original_price'])}"
                if discount.get('code'):
                    order_text += f"\n🎫 Promo Code: {discount['code']} (-{discount['percentage']}%)"
                order_text += f"\n💰 Discount: {format_currency(discount['amount'])}"
            
            # Add location coordinates if available
            if order.get('coordinates'):
                order_text += f"\n\n📍 <b>Pickup Coordinates:</b>\n{order['coordinates']}"
            
            if order.get('description'):
                order_text += f"\n\n📝 <b>Description:</b>\n{order['description']}"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Order History", callback_data="menu_history")],
                [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                order_text,
                reply_markup,
                use_banner=False
            )
            
        except Exception as e:
            logger.error(f"Error showing order details: {e}")
            await update.callback_query.answer("❌ Error loading order details", show_alert=True)
    
    async def cancel_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, order_id: str):
        """Cancel an order (if allowed)"""
        lang = user.get('language', 'en')
        
        try:
            order = self.db.get_order_details(int(order_id))
            if not order or order['user_id'] != user['user_id']:
                await update.callback_query.answer("❌ Order not found", show_alert=True)
                return
            
            # Check if order can be cancelled
            if order['status'] not in ['confirmed', 'pending']:
                await update.callback_query.answer("❌ Order cannot be cancelled", show_alert=True)
                return
            
            # Process cancellation
            success = self.db.update_order_status(int(order_id), 'cancelled')
            if success:
                # Refund user balance
                new_balance = user['balance'] + order['final_price']
                self.db.set_user_balance(user['user_id'], new_balance)
                
                # Restore inventory if applicable
                if order.get('inventory_id'):
                    self.db.restore_inventory_quantity(order['inventory_id'], order['quantity'])
                
                text = f"✅ <b>Order Cancelled</b>\n\nOrder #{order_id} has been cancelled.\n💰 {format_currency(order['final_price'])} has been refunded to your balance."
            else:
                text = "❌ <b>Cancellation Failed</b>\n\nThere was an error cancelling your order. Please contact support."
            
            keyboard = [
                [InlineKeyboardButton("📋 View Order History", callback_data="menu_history")],
                [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                text,
                reply_markup,
                use_banner=False
            )
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            await update.callback_query.answer("❌ Error cancelling order", show_alert=True)
    
    async def track_order_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, order_id: str):
        """Track order status and provide updates"""
        lang = user.get('language', 'en')
        
        try:
            order = self.db.get_order_details(int(order_id))
            if not order or order['user_id'] != user['user_id']:
                await update.callback_query.answer("❌ Order not found", show_alert=True)
                return
            
            # Create status tracking text
            status_text = f"""📦 <b>Order Tracking</b>

🆔 Order ID: #{order['id']}
📅 Order Date: {order['created_at'][:19].replace('T', ' ')}
📊 Current Status: <b>{order['status'].title()}</b>
"""
            
            # Add status-specific information
            if order['status'] == 'confirmed':
                status_text += "\n✅ Your order has been confirmed and is being prepared."
            elif order['status'] == 'processing':
                status_text += "\n⏳ Your order is currently being processed."
            elif order['status'] == 'ready':
                status_text += "\n🎉 Your order is ready for pickup!"
                if order.get('coordinates'):
                    status_text += f"\n📍 Pickup Location: {order['coordinates']}"
            elif order['status'] == 'completed':
                status_text += "\n✅ Your order has been completed. Thank you!"
            elif order['status'] == 'cancelled':
                status_text += "\n❌ This order has been cancelled."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Status", callback_data=f"track_order_{order_id}")],
                [InlineKeyboardButton("📋 Order Details", callback_data=f"order_{order_id}")],
                [InlineKeyboardButton("🔙 Back to History", callback_data="menu_history")]
            ]
            
            # Add cancel option if order can be cancelled
            if order['status'] in ['confirmed', 'pending']:
                keyboard.insert(-1, [InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order_{order_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                status_text,
                reply_markup,
                use_banner=False
            )
            
        except Exception as e:
            logger.error(f"Error tracking order: {e}")
            await update.callback_query.answer("❌ Error loading order status", show_alert=True)
    
    async def process_refund(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, order_id: str, reason: str = None):
        """Process a refund for an order"""
        lang = user.get('language', 'en')
        
        try:
            order = self.db.get_order_details(int(order_id))
            if not order or order['user_id'] != user['user_id']:
                await update.callback_query.answer("❌ Order not found", show_alert=True)
                return
            
            # Check if refund is allowed
            if order['status'] in ['cancelled', 'refunded']:
                await update.callback_query.answer("❌ Order already cancelled/refunded", show_alert=True)
                return
            
            # Process refund
            refund_amount = order['final_price']
            new_balance = user['balance'] + refund_amount
            
            # Update database
            success = self.db.update_order_status(int(order_id), 'refunded')
            if success:
                self.db.set_user_balance(user['user_id'], new_balance)
                
                # Log refund reason if provided
                if reason:
                    self.db.log_refund_reason(int(order_id), reason)
                
                text = f"""✅ <b>Refund Processed</b>

🆔 Order ID: #{order_id}
💰 Refund Amount: {format_currency(refund_amount)}
💳 New Balance: {format_currency(new_balance)}
"""
                
                if reason:
                    text += f"\n📝 Reason: {reason}"
                
                text += "\n\n✅ The refund has been processed successfully."
            else:
                text = "❌ <b>Refund Failed</b>\n\nThere was an error processing your refund. Please contact support."
            
            keyboard = [
                [InlineKeyboardButton("📋 View Order History", callback_data="menu_history")],
                [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.send_menu_with_banner(
                update,
                context,
                text,
                reply_markup,
                use_banner=False
            )
            
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            await update.callback_query.answer("❌ Error processing refund", show_alert=True)
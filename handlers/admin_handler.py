"""Admin handler module for TeleShop Bot.

Handles admin-related functionality including:
- Admin panel and system management
- User management (ban, balance, search)
- Maintenance mode control
- System logs and monitoring
- Bot configuration management
"""

import logging
import os
import glob
from datetime import datetime, timedelta
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .base_handler import BaseHandler
from translations import get_text
from utils import format_currency
from rate_limiter import rate_limit_check
from csrf_protection import csrf_protected, create_admin_keyboard

logger = logging.getLogger(__name__)

class AdminHandler(BaseHandler):
    """Handler for admin-related functionality."""
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, data: str):
        """Handle admin-related callbacks"""
        lang = user.get('language', 'en')
        
        # Main admin menu
        if data == "menu_admin":
            await self.admin_panel(update, context)
        
        # Admin actions with prefix
        elif data.startswith("admin_"):
            action = data.replace("admin_", "")
            await self.handle_admin_action(update, context, user, action)
        
        # Direct admin actions
        elif data in ["maintenance_on", "maintenance_off", "view_logs", "view_users", 
                      "search_user", "add_balance", "subtract_balance", "ban_user", 
                      "unban_user", "broadcast", "stats", "backup", "settings"]:
            await self.handle_admin_action(update, context, user, data)
        
        # Bot settings callbacks
        elif data.startswith("setting_"):
            setting = data.replace("setting_", "")
            await self.handle_bot_setting(update, context, user, setting)
        
        else:
            logger.warning(f"Unhandled admin callback: {data}")
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Access denied. You are not authorized.")
            return
        
        # Get user data for consistency
        user = self.db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found in database.")
            return
        
        # Clear previous messages using the optimized method
        await self._clear_previous_messages(update, context)
        
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
        
        # Send the admin panel using the centralized method
        await self.send_message_with_cleanup(
            update, context,
            "👑 <b>Admin Panel</b>\n\nSelect an action:",
            reply_markup
        )
    
    async def handle_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, action: str):
        """Handle specific admin actions"""
        if not self.bot_instance:
            logger.error("Bot instance not available in AdminHandler")
            await update.callback_query.answer("❌ Internal error occurred")
            return
        
        # Handle complex actions with IDs first
        if action.startswith("inv_strain_"):
            strain_id = action.split("_")[-1]
            await self.bot_instance.admin_add_inventory_for_strain(update, context, user, strain_id)
        elif action.startswith("inv_city_"):
            city_id = action.split("_")[-1]
            await self.bot_instance.admin_select_city_for_inventory(update, context, user, city_id)
        elif action.startswith("inv_loc_"):
            location_id = action.split("_")[-1]
            await self.bot_instance.admin_select_location_for_inventory(update, context, user, location_id)
        elif action.startswith("add_to_cat_"):
            category_id = action.split("_")[-1]
            await self.bot_instance.admin_add_product_to_category(update, context, user, category_id)
        elif action.startswith("custom_bal_promo_"):
            promo_code = action.replace("custom_bal_promo_", "")
            context.user_data['custom_balance_promo_code'] = promo_code
            await self.bot_instance.process_custom_balance_promo(update, context, user)
        elif action.startswith("create_bal_promo_"):
            # Handle preset balance promo actions (create_bal_promo_CODE_AMOUNT)
            parts = action.split("_")
            if len(parts) >= 4:
                promo_code = "_".join(parts[3:-1])  # Extract code part
                amount = parts[-1]  # Extract amount
                await self.bot_instance.process_preset_balance_promo(update, context, user, promo_code, float(amount))
            else:
                await update.callback_query.answer("❌ Invalid promo format")
        # Handle the specific admin actions
        elif action == "add_product":
            await self.bot_instance.admin_add_product(update, context, user)
        elif action == "add_inventory":
            await self.bot_instance.admin_add_inventory(update, context, user)
        elif action == "create_promo":
            await self.bot_instance.admin_create_promo(update, context, user)
        elif action == "create_discount":
            await self.bot_instance.admin_create_discount(update, context, user)
        elif action == "stats":
            await self.bot_instance.admin_show_stats(update, context, user)
        elif action == "user_management":
            await self.bot_instance.admin_user_management(update, context, user)
        elif action == "system_settings":
            await self.bot_instance.admin_system_settings(update, context, user)
        elif action == "database_tools":
            await self.bot_instance.admin_database_tools(update, context, user)
        elif action == "add_category":
            await self.bot_instance.admin_add_new_category(update, context, user)
        elif action == "promo_balance":
            await self.bot_instance.admin_create_balance_promo(update, context, user)
        elif action == "promo_discount":
            await self.bot_instance.admin_create_discount_promo(update, context, user)
        elif action == "promo_free":
            await self.bot_instance.admin_create_free_promo(update, context, user)
        else:
            # For any other admin actions, try to call the method dynamically
            method_name = f"admin_{action}"
            if hasattr(self.bot_instance, method_name):
                method = getattr(self.bot_instance, method_name)
                await method(update, context, user)
            else:
                logger.warning(f"Unhandled admin action: {action}")
                await update.callback_query.answer("❌ Action not implemented yet")
    
    async def handle_bot_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, setting: str):
        """Handle bot setting changes"""
        # This method needs to be implemented
        pass
    
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
    
    async def admin_toggle_maintenance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Toggle maintenance mode"""
        current_mode = self.config.get('maintenance_mode', False)
        new_mode = not current_mode
        
        # Update configuration
        self.config['maintenance_mode'] = new_mode
        # Note: save_bot_config method needs to be implemented in base class or main bot
        
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
    
    async def admin_view_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: View bot logs"""
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
                text += f"   ID: {u['user_id']} | {status}\n"
                text += f"   Balance: {format_currency(u['balance'])}\n\n"
        
        # Pagination buttons
        keyboard = []
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_users_page_{page-1}"))
        
        if len(users) == limit:  # There might be more pages
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_users_page_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
            [InlineKeyboardButton("💰 Manage Balance", callback_data="admin_manage_balance")],
            [InlineKeyboardButton("🚫 Ban/Unban User", callback_data="admin_ban_user")],
            [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    async def admin_search_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Search for a specific user"""
        if context.user_data.get('awaiting_user_search'):
            # Process search query
            search_query = update.message.text.strip()
            
            # Search by user ID or username
            found_users = []
            
            # Try to search by user ID
            if search_query.isdigit():
                found_user = self.db.get_user(int(search_query))
                if found_user:
                    found_users.append(found_user)
            
            # Search by username
            username_results = self.db.search_users_by_username(search_query)
            found_users.extend(username_results)
            
            # Remove duplicates
            seen_ids = set()
            unique_users = []
            for u in found_users:
                if u['user_id'] not in seen_ids:
                    unique_users.append(u)
                    seen_ids.add(u['user_id'])
            
            if not unique_users:
                text = f"🔍 <b>User Search Results</b>\n\nNo users found matching '{search_query}'"
            else:
                text = f"🔍 <b>User Search Results</b>\n\nFound {len(unique_users)} user(s):\n\n"
                for i, u in enumerate(unique_users[:10], 1):  # Show max 10 results
                    status = "🚫 Banned" if u.get('is_banned') else "✅ Active"
                    text += f"{i}. <b>{u['username'] or 'Unknown'}</b>\n"
                    text += f"   ID: {u['user_id']} | {status}\n"
                    text += f"   Balance: {format_currency(u['balance'])}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("🔍 Search Again", callback_data="admin_search_user")],
                [InlineKeyboardButton("👥 Back to All Users", callback_data="admin_view_users")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            context.user_data['awaiting_user_search'] = False
        else:
            # Show search prompt
            text = "🔍 <b>Search User</b>\n\nPlease enter:\n• User ID (numbers only)\n• Username (partial match supported)\n\nExample: 123456789 or @username"
            
            keyboard = [
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_view_users")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            context.user_data['awaiting_user_search'] = True
    
    async def admin_manage_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Manage user balance"""
        text = "💰 <b>Balance Management</b>\n\nChoose an action:"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Balance", callback_data="admin_add_balance")],
            [InlineKeyboardButton("➖ Remove Balance", callback_data="admin_remove_balance")],
            [InlineKeyboardButton("🔄 Set Balance", callback_data="admin_set_balance")],
            [InlineKeyboardButton("🔙 Back to Users", callback_data="admin_view_users")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    async def admin_ban_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Ban or unban a user"""
        if context.user_data.get('awaiting_ban_user_id'):
            # Process ban/unban
            user_input = update.message.text.strip()
            
            if not user_input.isdigit():
                await update.message.reply_text("❌ Please enter a valid user ID (numbers only)")
                return
            
            target_user_id = int(user_input)
            target_user = self.db.get_user(target_user_id)
            
            if not target_user:
                await update.message.reply_text(f"❌ User with ID {target_user_id} not found")
                context.user_data['awaiting_ban_user_id'] = False
                return
            
            # Toggle ban status
            is_banned = target_user.get('is_banned', False)
            new_status = not is_banned
            
            success = self.db.update_user_ban_status(target_user_id, new_status)
            
            if success:
                action = "banned" if new_status else "unbanned"
                text = f"✅ <b>User {action.title()}</b>\n\n"
                text += f"User: <b>{target_user['username'] or 'Unknown'}</b>\n"
                text += f"ID: {target_user_id}\n"
                text += f"Status: {'🚫 Banned' if new_status else '✅ Active'}"
            else:
                text = f"❌ <b>Failed to update user status</b>\n\nThere was an error updating the ban status for user {target_user_id}"
            
            keyboard = [
                [InlineKeyboardButton("🚫 Ban Another User", callback_data="admin_ban_user")],
                [InlineKeyboardButton("👥 Back to Users", callback_data="admin_view_users")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            context.user_data['awaiting_ban_user_id'] = False
        else:
            # Show ban prompt
            text = "🚫 <b>Ban/Unban User</b>\n\nPlease enter the User ID of the user you want to ban or unban:\n\nExample: 123456789"
            
            keyboard = [
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_view_users")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            context.user_data['awaiting_ban_user_id'] = True
    
    async def admin_confirm_ban_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, target_user_id: int, action: str):
        """Admin: Confirm ban/unban action"""
        target_user = self.db.get_user(target_user_id)
        
        if not target_user:
            text = "❌ <b>User Not Found</b>\n\nThe specified user could not be found."
            keyboard = [[InlineKeyboardButton("🔙 Back to Users", callback_data="admin_view_users")]]
        else:
            current_status = "Banned" if target_user.get('is_banned') else "Active"
            new_status = "Banned" if action == "ban" else "Active"
            
            text = f"🚫 <b>Confirm {action.title()} Action</b>\n\n"
            text += f"User: <b>{target_user['username'] or 'Unknown'}</b>\n"
            text += f"ID: {target_user_id}\n"
            text += f"Current Status: {current_status}\n"
            text += f"New Status: {new_status}\n\n"
            text += f"Are you sure you want to {action} this user?"
            
            keyboard = [
                [InlineKeyboardButton(f"✅ Confirm {action.title()}", callback_data=f"admin_confirm_{action}_{target_user_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_view_users")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    async def admin_test_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Admin: Test auto-cleanup functionality"""
        user_id = user['user_id']
        
        # Delete some recent messages to test cleanup
        deleted_count = 0
        try:
            for i in range(5):  # Try to delete last 5 messages
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=update.callback_query.message.message_id - i
                    )
                    deleted_count += 1
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error during cleanup test: {e}")
        
        text = f"🧹 <b>Auto-Cleanup Test</b>\n\n"
        text += f"✅ Successfully deleted {deleted_count} messages\n\n"
        text += "📋 <b>Cleanup Status:</b>\n"
        text += f"• Messages tracked: {len(self.auto_cleanup.user_messages.get(user_id, []))}\n"
        text += f"• Last activity: {self.auto_cleanup.user_activity.get(user_id, 'Never')}\n\n"
        text += "💡 <b>Note:</b> Auto-cleanup runs automatically based on user activity and configured intervals."
        
        keyboard = [
            [InlineKeyboardButton("🔄 Test Again", callback_data="admin_test_cleanup")],
            [InlineKeyboardButton("⚙️ Back to System Settings", callback_data="admin_system_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = await update.effective_chat.send_message(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        
        # Track this message for cleanup
        self.auto_cleanup.track_message(user_id, message.message_id, update)
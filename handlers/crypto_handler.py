import asyncio
import hashlib
import time
import random
import requests
import json
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from translations import get_text
from utils.helpers import format_currency
import qrcode
from io import BytesIO
import base64
from config import BTC_WALLET_ADDRESS

class BitcoinPriceAPI:
    """Handle Bitcoin price fetching from external APIs"""
    
    def __init__(self):
        self.cached_price = None
        self.cache_timestamp = 0
        self.cache_duration = 300  # 5 minutes cache
        self.fallback_price = 200000  # Fallback price in PLN
    
    async def get_btc_price_pln(self) -> float:
        """Get current Bitcoin price in PLN with caching"""
        current_time = time.time()
        
        # Return cached price if still valid
        if self.cached_price and (current_time - self.cache_timestamp) < self.cache_duration:
            return self.cached_price
        
        try:
            # Try CoinGecko API first
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=pln",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                price = data.get('bitcoin', {}).get('pln')
                if price:
                    self.cached_price = float(price)
                    self.cache_timestamp = current_time
                    return self.cached_price
            
            # Fallback to CoinAPI if CoinGecko fails
            response = requests.get(
                "https://rest.coinapi.io/v1/exchangerate/BTC/PLN",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                price = data.get('rate')
                if price:
                    self.cached_price = float(price)
                    self.cache_timestamp = current_time
                    return self.cached_price
                    
        except Exception as e:
            print(f"Error fetching Bitcoin price: {e}")
        
        # Return fallback price if all APIs fail
        return self.fallback_price
    
    def pln_to_btc(self, pln_amount: float, btc_price_pln: float) -> float:
        """Convert PLN amount to BTC"""
        return pln_amount / btc_price_pln
    
    def btc_to_pln(self, btc_amount: float, btc_price_pln: float) -> float:
        """Convert BTC amount to PLN"""
        return btc_amount * btc_price_pln

class CryptoPaymentHandler:
    """Handle cryptocurrency payments for the TeleShop bot"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        self.pending_payments = {}  # Store pending payment requests
        self.price_api = BitcoinPriceAPI()  # Initialize Bitcoin price API
        
    def generate_unique_amount(self, base_amount: float, user_id: int) -> float:
        """Generate a unique payment amount for verification"""
        # Add random cents to make amount unique for verification
        # This helps identify which user made the payment
        random.seed(f"{user_id}_{int(time.time())}")
        unique_cents = random.randint(10, 99)
        return base_amount + (unique_cents / 100.0)
    
    def generate_payment_address(self, user_id: int, amount: float) -> str:
        """Get the configured Bitcoin wallet address"""
        # Use the configured wallet address from .env
        return BTC_WALLET_ADDRESS
    
    async def generate_qr_code(self, address: str, amount_pln: float) -> BytesIO:
        """Generate QR code for Bitcoin payment"""
        # Convert PLN to BTC using real-time rate
        btc_rate = await self.price_api.get_btc_price_pln()
        btc_amount = self.price_api.pln_to_btc(amount_pln, btc_rate)
        
        # Bitcoin URI format
        bitcoin_uri = f"bitcoin:{address}?amount={btc_amount:.8f}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(bitcoin_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
    
    async def verify_bitcoin_payment(self, address: str, expected_amount_pln: float, tolerance_pln: float = 0.50) -> Dict:
        """Verify Bitcoin payment using blockchain API"""
        try:
            # Convert PLN amounts to BTC for verification using real-time rate
            btc_rate = await self.price_api.get_btc_price_pln()
            expected_btc = self.price_api.pln_to_btc(expected_amount_pln, btc_rate)
            tolerance_btc = self.price_api.pln_to_btc(tolerance_pln, btc_rate)
            
            # Use BlockCypher API (free tier) to check transactions
            api_url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/full"
            
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                return {'verified': False, 'error': 'API request failed'}
            
            data = response.json()
            
            # Check recent transactions (last 24 hours)
            current_time = time.time()
            recent_cutoff = current_time - (24 * 60 * 60)  # 24 hours ago
            
            if 'txs' in data:
                for tx in data['txs']:
                    # Check if transaction is recent
                    tx_time = tx.get('received', '')
                    if tx_time:
                        # Parse transaction time and check if it's recent
                        try:
                            from datetime import datetime
                            tx_timestamp = datetime.fromisoformat(tx_time.replace('Z', '+00:00')).timestamp()
                            if tx_timestamp < recent_cutoff:
                                continue
                        except:
                            continue
                    
                    # Check transaction outputs for our address
                    for output in tx.get('outputs', []):
                        if output.get('addresses') and address in output.get('addresses', []):
                            received_satoshi = output.get('value', 0)
                            received_btc = received_satoshi / 100000000  # Convert satoshi to BTC
                            
                            # Check if amount matches (within tolerance)
                            if abs(received_btc - expected_btc) <= tolerance_btc:
                                return {
                                    'verified': True,
                                    'tx_hash': tx.get('hash'),
                                    'amount_btc': received_btc,
                                    'amount_pln': self.price_api.btc_to_pln(received_btc, btc_rate),
                                    'confirmations': tx.get('confirmations', 0)
                                }
            
            return {'verified': False, 'error': 'No matching transaction found'}
            
        except requests.RequestException as e:
            return {'verified': False, 'error': f'Network error: {str(e)}'}
        except Exception as e:
            return {'verified': False, 'error': f'Verification error: {str(e)}'}
    
    async def show_crypto_payment_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show cryptocurrency payment options"""
        lang = user.get('language', 'en')
        
        keyboard = [
            [InlineKeyboardButton("← Back", callback_data="back_wallet")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        crypto_text = "₿ Enter amount (10-10,000 PLN):"
        
        await self.bot.send_menu_with_banner(update, crypto_text, reply_markup, use_banner=False)
        
        # Set state for custom amount input
        context.user_data['awaiting_crypto_amount'] = True
    

    
    async def process_bitcoin_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, amount: float):
        """Process Bitcoin payment request with unique amount"""
        lang = user.get('language', 'en')
        user_id = user['user_id']
        
        # Generate unique payment amount for verification
        unique_amount = self.generate_unique_amount(amount, user_id)
        
        # Generate payment address
        payment_address = self.generate_payment_address(user_id, unique_amount)
        
        # Store pending payment with unique amount
        payment_id = f"{user_id}_{int(time.time())}"
        self.pending_payments[payment_id] = {
            'user_id': user_id,
            'original_amount': amount,
            'unique_amount': unique_amount,
            'address': payment_address,
            'timestamp': time.time(),
            'status': 'pending'
        }
        
        # Generate QR code with unique amount
        qr_code = await self.generate_qr_code(payment_address, unique_amount)
        
        # Convert unique# Calculate BTC amount to display using real-time rate
        btc_rate = await self.price_api.get_btc_price_pln()
        btc_amount = self.price_api.pln_to_btc(unique_amount, btc_rate)
        
        keyboard = [
            [InlineKeyboardButton("✅ Verify", callback_data=f"verify_btc_{payment_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"crypto_cancel_{payment_id}")],
            [InlineKeyboardButton("← Back", callback_data="crypto_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        payment_text = f"""₿ <b>{format_currency(amount)}</b>

<code>{payment_address}</code>

Send: <b>{btc_amount:.8f} BTC</b>
Expires: 30 min"""
        
        # Send QR code image
        await update.callback_query.message.reply_photo(
            photo=qr_code,
            caption=payment_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    

    
    async def process_custom_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, amount_text: str):
        """Process custom amount input from user"""
        lang = user.get('language', 'en')
        
        try:
            # Clean the input and convert to float
            cleaned_amount = amount_text.replace(',', '.').replace(' ', '').strip()
            amount = float(cleaned_amount)
            
            # Validate amount
            if amount < 10:
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data="crypto_custom_amount")],
                    [InlineKeyboardButton("🔙 Back", callback_data="crypto_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"❌ <b>Amount Too Low</b>\n\n💰 Minimum amount: <b>10 PLN</b>\n📝 You entered: <b>{format_currency(amount)}</b>\n\n💡 Please enter at least 10 PLN.",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return
            elif amount > 10000:
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data="crypto_custom_amount")],
                    [InlineKeyboardButton("🔙 Back", callback_data="crypto_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"❌ <b>Amount Too High</b>\n\n💰 Maximum amount: <b>10,000 PLN</b>\n📝 You entered: <b>{format_currency(amount)}</b>\n\n💡 Please enter up to 10,000 PLN.",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return
            
            # Create a fake update object for process_bitcoin_payment
            fake_update = type('obj', (object,), {
                'callback_query': type('obj', (object,), {
                    'message': update.message
                })()
            })()
            
            # Process the payment
            await self.process_bitcoin_payment(fake_update, context, user, amount)
            
        except ValueError:
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="crypto_custom_amount")],
                [InlineKeyboardButton("🔙 Back", callback_data="crypto_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❌ <b>Invalid Amount Format</b>\n\n📝 You entered: <b>{amount_text}</b>\n\n💡 <b>Valid formats:</b>\n• 50\n• 150.50\n• 1000\n\n✍️ Please enter a valid number.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    
    async def check_payment_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
        """Check Bitcoin payment status (mock implementation)"""
        lang = context.user_data.get('language', 'en')
        
        if payment_id not in self.pending_payments:
            await update.callback_query.answer(get_text('payment_not_found', lang), show_alert=True)
            return
        
        payment = self.pending_payments[payment_id]
        
        # Mock payment verification - in real implementation, check blockchain
        # For demo, we'll simulate random confirmation after 30 seconds
        if time.time() - payment['timestamp'] > 30:
            # Simulate payment confirmation
            await self.confirm_payment(update, context, payment_id)
        else:
            await update.callback_query.answer(get_text('payment_still_pending', lang), show_alert=True)
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
        """Confirm Bitcoin payment and add balance"""
        lang = context.user_data.get('language', 'en')
        
        if payment_id not in self.pending_payments:
            await update.callback_query.answer(get_text('payment_not_found', lang), show_alert=True)
            return
        
        payment = self.pending_payments[payment_id]
        user_id = payment['user_id']
        amount = payment['original_amount']
        
        # Add balance to user account
        self.db.update_user_balance(user_id, amount)  # This method adds (increments) balance by amount
        
        # Mark payment as completed
        payment['status'] = 'completed'
        
        # Get updated user data
        user = self.db.get_user(user_id)
        new_balance = user.get('balance', 0)
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_back_wallet', lang), callback_data="back_wallet")],
            [InlineKeyboardButton(get_text('btn_back_menu', lang), callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        success_text = f"""{get_text('payment_confirmed_title', lang)}

✅ {get_text('payment_amount_added', lang).format(format_currency(amount))}
💰 {get_text('new_balance_label', lang).format(format_currency(new_balance))}

{get_text('payment_success_message', lang)}"""
        
        # Try to edit the caption if the original message was a photo; fallback to edit_text
        try:
            await update.callback_query.message.edit_caption(
                caption=success_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except:
            await update.callback_query.message.edit_text(
                success_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    
    async def cancel_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payment_id: str):
        """Cancel Bitcoin payment"""
        lang = context.user_data.get('language', 'en')
        
        if payment_id in self.pending_payments:
            del self.pending_payments[payment_id]
        
        await update.callback_query.answer(get_text('payment_cancelled', lang), show_alert=True)
        await self.show_crypto_payment_options(update, context, context.user_data.get('user', {}))
    
    async def show_payment_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict):
        """Show cryptocurrency payment history"""
        lang = user.get('language', 'en')
        user_id = user['user_id']
        
        # Get completed payments for this user
        completed_payments = [
            payment for payment in self.pending_payments.values()
            if payment['user_id'] == user_id and payment['status'] == 'completed'
        ]
        
        keyboard = [
            [InlineKeyboardButton(get_text('btn_back', lang), callback_data="crypto_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if not completed_payments:
            history_text = f"""{get_text('payment_history_title', lang)}

{get_text('no_payment_history', lang)}"""
        else:
            history_text = f"{get_text('payment_history_title', lang)}\n\n"
            
            for i, payment in enumerate(completed_payments[-10:], 1):  # Show last 10 payments
                timestamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(payment['timestamp']))
                amount_text = format_currency(payment['amount'])
                history_text += f"{i}. {timestamp} - {amount_text}\n"
        
        await self.bot.send_menu_with_banner(update, history_text, reply_markup, use_banner=False)
    
    async def verify_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, payment_id: str):
        """Handle payment verification callback"""
        try:
            lang = user.get('language', 'en')
            
            # Check if payment exists
            if payment_id not in self.pending_payments:
                try:
                    await update.callback_query.message.edit_caption(
                        caption="❌ Payment not found or expired",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="back_main")]])
                    )
                except:
                    await update.callback_query.message.edit_text(
                        "❌ Payment not found or expired",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')]])
                    )
                return
            
            payment_info = self.pending_payments[payment_id]
            
            # Check if payment is expired (30 minutes)
            if time.time() - payment_info['timestamp'] > 1800:
                try:
                    await update.callback_query.message.edit_caption(
                        caption="⏰ Payment expired. Please create a new payment.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔄 New Payment", callback_data='crypto_bitcoin'),
                            InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')
                        ]])
                    )
                except:
                    await update.callback_query.message.edit_text(
                        "⏰ Payment expired. Please create a new payment.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔄 New Payment", callback_data='crypto_bitcoin'),
                            InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')
                        ]])
                    )
                del self.pending_payments[payment_id]
                return
            
            # Show verification in progress
            try:
                await update.callback_query.message.edit_caption(
                    caption="🔍 Verifying...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⏳ Please wait", callback_data='checking')
                    ]])
                )
            except:
                await update.callback_query.message.edit_text(
                    "🔍 Verifying...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⏳ Please wait", callback_data='checking')
                    ]])
                )
            
            # For demo purposes, simulate payment verification
            # In a real implementation, this would check the blockchain
            import random
            verification_success = random.choice([True, False])  # 50% chance for demo
            
            if verification_success:
                # Payment verified successfully
                # Credit balance only once
                if payment_info.get('status') != 'completed':
                    try:
                        self.db.update_user_balance(user['user_id'], payment_info['original_amount'])
                    except Exception as _:
                        pass
                    payment_info['status'] = 'completed'
                
                keyboard = [
                    [InlineKeyboardButton("💰 Wallet", callback_data="wallet")],
                    [InlineKeyboardButton("🛒 Shop", callback_data="menu_buy")],
                    [InlineKeyboardButton("🏠 Menu", callback_data="back_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                success_text = f"""✅ <b>Payment Verified</b>

+{format_currency(payment_info['original_amount'])}

Balance updated successfully!"""
                
                try:
                    await update.callback_query.message.edit_caption(
                        caption=success_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except:
                    await update.callback_query.message.edit_text(
                        success_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                
            else:
                # Payment not found or verification failed
                btc_rate = await self.price_api.get_btc_price_pln()
                btc_amount = self.price_api.pln_to_btc(payment_info['unique_amount'], btc_rate)
                
                fail_text = f"""❌ <b>Payment Not Found</b>

Send: <b>{btc_amount:.8f} BTC</b>
Time: {max(0, int(1800 - (time.time() - payment_info['timestamp'])) // 60)} min left"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data=f'verify_btc_{payment_id}')],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f'crypto_cancel_{payment_id}')]
                ]
                
                try:
                    await update.callback_query.message.edit_caption(
                        caption=fail_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                except:
                    await update.callback_query.message.edit_text(
                        fail_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                
        except Exception as e:
            print(f"Error verifying payment: {e}")
            try:
                await update.callback_query.message.edit_caption(
                    caption="❌ Error occurred during verification. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                         InlineKeyboardButton("🔄 Try Again", callback_data=f'verify_btc_{payment_id}'),
                         InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')
                     ]])
                 )
            except:
                await update.callback_query.message.edit_text(
                    "❌ Error occurred during verification. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                         InlineKeyboardButton("🔄 Try Again", callback_data=f'verify_btc_{payment_id}'),
                         InlineKeyboardButton("🏠 Main Menu", callback_data='back_main')
                     ]])
                 )
    
    async def show_payment_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: Dict, payment_id: str):
        """Show detailed payment information"""
        lang = user.get('language', 'en')
        
        if payment_id not in self.pending_payments:
            await update.callback_query.answer(
                "❌ Payment not found",
                show_alert=True
            )
            return
        
        payment_info = self.pending_payments[payment_id]
        btc_rate = await self.price_api.get_btc_price_pln()
        btc_amount = self.price_api.pln_to_btc(payment_info['unique_amount'], btc_rate)
        time_remaining = max(0, int(1800 - (time.time() - payment_info['timestamp'])) // 60)
        
        keyboard = [
            [InlineKeyboardButton("✅ Verify Payment", callback_data=f"verify_btc_{payment_id}")],
            [InlineKeyboardButton("❌ Cancel Payment", callback_data=f"crypto_cancel_{payment_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="crypto_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        info_text = f"""📋 <b>Payment Information</b>

💰 <b>Amount to Add:</b> {format_currency(payment_info['original_amount'])}
💎 <b>Unique Amount to Send:</b> {format_currency(payment_info['unique_amount'])}
₿ <b>BTC Amount:</b> {btc_amount:.8f} BTC

📍 <b>Bitcoin Address:</b>
<code>{payment_info['address']}</code>

📊 <b>Payment Details:</b>
🆔 Payment ID: {payment_id}
📅 Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payment_info['timestamp']))}
⏰ Time Remaining: {time_remaining} minutes
📈 Status: {payment_info['status'].title()}

💡 <b>Instructions:</b>
1. Send exactly <b>{btc_amount:.8f} BTC</b> to the address above
2. Wait for blockchain confirmation
3. Click "✅ Verify Payment" to check status

⚠️ Make sure to send the exact BTC amount shown above."""
        
        await update.callback_query.edit_message_caption(
            caption=info_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
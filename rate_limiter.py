import time
import logging
from collections import defaultdict, deque
from typing import Dict, Deque
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import config

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter implementation with sliding window"""
    
    def __init__(self):
        # Store request timestamps for each user
        self.user_requests: Dict[int, Deque[float]] = defaultdict(deque)
        # Store cooldown periods for users who exceeded limits
        self.user_cooldowns: Dict[int, float] = {}
        
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        current_time = time.time()
        
        # Check if user is in cooldown period
        if user_id in self.user_cooldowns:
            if current_time < self.user_cooldowns[user_id]:
                return True
            else:
                # Cooldown expired, remove it
                del self.user_cooldowns[user_id]
        
        # Get user's request history
        user_requests = self.user_requests[user_id]
        
        # Remove requests older than the window
        window_start = current_time - config.RATE_LIMIT_WINDOW
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()
        
        # Check if user exceeded rate limit
        if len(user_requests) >= config.RATE_LIMIT_MESSAGES:
            # Add cooldown period
            self.user_cooldowns[user_id] = current_time + config.COOLDOWN_PERIOD
            logger.warning(f"User {user_id} exceeded rate limit. Cooldown applied.")
            return True
        
        # Add current request to history
        user_requests.append(current_time)
        return False
    
    def get_remaining_cooldown(self, user_id: int) -> int:
        """Get remaining cooldown time in seconds"""
        if user_id not in self.user_cooldowns:
            return 0
        
        remaining = self.user_cooldowns[user_id] - time.time()
        return max(0, int(remaining))
    
    def reset_user_limits(self, user_id: int):
        """Reset rate limits for a specific user (admin function)"""
        if user_id in self.user_requests:
            del self.user_requests[user_id]
        if user_id in self.user_cooldowns:
            del self.user_cooldowns[user_id]
        logger.info(f"Rate limits reset for user {user_id}")

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit_check(func):
    """Decorator to apply rate limiting to bot handlers"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Skip rate limiting for admins
        if hasattr(self, 'is_admin') and self.is_admin(user_id):
            return await func(self, update, context, *args, **kwargs)
        
        # Check rate limit
        if rate_limiter.is_rate_limited(user_id):
            remaining_cooldown = rate_limiter.get_remaining_cooldown(user_id)
            
            # Send rate limit message
            rate_limit_msg = (
                f"⚠️ <b>Rate Limit Exceeded</b>\n\n"
                f"You're sending messages too quickly. "
                f"Please wait {remaining_cooldown} seconds before trying again.\n\n"
                f"<i>This helps keep the bot running smoothly for everyone.</i>"
            )
            
            try:
                if update.callback_query:
                    await update.callback_query.answer(f"Rate limited. Wait {remaining_cooldown}s", show_alert=True)
                else:
                    await update.message.reply_text(rate_limit_msg, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Error sending rate limit message: {e}")
            
            return
        
        # Execute the original function
        return await func(self, update, context, *args, **kwargs)
    
    return wrapper
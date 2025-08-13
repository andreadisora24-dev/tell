"""Helper utilities for TeleShop Bot."""

import re
import hashlib
import secrets
import string
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

def generate_receipt_text(order_data: Dict[str, Any], lang: str = 'en') -> str:
    """Generate receipt text for order"""
    from translations import get_text
    
    # Import format_currency from the main utils.py
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils import format_currency
    
    receipt = f"""
🧾 <b>ORDER RECEIPT</b>
━━━━━━━━━━━━━━━━━━━━━

📦 Order ID: {order_data.get('order_id', 'N/A')}
📅 Date: {order_data.get('date', 'N/A')}
👤 Customer: {order_data.get('customer_id', 'N/A')}

<b>ITEMS:</b>
🌿 {order_data.get('product_name', 'N/A')}
   Strain: {order_data.get('strain_name', 'N/A')}
   Quantity: {order_data.get('quantity', 0)} {order_data.get('unit', 'g')}
   Price: {format_currency(order_data.get('unit_price', 0))}

📍 <b>DELIVERY LOCATION:</b>
   {order_data.get('location_name', 'N/A')}
   Coordinates: <code>{order_data.get('coordinates', 'N/A')}</code>

💰 <b>PAYMENT SUMMARY:</b>
   Subtotal: {format_currency(order_data.get('subtotal', 0))}
   Discount: -{format_currency(order_data.get('discount_amount', 0))}
   <b>Total: {format_currency(order_data.get('total_price', 0))}</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>IMPORTANT:</b>
• Save these coordinates safely
• Pickup within 24 hours
• Contact support if needed

🔒 This transaction is secure and anonymous
    """
    
    return receipt

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (7-15 digits)
    if len(digits_only) < 7 or len(digits_only) > 15:
        return False
    
    # Basic pattern matching for common formats
    patterns = [
        r'^\+?[1-9]\d{6,14}$',  # International format
        r'^[0-9]{7,15}$',       # Simple digits
        r'^\([0-9]{3}\)\s?[0-9]{3}-?[0-9]{4}$',  # US format
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone):
            return True
    
    return False

def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input by removing potentially harmful characters.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove potentially harmful characters
    text = re.sub(r'[<>"\'\\\/]', '', text)
    
    # Limit length
    text = text[:max_length]
    
    # Strip whitespace
    return text.strip()

def format_currency(amount: Union[float, Decimal, int], currency: str = "USD") -> str:
    """Format currency amount for display.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        str: Formatted currency string
    """
    try:
        if isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        
        # Round to 2 decimal places
        amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if currency.upper() == "USD":
            return f"${amount:.2f}"
        else:
            return f"{amount:.2f} {currency}"
            
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        return "$0.00"

def generate_order_id() -> str:
    """Generate a unique order ID.
    
    Returns:
        str: Unique order ID
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"ORD{timestamp}{random_part}"

def generate_promo_code(length: int = 8) -> str:
    """Generate a random promo code.
    
    Args:
        length: Length of the promo code
        
    Returns:
        str: Generated promo code
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with salt.
    
    Args:
        password: Password to hash
        salt: Optional salt (generated if not provided)
        
    Returns:
        tuple: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt
    salted_password = password + salt
    
    # Hash using SHA-256
    hashed = hashlib.sha256(salted_password.encode()).hexdigest()
    
    return hashed, salt

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed_password: Stored hash
        salt: Salt used for hashing
        
    Returns:
        bool: True if password matches
    """
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == hashed_password

def calculate_discount(original_price: Decimal, discount_percent: float) -> Decimal:
    """Calculate discounted price.
    
    Args:
        original_price: Original price
        discount_percent: Discount percentage (0-100)
        
    Returns:
        Decimal: Discounted price
    """
    if discount_percent < 0 or discount_percent > 100:
        return original_price
    
    discount_amount = original_price * Decimal(str(discount_percent / 100))
    discounted_price = original_price - discount_amount
    
    return discounted_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def format_datetime(dt: datetime, format_type: str = "default") -> str:
    """Format datetime for display.
    
    Args:
        dt: Datetime to format
        format_type: Type of formatting
        
    Returns:
        str: Formatted datetime string
    """
    formats = {
        "default": "%Y-%m-%d %H:%M:%S",
        "date_only": "%Y-%m-%d",
        "time_only": "%H:%M:%S",
        "friendly": "%B %d, %Y at %I:%M %p",
        "short": "%m/%d/%Y %H:%M"
    }
    
    format_str = formats.get(format_type, formats["default"])
    return dt.strftime(format_str)

def time_ago(dt: datetime) -> str:
    """Get human-readable time difference.
    
    Args:
        dt: Datetime to compare
        
    Returns:
        str: Human-readable time difference
    """
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

def paginate_list(items: List[Any], page: int, per_page: int = 10) -> Dict[str, Any]:
    """Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page: Current page (0-based)
        per_page: Items per page
        
    Returns:
        dict: Pagination info and items
    """
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    page_items = items[start_idx:end_idx]
    
    return {
        'items': page_items,
        'current_page': page,
        'total_pages': total_pages,
        'total_items': total_items,
        'has_previous': page > 0,
        'has_next': page < total_pages - 1,
        'per_page': per_page
    }

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def clean_filename(filename: str) -> str:
    """Clean filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Cleaned filename
    """
    # Remove invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # Strip leading/trailing underscores and spaces
    cleaned = cleaned.strip('_ ')
    
    return cleaned or "unnamed_file"

def is_valid_json(json_string: str) -> bool:
    """Check if string is valid JSON.
    
    Args:
        json_string: String to validate
        
    Returns:
        bool: True if valid JSON
    """
    try:
        import json
        json.loads(json_string)
        return True
    except (ValueError, TypeError):
        return False

def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text.
    
    Args:
        text: Text to extract numbers from
        
    Returns:
        list: List of extracted numbers
    """
    pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]

def generate_captcha_question() -> Dict[str, Any]:
    """Generate a simple math captcha question.
    
    Returns:
        dict: Question and answer
    """
    import random
    
    operations = [
        ('add', '+'),
        ('subtract', '-'),
        ('multiply', '×')
    ]
    
    operation, symbol = random.choice(operations)
    
    if operation == 'add':
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        answer = a + b
    elif operation == 'subtract':
        a = random.randint(10, 30)
        b = random.randint(1, a - 1)
        answer = a - b
    else:  # multiply
        a = random.randint(2, 10)
        b = random.randint(2, 10)
        answer = a * b
    
    question = f"{a} {symbol} {b} = ?"
    
    return {
        'question': question,
        'answer': answer,
        'operation': operation
    }

def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data like phone numbers or emails.
    
    Args:
        data: Data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible
        
    Returns:
        str: Masked data
    """
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    visible_start = visible_chars // 2
    visible_end = visible_chars - visible_start
    
    masked_length = len(data) - visible_chars
    
    return (
        data[:visible_start] + 
        mask_char * masked_length + 
        data[-visible_end:] if visible_end > 0 else ""
    )

def calculate_shipping_cost(distance_km: float, weight_kg: float) -> Decimal:
    """Calculate shipping cost based on distance and weight.
    
    Args:
        distance_km: Distance in kilometers
        weight_kg: Weight in kilograms
        
    Returns:
        Decimal: Shipping cost
    """
    base_cost = Decimal('5.00')  # Base shipping cost
    distance_rate = Decimal('0.50')  # Per km
    weight_rate = Decimal('2.00')  # Per kg
    
    distance_cost = Decimal(str(distance_km)) * distance_rate
    weight_cost = Decimal(str(weight_kg)) * weight_rate
    
    total_cost = base_cost + distance_cost + weight_cost
    
    return total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        float: File size in MB
    """
    try:
        import os
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0

def create_backup_filename(original_name: str) -> str:
    """Create a backup filename with timestamp.
    
    Args:
        original_name: Original filename
        
    Returns:
        str: Backup filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = original_name.rsplit('.', 1) if '.' in original_name else (original_name, '')
    
    backup_name = f"{name}_backup_{timestamp}"
    if ext:
        backup_name += f".{ext}"
    
    return backup_name

def validate_coordinates(lat: Union[str, float], lon: Union[str, float]) -> bool:
    """Validate GPS coordinates.
    
    Args:
        lat: Latitude value
        lon: Longitude value
        
    Returns:
        bool: True if coordinates are valid
    """
    try:
        lat_float = float(lat)
        lon_float = float(lon)
        
        # Check latitude range (-90 to 90)
        if not (-90 <= lat_float <= 90):
            return False
            
        # Check longitude range (-180 to 180)
        if not (-180 <= lon_float <= 180):
            return False
            
        return True
    except (ValueError, TypeError):
        return False
"""Validation utilities for TeleShop Bot."""

import re
import logging
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime

class ValidationError(Exception):
    """Custom validation error exception."""
    pass

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self, is_valid: bool, error_message: str = "", cleaned_value: Any = None):
        self.is_valid = is_valid
        self.error_message = error_message
        self.cleaned_value = cleaned_value
    
    def __bool__(self):
        return self.is_valid

class Validator:
    """Main validation class with various validation methods."""
    
    @staticmethod
    def validate_user_id(user_id: Any) -> ValidationResult:
        """Validate user ID.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            ValidationResult: Validation result
        """
        try:
            user_id = int(user_id)
            if user_id <= 0:
                return ValidationResult(False, "User ID must be positive")
            return ValidationResult(True, cleaned_value=user_id)
        except (ValueError, TypeError):
            return ValidationResult(False, "Invalid user ID format")
    
    @staticmethod
    def validate_username(username: str) -> ValidationResult:
        """Validate username.
        
        Args:
            username: Username to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not username or not isinstance(username, str):
            return ValidationResult(False, "Username is required")
        
        username = username.strip()
        
        if len(username) < 3:
            return ValidationResult(False, "Username must be at least 3 characters")
        
        if len(username) > 50:
            return ValidationResult(False, "Username must be less than 50 characters")
        
        # Allow letters, numbers, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return ValidationResult(False, "Username can only contain letters, numbers, underscores, and hyphens")
        
        return ValidationResult(True, cleaned_value=username)
    
    @staticmethod
    def validate_phone_number(phone: str) -> ValidationResult:
        """Validate phone number.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not phone or not isinstance(phone, str):
            return ValidationResult(False, "Phone number is required")
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) < 7:
            return ValidationResult(False, "Phone number is too short")
        
        if len(digits_only) > 15:
            return ValidationResult(False, "Phone number is too long")
        
        # Format the phone number
        if len(digits_only) == 10:  # US format
            formatted = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only[0] == '1':  # US with country code
            formatted = f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
        else:
            formatted = f"+{digits_only}"
        
        return ValidationResult(True, cleaned_value=formatted)
    
    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """Validate email address.
        
        Args:
            email: Email to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not email or not isinstance(email, str):
            return ValidationResult(False, "Email is required")
        
        email = email.strip().lower()
        
        if len(email) > 254:
            return ValidationResult(False, "Email is too long")
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return ValidationResult(False, "Invalid email format")
        
        return ValidationResult(True, cleaned_value=email)
    
    @staticmethod
    def validate_password(password: str) -> ValidationResult:
        """Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not password or not isinstance(password, str):
            return ValidationResult(False, "Password is required")
        
        if len(password) < 8:
            return ValidationResult(False, "Password must be at least 8 characters")
        
        if len(password) > 128:
            return ValidationResult(False, "Password is too long")
        
        # Check for at least one uppercase, lowercase, digit, and special character
        checks = [
            (r'[a-z]', "Password must contain at least one lowercase letter"),
            (r'[A-Z]', "Password must contain at least one uppercase letter"),
            (r'\d', "Password must contain at least one digit"),
            (r'[!@#$%^&*(),.?":{}|<>]', "Password must contain at least one special character")
        ]
        
        for pattern, message in checks:
            if not re.search(pattern, password):
                return ValidationResult(False, message)
        
        return ValidationResult(True, cleaned_value=password)
    
    @staticmethod
    def validate_amount(amount: Any, min_amount: float = 0.01, max_amount: float = 10000.0) -> ValidationResult:
        """Validate monetary amount.
        
        Args:
            amount: Amount to validate
            min_amount: Minimum allowed amount
            max_amount: Maximum allowed amount
            
        Returns:
            ValidationResult: Validation result
        """
        try:
            if isinstance(amount, str):
                # Remove currency symbols and spaces
                amount = re.sub(r'[^\d.-]', '', amount)
            
            amount = float(amount)
            
            if amount < min_amount:
                return ValidationResult(False, f"Amount must be at least ${min_amount:.2f}")
            
            if amount > max_amount:
                return ValidationResult(False, f"Amount cannot exceed ${max_amount:.2f}")
            
            # Convert to Decimal for precision
            decimal_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
            
            return ValidationResult(True, cleaned_value=decimal_amount)
            
        except (ValueError, TypeError):
            return ValidationResult(False, "Invalid amount format")
    
    @staticmethod
    def validate_quantity(quantity: Any, min_qty: int = 1, max_qty: int = 100) -> ValidationResult:
        """Validate quantity.
        
        Args:
            quantity: Quantity to validate
            min_qty: Minimum allowed quantity
            max_qty: Maximum allowed quantity
            
        Returns:
            ValidationResult: Validation result
        """
        try:
            quantity = int(quantity)
            
            if quantity < min_qty:
                return ValidationResult(False, f"Quantity must be at least {min_qty}")
            
            if quantity > max_qty:
                return ValidationResult(False, f"Quantity cannot exceed {max_qty}")
            
            return ValidationResult(True, cleaned_value=quantity)
            
        except (ValueError, TypeError):
            return ValidationResult(False, "Invalid quantity format")
    
    @staticmethod
    def validate_product_name(name: str) -> ValidationResult:
        """Validate product name.
        
        Args:
            name: Product name to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not name or not isinstance(name, str):
            return ValidationResult(False, "Product name is required")
        
        name = name.strip()
        
        if len(name) < 2:
            return ValidationResult(False, "Product name must be at least 2 characters")
        
        if len(name) > 200:
            return ValidationResult(False, "Product name must be less than 200 characters")
        
        # Remove potentially harmful characters
        cleaned_name = re.sub(r'[<>"\'\\\/]', '', name)
        
        return ValidationResult(True, cleaned_value=cleaned_name)
    
    @staticmethod
    def validate_description(description: str, max_length: int = 1000) -> ValidationResult:
        """Validate description text.
        
        Args:
            description: Description to validate
            max_length: Maximum allowed length
            
        Returns:
            ValidationResult: Validation result
        """
        if not description or not isinstance(description, str):
            return ValidationResult(False, "Description is required")
        
        description = description.strip()
        
        if len(description) < 10:
            return ValidationResult(False, "Description must be at least 10 characters")
        
        if len(description) > max_length:
            return ValidationResult(False, f"Description must be less than {max_length} characters")
        
        # Remove HTML tags and potentially harmful characters
        cleaned_desc = re.sub(r'<[^>]+>', '', description)
        cleaned_desc = re.sub(r'[<>"\'\\\/]', '', cleaned_desc)
        
        return ValidationResult(True, cleaned_value=cleaned_desc)
    
    @staticmethod
    def validate_address(address: str) -> ValidationResult:
        """Validate delivery address.
        
        Args:
            address: Address to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not address or not isinstance(address, str):
            return ValidationResult(False, "Address is required")
        
        address = address.strip()
        
        if len(address) < 10:
            return ValidationResult(False, "Address must be at least 10 characters")
        
        if len(address) > 500:
            return ValidationResult(False, "Address must be less than 500 characters")
        
        # Basic address validation - should contain numbers and letters
        if not re.search(r'\d', address):
            return ValidationResult(False, "Address should contain a house/building number")
        
        if not re.search(r'[a-zA-Z]', address):
            return ValidationResult(False, "Address should contain street name")
        
        # Clean the address
        cleaned_address = re.sub(r'[<>"\'\\\/]', '', address)
        
        return ValidationResult(True, cleaned_value=cleaned_address)
    
    @staticmethod
    def validate_promo_code(promo_code: str) -> ValidationResult:
        """Validate promo code format.
        
        Args:
            promo_code: Promo code to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not promo_code or not isinstance(promo_code, str):
            return ValidationResult(False, "Promo code is required")
        
        promo_code = promo_code.strip().upper()
        
        if len(promo_code) < 4:
            return ValidationResult(False, "Promo code must be at least 4 characters")
        
        if len(promo_code) > 20:
            return ValidationResult(False, "Promo code must be less than 20 characters")
        
        # Allow only alphanumeric characters
        if not re.match(r'^[A-Z0-9]+$', promo_code):
            return ValidationResult(False, "Promo code can only contain letters and numbers")
        
        return ValidationResult(True, cleaned_value=promo_code)
    
    @staticmethod
    def validate_discount_percent(discount: Any) -> ValidationResult:
        """Validate discount percentage.
        
        Args:
            discount: Discount percentage to validate
            
        Returns:
            ValidationResult: Validation result
        """
        try:
            discount = float(discount)
            
            if discount < 0:
                return ValidationResult(False, "Discount cannot be negative")
            
            if discount > 100:
                return ValidationResult(False, "Discount cannot exceed 100%")
            
            return ValidationResult(True, cleaned_value=discount)
            
        except (ValueError, TypeError):
            return ValidationResult(False, "Invalid discount format")
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: str) -> ValidationResult:
        """Validate date range.
        
        Args:
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            
        Returns:
            ValidationResult: Validation result
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start_dt >= end_dt:
                return ValidationResult(False, "Start date must be before end date")
            
            if start_dt < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                return ValidationResult(False, "Start date cannot be in the past")
            
            return ValidationResult(True, cleaned_value=(start_dt, end_dt))
            
        except ValueError:
            return ValidationResult(False, "Invalid date format. Use YYYY-MM-DD")
    
    @staticmethod
    def validate_search_query(query: str) -> ValidationResult:
        """Validate search query.
        
        Args:
            query: Search query to validate
            
        Returns:
            ValidationResult: Validation result
        """
        if not query or not isinstance(query, str):
            return ValidationResult(False, "Search query is required")
        
        query = query.strip()
        
        if len(query) < 2:
            return ValidationResult(False, "Search query must be at least 2 characters")
        
        if len(query) > 100:
            return ValidationResult(False, "Search query must be less than 100 characters")
        
        # Remove potentially harmful characters
        cleaned_query = re.sub(r'[<>"\'\\\/]', '', query)
        
        # Remove excessive whitespace
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query)
        
        return ValidationResult(True, cleaned_value=cleaned_query)
    
    @staticmethod
    def validate_language_code(lang_code: str) -> ValidationResult:
        """Validate language code.
        
        Args:
            lang_code: Language code to validate
            
        Returns:
            ValidationResult: Validation result
        """
        valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko']
        
        if not lang_code or not isinstance(lang_code, str):
            return ValidationResult(False, "Language code is required")
        
        lang_code = lang_code.lower().strip()
        
        if lang_code not in valid_languages:
            return ValidationResult(False, f"Unsupported language. Supported: {', '.join(valid_languages)}")
        
        return ValidationResult(True, cleaned_value=lang_code)
    
    @staticmethod
    def validate_file_upload(file_data: Dict[str, Any]) -> ValidationResult:
        """Validate file upload data.
        
        Args:
            file_data: File data dictionary
            
        Returns:
            ValidationResult: Validation result
        """
        if not file_data or not isinstance(file_data, dict):
            return ValidationResult(False, "File data is required")
        
        # Check required fields
        required_fields = ['filename', 'content_type', 'size']
        for field in required_fields:
            if field not in file_data:
                return ValidationResult(False, f"Missing required field: {field}")
        
        filename = file_data['filename']
        content_type = file_data['content_type']
        size = file_data['size']
        
        # Validate filename
        if not filename or len(filename) > 255:
            return ValidationResult(False, "Invalid filename")
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if size > max_size:
            return ValidationResult(False, "File size exceeds 10MB limit")
        
        # Validate content type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/csv'
        ]
        
        if content_type not in allowed_types:
            return ValidationResult(False, "Unsupported file type")
        
        return ValidationResult(True, cleaned_value=file_data)

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
    """Validate that all required fields are present and not empty.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        ValidationResult: Validation result
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return ValidationResult(
            False, 
            f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    return ValidationResult(True)

def validate_and_clean_data(data: Dict[str, Any], validation_rules: Dict[str, callable]) -> Dict[str, Any]:
    """Validate and clean data using provided validation rules.
    
    Args:
        data: Data to validate
        validation_rules: Dictionary mapping field names to validation functions
        
    Returns:
        dict: Cleaned data
        
    Raises:
        ValidationError: If validation fails
    """
    cleaned_data = {}
    errors = []
    
    for field, validator in validation_rules.items():
        if field in data:
            try:
                result = validator(data[field])
                if result.is_valid:
                    cleaned_data[field] = result.cleaned_value
                else:
                    errors.append(f"{field}: {result.error_message}")
            except Exception as e:
                logger.error(f"Validation error for field {field}: {e}")
                errors.append(f"{field}: Validation failed")
    
    if errors:
        raise ValidationError(f"Validation failed: {'; '.join(errors)}")
    
    return cleaned_data
"""Utilities package for TeleShop Bot.

This package contains utility functions and classes for:
- helpers: General helper functions for formatting, validation, etc.
- validators: Input validation classes and functions
"""

from .helpers import (
    validate_phone_number, validate_email, sanitize_input, format_currency,
    generate_order_id, generate_promo_code, hash_password, verify_password,
    calculate_discount, format_datetime, time_ago, paginate_list,
    truncate_text, clean_filename, is_valid_json, extract_numbers,
    generate_captcha_question, mask_sensitive_data, calculate_shipping_cost,
    get_file_size_mb, create_backup_filename, validate_coordinates
)

from .validators import (
    ValidationResult, Validator, validate_required_fields, validate_and_clean_data
)

__all__ = [
    # Helper functions
    'validate_phone_number', 'validate_email', 'sanitize_input', 'format_currency',
    'generate_order_id', 'generate_promo_code', 'hash_password', 'verify_password',
    'calculate_discount', 'format_datetime', 'time_ago', 'paginate_list',
    'truncate_text', 'clean_filename', 'is_valid_json', 'extract_numbers',
    'generate_captcha_question', 'mask_sensitive_data', 'calculate_shipping_cost',
    'get_file_size_mb', 'create_backup_filename', 'validate_coordinates',
    
    # Validation classes and functions
    'ValidationResult', 'Validator', 'validate_required_fields', 'validate_and_clean_data'
]
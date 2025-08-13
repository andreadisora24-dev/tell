"""Tests for validation utilities."""

import unittest
from decimal import Decimal
from datetime import datetime, timedelta

from utils.validators import Validator, ValidationResult, validate_required_fields
from core.exceptions import ValidationError

class TestValidator(unittest.TestCase):
    """Test cases for Validator class."""
    
    def test_validate_user_id_success(self):
        """Test successful user ID validation."""
        result = Validator.validate_user_id(123)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, 123)
    
    def test_validate_user_id_invalid(self):
        """Test invalid user ID validation."""
        # Test negative ID
        result = Validator.validate_user_id(-1)
        self.assertFalse(result.is_valid)
        self.assertIn("positive", result.error_message)
        
        # Test non-numeric ID
        result = Validator.validate_user_id("abc")
        self.assertFalse(result.is_valid)
        self.assertIn("format", result.error_message)
    
    def test_validate_username_success(self):
        """Test successful username validation."""
        result = Validator.validate_username("test_user123")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "test_user123")
    
    def test_validate_username_invalid(self):
        """Test invalid username validation."""
        # Test too short
        result = Validator.validate_username("ab")
        self.assertFalse(result.is_valid)
        self.assertIn("3 characters", result.error_message)
        
        # Test too long
        result = Validator.validate_username("a" * 51)
        self.assertFalse(result.is_valid)
        self.assertIn("50 characters", result.error_message)
        
        # Test invalid characters
        result = Validator.validate_username("user@name")
        self.assertFalse(result.is_valid)
        self.assertIn("letters, numbers", result.error_message)
    
    def test_validate_phone_number_success(self):
        """Test successful phone number validation."""
        # Test US format
        result = Validator.validate_phone_number("1234567890")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "(123) 456-7890")
        
        # Test with country code
        result = Validator.validate_phone_number("11234567890")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "+1 (123) 456-7890")
    
    def test_validate_phone_number_invalid(self):
        """Test invalid phone number validation."""
        # Test too short
        result = Validator.validate_phone_number("123456")
        self.assertFalse(result.is_valid)
        self.assertIn("too short", result.error_message)
        
        # Test too long
        result = Validator.validate_phone_number("1" * 16)
        self.assertFalse(result.is_valid)
        self.assertIn("too long", result.error_message)
    
    def test_validate_email_success(self):
        """Test successful email validation."""
        result = Validator.validate_email("test@example.com")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "test@example.com")
        
        # Test with uppercase
        result = Validator.validate_email("TEST@EXAMPLE.COM")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "test@example.com")
    
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        # Test missing @
        result = Validator.validate_email("testexample.com")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid email", result.error_message)
        
        # Test missing domain
        result = Validator.validate_email("test@")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid email", result.error_message)
    
    def test_validate_password_success(self):
        """Test successful password validation."""
        result = Validator.validate_password("Password123!")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "Password123!")
    
    def test_validate_password_invalid(self):
        """Test invalid password validation."""
        # Test too short
        result = Validator.validate_password("Pass1!")
        self.assertFalse(result.is_valid)
        self.assertIn("8 characters", result.error_message)
        
        # Test missing uppercase
        result = Validator.validate_password("password123!")
        self.assertFalse(result.is_valid)
        self.assertIn("uppercase", result.error_message)
        
        # Test missing lowercase
        result = Validator.validate_password("PASSWORD123!")
        self.assertFalse(result.is_valid)
        self.assertIn("lowercase", result.error_message)
        
        # Test missing digit
        result = Validator.validate_password("Password!")
        self.assertFalse(result.is_valid)
        self.assertIn("digit", result.error_message)
        
        # Test missing special character
        result = Validator.validate_password("Password123")
        self.assertFalse(result.is_valid)
        self.assertIn("special character", result.error_message)
    
    def test_validate_amount_success(self):
        """Test successful amount validation."""
        result = Validator.validate_amount("25.50")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, Decimal('25.50'))
        
        # Test with currency symbol
        result = Validator.validate_amount("$25.50")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, Decimal('25.50'))
    
    def test_validate_amount_invalid(self):
        """Test invalid amount validation."""
        # Test too small
        result = Validator.validate_amount("0.00")
        self.assertFalse(result.is_valid)
        self.assertIn("at least", result.error_message)
        
        # Test too large
        result = Validator.validate_amount("15000.00")
        self.assertFalse(result.is_valid)
        self.assertIn("cannot exceed", result.error_message)
        
        # Test invalid format
        result = Validator.validate_amount("abc")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid amount", result.error_message)
    
    def test_validate_quantity_success(self):
        """Test successful quantity validation."""
        result = Validator.validate_quantity(5)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, 5)
        
        # Test string input
        result = Validator.validate_quantity("10")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, 10)
    
    def test_validate_quantity_invalid(self):
        """Test invalid quantity validation."""
        # Test too small
        result = Validator.validate_quantity(0)
        self.assertFalse(result.is_valid)
        self.assertIn("at least", result.error_message)
        
        # Test too large
        result = Validator.validate_quantity(150)
        self.assertFalse(result.is_valid)
        self.assertIn("cannot exceed", result.error_message)
    
    def test_validate_product_name_success(self):
        """Test successful product name validation."""
        result = Validator.validate_product_name("Test Product")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "Test Product")
    
    def test_validate_product_name_invalid(self):
        """Test invalid product name validation."""
        # Test too short
        result = Validator.validate_product_name("A")
        self.assertFalse(result.is_valid)
        self.assertIn("2 characters", result.error_message)
        
        # Test too long
        result = Validator.validate_product_name("A" * 201)
        self.assertFalse(result.is_valid)
        self.assertIn("200 characters", result.error_message)
    
    def test_validate_address_success(self):
        """Test successful address validation."""
        result = Validator.validate_address("123 Main Street, City, State")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "123 Main Street, City, State")
    
    def test_validate_address_invalid(self):
        """Test invalid address validation."""
        # Test too short
        result = Validator.validate_address("123 Main")
        self.assertFalse(result.is_valid)
        self.assertIn("10 characters", result.error_message)
        
        # Test missing number
        result = Validator.validate_address("Main Street, City, State")
        self.assertFalse(result.is_valid)
        self.assertIn("house/building number", result.error_message)
        
        # Test missing letters
        result = Validator.validate_address("123456789012345")
        self.assertFalse(result.is_valid)
        self.assertIn("street name", result.error_message)
    
    def test_validate_promo_code_success(self):
        """Test successful promo code validation."""
        result = Validator.validate_promo_code("SAVE20")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "SAVE20")
        
        # Test lowercase input
        result = Validator.validate_promo_code("save20")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "SAVE20")
    
    def test_validate_promo_code_invalid(self):
        """Test invalid promo code validation."""
        # Test too short
        result = Validator.validate_promo_code("ABC")
        self.assertFalse(result.is_valid)
        self.assertIn("4 characters", result.error_message)
        
        # Test invalid characters
        result = Validator.validate_promo_code("SAVE-20")
        self.assertFalse(result.is_valid)
        self.assertIn("letters and numbers", result.error_message)
    
    def test_validate_discount_percent_success(self):
        """Test successful discount percentage validation."""
        result = Validator.validate_discount_percent(25.5)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, 25.5)
        
        # Test string input
        result = Validator.validate_discount_percent("15")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, 15.0)
    
    def test_validate_discount_percent_invalid(self):
        """Test invalid discount percentage validation."""
        # Test negative
        result = Validator.validate_discount_percent(-5)
        self.assertFalse(result.is_valid)
        self.assertIn("cannot be negative", result.error_message)
        
        # Test over 100%
        result = Validator.validate_discount_percent(150)
        self.assertFalse(result.is_valid)
        self.assertIn("cannot exceed 100%", result.error_message)
    
    def test_validate_search_query_success(self):
        """Test successful search query validation."""
        result = Validator.validate_search_query("laptop computer")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "laptop computer")
    
    def test_validate_search_query_invalid(self):
        """Test invalid search query validation."""
        # Test too short
        result = Validator.validate_search_query("a")
        self.assertFalse(result.is_valid)
        self.assertIn("2 characters", result.error_message)
        
        # Test too long
        result = Validator.validate_search_query("a" * 101)
        self.assertFalse(result.is_valid)
        self.assertIn("100 characters", result.error_message)
    
    def test_validate_language_code_success(self):
        """Test successful language code validation."""
        result = Validator.validate_language_code("en")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "en")
        
        # Test uppercase input
        result = Validator.validate_language_code("EN")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "en")
    
    def test_validate_language_code_invalid(self):
        """Test invalid language code validation."""
        result = Validator.validate_language_code("xyz")
        self.assertFalse(result.is_valid)
        self.assertIn("Unsupported language", result.error_message)

class TestValidationHelpers(unittest.TestCase):
    """Test cases for validation helper functions."""
    
    def test_validate_required_fields_success(self):
        """Test successful required fields validation."""
        data = {
            'name': 'Test Product',
            'price': 25.99,
            'description': 'A test product'
        }
        required_fields = ['name', 'price', 'description']
        
        result = validate_required_fields(data, required_fields)
        self.assertTrue(result.is_valid)
    
    def test_validate_required_fields_missing(self):
        """Test required fields validation with missing fields."""
        data = {
            'name': 'Test Product',
            'price': 25.99
            # Missing 'description'
        }
        required_fields = ['name', 'price', 'description']
        
        result = validate_required_fields(data, required_fields)
        self.assertFalse(result.is_valid)
        self.assertIn("description", result.error_message)
    
    def test_validate_required_fields_empty_values(self):
        """Test required fields validation with empty values."""
        data = {
            'name': '',  # Empty string
            'price': 25.99,
            'description': 'A test product'
        }
        required_fields = ['name', 'price', 'description']
        
        result = validate_required_fields(data, required_fields)
        self.assertFalse(result.is_valid)
        self.assertIn("name", result.error_message)

class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult class."""
    
    def test_validation_result_true(self):
        """Test ValidationResult with valid result."""
        result = ValidationResult(True, cleaned_value="test")
        self.assertTrue(result)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.cleaned_value, "test")
        self.assertEqual(result.error_message, "")
    
    def test_validation_result_false(self):
        """Test ValidationResult with invalid result."""
        result = ValidationResult(False, "Error message")
        self.assertFalse(result)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "Error message")
        self.assertIsNone(result.cleaned_value)

if __name__ == '__main__':
    unittest.main()
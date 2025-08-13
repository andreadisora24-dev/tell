"""Tests for UserService."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from services.user_service import UserService
from core.exceptions import ValidationError, DatabaseError, AuthenticationError
from repositories.user_repository import UserRepository

class TestUserService(unittest.TestCase):
    """Test cases for UserService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user_service = UserService()
        self.user_service.user_repo = Mock(spec=UserRepository)
    
    def test_create_user_success(self):
        """Test successful user creation."""
        # Mock repository response
        self.user_service.user_repo.create_user.return_value = {
            'id': 123,
            'username': 'testuser',
            'telegram_id': 456,
            'balance': Decimal('0.00'),
            'language': 'en',
            'is_banned': False,
            'created_at': '2024-01-01 12:00:00'
        }
        
        # Test user creation
        result = self.user_service.create_user(
            telegram_id=456,
            username='testuser',
            language='en'
        )
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['username'], 'testuser')
        self.assertEqual(result['telegram_id'], 456)
        self.user_service.user_repo.create_user.assert_called_once()
    
    def test_create_user_validation_error(self):
        """Test user creation with invalid data."""
        with self.assertRaises(ValidationError):
            self.user_service.create_user(
                telegram_id=None,  # Invalid telegram_id
                username='testuser',
                language='en'
            )
    
    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        # Mock repository response
        self.user_service.user_repo.get_user_by_telegram_id.return_value = {
            'id': 123,
            'username': 'testuser',
            'telegram_id': 456,
            'is_banned': False,
            'is_active': True
        }
        
        # Test authentication
        result = self.user_service.authenticate_user(456)
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['telegram_id'], 456)
        self.user_service.user_repo.get_user_by_telegram_id.assert_called_once_with(456)
    
    def test_authenticate_banned_user(self):
        """Test authentication of banned user."""
        # Mock repository response for banned user
        self.user_service.user_repo.get_user_by_telegram_id.return_value = {
            'id': 123,
            'username': 'testuser',
            'telegram_id': 456,
            'is_banned': True,
            'is_active': True
        }
        
        # Test authentication should raise error
        with self.assertRaises(AuthenticationError):
            self.user_service.authenticate_user(456)
    
    def test_update_user_balance_success(self):
        """Test successful balance update."""
        # Mock repository response
        self.user_service.user_repo.update_user_balance.return_value = True
        
        # Test balance update
        result = self.user_service.update_user_balance(
            user_id=123,
            amount=Decimal('50.00'),
            transaction_type='deposit'
        )
        
        # Assertions
        self.assertTrue(result)
        self.user_service.user_repo.update_user_balance.assert_called_once()
    
    def test_update_user_balance_insufficient_funds(self):
        """Test balance update with insufficient funds."""
        # Mock user with low balance
        self.user_service.user_repo.get_user_by_id.return_value = {
            'id': 123,
            'balance': Decimal('10.00')
        }
        
        # Test withdrawal with insufficient funds
        with self.assertRaises(ValidationError):
            self.user_service.update_user_balance(
                user_id=123,
                amount=Decimal('-50.00'),  # Withdrawal
                transaction_type='withdrawal'
            )
    
    def test_verify_captcha_success(self):
        """Test successful captcha verification."""
        # Test captcha verification
        result = self.user_service.verify_captcha(
            user_answer=15,
            correct_answer=15
        )
        
        # Assertions
        self.assertTrue(result)
    
    def test_verify_captcha_failure(self):
        """Test failed captcha verification."""
        # Test captcha verification
        result = self.user_service.verify_captcha(
            user_answer=10,
            correct_answer=15
        )
        
        # Assertions
        self.assertFalse(result)
    
    def test_get_user_stats(self):
        """Test getting user statistics."""
        # Mock repository response
        self.user_service.user_repo.get_user_by_id.return_value = {
            'id': 123,
            'username': 'testuser',
            'balance': Decimal('100.00'),
            'total_orders': 5,
            'total_spent': Decimal('250.00'),
            'created_at': '2024-01-01 12:00:00',
            'last_activity': '2024-01-15 10:30:00'
        }
        
        # Test getting user stats
        result = self.user_service.get_user_stats(123)
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result['username'], 'testuser')
        self.assertEqual(result['balance'], Decimal('100.00'))
        self.assertEqual(result['total_orders'], 5)
    
    @patch('services.user_service.logger')
    def test_database_error_handling(self, mock_logger):
        """Test database error handling."""
        # Mock repository to raise database error
        self.user_service.user_repo.get_user_by_id.side_effect = DatabaseError("Connection failed")
        
        # Test that database error is handled
        with self.assertRaises(DatabaseError):
            self.user_service.get_user_stats(123)
        
        # Verify error was logged
        mock_logger.error.assert_called()

if __name__ == '__main__':
    unittest.main()
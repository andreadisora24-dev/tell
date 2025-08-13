#!/usr/bin/env python3
"""
Integration tests for the TeleShop bot refactored architecture.
Tests the interaction between different layers of the application.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import tempfile
import os
from decimal import Decimal
from datetime import datetime

# Import the modules we want to test
from repositories.base_repository import BaseRepository, ConnectionPool
from repositories.user_repository import UserRepository
from repositories.inventory_repository import InventoryRepository
from repositories.order_repository import OrderRepository, OrderStatus
from services.user_service import UserService
from services.shop_service import ShopService
from services.order_service import OrderService
from utils.validators import Validator
from utils.helpers import generate_order_id, format_currency


class TestIntegration(unittest.TestCase):
    """Integration tests for the refactored architecture."""
    
    def setUp(self):
        """Set up test environment with temporary database."""
        # Create temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Initialize database schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute('''
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT DEFAULT 'en',
                balance DECIMAL(10,2) DEFAULT 0.00,
                is_banned BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                category TEXT,
                city TEXT,
                location TEXT,
                stock_quantity INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                status TEXT DEFAULT 'pending',
                delivery_address TEXT,
                delivery_phone TEXT,
                promo_code TEXT,
                discount_amount DECIMAL(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Mock the database path in ConnectionPool
        self.original_db_path = getattr(ConnectionPool, '_db_path', None)
        ConnectionPool._db_path = self.db_path
        
        # Initialize repositories
        self.user_repo = UserRepository()
        self.inventory_repo = InventoryRepository()
        self.order_repo = OrderRepository()
        
        # Initialize services
        self.user_service = UserService()
        self.shop_service = ShopService()
        self.order_service = OrderService()
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original database path
        if self.original_db_path:
            ConnectionPool._db_path = self.original_db_path
        
        # Close and remove temporary database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_user_creation_and_authentication_flow(self):
        """Test complete user creation and authentication flow."""
        # Test user creation
        user_data = {
            'user_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'language_code': 'en'
        }
        
        # Create user through service
        with patch('utils.helpers.generate_captcha_question') as mock_captcha:
            mock_captcha.return_value = ("5 + 3", "8")
            result = self.user_service.create_user(**user_data)
        
        self.assertTrue(result['success'])
        self.assertIn('captcha_question', result)
        
        # Verify user exists in database
        user = self.user_repo.get_user(12345)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'testuser')
        
        # Test authentication
        auth_result = self.user_service.authenticate_user(12345)
        self.assertTrue(auth_result['success'])
        self.assertFalse(auth_result['is_banned'])
    
    def test_product_management_and_shopping_flow(self):
        """Test product management and shopping functionality."""
        # Add a city first
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cities (name) VALUES ('TestCity')")
        conn.commit()
        conn.close()
        
        # Add a product through inventory repository
        product_data = {
            'name': 'Test Product',
            'description': 'A test product',
            'price': Decimal('29.99'),
            'category': 'Electronics',
            'city': 'TestCity',
            'location': 'Test Location',
            'stock_quantity': 10
        }
        
        product_id = self.inventory_repo.add_product(**product_data)
        self.assertIsNotNone(product_id)
        
        # Test getting cities through shop service
        cities = self.shop_service.get_cities()
        self.assertTrue(len(cities) > 0)
        self.assertEqual(cities[0]['name'], 'TestCity')
        
        # Test getting products
        products = self.shop_service.get_products('TestCity')
        self.assertTrue(len(products) > 0)
        self.assertEqual(products[0]['name'], 'Test Product')
        
        # Test product search
        search_results = self.shop_service.search_products('Test', 'TestCity')
        self.assertTrue(len(search_results) > 0)
        self.assertEqual(search_results[0]['name'], 'Test Product')
    
    def test_order_creation_and_processing_flow(self):
        """Test complete order creation and processing flow."""
        # Create a user first
        user_data = {
            'user_id': 12345,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'language_code': 'en'
        }
        
        # Insert user directly into database for this test
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, balance)
            VALUES (?, ?, ?, ?, ?)
        ''', (12345, 'testuser', 'Test', 'User', 100.00))
        
        # Add a city and product
        cursor.execute("INSERT INTO cities (name) VALUES ('TestCity')")
        cursor.execute('''
            INSERT INTO products (name, price, category, city, location, stock_quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Test Product', 29.99, 'Electronics', 'TestCity', 'Test Location', 10))
        
        conn.commit()
        conn.close()
        
        # Create order through service
        order_data = {
            'user_id': 12345,
            'items': [{'product_id': 1, 'quantity': 2}],
            'delivery_address': '123 Test Street',
            'delivery_phone': '+1234567890'
        }
        
        with patch('utils.helpers.generate_order_id') as mock_order_id:
            mock_order_id.return_value = 'TEST123456'
            result = self.order_service.create_order(**order_data)
        
        self.assertTrue(result['success'])
        self.assertIn('order_id', result)
        
        # Verify order exists in database
        order = self.order_repo.get_order_by_id(result['order_id'])
        self.assertIsNotNone(order)
        self.assertEqual(order['user_id'], 12345)
        self.assertEqual(order['status'], 'pending')
        
        # Test order status update
        update_result = self.order_repo.update_order_status(
            result['order_id'], OrderStatus.CONFIRMED
        )
        self.assertTrue(update_result)
        
        # Verify status was updated
        updated_order = self.order_repo.get_order_by_id(result['order_id'])
        self.assertEqual(updated_order['status'], 'confirmed')
    
    def test_validation_integration(self):
        """Test validation utilities integration."""
        # Test user ID validation
        valid_user_id = Validator.validate_user_id(12345)
        self.assertTrue(valid_user_id.is_valid)
        
        invalid_user_id = Validator.validate_user_id("invalid")
        self.assertFalse(invalid_user_id.is_valid)
        
        # Test email validation
        valid_email = Validator.validate_email("test@example.com")
        self.assertTrue(valid_email.is_valid)
        
        invalid_email = Validator.validate_email("invalid-email")
        self.assertFalse(invalid_email.is_valid)
        
        # Test phone validation
        valid_phone = Validator.validate_phone_number("+1234567890")
        self.assertTrue(valid_phone.is_valid)
        
        invalid_phone = Validator.validate_phone_number("123")
        self.assertFalse(invalid_phone.is_valid)
        
        # Test amount validation
        valid_amount = Validator.validate_amount("29.99")
        self.assertTrue(valid_amount.is_valid)
        
        invalid_amount = Validator.validate_amount("-10.00")
        self.assertFalse(invalid_amount.is_valid)
    
    def test_helper_functions_integration(self):
        """Test helper functions integration."""
        # Test order ID generation
        order_id = generate_order_id()
        self.assertIsInstance(order_id, str)
        self.assertTrue(len(order_id) > 0)
        
        # Test currency formatting
        formatted_price = format_currency(29.99)
        self.assertIn('29.99', formatted_price)
        
        # Test with Decimal
        decimal_price = format_currency(Decimal('29.99'))
        self.assertIn('29.99', decimal_price)
    
    def test_error_handling_integration(self):
        """Test error handling across different layers."""
        # Test handling of non-existent user
        auth_result = self.user_service.authenticate_user(99999)
        self.assertFalse(auth_result['success'])
        self.assertIn('error', auth_result)
        
        # Test handling of invalid product data
        invalid_product = {
            'name': '',  # Invalid empty name
            'price': -10,  # Invalid negative price
            'category': 'Test',
            'city': 'TestCity',
            'location': 'Test Location'
        }
        
        # This should fail validation
        name_validation = Validator.validate_product_name('')
        self.assertFalse(name_validation.is_valid)
        
        amount_validation = Validator.validate_amount('-10')
        self.assertFalse(amount_validation.is_valid)
    
    def test_database_connection_pooling(self):
        """Test database connection pooling functionality."""
        # Test getting multiple connections
        pool = ConnectionPool()
        
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        
        self.assertIsNotNone(conn1)
        self.assertIsNotNone(conn2)
        
        # Test that connections work
        cursor1 = conn1.cursor()
        cursor1.execute("SELECT 1")
        result = cursor1.fetchone()
        self.assertEqual(result[0], 1)
        
        # Return connections to pool
        pool.return_connection(conn1)
        pool.return_connection(conn2)
    
    def test_repository_base_functionality(self):
        """Test base repository functionality."""
        # Test execute_query method
        result = self.user_repo.execute_query(
            "SELECT COUNT(*) as count FROM users"
        )
        self.assertIsNotNone(result)
        self.assertIn('count', result[0])
        
        # Test execute_transaction method
        def transaction_func(cursor):
            cursor.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (54321, 'transaction_test')
            )
            return True
        
        success = self.user_repo.execute_transaction(transaction_func)
        self.assertTrue(success)
        
        # Verify user was created
        user = self.user_repo.get_user(54321)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'transaction_test')


if __name__ == '__main__':
    unittest.main()
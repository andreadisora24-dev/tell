import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from config import CITIES_CONFIG
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "teleshop.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.init_database()
        self._create_indexes()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            if not hasattr(self._local, 'connection') or self._local.connection is None:
                conn = sqlite3.connect(
                    self.db_path, 
                    check_same_thread=False,
                    timeout=30.0
                )
                conn.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrency
                conn.execute('PRAGMA journal_mode=WAL')
                # Optimize SQLite settings
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA cache_size=10000')
                conn.execute('PRAGMA temp_store=MEMORY')
                self._local.connection = conn
            else:
                conn = self._local.connection
            
            yield conn
        except sqlite3.Error as e:
            if conn:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
            logger.error(f"Unexpected database error: {e}")
            raise
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_inventory_id ON orders(inventory_id)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_strain_id ON inventory(strain_id)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_location_id ON inventory(location_id)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_available ON inventory(is_available)",
            "CREATE INDEX IF NOT EXISTS idx_locations_city_id ON locations(city_id)",
            "CREATE INDEX IF NOT EXISTS idx_product_strains_product_id ON product_strains(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code)",
            "CREATE INDEX IF NOT EXISTS idx_promo_codes_active ON promo_codes(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_promo_usage ON user_promo_usage(user_id, promo_code_id)"
        ]
        
        with self.get_connection() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                except sqlite3.Error as e:
                    logger.warning(f"Index creation warning: {e}")
            conn.commit()
    
    def init_database(self):
        """Initialize database with all required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance REAL DEFAULT 0.0,
                    discount INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned BOOLEAN DEFAULT FALSE,
                    total_orders INTEGER DEFAULT 0,
                    total_spent REAL DEFAULT 0.0
                )
            """)
            
            # Cities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Product categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    emoji TEXT DEFAULT '📦',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    base_price REAL NOT NULL,
                    emoji TEXT DEFAULT '🌿',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES product_categories (id)
                )
            """)
            
            # Product strains/variants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_strains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    price_modifier REAL DEFAULT 1.0,
                    thc_content TEXT,
                    cbd_content TEXT,
                    effects TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            """)
            
            # Locations/Provinces table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (city_id) REFERENCES cities (id),
                    UNIQUE(city_id, name)
                )
            """)
            
            # Inventory table (specific items available for purchase)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strain_id INTEGER,
                    location_id INTEGER,
                    coordinates TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT DEFAULT 'g',
                    banner_image TEXT,
                    download_image TEXT,
                    description TEXT,
                    is_available BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strain_id) REFERENCES product_strains (id),
                    FOREIGN KEY (location_id) REFERENCES locations (id)
                )
            """)
            
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    inventory_id INTEGER,
                    quantity REAL NOT NULL,
                    total_price REAL NOT NULL,
                    discount_applied REAL DEFAULT 0.0,
                    promo_code TEXT,
                    status TEXT DEFAULT 'pending',
                    coordinates TEXT,
                    payment_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (inventory_id) REFERENCES inventory (id)
                )
            """)
            
            # Promo codes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    value REAL NOT NULL,
                    type TEXT DEFAULT 'balance',
                    max_uses INTEGER DEFAULT 1,
                    current_uses INTEGER DEFAULT 0,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (user_id)
                )
            """)
            
            # Discounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    percentage REAL NOT NULL,
                    category_id INTEGER,
                    product_id INTEGER,
                    min_order_amount REAL DEFAULT 0.0,
                    max_discount_amount REAL,
                    starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES product_categories (id),
                    FOREIGN KEY (product_id) REFERENCES products (id),
                    FOREIGN KEY (created_by) REFERENCES users (user_id)
                )
            """)
            
            # User sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    session_data TEXT,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT CURRENT_DATE,
                    total_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    total_orders INTEGER DEFAULT 0,
                    total_revenue REAL DEFAULT 0.0,
                    avg_order_value REAL DEFAULT 0.0,
                    top_product_id INTEGER,
                    top_location_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (top_product_id) REFERENCES products (id),
                    FOREIGN KEY (top_location_id) REFERENCES locations (id)
                )
            """)
            
            # User promo usage table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_promo_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    promo_code_id INTEGER NOT NULL,
                    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes (id),
                    UNIQUE(user_id, promo_code_id)
                )
            """)
            
            # Balance logs table for admin balance additions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (admin_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
            
            # Insert default data (cities and locations)
            self._insert_default_data(cursor)
            conn.commit()
            
            # Clean up any duplicate locations that might exist
            self.cleanup_duplicate_locations()
    
    def _insert_default_data(self, cursor):
        """Insert default cities and locations from config"""
        # Insert cities from CITIES_CONFIG
        for city_name, city_data in CITIES_CONFIG.items():
            cursor.execute("""
                INSERT OR IGNORE INTO cities (name, is_active) 
                VALUES (?, ?)
            """, (city_name, True))
            
            # Get the city ID for inserting locations
            cursor.execute("SELECT id FROM cities WHERE name = ?", (city_name,))
            city_result = cursor.fetchone()
            if city_result:
                city_id = city_result[0]
                
                # Insert locations for this city
                for location in city_data['locations']:
                    cursor.execute("""
                        INSERT OR IGNORE INTO locations (city_id, name, description) 
                        VALUES (?, ?, ?)
                    """, (city_id, location['name'], location['description']))

    def create_user(self, user_id: int, username: str) -> bool:
        """Create a new user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, username) 
                    VALUES (?, ?)
                """, (user_id, username))
                conn.commit()
                logger.info(f"Created new user: {user_id} ({username})")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_id} already exists")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, balance, discount, language, total_orders, total_spent, 
                       is_banned, created_at, last_active 
                FROM users WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_user_balance(self, user_id: int, amount: float) -> bool:
        """Update user balance"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET balance = balance + ?, last_active = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (amount, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user balance: {e}")
            return False
    
    def get_cities(self) -> List[Dict]:
        """Get all active cities"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, is_active FROM cities WHERE is_active = TRUE ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_locations_admin(self) -> List[Dict]:
        """Get all locations (including inactive) for admin management"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.name, l.description, l.city_id, l.is_active,
                       c.name as city_name
                FROM locations l
                JOIN cities c ON l.city_id = c.id
                ORDER BY c.name, l.name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_location(self, name: str, description: str, city_id: int) -> bool:
        """Add a new location"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO locations (name, description, city_id, is_active) 
                    VALUES (?, ?, ?, TRUE)
                """, (name, description, city_id))
                conn.commit()
                logger.info(f"Location {name} added to city {city_id}")
                return True
        except Exception as e:
            logger.error(f"Error adding location {name}: {e}")
            return False
    
    def update_location_status(self, location_id: int, is_active: bool) -> bool:
        """Update location active status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE locations SET is_active = ? WHERE id = ?
                """, (is_active, location_id))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    status = "activated" if is_active else "deactivated"
                    logger.info(f"Location ID {location_id} {status}")
                return success
        except Exception as e:
            logger.error(f"Error updating location {location_id} status: {e}")
            return False
    
    def delete_location(self, location_id: int) -> bool:
        """Delete a location (soft delete by setting is_active to False)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE locations SET is_active = FALSE WHERE id = ?
                """, (location_id,))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Location ID {location_id} deleted (deactivated)")
                return success
        except Exception as e:
            logger.error(f"Error deleting location {location_id}: {e}")
            return False
    
    def get_all_cities_admin(self) -> List[Dict]:
        """Get all cities (including inactive) for admin management"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cities ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def add_city(self, name: str) -> bool:
        """Add a new city"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cities (name, is_active) VALUES (?, TRUE)
                """, (name,))
                conn.commit()
                logger.info(f"City {name} added successfully")
                return True
        except Exception as e:
            logger.error(f"Error adding city {name}: {e}")
            return False
    
    def update_city_status(self, city_id: int, is_active: bool) -> bool:
        """Update city active status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE cities SET is_active = ? WHERE id = ?
                """, (is_active, city_id))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    status = "activated" if is_active else "deactivated"
                    logger.info(f"City ID {city_id} {status}")
                return success
        except Exception as e:
            logger.error(f"Error updating city {city_id} status: {e}")
            return False
    
    def delete_city(self, city_id: int) -> bool:
        """Delete a city (soft delete by setting is_active to False)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Check if city has locations
                cursor.execute("SELECT COUNT(*) FROM locations WHERE city_id = ?", (city_id,))
                location_count = cursor.fetchone()[0]
                
                if location_count > 0:
                    # Soft delete - deactivate city and its locations
                    cursor.execute("UPDATE cities SET is_active = FALSE WHERE id = ?", (city_id,))
                    cursor.execute("UPDATE locations SET is_active = FALSE WHERE city_id = ?", (city_id,))
                else:
                    # Hard delete if no locations
                    cursor.execute("DELETE FROM cities WHERE id = ?", (city_id,))
                
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"City ID {city_id} deleted")
                return success
        except Exception as e:
            logger.error(f"Error deleting city {city_id}: {e}")
            return False
    
    def get_products_by_city(self, city_id: int) -> List[Dict]:
        """Get products available in a specific city"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT p.* FROM products p
                JOIN product_strains ps ON p.id = ps.product_id
                JOIN inventory i ON ps.id = i.strain_id
                JOIN locations l ON i.location_id = l.id
                WHERE l.city_id = ? AND p.is_active = TRUE AND i.is_available = TRUE
                ORDER BY p.name
            """, (city_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_product_strains(self, product_id: int, city_id: int) -> List[Dict]:
        """Get strains for a product that have inventory in a city"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT ps.* FROM product_strains ps
                JOIN inventory i ON ps.id = i.strain_id
                JOIN locations l ON i.location_id = l.id
                WHERE ps.product_id = ? AND l.city_id = ? 
                AND ps.is_active = TRUE AND i.is_available = TRUE
                ORDER BY ps.name
            """, (product_id, city_id))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_locations_for_strain(self, strain_id: int) -> List[Dict]:
        """Get locations where a strain is available (pooled by location)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.*, 
                       GROUP_CONCAT(i.id) as inventory_ids,
                       SUM(i.quantity) as total_quantity,
                       i.unit,
                       AVG(i.price) as avg_price,
                       COUNT(i.id) as item_count
                FROM locations l
                JOIN inventory i ON l.id = i.location_id
                WHERE i.strain_id = ? AND l.is_active = TRUE AND i.is_available = TRUE
                GROUP BY l.id, l.name, i.unit
                ORDER BY l.name
            """, (strain_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_quantity_options_for_strain(self, strain_id: int) -> List[Dict]:
        """Get available quantity options for a strain with calculated prices and discounts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT i.quantity, i.unit, 
                       (p.base_price * ps.price_modifier * i.quantity) as total_price,
                       COUNT(DISTINCT i.location_id) as location_count,
                       p.id as product_id, p.category_id
                FROM inventory i
                JOIN product_strains ps ON i.strain_id = ps.id
                JOIN products p ON ps.product_id = p.id
                WHERE i.strain_id = ? AND i.is_available = TRUE
                GROUP BY i.quantity, i.unit, p.id, p.category_id
                ORDER BY i.quantity
            """, (strain_id,))
            
            options = [dict(row) for row in cursor.fetchall()]
            
            # Add discount information to each option
            for option in options:
                original_price = option['total_price']
                best_discount = None
                
                # Check for category discount
                category_discount = self.get_category_discount(option['category_id'])
                if category_discount and (not best_discount or category_discount['percentage'] > best_discount['percentage']):
                    best_discount = category_discount
                    best_discount['type'] = 'category'
                
                # Check for product discount
                product_discount = self.get_product_discount(option['product_id'])
                if product_discount and (not best_discount or product_discount['percentage'] > best_discount['percentage']):
                    best_discount = product_discount
                    best_discount['type'] = 'product'
                
                # Check for global discount
                global_discount = self.get_global_discount()
                if global_discount and (not best_discount or global_discount['percentage'] > best_discount['percentage']):
                    best_discount = global_discount
                    best_discount['type'] = 'global'
                
                # Apply discount if found
                if best_discount:
                    discount_amount = original_price * (best_discount['percentage'] / 100)
                    option['discounted_price'] = original_price - discount_amount
                    option['discount_info'] = {
                        'name': best_discount['name'],
                        'percentage': best_discount['percentage'],
                        'amount': discount_amount
                    }
                else:
                    option['discounted_price'] = original_price
                    option['discount_info'] = None
            
            return options
    
    def get_locations_for_strain_quantity(self, strain_id: int, quantity: float) -> List[Dict]:
        """Get locations where a specific quantity of strain is available (pooled by location)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.*, 
                       GROUP_CONCAT(i.id) as inventory_ids,
                       SUM(i.quantity) as total_quantity,
                       i.unit,
                       AVG(i.price) as avg_price,
                       COUNT(i.id) as item_count
                FROM locations l
                JOIN inventory i ON l.id = i.location_id
                WHERE i.strain_id = ? AND l.is_active = TRUE AND i.is_available = TRUE
                GROUP BY l.id, l.name, i.unit
                HAVING SUM(i.quantity) >= ?
                ORDER BY l.name
            """, (strain_id, quantity))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_products(self) -> List[Dict]:
        """Get all active products"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM products 
                WHERE is_active = TRUE 
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def create_order(self, user_id: int, inventory_id: int, quantity: float, 
                    total_price: float, coordinates: str, payment_method: str) -> int:
        """Create a new order"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (user_id, inventory_id, quantity, total_price, 
                                  coordinates, payment_method)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, inventory_id, quantity, total_price, coordinates, payment_method))
            
            order_id = cursor.lastrowid
            
            # Update user statistics
            cursor.execute("""
                UPDATE users SET total_orders = total_orders + 1, 
                               total_spent = total_spent + ?,
                               last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (total_price, user_id))
            
            conn.commit()
            return order_id
    
    def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's order history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.*, ps.name as strain_name, p.name as product_name, 
                       l.name as location_name, c.name as city_name
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN product_strains ps ON i.strain_id = ps.id
                JOIN products p ON ps.product_id = p.id
                JOIN locations l ON i.location_id = l.id
                JOIN cities c ON l.city_id = c.id
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_categories(self) -> List[Dict]:
        """Get all product categories"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, emoji, is_active
                FROM product_categories
                WHERE is_active = TRUE
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_locations(self) -> List[Dict]:
        """Get all active locations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.name, l.description, c.name as city_name
                FROM locations l
                JOIN cities c ON l.city_id = c.id
                WHERE l.is_active = TRUE
                ORDER BY c.name, l.name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_locations_by_city(self, city_id: int) -> List[Dict]:
        """Get all active locations in a specific city"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.name, l.description, c.name as city_name
                FROM locations l
                JOIN cities c ON l.city_id = c.id
                WHERE l.is_active = TRUE AND l.city_id = ?
                ORDER BY l.name
            """, (city_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_strains(self) -> List[Dict]:
        """Get all product strains with product names"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ps.id, ps.name, ps.description, ps.thc_content, ps.cbd_content,
                       p.name as product_name, p.id as product_id
                FROM product_strains ps
                JOIN products p ON ps.product_id = p.id
                WHERE ps.is_active = TRUE AND p.is_active = TRUE
                ORDER BY p.name, ps.name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_strain_with_price(self, strain_id: int) -> Optional[Dict]:
        """Get strain details with calculated price from product base_price and strain price_modifier"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ps.*, p.base_price, p.name as product_name,
                       (p.base_price * ps.price_modifier) as calculated_price
                FROM product_strains ps
                JOIN products p ON ps.product_id = p.id
                WHERE ps.id = ? AND ps.is_active = TRUE AND p.is_active = TRUE
            """, (strain_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_active_promo_codes(self) -> List[Dict]:
        """Get all active promo codes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT code, value, type, max_uses, current_uses, created_at, expires_at
                FROM promo_codes
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_promo_code_info(self, promo_code: str) -> Optional[Dict]:
        """Get promo code information without redeeming it"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, code, value, type, max_uses, current_uses, expires_at, is_active
                    FROM promo_codes 
                    WHERE code = ? AND is_active = TRUE AND 
                    (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (promo_code,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting promo code info: {e}")
            return None
    
    def add_inventory_item(self, strain_id: int, location_id: int, coordinates: str,
                          quantity: float, unit: str = 'g',
                          banner_image: str = None, download_image: str = None,
                          description: str = None) -> int:
        """Add new inventory item - price is calculated from product base_price and strain price_modifier"""
        # Get strain details with calculated price
        strain_data = self.get_strain_with_price(strain_id)
        if not strain_data:
            logger.error(f"Strain {strain_id} not found or inactive")
            return 0
        
        calculated_price = strain_data['calculated_price']
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inventory (strain_id, location_id, coordinates, price, 
                                     quantity, unit, banner_image, download_image, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (strain_id, location_id, coordinates, calculated_price, quantity, unit,
                  banner_image, download_image, description))
            conn.commit()
            return cursor.lastrowid
    
    def create_promo_code(self, code: str, value: float, code_type: str = 'balance',
                         max_uses: int = 1, expires_at: str = None, created_by: int = None) -> bool:
        """Create a new promo code"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO promo_codes (code, value, type, max_uses, expires_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code, value, code_type, max_uses, expires_at, created_by))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def get_location_details(self, location_id: int) -> Optional[Dict]:
        """Get detailed location information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.name, l.description,
                       c.name as city_name
                FROM locations l
                JOIN cities c ON l.city_id = c.id
                WHERE l.id = ?
            """, (location_id,))
            
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
    
    def get_inventory_details(self, inventory_id: int) -> Optional[Dict]:
        """Get detailed inventory information with location, product, and strain details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.*, l.name as location_name, l.description as location_description,
                       c.name as city_name, p.name as product_name, p.category_id, p.id as product_id,
                       ps.name as strain_name, i.price, i.unit, i.coordinates, i.quantity
                FROM inventory i
                JOIN locations l ON i.location_id = l.id
                JOIN cities c ON l.city_id = c.id
                JOIN product_strains ps ON i.strain_id = ps.id
                JOIN products p ON ps.product_id = p.id
                WHERE i.id = ? AND i.is_available = TRUE
            """, (inventory_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def update_inventory_availability(self, inventory_id: int, is_available: bool) -> bool:
        """Update inventory item availability status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE inventory SET is_available = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (is_available, inventory_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating inventory availability: {e}")
            return False
    
    def update_inventory_quantity(self, inventory_id: int, quantity_sold: float) -> bool:
        """Update inventory quantity by reducing the sold amount"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE inventory SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ? AND quantity >= ?
                """, (quantity_sold, inventory_id, quantity_sold))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating inventory quantity: {e}")
            return False
     
    def get_order_details(self, order_id: int) -> Optional[Dict]:
        """Get detailed order information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.*, l.name as location_name, l.description as location_description,
                       c.name as city_name, p.name as product_name, 
                       ps.name as strain_name, i.price, i.unit, i.coordinates,
                       i.banner_image, i.download_image
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN locations l ON i.location_id = l.id
                JOIN cities c ON l.city_id = c.id
                JOIN product_strains ps ON i.strain_id = ps.id
                JOIN products p ON ps.product_id = p.id
                WHERE o.id = ?
            """, (order_id,))
            
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
    

    
    def get_detailed_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # User statistics
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            stats['total_users'] = cursor.fetchone()['total_users']
            
            cursor.execute("""
                SELECT COUNT(*) as new_users_today FROM users 
                WHERE DATE(created_at) = DATE('now')
            """)
            stats['new_users_today'] = cursor.fetchone()['new_users_today']
            
            # Order statistics
            cursor.execute("SELECT COUNT(*) as total_orders, SUM(total_price) as total_revenue FROM orders")
            order_stats = cursor.fetchone()
            stats['total_orders'] = order_stats['total_orders']
            stats['total_revenue'] = order_stats['total_revenue'] or 0.0
            
            cursor.execute("""
                SELECT COUNT(*) as orders_today, SUM(total_price) as revenue_today 
                FROM orders WHERE DATE(created_at) = DATE('now')
            """)
            today_stats = cursor.fetchone()
            stats['orders_today'] = today_stats['orders_today']
            stats['revenue_today'] = today_stats['revenue_today'] or 0.0
            
            # Average order value
            if stats['total_orders'] > 0:
                stats['avg_order_value'] = stats['total_revenue'] / stats['total_orders']
            else:
                stats['avg_order_value'] = 0.0
            
            # Additional statistics
            cursor.execute("SELECT COUNT(*) as active_promos FROM promo_codes WHERE is_active = TRUE")
            stats['active_promos'] = cursor.fetchone()['active_promos']
            
            cursor.execute("SELECT COUNT(*) as total_locations FROM locations")
            stats['total_locations'] = cursor.fetchone()['total_locations']
            
            cursor.execute("SELECT COUNT(*) as total_cities FROM cities")
            stats['total_cities'] = cursor.fetchone()['total_cities']
            
            cursor.execute("SELECT COUNT(*) as total_products FROM products")
            stats['total_products'] = cursor.fetchone()['total_products']
            
            # Most popular product
            cursor.execute("""
                SELECT p.name, COUNT(*) as order_count
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN product_strains ps ON i.strain_id = ps.id
                JOIN products p ON ps.product_id = p.id
                GROUP BY p.id, p.name
                ORDER BY order_count DESC
                LIMIT 1
            """)
            popular_result = cursor.fetchone()
            stats['popular_product'] = popular_result['name'] if popular_result else 'N/A'
            
            # Top city
            cursor.execute("""
                SELECT c.name, COUNT(*) as order_count
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN locations l ON i.location_id = l.id
                JOIN cities c ON l.city_id = c.id
                GROUP BY c.id, c.name
                ORDER BY order_count DESC
                LIMIT 1
            """)
            city_result = cursor.fetchone()
            stats['top_city'] = city_result['name'] if city_result else 'N/A'
            
            # Top products
            cursor.execute("""
                SELECT p.name, COUNT(o.id) as order_count, SUM(o.total_price) as revenue
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN product_strains ps ON i.strain_id = ps.id
                JOIN products p ON ps.product_id = p.id
                GROUP BY p.id, p.name
                ORDER BY order_count DESC
                LIMIT 5
            """)
            stats['top_products'] = [dict(row) for row in cursor.fetchall()]
            
            # Top locations
            cursor.execute("""
                SELECT l.name, c.name as city, COUNT(o.id) as order_count
                FROM orders o
                JOIN inventory i ON o.inventory_id = i.id
                JOIN locations l ON i.location_id = l.id
                JOIN cities c ON l.city_id = c.id
                GROUP BY l.id, l.name, c.name
                ORDER BY order_count DESC
                LIMIT 5
            """)
            stats['top_locations'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def redeem_promo_code(self, user_id: int, promo_code: str, lang: str = 'en') -> Dict:
        """Redeem a promo code for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if promo code exists and is active
                cursor.execute("""
                    SELECT * FROM promo_codes 
                    WHERE code = ? AND is_active = TRUE AND 
                    (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (promo_code,))
                
                promo = cursor.fetchone()
                if not promo:
                    from translations import get_text
                    return {'success': False, 'error': get_text('promo_error_default', lang)}
                
                # Check if user already used this promo code
                cursor.execute("""
                    SELECT COUNT(*) as count FROM user_promo_usage 
                    WHERE user_id = ? AND promo_code_id = ?
                """, (user_id, promo['id']))
                
                if cursor.fetchone()['count'] > 0:
                    from translations import get_text
                    return {'success': False, 'error': get_text('promo_already_used', lang)}
                
                # Check usage limit
                if promo['max_uses'] and promo['current_uses'] >= promo['max_uses']:
                    return {'success': False, 'error': 'Promo code usage limit reached'}
                
                # Redeem the promo code
                cursor.execute("""
                    INSERT INTO user_promo_usage (user_id, promo_code_id, redeemed_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, promo['id']))
                
                # Update promo code usage count
                cursor.execute("""
                    UPDATE promo_codes SET current_uses = current_uses + 1 
                    WHERE id = ?
                """, (promo['id'],))
                
                conn.commit()
                
                return {
                    'success': True, 
                    'amount': promo['value'],
                    'code': promo_code
                }
                
        except Exception as e:
            logger.error(f"Error redeeming promo code: {e}")
            return {'success': False, 'error': 'Database error'}
    
    def set_user_balance(self, user_id: int, new_balance: float) -> bool:
        """Set user's balance to a specific value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET balance = ?, last_active = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (new_balance, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting user balance: {e}")
            return False
    
    def update_user_language(self, user_id: int, language: str) -> bool:
        """Update user's language preference"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET language = ?, last_active = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (language, user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user language: {e}")
            return False
    
    def create_category(self, name: str, description: str = None, emoji: str = '📦') -> int:
        """Create a new product category"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO product_categories (name, description, emoji)
                    VALUES (?, ?, ?)
                """, (name, description, emoji))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return 0
    
    def get_category(self, category_id: int) -> Optional[Dict]:
        """Get a single category by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, description, emoji, is_active
                    FROM product_categories
                    WHERE id = ? AND is_active = TRUE
                """, (category_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting category: {e}")
            return None
    
    def create_product(self, category_id: int, name: str, description: str = None, 
                      base_price: float = 0.0, emoji: str = '🌿') -> int:
        """Create a new product"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO products (category_id, name, description, base_price, emoji)
                    VALUES (?, ?, ?, ?, ?)
                """, (category_id, name, description, base_price, emoji))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            return 0
    
    def create_product_strain(self, product_id: int, name: str, description: str = None,
                             thc_content: float = 0.0, cbd_content: float = 0.0, 
                             effects: str = None) -> int:
        """Create a new product strain"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO product_strains (product_id, name, description, thc_content, cbd_content, effects)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (product_id, name, description, thc_content, cbd_content, effects))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating product strain: {e}")
            return 0
    
    def check_user_purchase(self, user_id: int, inventory_id: int) -> bool:
        """Check if user has purchased a specific inventory item"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE user_id = ? AND inventory_id = ?
            """, (user_id, inventory_id))
            count = cursor.fetchone()[0]
            return count > 0
    
    def create_discount(self, name: str, percentage: float, category_id: int = None, 
                      product_id: int = None, min_order_amount: float = 0.0, 
                      max_discount_amount: float = None, expires_at: str = None, 
                      created_by: int = None) -> int:
        """Create a new discount"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO discounts (name, percentage, category_id, product_id, 
                                         min_order_amount, max_discount_amount, expires_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, percentage, category_id, product_id, min_order_amount, 
                      max_discount_amount, expires_at, created_by))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating discount: {e}")
            return 0
    
    def get_all_discounts(self) -> List[Dict]:
        """Get all active discounts"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT d.*, pc.name as category_name, p.name as product_name
                    FROM discounts d
                    LEFT JOIN product_categories pc ON d.category_id = pc.id
                    LEFT JOIN products p ON d.product_id = p.id
                    WHERE d.is_active = TRUE
                    ORDER BY d.created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting discounts: {e}")
            return []
    
    def get_discount_by_id(self, discount_id: int) -> Optional[Dict]:
        """Get discount by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT d.*, pc.name as category_name, p.name as product_name
                    FROM discounts d
                    LEFT JOIN product_categories pc ON d.category_id = pc.id
                    LEFT JOIN products p ON d.product_id = p.id
                    WHERE d.id = ? AND d.is_active = TRUE
                """, (discount_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting discount by ID: {e}")
            return None
    
    def update_discount_status(self, discount_id: int, is_active: bool) -> bool:
        """Update discount active status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE discounts SET is_active = ? WHERE id = ?
                """, (is_active, discount_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating discount status: {e}")
            return False
    
    def delete_discount(self, discount_id: int) -> bool:
        """Delete a discount (soft delete by setting is_active to False)"""
        return self.update_discount_status(discount_id, False)
    
    def get_category_discount(self, category_id: int) -> Optional[Dict]:
        """Get active discount for a specific category"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM discounts 
                    WHERE category_id = ? AND is_active = TRUE 
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY percentage DESC
                    LIMIT 1
                """, (category_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting category discount: {e}")
            return None
    
    def get_product_discount(self, product_id: int) -> Optional[Dict]:
        """Get active discount for a specific product"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM discounts 
                    WHERE product_id = ? AND is_active = TRUE 
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY percentage DESC
                    LIMIT 1
                """, (product_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting product discount: {e}")
            return None
    
    def get_global_discount(self) -> Optional[Dict]:
        """Get active global discount"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM discounts 
                    WHERE category_id IS NULL AND product_id IS NULL AND is_active = TRUE 
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY percentage DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting global discount: {e}")
            return None
    
    def get_products_by_category_and_city(self, category_id: int, city_id: int) -> List[Dict]:
        """Get products by category that are available in a specific city"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT p.* FROM products p
                JOIN product_strains ps ON p.id = ps.product_id
                JOIN inventory i ON ps.id = i.strain_id
                JOIN locations l ON i.location_id = l.id
                WHERE p.category_id = ? AND l.city_id = ? 
                AND p.is_active = TRUE AND i.is_available = TRUE
                ORDER BY p.name
            """, (category_id, city_id))
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_duplicate_locations(self):
        """Remove duplicate locations keeping only the first occurrence"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find and delete duplicate locations
                cursor.execute("""
                    DELETE FROM locations 
                    WHERE id NOT IN (
                        SELECT MIN(id) 
                        FROM locations 
                        GROUP BY city_id, name
                    )
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} duplicate locations")
                
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up duplicate locations: {e}")
            return 0
    
    # User Management Functions
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all users with pagination"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, balance, discount, language, 
                       created_at, last_active, is_banned, total_orders, total_spent
                FROM users 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def search_users(self, query: str, limit: int = 50) -> List[Dict]:
        """Search users by username or user_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Try to search by user_id if query is numeric
            if query.isdigit():
                cursor.execute("""
                    SELECT user_id, username, balance, discount, language, 
                           created_at, last_active, is_banned, total_orders, total_spent
                    FROM users 
                    WHERE user_id = ? OR username LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (int(query), f"%{query}%", limit))
            else:
                cursor.execute("""
                    SELECT user_id, username, balance, discount, language, 
                           created_at, last_active, is_banned, total_orders, total_spent
                    FROM users 
                    WHERE username LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (f"%{query}%", limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET is_banned = TRUE, last_active = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"User {user_id} has been banned")
                return success
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}")
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET is_banned = FALSE, last_active = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"User {user_id} has been unbanned")
                return success
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}")
            return False
    
    def is_user_banned(self, user_id: int) -> bool:
        """Check if a user is banned"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return bool(row['is_banned']) if row else False
    
    def get_user_statistics(self) -> Dict:
        """Get comprehensive user statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total users
            cursor.execute("SELECT COUNT(*) as total FROM users")
            stats['total_users'] = cursor.fetchone()['total']
            
            # Active users (last 30 days)
            cursor.execute("""
                SELECT COUNT(*) as active FROM users 
                WHERE last_active >= datetime('now', '-30 days')
            """)
            stats['active_users'] = cursor.fetchone()['active']
            
            # Banned users
            cursor.execute("SELECT COUNT(*) as banned FROM users WHERE is_banned = TRUE")
            stats['banned_users'] = cursor.fetchone()['banned']
            
            # New users (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) as new_users FROM users 
                WHERE created_at >= datetime('now', '-7 days')
            """)
            stats['new_users'] = cursor.fetchone()['new_users']
            
            # Total balance across all users
            cursor.execute("SELECT SUM(balance) as total_balance FROM users")
            stats['total_balance'] = cursor.fetchone()['total_balance'] or 0.0
            
            # Average balance
            cursor.execute("SELECT AVG(balance) as avg_balance FROM users WHERE balance > 0")
            stats['average_balance'] = cursor.fetchone()['avg_balance'] or 0.0
            
            # Total orders
            cursor.execute("SELECT SUM(total_orders) as total_orders FROM users")
            stats['total_orders'] = cursor.fetchone()['total_orders'] or 0
            
            # Total spent
            cursor.execute("SELECT SUM(total_spent) as total_spent FROM users")
            stats['total_spent'] = cursor.fetchone()['total_spent'] or 0.0
            
            # Top users by orders
            cursor.execute("""
                SELECT user_id, username, total_orders, total_spent 
                FROM users 
                WHERE total_orders > 0 
                ORDER BY total_orders DESC 
                LIMIT 10
            """)
            stats['top_users_by_orders'] = [dict(row) for row in cursor.fetchall()]
            
            # Top users by spending
            cursor.execute("""
                SELECT user_id, username, total_orders, total_spent 
                FROM users 
                WHERE total_spent > 0 
                ORDER BY total_spent DESC 
                LIMIT 10
            """)
            stats['top_users_by_spending'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
    
    def add_balance_to_user(self, user_id: int, amount: float, admin_id: int) -> bool:
        """Add balance to a user (admin function)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update user balance
                cursor.execute("""
                    UPDATE users SET balance = balance + ?, last_active = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (amount, user_id))
                
                # Log the balance addition (you might want to create a balance_log table)
                cursor.execute("""
                    INSERT INTO balance_logs (user_id, amount, admin_id, action, created_at)
                    VALUES (?, ?, ?, 'admin_add', CURRENT_TIMESTAMP)
                """, (user_id, amount, admin_id))
                
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Admin {admin_id} added {amount} balance to user {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error adding balance to user {user_id}: {e}")
            return False
    
    def clean_old_data(self, days_old: int = 90) -> Dict[str, int]:
        """Clean old data from database (older than specified days)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cleaned_counts = {}
                
                # Clean old completed orders (older than days_old)
                cursor.execute("""
                    DELETE FROM orders 
                    WHERE completed_at IS NOT NULL 
                    AND completed_at < datetime('now', '-{} days')
                """.format(days_old))
                cleaned_counts['old_orders'] = cursor.rowcount
                
                # Clean old user sessions (older than 30 days)
                cursor.execute("""
                    DELETE FROM user_sessions 
                    WHERE last_activity < datetime('now', '-30 days')
                """)
                cleaned_counts['old_sessions'] = cursor.rowcount
                
                # Clean old balance logs (older than days_old)
                cursor.execute("""
                    DELETE FROM balance_logs 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))
                cleaned_counts['old_balance_logs'] = cursor.rowcount
                
                # Clean expired promo codes
                cursor.execute("""
                    DELETE FROM promo_codes 
                    WHERE is_active = FALSE 
                    AND created_at < datetime('now', '-{} days')
                """.format(days_old))
                cleaned_counts['expired_promos'] = cursor.rowcount
                
                # Clean old promo usage records for deleted promos
                cursor.execute("""
                    DELETE FROM user_promo_usage 
                    WHERE promo_code_id NOT IN (SELECT id FROM promo_codes)
                """)
                cleaned_counts['orphaned_promo_usage'] = cursor.rowcount
                
                conn.commit()
                
                total_cleaned = sum(cleaned_counts.values())
                logger.info(f"Cleaned {total_cleaned} old records from database")
                
                return cleaned_counts
                
        except Exception as e:
            logger.error(f"Error cleaning old data: {e}")
            return {}
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create a backup of the database"""
        import shutil
        import os
        from datetime import datetime
        
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"teleshop_backup_{timestamp}.db"
            
            # Create backup using shutil.copy2 to preserve metadata
            shutil.copy2(self.db_path, backup_path)
            
            # Verify backup was created and has content
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                logger.info(f"Database backup created successfully: {backup_path}")
                return backup_path
            else:
                raise Exception("Backup file was not created properly")
                
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            raise e
    
    def reset_test_data(self) -> Dict[str, int]:
        """Reset/clear test data from database (for development/testing purposes)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                reset_counts = {}
                
                # Clear all orders
                cursor.execute("DELETE FROM orders")
                reset_counts['orders'] = cursor.rowcount
                
                # Clear user sessions
                cursor.execute("DELETE FROM user_sessions")
                reset_counts['sessions'] = cursor.rowcount
                
                # Clear balance logs
                cursor.execute("DELETE FROM balance_logs")
                reset_counts['balance_logs'] = cursor.rowcount
                
                # Clear promo usage
                cursor.execute("DELETE FROM user_promo_usage")
                reset_counts['promo_usage'] = cursor.rowcount
                
                # Clear inactive promo codes
                cursor.execute("DELETE FROM promo_codes WHERE is_active = FALSE")
                reset_counts['inactive_promos'] = cursor.rowcount
                
                # Reset user statistics (but keep users)
                cursor.execute("""
                    UPDATE users SET 
                    total_orders = 0, 
                    total_spent = 0.0,
                    balance = 0.0,
                    discount = 0.0
                    WHERE user_id NOT IN (SELECT user_id FROM users WHERE user_id IN (SELECT admin_id FROM users LIMIT 1))
                """)
                reset_counts['user_stats_reset'] = cursor.rowcount
                
                # Clear discounts
                cursor.execute("DELETE FROM discounts WHERE is_active = TRUE")
                reset_counts['discounts'] = cursor.rowcount
                
                conn.commit()
                
                total_reset = sum(reset_counts.values())
                logger.info(f"Reset {total_reset} test data records")
                
                return reset_counts
                
        except Exception as e:
            logger.error(f"Error resetting test data: {e}")
            return {}
    
    def delete_promo_code(self, promo_code: str) -> bool:
        """Delete a promo code (soft delete by setting is_active to False)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE promo_codes SET is_active = FALSE 
                    WHERE code = ? AND is_active = TRUE
                """, (promo_code,))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Promo code {promo_code} deleted (deactivated)")
                return success
        except Exception as e:
            logger.error(f"Error deleting promo code {promo_code}: {e}")
            return False
    
    def get_promo_code_by_id(self, promo_id: int) -> Optional[Dict]:
        """Get promo code by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, code, value, type, max_uses, current_uses, 
                           expires_at, is_active, created_at
                    FROM promo_codes 
                    WHERE id = ?
                """, (promo_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting promo code by ID {promo_id}: {e}")
            return None
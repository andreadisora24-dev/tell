import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '')  # Get from environment variables

# Admin Configuration
ADMIN_IDS = [
    int(admin_id) for admin_id in os.getenv('ADMIN_IDS', '').split(',') if admin_id.strip()
]
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')  # Admin username for contact purposes

# Multi-Admin System with Working Hours
ADMINS_WITH_HOURS = [
    {
        'id': int(os.getenv('PRIMARY_ADMIN_ID', '0')),
        'username': os.getenv('ADMIN_USERNAME', 'admin'),
        'name': 'Primary Admin',
        'start_hour': 9,
        'end_hour': 17,
        'timezone': 'Europe/Warsaw'
    }
]

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'teleshop.db')

# Security Configuration
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())  # Generate secure random key if not provided
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))  # Session timeout in seconds (1 hour)

# Payment Configuration
BTC_WALLET_ADDRESS = os.getenv('BTC_WALLET_ADDRESS', '')  # Get from environment variables
MIN_ORDER_AMOUNT = float(os.getenv('MIN_ORDER_AMOUNT', '10.0'))  # Minimum order amount in PLN
MAX_ORDER_AMOUNT = float(os.getenv('MAX_ORDER_AMOUNT', '1000.0'))  # Maximum order amount in PLN

# File Upload Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# Rate Limiting (optimized for better performance)
MAX_REQUESTS_PER_MINUTE = 60  # Increased from 30
MAX_REQUESTS_PER_HOUR = 200   # Added for better control
COOLDOWN_PERIOD = 30          # Added cooldown period
MAX_CAPTCHA_ATTEMPTS = 5      # Increased from 3

# Auto-cleanup Configuration
AUTO_CLEANUP_TIMEOUT = 60    # 1 minute in seconds
WELCOME_CLEANUP_ENABLED = True # Enable auto-cleanup feature

# Rate Limiting Configuration
RATE_LIMIT_MESSAGES = int(os.getenv('RATE_LIMIT_MESSAGES', '60'))  # Messages per window
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))      # Window in seconds

# Logging Configuration (optimized)
LOG_LEVEL = "WARNING"  # Reduced from INFO to WARNING for better performance
LOG_FILE = "teleshop.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_LOG_FILE_SIZE = 5 * 1024 * 1024  # 5MB max file size
LOG_BACKUP_COUNT = 3  # Keep last 3 log files

# Default Settings
DEFAULT_LANGUAGE = "en"
DEFAULT_CURRENCY = "PLN"
ORDER_HISTORY_LIMIT = 10

# Geolocation Configuration
GDANSK_BOUNDS = {
    'min_lat': 54.2,
    'max_lat': 54.5,
    'min_lon': 18.4,
    'max_lon': 18.8
}
WARSAW_BOUNDS = {
            'min_lat': 52.1,
            'max_lat': 52.4,
            'min_lon': 20.8,
            'max_lon': 21.2
        }
# Cities and Locations Configuration
# Easy to modify - just add/remove cities and their locations here
CITIES_CONFIG = {
    'Gdansk': {
        'bounds': GDANSK_BOUNDS,
        'locations': [
            {'name': 'Stare Miasto', 'description': 'Historic Old Town district'},
            {'name': 'Wrzeszcz', 'description': 'University and shopping district'},
            {'name': 'Oliwa', 'description': 'Peaceful residential area with cathedral'},
            {'name': 'Zaspa', 'description': 'Large residential district'},
            {'name': 'Morena', 'description': 'Modern residential area'}
        ]
    },
    'Warsaw': {
        'bounds': WARSAW_BOUNDS,
        'locations': [
            {'name': 'Śródmieście', 'description': 'City center and business district'},
            {'name': 'Praga', 'description': 'Artistic and cultural district'},
            {'name': 'Mokotów', 'description': 'Upscale residential area'},
            {'name': 'Żoliborz', 'description': 'Green residential district'}
        ]
    },
    'Krakow': {
        'bounds': {
            'min_lat': 50.0,
            'max_lat': 50.1,
            'min_lon': 19.8,
            'max_lon': 20.1
        },
        'locations': [
            {'name': 'Stare Miasto', 'description': 'UNESCO World Heritage old town'},
            {'name': 'Kazimierz', 'description': 'Historic Jewish quarter'},
            {'name': 'Podgórze', 'description': 'Trendy district across the river'},
            {'name': 'Nowa Huta', 'description': 'Socialist realist planned district'}
        ]
    }
}

# Promo Code Settings
PROMO_CODE_LENGTH = 8
MAX_PROMO_USES = 100

# Discount Settings
MAX_DISCOUNT_PERCENTAGE = 50
MIN_DISCOUNT_PERCENTAGE = 5

# Inventory Settings
MIN_STOCK_ALERT = 5  # Alert when stock is below this amount
DEFAULT_UNIT = "g"  # Default unit for products

# Captcha Settings (optimized)
CAPTCHA_TIMEOUT = 600  # Increased to 10 minutes to reduce regeneration
CAPTCHA_IMAGE_SIZE = (150, 150)  # Reduced size for faster generation
CAPTCHA_LENGTH = 5  # Reduced from default 6 for faster generation
CAPTCHA_MAX_ATTEMPTS = 3  # Increased to reduce user frustration

# Backup Settings
AUTO_BACKUP_ENABLED = True
BACKUP_INTERVAL_HOURS = 1
MAX_BACKUP_FILES = 7  # Keep last 7 backups
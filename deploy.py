#!/usr/bin/env python3
"""
Deployment script for TeleShop Bot.
Handles database initialization, dependency checks, and application startup.
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'python-telegram-bot',
        'python-dotenv',
        'cryptography'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        install = input("Install missing packages? (y/n): ").lower().strip()
        
        if install == 'y':
            try:
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install'
                ] + missing_packages)
                print("✅ Dependencies installed successfully!")
                return True
            except subprocess.CalledProcessError:
                print("❌ Failed to install dependencies.")
                return False
        else:
            return False
    
    return True


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\n🔧 Checking environment configuration...")
    
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found.")
        create_env = input("Create .env file template? (y/n): ").lower().strip()
        
        if create_env == 'y':
            create_env_template()
            print("✅ .env template created. Please edit it with your values.")
            return False
        else:
            return False
    
    # Check required environment variables
    required_vars = ['BOT_TOKEN', 'ADMIN_USER_IDS']
    missing_vars = []
    
    with open('.env', 'r') as f:
        env_content = f.read()
        
        for var in required_vars:
            if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Please configure these variables in .env: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment configuration looks good!")
    return True


def create_env_template():
    """Create a template .env file."""
    template = """# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321

# Database Configuration
DATABASE_PATH=teleshop.db

# Logging Configuration
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Session Management
SESSION_TIMEOUT=3600

# Optional: Webhook Configuration (for production)
# WEBHOOK_URL=https://yourdomain.com/webhook
# WEBHOOK_PORT=8443
"""
    
    with open('.env', 'w') as f:
        f.write(template)


def initialize_database():
    """Initialize the database if it doesn't exist."""
    print("\n🗄️  Checking database...")
    
    db_path = os.getenv('DATABASE_PATH', 'teleshop.db')
    
    if not os.path.exists(db_path):
        print("Creating database...")
        try:
            # Import and run database initialization
            import database
            print("✅ Database initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            return False
    else:
        print("✅ Database exists.")
    
    return True


def run_tests():
    """Run the test suite."""
    print("\n🧪 Running tests...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'unittest', 'discover', 'tests/', '-v'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Some tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"⚠️  Could not run tests: {e}")
        return True  # Don't fail deployment if tests can't run


def start_bot():
    """Start the bot application."""
    print("\n🚀 Starting TeleShop Bot...")
    print("Press Ctrl+C to stop the bot.\n")
    
    try:
        subprocess.run([sys.executable, 'bot.py'])
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")


def main():
    """Main deployment function."""
    print("🏪 TeleShop Bot Deployment Script")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install required packages.")
        sys.exit(1)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not available. Make sure environment variables are set.")
    
    # Check environment configuration
    if not check_env_file():
        print("\n❌ Environment configuration incomplete.")
        print("Please configure your .env file and run this script again.")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        print("\n❌ Database initialization failed.")
        sys.exit(1)
    
    # Ask if user wants to run tests
    run_tests_choice = input("\nRun tests before starting? (y/n): ").lower().strip()
    if run_tests_choice == 'y':
        if not run_tests():
            continue_anyway = input("Tests failed. Continue anyway? (y/n): ").lower().strip()
            if continue_anyway != 'y':
                sys.exit(1)
    
    print("\n✅ All checks passed! Ready to start the bot.")
    
    # Ask if user wants to start the bot now
    start_now = input("Start the bot now? (y/n): ").lower().strip()
    if start_now == 'y':
        start_bot()
    else:
        print("\n✅ Setup complete! Run 'python bot.py' to start the bot.")


if __name__ == '__main__':
    main()
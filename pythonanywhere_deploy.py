#!/usr/bin/env python3
"""
PythonAnywhere Deployment Script for TeleShop Bot
Prepares the bot for deployment with data clearing and configuration validation.
"""

import os
import sys
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class PythonAnywhereDeployer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "deployment_backups"
        self.deployment_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log deployment messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.deployment_log.append(log_entry)
        print(log_entry)
    
    def create_backup(self) -> bool:
        """Create backup of existing data before clearing"""
        try:
            self.log("Creating backup of existing data...")
            
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(exist_ok=True)
            
            # Backup database if exists
            db_path = self.project_root / "teleshop.db"
            if db_path.exists():
                shutil.copy2(db_path, backup_path / "teleshop.db")
                self.log(f"Database backed up to {backup_path}")
            
            # Backup logs directory
            logs_dir = self.project_root / "logs"
            if logs_dir.exists():
                shutil.copytree(logs_dir, backup_path / "logs", dirs_exist_ok=True)
                self.log("Logs directory backed up")
            
            # Backup uploads directory
            uploads_dir = self.project_root / "uploads"
            if uploads_dir.exists():
                shutil.copytree(uploads_dir, backup_path / "uploads", dirs_exist_ok=True)
                self.log("Uploads directory backed up")
            
            # Backup .env file if exists
            env_file = self.project_root / ".env"
            if env_file.exists():
                shutil.copy2(env_file, backup_path / ".env")
                self.log(".env file backed up")
            
            return True
            
        except Exception as e:
            self.log(f"Backup failed: {e}", "ERROR")
            return False
    
    def clear_existing_data(self) -> bool:
        """Clear all existing data for fresh deployment"""
        try:
            self.log("Clearing existing data...")
            
            # Remove database files
            db_files = [
                "teleshop.db",
                "teleshop.db-shm", 
                "teleshop.db-wal",
                "teleshop.log"
            ]
            
            for db_file in db_files:
                file_path = self.project_root / db_file
                if file_path.exists():
                    file_path.unlink()
                    self.log(f"Removed {db_file}")
            
            # Clear logs directory
            logs_dir = self.project_root / "logs"
            if logs_dir.exists():
                shutil.rmtree(logs_dir)
                self.log("Cleared logs directory")
            
            # Clear uploads directory
            uploads_dir = self.project_root / "uploads"
            if uploads_dir.exists():
                shutil.rmtree(uploads_dir)
                self.log("Cleared uploads directory")
            
            # Clear __pycache__ directories
            for pycache_dir in self.project_root.rglob("__pycache__"):
                if pycache_dir.is_dir():
                    shutil.rmtree(pycache_dir)
                    self.log(f"Cleared {pycache_dir}")
            
            # Clear .pyc files
            for pyc_file in self.project_root.rglob("*.pyc"):
                pyc_file.unlink()
                self.log(f"Removed {pyc_file}")
            
            return True
            
        except Exception as e:
            self.log(f"Data clearing failed: {e}", "ERROR")
            return False
    
    def create_required_directories(self) -> bool:
        """Create required directories for the application"""
        try:
            self.log("Creating required directories...")
            
            required_dirs = [
                "logs",
                "uploads", 
                "backups",
                "data"
            ]
            
            for dir_name in required_dirs:
                dir_path = self.project_root / dir_name
                dir_path.mkdir(exist_ok=True)
                self.log(f"Created directory: {dir_name}")
            
            return True
            
        except Exception as e:
            self.log(f"Directory creation failed: {e}", "ERROR")
            return False
    
    def validate_environment(self) -> bool:
        """Validate environment configuration"""
        try:
            self.log("Validating environment configuration...")
            
            # Check if .env file exists
            env_file = self.project_root / ".env"
            if not env_file.exists():
                self.log(".env file not found. Please create it from .env.example", "ERROR")
                return False
            
            # Load and validate environment variables
            from dotenv import load_dotenv
            load_dotenv()
            
            required_vars = {
                'BOT_TOKEN': 'Telegram bot token',
                'ADMIN_IDS': 'Admin user IDs',
                'SECRET_KEY': 'Secret key for encryption'
            }
            
            missing_vars = []
            for var, description in required_vars.items():
                value = os.getenv(var)
                if not value or value.startswith('your_'):
                    missing_vars.append(f"{var} ({description})")
            
            if missing_vars:
                self.log(f"Missing required environment variables: {', '.join(missing_vars)}", "ERROR")
                return False
            
            self.log("Environment configuration validated successfully")
            return True
            
        except Exception as e:
            self.log(f"Environment validation failed: {e}", "ERROR")
            return False
    
    def initialize_fresh_database(self) -> bool:
        """Initialize a fresh database with required tables"""
        try:
            self.log("Initializing fresh database...")
            
            # Import database manager to initialize tables
            from database import DatabaseManager
            
            db = DatabaseManager("teleshop.db")
            self.log("Database initialized with all required tables")
            
            # Add initial admin data if needed
            admin_ids = os.getenv('ADMIN_IDS', '').split(',')
            if admin_ids and admin_ids[0].strip():
                admin_id = int(admin_ids[0].strip())
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR IGNORE INTO users (user_id, username, balance, discount, is_banned)
                        VALUES (?, 'admin', 0.0, 0, FALSE)
                    """, (admin_id,))
                    conn.commit()
                    self.log(f"Admin user {admin_id} added to database")
            
            return True
            
        except Exception as e:
            self.log(f"Database initialization failed: {e}", "ERROR")
            return False
    
    def validate_dependencies(self) -> bool:
        """Validate that all required dependencies are available"""
        try:
            self.log("Validating dependencies...")
            
            # Read requirements.txt
            requirements_file = self.project_root / "requirements.txt"
            if not requirements_file.exists():
                self.log("requirements.txt not found", "ERROR")
                return False
            
            # Check critical imports
            critical_imports = [
                'telegram',
                'telegram.ext',
                'sqlite3',
                'dotenv',
                'cryptography'
            ]
            
            for module in critical_imports:
                try:
                    __import__(module)
                    self.log(f"✓ {module}")
                except ImportError as e:
                    self.log(f"✗ {module} - {e}", "ERROR")
                    return False
            
            self.log("All critical dependencies validated")
            return True
            
        except Exception as e:
            self.log(f"Dependency validation failed: {e}", "ERROR")
            return False
    
    def create_pythonanywhere_config(self) -> bool:
        """Create PythonAnywhere specific configuration files"""
        try:
            self.log("Creating PythonAnywhere configuration...")
            
            # Create WSGI file for web app (if needed)
            wsgi_content = '''#!/usr/bin/env python3
"""
WSGI configuration for TeleShop Bot on PythonAnywhere
This file is used if you want to run a web interface alongside the bot.
"""

import sys
import os

# Add your project directory to Python path
project_home = '/home/yourusername/teleshop'  # Update this path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'

# This is just a placeholder - modify according to your needs
def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return [b"TeleShop Bot is running as a background task."]
'''
            
            wsgi_file = self.project_root / "wsgi.py"
            with open(wsgi_file, 'w', encoding='utf-8') as f:
                f.write(wsgi_content)
            
            # Create startup script for PythonAnywhere
            startup_content = '''#!/usr/bin/env python3
"""
Startup script for TeleShop Bot on PythonAnywhere
Use this script in your "Always-On Tasks" section.
"""

import os
import sys
from pathlib import Path

# Set up the project path
project_path = Path(__file__).parent
sys.path.insert(0, str(project_path))

# Change to project directory
os.chdir(project_path)

# Import and run the bot
if __name__ == "__main__":
    from bot import main
    main()
'''
            
            startup_file = self.project_root / "start_bot.py"
            with open(startup_file, 'w', encoding='utf-8') as f:
                f.write(startup_content)
            
            # Make startup script executable
            os.chmod(startup_file, 0o755)
            
            self.log("PythonAnywhere configuration files created")
            return True
            
        except Exception as e:
            self.log(f"PythonAnywhere configuration failed: {e}", "ERROR")
            return False
    
    def create_deployment_summary(self) -> bool:
        """Create deployment summary and instructions"""
        try:
            summary_content = f'''# TeleShop Bot - PythonAnywhere Deployment Summary

Deployment completed on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Deployment Steps Completed:

'''
            
            for log_entry in self.deployment_log:
                summary_content += f"- {log_entry}\n"
            
            summary_content += '''

## PythonAnywhere Setup Instructions:

1. **Upload Files:**
   - Upload all project files to your PythonAnywhere account
   - Ensure the project is in your home directory (e.g., /home/yourusername/teleshop)

2. **Install Dependencies:**
   ```bash
   pip3.10 install --user -r requirements.txt
   ```

3. **Configure Environment:**
   - Edit the .env file with your actual values
   - Ensure BOT_TOKEN, ADMIN_IDS, and SECRET_KEY are properly set

4. **Set up Always-On Task:**
   - Go to your PythonAnywhere dashboard
   - Navigate to "Tasks" tab
   - Create a new always-on task
   - Command: `python3.10 /home/yourusername/teleshop/start_bot.py`
   - Replace "yourusername" with your actual username

5. **Verify Deployment:**
   - Check the task logs for any errors
   - Test the bot by sending /start command
   - Monitor the logs directory for application logs

## Important Notes:

- The database has been cleared and reinitialized
- All previous data has been backed up to deployment_backups/
- The bot is configured to run continuously via the always-on task
- Logs will be stored in the logs/ directory
- File uploads will be stored in the uploads/ directory

## Troubleshooting:

- If the bot doesn't start, check the always-on task logs
- Ensure all environment variables are properly set in .env
- Verify that the file paths in start_bot.py match your directory structure
- Check that all dependencies are installed for the correct Python version

## Support:

If you encounter issues, check the logs in the logs/ directory for detailed error messages.
'''
            
            summary_file = self.project_root / "DEPLOYMENT_SUMMARY.md"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            self.log("Deployment summary created")
            return True
            
        except Exception as e:
            self.log(f"Summary creation failed: {e}", "ERROR")
            return False
    
    def deploy(self, clear_data: bool = True) -> bool:
        """Execute full deployment process"""
        self.log("Starting PythonAnywhere deployment process...")
        
        steps = [
            ("Creating backup", self.create_backup),
            ("Validating dependencies", self.validate_dependencies),
            ("Validating environment", self.validate_environment),
        ]
        
        if clear_data:
            steps.append(("Clearing existing data", self.clear_existing_data))
        
        steps.extend([
            ("Creating required directories", self.create_required_directories),
            ("Initializing fresh database", self.initialize_fresh_database),
            ("Creating PythonAnywhere config", self.create_pythonanywhere_config),
            ("Creating deployment summary", self.create_deployment_summary)
        ])
        
        for step_name, step_function in steps:
            self.log(f"Executing: {step_name}")
            if not step_function():
                self.log(f"Deployment failed at step: {step_name}", "ERROR")
                return False
        
        self.log("\n🎉 Deployment completed successfully!")
        self.log("📋 Check DEPLOYMENT_SUMMARY.md for setup instructions")
        return True


def final_deployment_check(deployer) -> bool:
    """Perform final deployment readiness check"""
    deployer.log("Performing final deployment readiness check...")
    issues = []
    
    # Check critical files exist
    critical_files = [
        'bot.py', 'config.py', 'database.py', '.env',
        'requirements.txt', 'start_bot.py', 'wsgi.py'
    ]
    
    for file in critical_files:
        file_path = deployer.project_root / file
        if not file_path.exists():
            issues.append(f"Missing critical file: {file}")
    
    # Check .env file has required variables
    env_file = deployer.project_root / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
            required_vars = ['BOT_TOKEN', 'ADMIN_IDS', 'SECRET_KEY']
            for var in required_vars:
                if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                    issues.append(f"Environment variable {var} not properly configured")
    
    # Check database file exists and is accessible
    db_file = deployer.project_root / 'teleshop.db'
    if db_file.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            if len(tables) == 0:
                issues.append("Database exists but has no tables")
        except Exception as e:
            issues.append(f"Database access error: {e}")
    
    if issues:
        deployer.log("Deployment Issues Found:", "ERROR")
        for issue in issues:
            deployer.log(f"   • {issue}", "ERROR")
        return False
    else:
        deployer.log("All deployment checks passed!")
        return True

def main():
    """Main deployment function"""
    print("🚀 TeleShop Bot - PythonAnywhere Deployment Tool")
    print("=" * 60)
    
    deployer = PythonAnywhereDeployer()
    
    # Ask user about data clearing
    clear_data = True
    if input("\nClear all existing data? (Y/n): ").lower().strip() == 'n':
        clear_data = False
    
    # Execute deployment
    success = deployer.deploy(clear_data=clear_data)
    
    if success:
        # Perform final deployment check
        deployer.log("\nPerforming final deployment readiness check...")
        if final_deployment_check(deployer):
            print("\n" + "=" * 60)
            print("✅ DEPLOYMENT PREPARATION COMPLETE!")
            print("📋 Check DEPLOYMENT_SUMMARY.md for next steps")
            print("🚀 Your bot is ready for PythonAnywhere deployment!")
            print("\n💡 Quick Start:")
            print("   1. Upload all files to PythonAnywhere")
            print("   2. Install dependencies: pip3.10 install --user -r requirements.txt")
            print("   3. Configure .env file with your tokens")
            print("   4. Set up Always-On Task: python3.10 start_bot.py")
            return 0
        else:
            print("\n❌ Deployment preparation completed with issues!")
            print("Please resolve the issues above before deploying.")
            return 1
    else:
        print("\n❌ Deployment failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
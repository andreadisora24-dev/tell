#!/usr/bin/env python3
"""
Security Setup Script for TeleShop Bot

This script initializes all security components and performs necessary setup tasks.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from secure_config import secure_config, migrate_bot_secrets
from secure_logging import SecureLogger
from utils import hash_password

# Load environment variables
load_dotenv()

def setup_secure_environment():
    """Setup secure environment for production"""
    print("🔒 Setting up secure environment...")
    
    # Create necessary directories
    directories = ['logs', 'data', 'uploads', 'backups']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Set up secure logging
    try:
        loggers = SecureLogger.setup_secure_logging()
        print("✅ Secure logging initialized")
    except Exception as e:
        print(f"❌ Failed to setup secure logging: {e}")
        return False
    
    return True

def migrate_secrets():
    """Migrate secrets to secure vault"""
    print("🔐 Migrating secrets to secure vault...")
    
    try:
        migrated_count = migrate_bot_secrets()
        print(f"✅ Migrated {migrated_count} secrets to vault")
        
        # Log the migration
        SecureLogger.log_security_event(
            'secrets_migration_completed',
            details={'migrated_count': migrated_count},
            severity='INFO'
        )
        
        return True
    except Exception as e:
        print(f"❌ Failed to migrate secrets: {e}")
        return False

def setup_admin_password():
    """Setup secure admin password"""
    print("👤 Setting up admin password...")
    
    # Check if admin password exists in environment
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    if not admin_password:
        print("⚠️  No ADMIN_PASSWORD found in environment")
        
        # In production, require password to be set
        if os.getenv('ENVIRONMENT', 'development') == 'production':
            print("❌ ADMIN_PASSWORD must be set in production environment")
            return False
        
        # For development, use a default secure password
        admin_password = 'SecureAdmin123!'
        print("🔧 Using default password for development")
    
    # Hash the password and store in vault
    try:
        hashed_password = hash_password(admin_password)
        secure_config.store_secret(
            'admin_password_hash',
            hashed_password,
            'Hashed admin password for secure authentication'
        )
        print("✅ Admin password securely stored")
        
        SecureLogger.log_security_event(
            'admin_password_configured',
            details={'method': 'bcrypt_hash'},
            severity='INFO'
        )
        
        return True
    except Exception as e:
        print(f"❌ Failed to setup admin password: {e}")
        return False

def validate_security_configuration():
    """Validate security configuration"""
    print("🔍 Validating security configuration...")
    
    checks = [
        ('Bot Token', lambda: bool(os.getenv('BOT_TOKEN') or secure_config.get_secret('bot_token'))),
        ('Database Path', lambda: bool(os.getenv('DATABASE_PATH') and os.getenv('DATABASE_PATH').strip())),
        ('Logs Directory', lambda: Path('logs').exists()),
        ('Vault Encryption', lambda: bool(os.getenv('VAULT_ENCRYPTION_KEY') and len(os.getenv('VAULT_ENCRYPTION_KEY', '')) > 10)),
        ('Rate Limiting', lambda: bool(os.getenv('RATE_LIMIT_REQUESTS') or os.getenv('MAX_REQUESTS_PER_MINUTE'))),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if check_func():
                print(f"✅ {check_name}: OK")
            else:
                print(f"⚠️  {check_name}: Missing or invalid")
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name}: Error - {e}")
            all_passed = False
    
    return all_passed

def generate_security_report():
    """Generate security configuration report"""
    print("\n📊 Security Configuration Report")
    print("=" * 40)
    
    # Environment info
    environment = os.getenv('ENVIRONMENT', 'development')
    print(f"Environment: {environment}")
    
    # Security features status
    features = {
        'Secure Password Hashing': 'bcrypt',
        'Rate Limiting': 'Enabled' if os.getenv('MAX_REQUESTS_PER_MINUTE') else 'Disabled',
        'Session Management': 'Database-backed with timeout',
        'Error Handling': 'Sanitized user messages',
        'Logging': 'Secure with sensitive data masking',
        'CSRF Protection': 'Token-based for admin functions',
        'Secret Management': 'Encrypted vault storage'
    }
    
    for feature, status in features.items():
        print(f"• {feature}: {status}")
    
    # Vault statistics
    try:
        secrets = secure_config.list_secrets()
        print(f"\nSecrets in vault: {len(secrets)}")
        for secret_key, info in secrets.items():
            print(f"  - {secret_key}: {info.get('description', 'No description')}")
    except Exception as e:
        print(f"\nVault status: Error - {e}")
    
    print("\n" + "=" * 40)

def main():
    """Main security setup function"""
    print("🚀 TeleShop Security Setup")
    print("=" * 30)
    
    steps = [
        ("Environment Setup", setup_secure_environment),
        ("Secret Migration", migrate_secrets),
        ("Admin Password", setup_admin_password),
        ("Configuration Validation", validate_security_configuration)
    ]
    
    success_count = 0
    
    for step_name, step_func in steps:
        print(f"\n🔧 {step_name}")
        print("-" * 20)
        
        try:
            if step_func():
                success_count += 1
                print(f"✅ {step_name} completed successfully")
            else:
                print(f"❌ {step_name} failed")
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
    
    print(f"\n📈 Setup Summary: {success_count}/{len(steps)} steps completed")
    
    if success_count == len(steps):
        print("🎉 Security setup completed successfully!")
        generate_security_report()
        
        # Final security log
        SecureLogger.log_security_event(
            'security_setup_completed',
            details={
                'steps_completed': success_count,
                'total_steps': len(steps),
                'environment': os.getenv('ENVIRONMENT', 'development')
            },
            severity='INFO'
        )
        
        return True
    else:
        print("⚠️  Security setup completed with warnings. Please review the failed steps.")
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with unexpected error: {e}")
        sys.exit(1)
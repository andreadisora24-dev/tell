import os
import json
import base64
from typing import Dict, Any, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from secure_logging import SecureLogger

class SecureConfigManager:
    """Secure configuration management with encryption support"""
    
    def __init__(self, config_file: str = 'secure_config.json', 
                 vault_file: str = 'secrets.vault'):
        self.config_file = Path(config_file)
        self.vault_file = Path(vault_file)
        self._encryption_key = None
        self._config_cache = {}
        self._vault_cache = {}
        
        # Initialize encryption key from environment or generate new one
        self._init_encryption_key()
    
    def _init_encryption_key(self):
        """Initialize encryption key for vault"""
        # Try to get key from environment
        key_env = os.getenv('VAULT_ENCRYPTION_KEY')
        
        if key_env:
            try:
                self._encryption_key = base64.urlsafe_b64decode(key_env.encode())
            except Exception as e:
                SecureLogger.log_security_event(
                    'vault_key_error',
                    details={'error': 'Invalid encryption key format'},
                    severity='ERROR'
                )
                raise ValueError("Invalid vault encryption key format")
        else:
            # Generate new key for development
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                self._encryption_key = Fernet.generate_key()
                SecureLogger.log_security_event(
                    'vault_key_generated',
                    details={'environment': 'development'},
                    severity='WARNING'
                )
            else:
                raise ValueError("VAULT_ENCRYPTION_KEY must be set in production")
    
    def _get_fernet(self) -> Fernet:
        """Get Fernet encryption instance"""
        return Fernet(self._encryption_key)
    
    def store_secret(self, key: str, value: str, description: str = None):
        """Store a secret in the encrypted vault"""
        try:
            # Load existing vault
            vault_data = self._load_vault()
            
            # Encrypt the value
            fernet = self._get_fernet()
            encrypted_value = fernet.encrypt(value.encode()).decode()
            
            # Store in vault
            vault_data[key] = {
                'value': encrypted_value,
                'description': description,
                'created_at': SecureLogger.log_security_event.__defaults__[0],  # Current timestamp
                'updated_at': SecureLogger.log_security_event.__defaults__[0]
            }
            
            # Save vault
            self._save_vault(vault_data)
            
            SecureLogger.log_security_event(
                'secret_stored',
                details={'key': key, 'has_description': bool(description)}
            )
            
        except Exception as e:
            SecureLogger.log_security_event(
                'secret_store_error',
                details={'key': key, 'error': str(e)},
                severity='ERROR'
            )
            raise
    
    def get_secret(self, key: str, default: Any = None) -> Optional[str]:
        """Retrieve a secret from the vault"""
        try:
            # Check cache first
            if key in self._vault_cache:
                return self._vault_cache[key]
            
            # Load vault
            vault_data = self._load_vault()
            
            if key not in vault_data:
                return default
            
            # Decrypt the value
            fernet = self._get_fernet()
            encrypted_value = vault_data[key]['value'].encode()
            decrypted_value = fernet.decrypt(encrypted_value).decode()
            
            # Cache the decrypted value
            self._vault_cache[key] = decrypted_value
            
            return decrypted_value
            
        except Exception as e:
            SecureLogger.log_security_event(
                'secret_retrieve_error',
                details={'key': key, 'error': str(e)},
                severity='ERROR'
            )
            return default
    
    def _load_vault(self) -> Dict[str, Any]:
        """Load encrypted vault from file"""
        if not self.vault_file.exists():
            return {}
        
        try:
            with open(self.vault_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            SecureLogger.log_security_event(
                'vault_load_error',
                details={'error': str(e)},
                severity='ERROR'
            )
            return {}
    
    def _save_vault(self, vault_data: Dict[str, Any]):
        """Save encrypted vault to file"""
        try:
            # Ensure directory exists
            self.vault_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with restricted permissions
            with open(self.vault_file, 'w') as f:
                json.dump(vault_data, f, indent=2)
            
            # Set restrictive file permissions (owner read/write only)
            if os.name != 'nt':  # Unix-like systems
                os.chmod(self.vault_file, 0o600)
            
        except Exception as e:
            SecureLogger.log_security_event(
                'vault_save_error',
                details={'error': str(e)},
                severity='ERROR'
            )
            raise
    
    def get_config(self, key: str, default: Any = None, from_vault: bool = False) -> Any:
        """Get configuration value from environment, config file, or vault"""
        # Priority: Environment -> Vault (if requested) -> Config file -> Default
        
        # Check environment first
        env_value = os.getenv(key)
        if env_value is not None:
            return self._parse_config_value(env_value)
        
        # Check vault if requested
        if from_vault:
            vault_value = self.get_secret(key)
            if vault_value is not None:
                return self._parse_config_value(vault_value)
        
        # Check config file
        config_data = self._load_config()
        if key in config_data:
            return config_data[key]
        
        return default
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            SecureLogger.log_security_event(
                'config_load_error',
                details={'error': str(e)},
                severity='ERROR'
            )
            return {}
    
    def _parse_config_value(self, value: str) -> Any:
        """Parse configuration value to appropriate type"""
        if isinstance(value, str):
            # Try to parse as JSON for complex types
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            
            if value.isdigit():
                return int(value)
            
            try:
                return float(value)
            except ValueError:
                pass
            
            # Try JSON parsing for lists/dicts
            if value.startswith(('[', '{')):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
        
        return value
    
    def migrate_secrets_to_vault(self, secrets_mapping: Dict[str, str]):
        """Migrate secrets from environment/config to vault"""
        """secrets_mapping: {vault_key: env_key}"""
        
        migrated_count = 0
        
        for vault_key, env_key in secrets_mapping.items():
            # Get value from environment
            value = os.getenv(env_key)
            
            if value:
                try:
                    self.store_secret(
                        vault_key, 
                        value, 
                        f"Migrated from environment variable {env_key}"
                    )
                    migrated_count += 1
                    
                    SecureLogger.log_security_event(
                        'secret_migrated',
                        details={'vault_key': vault_key, 'env_key': env_key}
                    )
                    
                except Exception as e:
                    SecureLogger.log_security_event(
                        'secret_migration_error',
                        details={'vault_key': vault_key, 'env_key': env_key, 'error': str(e)},
                        severity='ERROR'
                    )
        
        SecureLogger.log_security_event(
            'secrets_migration_completed',
            details={'migrated_count': migrated_count, 'total_count': len(secrets_mapping)}
        )
        
        return migrated_count
    
    def list_secrets(self) -> Dict[str, Dict[str, Any]]:
        """List all secrets in vault (without values)"""
        vault_data = self._load_vault()
        
        return {
            key: {
                'description': info.get('description'),
                'created_at': info.get('created_at'),
                'updated_at': info.get('updated_at')
            }
            for key, info in vault_data.items()
        }
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from vault"""
        try:
            vault_data = self._load_vault()
            
            if key in vault_data:
                del vault_data[key]
                self._save_vault(vault_data)
                
                # Clear from cache
                self._vault_cache.pop(key, None)
                
                SecureLogger.log_security_event(
                    'secret_deleted',
                    details={'key': key}
                )
                
                return True
            
            return False
            
        except Exception as e:
            SecureLogger.log_security_event(
                'secret_delete_error',
                details={'key': key, 'error': str(e)},
                severity='ERROR'
            )
            return False
    
    def rotate_vault_key(self, new_key: bytes = None) -> str:
        """Rotate vault encryption key"""
        if not new_key:
            new_key = Fernet.generate_key()
        
        try:
            # Load current vault
            old_vault_data = self._load_vault()
            
            # Decrypt with old key
            old_fernet = self._get_fernet()
            decrypted_data = {}
            
            for key, info in old_vault_data.items():
                encrypted_value = info['value'].encode()
                decrypted_value = old_fernet.decrypt(encrypted_value).decode()
                decrypted_data[key] = {
                    **info,
                    'value': decrypted_value
                }
            
            # Update encryption key
            self._encryption_key = new_key
            new_fernet = self._get_fernet()
            
            # Re-encrypt with new key
            new_vault_data = {}
            for key, info in decrypted_data.items():
                encrypted_value = new_fernet.encrypt(info['value'].encode()).decode()
                new_vault_data[key] = {
                    **info,
                    'value': encrypted_value,
                    'updated_at': SecureLogger.log_security_event.__defaults__[0]
                }
            
            # Save with new key
            self._save_vault(new_vault_data)
            
            # Clear cache
            self._vault_cache.clear()
            
            # Return new key (base64 encoded for storage)
            new_key_b64 = base64.urlsafe_b64encode(new_key).decode()
            
            SecureLogger.log_security_event(
                'vault_key_rotated',
                details={'secrets_count': len(new_vault_data)},
                severity='WARNING'
            )
            
            return new_key_b64
            
        except Exception as e:
            SecureLogger.log_security_event(
                'vault_key_rotation_error',
                details={'error': str(e)},
                severity='CRITICAL'
            )
            raise

# Global secure config manager
secure_config = SecureConfigManager()

# Helper functions for easy access
def get_secret(key: str, default: Any = None) -> Any:
    """Get secret from vault"""
    return secure_config.get_secret(key, default)

def get_config(key: str, default: Any = None, from_vault: bool = False) -> Any:
    """Get configuration value"""
    return secure_config.get_config(key, default, from_vault)

def store_secret(key: str, value: str, description: str = None):
    """Store secret in vault"""
    return secure_config.store_secret(key, value, description)

# Migration helper
def migrate_bot_secrets():
    """Migrate bot secrets to vault"""
    secrets_to_migrate = {
        'bot_token': 'BOT_TOKEN',
        'database_url': 'DATABASE_URL',
        'admin_password': 'ADMIN_PASSWORD',
        'encryption_key': 'ENCRYPTION_KEY',
        'webhook_secret': 'WEBHOOK_SECRET',
        'payment_token': 'PAYMENT_TOKEN'
    }
    
    return secure_config.migrate_secrets_to_vault(secrets_to_migrate)
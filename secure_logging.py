import logging
import logging.handlers
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class SecureLogger:
    """Secure logging configuration with sensitive data protection"""
    
    # Sensitive patterns that should be masked in logs
    SENSITIVE_PATTERNS = [
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card numbers
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'password[\s]*[:=][\s]*[^\s]+',  # Passwords
        r'token[\s]*[:=][\s]*[^\s]+',  # Tokens
        r'secret[\s]*[:=][\s]*[^\s]+',  # Secrets
        r'key[\s]*[:=][\s]*[^\s]+',  # Keys
        r'api[_-]?key[\s]*[:=][\s]*[^\s]+',  # API keys
    ]
    
    @staticmethod
    def setup_secure_logging(log_level: str = 'INFO', log_dir: str = 'logs') -> Dict[str, logging.Logger]:
        """Setup secure logging configuration"""
        
        # Create logs directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Configure formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        json_formatter = SecureJSONFormatter()
        
        # Main application logger
        app_logger = logging.getLogger('teleshop')
        app_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Security events logger
        security_logger = logging.getLogger('security')
        security_logger.setLevel(logging.INFO)
        
        # Error logger
        error_logger = logging.getLogger('errors')
        error_logger.setLevel(logging.ERROR)
        
        # Performance logger
        performance_logger = logging.getLogger('performance')
        performance_logger.setLevel(logging.INFO)
        
        # Setup file handlers with rotation
        handlers = {
            'app': SecureLogger._create_rotating_handler(
                log_path / 'app.log', detailed_formatter
            ),
            'security': SecureLogger._create_rotating_handler(
                log_path / 'security.log', json_formatter
            ),
            'errors': SecureLogger._create_rotating_handler(
                log_path / 'errors.log', detailed_formatter
            ),
            'performance': SecureLogger._create_rotating_handler(
                log_path / 'performance.log', json_formatter
            )
        }
        
        # Add handlers to loggers
        app_logger.addHandler(handlers['app'])
        security_logger.addHandler(handlers['security'])
        error_logger.addHandler(handlers['errors'])
        performance_logger.addHandler(handlers['performance'])
        
        # Console handler for development
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            app_logger.addHandler(console_handler)
        
        return {
            'app': app_logger,
            'security': security_logger,
            'errors': error_logger,
            'performance': performance_logger
        }
    
    @staticmethod
    def _create_rotating_handler(file_path: Path, formatter: logging.Formatter) -> logging.handlers.RotatingFileHandler:
        """Create a rotating file handler"""
        handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(formatter)
        return handler
    
    @staticmethod
    def mask_sensitive_data(message: str) -> str:
        """Mask sensitive data in log messages"""
        import re
        
        masked_message = message
        for pattern in SecureLogger.SENSITIVE_PATTERNS:
            masked_message = re.sub(pattern, '[MASKED]', masked_message, flags=re.IGNORECASE)
        
        return masked_message
    
    @staticmethod
    def log_security_event(event_type: str, user_id: Optional[int] = None, 
                          details: Dict[str, Any] = None, severity: str = 'INFO'):
        """Log security events"""
        security_logger = logging.getLogger('security')
        
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'severity': severity,
            'details': details or {}
        }
        
        if severity.upper() == 'CRITICAL':
            security_logger.critical(json.dumps(event_data))
        elif severity.upper() == 'ERROR':
            security_logger.error(json.dumps(event_data))
        elif severity.upper() == 'WARNING':
            security_logger.warning(json.dumps(event_data))
        else:
            security_logger.info(json.dumps(event_data))
    
    @staticmethod
    def log_performance_metric(metric_name: str, value: float, user_id: Optional[int] = None, 
                             context: Dict[str, Any] = None):
        """Log performance metrics"""
        performance_logger = logging.getLogger('performance')
        
        metric_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'metric_name': metric_name,
            'value': value,
            'user_id': user_id,
            'context': context or {}
        }
        
        performance_logger.info(json.dumps(metric_data))
    
    @staticmethod
    def log_user_action(action: str, user_id: int, details: Dict[str, Any] = None):
        """Log user actions for audit trail"""
        SecureLogger.log_security_event(
            event_type='user_action',
            user_id=user_id,
            details={
                'action': action,
                'details': details or {}
            },
            severity='INFO'
        )
    
    @staticmethod
    def log_admin_action(action: str, admin_id: int, target_user_id: Optional[int] = None, 
                        details: Dict[str, Any] = None):
        """Log admin actions for audit trail"""
        SecureLogger.log_security_event(
            event_type='admin_action',
            user_id=admin_id,
            details={
                'action': action,
                'target_user_id': target_user_id,
                'details': details or {}
            },
            severity='WARNING'
        )
    
    @staticmethod
    def log_rate_limit_violation(user_id: int, endpoint: str, attempts: int):
        """Log rate limit violations"""
        SecureLogger.log_security_event(
            event_type='rate_limit_violation',
            user_id=user_id,
            details={
                'endpoint': endpoint,
                'attempts': attempts
            },
            severity='WARNING'
        )
    
    @staticmethod
    def log_authentication_event(event_type: str, user_id: Optional[int] = None, 
                               success: bool = True, details: Dict[str, Any] = None):
        """Log authentication events"""
        severity = 'INFO' if success else 'WARNING'
        
        SecureLogger.log_security_event(
            event_type=f'auth_{event_type}',
            user_id=user_id,
            details={
                'success': success,
                'details': details or {}
            },
            severity=severity
        )

class SecureJSONFormatter(logging.Formatter):
    """JSON formatter that masks sensitive data"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': SecureLogger.mask_sensitive_data(record.getMessage()),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# Performance monitoring decorator
def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        import time
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                SecureLogger.log_performance_metric(
                    metric_name, 
                    execution_time,
                    context={'function': func.__name__}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                SecureLogger.log_performance_metric(
                    f"{metric_name}_error", 
                    execution_time,
                    context={'function': func.__name__, 'error': str(e)}
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                SecureLogger.log_performance_metric(
                    metric_name, 
                    execution_time,
                    context={'function': func.__name__}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                SecureLogger.log_performance_metric(
                    f"{metric_name}_error", 
                    execution_time,
                    context={'function': func.__name__, 'error': str(e)}
                )
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator

# Initialize secure logging
loggers = SecureLogger.setup_secure_logging()
app_logger = loggers['app']
security_logger = loggers['security']
error_logger = loggers['errors']
performance_logger = loggers['performance']
"""
Security Configuration Implementation
Handles security features including authentication, file system protection,
and resource limits
"""

import os
import jwt
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
import yaml
from dataclasses import dataclass
from cryptography.fernet import Fernet
import resource
import psutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ResourceLimits:
    max_memory_mb: int = 8192  # 8GB
    max_cpu_percent: float = 80.0
    max_file_size_mb: int = 100
    max_open_files: int = 1000
    request_timeout: int = 30

class SecurityManager:
    def __init__(self, config_path: str = "security_config.yaml"):
        self.config_path = config_path
        self.allowed_paths: Set[Path] = set()
        self.allowed_commands: Set[str] = set()
        self.secret_key: Optional[bytes] = None
        self.fernet: Optional[Fernet] = None
        self.resource_limits = ResourceLimits()
        self.load_config()
        
    def load_config(self):
        """Load security configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Set up allowed paths
            self.allowed_paths = {Path(p).resolve() for p in config.get('allowed_paths', [])}
            
            # Set up allowed commands
            self.allowed_commands = set(config.get('allowed_commands', []))
            
            # Set up encryption
            if 'secret_key' in config:
                self.secret_key = config['secret_key'].encode()
                self.fernet = Fernet(self.secret_key)
                
            # Set up resource limits
            if 'resource_limits' in config:
                limits = config['resource_limits']
                self.resource_limits = ResourceLimits(
                    max_memory_mb=limits.get('max_memory_mb', 8192),
                    max_cpu_percent=limits.get('max_cpu_percent', 80.0),
                    max_file_size_mb=limits.get('max_file_size_mb', 100),
                    max_open_files=limits.get('max_open_files', 1000),
                    request_timeout=limits.get('request_timeout', 30)
                )
                
            logger.info("Security configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading security configuration: {str(e)}")
            raise
            
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token for authentication"""
        if not self.secret_key:
            raise RuntimeError("Secret key not configured")
            
        payload = {
            'user_id': user_id,
            'exp': time.time() + expires_in
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
        
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        if not self.secret_key:
            raise RuntimeError("Secret key not configured")
            
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
            
    def is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories"""
        try:
            path = path.resolve()
            return any(
                str(path).startswith(str(allowed_path))
                for allowed_path in self.allowed_paths
            )
        except Exception:
            return False
            
    def is_command_allowed(self, command: str) -> bool:
        """Check if command is in allowed list"""
        try:
            base_command = command.split()[0]
            return base_command in self.allowed_commands
        except Exception:
            return False
            
    def encrypt_data(self, data: str) -> bytes:
        """Encrypt sensitive data"""
        if not self.fernet:
            raise RuntimeError("Encryption not configured")
        return self.fernet.encrypt(data.encode())
        
    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive data"""
        if not self.fernet:
            raise RuntimeError("Encryption not configured")
        return self.fernet.decrypt(encrypted_data).decode()
        
    def apply_resource_limits(self):
        """Apply system resource limits"""
        try:
            # Set max memory
            memory_bytes = self.resource_limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            
            # Set max open files
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self.resource_limits.max_open_files, self.resource_limits.max_open_files)
            )
            
            # Set up CPU monitoring
            self.monitor_cpu_usage()
            
            logger.info("Resource limits applied successfully")
            
        except Exception as e:
            logger.error(f"Error applying resource limits: {str(e)}")
            raise
            
    def monitor_cpu_usage(self):
        """Monitor CPU usage and log warnings"""
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.resource_limits.max_cpu_percent:
            logger.warning(f"High CPU usage detected: {cpu_percent}%")
            
    def validate_file_size(self, path: Path) -> bool:
        """Check if file size is within limits"""
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            return size_mb <= self.resource_limits.max_file_size_mb
        except Exception:
            return False

if __name__ == "__main__":
    # Example configuration
    example_config = {
        'allowed_paths': ['./workspace', './data'],
        'allowed_commands': ['git', 'npm', 'python', 'pip'],
        'secret_key': Fernet.generate_key().decode(),
        'resource_limits': {
            'max_memory_mb': 8192,
            'max_cpu_percent': 80.0,
            'max_file_size_mb': 100,
            'max_open_files': 1000,
            'request_timeout': 30
        }
    }
    
    # Save example configuration
    with open('security_config.yaml', 'w') as f:
        yaml.dump(example_config, f)
        
    # Test security manager
    security = SecurityManager()
    
    # Test token generation and verification
    token = security.generate_token('test_user')
    payload = security.verify_token(token)
    print(f"Token verification result: {payload}")
    
    # Test path validation
    test_path = Path('./workspace/test.txt')
    print(f"Path {test_path} allowed: {security.is_path_allowed(test_path)}")
    
    # Test command validation
    test_command = "git status"
    print(f"Command '{test_command}' allowed: {security.is_command_allowed(test_command)}")
    
    # Test encryption
    secret_data = "sensitive information"
    encrypted = security.encrypt_data(secret_data)
    decrypted = security.decrypt_data(encrypted)
    print(f"Encryption test: {secret_data == decrypted}")
    
    # Apply resource limits
    security.apply_resource_limits()

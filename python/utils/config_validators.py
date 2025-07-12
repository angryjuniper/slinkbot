"""
Configuration validation utilities for SlinkBot.

This module provides reusable validation functions and decorators
for configuration values, reducing duplication across config classes.
"""

import re
import os
from pathlib import Path
from typing import Any, Callable, List, Optional, Union, Dict
from urllib.parse import urlparse

from utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Exception raised when configuration validation fails."""
    pass


class ConfigValidator:
    """
    Centralized configuration validation utilities.
    
    Provides reusable validation methods for common configuration
    patterns like URLs, ports, directories, and API keys.
    """
    
    @staticmethod
    def validate_url(url: str, service_name: str, required_schemes: Optional[List[str]] = None) -> str:
        """
        Validate and normalize URL format.
        
        Args:
            url: URL to validate
            service_name: Name of the service for error messages
            required_schemes: List of allowed schemes (default: ['http', 'https'])
            
        Returns:
            Normalized URL (trailing slashes removed)
            
        Raises:
            ValidationError: If URL format is invalid
        """
        if not url:
            raise ValidationError(f"{service_name} URL cannot be empty")
        
        if required_schemes is None:
            required_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme:
                raise ValidationError(f"{service_name} URL must include a scheme (http:// or https://)")
            
            if parsed.scheme not in required_schemes:
                schemes_str = ', '.join(required_schemes)
                raise ValidationError(f"{service_name} URL must use one of these schemes: {schemes_str}")
            
            if not parsed.netloc:
                raise ValidationError(f"{service_name} URL must include a hostname")
            
            # Normalize URL by removing trailing slashes
            normalized_url = url.rstrip('/')
            
            logger.debug(f"Validated {service_name} URL: {normalized_url}")
            return normalized_url
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Invalid {service_name} URL format: {str(e)}")
    
    @staticmethod
    def validate_port(port: Union[str, int], service_name: str, 
                     min_port: int = 1, max_port: int = 65535) -> int:
        """
        Validate port number.
        
        Args:
            port: Port number to validate
            service_name: Name of the service for error messages
            min_port: Minimum allowed port (default: 1)
            max_port: Maximum allowed port (default: 65535)
            
        Returns:
            Validated port as integer
            
        Raises:
            ValidationError: If port is invalid
        """
        try:
            port_int = int(port)
            
            if not (min_port <= port_int <= max_port):
                raise ValidationError(
                    f"{service_name} port must be between {min_port} and {max_port}, got {port_int}"
                )
            
            logger.debug(f"Validated {service_name} port: {port_int}")
            return port_int
            
        except (ValueError, TypeError):
            raise ValidationError(f"{service_name} port must be a valid integer, got {port}")
    
    @staticmethod
    def validate_positive_integer(value: Union[str, int], field_name: str, 
                                min_value: int = 1) -> int:
        """
        Validate positive integer value.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            min_value: Minimum allowed value (default: 1)
            
        Returns:
            Validated integer value
            
        Raises:
            ValidationError: If value is invalid
        """
        try:
            int_value = int(value)
            
            if int_value < min_value:
                raise ValidationError(f"{field_name} must be at least {min_value}, got {int_value}")
            
            logger.debug(f"Validated {field_name}: {int_value}")
            return int_value
            
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer, got {value}")
    
    @staticmethod
    def validate_directory(path: Union[str, Path], field_name: str, 
                          create_if_missing: bool = False, 
                          check_writable: bool = False) -> Path:
        """
        Validate directory path.
        
        Args:
            path: Directory path to validate
            field_name: Name of the field for error messages
            create_if_missing: Whether to create directory if it doesn't exist
            check_writable: Whether to check if directory is writable
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If directory is invalid
        """
        if not path:
            raise ValidationError(f"{field_name} directory path cannot be empty")
        
        path_obj = Path(path)
        
        try:
            # Create directory if requested and it doesn't exist
            if create_if_missing and not path_obj.exists():
                path_obj.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {path_obj}")
            
            # Check if path exists and is a directory
            if not path_obj.exists():
                raise ValidationError(f"{field_name} directory does not exist: {path_obj}")
            
            if not path_obj.is_dir():
                raise ValidationError(f"{field_name} path is not a directory: {path_obj}")
            
            # Check if writable (if requested)
            if check_writable and not os.access(path_obj, os.W_OK):
                raise ValidationError(f"{field_name} directory is not writable: {path_obj}")
            
            logger.debug(f"Validated {field_name} directory: {path_obj}")
            return path_obj
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Error validating {field_name} directory: {str(e)}")
    
    @staticmethod
    def validate_api_key(api_key: str, service_name: str, 
                        min_length: int = 8, max_length: int = 256) -> str:
        """
        Validate API key format.
        
        Args:
            api_key: API key to validate
            service_name: Name of the service for error messages
            min_length: Minimum key length (default: 8)
            max_length: Maximum key length (default: 256)
            
        Returns:
            Validated API key
            
        Raises:
            ValidationError: If API key is invalid
        """
        if not api_key:
            raise ValidationError(f"{service_name} API key cannot be empty")
        
        api_key = api_key.strip()
        
        if len(api_key) < min_length:
            raise ValidationError(f"{service_name} API key must be at least {min_length} characters")
        
        if len(api_key) > max_length:
            raise ValidationError(f"{service_name} API key must be at most {max_length} characters")
        
        # Check for obviously invalid keys
        if api_key.lower() in ['your_api_key', 'api_key_here', 'changeme', 'placeholder']:
            raise ValidationError(f"{service_name} API key appears to be a placeholder value")
        
        logger.debug(f"Validated {service_name} API key (length: {len(api_key)})")
        return api_key
    
    @staticmethod
    def validate_log_level(level: str) -> str:
        """
        Validate logging level.
        
        Args:
            level: Log level to validate
            
        Returns:
            Validated log level
            
        Raises:
            ValidationError: If log level is invalid
        """
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        if not level:
            raise ValidationError("Log level cannot be empty")
        
        level = level.upper().strip()
        
        if level not in valid_levels:
            valid_str = ', '.join(valid_levels)
            raise ValidationError(f"Log level must be one of: {valid_str}, got {level}")
        
        logger.debug(f"Validated log level: {level}")
        return level
    
    @staticmethod
    def validate_channel_id(channel_id: Union[str, int], channel_name: str) -> int:
        """
        Validate Discord channel ID.
        
        Args:
            channel_id: Channel ID to validate
            channel_name: Name of the channel for error messages
            
        Returns:
            Validated channel ID as integer
            
        Raises:
            ValidationError: If channel ID is invalid
        """
        try:
            channel_id_int = int(channel_id)
            
            # Discord IDs are 64-bit integers, typically 17-19 digits for channels
            if channel_id_int < 10**16 or channel_id_int > 10**20:
                raise ValidationError(f"{channel_name} channel ID appears invalid: {channel_id_int}")
            
            logger.debug(f"Validated {channel_name} channel ID: {channel_id_int}")
            return channel_id_int
            
        except (ValueError, TypeError):
            raise ValidationError(f"{channel_name} channel ID must be a valid integer, got {channel_id}")
    
    @staticmethod
    def validate_email(email: str, field_name: str = "Email") -> str:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            field_name: Name of the field for error messages
            
        Returns:
            Validated email address
            
        Raises:
            ValidationError: If email is invalid
        """
        if not email:
            raise ValidationError(f"{field_name} cannot be empty")
        
        email = email.strip().lower()
        
        # Basic email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            raise ValidationError(f"{field_name} format is invalid: {email}")
        
        logger.debug(f"Validated {field_name}: {email}")
        return email
    
    @staticmethod
    def validate_required_fields(config_dict: Dict[str, Any], 
                                required_fields: List[str], 
                                config_name: str = "Configuration") -> None:
        """
        Validate that all required fields are present and not empty.
        
        Args:
            config_dict: Configuration dictionary to validate
            required_fields: List of required field names
            config_name: Name of the configuration for error messages
            
        Raises:
            ValidationError: If required fields are missing
        """
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in config_dict:
                missing_fields.append(field)
            elif not config_dict[field]:
                empty_fields.append(field)
        
        errors = []
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        if empty_fields:
            errors.append(f"Empty required fields: {', '.join(empty_fields)}")
        
        if errors:
            error_msg = f"{config_name} validation failed. " + "; ".join(errors)
            raise ValidationError(error_msg)
        
        logger.debug(f"All required fields present for {config_name}")


def validate_config_field(validator_func: Callable[[Any], Any], 
                         error_message: Optional[str] = None):
    """
    Decorator to validate a single configuration field.
    
    Args:
        validator_func: Function to validate the field value
        error_message: Custom error message (optional)
    
    Usage:
        @validate_config_field(lambda x: len(x) > 0, "Field cannot be empty")
        def set_api_key(self, value: str):
            self.api_key = value
    """
    def decorator(func):
        def wrapper(self, value):
            try:
                validated_value = validator_func(value)
                return func(self, validated_value)
            except Exception as e:
                if error_message:
                    raise ValidationError(error_message)
                raise ValidationError(f"Validation failed for {func.__name__}: {str(e)}")
        return wrapper
    return decorator


def validate_config_class(required_fields: Optional[List[str]] = None):
    """
    Class decorator to add validation to configuration classes.
    
    Args:
        required_fields: List of required field names
    
    Usage:
        @validate_config_class(required_fields=['api_key', 'url'])
        class ServiceConfig:
            def __init__(self):
                self.api_key = ""
                self.url = ""
    """
    def decorator(cls):
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            
            # Auto-validate if validate() method exists
            if hasattr(self, 'validate'):
                self.validate()
            elif required_fields:
                # Basic required field validation
                config_dict = {field: getattr(self, field, None) for field in required_fields}
                ConfigValidator.validate_required_fields(
                    config_dict, required_fields, cls.__name__
                )
        
        cls.__init__ = new_init
        return cls
    
    return decorator


# Convenience validation functions
def validate_url(url: str, service_name: str = "Service") -> str:
    """Convenience function for URL validation."""
    return ConfigValidator.validate_url(url, service_name)


def validate_positive_int(value: Union[str, int], field_name: str = "Value") -> int:
    """Convenience function for positive integer validation."""
    return ConfigValidator.validate_positive_integer(value, field_name)


def validate_directory_path(path: Union[str, Path], field_name: str = "Directory", 
                           create: bool = False) -> Path:
    """Convenience function for directory validation."""
    return ConfigValidator.validate_directory(path, field_name, create_if_missing=create)
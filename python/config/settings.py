"""Configuration management system for SlinkBot.

This module provides centralized configuration management with validation,
environment variable loading, and type safety.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from utils.config_validators import ConfigValidator, ValidationError


@dataclass
class APIConfig:
    """Configuration for external API services.
    
    Attributes:
        jellyseerr_url: Base URL for Jellyseerr API
        jellyseerr_api_key: API key for Jellyseerr authentication
        radarr_url: Base URL for Radarr API
        radarr_api_key: API key for Radarr authentication
        sonarr_url: Base URL for Sonarr API
        sonarr_api_key: API key for Sonarr authentication
        sabnzbd_url: Base URL for SABnzbd API
        sabnzbd_api_key: API key for SABnzbd authentication
        discord_bot_token: Discord bot authentication token
        nvidia_api_key: NVIDIA Developer API key for LLM services
        nvidia_base_url: Base URL for NVIDIA API
        nvidia_model: NVIDIA model name for LLM inference
    """
    
    jellyseerr_url: str
    jellyseerr_api_key: str
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    sabnzbd_url: str = ""
    sabnzbd_api_key: str = ""
    discord_bot_token: str = ""
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.3-70b-instruct"
    
    def validate(self) -> None:
        """Validate all required configuration values.
        
        Raises:
            ValidationError: If required configuration values are missing or invalid
        """
        try:
            # Validate required fields
            ConfigValidator.validate_required_fields(
                {
                    'jellyseerr_url': self.jellyseerr_url,
                    'jellyseerr_api_key': self.jellyseerr_api_key,
                    'discord_bot_token': self.discord_bot_token
                },
                ['jellyseerr_url', 'jellyseerr_api_key', 'discord_bot_token'],
                'API Configuration'
            )
            
            # Validate URLs
            self.jellyseerr_url = ConfigValidator.validate_url(self.jellyseerr_url, "Jellyseerr")
            
            if self.radarr_url:
                self.radarr_url = ConfigValidator.validate_url(self.radarr_url, "Radarr")
            
            if self.sonarr_url:
                self.sonarr_url = ConfigValidator.validate_url(self.sonarr_url, "Sonarr")
            
            if self.sabnzbd_url:
                self.sabnzbd_url = ConfigValidator.validate_url(self.sabnzbd_url, "SABnzbd")
            
            # Validate API keys
            ConfigValidator.validate_api_key(self.jellyseerr_api_key, "Jellyseerr")
            ConfigValidator.validate_api_key(self.discord_bot_token, "Discord Bot", min_length=32)
            
            if self.nvidia_api_key:
                ConfigValidator.validate_api_key(self.nvidia_api_key, "NVIDIA")
                
        except ValidationError as e:
            raise ValueError(str(e))


@dataclass
class ChannelConfig:
    """Configuration for Discord channel mappings.
    
    Attributes:
        slinkbot_status: Channel ID for bot status messages
        request_status: Channel ID for request status updates
        movie_requests: Channel ID for movie requests
        tv_requests: Channel ID for TV show requests
        anime_requests: Channel ID for anime requests
        download_queue: Channel ID for download queue updates
        media_arrivals: Channel ID for new media notifications
        cancel_request: Channel ID for request cancellations
        service_alerts: Channel ID for service health alerts
    """
    
    slinkbot_status: int
    request_status: int
    movie_requests: int
    tv_requests: int
    anime_requests: int
    download_queue: int
    media_arrivals: int
    cancel_request: int
    service_alerts: int
    
    @classmethod
    def from_env(cls) -> 'ChannelConfig':
        """Load channel configuration from environment variables.
        
        Returns:
            ChannelConfig instance with values from environment
            
        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        try:
            return cls(
                slinkbot_status=int(os.getenv('CHANNEL_SLINKBOT_STATUS', '0')),
                request_status=int(os.getenv('CHANNEL_REQUEST_STATUS', '0')),
                movie_requests=int(os.getenv('CHANNEL_MOVIE_REQUESTS', '0')),
                tv_requests=int(os.getenv('CHANNEL_TV_REQUESTS', '0')),
                anime_requests=int(os.getenv('CHANNEL_ANIME_REQUESTS', '0')),
                download_queue=int(os.getenv('CHANNEL_DOWNLOAD_QUEUE', '0')),
                media_arrivals=int(os.getenv('CHANNEL_MEDIA_ARRIVALS', '0')),
                cancel_request=int(os.getenv('CHANNEL_CANCEL_REQUEST', '0')),
                service_alerts=int(os.getenv('CHANNEL_SERVICE_ALERTS', '0'))
            )
        except ValueError as e:
            raise ValueError(f"Invalid channel ID in environment variables: {e}")
    
    def validate(self) -> None:
        """Validate channel configuration.
        
        Raises:
            ValueError: If channel IDs are invalid
        """
        try:
            required_channels = {
                'slinkbot_status': self.slinkbot_status,
                'request_status': self.request_status,
                'movie_requests': self.movie_requests,
                'tv_requests': self.tv_requests,
                'anime_requests': self.anime_requests,
                'download_queue': self.download_queue,
                'media_arrivals': self.media_arrivals,
                'cancel_request': self.cancel_request,
                'service_alerts': self.service_alerts
            }
            
            # Validate each channel ID
            for channel_name, channel_id in required_channels.items():
                if channel_id == 0:
                    raise ValidationError(f"Missing required channel ID: {channel_name}")
                
                ConfigValidator.validate_channel_id(channel_id, channel_name)
                
        except ValidationError as e:
            raise ValueError(str(e))


@dataclass
class DatabaseConfig:
    """Configuration for database settings.
    
    Attributes:
        db_path: Path to SQLite database file
        backup_enabled: Whether to enable automatic backups
        backup_interval_hours: Hours between automatic backups
        max_backup_files: Maximum number of backup files to keep
    """
    
    db_path: str = "data/slinkbot.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_backup_files: int = 7
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Load database configuration from environment variables.
        
        Returns:
            DatabaseConfig instance with values from environment
        """
        return cls(
            db_path=os.getenv('DB_PATH', 'data/slinkbot.db'),
            backup_enabled=os.getenv('DB_BACKUP_ENABLED', 'true').lower() == 'true',
            backup_interval_hours=int(os.getenv('DB_BACKUP_INTERVAL_HOURS', '24')),
            max_backup_files=int(os.getenv('DB_MAX_BACKUP_FILES', '7'))
        )
    
    def validate(self) -> None:
        """Validate database configuration.
        
        Raises:
            ValueError: If configuration values are invalid
        """
        if not self.db_path:
            raise ValueError("Database path is required")
        
        if self.backup_interval_hours <= 0:
            raise ValueError("Backup interval must be positive")
        
        if self.max_backup_files <= 0:
            raise ValueError("Max backup files must be positive")
        
        # Ensure database directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class LoggingConfig:
    """Configuration for logging settings.
    
    Attributes:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        json_log_file: Path to JSON structured log file
        enable_console_output: Whether to output logs to console
        enable_json_logging: Whether to enable JSON structured logging
        max_log_size_mb: Maximum log file size in MB before rotation
        backup_count: Number of backup log files to keep
    """
    
    log_level: str = "INFO"
    log_file: str = "logs/slinkbot.log"
    json_log_file: str = "logs/slinkbot.json.log"
    enable_console_output: bool = True
    enable_json_logging: bool = True
    max_log_size_mb: int = 10
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Load logging configuration from environment variables.
        
        Returns:
            LoggingConfig instance with values from environment
        """
        return cls(
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file=os.getenv('LOG_FILE', 'logs/slinkbot.log'),
            json_log_file=os.getenv('JSON_LOG_FILE', 'logs/slinkbot.json.log'),
            enable_console_output=os.getenv('LOG_CONSOLE', 'true').lower() == 'true',
            enable_json_logging=os.getenv('LOG_JSON', 'true').lower() == 'true',
            max_log_size_mb=int(os.getenv('LOG_MAX_SIZE_MB', '10')),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5'))
        )
    
    def validate(self) -> None:
        """Validate logging configuration.
        
        Raises:
            ValueError: If configuration values are invalid
        """
        try:
            # Validate log level
            self.log_level = ConfigValidator.validate_log_level(self.log_level)
            
            # Validate positive integers
            ConfigValidator.validate_positive_integer(self.max_log_size_mb, "Max log size (MB)")
            ConfigValidator.validate_positive_integer(self.backup_count, "Backup count", min_value=0)
            
            # Ensure log directories exist
            for log_path in [self.log_file, self.json_log_file]:
                if log_path:
                    log_dir = Path(log_path).parent
                    ConfigValidator.validate_directory(
                        log_dir, f"Log directory for {log_path}", 
                        create_if_missing=True, check_writable=True
                    )
                    
        except ValidationError as e:
            raise ValueError(str(e))


class Config:
    """Main configuration class that aggregates all configuration sections.
    
    This class loads configuration from environment variables and provides
    validation for all configuration sections.
    
    Attributes:
        api: API configuration for external services
        channels: Discord channel mappings
        database: Database configuration
        logging: Logging configuration
    """
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.api = self._load_api_config()
        self.channels = ChannelConfig.from_env()
        self.database = DatabaseConfig.from_env()
        self.logging = LoggingConfig.from_env()
        
        # Validate all configuration sections
        self.validate()
    
    def _load_api_config(self) -> APIConfig:
        """Load API configuration from environment variables.
        
        Returns:
            APIConfig instance with values from environment
        """
        return APIConfig(
            jellyseerr_url=os.getenv('JELLYSEERR_URL', ''),
            jellyseerr_api_key=os.getenv('JELLYSEERR_API_KEY', ''),
            radarr_url=os.getenv('RADARR_URL', ''),
            radarr_api_key=os.getenv('RADARR_API_KEY', ''),
            sonarr_url=os.getenv('SONARR_URL', ''),
            sonarr_api_key=os.getenv('SONARR_API_KEY', ''),
            sabnzbd_url=os.getenv('SABNZBD_URL', ''),
            sabnzbd_api_key=os.getenv('SABNZBD_API_KEY', ''),
            discord_bot_token=os.getenv('DISCORD_BOT_TOKEN', ''),
            nvidia_api_key=os.getenv('NVIDIA_API_KEY', ''),
            nvidia_base_url=os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1'),
            nvidia_model=os.getenv('NVIDIA_MODEL', 'meta/llama-3.3-70b-instruct')
        )
    
    def validate(self) -> None:
        """Validate entire configuration.
        
        Raises:
            ValueError: If any configuration section is invalid
        """
        try:
            self.api.validate()
            self.channels.validate()
            self.database.validate()
            self.logging.validate()
        except ValueError as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format.
        
        Returns:
            Dictionary representation of configuration (excluding sensitive data)
        """
        return {
            'api': {
                'jellyseerr_url': self.api.jellyseerr_url,
                'radarr_url': self.api.radarr_url,
                'sonarr_url': self.api.sonarr_url,
                'sabnzbd_url': self.api.sabnzbd_url,
                # Exclude API keys and tokens for security
            },
            'channels': {
                'slinkbot_status': self.channels.slinkbot_status,
                'request_status': self.channels.request_status,
                'movie_requests': self.channels.movie_requests,
                'tv_requests': self.channels.tv_requests,
                'anime_requests': self.channels.anime_requests,
                'download_queue': self.channels.download_queue,
                'media_arrivals': self.channels.media_arrivals,
                'cancel_request': self.channels.cancel_request,
                'service_alerts': self.channels.service_alerts,
            },
            'database': {
                'db_path': self.database.db_path,
                'backup_enabled': self.database.backup_enabled,
                'backup_interval_hours': self.database.backup_interval_hours,
                'max_backup_files': self.database.max_backup_files,
            },
            'logging': {
                'log_level': self.logging.log_level,
                'log_file': self.logging.log_file,
                'json_log_file': self.logging.json_log_file,
                'enable_console_output': self.logging.enable_console_output,
                'enable_json_logging': self.logging.enable_json_logging,
                'max_log_size_mb': self.logging.max_log_size_mb,
                'backup_count': self.logging.backup_count,
            }
        }


def load_config() -> Config:
    """Load and validate configuration from environment variables.
    
    Returns:
        Validated Config instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    return Config() 
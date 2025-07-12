"""Unit tests for configuration management system."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from config.settings import (
    APIConfig, 
    ChannelConfig, 
    DatabaseConfig, 
    LoggingConfig, 
    Config,
    load_config
)


class TestAPIConfig:
    """Test cases for APIConfig class."""
    
    def test_api_config_creation(self):
        """Test creating APIConfig with valid data."""
        config = APIConfig(
            jellyseerr_url="https://jellyseerr.example.com",
            jellyseerr_api_key="test_key",
            discord_bot_token="discord_token"
        )
        
        assert config.jellyseerr_url == "https://jellyseerr.example.com"
        assert config.jellyseerr_api_key == "test_key"
        assert config.discord_bot_token == "discord_token"
        assert config.radarr_url == ""  # Default value
    
    def test_api_config_validation_success(self):
        """Test successful validation of APIConfig."""
        config = APIConfig(
            jellyseerr_url="https://jellyseerr.example.com",
            jellyseerr_api_key="test_key",
            discord_bot_token="discord_token"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_api_config_validation_missing_jellyseerr_url(self):
        """Test validation failure when Jellyseerr URL is missing."""
        config = APIConfig(
            jellyseerr_url="",
            jellyseerr_api_key="test_key",
            discord_bot_token="discord_token"
        )
        
        with pytest.raises(ValueError, match="Jellyseerr configuration incomplete"):
            config.validate()
    
    def test_api_config_validation_missing_jellyseerr_api_key(self):
        """Test validation failure when Jellyseerr API key is missing."""
        config = APIConfig(
            jellyseerr_url="https://jellyseerr.example.com",
            jellyseerr_api_key="",
            discord_bot_token="discord_token"
        )
        
        with pytest.raises(ValueError, match="Jellyseerr configuration incomplete"):
            config.validate()
    
    def test_api_config_validation_missing_discord_token(self):
        """Test validation failure when Discord token is missing."""
        config = APIConfig(
            jellyseerr_url="https://jellyseerr.example.com",
            jellyseerr_api_key="test_key",
            discord_bot_token=""
        )
        
        with pytest.raises(ValueError, match="Discord bot token is required"):
            config.validate()
    
    def test_api_config_validation_invalid_url_format(self):
        """Test validation failure with invalid URL format."""
        config = APIConfig(
            jellyseerr_url="invalid-url",
            jellyseerr_api_key="test_key",
            discord_bot_token="discord_token"
        )
        
        with pytest.raises(ValueError, match="must start with http://"):
            config.validate()
    
    def test_api_config_validation_optional_urls(self):
        """Test validation with optional service URLs."""
        config = APIConfig(
            jellyseerr_url="https://jellyseerr.example.com",
            jellyseerr_api_key="test_key",
            discord_bot_token="discord_token",
            radarr_url="https://radarr.example.com",
            sonarr_url="https://sonarr.example.com"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_api_config_validation_invalid_optional_url(self):
        """Test validation failure with invalid optional URL."""
        config = APIConfig(
            jellyseerr_url="https://jellyseerr.example.com",
            jellyseerr_api_key="test_key",
            discord_bot_token="discord_token",
            radarr_url="invalid-radarr-url"
        )
        
        with pytest.raises(ValueError, match="Radarr URL must start with http://"):
            config.validate()


class TestChannelConfig:
    """Test cases for ChannelConfig class."""
    
    def test_channel_config_from_env(self):
        """Test loading ChannelConfig from environment variables."""
        env_vars = {
            'CHANNEL_SLINKBOT_STATUS': '123456789',
            'CHANNEL_REQUEST_STATUS': '234567890',
            'CHANNEL_MOVIE_REQUESTS': '345678901',
            'CHANNEL_TV_REQUESTS': '456789012',
            'CHANNEL_ANIME_REQUESTS': '567890123',
            'CHANNEL_DOWNLOAD_QUEUE': '678901234',
            'CHANNEL_MEDIA_ARRIVALS': '789012345',
            'CHANNEL_CANCEL_REQUEST': '890123456',
            'CHANNEL_SERVICE_ALERTS': '901234567'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ChannelConfig.from_env()
            
            assert config.slinkbot_status == 123456789
            assert config.request_status == 234567890
            assert config.movie_requests == 345678901
            assert config.tv_requests == 456789012
            assert config.anime_requests == 567890123
            assert config.download_queue == 678901234
            assert config.media_arrivals == 789012345
            assert config.cancel_request == 890123456
            assert config.service_alerts == 901234567
    
    def test_channel_config_from_env_defaults(self):
        """Test ChannelConfig with default values when env vars are missing."""
        with patch.dict(os.environ, {}, clear=True):
            config = ChannelConfig.from_env()
            
            # All channels should default to 0
            assert config.slinkbot_status == 0
            assert config.request_status == 0
            assert config.movie_requests == 0
            assert config.tv_requests == 0
            assert config.anime_requests == 0
            assert config.download_queue == 0
            assert config.media_arrivals == 0
            assert config.cancel_request == 0
            assert config.service_alerts == 0
    
    def test_channel_config_from_env_invalid_values(self):
        """Test ChannelConfig with invalid environment values."""
        env_vars = {
            'CHANNEL_SLINKBOT_STATUS': 'invalid_number'
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError, match="Invalid channel ID"):
                ChannelConfig.from_env()
    
    def test_channel_config_validation_success(self):
        """Test successful validation of ChannelConfig."""
        config = ChannelConfig(
            slinkbot_status=123456789,
            request_status=234567890,
            movie_requests=345678901,
            tv_requests=456789012,
            anime_requests=567890123,
            download_queue=678901234,
            media_arrivals=789012345,
            cancel_request=890123456,
            service_alerts=901234567
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_channel_config_validation_missing_channels(self):
        """Test validation failure with missing channel IDs."""
        config = ChannelConfig(
            slinkbot_status=0,  # Invalid
            request_status=234567890,
            movie_requests=345678901,
            tv_requests=456789012,
            anime_requests=567890123,
            download_queue=678901234,
            media_arrivals=789012345,
            cancel_request=890123456,
            service_alerts=901234567
        )
        
        with pytest.raises(ValueError, match="Missing required channel IDs"):
            config.validate()
    
    def test_channel_config_validation_negative_channels(self):
        """Test validation failure with negative channel IDs."""
        config = ChannelConfig(
            slinkbot_status=-1,  # Invalid
            request_status=234567890,
            movie_requests=345678901,
            tv_requests=456789012,
            anime_requests=567890123,
            download_queue=678901234,
            media_arrivals=789012345,
            cancel_request=890123456,
            service_alerts=901234567
        )
        
        with pytest.raises(ValueError, match="Invalid channel IDs"):
            config.validate()


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""
    
    def test_database_config_defaults(self):
        """Test DatabaseConfig with default values."""
        config = DatabaseConfig()
        
        assert config.db_path == "data/slinkbot.db"
        assert config.backup_enabled is True
        assert config.backup_interval_hours == 24
        assert config.max_backup_files == 7
    
    def test_database_config_from_env(self):
        """Test loading DatabaseConfig from environment variables."""
        env_vars = {
            'DB_PATH': '/custom/path/db.sqlite',
            'DB_BACKUP_ENABLED': 'false',
            'DB_BACKUP_INTERVAL_HOURS': '12',
            'DB_MAX_BACKUP_FILES': '5'
        }
        
        with patch.dict(os.environ, env_vars):
            config = DatabaseConfig.from_env()
            
            assert config.db_path == '/custom/path/db.sqlite'
            assert config.backup_enabled is False
            assert config.backup_interval_hours == 12
            assert config.max_backup_files == 5
    
    def test_database_config_validation_success(self):
        """Test successful validation of DatabaseConfig."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DatabaseConfig(
                db_path=f"{temp_dir}/test.db",
                backup_enabled=True,
                backup_interval_hours=24,
                max_backup_files=7
            )
            
            # Should not raise any exception
            config.validate()
    
    def test_database_config_validation_empty_path(self):
        """Test validation failure with empty database path."""
        config = DatabaseConfig(
            db_path="",
            backup_enabled=True,
            backup_interval_hours=24,
            max_backup_files=7
        )
        
        with pytest.raises(ValueError, match="Database path is required"):
            config.validate()
    
    def test_database_config_validation_invalid_interval(self):
        """Test validation failure with invalid backup interval."""
        config = DatabaseConfig(
            db_path="test.db",
            backup_enabled=True,
            backup_interval_hours=0,  # Invalid
            max_backup_files=7
        )
        
        with pytest.raises(ValueError, match="Backup interval must be positive"):
            config.validate()
    
    def test_database_config_validation_invalid_backup_files(self):
        """Test validation failure with invalid max backup files."""
        config = DatabaseConfig(
            db_path="test.db",
            backup_enabled=True,
            backup_interval_hours=24,
            max_backup_files=0  # Invalid
        )
        
        with pytest.raises(ValueError, match="Max backup files must be positive"):
            config.validate()


class TestLoggingConfig:
    """Test cases for LoggingConfig class."""
    
    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        config = LoggingConfig()
        
        assert config.log_level == "INFO"
        assert config.log_file == "logs/slinkbot.log"
        assert config.json_log_file == "logs/slinkbot.json.log"
        assert config.enable_console_output is True
        assert config.enable_json_logging is True
        assert config.max_log_size_mb == 10
        assert config.backup_count == 5
    
    def test_logging_config_from_env(self):
        """Test loading LoggingConfig from environment variables."""
        env_vars = {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE': '/custom/app.log',
            'JSON_LOG_FILE': '/custom/app.json.log',
            'LOG_CONSOLE': 'false',
            'LOG_JSON': 'false',
            'LOG_MAX_SIZE_MB': '20',
            'LOG_BACKUP_COUNT': '10'
        }
        
        with patch.dict(os.environ, env_vars):
            config = LoggingConfig.from_env()
            
            assert config.log_level == "DEBUG"
            assert config.log_file == "/custom/app.log"
            assert config.json_log_file == "/custom/app.json.log"
            assert config.enable_console_output is False
            assert config.enable_json_logging is False
            assert config.max_log_size_mb == 20
            assert config.backup_count == 10
    
    def test_logging_config_validation_success(self):
        """Test successful validation of LoggingConfig."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                log_level="INFO",
                log_file=f"{temp_dir}/test.log",
                json_log_file=f"{temp_dir}/test.json.log",
                enable_console_output=True,
                enable_json_logging=True,
                max_log_size_mb=10,
                backup_count=5
            )
            
            # Should not raise any exception
            config.validate()
    
    def test_logging_config_validation_invalid_level(self):
        """Test validation failure with invalid log level."""
        config = LoggingConfig(
            log_level="INVALID",
            log_file="test.log",
            json_log_file="test.json.log",
            enable_console_output=True,
            enable_json_logging=True,
            max_log_size_mb=10,
            backup_count=5
        )
        
        with pytest.raises(ValueError, match="Invalid log level"):
            config.validate()
    
    def test_logging_config_validation_invalid_size(self):
        """Test validation failure with invalid max log size."""
        config = LoggingConfig(
            log_level="INFO",
            log_file="test.log",
            json_log_file="test.json.log",
            enable_console_output=True,
            enable_json_logging=True,
            max_log_size_mb=0,  # Invalid
            backup_count=5
        )
        
        with pytest.raises(ValueError, match="Max log size must be positive"):
            config.validate()
    
    def test_logging_config_validation_invalid_backup_count(self):
        """Test validation failure with negative backup count."""
        config = LoggingConfig(
            log_level="INFO",
            log_file="test.log",
            json_log_file="test.json.log",
            enable_console_output=True,
            enable_json_logging=True,
            max_log_size_mb=10,
            backup_count=-1  # Invalid
        )
        
        with pytest.raises(ValueError, match="Backup count cannot be negative"):
            config.validate()


class TestConfig:
    """Test cases for main Config class."""
    
    def test_config_initialization(self):
        """Test Config initialization with environment variables."""
        env_vars = {
            # API config
            'JELLYSEERR_URL': 'https://jellyseerr.example.com',
            'JELLYSEERR_API_KEY': 'test_api_key',
            'DISCORD_BOT_TOKEN': 'discord_token',
            
            # Channel config
            'CHANNEL_SLINKBOT_STATUS': '123456789',
            'CHANNEL_REQUEST_STATUS': '234567890',
            'CHANNEL_MOVIE_REQUESTS': '345678901',
            'CHANNEL_TV_REQUESTS': '456789012',
            'CHANNEL_ANIME_REQUESTS': '567890123',
            'CHANNEL_DOWNLOAD_QUEUE': '678901234',
            'CHANNEL_MEDIA_ARRIVALS': '789012345',
            'CHANNEL_CANCEL_REQUEST': '890123456',
            'CHANNEL_SERVICE_ALERTS': '901234567',
            
            # Database config
            'DB_PATH': 'test.db',
            
            # Logging config
            'LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars):
            with tempfile.TemporaryDirectory() as temp_dir:
                # Patch the database path to use temp directory
                with patch.object(DatabaseConfig, 'from_env') as mock_db_config:
                    mock_db_config.return_value = DatabaseConfig(
                        db_path=f"{temp_dir}/test.db"
                    )
                    
                    config = Config()
                    
                    # Verify API configuration
                    assert config.api.jellyseerr_url == 'https://jellyseerr.example.com'
                    assert config.api.jellyseerr_api_key == 'test_api_key'
                    assert config.api.discord_bot_token == 'discord_token'
                    
                    # Verify channel configuration
                    assert config.channels.slinkbot_status == 123456789
                    assert config.channels.request_status == 234567890
                    
                    # Verify database configuration
                    assert config.database.db_path == f"{temp_dir}/test.db"
                    
                    # Verify logging configuration
                    assert config.logging.log_level == 'DEBUG'
    
    def test_config_validation_failure(self):
        """Test Config validation failure."""
        env_vars = {
            'JELLYSEERR_URL': '',  # Invalid - empty URL
            'JELLYSEERR_API_KEY': 'test_api_key',
            'DISCORD_BOT_TOKEN': 'discord_token',
            'CHANNEL_SLINKBOT_STATUS': '123456789',
            'CHANNEL_REQUEST_STATUS': '234567890',
            'CHANNEL_MOVIE_REQUESTS': '345678901',
            'CHANNEL_TV_REQUESTS': '456789012',
            'CHANNEL_ANIME_REQUESTS': '567890123',
            'CHANNEL_DOWNLOAD_QUEUE': '678901234',
            'CHANNEL_MEDIA_ARRIVALS': '789012345',
            'CHANNEL_CANCEL_REQUEST': '890123456',
            'CHANNEL_SERVICE_ALERTS': '901234567'
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config()
    
    def test_config_to_dict(self):
        """Test Config to_dict method excludes sensitive data."""
        env_vars = {
            'JELLYSEERR_URL': 'https://jellyseerr.example.com',
            'JELLYSEERR_API_KEY': 'secret_key',
            'DISCORD_BOT_TOKEN': 'secret_token',
            'CHANNEL_SLINKBOT_STATUS': '123456789',
            'CHANNEL_REQUEST_STATUS': '234567890',
            'CHANNEL_MOVIE_REQUESTS': '345678901',
            'CHANNEL_TV_REQUESTS': '456789012',
            'CHANNEL_ANIME_REQUESTS': '567890123',
            'CHANNEL_DOWNLOAD_QUEUE': '678901234',
            'CHANNEL_MEDIA_ARRIVALS': '789012345',
            'CHANNEL_CANCEL_REQUEST': '890123456',
            'CHANNEL_SERVICE_ALERTS': '901234567'
        }
        
        with patch.dict(os.environ, env_vars):
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch.object(DatabaseConfig, 'from_env') as mock_db_config:
                    mock_db_config.return_value = DatabaseConfig(
                        db_path=f"{temp_dir}/test.db"
                    )
                    
                    config = Config()
                    config_dict = config.to_dict()
                    
                    # Should include URLs but not API keys/tokens
                    assert 'api' in config_dict
                    assert config_dict['api']['jellyseerr_url'] == 'https://jellyseerr.example.com'
                    assert 'jellyseerr_api_key' not in config_dict['api']
                    assert 'discord_bot_token' not in config_dict['api']
                    
                    # Should include all channel IDs
                    assert 'channels' in config_dict
                    assert config_dict['channels']['slinkbot_status'] == 123456789
                    
                    # Should include database and logging configs
                    assert 'database' in config_dict
                    assert 'logging' in config_dict


class TestLoadConfig:
    """Test cases for load_config function."""
    
    def test_load_config_success(self):
        """Test successful config loading."""
        env_vars = {
            'JELLYSEERR_URL': 'https://jellyseerr.example.com',
            'JELLYSEERR_API_KEY': 'test_api_key',
            'DISCORD_BOT_TOKEN': 'discord_token',
            'CHANNEL_SLINKBOT_STATUS': '123456789',
            'CHANNEL_REQUEST_STATUS': '234567890',
            'CHANNEL_MOVIE_REQUESTS': '345678901',
            'CHANNEL_TV_REQUESTS': '456789012',
            'CHANNEL_ANIME_REQUESTS': '567890123',
            'CHANNEL_DOWNLOAD_QUEUE': '678901234',
            'CHANNEL_MEDIA_ARRIVALS': '789012345',
            'CHANNEL_CANCEL_REQUEST': '890123456',
            'CHANNEL_SERVICE_ALERTS': '901234567'
        }
        
        with patch.dict(os.environ, env_vars):
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch.object(DatabaseConfig, 'from_env') as mock_db_config:
                    mock_db_config.return_value = DatabaseConfig(
                        db_path=f"{temp_dir}/test.db"
                    )
                    
                    config = load_config()
                    assert isinstance(config, Config)
    
    def test_load_config_validation_error(self):
        """Test config loading with validation error."""
        env_vars = {
            'JELLYSEERR_URL': '',  # Invalid
            'JELLYSEERR_API_KEY': 'test_api_key',
            'DISCORD_BOT_TOKEN': 'discord_token'
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError):
                load_config() 
"""Unit tests for logging configuration system."""

import json
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import StringIO

from config.settings import LoggingConfig
from utils.logging_config import (
    JSONFormatter,
    StructuredLogger,
    setup_logging,
    get_logger,
    LogContext,
    log_function_performance,
    log_api_metrics,
    log_user_action
)


class TestJSONFormatter:
    """Test cases for JSONFormatter class."""
    
    def test_json_formatter_basic_record(self):
        """Test formatting basic log record to JSON."""
        formatter = JSONFormatter()
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert log_data["message"] == "Test message"
        assert log_data["thread"] == 12345
        assert log_data["thread_name"] == "MainThread"
        assert "timestamp" in log_data
        assert log_data["timestamp"].endswith("Z")
    
    def test_json_formatter_with_extra_fields(self):
        """Test formatting log record with extra fields."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        
        # Add extra fields
        record.user_id = 123456789
        record.channel_id = 987654321
        record.service = "jellyseerr"
        record.execution_time = 1.234
        record.status_code = 200
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["user_id"] == 123456789
        assert log_data["channel_id"] == 987654321
        assert log_data["service"] == "jellyseerr"
        assert log_data["execution_time"] == 1.234
        assert log_data["status_code"] == 200
    
    def test_json_formatter_with_context_fields(self):
        """Test formatting log record with context fields."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        
        # Add context fields (with ctx_ prefix)
        record.ctx_operation = "media_search"
        record.ctx_request_id = "req-123"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["operation"] == "media_search"
        assert log_data["request_id"] == "req-123"
    
    def test_json_formatter_with_exception(self):
        """Test formatting log record with exception information."""
        formatter = JSONFormatter(include_traceback=True)
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Capture the actual exception info, not just True
            import sys
            exc_info = sys.exc_info()
        else:
            exc_info = None
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=exc_info
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]
    
    def test_json_formatter_without_traceback(self):
        """Test formatting log record without traceback when disabled."""
        formatter = JSONFormatter(include_traceback=False)
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Capture the actual exception info, not just True
            import sys
            exc_info = sys.exc_info()
        else:
            exc_info = None
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=exc_info
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        # Exception info should not be included
        assert "exception" not in log_data


class TestStructuredLogger:
    """Test cases for StructuredLogger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = StructuredLogger("test.logger")
    
    def test_structured_logger_debug(self):
        """Test debug logging with context."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.debug("Debug message", user_id=123, action="test")
            
            mock_log.assert_called_once_with(
                logging.DEBUG, 
                "Debug message", 
                extra={"user_id": 123, "action": "test"}
            )
    
    def test_structured_logger_info(self):
        """Test info logging with context."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.info("Info message", service="jellyseerr")
            
            mock_log.assert_called_once_with(
                logging.INFO, 
                "Info message", 
                extra={"service": "jellyseerr"}
            )
    
    def test_structured_logger_warning(self):
        """Test warning logging with context."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.warning("Warning message", error_count=3)
            
            mock_log.assert_called_once_with(
                logging.WARNING, 
                "Warning message", 
                extra={"error_count": 3}
            )
    
    def test_structured_logger_error(self):
        """Test error logging with context."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.error("Error message", status_code=500)
            
            mock_log.assert_called_once_with(
                logging.ERROR, 
                "Error message", 
                extra={"status_code": 500}
            )
    
    def test_structured_logger_critical(self):
        """Test critical logging with context."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.critical("Critical message", system="database")
            
            mock_log.assert_called_once_with(
                logging.CRITICAL, 
                "Critical message", 
                extra={"system": "database"}
            )
    
    def test_structured_logger_exception(self):
        """Test exception logging with context."""
        with patch.object(self.logger.logger, 'exception') as mock_exception:
            self.logger.exception("Exception occurred", user_id=123)
            
            mock_exception.assert_called_once_with(
                "Exception occurred", 
                extra={"user_id": 123}
            )
    
    def test_structured_logger_discord_interaction(self):
        """Test Discord interaction logging."""
        mock_interaction = MagicMock()
        mock_interaction.user.id = 123456789
        mock_interaction.channel_id = 987654321
        mock_interaction.guild_id = 111222333
        mock_interaction.guild = MagicMock()
        mock_interaction.data = {"name": "test_command"}
        
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.discord_interaction(
                logging.INFO, 
                "Command executed", 
                mock_interaction,
                result="success"
            )
            
            expected_context = {
                "user_id": 123456789,
                "channel_id": 987654321,
                "guild_id": 111222333,
                "command": "test_command",
                "result": "success"
            }
            
            mock_log.assert_called_once_with(
                logging.INFO, 
                "Command executed", 
                extra=expected_context
            )
    
    def test_structured_logger_api_call(self):
        """Test API call logging."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.api_call(
                logging.INFO,
                "API request completed",
                service="jellyseerr",
                url="/api/v1/search",
                status_code=200,
                execution_time=0.45,
                query="test movie"
            )
            
            expected_context = {
                "service": "jellyseerr",
                "url": "/api/v1/search",
                "status_code": 200,
                "execution_time": 0.45,
                "query": "test movie"
            }
            
            mock_log.assert_called_once_with(
                logging.INFO, 
                "API request completed", 
                extra=expected_context
            )
    
    def test_structured_logger_media_request(self):
        """Test media request logging."""
        with patch.object(self.logger.logger, 'log') as mock_log:
            self.logger.media_request(
                logging.INFO,
                "Media request submitted",
                user_id=123456789,
                media_title="Test Movie",
                media_type="movie",
                request_id=42,
                status="pending"
            )
            
            expected_context = {
                "user_id": 123456789,
                "media_title": "Test Movie",
                "media_type": "movie",
                "request_id": 42,
                "status": "pending"
            }
            
            mock_log.assert_called_once_with(
                logging.INFO, 
                "Media request submitted", 
                extra=expected_context
            )


class TestSetupLogging:
    """Test cases for setup_logging function."""
    
    def test_setup_logging_with_config(self):
        """Test logging setup with custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                log_level="DEBUG",
                log_file=f"{temp_dir}/test.log",
                json_log_file=f"{temp_dir}/test.json.log",
                enable_console_output=True,
                enable_json_logging=True,
                max_log_size_mb=5,
                backup_count=3
            )
            
            # Clear any existing handlers
            root_logger = logging.getLogger()
            root_logger.handlers.clear()
            
            setup_logging(config)
            
            # Verify root logger level
            assert root_logger.level == logging.DEBUG
            
            # Verify handlers were added
            assert len(root_logger.handlers) >= 1  # At least console handler
            
            # Verify log files were created
            assert Path(config.log_file).parent.exists()
            assert Path(config.json_log_file).parent.exists()
    
    def test_setup_logging_console_only(self):
        """Test logging setup with console output only."""
        config = LoggingConfig(
            log_level="INFO",
            log_file="",  # Disable file logging
            json_log_file="",  # Disable JSON logging
            enable_console_output=True,
            enable_json_logging=False
        )
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        setup_logging(config)
        
        # Should have at least one handler (console)
        assert len(root_logger.handlers) >= 1
        
        # Find console handler
        console_handlers = [
            h for h in root_logger.handlers 
            if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
        ]
        assert len(console_handlers) == 1
    
    def test_setup_logging_no_console(self):
        """Test logging setup without console output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                log_level="INFO",
                log_file=f"{temp_dir}/test.log",
                json_log_file=f"{temp_dir}/test.json.log",
                enable_console_output=False,
                enable_json_logging=True
            )
            
            # Clear any existing handlers
            root_logger = logging.getLogger()
            root_logger.handlers.clear()
            
            setup_logging(config)
            
            # Should not have console handler
            console_handlers = [
                h for h in root_logger.handlers 
                if isinstance(h, logging.StreamHandler) and h.stream.name == '<stdout>'
            ]
            assert len(console_handlers) == 0
    
    def test_setup_logging_default_config(self):
        """Test logging setup with default configuration."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        setup_logging()  # Use default config
        
        # Should set up logging with defaults
        assert root_logger.level == logging.INFO


class TestGetLogger:
    """Test cases for get_logger function."""
    
    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns StructuredLogger instance."""
        logger = get_logger("test.module")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == "test.module"
    
    def test_get_logger_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("module.one")
        logger2 = get_logger("module.two")
        
        assert logger1.logger.name == "module.one"
        assert logger2.logger.name == "module.two"
        assert logger1.logger != logger2.logger


class TestLogContext:
    """Test cases for LogContext context manager."""
    
    def test_log_context_adds_fields(self):
        """Test that LogContext adds context fields to log records."""
        # Capture log records
        captured_records = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                captured_records.append(record)
        
        # Set up logger with test handler
        logger = logging.getLogger("test.context")
        handler = TestHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test logging with context
        with LogContext(user_id=123, operation="test"):
            logger.info("Test message")
        
        # Verify context was added
        assert len(captured_records) == 1
        record = captured_records[0]
        assert hasattr(record, 'ctx_user_id')
        assert hasattr(record, 'ctx_operation')
        assert record.ctx_user_id == 123
        assert record.ctx_operation == "test"
        
        # Clean up
        logger.removeHandler(handler)
    
    def test_log_context_restores_factory(self):
        """Test that LogContext restores original record factory."""
        original_factory = logging.getLogRecordFactory()
        
        with LogContext(test_field="test_value"):
            # Factory should be different inside context
            assert logging.getLogRecordFactory() != original_factory
        
        # Factory should be restored outside context
        assert logging.getLogRecordFactory() == original_factory


class TestLogUtilityFunctions:
    """Test cases for logging utility functions."""
    
    def test_log_function_performance(self):
        """Test log_function_performance function."""
        with patch('utils.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_function_performance(
                func_name="test_function",
                execution_time=1.234,
                success=True,
                user_id=123
            )
            
            mock_get_logger.assert_called_once_with('slinkbot.performance')
            mock_logger._log_with_context.assert_called_once_with(
                logging.INFO,
                "Function test_function completed in 1.234s",
                function="test_function",
                execution_time=1.234,
                success=True,
                user_id=123
            )
    
    def test_log_function_performance_failure(self):
        """Test log_function_performance with failure."""
        with patch('utils.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_function_performance(
                func_name="test_function",
                execution_time=0.5,
                success=False,
                error="Test error"
            )
            
            mock_logger._log_with_context.assert_called_once_with(
                logging.ERROR,
                "Function test_function failed in 0.500s",
                function="test_function",
                execution_time=0.5,
                success=False,
                error="Test error"
            )
    
    def test_log_api_metrics_success(self):
        """Test log_api_metrics with successful response."""
        with patch('utils.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_api_metrics(
                service="jellyseerr",
                endpoint="/api/v1/search",
                method="GET",
                status_code=200,
                response_time=0.45,
                query="test"
            )
            
            mock_get_logger.assert_called_once_with('slinkbot.api_metrics')
            mock_logger._log_with_context.assert_called_once_with(
                logging.INFO,
                "jellyseerr API GET /api/v1/search -> 200 (0.450s)",
                service="jellyseerr",
                endpoint="/api/v1/search",
                method="GET",
                status_code=200,
                response_time=0.45,
                query="test"
            )
    
    def test_log_api_metrics_error(self):
        """Test log_api_metrics with error response."""
        with patch('utils.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_api_metrics(
                service="jellyseerr",
                endpoint="/api/v1/request",
                method="POST",
                status_code=500,
                response_time=2.1
            )
            
            mock_logger._log_with_context.assert_called_once_with(
                logging.ERROR,
                "jellyseerr API POST /api/v1/request -> 500 (2.100s)",
                service="jellyseerr",
                endpoint="/api/v1/request",
                method="POST",
                status_code=500,
                response_time=2.1
            )
    
    def test_log_user_action(self):
        """Test log_user_action function."""
        with patch('utils.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_user_action(
                user_id=123456789,
                action="request_movie",
                channel_id=987654321,
                guild_id=111222333,
                media_title="Test Movie"
            )
            
            mock_get_logger.assert_called_once_with('slinkbot.user_actions')
            mock_logger.info.assert_called_once_with(
                "User 123456789 performed action: request_movie",
                user_id=123456789,
                action="request_movie",
                channel_id=987654321,
                guild_id=111222333,
                media_title="Test Movie"
            )
    
    def test_log_user_action_minimal(self):
        """Test log_user_action with minimal parameters."""
        with patch('utils.logging_config.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_user_action(
                user_id=123456789,
                action="status_check"
            )
            
            mock_logger.info.assert_called_once_with(
                "User 123456789 performed action: status_check",
                user_id=123456789,
                action="status_check"
            ) 
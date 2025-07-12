"""Structured logging configuration for SlinkBot.

This module provides comprehensive logging setup with JSON formatting,
rotation, and structured log entries for better observability.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import LoggingConfig


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.
    
    This formatter converts log records to JSON format with additional
    context fields and standardized structure for better log analysis.
    """
    
    def __init__(self, include_traceback: bool = True):
        """Initialize JSON formatter.
        
        Args:
            include_traceback: Whether to include traceback in exception logs
        """
        super().__init__()
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log entry
        """
        # Base log entry structure
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception information if present
        if record.exc_info and self.include_traceback:
            # Handle both tuple (processed exc_info) and boolean True (raw exc_info)
            if isinstance(record.exc_info, tuple):
                exc_info = record.exc_info
            elif record.exc_info is True:
                # Get current exception info
                import sys
                exc_info = sys.exc_info()
            else:
                exc_info = None
                
            if exc_info and exc_info[0] is not None:
                log_entry['exception'] = {
                    'type': exc_info[0].__name__ if exc_info[0] else None,
                    'message': str(exc_info[1]) if exc_info[1] else None,
                    'traceback': self.formatException(exc_info) if exc_info else None
                }
        
        # Add custom fields from extra parameters using getattr for type safety
        custom_fields = [
            'user_id', 'channel_id', 'guild_id', 'service', 'function', 
            'execution_time', 'status_code', 'url', 'error_type', 
            'request_id', 'media_type', 'media_title'
        ]
        
        for field in custom_fields:
            value = getattr(record, field, None)
            if value is not None:
                # Use function_name instead of function to avoid conflict with built-in
                key = 'function_name' if field == 'function' else field
                log_entry[key] = value
        
        # Add any additional context fields
        for key, value in record.__dict__.items():
            if key.startswith('ctx_'):
                log_entry[key[4:]] = value  # Remove 'ctx_' prefix
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """Enhanced logger with structured logging capabilities.
    
    This class provides convenience methods for logging with structured
    context and standard fields.
    """
    
    def __init__(self, name: str):
        """Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
    
    def _log_with_context(self, level: int, message: str, **context) -> None:
        """Log message with structured context.
        
        Args:
            level: Logging level
            message: Log message
            **context: Additional context fields
        """
        self.logger.log(level, message, extra=context)
    
    def debug(self, message: str, **context) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **context)
    
    def info(self, message: str, **context) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **context)
    
    def warning(self, message: str, **context) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **context)
    
    def error(self, message: str, **context) -> None:
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **context)
    
    def critical(self, message: str, **context) -> None:
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **context)
    
    def exception(self, message: str, **context) -> None:
        """Log exception with context and traceback."""
        self.logger.exception(message, extra=context)
    
    def discord_interaction(self, level: int, message: str, interaction, **context) -> None:
        """Log Discord interaction with automatic context extraction.
        
        Args:
            level: Logging level
            message: Log message
            interaction: Discord interaction object
            **context: Additional context fields
        """
        discord_context = {
            'user_id': interaction.user.id,
            'channel_id': interaction.channel_id,
            'guild_id': interaction.guild_id if interaction.guild else None,
            'command': interaction.data.get('name') if hasattr(interaction, 'data') else None
        }
        discord_context.update(context)
        self._log_with_context(level, message, **discord_context)
    
    def api_call(self, level: int, message: str, service: str, url: Optional[str] = None, 
                 status_code: Optional[int] = None, execution_time: Optional[float] = None, **context) -> None:
        """Log API call with structured context.
        
        Args:
            level: Logging level
            message: Log message
            service: Name of the service
            url: API endpoint URL
            status_code: HTTP response status code
            execution_time: Request execution time in seconds
            **context: Additional context fields
        """
        api_context: Dict[str, Any] = {'service': service}
        if url:
            api_context['url'] = url
        if status_code is not None:
            api_context['status_code'] = status_code
        if execution_time is not None:
            api_context['execution_time'] = execution_time
        
        api_context.update(context)
        self._log_with_context(level, message, **api_context)
    
    def media_request(self, level: int, message: str, user_id: int, media_title: str,
                     media_type: str, request_id: Optional[int] = None, **context) -> None:
        """Log media request with structured context.
        
        Args:
            level: Logging level
            message: Log message
            user_id: Discord user ID
            media_title: Title of requested media
            media_type: Type of media (movie, tv, anime)
            request_id: Internal request ID
            **context: Additional context fields
        """
        media_context = {
            'user_id': user_id,
            'media_title': media_title,
            'media_type': media_type
        }
        if request_id is not None:
            media_context['request_id'] = request_id
        
        media_context.update(context)
        self._log_with_context(level, message, **media_context)


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """Configure application logging with structured output.
    
    This function sets up comprehensive logging including:
    - Console output with colored formatting
    - File output with rotation
    - JSON structured logging
    - Proper log levels and formatters
    
    Args:
        config: Logging configuration object. If None, uses default settings.
    """
    if config is None:
        config = LoggingConfig()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Standard formatter for console output
    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Colored formatter for console (if colorlog is available)
    try:
        import colorlog  # type: ignore
        colored_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    except ImportError:
        colored_formatter = console_formatter
    
    # Console handler
    if config.enable_console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(colored_formatter)
        console_handler.setLevel(getattr(logging, config.log_level))
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.log_file:
        # Ensure log directory exists
        log_dir = Path(config.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file,
            maxBytes=config.max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(console_formatter)
        file_handler.setLevel(getattr(logging, config.log_level))
        root_logger.addHandler(file_handler)
    
    # JSON structured logging handler
    if config.enable_json_logging and config.json_log_file:
        # Ensure JSON log directory exists
        json_log_dir = Path(config.json_log_file).parent
        json_log_dir.mkdir(parents=True, exist_ok=True)
        
        json_handler = logging.handlers.RotatingFileHandler(
            filename=config.json_log_file,
            maxBytes=config.max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(getattr(logging, config.log_level))
        
        # Create separate logger for JSON output to avoid duplication
        json_logger = logging.getLogger('slinkbot.structured')
        json_logger.addHandler(json_handler)
        json_logger.setLevel(getattr(logging, config.log_level))
        json_logger.propagate = False  # Don't propagate to root logger
    
    # Configure third-party loggers to reduce noise
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log the logging configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            'log_level': config.log_level,
            'console_output': config.enable_console_output,
            'file_logging': bool(config.log_file),
            'json_logging': config.enable_json_logging,
            'log_file': config.log_file,
            'json_log_file': config.json_log_file
        }
    )


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name, typically __name__
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


class LogContext:
    """Context manager for adding context to all log messages within a block.
    
    This context manager automatically adds specified context fields to all
    log messages generated within its scope.
    
    Example:
        with LogContext(user_id=123, operation="media_search"):
            logger.info("Starting search")  # Will include user_id and operation
            # ... more operations
            logger.info("Search completed")  # Will also include context
    """
    
    def __init__(self, **context):
        """Initialize log context.
        
        Args:
            **context: Key-value pairs to add to all log messages
        """
        self.context = {f'ctx_{k}': v for k, v in context.items()}
        self.old_factory = None
    
    def __enter__(self):
        """Enter the context manager."""
        # Store the old record factory
        self.old_factory = logging.getLogRecordFactory()
        
        # Create new factory that adds our context
        def record_factory(*args, **kwargs):
            # Use the old factory if it exists, otherwise use the default
            if self.old_factory is not None:
                record = self.old_factory(*args, **kwargs)
            else:
                record = logging.LogRecord(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        # Set the new factory
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        # Restore the old record factory
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


def log_function_performance(func_name: str, execution_time: float, 
                           success: bool = True, **context) -> None:
    """Log function performance metrics.
    
    Args:
        func_name: Name of the function
        execution_time: Execution time in seconds
        success: Whether the function completed successfully
        **context: Additional context fields
    """
    logger = get_logger('slinkbot.performance')
    
    level = logging.INFO if success else logging.ERROR
    message = f"Function {func_name} {'completed' if success else 'failed'} in {execution_time:.3f}s"
    
    performance_context = {
        'function': func_name,
        'execution_time': execution_time,
        'success': success
    }
    performance_context.update(context)
    
    logger._log_with_context(level, message, **performance_context)


def log_api_metrics(service: str, endpoint: str, method: str, status_code: int,
                   response_time: float, **context) -> None:
    """Log API call metrics.
    
    Args:
        service: Name of the service
        endpoint: API endpoint
        method: HTTP method
        status_code: Response status code
        response_time: Response time in seconds
        **context: Additional context fields
    """
    logger = get_logger('slinkbot.api_metrics')
    
    level = logging.INFO if 200 <= status_code < 400 else logging.ERROR
    message = f"{service} API {method} {endpoint} -> {status_code} ({response_time:.3f}s)"
    
    api_context = {
        'service': service,
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'response_time': response_time
    }
    api_context.update(context)
    
    logger._log_with_context(level, message, **api_context)


def log_user_action(user_id: int, action: str, channel_id: Optional[int] = None, 
                   guild_id: Optional[int] = None, **context) -> None:
    """Log user actions for audit purposes.
    
    Args:
        user_id: Discord user ID
        action: Description of the action
        channel_id: Discord channel ID
        guild_id: Discord guild ID
        **context: Additional context fields
    """
    logger = get_logger('slinkbot.user_actions')
    
    message = f"User {user_id} performed action: {action}"
    
    user_context = {
        'user_id': user_id,
        'action': action
    }
    if channel_id is not None:
        user_context['channel_id'] = channel_id
    if guild_id is not None:
        user_context['guild_id'] = guild_id
    
    user_context.update(context)
    
    logger.info(message, **user_context) 
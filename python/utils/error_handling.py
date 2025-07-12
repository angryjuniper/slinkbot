"""
Enhanced error handling utilities for SlinkBot.
Provides graceful handling of unfindable media, timeouts, and service failures.
"""

import asyncio
import functools
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, Callable, TypeVar
from enum import Enum
import traceback

from utils.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class ErrorType(Enum):
    """Types of errors that can occur during media requests."""
    MEDIA_NOT_FOUND = "media_not_found"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"
    PERMISSION_ERROR = "permission_error"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    DUPLICATE_REQUEST = "duplicate_request"
    UNKNOWN_ERROR = "unknown_error"


class MediaRequestError(Exception):
    """Custom exception for media request errors."""
    
    def __init__(self, error_type: ErrorType, message: str, retryable: bool = True, 
                 retry_delay: int = 300, context: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        self.retry_delay = retry_delay  # Seconds
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class ErrorHandler:
    """Centralized error handling for media requests."""
    
    def __init__(self):
        self.error_patterns = {
            ErrorType.MEDIA_NOT_FOUND: [
                "not found", "404", "does not exist", "no results",
                "media not available", "content not found"
            ],
            ErrorType.SERVICE_UNAVAILABLE: [
                "service unavailable", "503", "502", "connection refused",
                "timeout", "server error"
            ],
            ErrorType.TIMEOUT: [
                "timeout", "time out", "timed out", "connection timeout"
            ],
            ErrorType.NETWORK_ERROR: [
                "network error", "connection error", "dns", "unreachable"
            ],
            ErrorType.AUTHENTICATION_ERROR: [
                "401", "unauthorized", "invalid api key", "authentication failed"
            ],
            ErrorType.PERMISSION_ERROR: [
                "403", "forbidden", "permission denied", "access denied"
            ],
            ErrorType.RATE_LIMIT: [
                "rate limit", "429", "too many requests", "quota exceeded"
            ]
        }
    
    def classify_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorType:
        """
        Classify an error based on its message and context.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
        
        Returns:
            ErrorType classification
        """
        error_message = str(error).lower()
        
        # Check each error type pattern
        for error_type, patterns in self.error_patterns.items():
            if any(pattern in error_message for pattern in patterns):
                return error_type
        
        # Check HTTP status codes if available
        if context and 'status_code' in context:
            status_code = context['status_code']
            if status_code == 404:
                return ErrorType.MEDIA_NOT_FOUND
            elif status_code in [500, 502, 503, 504]:
                return ErrorType.SERVICE_UNAVAILABLE
            elif status_code == 401:
                return ErrorType.AUTHENTICATION_ERROR
            elif status_code == 403:
                return ErrorType.PERMISSION_ERROR
            elif status_code == 429:
                return ErrorType.RATE_LIMIT
        
        return ErrorType.UNKNOWN_ERROR
    
    def create_error(self, error_type: ErrorType, original_error: Exception, 
                    context: Dict[str, Any] = None) -> MediaRequestError:
        """
        Create a MediaRequestError from an original error.
        
        Args:
            error_type: Classified error type
            original_error: Original exception
            context: Additional context
        
        Returns:
            MediaRequestError with appropriate handling parameters
        """
        context = context or {}
        
        # Determine retry parameters based on error type
        retry_config = {
            ErrorType.MEDIA_NOT_FOUND: {
                'retryable': False,
                'retry_delay': 0,
                'message': "Media not found in external databases"
            },
            ErrorType.SERVICE_UNAVAILABLE: {
                'retryable': True,
                'retry_delay': 300,  # 5 minutes
                'message': "External service temporarily unavailable"
            },
            ErrorType.TIMEOUT: {
                'retryable': True,
                'retry_delay': 180,  # 3 minutes
                'message': "Request timed out"
            },
            ErrorType.NETWORK_ERROR: {
                'retryable': True,
                'retry_delay': 120,  # 2 minutes
                'message': "Network connectivity issue"
            },
            ErrorType.AUTHENTICATION_ERROR: {
                'retryable': False,
                'retry_delay': 0,
                'message': "Authentication failed - check API keys"
            },
            ErrorType.PERMISSION_ERROR: {
                'retryable': False,
                'retry_delay': 0,
                'message': "Permission denied - check API permissions"
            },
            ErrorType.RATE_LIMIT: {
                'retryable': True,
                'retry_delay': 900,  # 15 minutes
                'message': "Rate limit exceeded"
            },
            ErrorType.INVALID_REQUEST: {
                'retryable': False,
                'retry_delay': 0,
                'message': "Invalid request parameters"
            },
            ErrorType.UNKNOWN_ERROR: {
                'retryable': True,
                'retry_delay': 600,  # 10 minutes
                'message': f"Unknown error: {str(original_error)}"
            }
        }
        
        config = retry_config[error_type]
        
        return MediaRequestError(
            error_type=error_type,
            message=config['message'],
            retryable=config['retryable'],
            retry_delay=config['retry_delay'],
            context={**context, 'original_error': str(original_error)}
        )
    
    def get_user_friendly_message(self, error: MediaRequestError) -> str:
        """
        Get a user-friendly error message.
        
        Args:
            error: MediaRequestError
        
        Returns:
            User-friendly error message
        """
        messages = {
            ErrorType.MEDIA_NOT_FOUND: "❌ **Media Not Found**\nSorry, this content couldn't be found in the available databases. It may not exist or might be too new/old.",
            ErrorType.SERVICE_UNAVAILABLE: "⚠️ **Service Temporarily Unavailable**\nThe media service is currently down. Your request will be retried automatically.",
            ErrorType.TIMEOUT: "⏱️ **Request Timed Out**\nThe request took too long to process. It will be retried automatically.",
            ErrorType.NETWORK_ERROR: "🌐 **Network Issue**\nThere's a temporary network problem. Your request will be retried automatically.",
            ErrorType.AUTHENTICATION_ERROR: "🔐 **Authentication Error**\nThere's an issue with the service configuration. Please contact an administrator.",
            ErrorType.PERMISSION_ERROR: "🚫 **Permission Denied**\nThe service doesn't have permission to fulfill this request. Please contact an administrator.",
            ErrorType.RATE_LIMIT: "⏳ **Rate Limited**\nToo many requests have been made. Your request will be retried automatically after a delay.",
            ErrorType.INVALID_REQUEST: "❓ **Invalid Request**\nThere was an issue with your request. Please try again with different search terms.",
            ErrorType.UNKNOWN_ERROR: "❌ **Unexpected Error**\nAn unexpected error occurred. Your request will be retried automatically."
        }
        
        base_message = messages.get(error.error_type, messages[ErrorType.UNKNOWN_ERROR])
        
        if error.retryable:
            retry_time = datetime.utcnow() + timedelta(seconds=error.retry_delay)
            retry_str = retry_time.strftime("%H:%M UTC")
            base_message += f"\n\n🔄 **Auto-retry scheduled for {retry_str}**"
        else:
            base_message += "\n\n❌ **This request cannot be retried automatically.**"
        
        return base_message


async def with_timeout_and_retry(
    coro_func,
    timeout_seconds: int = 30,
    max_retries: int = 3,
    retry_delay: int = 5,
    context: Dict[str, Any] = None
) -> Tuple[Any, Optional[MediaRequestError]]:
    """
    Execute a coroutine function with timeout and retry logic.
    
    Args:
        coro_func: Coroutine function to execute (or coroutine object for single attempt)
        timeout_seconds: Timeout in seconds
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        context: Additional context for error handling
    
    Returns:
        Tuple of (result, error) - one will be None
    """
    error_handler = ErrorHandler()
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Create fresh coroutine for each attempt
            if callable(coro_func):
                coro = coro_func()
            else:
                # For backward compatibility, handle coroutine objects (single attempt only)
                coro = coro_func
            
            # Execute with timeout
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            return result, None
            
        except asyncio.TimeoutError as e:
            error_type = ErrorType.TIMEOUT
            last_error = error_handler.create_error(error_type, e, context)
            logger.warning(f"Attempt {attempt + 1} timed out after {timeout_seconds}s")
            
        except Exception as e:
            error_type = error_handler.classify_error(e, context)
            last_error = error_handler.create_error(error_type, e, context)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
            # Don't retry for non-retryable errors
            if not last_error.retryable:
                break
        
        # Wait before retry (except on last attempt)
        if attempt < max_retries:
            await asyncio.sleep(retry_delay)
            logger.info(f"Retrying in {retry_delay} seconds...")
    
    return None, last_error


# Global error handler instance
error_handler = ErrorHandler()


def handle_service_errors(operation_name: str = "service operation", 
                         log_errors: bool = True,
                         default_return=None):
    """
    Decorator to standardize error handling for service operations.
    
    Args:
        operation_name: Human-readable name for the operation
        log_errors: Whether to log errors
        default_return: Default value to return on error
    
    Usage:
        @handle_service_errors("fetch user data")
        def get_user(self, user_id: int):
            # Service operation here
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if log_errors:
                    logger.debug(f"Starting {operation_name}")
                
                result = func(*args, **kwargs)
                
                if log_errors:
                    logger.debug(f"Completed {operation_name} successfully")
                
                return result
                
            except MediaRequestError as e:
                if log_errors:
                    logger.error(f"Service error in {operation_name}: {e}")
                raise  # Re-raise MediaRequestError for proper handling
                
            except Exception as e:
                if log_errors:
                    logger.error(f"Unexpected error in {operation_name}: {e}")
                    logger.error(traceback.format_exc())
                
                # Convert to MediaRequestError for consistency
                raise MediaRequestError(
                    error_type=ErrorType.UNKNOWN_ERROR,
                    message=f"Failed to complete {operation_name}: {str(e)}",
                    retryable=False
                )
        
        return wrapper
    return decorator


def handle_service_errors_async(operation_name: str = "async service operation",
                               log_errors: bool = True,
                               default_return=None):
    """
    Async version of service error handling decorator.
    
    Args:
        operation_name: Human-readable name for the operation
        log_errors: Whether to log errors
        default_return: Default value to return on error
    
    Usage:
        @handle_service_errors_async("fetch user data")
        async def get_user(self, user_id: int):
            # Async service operation here
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                if log_errors:
                    logger.debug(f"Starting {operation_name}")
                
                result = await func(*args, **kwargs)
                
                if log_errors:
                    logger.debug(f"Completed {operation_name} successfully")
                
                return result
                
            except MediaRequestError as e:
                if log_errors:
                    logger.error(f"Service error in {operation_name}: {e}")
                raise  # Re-raise MediaRequestError for proper handling
                
            except Exception as e:
                if log_errors:
                    logger.error(f"Unexpected error in {operation_name}: {e}")
                    logger.error(traceback.format_exc())
                
                # Convert to MediaRequestError for consistency
                raise MediaRequestError(
                    error_type=ErrorType.UNKNOWN_ERROR,
                    message=f"Failed to complete {operation_name}: {str(e)}",
                    retryable=False
                )
        
        return wrapper
    return decorator


def safe_execute(operation_name: str = "operation", 
                default_return=None,
                log_errors: bool = True):
    """
    Decorator for safe execution that returns default value on error instead of raising.
    
    Args:
        operation_name: Human-readable name for the operation
        default_return: Value to return on error
        log_errors: Whether to log errors
    
    Usage:
        @safe_execute("get user preferences", default_return={})
        def get_user_prefs(self, user_id: int):
            # Operation that might fail
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {operation_name}: {e}")
                return default_return
        
        return wrapper
    return decorator


def safe_execute_async(operation_name: str = "async operation",
                      default_return=None,
                      log_errors: bool = True):
    """
    Async version of safe execution decorator.
    
    Args:
        operation_name: Human-readable name for the operation
        default_return: Value to return on error
        log_errors: Whether to log errors
    
    Usage:
        @safe_execute_async("get user preferences", default_return={})
        async def get_user_prefs(self, user_id: int):
            # Async operation that might fail
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {operation_name}: {e}")
                return default_return
        
        return wrapper
    return decorator
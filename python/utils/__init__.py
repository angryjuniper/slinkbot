"""Utilities package for SlinkBot."""

from .error_handling import (
    ErrorType,
    MediaRequestError,
    ErrorHandler,
    with_timeout_and_retry,
    error_handler
)
from .simple_logging import setup_logging, logger

__all__ = [
    'ErrorType',
    'MediaRequestError',
    'ErrorHandler',
    'with_timeout_and_retry',
    'error_handler',
    'setup_logging',
    'logger'
] 
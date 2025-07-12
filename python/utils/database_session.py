"""
Database session management utilities for SlinkBot.

This module provides decorators and context managers to standardize
database session handling and reduce boilerplate code.
"""

import functools
from contextlib import contextmanager
from typing import Generator, Callable, Any, TypeVar, Union
from sqlalchemy.orm import Session
from database.models import get_db, db_manager
from utils.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


@contextmanager
def database_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup.
    
    Usage:
        with database_session() as session:
            # Use session here
            result = session.query(Model).all()
            session.commit()
    
    Yields:
        Session: SQLAlchemy database session
    """
    with get_db() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def with_database_session(func: F) -> F:
    """
    Decorator that automatically provides a database session as the first argument.
    
    The decorated function should accept 'session' as its first parameter after 'self'
    (for methods) or as the first parameter (for functions).
    
    Usage:
        @with_database_session
        def my_function(session: Session, other_param: str) -> None:
            # Use session here
            pass
        
        @with_database_session
        def my_method(self, session: Session, other_param: str) -> None:
            # Use session here
            pass
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function with automatic session management
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with database_session() as session:
            # Insert session as first argument after self (if method) or as first argument
            if args and hasattr(args[0], '__dict__'):
                # This is a method call, insert session after self
                return func(args[0], session, *args[1:], **kwargs)
            else:
                # This is a function call, insert session as first argument
                return func(session, *args, **kwargs)
    
    return wrapper


def with_database_session_async(func: F) -> F:
    """
    Decorator for async functions that automatically provides a database session.
    
    Usage:
        @with_database_session_async
        async def my_async_function(session: Session, other_param: str) -> None:
            # Use session here
            pass
    
    Args:
        func: Async function to decorate
        
    Returns:
        Decorated async function with automatic session management
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with database_session() as session:
            # Insert session as first argument after self (if method) or as first argument
            if args and hasattr(args[0], '__dict__'):
                # This is a method call, insert session after self
                return await func(args[0], session, *args[1:], **kwargs)
            else:
                # This is a function call, insert session as first argument
                return await func(session, *args, **kwargs)
    
    return wrapper


class DatabaseTransaction:
    """
    Context manager for database transactions with automatic rollback on errors.
    
    Usage:
        with DatabaseTransaction() as session:
            # Perform database operations
            session.add(new_object)
            # Commit happens automatically if no exception
    """
    
    def __init__(self):
        self.session = None
    
    def __enter__(self) -> Session:
        """Enter the transaction context."""
        self.session = next(get_db())
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the transaction context with automatic commit/rollback."""
        if self.session:
            try:
                if exc_type is None:
                    # No exception occurred, commit the transaction
                    self.session.commit()
                    logger.debug("Database transaction committed successfully")
                else:
                    # Exception occurred, rollback the transaction
                    self.session.rollback()
                    logger.warning(f"Database transaction rolled back due to {exc_type.__name__}: {exc_val}")
            except Exception as e:
                logger.error(f"Error during transaction cleanup: {e}")
                self.session.rollback()
            finally:
                self.session.close()


def safe_database_operation(operation_name: str = "database operation"):
    """
    Decorator that wraps database operations with error handling and logging.
    
    Args:
        operation_name: Human-readable name for the operation (for logging)
    
    Usage:
        @safe_database_operation("update user preferences")
        def update_user_prefs(session: Session, user_id: int, prefs: dict):
            # Database operation here
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.debug(f"Starting {operation_name}")
                result = func(*args, **kwargs)
                logger.debug(f"Completed {operation_name} successfully")
                return result
            except Exception as e:
                logger.error(f"Failed {operation_name}: {e}")
                raise
        return wrapper
    return decorator


# Utility functions for common database patterns
def get_stats_safely() -> dict:
    """
    Safely get database statistics with error handling.
    
    Returns:
        Dictionary with database statistics or empty dict on error
    """
    try:
        return db_manager.get_stats()
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


def health_check_safely() -> bool:
    """
    Safely perform database health check with error handling.
    
    Returns:
        True if database is healthy, False otherwise
    """
    try:
        return db_manager.health_check()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
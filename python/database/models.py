"""
Database models for SlinkBot using SQLAlchemy ORM.
"""

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from utils.logging_config import get_logger
from utils.status_manager import StatusManager

logger = get_logger(__name__)

Base = declarative_base()


class TrackedRequest(Base):
    """Database model for tracking media requests."""
    __tablename__ = 'tracked_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    jellyseerr_request_id = Column(Integer, unique=True, nullable=False, index=True)
    discord_user_id = Column(Integer, nullable=False, index=True)
    discord_channel_id = Column(Integer, nullable=False)
    media_title = Column(String(255), nullable=False)
    media_year = Column(String(4), nullable=False)
    media_type = Column(String(50), nullable=False)
    media_id = Column(Integer, nullable=False)  # TMDB/TVDB ID
    poster_url = Column(String(500), nullable=True)  # Poster image URL
    last_status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Notification tracking
    completion_notified = Column(Boolean, default=False, nullable=False)
    completion_notified_at = Column(DateTime, nullable=True)
    
    # Request persistence and integrity
    request_hash = Column(String(64), nullable=True, index=True)  # Hash for duplicate detection
    failure_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    retry_after = Column(DateTime, nullable=True)  # When to retry failed requests
    
    # Relationship to status history
    status_history = relationship("RequestStatusHistory", back_populates="tracked_request", cascade="all, delete-orphan")
    
    # Composite index for better query performance
    __table_args__ = (
        Index('idx_user_status', 'discord_user_id', 'last_status'),
        Index('idx_media_hash', 'media_id', 'media_type', 'discord_user_id'),
        Index('idx_active_requests', 'is_active', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TrackedRequest(id={self.id}, title='{self.media_title}', status={self.last_status})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'jellyseerr_request_id': self.jellyseerr_request_id,
            'discord_user_id': self.discord_user_id,
            'discord_channel_id': self.discord_channel_id,
            'media_title': self.media_title,
            'media_year': self.media_year,
            'media_type': self.media_type,
            'media_id': self.media_id,
            'poster_url': self.poster_url,
            'last_status': self.last_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'completion_notified': self.completion_notified,
            'completion_notified_at': self.completion_notified_at.isoformat() if self.completion_notified_at else None
        }
    
    def get_status_display(self):
        """Get human-readable status string."""
        return StatusManager.get_status_display(self.last_status)
    
    def is_final_status(self):
        """Check if request is in a final state."""
        return StatusManager.is_final_status(self.last_status)
    
    def can_retry(self):
        """Check if a failed request can be retried."""
        if not self.retry_after:
            return True
        return datetime.utcnow() > self.retry_after
    
    def mark_failed(self, error_message: str, retry_delay_minutes: int = 30):
        """Mark request as failed with retry logic."""
        self.failure_count = (self.failure_count or 0) + 1
        self.last_error = error_message
        self.last_error_at = datetime.utcnow()
        self.retry_after = datetime.utcnow().replace(
            minute=datetime.utcnow().minute + retry_delay_minutes
        )
        self.updated_at = datetime.utcnow()
    
    def reset_failure_state(self):
        """Reset failure state when request succeeds."""
        self.failure_count = 0
        self.last_error = None
        self.last_error_at = None
        self.retry_after = None
        self.updated_at = datetime.utcnow()
    
    def generate_request_hash(self):
        """Generate hash for duplicate detection."""
        import hashlib
        hash_string = f"{self.media_id}:{self.media_type}:{self.discord_user_id}"
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def add_status_change(self, old_status: int, new_status: int, session: Session):
        """Add status change to history."""
        history = RequestStatusHistory(
            tracked_request_id=self.id,
            old_status=old_status,
            new_status=new_status,
            changed_at=datetime.utcnow()
        )
        session.add(history)
        return history


class ServiceHealth(Base):
    """Database model for tracking service health status."""
    __tablename__ = 'service_health'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String(100), nullable=False, unique=True, index=True)
    is_healthy = Column(Boolean, nullable=False, default=True)
    last_check = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    last_success = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ServiceHealth(service='{self.service_name}', healthy={self.is_healthy})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'service_name': self.service_name,
            'is_healthy': self.is_healthy,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'last_error': self.last_error,
            'error_count': self.error_count,
            'consecutive_failures': self.consecutive_failures,
            'last_success': self.last_success.isoformat() if self.last_success else None
        }


class RequestStatusHistory(Base):
    """Database model for tracking request status change history."""
    __tablename__ = 'request_status_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tracked_request_id = Column(Integer, ForeignKey('tracked_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    old_status = Column(Integer, nullable=False)
    new_status = Column(Integer, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notification_sent = Column(Boolean, default=False, nullable=False)
    reason = Column(Text, nullable=True)  # Optional reason for status change
    
    # Relationship back to tracked request
    tracked_request = relationship("TrackedRequest", back_populates="status_history")
    
    def __repr__(self):
        return f"<RequestStatusHistory(request_id={self.tracked_request_id}, {self.old_status}->{self.new_status})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'tracked_request_id': self.tracked_request_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'notification_sent': self.notification_sent,
            'reason': self.reason
        }


class BotConfiguration(Base):
    """Database model for storing bot configuration."""
    __tablename__ = 'bot_configuration'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<BotConfiguration(key='{self.key}', value='{self.value}')>"


# Database setup and session management
class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager.
        
        Args:
            database_url: SQLite database URL. Defaults to local file.
        """
        if database_url is None:
            # Default to local SQLite database
            db_path = os.getenv('DATABASE_PATH', '/opt/docker/slinkbot/python/data/slinkbot.db')
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            database_url = f'sqlite:///{db_path}'
        
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before use
            connect_args={'check_same_thread': False} if 'sqlite' in database_url else {}
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database manager initialized with URL: {database_url}")
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session with automatic cleanup.
        
        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """
        Check database connectivity.
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            with next(self.get_session()) as session:
                # Simple query to test connectivity
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with next(self.get_session()) as session:
                stats = {
                    'total_requests': session.query(TrackedRequest).count(),
                    'active_requests': session.query(TrackedRequest).filter(TrackedRequest.is_active == True).count(),
                    'completed_requests': session.query(TrackedRequest).filter(TrackedRequest.last_status == 5).count(),
                    'failed_requests': session.query(TrackedRequest).filter(TrackedRequest.failure_count > 0).count(),
                    'pending_retry': session.query(TrackedRequest).filter(
                        TrackedRequest.retry_after.isnot(None),
                        TrackedRequest.retry_after > datetime.utcnow()
                    ).count(),
                    'services_monitored': session.query(ServiceHealth).count(),
                    'healthy_services': session.query(ServiceHealth).filter(ServiceHealth.is_healthy == True).count(),
                    'status_history_count': session.query(RequestStatusHistory).count()
                }
                return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    def check_integrity(self) -> dict:
        """
        Perform comprehensive database integrity checks.
        
        Returns:
            Dictionary with integrity check results
        """
        try:
            with next(self.get_session()) as session:
                results = {
                    'healthy': True,
                    'issues': [],
                    'stats': {}
                }
                
                # Check for orphaned status history records
                orphaned_history = session.query(RequestStatusHistory).filter(
                    ~RequestStatusHistory.tracked_request_id.in_(
                        session.query(TrackedRequest.id)
                    )
                ).count()
                
                if orphaned_history > 0:
                    results['healthy'] = False
                    results['issues'].append(f"Found {orphaned_history} orphaned status history records")
                
                # Check for requests without proper hashes
                unhashed_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.request_hash.is_(None)
                ).count()
                
                if unhashed_requests > 0:
                    results['issues'].append(f"Found {unhashed_requests} requests without duplicate detection hash")
                
                # Check for requests missing required fields
                invalid_requests = session.query(TrackedRequest).filter(
                    (TrackedRequest.jellyseerr_request_id.is_(None)) |
                    (TrackedRequest.discord_user_id.is_(None)) |
                    (TrackedRequest.media_id.is_(None))
                ).count()
                
                if invalid_requests > 0:
                    results['healthy'] = False
                    results['issues'].append(f"Found {invalid_requests} requests with missing required fields")
                
                # Check for stale retry requests
                stale_retries = session.query(TrackedRequest).filter(
                    TrackedRequest.retry_after.isnot(None),
                    TrackedRequest.retry_after < datetime.utcnow(),
                    TrackedRequest.failure_count > 5  # More than 5 failures
                ).count()
                
                if stale_retries > 0:
                    results['issues'].append(f"Found {stale_retries} requests with excessive failures")
                
                results['stats'] = {
                    'orphaned_history': orphaned_history,
                    'unhashed_requests': unhashed_requests,
                    'invalid_requests': invalid_requests,
                    'stale_retries': stale_retries
                }
                
                return results
                
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return {
                'healthy': False,
                'issues': [f"Integrity check failed: {str(e)}"],
                'stats': {}
            }
    
    def repair_integrity(self) -> dict:
        """
        Attempt to repair database integrity issues.
        
        Returns:
            Dictionary with repair results
        """
        try:
            with next(self.get_session()) as session:
                repairs = {
                    'performed': [],
                    'failed': [],
                    'total_repairs': 0
                }
                
                # Clean up orphaned status history records
                orphaned_deleted = session.query(RequestStatusHistory).filter(
                    ~RequestStatusHistory.tracked_request_id.in_(
                        session.query(TrackedRequest.id)
                    )
                ).delete(synchronize_session=False)
                
                if orphaned_deleted > 0:
                    repairs['performed'].append(f"Removed {orphaned_deleted} orphaned status history records")
                    repairs['total_repairs'] += orphaned_deleted
                
                # Generate missing request hashes
                unhashed_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.request_hash.is_(None)
                ).all()
                
                for request in unhashed_requests:
                    request.request_hash = request.generate_request_hash()
                    session.add(request)
                
                if unhashed_requests:
                    repairs['performed'].append(f"Generated hashes for {len(unhashed_requests)} requests")
                    repairs['total_repairs'] += len(unhashed_requests)
                
                # Reset stale retry requests that have failed too many times
                stale_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.retry_after.isnot(None),
                    TrackedRequest.failure_count > 10  # More than 10 failures
                ).all()
                
                for request in stale_requests:
                    request.is_active = False  # Mark as inactive instead of deleting
                    request.last_error = "Request failed too many times - marked inactive"
                    session.add(request)
                
                if stale_requests:
                    repairs['performed'].append(f"Deactivated {len(stale_requests)} requests with excessive failures")
                    repairs['total_repairs'] += len(stale_requests)
                
                session.commit()
                return repairs
                
        except Exception as e:
            logger.error(f"Database repair failed: {e}")
            return {
                'performed': [],
                'failed': [f"Repair failed: {str(e)}"],
                'total_repairs': 0
            }


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        SQLAlchemy session
    """
    yield from db_manager.get_session()


def init_database():
    """Initialize database tables."""
    db_manager.create_tables()


def get_database_stats() -> dict:
    """Get database statistics."""
    return db_manager.get_stats()
"""
Utility functions for request management, duplicate detection, and error handling.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from database.models import TrackedRequest, RequestStatusHistory
from utils.logging_config import get_logger

logger = get_logger(__name__)


def generate_request_hash(media_id: int, media_type: str, user_id: int) -> str:
    """
    Generate a hash for duplicate detection.
    
    Args:
        media_id: TMDB/TVDB media ID
        media_type: Type of media (movie, tv, etc.)
        user_id: Discord user ID
    
    Returns:
        SHA256 hash string for duplicate detection
    """
    hash_string = f"{media_id}:{media_type}:{user_id}"
    return hashlib.sha256(hash_string.encode()).hexdigest()


def check_duplicate_request(session: Session, media_id: int, media_type: str, user_id: int) -> Optional[TrackedRequest]:
    """
    Check if a request already exists for this user and media.
    
    Args:
        session: Database session
        media_id: TMDB/TVDB media ID
        media_type: Type of media
        user_id: Discord user ID
    
    Returns:
        Existing TrackedRequest if found, None otherwise
    """
    try:
        request_hash = generate_request_hash(media_id, media_type, user_id)
        
        # Check for exact hash match first (most efficient)
        existing_request = session.query(TrackedRequest).filter(
            TrackedRequest.request_hash == request_hash,
            TrackedRequest.is_active == True
        ).first()
        
        if existing_request:
            return existing_request
        
        # Fallback: check by media_id, media_type, and user_id
        existing_request = session.query(TrackedRequest).filter(
            TrackedRequest.media_id == media_id,
            TrackedRequest.media_type == media_type,
            TrackedRequest.discord_user_id == user_id,
            TrackedRequest.is_active == True
        ).first()
        
        return existing_request
        
    except Exception as e:
        logger.error(f"Error checking for duplicate request: {e}")
        return None


def get_retryable_requests(session: Session, limit: int = 50) -> List[TrackedRequest]:
    """
    Get requests that failed but can be retried.
    
    Args:
        session: Database session
        limit: Maximum number of requests to return
    
    Returns:
        List of TrackedRequest objects ready for retry
    """
    try:
        now = datetime.utcnow()
        
        retryable_requests = session.query(TrackedRequest).filter(
            TrackedRequest.is_active == True,
            TrackedRequest.failure_count > 0,
            TrackedRequest.failure_count < 5,  # Don't retry after 5 failures
            TrackedRequest.retry_after.isnot(None),
            TrackedRequest.retry_after <= now
        ).limit(limit).all()
        
        return retryable_requests
        
    except Exception as e:
        logger.error(f"Error getting retryable requests: {e}")
        return []


def mark_request_failed(session: Session, request: TrackedRequest, error_message: str, 
                       retry_delay_minutes: int = 30) -> bool:
    """
    Mark a request as failed with retry logic.
    
    Args:
        session: Database session
        request: TrackedRequest to mark as failed
        error_message: Error description
        retry_delay_minutes: Minutes to wait before retry
    
    Returns:
        True if marked successfully, False otherwise
    """
    try:
        old_status = request.last_status
        request.mark_failed(error_message, retry_delay_minutes)
        
        # Add to status history
        request.add_status_change(old_status, request.last_status, session)
        
        session.add(request)
        session.commit()
        
        logger.warning(f"Request {request.id} marked as failed: {error_message}")
        return True
        
    except Exception as e:
        logger.error(f"Error marking request as failed: {e}")
        session.rollback()
        return False


def mark_request_success(session: Session, request: TrackedRequest, new_status: int) -> bool:
    """
    Mark a request as successful and reset failure state.
    
    Args:
        session: Database session
        request: TrackedRequest to mark as successful
        new_status: New status code
    
    Returns:
        True if marked successfully, False otherwise
    """
    try:
        old_status = request.last_status
        request.reset_failure_state()
        request.last_status = new_status
        request.updated_at = datetime.utcnow()
        
        # Add to status history
        request.add_status_change(old_status, new_status, session)
        
        session.add(request)
        session.commit()
        
        logger.info(f"Request {request.id} marked as successful with status {new_status}")
        return True
        
    except Exception as e:
        logger.error(f"Error marking request as successful: {e}")
        session.rollback()
        return False


def cleanup_old_requests(session: Session, days_old: int = 90) -> Dict[str, int]:
    """
    Clean up old completed requests to prevent database bloat.
    
    Args:
        session: Database session
        days_old: Remove requests older than this many days
    
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old completed requests
        old_requests = session.query(TrackedRequest).filter(
            TrackedRequest.is_active == False,
            TrackedRequest.last_status == 5,  # Completed
            TrackedRequest.updated_at < cutoff_date
        ).all()
        
        # Archive them (mark as archived instead of deleting)
        archived_count = 0
        for request in old_requests:
            # Keep the request but mark as archived
            request.last_error = "Archived due to age"
            request.updated_at = datetime.utcnow()
            session.add(request)
            archived_count += 1
        
        # Clean up very old status history (older than 1 year)
        very_old_cutoff = datetime.utcnow() - timedelta(days=365)
        old_history_count = session.query(RequestStatusHistory).filter(
            RequestStatusHistory.changed_at < very_old_cutoff
        ).count()
        
        # Delete very old history records
        session.query(RequestStatusHistory).filter(
            RequestStatusHistory.changed_at < very_old_cutoff
        ).delete(synchronize_session=False)
        
        session.commit()
        
        result = {
            'archived_requests': archived_count,
            'deleted_history': old_history_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
        logger.info(f"Cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        session.rollback()
        return {
            'archived_requests': 0,
            'deleted_history': 0,
            'error': str(e)
        }


def get_request_statistics(session: Session) -> Dict[str, Any]:
    """
    Get comprehensive request statistics.
    
    Args:
        session: Database session
    
    Returns:
        Dictionary with detailed statistics
    """
    try:
        now = datetime.utcnow()
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        stats = {
            'total_requests': session.query(TrackedRequest).count(),
            'active_requests': session.query(TrackedRequest).filter(TrackedRequest.is_active == True).count(),
            'completed_requests': session.query(TrackedRequest).filter(TrackedRequest.last_status == 5).count(),
            'failed_requests': session.query(TrackedRequest).filter(TrackedRequest.failure_count > 0).count(),
            'retryable_requests': session.query(TrackedRequest).filter(
                TrackedRequest.failure_count > 0,
                TrackedRequest.failure_count < 5,
                TrackedRequest.retry_after <= now
            ).count(),
            'recent_requests': {
                'last_week': session.query(TrackedRequest).filter(TrackedRequest.created_at >= last_week).count(),
                'last_month': session.query(TrackedRequest).filter(TrackedRequest.created_at >= last_month).count()
            },
            'status_breakdown': {},
            'media_type_breakdown': {}
        }
        
        # Get status breakdown
        from sqlalchemy import func
        status_counts = session.query(
            TrackedRequest.last_status,
            func.count(TrackedRequest.id)
        ).group_by(TrackedRequest.last_status).all()
        
        for status, count in status_counts:
            stats['status_breakdown'][status] = count
        
        # Get media type breakdown
        media_counts = session.query(
            TrackedRequest.media_type,
            func.count(TrackedRequest.id)
        ).group_by(TrackedRequest.media_type).all()
        
        for media_type, count in media_counts:
            stats['media_type_breakdown'][media_type] = count
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting request statistics: {e}")
        return {}


def ensure_request_integrity(session: Session, request: TrackedRequest) -> bool:
    """
    Ensure a request has proper integrity (hash, required fields, etc.).
    
    Args:
        session: Database session
        request: TrackedRequest to check
    
    Returns:
        True if integrity ensured, False if failed
    """
    try:
        updated = False
        
        # Ensure request hash exists
        if not request.request_hash:
            request.request_hash = generate_request_hash(
                request.media_id, 
                request.media_type, 
                request.discord_user_id
            )
            updated = True
        
        # Ensure required fields are present
        if not request.jellyseerr_request_id or not request.discord_user_id or not request.media_id:
            logger.warning(f"Request {request.id} missing required fields")
            return False
        
        # Ensure timestamps are present
        if not request.created_at:
            request.created_at = datetime.utcnow()
            updated = True
        
        if not request.updated_at:
            request.updated_at = datetime.utcnow()
            updated = True
        
        if updated:
            session.add(request)
            session.commit()
            logger.info(f"Request {request.id} integrity ensured")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring request integrity: {e}")
        session.rollback()
        return False
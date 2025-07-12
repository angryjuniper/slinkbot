"""
Request Manager for handling media request lifecycle.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database.models import TrackedRequest, RequestStatusHistory, get_db
from services.jellyseerr import JellyseerrService
from models.media import MediaRequest
from utils.logging_config import get_logger
from utils.database_session import with_database_session, database_session, safe_database_operation

logger = get_logger(__name__)
from utils.error_handling import ErrorType, MediaRequestError, error_handler, with_timeout_and_retry
from utils.request_utils import (
    check_duplicate_request, mark_request_failed, mark_request_success,
    ensure_request_integrity, generate_request_hash
)


class RequestManager:
    """Manages media request lifecycle and tracking."""
    
    def __init__(self, jellyseerr_service: JellyseerrService):
        """
        Initialize request manager.
        
        Args:
            jellyseerr_service: JellyseerrService instance
        """
        self.jellyseerr_service = jellyseerr_service
    
    async def submit_request(self, media_id: int, media_type: str, user_id: int, 
                           channel_id: int, media_title: str = None, media_year: str = None, 
                           poster_url: str = None) -> Optional[TrackedRequest]:
        """
        Submit a new media request and start tracking it with duplicate prevention.
        
        Args:
            media_id: TMDB/TVDB ID of the media
            media_type: Type of media ('movie', 'tv', 'anime')
            user_id: Discord user ID
            channel_id: Discord channel ID
            media_title: Optional media title (will be fetched if not provided)
            media_year: Optional media year (will be fetched if not provided)
            poster_url: Optional poster image URL
            
        Returns:
            TrackedRequest object if successful, None otherwise
        """
        try:
            logger.info(f"Submitting request for {media_type} ID {media_id} by user {user_id}")
            
            with next(get_db()) as session:
                # Check for duplicate requests first
                existing_request = check_duplicate_request(session, media_id, media_type, user_id)
                if existing_request:
                    logger.info(f"Duplicate request detected for user {user_id}, media {media_id}")
                    return existing_request
            
                # Submit request to Jellyseerr with timeout and retry
                context = {
                    'media_id': media_id,
                    'media_type': media_type,
                    'user_id': user_id
                }
                
                async def _submit_request_coro():
                    return await self.jellyseerr_service.submit_request(media_id, media_type)
                
                media_request, error = await with_timeout_and_retry(
                    _submit_request_coro,
                    timeout_seconds=30,
                    max_retries=2,
                    context=context
                )
                
                if error:
                    # Handle different types of errors
                    if error.error_type == ErrorType.MEDIA_NOT_FOUND:
                        logger.warning(f"Media {media_id} not found in Jellyseerr database")
                        return None
                    else:
                        # For retryable errors, log the error but don't create invalid database records
                        logger.error(f"Failed to submit request for {media_type} ID {media_id}: {error.message}")
                        logger.info(f"Error is retryable, will be retried automatically in background")
                        return None
                
                # Use provided title/year or get from request response
                title = media_title or media_request.title
                year = media_year or media_request.year
                
                # Store in database for tracking
                with next(get_db()) as session:
                    # Check if already tracking this request
                    existing = session.query(TrackedRequest).filter(
                        TrackedRequest.jellyseerr_request_id == media_request.id
                    ).first()
                    
                    if existing:
                        logger.warning(f"Request {media_request.id} is already being tracked")
                        return existing
                    
                    tracked_request = TrackedRequest(
                        jellyseerr_request_id=media_request.id,
                        discord_user_id=user_id,
                        discord_channel_id=channel_id,
                        media_title=title,
                        media_year=year,
                        media_type=media_type,
                        media_id=media_id,
                        poster_url=poster_url,
                        last_status=media_request.status,
                        request_hash=generate_request_hash(media_id, media_type, user_id)
                    )
                    
                    session.add(tracked_request)
                    session.commit()
                    session.refresh(tracked_request)
                    
                    # Ensure integrity
                    ensure_request_integrity(session, tracked_request)
                    
                    # Record initial status in history
                    self._record_status_change(session, tracked_request.id, None, media_request.status)
                    
                    logger.info(f"Request submitted and tracked: {tracked_request.id} (Jellyseerr: {media_request.id})")
                    return tracked_request
                
        except Exception as e:
            logger.error(f"Failed to submit request for {media_type} ID {media_id}: {e}")
            
            # Create error and potentially save for retry
            error_type = error_handler.classify_error(e)
            media_error = error_handler.create_error(error_type, e, {'media_id': media_id, 'user_id': user_id})
            
            if media_error.retryable:
                logger.error(f"Retryable error for {media_type} ID {media_id}: {str(e)}")
                logger.info(f"Error will be retried automatically in background")
            else:
                logger.error(f"Non-retryable error for {media_type} ID {media_id}: {str(e)}")
            
            return None
    
    async def check_request_updates(self) -> List[Dict[str, Any]]:
        """
        Check for status updates on all tracked requests with enhanced error handling.
        
        Returns:
            List of dictionaries containing update information
        """
        updates = []
        
        try:
            with next(get_db()) as session:
                # Get all active requests
                active_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.is_active == True
                ).all()
                
                logger.debug(f"Checking {len(active_requests)} active requests for updates")
                
                for tracked_request in active_requests:
                    try:
                        # Use enhanced error handling for API calls
                        context = {
                            'tracked_request_id': tracked_request.id,
                            'jellyseerr_request_id': tracked_request.jellyseerr_request_id
                        }
                        
                        async def _get_status_coro():
                            return await self.jellyseerr_service.get_request_status(tracked_request.jellyseerr_request_id)
                        
                        current_request, error = await with_timeout_and_retry(
                            _get_status_coro,
                            timeout_seconds=15,
                            max_retries=1,
                            context=context
                        )
                        
                        if error:
                            # Handle API errors gracefully
                            if error.error_type == ErrorType.MEDIA_NOT_FOUND:
                                # Request no longer exists, mark as inactive
                                logger.info(f"Request {tracked_request.jellyseerr_request_id} no longer exists, marking inactive")
                                tracked_request.is_active = False
                                session.commit()
                                continue
                            else:
                                # For other errors, mark as failed for retry
                                mark_request_failed(session, tracked_request, error.message, error.retry_delay // 60)
                                logger.warning(f"Failed to check request {tracked_request.id}: {error.message}")
                                continue
                        
                        if not current_request:
                            # Request no longer exists, mark as inactive
                            logger.info(f"Request {tracked_request.jellyseerr_request_id} no longer exists, marking inactive")
                            tracked_request.is_active = False
                            session.commit()
                            continue
                        
                        # Check for status change
                        if current_request.status != tracked_request.last_status:
                            old_status = tracked_request.last_status
                            
                            # Reset failure state on successful update
                            if tracked_request.failure_count > 0:
                                mark_request_success(session, tracked_request, current_request.status)
                            else:
                                tracked_request.last_status = current_request.status
                                tracked_request.updated_at = datetime.utcnow()
                            
                            # If request is completed, mark as inactive
                            if current_request.status == 5:  # Available
                                tracked_request.is_active = False
                            
                            session.commit()
                            
                            # Record status change in history
                            self._record_status_change(session, tracked_request.id, old_status, current_request.status)
                            
                            updates.append({
                                'tracked_request': tracked_request,
                                'old_status': old_status,
                                'new_status': current_request.status,
                                'media_request': current_request
                            })
                            
                            logger.info(f"Status update for request {tracked_request.id}: {old_status} -> {current_request.status}")
                            
                    except Exception as e:
                        logger.error(f"Error checking request {tracked_request.id}: {e}")
                        # Mark request as failed for retry
                        try:
                            with next(get_db()) as session:
                                mark_request_failed(session, tracked_request, str(e))
                        except:
                            pass  # Don't let error handling errors break the loop
                        continue
                
                logger.info(f"Found {len(updates)} request updates")
                return updates
                
        except Exception as e:
            logger.error(f"Error checking request updates: {e}")
            return []
    
    async def cancel_request(self, request_id: int, user_id: int) -> bool:
        """
        Cancel a request if user has permission.
        
        Args:
            request_id: Jellyseerr request ID
            user_id: Discord user ID
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            with next(get_db()) as session:
                # Find the tracked request
                tracked_request = session.query(TrackedRequest).filter(
                    and_(
                        TrackedRequest.jellyseerr_request_id == request_id,
                        TrackedRequest.discord_user_id == user_id,
                        TrackedRequest.last_status.in_([1, 2, 3, 4])  # Only allow cancelling pending/approved/downloading requests
                    )
                ).first()
                
                if not tracked_request:
                    logger.warning(f"Request {request_id} not found or user {user_id} not authorized")
                    return False
                
                # Cancel in Jellyseerr
                success = await self.jellyseerr_service.cancel_request(request_id)
                
                if success:
                    # Mark as inactive and record cancellation
                    old_status = tracked_request.last_status
                    tracked_request.is_active = False
                    tracked_request.updated_at = datetime.utcnow()
                    session.commit()
                    
                    # Record cancellation in history
                    self._record_status_change(session, tracked_request.id, old_status, -1, "Cancelled by user")
                    
                    logger.info(f"Request {request_id} cancelled by user {user_id}")
                    return True
                else:
                    logger.error(f"Failed to cancel request {request_id} in Jellyseerr")
                    return False
                
        except Exception as e:
            logger.error(f"Error cancelling request {request_id}: {e}")
            return False
    
    def get_user_requests(self, user_id: int, include_inactive: bool = False) -> List[TrackedRequest]:
        """
        Get all requests for a specific user.
        
        Args:
            user_id: Discord user ID
            include_inactive: Whether to include inactive requests
            
        Returns:
            List of TrackedRequest objects
        """
        try:
            with next(get_db()) as session:
                query = session.query(TrackedRequest).filter(
                    TrackedRequest.discord_user_id == user_id
                )
                
                if not include_inactive:
                    query = query.filter(TrackedRequest.is_active == True)
                    logger.debug(f"Filtering for active requests only")
                
                requests = query.order_by(TrackedRequest.created_at.desc()).all()
                
                # Ensure all attributes are loaded before session closes
                for req in requests:
                    # Access all attributes to ensure they're loaded
                    _ = req.media_title, req.media_year, req.media_type, req.last_status, req.jellyseerr_request_id
                
                logger.debug(f"Found {len(requests)} requests for user {user_id}")
                return requests
                
        except Exception as e:
            logger.error(f"Error getting user requests for {user_id}: {e}")
            return []
    
    def get_request_by_id(self, request_id: int) -> Optional[TrackedRequest]:
        """
        Get a specific tracked request by ID.
        
        Args:
            request_id: Jellyseerr request ID
            
        Returns:
            TrackedRequest object if found, None otherwise
        """
        try:
            with next(get_db()) as session:
                request = session.query(TrackedRequest).filter(
                    TrackedRequest.jellyseerr_request_id == request_id
                ).first()
                
                return request
                
        except Exception as e:
            logger.error(f"Error getting request {request_id}: {e}")
            return None
    
    def get_requests_by_status(self, status: int, limit: int = 50) -> List[TrackedRequest]:
        """
        Get requests by status.
        
        Args:
            status: Request status code
            limit: Maximum number of requests to return
            
        Returns:
            List of TrackedRequest objects
        """
        try:
            with next(get_db()) as session:
                requests = session.query(TrackedRequest).filter(
                    and_(
                        TrackedRequest.last_status == status,
                        TrackedRequest.is_active == True
                    )
                ).order_by(TrackedRequest.updated_at.desc()).limit(limit).all()
                
                return requests
                
        except Exception as e:
            logger.error(f"Error getting requests by status {status}: {e}")
            return []
    
    def get_recent_completions(self, days: int = 7, limit: int = 10) -> List[TrackedRequest]:
        """
        Get recently completed requests.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of requests to return
            
        Returns:
            List of TrackedRequest objects
        """
        try:
            with next(get_db()) as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                requests = session.query(TrackedRequest).filter(
                    and_(
                        TrackedRequest.last_status == 5,  # Available
                        TrackedRequest.updated_at >= cutoff_date
                    )
                ).order_by(TrackedRequest.updated_at.desc()).limit(limit).all()
                
                return requests
                
        except Exception as e:
            logger.error(f"Error getting recent completions: {e}")
            return []
    
    @with_database_session
    @safe_database_operation("get request statistics")
    def get_request_statistics(self, session: Session) -> Dict[str, Any]:
        """
        Get request statistics.
        
        Returns:
            Dictionary with request statistics
        """
        total_requests = session.query(TrackedRequest).count()
        active_requests = session.query(TrackedRequest).filter(TrackedRequest.is_active == True).count()
        completed_requests = session.query(TrackedRequest).filter(TrackedRequest.last_status == 5).count()
        
        # Status breakdown
        status_counts = {}
        for status in [1, 2, 3, 4, 5]:
            count = session.query(TrackedRequest).filter(
                and_(
                    TrackedRequest.last_status == status,
                    TrackedRequest.is_active == True
                )
            ).count()
            status_counts[status] = count
        
        # Media type breakdown
        type_counts = {}
        for media_type in ['movie', 'tv', 'anime']:
            count = session.query(TrackedRequest).filter(
                and_(
                    TrackedRequest.media_type == media_type,
                    TrackedRequest.is_active == True
                )
            ).count()
            type_counts[media_type] = count
        
        return {
            'total_requests': total_requests,
            'active_requests': active_requests,
            'completed_requests': completed_requests,
            'status_breakdown': status_counts,
            'type_breakdown': type_counts
        }

    def get_all_requests(self, limit: int = 1000) -> List[TrackedRequest]:
        """
        Get all requests with optional limit.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of TrackedRequest objects
        """
        try:
            with next(get_db()) as session:
                requests = session.query(TrackedRequest).order_by(
                    TrackedRequest.created_at.desc()
                ).limit(limit).all()
                
                # Ensure all attributes are loaded before session closes
                for req in requests:
                    _ = req.media_title, req.media_year, req.media_type, req.last_status, req.jellyseerr_request_id
                
                logger.debug(f"Retrieved {len(requests)} total requests")
                return requests
                
        except Exception as e:
            logger.error(f"Error getting all requests: {e}")
            return []

    def get_statistics(self, period: str) -> Dict[str, Any]:
        """
        Get statistics for a specific time period.
        
        Args:
            period: Time period ('today', 'week', 'month', 'year')
            
        Returns:
            Dictionary with statistics for the period
        """
        try:
            with next(get_db()) as session:
                # Calculate date range based on period
                now = datetime.utcnow()
                if period == 'today':
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                elif period == 'week':
                    start_date = now - timedelta(days=7)
                elif period == 'month':
                    start_date = now - timedelta(days=30)
                elif period == 'year':
                    start_date = now - timedelta(days=365)
                else:
                    # Default to all time
                    start_date = datetime.min
                
                # Get requests in the period
                period_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.created_at >= start_date
                ).all()
                
                # Calculate statistics
                total_requests = len(period_requests)
                completed_requests = len([r for r in period_requests if r.last_status == 5])
                pending_requests = len([r for r in period_requests if r.last_status in [1, 2, 4]])
                processing_requests = len([r for r in period_requests if r.last_status == 3])
                
                # Get active users (users who made requests in this period)
                active_users = len(set(r.discord_user_id for r in period_requests))
                
                # Get popular content (most requested titles)
                title_counts = {}
                for req in period_requests:
                    title = req.media_title
                    title_counts[title] = title_counts.get(title, 0) + 1
                
                popular_content = sorted(title_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                # Get top users (users with most requests)
                user_counts = {}
                for req in period_requests:
                    user_id = req.discord_user_id
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1
                
                top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                # Calculate daily activity (for weekly stats)
                daily_activity = [0] * 7
                if period == 'week':
                    for req in period_requests:
                        day_index = (now - req.created_at).days
                        if 0 <= day_index < 7:
                            daily_activity[6 - day_index] += 1
                
                # Calculate requests per hour (for today stats)
                requests_per_hour = 0
                if period == 'today' and total_requests > 0:
                    hours_elapsed = (now - start_date).total_seconds() / 3600
                    requests_per_hour = total_requests / max(hours_elapsed, 1)
                
                return {
                    'total_requests': total_requests,
                    'completed_requests': completed_requests,
                    'pending_requests': pending_requests,
                    'processing_requests': processing_requests,
                    'active_users': active_users,
                    'popular_content': popular_content,
                    'top_users': top_users,
                    'daily_activity': daily_activity,
                    'requests_per_hour': requests_per_hour,
                    'period': period,
                    'start_date': start_date,
                    'end_date': now
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics for period {period}: {e}")
            return {}

    def cleanup_old_requests(self, days: int = 30) -> int:
        """
        Clean up old inactive requests.
        
        Args:
            days: Number of days to keep completed requests
            
        Returns:
            Number of requests cleaned up
        """
        try:
            with next(get_db()) as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Delete old completed/inactive requests
                deleted = session.query(TrackedRequest).filter(
                    and_(
                        TrackedRequest.is_active == False,
                        TrackedRequest.updated_at < cutoff_date
                    )
                ).delete()
                
                session.commit()
                
                logger.info(f"Cleaned up {deleted} old requests")
                return deleted
                
        except Exception as e:
            logger.error(f"Error cleaning up old requests: {e}")
            return 0
    
    async def process_failed_requests(self) -> Dict[str, int]:
        """
        Process failed requests that are ready for retry.
        
        Returns:
            Dictionary with retry statistics
        """
        stats = {
            'retried': 0,
            'failed_again': 0,
            'max_failures_reached': 0
        }
        
        try:
            with next(get_db()) as session:
                from utils.request_utils import get_retryable_requests
                
                # Get requests ready for retry
                retryable_requests = get_retryable_requests(session, limit=10)  # Process max 10 at a time
                
                logger.info(f"Processing {len(retryable_requests)} failed requests for retry")
                
                for request in retryable_requests:
                    try:
                        # Check if we've exceeded max failures
                        if request.failure_count >= 5:
                            request.is_active = False
                            request.last_error = "Maximum retry attempts exceeded"
                            stats['max_failures_reached'] += 1
                            session.commit()
                            continue
                        
                        # Attempt to resubmit the request
                        context = {
                            'media_id': request.media_id,
                            'media_type': request.media_type,
                            'user_id': request.discord_user_id,
                            'retry_attempt': request.failure_count + 1
                        }
                        
                        async def _retry_submit_coro():
                            return await self.jellyseerr_service.submit_request(request.media_id, request.media_type)
                        
                        media_request, error = await with_timeout_and_retry(
                            _retry_submit_coro,
                            timeout_seconds=30,
                            max_retries=1,
                            context=context
                        )
                        
                        if error:
                            # Still failing, update failure info
                            mark_request_failed(session, request, error.message, error.retry_delay // 60)
                            stats['failed_again'] += 1
                            logger.warning(f"Retry failed for request {request.id}: {error.message}")
                        else:
                            # Success! Update the request
                            request.jellyseerr_request_id = media_request.id
                            mark_request_success(session, request, media_request.status)
                            stats['retried'] += 1
                            logger.info(f"Successfully retried request {request.id} (Jellyseerr: {media_request.id})")
                            
                    except Exception as e:
                        logger.error(f"Error retrying request {request.id}: {e}")
                        mark_request_failed(session, request, str(e))
                        stats['failed_again'] += 1
                
                return stats
                
        except Exception as e:
            logger.error(f"Error processing failed requests: {e}")
            return stats
    
    def _record_status_change(self, session: Session, tracked_request_id: int, 
                            old_status: Optional[int], new_status: int, notes: str = None):
        """
        Record a status change in the history table.
        
        Args:
            session: Database session
            tracked_request_id: ID of the tracked request
            old_status: Previous status (None for initial status)
            new_status: New status
            notes: Optional notes about the change
        """
        try:
            history_entry = RequestStatusHistory(
                tracked_request_id=tracked_request_id,
                old_status=old_status or 0,
                new_status=new_status,
                changed_at=datetime.utcnow(),
                reason=notes
            )
            
            session.add(history_entry)
            session.commit()
            
        except Exception as e:
            logger.error(f"Error recording status change: {e}")
            # Don't raise exception as this is not critical
"""
Shared request submission service for SlinkBot.

This module consolidates request submission logic that was previously
duplicated across command files and UI components.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import discord
from discord import Embed, Color

from database.models import TrackedRequest
from services.jellyseerr import JellyseerrService
from models.media import MediaRequest, MediaSearchResult
from utils.logging_config import get_logger
from utils.status_manager import StatusManager
from utils.database_session import with_database_session, database_session
from utils.request_utils import check_duplicate_request, generate_request_hash
from utils.error_handling import MediaRequestError, ErrorType, error_handler
from utils.emoji_constants import *
from utils.version import get_footer_text

logger = get_logger(__name__)


class RequestSubmissionResult:
    """
    Result object for request submission operations.
    """
    
    def __init__(self, success: bool, message: str, request_id: Optional[int] = None, 
                 embed: Optional[Embed] = None, error_type: Optional[ErrorType] = None):
        self.success = success
        self.message = message
        self.request_id = request_id
        self.embed = embed
        self.error_type = error_type


class RequestService:
    """
    Centralized service for handling media request submissions.
    
    This service consolidates all request submission logic, including
    duplicate detection, validation, submission to Jellyseerr, and
    database tracking.
    """
    
    def __init__(self, jellyseerr_service: JellyseerrService, request_manager, notifier):
        """
        Initialize the request service.
        
        Args:
            jellyseerr_service: Jellyseerr API service instance
            request_manager: Request manager for database operations
            notifier: Notification service for status updates
        """
        self.jellyseerr_service = jellyseerr_service
        self.request_manager = request_manager
        self.notifier = notifier
    
    @with_database_session
    async def submit_request(self, session, user_id: int, channel_id: int, 
                           media_result: MediaSearchResult, 
                           poster_url: Optional[str] = None) -> RequestSubmissionResult:
        """
        Submit a new media request with full validation and error handling.
        
        Args:
            session: Database session
            user_id: Discord user ID making the request
            channel_id: Discord channel ID where request was made
            media_result: Media search result to request
            poster_url: Optional poster image URL
            
        Returns:
            RequestSubmissionResult with success status and details
        """
        try:
            # Check for duplicate requests
            duplicate = check_duplicate_request(
                session, media_result.id, media_result.media_type, user_id
            )
            
            if duplicate:
                return RequestSubmissionResult(
                    success=False,
                    message=f"You already have a request for **{media_result.title}** ({media_result.year})",
                    embed=self._create_duplicate_embed(duplicate, media_result),
                    error_type=ErrorType.DUPLICATE_REQUEST
                )
            
            # Submit to Jellyseerr
            jellyseerr_result = await self._submit_to_jellyseerr(media_result, user_id)
            
            if not jellyseerr_result.success:
                return RequestSubmissionResult(
                    success=False,
                    message=jellyseerr_result.message,
                    error_type=jellyseerr_result.error_type
                )
            
            # Create database record
            tracked_request = await self._create_database_record(
                session, user_id, channel_id, media_result, 
                jellyseerr_result.request_id, poster_url
            )
            
            # Create success embed
            success_embed = self._create_success_embed(tracked_request, media_result)
            
            # Send notification
            if self.notifier:
                await self.notifier.send_request_confirmation(
                    tracked_request, channel_id
                )
            
            return RequestSubmissionResult(
                success=True,
                message=f"Successfully requested **{media_result.title}**",
                request_id=tracked_request.id,
                embed=success_embed
            )
            
        except MediaRequestError as e:
            logger.error(f"Media request error for user {user_id}: {e}")
            return RequestSubmissionResult(
                success=False,
                message=str(e),
                error_type=e.error_type
            )
        except Exception as e:
            logger.error(f"Unexpected error in request submission: {e}")
            return RequestSubmissionResult(
                success=False,
                message="An unexpected error occurred while processing your request.",
                error_type=ErrorType.UNKNOWN_ERROR
            )
    
    async def _submit_to_jellyseerr(self, media_result: MediaSearchResult, 
                                   user_id: int) -> RequestSubmissionResult:
        """
        Submit request to Jellyseerr service.
        
        Args:
            media_result: Media to request
            user_id: Discord user making the request
            
        Returns:
            RequestSubmissionResult with Jellyseerr response
        """
        try:
            # Create MediaRequest object
            media_request = MediaRequest(
                media_id=media_result.id,
                media_type=media_result.media_type,
                user_id=user_id
            )
            
            # Submit to Jellyseerr
            jellyseerr_response = await self.jellyseerr_service.submit_request(media_request)
            
            if jellyseerr_response.get('success'):
                return RequestSubmissionResult(
                    success=True,
                    message="Request submitted to Jellyseerr",
                    request_id=jellyseerr_response.get('id')
                )
            else:
                error_msg = jellyseerr_response.get('message', 'Unknown error')
                return RequestSubmissionResult(
                    success=False,
                    message=f"Jellyseerr error: {error_msg}",
                    error_type=ErrorType.SERVICE_UNAVAILABLE
                )
                
        except Exception as e:
            logger.error(f"Error submitting to Jellyseerr: {e}")
            return RequestSubmissionResult(
                success=False,
                message=f"Failed to submit request to Jellyseerr: {str(e)}",
                error_type=ErrorType.SERVICE_UNAVAILABLE
            )
    
    async def _create_database_record(self, session, user_id: int, channel_id: int,
                                    media_result: MediaSearchResult, 
                                    jellyseerr_request_id: int,
                                    poster_url: Optional[str]) -> TrackedRequest:
        """
        Create database record for the request.
        
        Args:
            session: Database session
            user_id: Discord user ID
            channel_id: Discord channel ID
            media_result: Media search result
            jellyseerr_request_id: ID from Jellyseerr
            poster_url: Optional poster URL
            
        Returns:
            Created TrackedRequest object
        """
        tracked_request = TrackedRequest(
            jellyseerr_request_id=jellyseerr_request_id,
            discord_user_id=user_id,
            discord_channel_id=channel_id,
            media_title=media_result.title,
            media_year=str(media_result.year),
            media_type=media_result.media_type,
            media_id=media_result.id,
            poster_url=poster_url,
            last_status=1,  # Pending approval
            request_hash=generate_request_hash(media_result.id, media_result.media_type, user_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(tracked_request)
        session.commit()
        session.refresh(tracked_request)
        
        logger.info(f"Created request record {tracked_request.id} for {media_result.title}")
        return tracked_request
    
    def _create_success_embed(self, tracked_request: TrackedRequest, 
                            media_result: MediaSearchResult) -> Embed:
        """
        Create success embed for request submission.
        
        Args:
            tracked_request: Database record
            media_result: Media search result
            
        Returns:
            Discord embed object
        """
        embed = Embed(
            title=f"{REQUEST_SUCCESS} Request Submitted",
            description=f"**{media_result.title}** ({media_result.year})",
            color=StatusManager.get_status_color(tracked_request.last_status),
            timestamp=datetime.utcnow()
        )
        
        # Add media type and status
        media_emoji = get_media_type_emoji(media_result.media_type)
        embed.add_field(
            name="Media Type",
            value=f"{media_emoji} {media_result.media_type.title()}",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value=StatusManager.get_status_display(tracked_request.last_status),
            inline=True
        )
        
        embed.add_field(
            name="Request ID",
            value=f"`{tracked_request.id}`",
            inline=True
        )
        
        # Add poster if available
        if tracked_request.poster_url:
            embed.set_thumbnail(url=tracked_request.poster_url)
        
        # Add footer
        embed.set_footer(text=get_footer_text())
        
        return embed
    
    def _create_duplicate_embed(self, duplicate_request: TrackedRequest, 
                               media_result: MediaSearchResult) -> Embed:
        """
        Create embed for duplicate request notification.
        
        Args:
            duplicate_request: Existing request record
            media_result: Media search result
            
        Returns:
            Discord embed object
        """
        embed = Embed(
            title=f"{WARNING} Duplicate Request",
            description=f"You already have a request for **{media_result.title}** ({media_result.year})",
            color=0xFFAA00,  # Orange
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Current Status",
            value=StatusManager.get_status_display(duplicate_request.last_status),
            inline=True
        )
        
        embed.add_field(
            name="Request ID",
            value=f"`{duplicate_request.id}`",
            inline=True
        )
        
        embed.add_field(
            name="Requested",
            value=f"<t:{int(duplicate_request.created_at.timestamp())}:R>",
            inline=True
        )
        
        if duplicate_request.poster_url:
            embed.set_thumbnail(url=duplicate_request.poster_url)
        
        embed.set_footer(text=get_footer_text())
        
        return embed
    
    @with_database_session
    async def batch_submit_requests(self, session, requests: List[Dict[str, Any]]) -> List[RequestSubmissionResult]:
        """
        Submit multiple requests in batch.
        
        Args:
            session: Database session
            requests: List of request dictionaries
            
        Returns:
            List of RequestSubmissionResult objects
        """
        results = []
        
        for request_data in requests:
            try:
                result = await self.submit_request(
                    session,
                    request_data['user_id'],
                    request_data['channel_id'],
                    request_data['media_result'],
                    request_data.get('poster_url')
                )
                results.append(result)
                
                # Add small delay between requests to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in batch request submission: {e}")
                results.append(RequestSubmissionResult(
                    success=False,
                    message=f"Failed to process request: {str(e)}",
                    error_type=ErrorType.UNKNOWN_ERROR
                ))
        
        return results
    
    async def get_request_status(self, request_id: int) -> Optional[Dict[str, Any]]:
        """
        Get current status of a request.
        
        Args:
            request_id: Request ID to check
            
        Returns:
            Dictionary with request status information
        """
        try:
            with database_session() as session:
                request = session.query(TrackedRequest).filter_by(id=request_id).first()
                
                if not request:
                    return None
                
                return {
                    'id': request.id,
                    'title': request.media_title,
                    'year': request.media_year,
                    'status': request.last_status,
                    'status_display': StatusManager.get_status_display(request.last_status),
                    'created_at': request.created_at,
                    'updated_at': request.updated_at,
                    'is_final': StatusManager.is_final_status(request.last_status)
                }
                
        except Exception as e:
            logger.error(f"Error getting request status: {e}")
            return None
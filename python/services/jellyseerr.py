"""
Jellyseerr service implementation for media requests and search.
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from services.base import BaseService
from models.media import MediaSearchResult, MediaRequest
from utils.error_handling import error_handler

logger = logging.getLogger(__name__)


class JellyseerrService(BaseService):
    """Service for interacting with Jellyseerr API."""
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Jellyseerr API requests."""
        return {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def _get_health_endpoint(self) -> str:
        """Get health check endpoint for Jellyseerr."""
        return '/api/v1/status'
    
    async def search_media(self, query: str, media_type: Optional[str] = None, page: int = 1) -> List[MediaSearchResult]:
        """
        Search for media in Jellyseerr.
        
        Args:
            query: Search query string
            media_type: Filter by media type ('movie', 'tv', 'anime')
            page: Page number for results
            
        Returns:
            List of MediaSearchResult objects
        """
        encoded_query = quote(query)
        params = {
            'query': encoded_query,
            'page': page,
            'language': 'en'
        }
        
        logger.info(f"Searching for media: {query} (type: {media_type})")
        
        try:
            data = await self._make_request('GET', '/api/v1/search', params=params)
            results = data.get('results', [])
            
            # Filter by media type if specified
            if media_type:
                # Handle anime as TV type
                filter_type = 'tv' if media_type == 'anime' else media_type
                results = [r for r in results if r.get('mediaType') == filter_type]
            
            # Convert to MediaSearchResult objects
            search_results = []
            for result in results:
                try:
                    search_results.append(MediaSearchResult.from_api_data(result))
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
                    continue
            
            logger.info(f"Found {len(search_results)} results for query: {query}")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise
    
    async def submit_request(self, media_id: int, media_type: str) -> MediaRequest:
        """
        Submit a media request to Jellyseerr.
        
        Args:
            media_id: ID of the media to request
            media_type: Type of media ('movie', 'tv', 'anime')
            
        Returns:
            MediaRequest object
        """
        # Handle anime as TV type
        request_type = 'tv' if media_type == 'anime' else media_type
        
        payload = {
            'mediaType': request_type,
            'mediaId': media_id
        }
        
        logger.info(f"Submitting request for {media_type} ID: {media_id}")
        
        try:
            data = await self._make_request('POST', '/api/v1/request', json=payload)
            request = MediaRequest.from_api_data(data)
            
            logger.info(f"Request submitted successfully: {request.title} (ID: {request.id})")
            return request
            
        except Exception as e:
            logger.error(f"Failed to submit request for {media_type} ID {media_id}: {e}")
            raise
    
    async def get_request_status(self, request_id: int) -> Optional[MediaRequest]:
        """
        Get status of a specific request.
        
        Args:
            request_id: ID of the request to check
            
        Returns:
            MediaRequest object if found, None otherwise
        """
        try:
            data = await self._make_request('GET', f'/api/v1/request/{request_id}')
            return MediaRequest.from_api_data(data)
            
        except Exception as e:
            logger.warning(f"Failed to get request status for ID {request_id}: {e}")
            return None
    
    async def get_all_requests(self, status_filter: Optional[str] = None, take: int = 100) -> List[MediaRequest]:
        """
        Get all requests with optional filtering.
        
        Args:
            status_filter: Filter by status ('pending', 'approved', 'available', etc.)
            take: Number of requests to retrieve
            
        Returns:
            List of MediaRequest objects
        """
        params = {
            'take': take,
            'sort': 'added'
        }
        
        if status_filter:
            params['filter'] = status_filter
        
        try:
            data = await self._make_request('GET', '/api/v1/request', params=params)
            results = data.get('results', [])
            
            requests = []
            for result in results:
                try:
                    requests.append(MediaRequest.from_api_data(result))
                except Exception as e:
                    logger.warning(f"Failed to parse request data: {e}")
                    continue
            
            logger.info(f"Retrieved {len(requests)} requests")
            return requests
            
        except Exception as e:
            logger.error(f"Failed to retrieve requests: {e}")
            raise
    
    async def get_user_requests(self, user_id: int, status_filter: Optional[str] = None) -> List[MediaRequest]:
        """
        Get requests for a specific user.
        
        Args:
            user_id: Discord user ID
            status_filter: Filter by status
            
        Returns:
            List of MediaRequest objects for the user
        """
        all_requests = await self.get_all_requests(status_filter)
        
        # Filter by user ID (this is a simplification - in practice you'd want
        # to map Discord user IDs to Jellyseerr user IDs)
        user_requests = [req for req in all_requests if req.requester_id == user_id]
        
        logger.info(f"Found {len(user_requests)} requests for user {user_id}")
        return user_requests
    
    async def cancel_request(self, request_id: int) -> bool:
        """
        Cancel a media request.
        
        Args:
            request_id: ID of the request to cancel
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            await self._make_request('DELETE', f'/api/v1/request/{request_id}')
            logger.info(f"Request {request_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel request {request_id}: {e}")
            return False
    
    async def find_request_by_media_id(self, media_id: int, media_type: str) -> Optional[MediaRequest]:
        """
        Find a request by media ID and type.
        
        Args:
            media_id: TMDB/TVDB ID of the media
            media_type: Type of media ('movie', 'tv')
            
        Returns:
            MediaRequest object if found, None otherwise
        """
        try:
            all_requests = await self.get_all_requests()
            
            # Determine which ID field to check
            id_key = 'tmdbId' if media_type == 'movie' else 'tvdbId'
            
            for request in all_requests:
                if request.media_id == media_id:
                    return request
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find request for media ID {media_id}: {e}")
            return None
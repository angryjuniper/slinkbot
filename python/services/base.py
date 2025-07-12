"""
Base service class for all external API integrations.
Provides common functionality for error handling, retries, and health checks.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from functools import wraps

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from utils.error_handling import ErrorType, MediaRequestError, ErrorHandler, with_timeout_and_retry, error_handler

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for all external service integrations."""
    
    def __init__(self, base_url: str, api_key: str, service_name: str):
        """
        Initialize the service with basic configuration.
        
        Args:
            base_url: The base URL for the service API
            api_key: API key for authentication
            service_name: Human-readable name for the service
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.service_name = service_name
        self.session = requests.Session()
        self.session.headers.update(self._get_headers())
        self._last_health_check = 0
        self._health_check_interval = 60  # seconds
        self._is_healthy = None
    
    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _get_health_endpoint(self) -> str:
        """Get health check endpoint for service. Must be implemented by subclasses."""
        pass
    
    async def _make_request(self, method: str, endpoint: str, timeout: int = 10, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for requests
            
        Returns:
            JSON response data
            
        Raises:
            APIError: If the API returns an error response
            ServiceError: If the service is unavailable
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async def request_coro():
            try:
                logger.debug(f"Making {method} request to {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=timeout,
                    **kwargs
                )
                response.raise_for_status()
                
                # Try to parse JSON response
                try:
                    return response.json()
                except ValueError:
                    # If response is not JSON, return empty dict
                    return {}
            except Timeout:
                logger.error(f"{self.service_name} request timed out: {url}")
                raise MediaRequestError(ErrorType.TIMEOUT, f"{self.service_name} request timed out")
            except ConnectionError:
                logger.error(f"Cannot connect to {self.service_name}: {url}")
                raise MediaRequestError(ErrorType.NETWORK_ERROR, f"Cannot connect to {self.service_name}")
            except requests.exceptions.HTTPError as e:
                if e.response is not None:
                    logger.error(f"{self.service_name} API error {e.response.status_code}: {url}")
                    raise MediaRequestError(ErrorType.UNKNOWN_ERROR, f"{self.service_name} API error: {str(e)}")
                else:
                    logger.error(f"{self.service_name} HTTP error: {e}")
                    raise MediaRequestError(ErrorType.UNKNOWN_ERROR, f"{self.service_name} HTTP error")
            except RequestException as e:
                logger.error(f"{self.service_name} request failed: {e}")
                raise MediaRequestError(ErrorType.UNKNOWN_ERROR, f"{self.service_name} request failed: {str(e)}")

        result, error = await with_timeout_and_retry(request_coro, timeout_seconds=timeout, max_retries=3, retry_delay=1)
        if error:
            raise error
        return result
    
    async def health_check(self) -> bool:
        """
        Check if service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        current_time = time.time()
        
        # Use cached result if recent
        if (self._is_healthy is not None and 
            current_time - self._last_health_check < self._health_check_interval):
            return self._is_healthy
        
        try:
            await self._make_request('GET', self._get_health_endpoint(), timeout=5)
            self._is_healthy = True
            logger.debug(f"{self.service_name} health check passed")
        except Exception as e:
            self._is_healthy = False
            logger.warning(f"{self.service_name} health check failed: {e}")
        
        self._last_health_check = current_time
        return self._is_healthy
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get basic service information.
        
        Returns:
            Dictionary containing service information
        """
        return {
            'name': self.service_name,
            'base_url': self.base_url,
            'healthy': self._is_healthy,
            'last_health_check': self._last_health_check
        }
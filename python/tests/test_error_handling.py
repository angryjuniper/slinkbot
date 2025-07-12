"""Unit tests for error handling system."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import discord

from utils.error_handling import MediaRequestError, ErrorType


class TestMediaRequestError:
    def test_media_request_error_inheritance(self):
        error = MediaRequestError(ErrorType.SERVICE_UNAVAILABLE, "Service failed")
        assert isinstance(error, Exception)
        assert str(error) == "Service failed"

    def test_media_request_error_context(self):
        error = MediaRequestError(ErrorType.UNKNOWN_ERROR, "Not found", context={"url": "/api/test"})
        assert error.error_type == ErrorType.UNKNOWN_ERROR
        assert error.message == "Not found"
        assert error.context == {"url": "/api/test"} 
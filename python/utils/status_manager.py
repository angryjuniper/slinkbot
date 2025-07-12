"""
Centralized status management for SlinkBot media requests.

This module consolidates all status-related operations, emoji mapping,
and display logic into a single, maintainable class.
"""

from enum import IntEnum
from typing import Dict, Any, Optional
from utils.logging_config import get_logger

logger = get_logger(__name__)


class RequestStatus(IntEnum):
    """Enumeration of all possible request statuses."""
    PENDING_APPROVAL = 1
    APPROVED = 2  
    PROCESSING = 3
    PARTIALLY_AVAILABLE = 4
    AVAILABLE = 5


class StatusManager:
    """
    Centralized manager for all status-related operations.
    
    This class handles status display, emoji mapping, validation,
    and status transitions for media requests.
    """
    
    # Status display mapping
    STATUS_DISPLAY = {
        RequestStatus.PENDING_APPROVAL: "🟡 Pending Approval",
        RequestStatus.APPROVED: "👍 Approved",
        RequestStatus.PROCESSING: "⏳ Processing",
        RequestStatus.PARTIALLY_AVAILABLE: "🎬 Partially Available", 
        RequestStatus.AVAILABLE: "✅ Available"
    }
    
    # Emoji-only mapping for compact display
    STATUS_EMOJI = {
        RequestStatus.PENDING_APPROVAL: "🟡",
        RequestStatus.APPROVED: "👍",
        RequestStatus.PROCESSING: "⏳",
        RequestStatus.PARTIALLY_AVAILABLE: "🎬",
        RequestStatus.AVAILABLE: "✅"
    }
    
    # Text-only mapping for accessibility
    STATUS_TEXT = {
        RequestStatus.PENDING_APPROVAL: "Pending Approval",
        RequestStatus.APPROVED: "Approved",
        RequestStatus.PROCESSING: "Processing",
        RequestStatus.PARTIALLY_AVAILABLE: "Partially Available",
        RequestStatus.AVAILABLE: "Available"
    }
    
    # Color mapping for embeds
    STATUS_COLORS = {
        RequestStatus.PENDING_APPROVAL: 0xFFFF00,  # Yellow
        RequestStatus.APPROVED: 0x00FF00,          # Green
        RequestStatus.PROCESSING: 0x0099FF,        # Blue
        RequestStatus.PARTIALLY_AVAILABLE: 0xFF9900,  # Orange
        RequestStatus.AVAILABLE: 0x00CC00          # Dark Green
    }
    
    # Final statuses that don't change
    FINAL_STATUSES = {RequestStatus.AVAILABLE}
    
    # Statuses that indicate successful completion
    COMPLETED_STATUSES = {RequestStatus.AVAILABLE}
    
    # Valid status transitions (from -> to)
    VALID_TRANSITIONS = {
        RequestStatus.PENDING_APPROVAL: {
            RequestStatus.APPROVED,
            RequestStatus.PROCESSING,  # Direct approval bypass
            RequestStatus.AVAILABLE    # Instant availability (rare)
        },
        RequestStatus.APPROVED: {
            RequestStatus.PROCESSING,
            RequestStatus.AVAILABLE,   # Direct to available
            RequestStatus.PARTIALLY_AVAILABLE
        },
        RequestStatus.PROCESSING: {
            RequestStatus.PARTIALLY_AVAILABLE,
            RequestStatus.AVAILABLE,
            RequestStatus.APPROVED     # Fallback if processing fails
        },
        RequestStatus.PARTIALLY_AVAILABLE: {
            RequestStatus.AVAILABLE,
            RequestStatus.PROCESSING   # Re-processing
        },
        RequestStatus.AVAILABLE: set()  # Final status, no transitions
    }
    
    @classmethod
    def get_status_display(cls, status: int, format_type: str = "full") -> str:
        """
        Get human-readable status string.
        
        Args:
            status: Integer status code
            format_type: Display format ("full", "emoji", "text")
            
        Returns:
            Formatted status string
        """
        try:
            status_enum = RequestStatus(status)
        except ValueError:
            logger.warning(f"Unknown status code: {status}")
            return "❓ Unknown"
        
        if format_type == "emoji":
            return cls.STATUS_EMOJI.get(status_enum, "❓")
        elif format_type == "text":
            return cls.STATUS_TEXT.get(status_enum, "Unknown")
        else:  # full
            return cls.STATUS_DISPLAY.get(status_enum, "❓ Unknown")
    
    @classmethod
    def get_status_emoji(cls, status: int) -> str:
        """Get emoji for status (convenience method)."""
        return cls.get_status_display(status, "emoji")
    
    @classmethod
    def get_status_text(cls, status: int) -> str:
        """Get text for status (convenience method)."""
        return cls.get_status_display(status, "text")
    
    @classmethod
    def get_status_color(cls, status: int) -> int:
        """
        Get color code for status embeds.
        
        Args:
            status: Integer status code
            
        Returns:
            Hex color code as integer
        """
        try:
            status_enum = RequestStatus(status)
            return cls.STATUS_COLORS.get(status_enum, 0x808080)  # Gray for unknown
        except ValueError:
            return 0x808080  # Gray for invalid status
    
    @classmethod
    def is_final_status(cls, status: int) -> bool:
        """
        Check if status is final (no further changes expected).
        
        Args:
            status: Integer status code
            
        Returns:
            True if status is final
        """
        try:
            status_enum = RequestStatus(status)
            return status_enum in cls.FINAL_STATUSES
        except ValueError:
            return False
    
    @classmethod
    def is_completed_status(cls, status: int) -> bool:
        """
        Check if status indicates successful completion.
        
        Args:
            status: Integer status code
            
        Returns:
            True if status indicates completion
        """
        try:
            status_enum = RequestStatus(status)
            return status_enum in cls.COMPLETED_STATUSES
        except ValueError:
            return False
    
    @classmethod
    def can_transition_to(cls, from_status: int, to_status: int) -> bool:
        """
        Check if status transition is valid.
        
        Args:
            from_status: Current status code
            to_status: Target status code
            
        Returns:
            True if transition is valid
        """
        try:
            from_enum = RequestStatus(from_status)
            to_enum = RequestStatus(to_status)
            
            valid_targets = cls.VALID_TRANSITIONS.get(from_enum, set())
            return to_enum in valid_targets
        except ValueError:
            logger.warning(f"Invalid status transition: {from_status} -> {to_status}")
            return False
    
    @classmethod
    def get_valid_transitions(cls, from_status: int) -> Dict[int, str]:
        """
        Get all valid status transitions from current status.
        
        Args:
            from_status: Current status code
            
        Returns:
            Dictionary mapping status codes to display names
        """
        try:
            from_enum = RequestStatus(from_status)
            valid_targets = cls.VALID_TRANSITIONS.get(from_enum, set())
            
            return {
                status.value: cls.get_status_display(status.value)
                for status in valid_targets
            }
        except ValueError:
            return {}
    
    @classmethod
    def get_all_statuses(cls) -> Dict[int, str]:
        """
        Get all available statuses.
        
        Returns:
            Dictionary mapping status codes to display names
        """
        return {
            status.value: cls.get_status_display(status.value)
            for status in RequestStatus
        }
    
    @classmethod
    def validate_status(cls, status: int) -> bool:
        """
        Validate if status code is valid.
        
        Args:
            status: Status code to validate
            
        Returns:
            True if status is valid
        """
        try:
            RequestStatus(status)
            return True
        except ValueError:
            return False
    
    @classmethod
    def get_status_summary(cls, status: int) -> Dict[str, Any]:
        """
        Get comprehensive status information.
        
        Args:
            status: Status code
            
        Returns:
            Dictionary with all status information
        """
        if not cls.validate_status(status):
            return {
                'status': status,
                'display': "❓ Unknown",
                'emoji': "❓",
                'text': "Unknown",
                'color': 0x808080,
                'is_final': False,
                'is_completed': False,
                'valid_transitions': {}
            }
        
        return {
            'status': status,
            'display': cls.get_status_display(status),
            'emoji': cls.get_status_emoji(status),
            'text': cls.get_status_text(status),
            'color': cls.get_status_color(status),
            'is_final': cls.is_final_status(status),
            'is_completed': cls.is_completed_status(status),
            'valid_transitions': cls.get_valid_transitions(status)
        }


# Convenience functions for backward compatibility
def get_status_display(status: int) -> str:
    """Get human-readable status string (backward compatibility)."""
    return StatusManager.get_status_display(status)


def get_status_emoji(status: int) -> str:
    """Get emoji for status (backward compatibility)."""
    return StatusManager.get_status_emoji(status)


def get_status_text(status: int) -> str:
    """Get text for status (backward compatibility)."""
    return StatusManager.get_status_text(status)
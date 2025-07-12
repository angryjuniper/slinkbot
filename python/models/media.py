"""
Data models for media-related objects.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class MediaSearchResult:
    """Represents a media search result from external APIs."""
    
    id: int
    title: str
    year: str
    overview: str
    media_type: str
    poster_path: Optional[str] = None
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'MediaSearchResult':
        """
        Create instance from API response data.
        
        Args:
            data: Raw API response data
            
        Returns:
            MediaSearchResult instance
        """
        # Handle both movie and TV show title fields
        title = data.get('title') or data.get('name', 'Unknown')
        
        # Extract year from release date
        year = cls._extract_year(data.get('releaseDate') or data.get('firstAirDate'))
        
        return cls(
            id=data['id'],
            title=title,
            year=year,
            overview=data.get('overview', 'No description available'),
            media_type=data['mediaType'],
            poster_path=data.get('posterPath')
        )
    
    @staticmethod
    def _extract_year(date_str: Optional[str]) -> str:
        """Extract year from date string."""
        if date_str and len(date_str) >= 4:
            return date_str[:4]
        return "TBA"


@dataclass
class MediaRequest:
    """Represents a media request in the system."""
    
    id: int
    media_id: int
    media_type: str
    title: str
    year: str
    status: int
    requester_id: int
    requester_name: str
    created_at: datetime
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'MediaRequest':
        """
        Create instance from API response data.
        
        Args:
            data: Raw API response data
            
        Returns:
            MediaRequest instance
        """
        media_info = data.get('media', {})
        requester_info = data.get('requestedBy', {})
        
        # Handle both movie and TV show title fields
        title = media_info.get('title') or media_info.get('name', 'Unknown')
        
        # Extract year from release date
        year = cls._extract_year(media_info.get('releaseDate') or media_info.get('firstAirDate'))
        
        # Parse creation date
        created_at_str = data.get('createdAt', '')
        try:
            # Remove 'Z' suffix and add timezone info
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            created_at = datetime.utcnow()
        
        return cls(
            id=data['id'],
            media_id=media_info.get('id', 0),
            media_type=data.get('type', 'unknown'),
            title=title,
            year=year,
            status=data.get('status', 0),
            requester_id=requester_info.get('id', 0),
            requester_name=requester_info.get('displayName', 'Unknown'),
            created_at=created_at
        )
    
    @staticmethod
    def _extract_year(date_str: Optional[str]) -> str:
        """Extract year from date string."""
        if date_str and len(date_str) >= 4:
            return date_str[:4]
        return "TBA"
    
    def get_status_display(self) -> str:
        """Get human-readable status string."""
        status_map = {
            1: "🟡 Pending Approval",
            2: "👍 Approved", 
            3: "⏳ Processing",
            4: "🎬 Partially Available",
            5: "✅ Available"
        }
        return status_map.get(self.status, "❓ Unknown")
    
    def is_final_status(self) -> bool:
        """Check if request is in a final state."""
        return self.status == 5  # Available
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'media_id': self.media_id,
            'media_type': self.media_type,
            'title': self.title,
            'year': self.year,
            'status': self.status,
            'requester_id': self.requester_id,
            'requester_name': self.requester_name,
            'created_at': self.created_at.isoformat()
        }
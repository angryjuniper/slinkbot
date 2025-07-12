"""
Emoji constants for consistent usage across SlinkBot notifications and UI components.
"""

# Status Emojis
STATUS_PENDING = "⏳"         # Pending Approval
STATUS_APPROVED = "✅"        # Approved  
STATUS_DOWNLOADING = "⬇️"     # Downloading
STATUS_PREPARING = "🔄"      # Preparing
STATUS_AVAILABLE = "🎉"      # Available
STATUS_DECLINED = "❌"       # Declined
STATUS_UNKNOWN = "❓"        # Unknown

# Media Type Emojis
MEDIA_MOVIE = "🎬"           # Movies
MEDIA_TV = "📺"              # TV Shows
MEDIA_ANIME = "📺"           # Anime (same as TV)
MEDIA_MUSIC = "🎵"           # Music
MEDIA_BOOK = "📚"            # Books

# System Status Emojis
SYSTEM_ONLINE = "🐈‍⬛"         # Bot online (black cat)
SYSTEM_OFFLINE = "💤"        # Bot offline
SYSTEM_ERROR = "🚨"          # System error
SYSTEM_WARNING = "⚠️"        # Warning
SYSTEM_SUCCESS = "✅"        # Success
SYSTEM_INFO = "ℹ️"           # Information

# Service Health Emojis
SERVICE_HEALTHY = "✅"       # Service healthy
SERVICE_UNHEALTHY = "❌"     # Service unhealthy
SERVICE_RECOVERED = "🔧"     # Service recovered
SERVICE_DEGRADED = "⚠️"      # Service degraded

# Action Emojis
ACTION_REFRESH = "🔄"        # Refresh
ACTION_SYNC = "⚡"           # Sync
ACTION_CANCEL = "❌"         # Cancel
ACTION_APPROVE = "✅"        # Approve
ACTION_SEARCH = "🔍"         # Search
ACTION_FILTER = "🔽"         # Filter
ACTION_SORT = "📊"           # Sort

# Media Actions
MEDIA_STREAM = "🍿"          # Ready to stream
MEDIA_REQUEST = "📝"         # Request
MEDIA_DOWNLOAD = "⬇️"        # Download
MEDIA_ARRIVAL = "🎉"         # Media arrival

# Navigation Emojis
NAV_PREVIOUS = "⬅️"          # Previous page
NAV_NEXT = "➡️"              # Next page
NAV_FIRST = "⏪"             # First page
NAV_LAST = "⏩"              # Last page

# Storage Emojis
STORAGE_NORMAL = "🟢"        # Normal storage
STORAGE_WARNING = "🟡"       # Warning storage
STORAGE_CRITICAL = "🔴"      # Critical storage
STORAGE_INFO = "💾"          # Storage info

# Database Emojis
DB_HEALTHY = "💚"            # Database healthy
DB_UNHEALTHY = "💔"          # Database unhealthy
DB_SYNC = "🔄"               # Database sync
DB_STATS = "📊"              # Database stats

# Notification Categories
NOTIFY_SUCCESS = "✅"        # Success notification
NOTIFY_ERROR = "❌"          # Error notification
NOTIFY_WARNING = "⚠️"        # Warning notification
NOTIFY_INFO = "ℹ️"           # Info notification
NOTIFY_ARRIVAL = "🎉"        # Media arrival notification

# User Interface
UI_SETTINGS = "⚙️"           # Settings
UI_HELP = "❓"               # Help
UI_ADMIN = "👑"              # Admin
UI_USER = "👤"               # User
UI_TIME = "🕒"               # Time

# Quality/Priority
PRIORITY_HIGH = "🔥"         # High priority
PRIORITY_MEDIUM = "📋"       # Medium priority  
PRIORITY_LOW = "📝"          # Low priority

# Status functions moved to utils.status_manager for centralized management

def get_media_type_emoji(media_type: str) -> str:
    """Get emoji for media type."""
    media_map = {
        'movie': MEDIA_MOVIE,
        'tv': MEDIA_TV,
        'anime': MEDIA_ANIME,
        'music': MEDIA_MUSIC,
        'book': MEDIA_BOOK
    }
    return media_map.get(media_type.lower(), MEDIA_MOVIE)

def get_service_status_emoji(is_healthy: bool) -> str:
    """Get emoji for service health status."""
    return SERVICE_HEALTHY if is_healthy else SERVICE_UNHEALTHY

def get_storage_status_emoji(usage_percent: float) -> str:
    """Get emoji for storage usage percentage."""
    if usage_percent > 90:
        return STORAGE_CRITICAL
    elif usage_percent > 80:
        return STORAGE_WARNING
    else:
        return STORAGE_NORMAL
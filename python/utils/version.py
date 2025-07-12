"""
Version management utility for SlinkBot.
Reads version from VERSION file and provides consistent version strings.
"""

import os
from pathlib import Path

def get_version() -> str:
    """
    Get the current version from the VERSION file.
    
    Returns:
        str: Current version string (e.g., "Alpha v0.1.0")
    """
    try:
        # Get the project root directory (go up from python/utils/ to main directory)
        project_root = Path(__file__).parent.parent.parent
        version_file = project_root / "VERSION"
        
        if version_file.exists():
            with open(version_file, 'r', encoding='utf-8') as f:
                version = f.read().strip()
                return version
        else:
            # Fallback version if file doesn't exist
            return "Alpha v0.1.0"
    except Exception:
        # Fallback version on any error
        return "Alpha v0.1.0"

def get_version_short() -> str:
    """
    Get the short version number (e.g., "v0.1.0" from "Alpha v0.1.0").
    
    Returns:
        str: Short version string
    """
    full_version = get_version()
    # Extract version number after "Alpha " or similar prefix
    if "v" in full_version:
        return full_version.split()[-1]  # Get the last part (v0.1.0)
    return full_version

def get_version_numeric() -> str:
    """
    Get just the numeric version (e.g., "0.1.0" from "Alpha v0.1.0").
    
    Returns:
        str: Numeric version string
    """
    short_version = get_version_short()
    if short_version.startswith('v'):
        return short_version[1:]  # Remove the 'v' prefix
    return short_version

def get_bot_description() -> str:
    """
    Get a standardized bot description with current version.
    
    Returns:
        str: Bot description string
    """
    version = get_version()
    return f"SlinkBot {version} - Enhanced Media Request System"

def get_footer_text(suffix: str = "") -> str:
    """
    Get standardized footer text for embeds.
    
    Args:
        suffix: Optional suffix to append (e.g., "• Media Server Storage")
    
    Returns:
        str: Footer text with version
    """
    version = get_version()
    base_text = f"SlinkBot {version}"
    if suffix:
        return f"{base_text} • {suffix}"
    return base_text

# Version constants for easy import
VERSION = get_version()
VERSION_SHORT = get_version_short()
VERSION_NUMERIC = get_version_numeric()
BOT_DESCRIPTION = get_bot_description()
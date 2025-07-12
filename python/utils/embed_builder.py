"""
Centralized embed creation utilities for SlinkBot Discord embeds.

This module provides reusable embed builders and templates to ensure
consistent styling and reduce code duplication across the application.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import discord
from discord import Embed, Color

from utils.status_manager import StatusManager
from utils.emoji_constants import *
from utils.version import get_footer_text
from utils.logging_config import get_logger

logger = get_logger(__name__)


class EmbedBuilder:
    """
    Builder class for creating consistent Discord embeds.
    
    Provides a fluent interface for building embeds with
    consistent styling and common patterns.
    """
    
    # Standard colors
    SUCCESS_COLOR = 0x00FF00      # Green
    ERROR_COLOR = 0xFF0000        # Red  
    WARNING_COLOR = 0xFFAA00      # Orange
    INFO_COLOR = 0x0099FF         # Blue
    PENDING_COLOR = 0xFFFF00      # Yellow
    NEUTRAL_COLOR = 0x808080      # Gray
    
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None):
        """
        Initialize embed builder.
        
        Args:
            title: Embed title
            description: Embed description
        """
        self.embed = Embed()
        
        if title:
            self.embed.title = title
        if description:
            self.embed.description = description
            
        # Set default timestamp and footer
        self.embed.timestamp = datetime.utcnow()
        self.embed.set_footer(text=get_footer_text())
    
    def title(self, title: str) -> 'EmbedBuilder':
        """Set embed title."""
        self.embed.title = title
        return self
    
    def description(self, description: str) -> 'EmbedBuilder':
        """Set embed description."""
        self.embed.description = description
        return self
    
    def color(self, color: int) -> 'EmbedBuilder':
        """Set embed color."""
        self.embed.color = color
        return self
    
    def success(self) -> 'EmbedBuilder':
        """Set success color."""
        return self.color(self.SUCCESS_COLOR)
    
    def error(self) -> 'EmbedBuilder':
        """Set error color."""
        return self.color(self.ERROR_COLOR)
    
    def warning(self) -> 'EmbedBuilder':
        """Set warning color."""
        return self.color(self.WARNING_COLOR)
    
    def info(self) -> 'EmbedBuilder':
        """Set info color."""
        return self.color(self.INFO_COLOR)
    
    def pending(self) -> 'EmbedBuilder':
        """Set pending color."""
        return self.color(self.PENDING_COLOR)
    
    def field(self, name: str, value: str, inline: bool = False) -> 'EmbedBuilder':
        """Add a field to the embed."""
        self.embed.add_field(name=name, value=value, inline=inline)
        return self
    
    def thumbnail(self, url: str) -> 'EmbedBuilder':
        """Set embed thumbnail."""
        self.embed.set_thumbnail(url=url)
        return self
    
    def image(self, url: str) -> 'EmbedBuilder':
        """Set embed image."""
        self.embed.set_image(url=url)
        return self
    
    def author(self, name: str, icon_url: Optional[str] = None, url: Optional[str] = None) -> 'EmbedBuilder':
        """Set embed author."""
        self.embed.set_author(name=name, icon_url=icon_url, url=url)
        return self
    
    def footer(self, text: str, icon_url: Optional[str] = None) -> 'EmbedBuilder':
        """Set embed footer."""
        self.embed.set_footer(text=text, icon_url=icon_url)
        return self
    
    def timestamp(self, timestamp: Optional[datetime] = None) -> 'EmbedBuilder':
        """Set embed timestamp."""
        self.embed.timestamp = timestamp or datetime.utcnow()
        return self
    
    def build(self) -> Embed:
        """Build and return the embed."""
        return self.embed


class MediaEmbedBuilder:
    """
    Specialized builder for media-related embeds.
    """
    
    @staticmethod
    def request_success(title: str, year: str, media_type: str, 
                       request_id: int, status: int = 1,
                       poster_url: Optional[str] = None) -> Embed:
        """
        Create a successful request embed.
        
        Args:
            title: Media title
            year: Media year
            media_type: Type of media (movie, tv, anime)
            request_id: Request ID
            status: Request status code
            poster_url: Optional poster image URL
            
        Returns:
            Discord embed for successful request
        """
        embed = EmbedBuilder(
            title=f"{REQUEST_SUCCESS} Request Submitted",
            description=f"**{title}** ({year})"
        ).color(StatusManager.get_status_color(status))
        
        # Add media info
        media_emoji = get_media_type_emoji(media_type)
        embed.field("Media Type", f"{media_emoji} {media_type.title()}", inline=True)
        embed.field("Status", StatusManager.get_status_display(status), inline=True)
        embed.field("Request ID", f"`{request_id}`", inline=True)
        
        if poster_url:
            embed.thumbnail(poster_url)
        
        return embed.build()
    
    @staticmethod
    def request_duplicate(title: str, year: str, existing_request_id: int,
                         existing_status: int, created_at: datetime,
                         poster_url: Optional[str] = None) -> Embed:
        """
        Create a duplicate request embed.
        
        Args:
            title: Media title
            year: Media year
            existing_request_id: ID of existing request
            existing_status: Status of existing request
            created_at: When existing request was created
            poster_url: Optional poster image URL
            
        Returns:
            Discord embed for duplicate request
        """
        embed = EmbedBuilder(
            title=f"{WARNING} Duplicate Request",
            description=f"You already have a request for **{title}** ({year})"
        ).warning()
        
        embed.field("Current Status", StatusManager.get_status_display(existing_status), inline=True)
        embed.field("Request ID", f"`{existing_request_id}`", inline=True)
        embed.field("Requested", f"<t:{int(created_at.timestamp())}:R>", inline=True)
        
        if poster_url:
            embed.thumbnail(poster_url)
        
        return embed.build()
    
    @staticmethod
    def search_results(query: str, results: List[Dict[str, Any]], 
                      total_found: int) -> Embed:
        """
        Create search results embed.
        
        Args:
            query: Search query
            results: List of search results
            total_found: Total number of results found
            
        Returns:
            Discord embed for search results
        """
        embed = EmbedBuilder(
            title=f"{SEARCH} Search Results",
            description=f"Search query: **{query}**"
        ).info()
        
        embed.field("Results Found", str(total_found), inline=True)
        embed.field("Showing", f"{len(results)} results", inline=True)
        
        # Add top results
        for i, result in enumerate(results[:5], 1):
            media_emoji = get_media_type_emoji(result.get('media_type', 'unknown'))
            embed.field(
                f"{i}. {result['title']} ({result.get('year', 'Unknown')})",
                f"{media_emoji} {result.get('media_type', 'Unknown').title()}",
                inline=False
            )
        
        if len(results) > 5:
            embed.field("", f"... and {len(results) - 5} more results", inline=False)
        
        return embed.build()


class StatusEmbedBuilder:
    """
    Specialized builder for status and notification embeds.
    """
    
    @staticmethod
    def system_status(uptime: str, database_healthy: bool, services_status: Dict[str, bool],
                     request_stats: Dict[str, int], memory_usage: float,
                     disk_usage: Dict[str, Any]) -> Embed:
        """
        Create system status embed.
        
        Args:
            uptime: System uptime string
            database_healthy: Database health status
            services_status: Dictionary of service health statuses
            request_stats: Request statistics
            memory_usage: Memory usage percentage
            disk_usage: Disk usage information
            
        Returns:
            Discord embed for system status
        """
        embed = EmbedBuilder(
            title=f"{STATUS_ONLINE} SlinkBot System Status",
            description="Current system health and statistics"
        ).info()
        
        # System info
        embed.field("Uptime", uptime, inline=True)
        embed.field("Memory Usage", f"{memory_usage:.1f}%", inline=True)
        
        # Database status
        db_status = "✅ Healthy" if database_healthy else "❌ Issues"
        embed.field("Database", db_status, inline=True)
        
        # Request statistics
        embed.field(
            "Request Statistics",
            f"**Active:** {request_stats.get('active', 0)}\n"
            f"**Completed:** {request_stats.get('completed', 0)}\n"
            f"**Total:** {request_stats.get('total', 0)}",
            inline=True
        )
        
        # Disk usage
        disk_emoji = "🟢" if disk_usage.get('used_percent', 0) < 80 else "🟡" if disk_usage.get('used_percent', 0) < 95 else "🔴"
        embed.field(
            "Storage",
            f"{disk_emoji} {disk_usage.get('free_gb', 0):.1f} GB free\n"
            f"**Used:** {disk_usage.get('used_percent', 0):.1f}%",
            inline=True
        )
        
        # Services status
        healthy_services = sum(1 for status in services_status.values() if status)
        total_services = len(services_status)
        embed.field(
            "External Services",
            f"**Healthy:** {healthy_services}/{total_services}",
            inline=True
        )
        
        return embed.build()
    
    @staticmethod
    def request_notification(request_title: str, request_year: str,
                           old_status: int, new_status: int,
                           request_id: int, poster_url: Optional[str] = None) -> Embed:
        """
        Create request status change notification embed.
        
        Args:
            request_title: Title of the requested media
            request_year: Year of the requested media
            old_status: Previous status code
            new_status: New status code
            request_id: Request ID
            poster_url: Optional poster image URL
            
        Returns:
            Discord embed for status change notification
        """
        embed = EmbedBuilder(
            title=f"{STATUS_UPDATE} Request Status Update",
            description=f"**{request_title}** ({request_year})"
        ).color(StatusManager.get_status_color(new_status))
        
        # Status change
        old_display = StatusManager.get_status_display(old_status)
        new_display = StatusManager.get_status_display(new_status)
        embed.field("Status Change", f"{old_display} → {new_display}", inline=False)
        
        embed.field("Request ID", f"`{request_id}`", inline=True)
        
        if StatusManager.is_completed_status(new_status):
            embed.field("🎉 Ready to Watch!", "Your requested content is now available!", inline=False)
        
        if poster_url:
            embed.thumbnail(poster_url)
        
        return embed.build()


class ErrorEmbedBuilder:
    """
    Specialized builder for error and warning embeds.
    """
    
    @staticmethod
    def service_error(service_name: str, error_message: str, 
                     is_retryable: bool = False, retry_time: Optional[str] = None) -> Embed:
        """
        Create service error embed.
        
        Args:
            service_name: Name of the failing service
            error_message: Error description
            is_retryable: Whether the error is retryable
            retry_time: When retry will occur (if retryable)
            
        Returns:
            Discord embed for service error
        """
        embed = EmbedBuilder(
            title=f"{ERROR} Service Error",
            description=f"**{service_name}** is experiencing issues"
        ).error()
        
        embed.field("Error", error_message, inline=False)
        
        if is_retryable and retry_time:
            embed.field("Auto-Retry", f"Scheduled for {retry_time}", inline=True)
        elif is_retryable:
            embed.field("Status", "Will retry automatically", inline=True)
        else:
            embed.field("Status", "Manual intervention required", inline=True)
        
        return embed.build()
    
    @staticmethod
    def validation_error(field_name: str, error_description: str) -> Embed:
        """
        Create validation error embed.
        
        Args:
            field_name: Name of the field that failed validation
            error_description: Description of the validation error
            
        Returns:
            Discord embed for validation error
        """
        embed = EmbedBuilder(
            title=f"{WARNING} Validation Error",
            description=f"There was an issue with your input"
        ).warning()
        
        embed.field("Field", field_name, inline=True)
        embed.field("Error", error_description, inline=False)
        
        return embed.build()


class AdminEmbedBuilder:
    """
    Specialized builder for admin and maintenance embeds.
    """
    
    @staticmethod
    def maintenance_mode(enabled: bool, reason: Optional[str] = None) -> Embed:
        """
        Create maintenance mode embed.
        
        Args:
            enabled: Whether maintenance mode is enabled
            reason: Optional reason for maintenance
            
        Returns:
            Discord embed for maintenance mode
        """
        if enabled:
            embed = EmbedBuilder(
                title=f"{MAINTENANCE} Maintenance Mode Enabled",
                description="The bot is currently under maintenance"
            ).warning()
            
            if reason:
                embed.field("Reason", reason, inline=False)
                
            embed.field("Status", "Most commands are disabled", inline=True)
        else:
            embed = EmbedBuilder(
                title=f"{STATUS_ONLINE} Maintenance Mode Disabled", 
                description="The bot is back online and fully operational"
            ).success()
            
            embed.field("Status", "All commands are available", inline=True)
        
        return embed.build()


# Convenience functions for common embed types
def success_embed(title: str, description: str) -> Embed:
    """Create a simple success embed."""
    return EmbedBuilder(title, description).success().build()


def error_embed(title: str, description: str) -> Embed:
    """Create a simple error embed."""
    return EmbedBuilder(title, description).error().build()


def info_embed(title: str, description: str) -> Embed:
    """Create a simple info embed."""
    return EmbedBuilder(title, description).info().build()


def warning_embed(title: str, description: str) -> Embed:
    """Create a simple warning embed."""
    return EmbedBuilder(title, description).warning().build()
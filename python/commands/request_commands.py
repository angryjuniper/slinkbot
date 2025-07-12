"""
Request command implementations using the new service layer.
"""

import logging
from typing import List

import discord
from discord import Interaction, Embed, Color

from commands.base import BaseCommand
from services.jellyseerr import JellyseerrService
from ui.media_selection import MediaSelectionView
from models.media import MediaSearchResult

logger = logging.getLogger(__name__)


class RequestCommand(BaseCommand):
    """Base class for media request commands."""
    
    def __init__(self, allowed_channels: List[int], jellyseerr_service: JellyseerrService, request_manager=None):
        """
        Initialize the request command.
        
        Args:
            allowed_channels: List of channel IDs where this command is allowed
            jellyseerr_service: Jellyseerr service instance
            request_manager: Optional RequestManager for Phase 3 database tracking
        """
        super().__init__(allowed_channels)
        self.jellyseerr_service = jellyseerr_service
        self.request_manager = request_manager
    
    async def execute(self, interaction: Interaction, title: str, media_type: str, season: int = None):
        """
        Execute media request command.
        
        Args:
            interaction: Discord interaction object
            title: Media title to search for
            media_type: Type of media ('movie', 'tv', 'anime')
            season: Season number for TV shows (optional)
        """
        await interaction.response.defer()
        
        try:
            # Search for media
            search_results = await self.jellyseerr_service.search_media(title, media_type)
            
            if not search_results:
                embed = Embed(
                    title="No Results Found",
                    description=f"Sorry, I couldn't find any {media_type} matching '{title}'.",
                    color=Color.red()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Handle single result
            if len(search_results) == 1:
                selected_media = search_results[0]
                await self._submit_request(interaction, selected_media, media_type)
                return
            
            # Show selection UI for multiple results
            await self._show_selection_ui(interaction, search_results, title, media_type)
            
        except Exception as e:
            logger.error(f"Error in {media_type} request command: {e}")
            embed = Embed(
                title="❌ An Error Occurred",
                description="Something went wrong while processing your request.",
                color=Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    async def _show_selection_ui(self, interaction: Interaction, search_results: List[MediaSearchResult], 
                                 title: str, media_type: str):
        """
        Show interactive selection UI for multiple results.
        
        Args:
            interaction: Discord interaction object
            search_results: List of search results
            title: Original search title
            media_type: Type of media
        """
        embed = Embed(
            title=f"Multiple Results Found for '{title}'",
            description="Please choose the correct item from the dropdown below.",
            color=Color.blue()
        )
        
        view = MediaSelectionView(search_results, timeout=180.0)
        message = await interaction.followup.send(embed=embed, view=view, wait=True)
        
        try:
            await view.wait()
            
            if view.selected_index is not None:
                selected_media = search_results[view.selected_index]
                
                # Update message to show selection
                await message.edit(
                    content=f"✅ You selected: **{selected_media.title} ({selected_media.year})**",
                    embed=None,
                    view=None
                )
                
                # Submit the request
                await self._submit_request(interaction, selected_media, media_type)
            else:
                # Timeout or no selection
                await message.edit(
                    content="Timed out waiting for a selection.",
                    embed=None,
                    view=None
                )
                
        except Exception as e:
            logger.error(f"Error in selection UI: {e}")
            await message.edit(
                content="An error occurred during selection.",
                embed=None,
                view=None
            )
    
    async def _submit_request(self, interaction: Interaction, media: MediaSearchResult, media_type: str):
        """
        Submit a media request.
        
        Args:
            interaction: Discord interaction object
            media: Selected media
            media_type: Type of media
        """
        try:
            # Use RequestManager if available (Phase 3), otherwise submit directly (Phase 2)
            if self.request_manager:
                # Phase 3: Use RequestManager for database tracking
                poster_url = f"https://image.tmdb.org/t/p/w500{media.poster_path}" if media.poster_path else None
                tracked_request = await self.request_manager.submit_request(
                    media_id=media.id,
                    media_type=media_type,
                    user_id=interaction.user.id,
                    channel_id=interaction.channel_id,
                    media_title=media.title,
                    media_year=media.year,
                    poster_url=poster_url
                )
                
                if tracked_request:
                    embed = Embed(
                        title="✅ Request Submitted!",
                        description=f"Your request for **{media.title} ({media.year})** has been submitted and is now being tracked.",
                        color=Color.green()
                    )
                    embed.add_field(
                        name="Status",
                        value=tracked_request.get_status_display(),
                        inline=True
                    )
                    embed.add_field(
                        name="Request ID",
                        value=str(tracked_request.jellyseerr_request_id),
                        inline=True
                    )
                    embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                else:
                    # RequestManager failed to submit
                    embed = Embed(
                        title="❌ Request Failed",
                        description="Failed to submit your request. Please try again.",
                        color=Color.red()
                    )
            else:
                # Phase 2: Direct submission without tracking
                request = await self.jellyseerr_service.submit_request(media.id, media_type)
                
                embed = Embed(
                    title="✅ Request Submitted!",
                    description=f"Your request for **{media.title} ({media.year})** has been submitted.",
                    color=Color.green()
                )
                embed.add_field(
                    name="Status",
                    value=request.get_status_display(),
                    inline=True
                )
                embed.add_field(
                    name="Request ID",
                    value=str(request.id),
                    inline=True
                )
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to submit request: {e}")
            
            # Check if it's a duplicate request error
            error_msg = str(e).lower()
            if 'already' in error_msg or 'exist' in error_msg:
                embed = Embed(
                    title="🚫 Already Requested",
                    description=f"This {media_type} has already been requested.",
                    color=Color.orange()
                )
            else:
                embed = Embed(
                    title="❌ Request Failed",
                    description="Failed to submit your request. Please try again later.",
                    color=Color.red()
                )
            
            await interaction.followup.send(embed=embed)


class RequestMovieCommand(RequestCommand):
    """Command for requesting movies."""
    
    async def execute(self, interaction: Interaction, title: str):
        """Execute movie request."""
        await super().execute(interaction, title, 'movie', None)


class RequestTVCommand(RequestCommand):
    """Command for requesting TV shows."""
    
    async def execute(self, interaction: Interaction, title: str, season: int = None):
        """Execute TV show request with season filter."""
        await super().execute(interaction, title, 'tv', season)


class RequestAnimeCommand(RequestCommand):
    """Command for requesting anime."""
    
    async def execute(self, interaction: Interaction, title: str):
        """Execute anime request."""
        await super().execute(interaction, title, 'anime', None)
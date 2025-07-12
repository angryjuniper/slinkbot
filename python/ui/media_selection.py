"""
Interactive UI components for media selection.
"""

import logging
from typing import List, Optional

import discord
from discord import ui, Interaction, SelectOption, Embed, Color

from models.media import MediaSearchResult

logger = logging.getLogger(__name__)


class MediaSelectionView(ui.View):
    """Interactive view for selecting media from search results."""
    
    def __init__(self, search_results: List[MediaSearchResult], *, timeout: float = 180.0):
        """
        Initialize the media selection view.
        
        Args:
            search_results: List of search results to choose from
            timeout: Timeout in seconds for the view
        """
        super().__init__(timeout=timeout)
        self.search_results = search_results
        self.selected_index: Optional[int] = None
        
        # Create dropdown options (Discord limit is 25)
        options = []
        for i, result in enumerate(search_results[:25]):
            # Ensure description is safe for Discord (max 100 chars, handle empty/None)
            overview = result.overview or "No description available"
            if len(overview) > 97:  # Leave room for "..."
                description = overview[:97] + "..."
            else:
                description = overview
            
            # Ensure title is also safe (max 100 chars for label)
            title = result.title or "Unknown Title"
            label = f"{title} ({result.year})"
            if len(label) > 100:
                title_max = 100 - len(f" ({result.year})")
                label = f"{title[:title_max]}... ({result.year})"
            
            options.append(SelectOption(
                label=label,
                value=str(i),
                description=description
            ))
        
        # Create and add the select menu
        self.select_menu = ui.Select(
            placeholder="Choose a media item...",
            options=options,
            custom_id="media_selection"
        )
        self.select_menu.callback = self._select_callback
        self.add_item(self.select_menu)
    
    async def _select_callback(self, interaction: Interaction):
        """Handle media selection."""
        try:
            self.selected_index = int(self.select_menu.values[0])
            selected_media = self.search_results[self.selected_index]
            
            # Create confirmation embed
            embed = Embed(
                title="✅ Selection Confirmed",
                description=f"You selected: **{selected_media.title} ({selected_media.year})**",
                color=Color.green()
            )
            
            if selected_media.overview:
                embed.add_field(
                    name="Overview",
                    value=selected_media.overview[:500] + "..." if len(selected_media.overview) > 500 else selected_media.overview,
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            
        except Exception as e:
            logger.error(f"Error in media selection callback: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your selection.",
                ephemeral=True
            )
    
    async def on_timeout(self):
        """Handle timeout."""
        try:
            for item in self.children:
                item.disabled = True
            
            embed = Embed(
                title="⏰ Selection Timed Out",
                description="You took too long to select media. Please try again.",
                color=Color.orange()
            )
            
            # Note: We can't edit the message here since we don't have access to it
            # The calling code should handle timeout by checking if selected_index is None
            
        except Exception as e:
            logger.error(f"Error in timeout handler: {e}")
    
    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item):
        """Handle errors in the view."""
        logger.error(f"Error in MediaSelectionView: {error}")
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred while processing your selection.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


class RequestStatusView(ui.View):
    """View for displaying and managing user requests."""
    
    def __init__(self, user_requests: List, *, timeout: float = 300.0):
        """
        Initialize the request status view.
        
        Args:
            user_requests: List of user requests
            timeout: Timeout in seconds for the view
        """
        super().__init__(timeout=timeout)
        self.user_requests = user_requests
        self.current_page = 0
        self.items_per_page = 5
        
        self._update_buttons()
    
    def _update_buttons(self):
        """Update navigation buttons based on current state."""
        self.clear_items()
        
        total_pages = (len(self.user_requests) + self.items_per_page - 1) // self.items_per_page
        
        # Previous button
        if self.current_page > 0:
            prev_button = ui.Button(
                label="◀ Previous",
                style=discord.ButtonStyle.secondary,
                custom_id="prev_page"
            )
            prev_button.callback = self._previous_page
            self.add_item(prev_button)
        
        # Page indicator
        if total_pages > 1:
            page_button = ui.Button(
                label=f"Page {self.current_page + 1}/{total_pages}",
                style=discord.ButtonStyle.primary,
                disabled=True
            )
            self.add_item(page_button)
        
        # Next button
        if self.current_page < total_pages - 1:
            next_button = ui.Button(
                label="Next ▶",
                style=discord.ButtonStyle.secondary,
                custom_id="next_page"
            )
            next_button.callback = self._next_page
            self.add_item(next_button)
    
    def _get_current_page_requests(self):
        """Get requests for current page."""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.user_requests[start:end]
    
    async def _previous_page(self, interaction: Interaction):
        """Go to previous page."""
        self.current_page -= 1
        self._update_buttons()
        embed = self._create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _next_page(self, interaction: Interaction):
        """Go to next page."""
        self.current_page += 1
        self._update_buttons()
        embed = self._create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _create_embed(self) -> Embed:
        """Create embed for current page."""
        if not self.user_requests:
            return Embed(
                title="📋 Your Requests",
                description="You have no active requests.",
                color=Color.blue()
            )
        
        embed = Embed(
            title="📋 Your Active Requests",
            color=Color.blue()
        )
        
        current_requests = self._get_current_page_requests()
        
        for req in current_requests:
            try:
                # Access TrackedRequest attributes directly and handle status display locally
                status_map = {
                    1: "🟡 Pending Approval",
                    2: "👍 Approved", 
                    3: "⏳ Processing",
                    4: "🎬 Partially Available",
                    5: "✅ Available"
                }
                status_display = status_map.get(req.last_status, "❓ Unknown")
                
                embed.add_field(
                    name=f"📺 {req.media_title} ({req.media_year})",
                    value=f"**Type:** {req.media_type.title()}\n**Status:** {status_display}\n**Request ID:** {req.jellyseerr_request_id}",
                    inline=False
                )
            except Exception as e:
                logger.error(f"Error processing request object: {e}")
                logger.error(f"Request object type: {type(req)}")
                logger.error(f"Request object attributes: {dir(req)}")
                # Add a fallback field
                embed.add_field(
                    name="📺 Error Loading Request",
                    value=f"**Error:** {str(e)}",
                    inline=False
                )
        
        return embed
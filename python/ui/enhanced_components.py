# ui/enhanced_components.py
import discord
from discord import ui, ButtonStyle, SelectOption
from typing import List, Optional, Dict, Any, Callable
import asyncio
from datetime import datetime, timedelta
from utils.logging_config import get_logger
from utils.status_manager import StatusManager
from utils.emoji_constants import *

logger = get_logger(__name__)

class PaginatedRequestView(ui.View):
    """Enhanced paginated view for user requests with filtering and sorting"""
    
    def __init__(self, user_requests: List, request_manager, user_id: int, *, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.user_requests = user_requests
        self.filtered_requests = user_requests.copy()
        self.request_manager = request_manager
        self.user_id = user_id
        self.current_page = 0
        self.items_per_page = 3
        self.current_filter = "all"
        self.current_sort = "date_desc"
        self.show_past_requests = False  # Toggle between active and past requests
        self.past_requests = []  # Will store past/completed requests
        
        self.update_components()
    
    def filter_requests(self, filter_type: str):
        """Filter requests based on type or status"""
        # Get the appropriate source list based on current view
        source_requests = self.past_requests if self.show_past_requests else self.user_requests
        
        if filter_type == "all":
            self.filtered_requests = source_requests.copy()
        elif filter_type == "pending":
            if self.show_past_requests:
                # For past requests, show completed ones
                self.filtered_requests = [r for r in source_requests if r.last_status == 5]
            else:
                # For active requests, show pending ones
                self.filtered_requests = [r for r in source_requests if r.last_status in [1, 2, 3, 4]]
        elif filter_type == "completed":
            self.filtered_requests = [r for r in source_requests if r.last_status == 5]
        elif filter_type == "movies":
            self.filtered_requests = [r for r in source_requests if r.media_type == "movie"]
        elif filter_type == "tv":
            self.filtered_requests = [r for r in source_requests if r.media_type in ["tv", "anime"]]
        
        self.current_filter = filter_type
        self.current_page = 0
    
    def sort_requests(self, sort_type: str):
        """Sort requests based on criteria"""
        if sort_type == "date_desc":
            self.filtered_requests.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_type == "date_asc":
            self.filtered_requests.sort(key=lambda x: x.created_at)
        elif sort_type == "title":
            self.filtered_requests.sort(key=lambda x: x.media_title.lower())
        elif sort_type == "status":
            self.filtered_requests.sort(key=lambda x: x.last_status)
        
        self.current_sort = sort_type
        self.current_page = 0
    
    async def fetch_past_requests(self):
        """Fetch past/completed requests for this user"""
        try:
            from database.models import get_db, TrackedRequest
            with next(get_db()) as session:
                # Fetch all non-active requests (completed, cancelled, etc.)
                past_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.discord_user_id == self.user_id,
                    TrackedRequest.is_active == False
                ).all()
                
                # Also include completed active requests (status 5)
                completed_active = session.query(TrackedRequest).filter(
                    TrackedRequest.discord_user_id == self.user_id,
                    TrackedRequest.is_active == True,
                    TrackedRequest.last_status == 5
                ).all()
                
                # Combine and deduplicate
                all_past = list(past_requests) + list(completed_active)
                self.past_requests = list({req.id: req for req in all_past}.values())
                
                logger.info(f"Fetched {len(self.past_requests)} past requests for user {self.user_id}")
                
        except Exception as e:
            logger.error(f"Error fetching past requests: {e}")
            self.past_requests = []
    
    async def toggle_request_view(self, interaction: discord.Interaction):
        """Toggle between active and past requests"""
        if not self.show_past_requests:
            # Switching to past requests - fetch them first
            await self.fetch_past_requests()
            self.show_past_requests = True
        else:
            # Switching back to active requests
            self.show_past_requests = False
        
        # Reset filters and pagination
        self.current_filter = "all"
        self.current_page = 0
        self.filter_requests("all")
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def update_components(self):
        """Update all UI components based on current state"""
        self.clear_items()
        
        # Add refresh button first (appears beneath summary, above filters)
        refresh_button = ui.Button(
            label="Refresh Status",
            emoji="🔄",
            style=ButtonStyle.green,
            row=0
        )
        refresh_button.callback = self.refresh_status
        self.add_item(refresh_button)
        
        # Add toggle button for past requests
        toggle_button = ui.Button(
            label="View Past Requests" if not self.show_past_requests else "View Active Requests",
            emoji="📋" if not self.show_past_requests else "⏳",
            style=ButtonStyle.primary,
            row=0
        )
        toggle_button.callback = self.toggle_request_view
        self.add_item(toggle_button)
        
        # Add filter dropdown
        filter_options = [
            SelectOption(label="All Requests", value="all", emoji="📋", 
                        description="Show all your requests"),
            SelectOption(label="Pending", value="pending", emoji="⏳", 
                        description="Show pending requests"),
            SelectOption(label="Completed", value="completed", emoji="✅", 
                        description="Show completed requests"),
            SelectOption(label="Movies", value="movies", emoji="🎬", 
                        description="Show only movies"),
            SelectOption(label="TV Shows", value="tv", emoji="📺", 
                        description="Show TV shows and anime")
        ]
        
        filter_select = ui.Select(
            placeholder=f"Filter: {self.current_filter.title()}",
            options=filter_options,
            custom_id="filter_select",
            row=1
        )
        filter_select.callback = self.filter_callback
        self.add_item(filter_select)
        
        # Add sort dropdown
        sort_options = [
            SelectOption(label="Newest First", value="date_desc", emoji="🕒"),
            SelectOption(label="Oldest First", value="date_asc", emoji="🕐"),
            SelectOption(label="Alphabetical", value="title", emoji="🔤"),
            SelectOption(label="By Status", value="status", emoji="📊")
        ]
        
        sort_select = ui.Select(
            placeholder=f"Sort: {self.get_sort_label(self.current_sort)}",
            options=sort_options,
            custom_id="sort_select",
            row=2
        )
        sort_select.callback = self.sort_callback
        self.add_item(sort_select)
        
        # Add navigation buttons
        total_pages = (len(self.filtered_requests) + self.items_per_page - 1) // self.items_per_page
        
        if total_pages > 1:
            nav_buttons = []
            
            # Previous button
            prev_button = ui.Button(
                emoji="⬅️",
                style=ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=3
            )
            prev_button.callback = self.previous_page
            nav_buttons.append(prev_button)
            
            # Page indicator
            page_button = ui.Button(
                label=f"{self.current_page + 1}/{total_pages}",
                style=ButtonStyle.primary,
                disabled=True,
                row=3
            )
            nav_buttons.append(page_button)
            
            # Next button
            next_button = ui.Button(
                emoji="➡️",
                style=ButtonStyle.secondary,
                disabled=self.current_page >= total_pages - 1,
                row=3
            )
            next_button.callback = self.next_page
            nav_buttons.append(next_button)
            
            for button in nav_buttons:
                self.add_item(button)
        
        # Add cancel request dropdown - always show if there are active requests
        if not self.show_past_requests:  # Only show cancel option for active requests view
            all_active_requests = [r for r in self.user_requests if r.last_status in [1, 2, 3, 4]]
            if all_active_requests:
                # Get cancellable requests from current page
                current_requests = self.get_current_page_requests()
                cancellable_requests = [r for r in current_requests if r.last_status in [1, 2, 3, 4]]
                
                if cancellable_requests:
                    cancel_options = []
                    for req in cancellable_requests:
                        status_emoji = self.get_status_emoji(req.last_status)
                        cancel_options.append(SelectOption(
                            label=f"{req.media_title[:50]}",
                            value=str(req.jellyseerr_request_id),
                            description=f"{status_emoji} {req.media_type.title()} • {req.media_year}",
                            emoji="❌"
                        ))
                    
                    cancel_select = ui.Select(
                        placeholder="Select request to cancel...",
                        options=cancel_options,
                        custom_id="cancel_select",
                        row=4
                    )
                    cancel_select.callback = self.cancel_request
                    self.add_item(cancel_select)
                else:
                    # Show disabled cancel button when no cancellable requests on this page
                    cancel_button = ui.Button(
                        label="No cancellable requests on this page",
                        emoji="❌",
                        style=ButtonStyle.secondary,
                        disabled=True,
                        row=4
                    )
                    self.add_item(cancel_button)
    
    def get_current_page_requests(self):
        """Get requests for current page"""
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        return self.filtered_requests[start:end]
    
    def get_sort_label(self, sort_type: str) -> str:
        """Get display label for sort type"""
        labels = {
            "date_desc": "Newest First",
            "date_asc": "Oldest First", 
            "title": "Alphabetical",
            "status": "By Status"
        }
        return labels.get(sort_type, "Unknown")
    
    async def filter_callback(self, interaction: discord.Interaction):
        """Handle filter selection"""
        filter_value = interaction.data['values'][0]
        self.filter_requests(filter_value)
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def sort_callback(self, interaction: discord.Interaction):
        """Handle sort selection"""
        sort_value = interaction.data['values'][0]
        self.sort_requests(sort_value)
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        self.current_page -= 1
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        self.current_page += 1
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def refresh_status(self, interaction: discord.Interaction):
        """Refresh request statuses"""
        await interaction.response.defer()
        
        try:
            # Trigger manual status check for all requests
            updates = await self.request_manager.check_request_updates()
            
            # Filter updates for this user
            user_updates = [update for update in updates 
                          if update.get('tracked_request', {}).get('discord_user_id') == self.user_id]
            
            if user_updates:
                # Refresh the user_requests data
                from database.models import get_db, TrackedRequest
                with next(get_db()) as session:
                    self.user_requests = session.query(TrackedRequest).filter(
                        TrackedRequest.discord_user_id == self.user_id,
                        TrackedRequest.is_active == True
                    ).all()
                    
                # Reapply current filter and sort
                self.filter_requests(self.current_filter)
                self.sort_requests(self.current_sort)
                self.update_components()
                
                embed = self.create_embed()
                embed.add_field(
                    name="🔄 Status Updated",
                    value=f"Found {len(user_updates)} status updates for your requests!",
                    inline=False
                )
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=self
                )
            else:
                embed = self.create_embed()
                embed.add_field(
                    name="🔄 Status Check Complete",
                    value="All your requests are up to date.",
                    inline=False
                )
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=self
                )
        except Exception as e:
            logger.error(f"Error refreshing status: {e}")
            await interaction.followup.send(
                "❌ Failed to refresh request status. Please try again later.",
                ephemeral=True
            )
    
    async def cancel_request(self, interaction: discord.Interaction):
        """Handle request cancellation with confirmation"""
        request_id = int(interaction.data['values'][0])
        request_to_cancel = next(
            (r for r in self.filtered_requests if r.jellyseerr_request_id == request_id), 
            None
        )
        
        if not request_to_cancel:
            await interaction.response.send_message(
                "❌ Request not found.",
                ephemeral=True
            )
            return
        
        # Create confirmation view
        confirm_view = ConfirmationView(
            title=f"Cancel {request_to_cancel.media_title}?",
            description="This action cannot be undone.",
            confirm_callback=lambda: self._do_cancel_request(request_id, interaction)
        )
        
        embed = discord.Embed(
            title="⚠️ Confirm Cancellation",
            description=f"Are you sure you want to cancel your request for **{request_to_cancel.media_title} ({request_to_cancel.media_year})**?",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
    
    async def _do_cancel_request(self, request_id: int, original_interaction: discord.Interaction):
        """Actually cancel the request after confirmation"""
        success = await self.request_manager.cancel_request(request_id, self.user_id)
        
        if success:
            # Remove cancelled request from lists
            self.user_requests = [r for r in self.user_requests if r.jellyseerr_request_id != request_id]
            self.filter_requests(self.current_filter)
            
            # Adjust current page if necessary
            total_pages = (len(self.filtered_requests) + self.items_per_page - 1) // self.items_per_page
            if self.current_page >= total_pages and total_pages > 0:
                self.current_page = total_pages - 1
            
            self.update_components()
            embed = self.create_embed()
            embed.add_field(
                name="✅ Request Cancelled",
                value="Your request has been successfully cancelled.",
                inline=False
            )
            
            # Update the original message
            await original_interaction.edit_original_response(embed=embed, view=self)
        else:
            await original_interaction.followup.send(
                "❌ Failed to cancel request. It may have already been processed.",
                ephemeral=True
            )
    
    def create_embed(self) -> discord.Embed:
        """Create embed for current page"""
        # Determine title based on current view
        view_type = "Past Requests" if self.show_past_requests else "Active Requests"
        
        if not self.filtered_requests:
            embed = discord.Embed(
                title=f"📋 Your {view_type}",
                description="No requests found matching the current filter.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="💡 Tip",
                value="Try changing the filter or make some new requests!" if not self.show_past_requests else "Use 'View Active Requests' to see your current requests.",
                inline=False
            )
            return embed
        
        # Get appropriate request count based on view
        source_requests = self.past_requests if self.show_past_requests else self.user_requests
        total_requests = len(source_requests)
        filtered_count = len(self.filtered_requests)
        
        title = f"📋 Your {view_type} ({filtered_count}"
        if filtered_count != total_requests:
            title += f" of {total_requests}"
        title += ")"
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        current_requests = self.get_current_page_requests()
        
        for i, req in enumerate(current_requests):
            status_emoji = self.get_status_emoji(req.last_status)
            status_text = self.get_status_text(req.last_status)
            
            # Calculate time since request
            time_since = datetime.utcnow() - req.created_at
            if time_since.days > 0:
                time_str = f"{time_since.days} days ago"
            elif time_since.seconds > 3600:
                time_str = f"{time_since.seconds // 3600} hours ago"
            else:
                time_str = f"{time_since.seconds // 60} minutes ago"
            
            field_name = f"{status_emoji} {req.media_title}"
            if len(field_name) > 256:  # Discord limit
                field_name = field_name[:253] + "..."
            
            field_value = (
                f"**Type:** {req.media_type.title()} • **Year:** {req.media_year}\n"
                f"**Status:** {status_text}\n"
                f"**Requested:** {time_str}"
            )
            
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False
            )
        
        # Add filter/sort info in footer with view type
        view_indicator = "Past" if self.show_past_requests else "Active"
        footer_text = f"{view_indicator} • Filter: {self.current_filter.title()} • Sort: {self.get_sort_label(self.current_sort)}"
        embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def get_status_emoji(status: int) -> str:
        """Get emoji for request status"""
        return StatusManager.get_status_emoji(status)
    
    @staticmethod
    def get_status_text(status: int) -> str:
        """Get text description for request status"""
        return StatusManager.get_status_text(status)


class ConfirmationView(ui.View):
    """Reusable confirmation dialog"""
    
    def __init__(self, title: str, description: str, confirm_callback: Callable, *, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.title = title
        self.description = description
        self.confirm_callback = confirm_callback
        self.result = None
    
    @ui.button(label="Confirm", style=ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        """Handle confirmation"""
        self.result = True
        await self.confirm_callback()
        self.stop()
    
    @ui.button(label="Cancel", style=ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        """Handle cancellation"""
        self.result = False
        await interaction.response.edit_message(
            content="❌ Action cancelled.",
            embed=None,
            view=None
        )
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout"""
        self.result = False
        self.stop()


class AdvancedMediaSelectionView(ui.View):
    """Enhanced media selection with preview"""
    
    def __init__(self, search_results: List, request_manager, *, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.search_results = search_results
        self.request_manager = request_manager
        self.selected_index: Optional[int] = None
        self.current_preview = 0
        
        self.update_components()
    
    def update_components(self):
        """Update UI components"""
        self.clear_items()
        
        # Media selection dropdown
        options = []
        for i, result in enumerate(self.search_results[:25]):  # Discord limit
            description = result.overview[:97] + "..." if len(result.overview) > 97 else result.overview
            options.append(SelectOption(
                label=f"{result.title} ({result.year})",
                value=str(i),
                description=description,
                emoji="🎬" if result.media_type == "movie" else "📺"
            ))
        
        media_select = ui.Select(
            placeholder="Choose a media item...",
            options=options,
            custom_id="media_selection",
            row=0
        )
        media_select.callback = self.select_callback
        self.add_item(media_select)
        
        # Preview navigation if multiple results
        if len(self.search_results) > 1:
            prev_button = ui.Button(
                emoji="⬅️",
                style=ButtonStyle.secondary,
                disabled=self.current_preview == 0,
                row=1
            )
            prev_button.callback = self.previous_preview
            self.add_item(prev_button)
            
            preview_button = ui.Button(
                label=f"Preview {self.current_preview + 1}/{len(self.search_results)}",
                style=ButtonStyle.primary,
                disabled=True,
                row=1
            )
            self.add_item(preview_button)
            
            next_button = ui.Button(
                emoji="➡️", 
                style=ButtonStyle.secondary,
                disabled=self.current_preview >= len(self.search_results) - 1,
                row=1
            )
            next_button.callback = self.next_preview
            self.add_item(next_button)
        
        # Action buttons
        if self.selected_index is not None:
            confirm_button = ui.Button(
                label="Submit Request",
                style=ButtonStyle.green,
                emoji="✅",
                row=2
            )
            confirm_button.callback = self.confirm_selection
            self.add_item(confirm_button)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle media selection"""
        self.selected_index = int(interaction.data['values'][0])
        self.current_preview = self.selected_index
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def previous_preview(self, interaction: discord.Interaction):
        """Show previous media preview"""
        self.current_preview -= 1
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_preview(self, interaction: discord.Interaction):
        """Show next media preview"""
        self.current_preview += 1
        self.update_components()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def confirm_selection(self, interaction: discord.Interaction):
        """Confirm and submit the selected media request"""
        await interaction.response.defer()
        
        if self.selected_index is None:
            await interaction.followup.send(
                "❌ Please select a media item first.",
                ephemeral=True
            )
            return
        
        selected_media = self.search_results[self.selected_index]
        
        try:
            # Submit the request
            tracked_request = await self.request_manager.submit_request(
                selected_media.id,
                selected_media.media_type,
                interaction.user.id,
                interaction.channel_id,
                media_title=selected_media.title,
                media_year=selected_media.year,
                poster_url=f"https://image.tmdb.org/t/p/w500{selected_media.poster_path}" if selected_media.poster_path else None
            )
            
            if tracked_request:
                embed = discord.Embed(
                    title="✅ Request Submitted Successfully!",
                    description=f"Your request for **{selected_media.title} ({selected_media.year})** has been submitted.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Request ID",
                    value=str(tracked_request.jellyseerr_request_id),
                    inline=True
                )
                embed.add_field(
                    name="What's Next?",
                    value="You'll receive notifications as your request progresses through approval and processing.",
                    inline=False
                )
                
                # Add cancel button for the newly submitted request
                cancel_view = RequestCancelView(tracked_request.jellyseerr_request_id, self.request_manager)
                
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=cancel_view
                )
            else:
                embed = discord.Embed(
                    title="❌ Request Failed",
                    description="Failed to submit your request. This might be because:",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Possible Reasons",
                    value="• Media already exists in library\n• Similar request already pending\n• Service temporarily unavailable",
                    inline=False
                )
                
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=embed,
                    view=None
                )
                
        except Exception as e:
            logger.error(f"Error submitting request: {e}")
            embed = discord.Embed(
                title="❌ An Error Occurred",
                description="Something went wrong while processing your request.",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=None
            )
    
    def create_embed(self) -> discord.Embed:
        """Create embed showing current preview"""
        if not self.search_results:
            return discord.Embed(
                title="No Results",
                description="No media found matching your search.",
                color=discord.Color.red()
            )
        
        current_media = self.search_results[self.current_preview]
        
        embed = discord.Embed(
            title=f"🔍 {current_media.title} ({current_media.year})",
            description=current_media.overview[:2048] if current_media.overview else "No description available.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Type",
            value=current_media.media_type.title(),
            inline=True
        )
        
        embed.add_field(
            name="Year",
            value=current_media.year,
            inline=True
        )
        
        if self.selected_index is not None:
            embed.add_field(
                name="✅ Selected",
                value="Ready to submit",
                inline=True
            )
        
        if current_media.poster_path:
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{current_media.poster_path}")
        
        embed.set_footer(text=f"Showing {self.current_preview + 1} of {len(self.search_results)} results")
        
        return embed
    
    async def on_timeout(self):
        """Handle timeout"""
        embed = discord.Embed(
            title="⏰ Selection Timed Out",
            description="You took too long to select media. Please try searching again.",
            color=discord.Color.orange()
        )
        
        try:
            await self.message.edit(embed=embed, view=None)
        except:
            pass


class RequestCancelView(ui.View):
    """Simple view with cancel button for newly submitted requests"""
    
    def __init__(self, jellyseerr_request_id: int, request_manager, *, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.jellyseerr_request_id = jellyseerr_request_id
        self.request_manager = request_manager
    
    @ui.button(label="Cancel Request", emoji="❌", style=ButtonStyle.danger)
    async def cancel_request(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel the request"""
        await interaction.response.defer()
        
        try:
            # Attempt to cancel the request
            success = await self.request_manager.cancel_request(
                self.jellyseerr_request_id, 
                interaction.user.id
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Request Cancelled",
                    description="Your request has been successfully cancelled.",
                    color=discord.Color.green()
                )
                # Disable the view
                self.clear_items()
            else:
                embed = discord.Embed(
                    title="❌ Cancellation Failed",
                    description="Unable to cancel the request. It may have already been processed or approved.",
                    color=discord.Color.red()
                )
            
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self if not success else None
            )
            
        except Exception as e:
            logger.error(f"Error cancelling request: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while trying to cancel the request.",
                color=discord.Color.red()
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=self
            )
    
    async def on_timeout(self):
        """Handle timeout"""
        # Just disable the cancel button after timeout
        for item in self.children:
            item.disabled = True
        
        try:
            # Try to update the message to show disabled button
            await self.message.edit(view=self)
        except:
            pass
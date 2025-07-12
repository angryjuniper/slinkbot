# commands/advanced_commands.py
import asyncio
import re
import discord
from discord import app_commands, Interaction, Embed, Color
from discord.ext import commands
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timedelta
from utils.logging_config import get_logger
from ui.enhanced_components import PaginatedRequestView, AdvancedMediaSelectionView
from notifications.enhanced_notifier import EnhancedStatusNotifier

logger = get_logger(__name__)

class AdvancedRequestCommands(commands.Cog):
    """Advanced request management commands with enhanced features"""
    
    def __init__(self, bot, config, request_manager, jellyseerr_service, notifier):
        self.bot = bot
        self.config = config
        self.request_manager = request_manager
        self.jellyseerr_service = jellyseerr_service
        self.notifier = notifier
    
    @app_commands.command(name="search", description="Search for media without requesting")
    @app_commands.describe(
        query="Search term for movies, TV shows, or anime",
        media_type="Filter by media type",
        year="Filter by release year"
    )
    async def search_media(
        self,
        interaction: Interaction,
        query: str,
        media_type: Optional[Literal["movie", "tv", "anime"]] = None,
        year: Optional[int] = None
    ):
        """Advanced media search with filtering options"""
        if not self._check_channel_permissions(interaction, [
            self.config.channels.movie_requests,
            self.config.channels.tv_requests,
            self.config.channels.anime_requests
        ]):
            return
        
        await interaction.response.defer()
        
        try:
            # Search with filters
            search_results = await self.jellyseerr_service.search_media(query, media_type)
            
            # Apply year filter if specified
            if year:
                search_results = [r for r in search_results if r.year == str(year)]
            
            if not search_results:
                embed = Embed(
                    title="🔍 No Results Found",
                    description=f"No media found matching your search criteria.",
                    color=Color.orange()
                )
                embed.add_field(name="Search Term", value=query, inline=True)
                if media_type:
                    embed.add_field(name="Media Type", value=media_type.title(), inline=True)
                if year:
                    embed.add_field(name="Year", value=str(year), inline=True)
                
                embed.add_field(
                    name="💡 Search Tips",
                    value="• Try different keywords\n• Check spelling\n• Use broader search terms\n• Try without year filter",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Create search results embed
            embed = Embed(
                title=f"🔍 Search Results for '{query}'",
                description=f"Found {len(search_results)} result{'s' if len(search_results) != 1 else ''}",
                color=Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Show first few results in embed
            for i, result in enumerate(search_results[:5]):
                status_check = await self._check_media_availability(result.id, result.media_type)
                availability = self._format_availability_status(status_check)
                
                embed.add_field(
                    name=f"{'🎬' if result.media_type == 'movie' else '📺'} {result.title} ({result.year})",
                    value=f"**Type:** {result.media_type.title()}\n**Status:** {availability}\n**Overview:** {result.overview[:100]}{'...' if len(result.overview) > 100 else ''}",
                    inline=False
                )
            
            if len(search_results) > 5:
                embed.add_field(
                    name="📋 Additional Results",
                    value=f"... and {len(search_results) - 5} more results.\nUse the selection menu to browse all results.",
                    inline=False
                )
            
            # Add search filters to footer
            filters = []
            if media_type:
                filters.append(f"Type: {media_type.title()}")
            if year:
                filters.append(f"Year: {year}")
            
            footer_text = f"Search performed at {datetime.now().strftime('%H:%M')}"
            if filters:
                footer_text += f" • Filters: {', '.join(filters)}"
            
            embed.set_footer(text=footer_text)
            
            # Create interactive view for requesting
            view = SearchResultView(search_results, self.request_manager, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in search command: {e}")
            await interaction.followup.send(
                "❌ An error occurred while searching. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="request-media", description="Request movies, TV shows, or episodes")
    @app_commands.describe(
        title="Media title or episode (use S01E01 for specific episodes)", 
        media_type="Choose media type (auto-detect if not specified)"
    )
    async def request_media(
        self, 
        interaction: Interaction, 
        title: str,
        media_type: Optional[Literal["movie", "tv", "episode", "auto"]] = "auto"
    ):
        """Comprehensive media request command for movies, TV shows, and episodes"""
        if not self._check_channel_permissions(interaction, [
            self.config.channels.movie_requests,
            self.config.channels.tv_requests,
            self.config.channels.anime_requests
        ]):
            return
        
        await interaction.response.defer()
        
        try:
            # Determine the actual media type to search for
            episode_pattern = r'S\d{2}E\d{2}'
            has_episode_format = bool(re.search(episode_pattern, title, re.IGNORECASE))
            
            # Determine search type based on user selection and format detection
            if media_type == "auto":
                if has_episode_format:
                    search_type = 'tv'
                    request_mode = 'episode'
                else:
                    # Auto-detect: search both movies and TV shows
                    search_type = None  # Search all types
                    request_mode = 'auto'
            elif media_type == "episode":
                search_type = 'tv'
                request_mode = 'episode'
            elif media_type == "tv":
                search_type = 'tv' 
                request_mode = 'tv_show'
            else:  # movie
                search_type = 'movie'
                request_mode = 'movie'
            
            # Perform the search
            if search_type:
                search_results = await self.jellyseerr_service.search_media(title, search_type)
            else:
                # Search both movies and TV shows
                movie_results = await self.jellyseerr_service.search_media(title, 'movie')
                tv_results = await self.jellyseerr_service.search_media(title, 'tv')
                search_results = movie_results + tv_results
            
            if not search_results:
                embed = Embed(
                    title="❌ No Results Found",
                    description=f"Sorry, couldn't find any media matching '{title}'.",
                    color=Color.red()
                )
                embed.add_field(
                    name="💡 Search Tips",
                    value="• Try different keywords or spelling\n• Use S01E01 format for specific episodes\n• Try selecting a specific media type\n• Check if the content exists on TMDB",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Handle TV show season/episode selection for TV requests
            if request_mode == 'tv_show' and search_results:
                # For TV show requests, we need to ask about seasons
                view = TVShowSelectionView(search_results, self.request_manager, interaction.user.id)
                embed = Embed(
                    title=f"📺 TV Show Request for '{title}'",
                    description="Select the show and choose how you want to request it:",
                    color=Color.blue()
                )
                await interaction.followup.send(embed=embed, view=view)
                return
            
            # If exactly one result for movies/episodes, auto-request it
            if len(search_results) == 1:
                result = search_results[0]
                
                # Check availability first
                status_check = await self._check_media_availability(result.id, result.media_type)
                if status_check['available']:
                    embed = Embed(
                        title="ℹ️ Already Available",
                        description=f"**{result.title} ({result.year})** is already available in your library.",
                        color=Color.blue()
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                # Submit request automatically with poster URL
                poster_url = f"https://image.tmdb.org/t/p/w500{result.poster_path}" if result.poster_path else None
                tracked_request = await self.request_manager.submit_request(
                    result.id,
                    result.media_type,
                    interaction.user.id,
                    interaction.channel_id,
                    media_title=result.title,
                    media_year=result.year,
                    poster_url=poster_url
                )
                
                if tracked_request:
                    request_type = "Episode" if request_mode == 'episode' else result.media_type.title()
                    embed = Embed(
                        title="✅ Media Request Submitted!",
                        description=f"Your {request_type.lower()} request for **{result.title} ({result.year})** has been submitted and is now being tracked.",
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
                    await interaction.followup.send(embed=embed)
                else:
                    embed = Embed(
                        title="❌ Request Failed",
                        description="Failed to submit request. It may already exist or the service is unavailable.",
                        color=Color.red()
                    )
                    await interaction.followup.send(embed=embed)
            
            else:
                # Multiple results - show selection view
                view = AdvancedMediaSelectionView(search_results, self.request_manager)
                embed = Embed(
                    title=f"🔍 Multiple Results for '{title}'",
                    description="Please select the correct media from the options below.",
                    color=Color.blue()
                )
                await interaction.followup.send(embed=embed, view=view)
                
        except Exception as e:
            logger.error(f"Error in media request: {e}")
            await interaction.followup.send(
                "❌ An error occurred while processing your request.",
                ephemeral=True
            )
    
    @app_commands.command(name="my-requests", description="View and manage your requests")
    @app_commands.describe(
        filter_type="Filter requests by type or status",
        sort_by="Sort requests by criteria"
    )
    async def my_requests(
        self,
        interaction: Interaction,
        filter_type: Optional[Literal["all", "pending", "completed", "movies", "tv"]] = "all",
        sort_by: Optional[Literal["newest", "oldest", "title", "status"]] = "newest"
    ):
        """Enhanced request management with filtering and sorting"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get all requests and separate active from completed
            all_requests = self.request_manager.get_user_requests(interaction.user.id, include_inactive=True)
            
            # Separate requests: status 5 (Available) should be considered past/completed
            active_requests = [r for r in all_requests if r.last_status in [1, 2, 3, 4]]
            past_requests = [r for r in all_requests if r.last_status == 5 or not r.is_active]
            
            # Use active requests as the primary list, past requests as secondary
            user_requests = active_requests
            
            if not user_requests and not past_requests:
                embed = Embed(
                    title="📋 Your Requests",
                    description="You haven't made any requests yet.",
                    color=Color.blue()
                )
                embed.add_field(
                    name="💡 Getting Started",
                    value="Use **`/request-media`** to request movies, TV shows, or episodes. Use **`/search`** to browse without requesting.",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return
            elif not user_requests and past_requests:
                # Only past requests exist
                embed = Embed(
                    title="📋 Your Active Requests",
                    description="You have no active requests currently, but you have completed requests in your history.",
                    color=Color.blue()
                )
                embed.add_field(
                    name="📚 View History",
                    value=f"You have {len(past_requests)} completed request(s). Use the 'Show Past Requests' button below to view them.",
                    inline=False
                )
                embed.add_field(
                    name="💡 Make New Requests",
                    value="Use **`/request-media`** to request movies, TV shows, or episodes.",
                    inline=False
                )
                
                # Create minimal view for accessing past requests
                view = PaginatedRequestView([], self.request_manager, interaction.user.id)
                view.past_requests = past_requests
                await interaction.followup.send(embed=embed, view=view)
                return
            
            # Create enhanced paginated view
            view = PaginatedRequestView(
                user_requests,
                self.request_manager,
                interaction.user.id
            )
            # Set past requests for the view
            view.past_requests = past_requests
            
            # Apply initial filters
            if filter_type and filter_type != "all":
                view.filter_requests(str(filter_type))
            
            # Apply initial sort
            sort_map = {
                "newest": "date_desc",
                "oldest": "date_asc", 
                "title": "title",
                "status": "status"
            }
            sort_key = sort_map.get(str(sort_by), "date_desc")
            view.sort_requests(sort_key)
            
            embed = view.create_embed()
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in my-requests command: {e}")
            await interaction.followup.send(
                "❌ Failed to retrieve your requests. Please try again later.",
                ephemeral=True
            )
    
    @app_commands.command(name="request-stats", description="View detailed request statistics")
    @app_commands.describe(period="Time period for statistics")
    async def request_stats(
        self,
        interaction: Interaction,
        period: Optional[Literal["today", "week", "month", "all"]] = "week"
    ):
        """Display comprehensive request statistics"""
        if not self._check_admin_permissions(interaction):
            await interaction.response.send_message(
                "❌ This command requires administrator permissions.",
                ephemeral=True
            )
            return
        await interaction.response.defer()
        try:
            # Get statistics from request manager
            stats = self.request_manager.get_statistics(period)
            # Ensure period is always a string for .title()
            period_str = str(period) if period else "week"
            embed = Embed(
                title=f"📊 Request Statistics ({period_str.title()})",
                description="Comprehensive overview of request activity",
                color=Color.purple(),
                timestamp=datetime.utcnow()
            )
            
            # Overall metrics
            embed.add_field(
                name="📈 Total Requests",
                value=str(stats.get('total_requests', 0)),
                inline=True
            )
            embed.add_field(
                name="✅ Completed",
                value=str(stats.get('completed_requests', 0)),
                inline=True
            )
            embed.add_field(
                name="⏳ Pending",
                value=str(stats.get('pending_requests', 0)),
                inline=True
            )
            
            # Completion rate
            total = stats.get('total_requests', 0)
            completed = stats.get('completed_requests', 0)
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            embed.add_field(
                name="📊 Completion Rate",
                value=f"{completion_rate:.1f}%",
                inline=True
            )
            
            # Average processing time
            avg_time = stats.get('avg_processing_time', 0)
            if avg_time > 0:
                hours = avg_time // 3600
                minutes = (avg_time % 3600) // 60
                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                embed.add_field(
                    name="⏱️ Avg Processing Time",
                    value=time_str,
                    inline=True
                )
            
            # Active users
            embed.add_field(
                name="👥 Active Users",
                value=str(stats.get('active_users', 0)),
                inline=True
            )
            
            # Media type breakdown
            media_breakdown = stats.get('media_type_breakdown', {})
            if media_breakdown:
                breakdown_text = ""
                for media_type, count in media_breakdown.items():
                    emoji = "🎬" if media_type == "movie" else "📺"
                    breakdown_text += f"{emoji} {media_type.title()}: {count}\n"
                
                embed.add_field(
                    name="🎭 Media Types",
                    value=breakdown_text,
                    inline=False
                )
            
            # Top requesters
            top_users = stats.get('top_users', [])
            if top_users:
                users_text = ""
                for i, user_data in enumerate(top_users[:5], 1):
                    user = self.bot.get_user(user_data['user_id'])
                    username = user.display_name if user else f"User {user_data['user_id']}"
                    users_text += f"{i}. {username}: {user_data['request_count']} requests\n"
                
                embed.add_field(
                    name="🏆 Top Requesters",
                    value=users_text,
                    inline=False
                )
            
            # Most popular content
            popular_content = stats.get('popular_content', [])
            if popular_content:
                content_text = ""
                for i, item in enumerate(popular_content[:5], 1):
                    content_text += f"{i}. {item['title']} ({item['year']}): {item['count']} requests\n"
                
                embed.add_field(
                    name="🔥 Most Requested",
                    value=content_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Statistics generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            await interaction.followup.send(
                "❌ Failed to generate statistics. Please try again later."
            )
    
    def _check_channel_permissions(self, interaction: Interaction, allowed_channels: List[int]) -> bool:
        """Check if command can be used in current channel"""
        if not interaction.channel_id or interaction.channel_id not in allowed_channels:
            asyncio.create_task(interaction.response.send_message(
                "❌ This command can only be used in designated request channels.",
                ephemeral=True
            ))
            return False
        return True
    
    def _check_admin_permissions(self, interaction: Interaction) -> bool:
        member = getattr(interaction, "user", None)
        if isinstance(member, discord.Member):
            return member.guild_permissions.administrator
        return False
    
    async def _check_media_availability(self, media_id: int, media_type: str) -> Dict[str, Any]:
        """Check if media is already available in library"""
        try:
            # This would check Jellyseerr for existing requests/availability
            status = await self.jellyseerr_service.get_media_status(media_id, media_type)
            return {
                'available': status.get('available', False),
                'requested': status.get('requested', False),
                'status': status.get('status', 'unknown')
            }
        except:
            return {'available': False, 'requested': False, 'status': 'unknown'}
    
    def _format_availability_status(self, status_check: Dict[str, Any]) -> str:
        """Format availability status for display"""
        if status_check['available']:
            return "✅ Available"
        elif status_check['requested']:
            return "⏳ Requested"
        else:
            return "➕ Available to request"


class SearchResultView(discord.ui.View):
    """Interactive view for search results with request options"""
    
    def __init__(self, search_results: List, request_manager, user_id: int, *, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.search_results = search_results
        self.request_manager = request_manager
        self.user_id = user_id
        
        # Add request buttons for each result (up to 5)
        for i, result in enumerate(search_results[:5]):
            button = discord.ui.Button(
                label=f"Request: {result.title[:30]}",
                style=discord.ButtonStyle.green,
                emoji="➕",
                custom_id=f"request_{i}"
            )
            button.callback = self._create_request_callback(i)
            self.add_item(button)
    
    def _create_request_callback(self, index: int):
        """Create callback for request button"""
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    "❌ Only the original user can make requests from this search.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            result = self.search_results[index]
            
            try:
                tracked_request = await self.request_manager.submit_request(
                    result.id,
                    result.media_type,
                    interaction.user.id,
                    interaction.channel_id
                )
                
                if tracked_request:
                    embed = discord.Embed(
                        title="✅ Request Submitted!",
                        description=f"Successfully requested **{result.title} ({result.year})**",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Request ID", value=str(tracked_request.id), inline=True)
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(
                        "❌ Failed to submit request. It may already exist or the service is unavailable.",
                        ephemeral=True
                    )
                    
            except Exception as e:
                logger.error(f"Error submitting request: {e}")
                await interaction.followup.send(
                    "❌ An error occurred while submitting your request.",
                    ephemeral=True
                )
        
        return callback
    
    async def on_timeout(self):
        """Disable all buttons on timeout"""
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        # Optionally, if you want to update the message, you must store it when sending the view
        # This is skipped here for safety


class TVShowSelectionView(discord.ui.View):
    """Interactive view for TV show requests with season/episode options"""
    
    def __init__(self, search_results: List, request_manager, user_id: int, *, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.search_results = search_results
        self.request_manager = request_manager
        self.user_id = user_id
        self.selected_show = None
        
        # Add show selection dropdown
        show_options = []
        for i, result in enumerate(search_results[:25]):
            description = result.overview[:97] + "..." if len(result.overview) > 97 else result.overview
            show_options.append(discord.SelectOption(
                label=f"{result.title} ({result.year})",
                value=str(i),
                description=description,
                emoji="📺"
            ))
        
        show_select = discord.ui.Select(
            placeholder="Choose a TV show...",
            options=show_options,
            custom_id="show_selection",
            row=0
        )
        show_select.callback = self.show_selected
        self.add_item(show_select)
    
    async def show_selected(self, interaction: discord.Interaction):
        """Handle show selection and show request options"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the original user can make requests from this search.",
                ephemeral=True
            )
            return
        # Use interaction.data["values"] if available
        selected_index = None
        data = getattr(interaction, "data", None)
        if data is not None and isinstance(data, dict) and "values" in data and data["values"]:
            try:
                selected_index = int(data["values"][0])
            except Exception:
                selected_index = None
        if selected_index is None or selected_index >= len(self.search_results):
            await interaction.response.send_message(
                "❌ Invalid selection.", ephemeral=True
            )
            return
        self.selected_show = self.search_results[selected_index]
        if not self.selected_show:
            await interaction.response.send_message(
                "❌ Could not find the selected show.", ephemeral=True
            )
            return
        self.clear_items()
        
        # Add request type buttons
        whole_show_btn = discord.ui.Button(
            label="Request Entire Show",
            style=discord.ButtonStyle.green,
            emoji="📺",
            row=0
        )
        whole_show_btn.callback = self.request_whole_show
        self.add_item(whole_show_btn)
        
        specific_season_btn = discord.ui.Button(
            label="Request Specific Season",
            style=discord.ButtonStyle.primary,
            emoji="📅",
            row=0
        )
        specific_season_btn.callback = self.request_specific_season
        self.add_item(specific_season_btn)
        
        latest_season_btn = discord.ui.Button(
            label="Request Latest Season",
            style=discord.ButtonStyle.secondary,
            emoji="🆕",
            row=1
        )
        latest_season_btn.callback = self.request_latest_season
        self.add_item(latest_season_btn)
        
        # Update embed
        embed = discord.Embed(
            title=f"📺 {self.selected_show.title} ({self.selected_show.year})",
            description=f"How would you like to request this show?\n\n{self.selected_show.overview[:300]}{'...' if len(self.selected_show.overview) > 300 else ''}",
            color=discord.Color.blue()
        )
        
        if self.selected_show.poster_path:
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{self.selected_show.poster_path}")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def request_whole_show(self, interaction: discord.Interaction):
        """Request the entire TV show"""
        await self._submit_request(interaction, "entire show")
    
    async def request_latest_season(self, interaction: discord.Interaction):
        """Request the latest season"""
        await self._submit_request(interaction, "latest season")
    
    async def request_specific_season(self, interaction: discord.Interaction):
        """Request a specific season with season selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the original user can make requests from this search.",
                ephemeral=True
            )
            return
        
        if not self.selected_show:
            await interaction.response.send_message(
                "❌ No show selected.", ephemeral=True
            )
            return
        
        # Create season selection interface
        self.clear_items()
        
        # Add season input field (for now, ask for season number)
        # In a full implementation, you could fetch season data from TMDB
        season_options = []
        
        # Generate options for common seasons (1-10)
        for i in range(1, 11):
            season_options.append(discord.SelectOption(
                label=f"Season {i}",
                value=str(i),
                description=f"Request Season {i} of {getattr(self.selected_show, 'title', 'this show')}",
                emoji="📅"
            ))
        
        # Add "All Seasons" option
        season_options.insert(0, discord.SelectOption(
            label="All Seasons",
            value="all",
            description="Request all available seasons",
            emoji="📺"
        ))
        
        season_select = discord.ui.Select(
            placeholder="Choose which season(s) to request...",
            options=season_options,
            custom_id="season_selection",
            row=0
        )
        season_select.callback = self.season_selected
        self.add_item(season_select)
        
        # Add back button
        back_button = discord.ui.Button(
            label="Back to Show Options",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=1
        )
        back_button.callback = self.back_to_show_options
        self.add_item(back_button)
        
        # Update embed
        embed = discord.Embed(
            title=f"📅 Season Selection for {getattr(self.selected_show, 'title', 'Unknown')}",
            description="Choose which season(s) you want to request:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 Note",
            value="Selecting a specific season will only request that season. Choose 'All Seasons' to request the entire series.",
            inline=False
        )
        
        if getattr(self.selected_show, 'poster_path', None):
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{getattr(self.selected_show, 'poster_path', '')}")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def season_selected(self, interaction: discord.Interaction):
        """Handle season selection and submit request"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the original user can make requests from this search.",
                ephemeral=True
            )
            return
        
        selected_season = interaction.data['values'][0]
        
        if selected_season == "all":
            request_type = "all seasons"
        else:
            request_type = f"season {selected_season}"
        
        await self._submit_request(interaction, request_type)
    
    async def back_to_show_options(self, interaction: discord.Interaction):
        """Go back to the show selection options"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the original user can make requests from this search.",
                ephemeral=True
            )
            return
        
        # Rebuild the original show options interface
        self.clear_items()
        
        # Add request type buttons
        whole_show_btn = discord.ui.Button(
            label="Request Entire Show",
            style=discord.ButtonStyle.green,
            emoji="📺",
            row=0
        )
        whole_show_btn.callback = self.request_whole_show
        self.add_item(whole_show_btn)
        
        specific_season_btn = discord.ui.Button(
            label="Request Specific Season",
            style=discord.ButtonStyle.primary,
            emoji="📅",
            row=0
        )
        specific_season_btn.callback = self.request_specific_season
        self.add_item(specific_season_btn)
        
        latest_season_btn = discord.ui.Button(
            label="Request Latest Season",
            style=discord.ButtonStyle.secondary,
            emoji="🆕",
            row=1
        )
        latest_season_btn.callback = self.request_latest_season
        self.add_item(latest_season_btn)
        
        # Update embed
        embed = discord.Embed(
            title=f"📺 {getattr(self.selected_show, 'title', 'Unknown')} ({getattr(self.selected_show, 'year', 'Unknown')})",
            description=f"How would you like to request this show?\n\n{getattr(self.selected_show, 'overview', '')[:300]}{'...' if len(getattr(self.selected_show, 'overview', '')) > 300 else ''}",
            color=discord.Color.blue()
        )
        
        if getattr(self.selected_show, 'poster_path', None):
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{getattr(self.selected_show, 'poster_path', '')}")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def _submit_request(self, interaction: discord.Interaction, request_type: str):
        """Submit the TV show request"""
        await interaction.response.defer()
        try:
            if not self.selected_show:
                await interaction.followup.send(
                    "❌ No show selected.", ephemeral=True
                )
                return
            poster_url = f"https://image.tmdb.org/t/p/w500{getattr(self.selected_show, 'poster_path', '')}" if getattr(self.selected_show, 'poster_path', None) else None
            tracked_request = await self.request_manager.submit_request(
                getattr(self.selected_show, 'id', None),
                getattr(self.selected_show, 'media_type', None),
                interaction.user.id,
                interaction.channel_id,
                media_title=getattr(self.selected_show, 'title', None),
                media_year=getattr(self.selected_show, 'year', None),
                poster_url=poster_url
            )
            if tracked_request:
                embed = discord.Embed(
                    title="✅ TV Show Request Submitted!",
                    description=f"Your request for **{getattr(self.selected_show, 'title', 'Unknown')} ({getattr(self.selected_show, 'year', 'Unknown')})** ({request_type}) has been submitted.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Request ID", value=str(getattr(tracked_request, 'jellyseerr_request_id', '')), inline=True)
                embed.add_field(name="Type", value=request_type.title(), inline=True)
                if hasattr(interaction, 'message') and interaction.message is not None and hasattr(interaction.message, 'id'):
                    await interaction.followup.edit_message(
                        message_id=interaction.message.id,
                        embed=embed,
                        view=None
                    )
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Request Failed",
                    description="Failed to submit request. It may already exist or the service is unavailable.",
                    color=discord.Color.red()
                )
                if hasattr(interaction, 'message') and interaction.message is not None and hasattr(interaction.message, 'id'):
                    await interaction.followup.edit_message(
                        message_id=interaction.message.id,
                        embed=embed,
                        view=None
                    )
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error submitting TV show request: {e}")
            await interaction.followup.send(
                "❌ An error occurred while submitting your request.",
                ephemeral=True
            )


async def setup(bot):
    """Setup function for the cog"""
    # This would be called when loading the cog
    # You would pass the required dependencies here
    pass
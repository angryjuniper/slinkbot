#!/usr/bin/env python3
"""
SlinkBot - Advanced Command Management & Database Consistency
Enhanced media request system with improved command synchronization and database integrity
"""

import asyncio
import os
import shutil
import signal
import sys
import traceback
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

# Import version management and emoji constants
from utils.version import VERSION, BOT_DESCRIPTION, get_footer_text
from utils.emoji_constants import *

# Import current version components
from commands.quick_sync import QuickSyncManager, QuickSyncCog

# Import existing core components
from database.models import init_database, get_db, TrackedRequest, db_manager
from services.jellyseerr import JellyseerrService
from managers.request_manager import RequestManager
from managers.health_manager import HealthManager
from notifications.enhanced_notifier import EnhancedStatusNotifier
from tasks.scheduler import TaskScheduler
from commands.advanced_commands import AdvancedRequestCommands
# UI components imported as needed
from utils.logging_config import setup_logging, get_logger
from utils.database_session import database_session, get_stats_safely, health_check_safely
# Configuration loaded from environment

logger = get_logger(__name__)

class SlinkBot(commands.Bot):
    """SlinkBot - Advanced Command Management with Database Consistency"""
    
    def __init__(self, intents: discord.Intents):
        super().__init__(
            command_prefix='!',
            intents=intents,
            description=BOT_DESCRIPTION
        )
        
        # Core services
        self.jellyseerr_service = None
        self.request_manager = None
        self.health_manager = None
        self.enhanced_notifier = None
        self.task_scheduler = None
        
        # Current version components
        self.quick_sync_manager = None
        self.sync_command = None
        
        # Configuration
        self.guild_id = int(os.getenv('DISCORD_GUILD_ID', '1371578854665224232'))
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.close())
    
    async def setup_hook(self):
        """Initialize bot services and commands"""
        logger.info(f"Setting up SlinkBot {VERSION}...")
        
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        # Verify database health
        if not db_manager.health_check():
            logger.error("Database health check failed!")
            raise RuntimeError("Database is not accessible")
        
        # Initialize core services
        await self._initialize_services()
        
        # Initialize current version components
        await self._initialize_version_components()
        
        # Register commands
        await self._register_commands()
        
        # Setup background tasks
        await self._setup_background_tasks()
        
        logger.info(f"SlinkBot {VERSION} setup complete")
    
    async def _initialize_services(self):
        """Initialize core services"""
        # Jellyseerr service
        self.jellyseerr_service = JellyseerrService(
            base_url=os.getenv('JELLYSEERR_URL', 'http://localhost:5055'),
            api_key=os.getenv('JELLYSEERR_API_KEY', ''),
            service_name='jellyseerr'
        )
        
        # Request manager
        self.request_manager = RequestManager(self.jellyseerr_service)
        
        # Health manager
        self.health_manager = HealthManager({
            'jellyseerr': self.jellyseerr_service
        })
        
        # Enhanced notifier
        self.enhanced_notifier = EnhancedStatusNotifier(self, {
            'request_status': int(os.getenv('CHANNEL_REQUEST_STATUS', '0')),
            'media_arrivals': int(os.getenv('CHANNEL_MEDIA_ARRIVALS', '0')),
            'slinkbot_status': int(os.getenv('CHANNEL_SLINKBOT_STATUS', '0'))
        })
        
        logger.info("Core services initialized")
    
    async def _initialize_version_components(self):
        """Initialize current version specific components"""
        # Quick sync manager for immediate command updates
        self.quick_sync_manager = QuickSyncManager(self)
        
        # Current version sync command
        self.sync_command = QuickSyncCog(self)
        
        logger.info(f"{VERSION} components initialized")
    
    async def _register_commands(self):
        """Register all slash commands"""
        
        # Alpha v0.1.0 Quick Sync Command
        @self.tree.command(name="sync-commands", description="Force immediate guild command sync (Admin only)")
        @app_commands.describe(
            force="Force sync even if recently synced",
            verify="Verify commands after sync"
        )
        async def sync_commands(interaction: discord.Interaction, force: bool = False, verify: bool = True):
            """Alpha v0.1.0 immediate guild sync command"""
            
            # Check admin permissions
            if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ This command requires administrator permissions.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer(ephemeral=True)
            
            try:
                guild_id = interaction.guild_id
                
                # Perform immediate sync
                if self.quick_sync_manager is None:
                    await interaction.followup.send("❌ Quick sync manager not initialized.", ephemeral=True)
                    return
                if guild_id is None:
                    await interaction.followup.send("❌ Could not determine guild ID for sync.", ephemeral=True)
                    return
                result = await self.quick_sync_manager.immediate_guild_sync(guild_id, force)
                
                # Create response embed
                if result["status"] == "success":
                    embed = discord.Embed(
                        title=f"{ACTION_SYNC} Command Sync Complete!",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    embed.add_field(
                        name="📊 Sync Results",
                        value=f"**Commands:** {result['commands_synced']}\n**Duration:** {result['duration_seconds']:.2f}s\n**Method:** {result['method']}",
                        inline=False
                    )
                    
                    if "commands" in result and result["commands"]:
                        command_list = "\\n".join([f"• /{cmd}" for cmd in result["commands"][:10]])
                        if len(result["commands"]) > 10:
                            command_list += f"\\n• ... and {len(result['commands']) - 10} more"
                        
                        embed.add_field(
                            name="🎯 Synced Commands",
                            value=command_list,
                            inline=False
                        )
                    
                    embed.add_field(
                        name="💡 Next Steps",
                        value="Commands should appear immediately. Try refreshing Discord (Ctrl+R) if needed.",
                        inline=False
                    )
                    
                elif result["status"] == "skipped":
                    embed = discord.Embed(
                        title="⏭️ Sync Skipped",
                        description=f"Reason: {result['reason']}\\nUse `force: True` to override.",
                        color=discord.Color.orange()
                    )
                    
                else:  # failed
                    embed = discord.Embed(
                        title="❌ Sync Failed",
                        description=f"Error: {result.get('error', 'Unknown error')}",
                        color=discord.Color.red()
                    )
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                logger.error(f"{VERSION} sync command error: {e}")
                embed = discord.Embed(
                    title="❌ Command Error",
                    description=f"An error occurred: {str(e)[:200]}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
        
        # Enhanced Drive Space Command
        @self.tree.command(name="check-drive-space", description="Check remaining drive space on media server")
        async def check_drive_space(interaction: discord.Interaction):
            """Check total remaining drive space on media server with enhanced accuracy"""
            # Check if user has administrator permissions
            if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ This command requires administrator permissions.",
                    ephemeral=True
                )
                return
            
            await interaction.response.defer()
            
            try:
                # Check root filesystem space (most accurate)
                total, used, free = shutil.disk_usage("/")
                
                # Convert to GB
                free_gb = free / (1024**3)
                total_gb = total / (1024**3)
                used_gb = used / (1024**3)
                used_percent = (used / total) * 100
                
                # Determine status emoji and color based on usage
                if used_percent > 90:
                    status_emoji = "🔴"
                    status_text = "CRITICAL"
                    color = discord.Color.red()
                elif used_percent > 80:
                    status_emoji = "🟡"
                    status_text = "WARNING"
                    color = discord.Color.orange()
                else:
                    status_emoji = "🟢"
                    status_text = "NORMAL"
                    color = discord.Color.green()
                
                embed = discord.Embed(
                    title=f"{status_emoji} Drive Space Status",
                    color=color,
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="�� Available Space",
                    value=f"**{free_gb:.1f} GB** free",
                    inline=True
                )
                
                embed.add_field(
                    name="💾 Used Space",
                    value=f"**{used_gb:.1f} GB** ({used_percent:.1f}%)",
                    inline=True
                )
                
                embed.add_field(
                    name="🗄️ Total Capacity",
                    value=f"**{total_gb:.1f} GB**",
                    inline=True
                )
                
                embed.add_field(
                    name="🎯 Status",
                    value=f"**{status_text}**",
                    inline=False
                )
                
                if used_percent > 80:
                    embed.add_field(
                        name="⚠️ Storage Notice",
                        value="Consider cleaning up downloads or expanding storage capacity",
                        inline=False
                    )
                
                embed.set_footer(text=get_footer_text("Media Server Storage"))
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in check-drive-space command: {e}")
                await interaction.followup.send(
                    "❌ An error occurred while checking drive space. Please try again.",
                    ephemeral=True
                )
        
        # Note: /database-status command removed as it's redundant with /system-status
        
        # Create proper config object for commands
        class SimpleConfig:
            def __init__(self):
                # Channel configuration from environment
                class Channels:
                    def __init__(self):
                        self.movie_requests = int(os.getenv('CHANNEL_MOVIE_REQUESTS', '0'))
                        self.tv_requests = int(os.getenv('CHANNEL_TV_REQUESTS', '0'))
                        self.anime_requests = int(os.getenv('CHANNEL_ANIME_REQUESTS', '0'))
                        self.request_status = int(os.getenv('CHANNEL_REQUEST_STATUS', '0'))
                        self.media_arrivals = int(os.getenv('CHANNEL_MEDIA_ARRIVALS', '0'))
                        self.cancel_request = int(os.getenv('CHANNEL_CANCEL_REQUEST', '0'))
                
                self.channels = Channels()
        
        config = SimpleConfig()
        
        # Add advanced request commands as a cog
        await self.add_cog(AdvancedRequestCommands(
            bot=self,
            config=config,
            request_manager=self.request_manager,
            jellyseerr_service=self.jellyseerr_service,
            notifier=self.enhanced_notifier
        ))
        
        # Comprehensive System Status Command
        @self.tree.command(name="system-status", description="Check comprehensive system status including bot, database, and services")
        async def system_status(interaction: discord.Interaction):
            await self._handle_system_status(interaction)
        
        # User Help Command
        @self.tree.command(name="slinkbot-help", description="Get help with SlinkBot commands and features")
        async def slinkbot_help(interaction: discord.Interaction):
            """User-friendly help system for non-admin commands"""
            await interaction.response.defer(ephemeral=True)
            
            try:
                embed = discord.Embed(
                    title="🐈‍⬛ SlinkBot Help Guide",
                    description="SlinkBot is your advanced media request assistant. Here's what you can do:",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                # Media Request Commands
                embed.add_field(
                    name="🎬 Request Media",
                    value=(
                        "**`/search`** - Search for movies, TV shows, or anime without requesting\n"
                        "**`/request-media`** - Request movies, TV shows, or specific episodes\n"
                        "• Auto-detects episodes (e.g., 'Breaking Bad S01E01')\n"
                        "• Supports movies, TV series, and anime"
                    ),
                    inline=False
                )
                
                # Status & Tracking
                embed.add_field(
                    name="📊 Track Your Requests",
                    value=(
                        "**`/my-requests`** - View your complete request history\n"
                        "• See both active and completed requests\n"
                        "• Filter by status (pending, approved, completed)\n"
                        "• Sort by date, title, or status"
                    ),
                    inline=False
                )
                
                # System Information
                embed.add_field(
                    name="ℹ️ System Information",
                    value=(
                        "**`/bot-status`** - Check SlinkBot system status\n"
                        "**`/request-stats`** - View server-wide request statistics\n"
                        "• See total requests, completion rates, and trends"
                    ),
                    inline=False
                )
                
                # Request Status Guide
                embed.add_field(
                    name="📋 Request Status Guide",
                    value=(
                        "⏳ **Pending** - Waiting for approval\n"
                        "✅ **Approved** - Queued for download\n"
                        "🔄 **Downloading** - Currently being processed\n"
                        "🎉 **Available** - Ready to watch in your library!\n"
                        "❌ **Declined** - Request could not be fulfilled"
                    ),
                    inline=False
                )
                
                # Tips & Notes
                embed.add_field(
                    name="💡 Tips & Notes",
                    value=(
                        "• Most commands work in dedicated request channels\n"
                        "• Use **`/search`** first to verify content availability\n"
                        "• You'll receive notifications when your requests update\n"
                        "• Request history helps track your media library growth"
                    ),
                    inline=False
                )
                
                embed.set_footer(text=get_footer_text("User Help System"))
                
                await interaction.followup.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in slinkbot-help command: {e}")
                await interaction.followup.send(
                    "❌ An error occurred while loading help information.",
                    ephemeral=True
                )
        
        # Sync commands immediately for Alpha v0.1.0 deployment
        try:
            guild = discord.Object(id=self.guild_id)
            synced = await self.tree.sync(guild=guild)
            logger.info(f"Alpha v0.1.0 slash commands registered and synced for guild {self.guild_id}")
            logger.info(f"Synced {len(synced)} commands: {[cmd.name for cmd in synced]}")
            
            # Also sync globally for backup
            global_synced = await self.tree.sync()
            logger.info(f"Global slash commands synced: {len(global_synced)} commands")
            
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def _setup_background_tasks(self):
        """Setup background task scheduler"""
        self.task_scheduler = TaskScheduler()
        
        # Register enhanced tasks with better error handling
        self.task_scheduler.register_task(
            "status_updates",
            self._enhanced_status_check,
            interval_seconds=60,
            run_immediately=True
        )
        
        self.task_scheduler.register_task(
            "health_monitoring", 
            self._health_check,
            interval_seconds=300,
            run_immediately=False
        )
        
        self.task_scheduler.register_task(
            "database_consistency_check",
            self._database_consistency_check,
            interval_seconds=1800,  # 30 minutes
            run_immediately=False
        )
        
        self.task_scheduler.register_task(
            "retry_failed_requests",
            self._retry_failed_requests,
            interval_seconds=600,  # 10 minutes
            run_immediately=False
        )
        
        logger.info("Background tasks registered")
    
    async def _enhanced_status_check(self):
        """Enhanced status checking with database consistency verification"""
        try:
            if self.request_manager:
                updates = await self.request_manager.check_request_updates()
                if updates:
                    logger.info(f"Found {len(updates)} request updates")
                    if self.enhanced_notifier:
                        await self.enhanced_notifier.send_status_updates(updates)
                        
                        # Verify database consistency after updates
                        await self._verify_request_consistency()
                else:
                    logger.info("Found 0 request updates")
            else:
                logger.warning("Request manager not initialized, skipping status check.")
                
        except Exception as e:
            logger.error(f"Enhanced status check failed: {e}")
    
    async def _retry_failed_requests(self):
        """Process failed requests that are ready for retry"""
        try:
            if self.request_manager:
                retry_stats = await self.request_manager.process_failed_requests()
                
                if retry_stats['retried'] > 0 or retry_stats['failed_again'] > 0:
                    logger.info(f"Retry processing: {retry_stats['retried']} retried, "
                              f"{retry_stats['failed_again']} failed again, "
                              f"{retry_stats['max_failures_reached']} max failures reached")
            else:
                logger.warning("Request manager not initialized, skipping retry processing.")
                
        except Exception as e:
            logger.error(f"Failed request retry processing failed: {e}")
    
    async def _database_consistency_check(self):
        """Check database consistency and fix any issues"""
        try:
            with database_session() as session:
                # Check for orphaned requests
                total_requests = session.query(TrackedRequest).count()
                active_requests = session.query(TrackedRequest).filter(TrackedRequest.is_active == True).count()
                
                logger.info(f"Database consistency check: {total_requests} total, {active_requests} active requests")
                
                # Check for requests without proper IDs
                invalid_requests = session.query(TrackedRequest).filter(
                    (TrackedRequest.jellyseerr_request_id.is_(None)) |
                    (TrackedRequest.discord_user_id.is_(None)) |
                    (TrackedRequest.media_id.is_(None))
                ).count()
                
                if invalid_requests > 0:
                    logger.warning(f"Found {invalid_requests} requests with missing required fields")
                
                # Verify index integrity
                indexed_requests = session.query(TrackedRequest).filter(
                    TrackedRequest.jellyseerr_request_id.isnot(None)
                ).count()
                
                logger.info(f"Database index integrity: {indexed_requests}/{total_requests} requests properly indexed")
                
        except Exception as e:
            logger.error(f"Database consistency check failed: {e}")
    
    async def _verify_request_consistency(self):
        """Verify that all requests have proper requester and ID assignment"""
        try:
            with next(db_manager.get_session()) as session:
                # Check for requests missing critical information
                problematic_requests = session.query(TrackedRequest).filter(
                    (TrackedRequest.discord_user_id.is_(None)) |
                    (TrackedRequest.jellyseerr_request_id.is_(None))
                ).all()
                
                if problematic_requests:
                    logger.warning(f"Found {len(problematic_requests)} requests with missing user/request IDs")
                    for req in problematic_requests:
                        logger.warning(f"Request {req.id}: user_id={req.discord_user_id}, jellyseerr_id={req.jellyseerr_request_id}")
                
        except Exception as e:
            logger.error(f"Request consistency verification failed: {e}")
    
    async def _health_check(self):
        """Perform health check on all services"""
        try:
            if self.health_manager:
                health_status = await self.health_manager.check_all_services()
                healthy_count = sum(1 for status in health_status.values() if status)
                total_count = len(health_status)
                logger.info(f"Health check complete: {healthy_count}/{total_count} services healthy")
            else:
                logger.warning("Health manager not initialized, skipping health check.")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def _handle_system_status(self, interaction: discord.Interaction):
        """Handle comprehensive system status command"""
        await interaction.response.defer()
        
        try:
            # Get system status
            uptime = datetime.utcnow() - self.start_time if hasattr(self, 'start_time') else None
            guild_count = len(self.guilds)
            
            # Format uptime properly (X Days HH:MM:SS)
            uptime_str = "Unknown"
            if uptime:
                days = uptime.days
                hours, remainder = divmod(uptime.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_str = f"{days} Days {hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Get database stats
            db_stats = get_stats_safely()
            db_healthy = health_check_safely()
            
            # Get drive usage
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            used_percent = (used / total) * 100
            drive_status_emoji = get_storage_status_emoji(used_percent)
            
            # Get service health
            if self.health_manager:
                service_health = await self.health_manager.check_all_services()
                healthy_services = sum(1 for status in service_health.values() if status)
                total_services = len(service_health)
            else:
                healthy_services = 0
                total_services = 0
            
            # Add known services that we should monitor
            all_services = ['Jellyseerr', 'Radarr', 'Sonarr', 'Prowlarr', 'SABnzbd', 'Gluetun', 'SlinkBot']
            # Note: Server, NZBGeek, and Newshosting would need additional health check implementation
            
            # Get quick sync status
            if self.quick_sync_manager:
                sync_status = self.quick_sync_manager.get_sync_status()
            else:
                sync_status = {'bot_ready': False, 'last_sync_time': 'Never'}
            
            embed = discord.Embed(
                title=f"{SYSTEM_ONLINE} SlinkBot System Status",
                color=discord.Color.green() if db_healthy else discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            
            # Version and Basic Info
            embed.add_field(
                name="📋 Version & Status",
                value=f"**Version:** {VERSION}\n**Guilds:** {guild_count}\n**Uptime:** {uptime_str}",
                inline=True
            )
            
            # Request Statistics
            embed.add_field(
                name="📊 Request Statistics",
                value=f"**Active:** {db_stats.get('active_requests', 0)}\n**Completed:** {db_stats.get('completed_requests', 0)}\n**Total:** {db_stats.get('total_requests', 0)}",
                inline=True
            )
            
            # Service Monitoring
            embed.add_field(
                name="🔧 Service Monitoring",
                value=f"**Services Online:** {healthy_services}/{total_services}\n**Database:** {'✅ Healthy' if db_healthy else '❌ Issues'}\n**Bot Status:** ✅ Online",
                inline=True
            )
            
            # Drive Usage
            embed.add_field(
                name=f"{drive_status_emoji} Drive Usage",
                value=f"**Available:** {free_gb:.1f} GB\n**Usage:** {used_percent:.1f}%\n**Total:** {total_gb:.1f} GB",
                inline=True
            )
            
            # Quick Sync Info
            last_sync = sync_status.get('last_sync_time', 'Never')
            if last_sync and last_sync != 'Never':
                try:
                    sync_time = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                    last_sync = sync_time.strftime('%H:%M:%S')
                except:
                    last_sync = 'Recently'
                    
            embed.add_field(
                name="⚡ Quick Sync",
                value=f"**Status:** {'✅ Ready' if sync_status['bot_ready'] else '❌ Not Ready'}\n**Last Sync:** {last_sync}\n**Purpose:** Force immediate command updates",
                inline=True
            )
            
            # Database Details
            embed.add_field(
                name="💾 Database Health",
                value=f"**Status:** {'✅ Healthy' if db_healthy else '❌ Issues'}\n**Services Monitored:** {db_stats.get('services_monitored', 0)}\n**Healthy Services:** {db_stats.get('healthy_services', 0)}",
                inline=True
            )
            
            embed.set_footer(text=get_footer_text("Use **`/sync-commands`** to force command updates"))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in system status command: {e}")
            await interaction.followup.send("❌ Error retrieving system status")
    
    async def on_ready(self):
        """Called when bot is ready"""
        self.start_time = datetime.utcnow()
        logger.info(f"SlinkBot {VERSION} is online as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Send startup notification first
        try:
            logger.info("Sending startup notification directly...")
            await self._send_startup_notification()
            logger.info("Startup notification sent")
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
            logger.error(traceback.format_exc())
        
        # Start background task scheduler
        if self.task_scheduler:
            await self.task_scheduler.start()
            logger.info("Task scheduler started")
    
    async def _delayed_startup_notification(self):
        """Send startup notification after a delay"""
        try:
            logger.info("Delayed startup notification task starting...")
            await asyncio.sleep(1)
            logger.info("Sleep completed, calling _send_startup_notification...")
            await self._send_startup_notification()
            logger.info("Delayed startup notification task completed")
        except Exception as e:
            logger.error(f"Error in delayed startup notification: {e}")
            logger.error(traceback.format_exc())
    
    async def _send_startup_notification(self):
        """Send startup notification to status channel"""
        try:
            status_channel_id = int(os.getenv('CHANNEL_SLINKBOT_STATUS', '0'))
            logger.info(f"Attempting to send startup notification to channel ID: {status_channel_id}")
            
            if status_channel_id:
                channel = self.get_channel(status_channel_id)
                logger.info(f"Channel found: {channel is not None}")
                
                if channel and isinstance(channel, discord.TextChannel):
                    embed = discord.Embed(
                        title=f"{SYSTEM_ONLINE} SlinkBot {VERSION} Online",
                        description="SlinkBot advanced media request system is ready to receive requests. Type **`/slinkbot-help`** for more information.",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(
                        name="✨ Current Features",
                        value="• Quick command synchronization\n• Enhanced database consistency\n• Improved request tracking\n• Advanced error handling\n• Real-time status monitoring",
                        inline=False
                    )
                    embed.add_field(
                        name="📊 System Status",
                        value=f"Connected to **{len(self.guilds)}** guild(s)\nBackground tasks: **Active**\nDatabase: **Healthy**",
                        inline=True
                    )
                    embed.set_footer(text=f"SlinkBot {VERSION} - Ready to serve!")
                    
                    await channel.send(embed=embed)
                    logger.info("Startup notification sent to status channel")
                else:
                    logger.warning(f"Status channel {status_channel_id} not found or not a text channel")
            else:
                logger.warning("CHANNEL_SLINKBOT_STATUS not configured")
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
            logger.error(traceback.format_exc())
    
    async def _send_offline_notification(self):
        """Send offline notification to status channel"""
        try:
            status_channel_id = int(os.getenv('CHANNEL_SLINKBOT_STATUS', '0'))
            logger.info(f"Attempting to send offline notification to channel ID: {status_channel_id}")
            
            if status_channel_id:
                channel = self.get_channel(status_channel_id)
                logger.info(f"Channel found: {channel is not None}")
                
                if channel and isinstance(channel, discord.TextChannel):
                    embed = discord.Embed(
                        title="🐈‍⬛ SlinkBot is taking a cat nap...",
                        description="SlinkBot is going offline for maintenance or updates. Be back soon! 😴",
                        color=discord.Color.orange(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(
                        name="💤 Status",
                        value="• Bot is shutting down gracefully\n• All pending requests remain tracked\n• Service will resume automatically",
                        inline=False
                    )
                    embed.add_field(
                        name="📝 Note",
                        value="Use **`/my-requests`** when I'm back online to check your request status!",
                        inline=False
                    )
                    embed.set_footer(text=f"SlinkBot {VERSION} - See you soon!")
                    
                    await channel.send(embed=embed)
                    logger.info("Offline notification sent to status channel")
                else:
                    logger.warning(f"Status channel {status_channel_id} not found or not a text channel")
            else:
                logger.warning("CHANNEL_SLINKBOT_STATUS not configured")
        except Exception as e:
            logger.error(f"Failed to send offline notification: {e}")
            logger.error(traceback.format_exc())
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle application command errors with enhanced logging"""
        logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}")
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An error occurred while processing your command. The issue has been logged.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ An error occurred while processing your command. The issue has been logged.",
                ephemeral=True
            )
    
    async def close(self):
        """Graceful shutdown"""
        logger.info(f"SlinkBot {VERSION} shutting down...")
        
        # Send offline notification
        await self._send_offline_notification()
        
        if self.task_scheduler:
            await self.task_scheduler.stop()
            logger.info("Task scheduler stopped")
        
        await super().close()
        logger.info(f"SlinkBot {VERSION} shutdown complete")


async def main():
    """Main function to run SlinkBot"""
    # Setup logging
    setup_logging()
    
    # Display version information
    logger.info(f"Starting SlinkBot {VERSION}")
    logger.info(f"Version loaded from VERSION file: {VERSION}")
    
    # Set up Discord intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.guild_messages = True
    
    # Create and run bot
    bot = SlinkBot(intents=intents)
    
    try:
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is required")
        
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
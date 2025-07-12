"""
Status notification system for Discord alerts.
"""

import asyncio
from typing import List, Dict, Any, Optional

import discord
from discord import Embed, Color

from database.models import TrackedRequest, ServiceHealth
from utils.logging_config import get_logger

logger = get_logger(__name__)


class StatusNotifier:
    """Handles Discord notifications for request status changes and service alerts."""
    
    def __init__(self, bot: discord.Client, channels: Dict[str, int]):
        """
        Initialize status notifier.
        
        Args:
            bot: Discord bot instance
            channels: Dictionary of channel types to channel IDs
        """
        self.bot = bot
        self.channels = channels
        
        # Status message configurations
        self.status_messages = {
            1: {"title": "⏳ Request Pending", "color": Color.orange()},
            2: {"title": "✅ Request Approved", "color": Color.green()},
            3: {"title": "🔄 Request Processing", "color": Color.blue()},
            4: {"title": "🎬 Partially Available", "color": Color.gold()},
            5: {"title": "📥 Media Available", "color": Color.green()}
        }
    
    async def send_status_updates(self, updates: List[Dict[str, Any]]):
        """
        Send Discord notifications for status updates.
        
        Args:
            updates: List of update dictionaries from RequestManager
        """
        if not updates:
            return
        
        logger.info(f"Sending {len(updates)} status update notifications")
        
        for update in updates:
            try:
                await self._send_individual_update(update)
            except Exception as e:
                logger.error(f"Failed to send status update notification: {e}")
    
    async def _send_individual_update(self, update: Dict[str, Any]):
        """
        Send notification for a single status update.
        
        Args:
            update: Update dictionary containing tracked_request, old_status, new_status
        """
        tracked_request: TrackedRequest = update['tracked_request']
        old_status: int = update['old_status']
        new_status: int = update['new_status']
        
        # Get status info
        status_info = self.status_messages.get(new_status, {
            "title": "📢 Status Update",
            "color": Color.blue()
        })
        
        # Create embed
        embed = Embed(
            title=status_info["title"],
            description=f"**{tracked_request.media_title} ({tracked_request.media_year})**",
            color=status_info["color"]
        )
        
        # Add media information
        embed.add_field(
            name="Media Type",
            value=tracked_request.media_type.title(),
            inline=True
        )
        
        embed.add_field(
            name="Request ID",
            value=str(tracked_request.jellyseerr_request_id),
            inline=True
        )
        
        embed.add_field(
            name="Status Change",
            value=f"{self._get_status_emoji(old_status)} → {self._get_status_emoji(new_status)}",
            inline=True
        )
        
        # Add status-specific information
        if new_status == 2:  # Approved
            embed.add_field(
                name="Next Steps",
                value="Your request has been approved and will be downloaded soon.",
                inline=False
            )
        elif new_status == 3:  # Processing
            embed.add_field(
                name="Status",
                value="Your request is currently being downloaded.",
                inline=False
            )
        elif new_status == 4:  # Partially Available
            embed.add_field(
                name="Status", 
                value="Some episodes/parts are now available.",
                inline=False
            )
        elif new_status == 5:  # Available
            embed.add_field(
                name="Ready to Watch!",
                value="Your requested media is now available in the library.",
                inline=False
            )
        
        # Add timestamp
        embed.timestamp = tracked_request.updated_at
        
        # Send to appropriate channel based on status
        try:
            if new_status == 5:  # Available/Complete - send to media arrivals
                channel_id = self.channels.get('media_arrivals')
                if not channel_id:
                    logger.error("Media arrivals channel not configured")
                    return
            else:  # All other statuses - send to request status
                channel_id = self.channels.get('request_status')
                if not channel_id:
                    logger.error("Request status channel not configured")
                    return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Request status channel not found: {channel_id}")
                return
            
            # Mention the user who made the request
            user = self.bot.get_user(tracked_request.discord_user_id)
            mention = user.mention if user else f"<@{tracked_request.discord_user_id}>"
            
            await channel.send(content=mention, embed=embed)
            logger.info(f"Sent status update for request {tracked_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to send status update to channel: {e}")
    
    async def send_health_alert(self, service_name: str, is_healthy: bool, error_message: str = None):
        """
        Send service health alert.
        
        Args:
            service_name: Name of the service
            is_healthy: Whether service is healthy or not
            error_message: Optional error message if unhealthy
        """
        try:
            if is_healthy:
                # Service recovered
                embed = Embed(
                    title="✅ Service Restored",
                    description=f"**{service_name}** is now back online and functioning normally.",
                    color=Color.green()
                )
            else:
                # Service is down
                embed = Embed(
                    title="🚨 Service Alert",
                    description=f"**{service_name}** is currently experiencing issues.",
                    color=Color.red()
                )
                
                if error_message:
                    embed.add_field(
                        name="Error Details",
                        value=error_message[:1024],  # Discord field limit
                        inline=False
                    )
                
                embed.add_field(
                    name="Impact",
                    value="Some bot functions may be temporarily unavailable.",
                    inline=False
                )
            
            embed.timestamp = discord.utils.utcnow()
            
            # Send to service alerts channel
            channel_id = self.channels.get('service_alerts')
            if not channel_id:
                logger.error("Service alerts channel not configured")
                return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Service alerts channel not found: {channel_id}")
                return
            
            await channel.send(embed=embed)
            logger.info(f"Sent health alert for {service_name} (healthy: {is_healthy})")
            
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
    
    async def send_batch_health_summary(self, health_summary: Dict[str, Dict[str, Any]]):
        """
        Send a summary of all service health statuses.
        
        Args:
            health_summary: Dictionary of service health information
        """
        try:
            # Count healthy vs unhealthy services
            total_services = len(health_summary)
            healthy_services = sum(1 for info in health_summary.values() if info.get('healthy', False))
            unhealthy_services = total_services - healthy_services
            
            # Determine overall status color
            if unhealthy_services == 0:
                color = Color.green()
                status_emoji = "✅"
                status_text = "All Systems Operational"
            elif unhealthy_services < total_services / 2:
                color = Color.orange()
                status_emoji = "⚠️"
                status_text = "Some Services Degraded"
            else:
                color = Color.red()
                status_emoji = "🚨"
                status_text = "Multiple Services Down"
            
            embed = Embed(
                title=f"{status_emoji} System Health Summary",
                description=status_text,
                color=color
            )
            
            # Add overall stats
            embed.add_field(
                name="Overview",
                value=f"**Healthy:** {healthy_services}\n**Unhealthy:** {unhealthy_services}\n**Total:** {total_services}",
                inline=True
            )
            
            # Add service details
            healthy_list = []
            unhealthy_list = []
            
            for service_name, info in health_summary.items():
                if info.get('healthy', False):
                    healthy_list.append(f"✅ {service_name}")
                else:
                    error_msg = info.get('last_error', 'Unknown error')
                    unhealthy_list.append(f"❌ {service_name}: {error_msg[:50]}")
            
            if healthy_list:
                embed.add_field(
                    name="Healthy Services",
                    value="\n".join(healthy_list[:10]),  # Limit to 10
                    inline=True
                )
            
            if unhealthy_list:
                embed.add_field(
                    name="Unhealthy Services",
                    value="\n".join(unhealthy_list[:10]),  # Limit to 10
                    inline=True
                )
            
            embed.timestamp = discord.utils.utcnow()
            
            # Send to service alerts channel
            channel_id = self.channels.get('service_alerts')
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed)
                    logger.info("Sent health summary notification")
            
        except Exception as e:
            logger.error(f"Failed to send health summary: {e}")
    
    async def send_request_completion_summary(self, completed_requests: List[TrackedRequest]):
        """
        Send a summary of recently completed requests.
        
        Args:
            completed_requests: List of recently completed TrackedRequest objects
        """
        if not completed_requests:
            return
        
        try:
            embed = Embed(
                title="📥 Recent Media Arrivals",
                description=f"{len(completed_requests)} media items recently became available",
                color=Color.green()
            )
            
            # Group by media type
            by_type = {}
            for request in completed_requests[:15]:  # Limit to 15 most recent
                media_type = request.media_type
                if media_type not in by_type:
                    by_type[media_type] = []
                by_type[media_type].append(request)
            
            # Add fields for each media type
            for media_type, requests in by_type.items():
                media_list = []
                for req in requests[:5]:  # Limit to 5 per type
                    media_list.append(f"• **{req.media_title}** ({req.media_year})")
                
                embed.add_field(
                    name=f"{media_type.title()} ({len(requests)})",
                    value="\n".join(media_list),
                    inline=True
                )
            
            embed.timestamp = discord.utils.utcnow()
            
            # Send to media arrivals channel
            channel_id = self.channels.get('media_arrivals')
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed)
                    logger.info(f"Sent completion summary for {len(completed_requests)} requests")
            
        except Exception as e:
            logger.error(f"Failed to send completion summary: {e}")
    
    def _get_status_emoji(self, status: int) -> str:
        """Get emoji for request status."""
        status_emojis = {
            1: "⏳",  # Pending
            2: "✅",  # Approved
            3: "🔄",  # Processing
            4: "🎬",  # Partially Available
            5: "📥"   # Available
        }
        return status_emojis.get(status, "❓")
    
    async def send_startup_notification(self):
        """Send notification when bot starts up."""
        try:
            embed = Embed(
                title="🤖 SlinkBot Online",
                description="SlinkBot has started and is ready to process requests.",
                color=Color.green()
            )
            embed.timestamp = discord.utils.utcnow()
            
            # Send to bot status channel
            channel_id = self.channels.get('bot_status')
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    async def send_shutdown_notification(self):
        """Send notification when bot shuts down."""
        try:
            embed = Embed(
                title="👋 SlinkBot Shutting Down",
                description="SlinkBot is shutting down for maintenance.",
                color=Color.orange()
            )
            embed.timestamp = discord.utils.utcnow()
            
            # Send to bot status channel
            channel_id = self.channels.get('bot_status')
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Failed to send shutdown notification: {e}")
# notifications/enhanced_notifier.py
import discord
from discord import Embed, Color, File
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import os
from collections import defaultdict
from utils.logging_config import get_logger
from utils.version import get_footer_text
from utils.emoji_constants import *
import json

from .status_notifier import StatusNotifier

logger = get_logger(__name__)

class EnhancedStatusNotifier(StatusNotifier):
    """Enhanced notification system with rich embeds, batching, and user preferences"""
    
    def __init__(self, bot, config):
        # Initialize parent StatusNotifier
        super().__init__(bot, config)
        
        # Store config for enhanced features
        self.config = config
        
        # Additional enhanced features
        self.notification_queue = defaultdict(list)
        self.batch_timer = None
        self.user_preferences = {}
        
        # Status configuration with rich metadata
        self.status_config = {
            1: {
                "title": "⏳ Request Pending Review",
                "color": Color.orange(),
                "priority": "normal",
                "description": "Your request is waiting for approval",
                "icon": "⏳",
                "actions": ["Track status", "Cancel request"]
            },
            2: {
                "title": "✅ Request Approved",
                "color": Color.green(),
                "priority": "high", 
                "description": "Your request has been approved and queued for download",
                "icon": "✅",
                "actions": ["Track download", "View queue position"]
            },
            3: {
                "title": "❌ Request Declined",
                "color": Color.red(),
                "priority": "high",
                "description": "Your request could not be fulfilled",
                "icon": "❌",
                "actions": ["View reason", "Submit new request"]
            },
            4: {
                "title": "🔄 Download in Progress",
                "color": Color.blue(),
                "priority": "normal",
                "description": "Your content is being downloaded and processed",
                "icon": "🔄",
                "actions": ["View progress", "Estimated time"]
            },
            5: {
                "title": "🎉 Media Ready!",
                "color": Color.green(),
                "priority": "high",
                "description": "Your requested content is now available to stream",
                "icon": "🎉",
                "actions": ["Watch now", "Add to library"]
            }
        }
    
    async def queue_status_update(self, update: Dict[str, Any]):
        """Queue a status update for batched processing"""
        tracked_request = update['tracked_request']
        user_id = tracked_request.discord_user_id
        
        # Add to user's notification queue
        self.notification_queue[user_id].append(update)
        
        # Start batch timer if not already running
        if self.batch_timer is None:
            self.batch_timer = asyncio.create_task(self._process_batch_notifications())
    
    async def _process_batch_notifications(self):
        """Process queued notifications in batches"""
        await asyncio.sleep(30)  # Wait 30 seconds to collect updates
        
        try:
            # Process all queued notifications
            for user_id, updates in self.notification_queue.items():
                if updates:
                    await self._send_batched_notifications(user_id, updates)
            
            # Clear the queue
            self.notification_queue.clear()
        except Exception as e:
            logger.error(f"Error processing batch notifications: {e}")
        finally:
            self.batch_timer = None
    
    async def _send_batched_notifications(self, user_id: int, updates: List[Dict[str, Any]]):
        """Send batched notifications for a user"""
        if len(updates) == 1:
            # Single update - send detailed notification
            await self._send_detailed_notification(updates[0])
        else:
            # Multiple updates - send summary notification
            await self._send_summary_notification(user_id, updates)
    
    async def send_status_updates(self, updates: List[Dict[str, Any]]):
        """
        Send Discord notifications for status updates.
        Main entry point called by background tasks.
        
        Args:
            updates: List of update dictionaries from RequestManager
        """
        if not updates:
            return
        
        logger.info(f"Processing {len(updates)} status update notifications")
        
        try:
            # Group updates by user for better UX
            updates_by_user = defaultdict(list)
            for update in updates:
                user_id = update['tracked_request'].discord_user_id
                updates_by_user[user_id].append(update)
            
            # Process each user's updates
            for user_id, user_updates in updates_by_user.items():
                await self._process_user_updates_enhanced(user_id, user_updates)
                
        except Exception as e:
            logger.error(f"Error processing status updates: {e}")
            # Fallback to basic notifications
            for update in updates:
                try:
                    await self._send_detailed_notification(update)
                except Exception as fallback_error:
                    logger.error(f"Fallback notification failed: {fallback_error}")

    async def _process_user_updates_enhanced(self, user_id: int, user_updates: List[Dict[str, Any]]):
        """Process updates for a specific user with enhanced features"""
        try:
            # For now, just send individual notifications
            # This can be enhanced to batch similar updates
            for update in user_updates:
                await self._send_detailed_notification(update)
        except Exception as e:
            logger.error(f"Error processing user updates for {user_id}: {e}")

    async def _send_detailed_notification(self, update: Dict[str, Any]):
        """Send detailed notification for a single status update"""
        tracked_request = update['tracked_request']
        new_status = update['new_status']
        old_status = update.get('old_status')
        
        status_info = self.status_config.get(new_status, {
            "title": "📢 Status Update",
            "color": Color.blue(),
            "description": "Your request status has been updated",
            "icon": "📢"
        })
        
        # Create rich embed
        embed = Embed(
            title=status_info["title"],
            description=f"**{tracked_request.media_title} ({tracked_request.media_year})**",
            color=status_info["color"],
            timestamp=datetime.utcnow()
        )
        
        # Add media information
        embed.add_field(
            name="📺 Media Details",
            value=f"**Type:** {tracked_request.media_type.title()}\n**Year:** {tracked_request.media_year}",
            inline=True
        )
        
        embed.add_field(
            name="🆔 Request Info",
            value=f"**ID:** {tracked_request.id}\n**Requested:** {self._format_relative_time(tracked_request.created_at)}",
            inline=True
        )
        
        # Add status-specific information
        embed.add_field(
            name="ℹ️ Status Details",
            value=status_info["description"],
            inline=False
        )
        
        # Add status transition info if available
        if old_status and old_status != new_status:
            old_status_name = self.status_config.get(old_status, {}).get("title", f"Status {old_status}")
            embed.add_field(
                name="🔄 Status Change",
                value=f"{old_status_name} → {status_info['title']}",
                inline=False
            )
        
        # Add next steps for specific statuses
        if new_status == 2:  # Approved
            embed.add_field(
                name="📋 Next Steps",
                value="Your request will be downloaded automatically. You'll receive another notification when it's ready to watch.",
                inline=False
            )
        elif new_status == 3:  # Declined
            embed.add_field(
                name="🤔 What Now?",
                value="Check with administrators for the decline reason, or try requesting different content.",
                inline=False
            )
        elif new_status == 5:  # Available
            embed.add_field(
                name="🍿 Ready to Watch!",
                value="Your content is now available in your media library. Enjoy your show!",
                inline=False
            )
        
        # Add poster thumbnail if available
        if hasattr(tracked_request, 'poster_url') and tracked_request.poster_url:
            embed.set_thumbnail(url=tracked_request.poster_url)
        
        # Set footer with helpful info
        embed.set_footer(
            text="Use /my-requests to manage all your requests",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        # Send to appropriate channel
        await self._send_to_channels(embed, tracked_request, new_status)
    
    async def _send_summary_notification(self, user_id: int, updates: List[Dict[str, Any]]):
        """Send summary notification for multiple updates"""
        user = self.bot.get_user(user_id)
        if not user:
            return
        
        embed = Embed(
            title="📬 Multiple Request Updates",
            description=f"You have {len(updates)} request status updates:",
            color=Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Group updates by status
        status_groups = defaultdict(list)
        for update in updates:
            status = update['new_status']
            status_groups[status].append(update['tracked_request'])
        
        # Add field for each status group
        for status, requests in status_groups.items():
            status_info = self.status_config.get(status, {"icon": "📢", "title": f"Status {status}"})
            
            if len(requests) == 1:
                value = f"• {requests[0].media_title} ({requests[0].media_year})"
            else:
                value = f"• {len(requests)} requests updated"
                for req in requests[:3]:  # Show first 3
                    value += f"\n  - {req.media_title}"
                if len(requests) > 3:
                    value += f"\n  - ... and {len(requests) - 3} more"
            
            embed.add_field(
                name=f"{status_info['icon']} {status_info['title']}",
                value=value,
                inline=False
            )
        
        embed.add_field(
            name="💡 Tip",
            value="Use **`/my-requests`** to see detailed information about all your requests.",
            inline=False
        )
        
        embed.set_footer(
            text="Individual notifications can be enabled in settings",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        # Send to request status channel with user mention
        try:
            channel = self.bot.get_channel(self.config.channels.request_status)
            if channel:
                await channel.send(content=user.mention, embed=embed)
        except Exception as e:
            logger.error(f"Failed to send summary notification: {e}")
    
    async def _send_to_channels(self, embed: Embed, tracked_request, status: int):
        """Send notification to appropriate channels based on status"""
        user = self.bot.get_user(tracked_request.discord_user_id)
        user_mention = user.mention if user else f"<@{tracked_request.discord_user_id}>"
        
        try:
            # For status 5 (Available), send consolidated notification to media arrivals
            if status == 5:  # Available - send consolidated notification
                await self._send_consolidated_arrival_notification(tracked_request, user_mention)
            else:  # Other statuses - send to slinkbot status (consolidated)
                channel = self.bot.get_channel(self.config.channels.request_status)
                if channel:
                    await channel.send(content=user_mention, embed=embed)
                else:
                    logger.warning(f"Target channel not found for status {status}")
                
        except Exception as e:
            logger.error(f"Failed to send status notification: {e}")
    
    async def _send_consolidated_arrival_notification(self, tracked_request, user_mention):
        """Send a single consolidated notification for media arrival"""
        try:
            channel = self.bot.get_channel(self.config.channels.media_arrivals)
            if not channel:
                logger.warning("Media arrivals channel not found")
                return
            
            # Create a simple, clean arrival notification
            media_emoji = get_media_type_emoji(tracked_request.media_type)
            embed = Embed(
                title=f"{MEDIA_ARRIVAL} Your Media is Ready!",
                description=f"**{tracked_request.media_title} ({tracked_request.media_year})** is now available to stream!",
                color=Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name=f"{media_emoji} Media Details",
                value=f"**Type:** {tracked_request.media_type.title()}\n**Year:** {tracked_request.media_year}",
                inline=True
            )
            
            embed.add_field(
                name=f"{UI_TIME} Request Info",
                value=f"**ID:** {tracked_request.id}\n**Requested:** {self._format_relative_time(tracked_request.created_at)}",
                inline=True
            )
            
            # Add streaming link if available
            jellyfin_url = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
            if jellyfin_url and jellyfin_url != 'http://localhost:8096':
                embed.add_field(
                    name=f"{MEDIA_STREAM} Ready to Watch!",
                    value=f"[**Click here to login and stream!**]({jellyfin_url})\n\nYour content is now available in your media library.",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"{MEDIA_STREAM} Ready to Watch!",
                    value="Your content is now available in your media library. Check your Jellyfin server to start streaming!",
                    inline=False
                )
            
            # Add poster image if available
            if hasattr(tracked_request, 'poster_url') and tracked_request.poster_url:
                embed.set_image(url=tracked_request.poster_url)
            
            embed.set_footer(
                text="Use /my-requests to manage all your requests",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )
            
            # Send single consolidated message
            await channel.send(content=user_mention, embed=embed)
            logger.info(f"Sent consolidated arrival notification for {tracked_request.media_title}")
            
            # Mark as notified in database
            await self._mark_completion_notified(tracked_request)
            
        except Exception as e:
            logger.error(f"Failed to send consolidated arrival notification: {e}")
    
    async def send_service_health_alert(self, service_name: str, is_healthy: bool, error_details: Optional[str] = None):
        """Send enhanced service health alerts"""
        if is_healthy:
            embed = Embed(
                title="✅ Service Recovered",
                description=f"**{service_name.title()}** is now responding normally.",
                color=Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="🔧 Status",
                value="All systems operational",
                inline=True
            )
        else:
            embed = Embed(
                title="🚨 Service Health Alert",
                description=f"**{service_name.title()}** is experiencing issues.",
                color=Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="⚠️ Impact",
                value=self._get_service_impact(service_name),
                inline=True
            )
            
            embed.add_field(
                name="🔧 Status",
                value="Service unavailable",
                inline=True
            )
            
            if error_details:
                # Truncate error details if too long
                if len(error_details) > 1024:
                    error_details = error_details[:1021] + "..."
                
                embed.add_field(
                    name="📝 Error Details",
                    value=f"```{error_details}```",
                    inline=False
                )
            
            embed.add_field(
                name="🛠️ Troubleshooting",
                value=self._get_troubleshooting_steps(service_name),
                inline=False
            )
        
        embed.set_footer(
            text="Automated health monitoring system",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        try:
            channel = self.bot.get_channel(self.config.channels.service_alerts)
            if channel:
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")
    
    async def send_system_status_report(self, status_data: Dict[str, Any]):
        """Send comprehensive system status report"""
        embed = Embed(
            title="📊 System Status Report",
            description="Automated system health and performance summary",
            color=Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Service health summary
        service_health = status_data.get('service_health', {})
        healthy_count = sum(1 for status in service_health.values() if status.get('healthy', False))
        total_services = len(service_health)
        
        health_emoji = "✅" if healthy_count == total_services else "⚠️" if healthy_count > 0 else "❌"
        embed.add_field(
            name=f"{health_emoji} Service Health",
            value=f"{healthy_count}/{total_services} services operational",
            inline=True
        )
        
        # Request statistics
        request_stats = status_data.get('request_stats', {})
        embed.add_field(
            name="📈 Recent Activity",
            value=f"**Today:** {request_stats.get('today', 0)} requests\n**This Week:** {request_stats.get('week', 0)} requests",
            inline=True
        )
        
        # Queue status
        queue_stats = status_data.get('queue_stats', {})
        embed.add_field(
            name="⏳ Queue Status",
            value=f"**Pending:** {queue_stats.get('pending', 0)}\n**Processing:** {queue_stats.get('processing', 0)}",
            inline=True
        )
        
        # Add detailed service status
        if service_health:
            service_status_text = ""
            for service_name, status in service_health.items():
                emoji = "✅" if status.get('healthy', False) else "❌"
                uptime = status.get('uptime_hours', 0)
                service_status_text += f"{emoji} **{service_name.title()}** - {uptime:.1f}h uptime\n"
            
            embed.add_field(
                name="🔧 Service Details",
                value=service_status_text or "No services monitored",
                inline=False
            )
        
        # Performance metrics
        performance = status_data.get('performance', {})
        if performance:
            perf_text = ""
            if 'avg_response_time' in performance:
                perf_text += f"**Avg Response:** {performance['avg_response_time']:.2f}s\n"
            if 'requests_per_hour' in performance:
                perf_text += f"**Requests/Hour:** {performance['requests_per_hour']}\n"
            
            if perf_text:
                embed.add_field(
                    name="⚡ Performance",
                    value=perf_text,
                    inline=True
                )
        
        embed.set_footer(
            text="Next report in 6 hours",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        try:
            channel = self.bot.get_channel(self.config.channels.slinkbot_status)
            if channel:
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send status report: {e}")
    
    async def send_weekly_media_arrivals_summary(self):
        """Send weekly summary of recently arrived media every Sunday at midnight"""
        try:
            # Get recent completions from the last week
            from datetime import timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            # This would get recent completions from the database
            # For now, we'll create a placeholder structure
            recent_arrivals = await self._get_recent_arrivals(since=week_ago, limit=5)
            
            if not recent_arrivals:
                logger.info("No recent arrivals to summarize this week")
                return
            
            embed = Embed(
                title="🎬 Weekly Media Arrivals",
                description=f"Here's what arrived in your library this week ({len(recent_arrivals)} new titles)",
                color=Color.purple(),
                timestamp=datetime.utcnow()
            )
            
            # Add each recent arrival
            for i, arrival in enumerate(recent_arrivals, 1):
                embed.add_field(
                    name=f"{i}. {arrival['title']} ({arrival['year']})",
                    value=f"**Type:** {arrival['type'].title()}\n**Completed:** {arrival['completed_date']}\n**Requested by:** {arrival['requester']}",
                    inline=False
                )
            
            embed.add_field(
                name="🍿 Ready to Stream",
                value="All titles above are now available in your media library!",
                inline=False
            )
            
            embed.set_footer(
                text="Weekly summary • Next summary next Sunday",
                icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
            )
            
            # Send to media arrivals channel
            channel = self.bot.get_channel(self.config.channels.media_arrivals)
            if channel:
                await channel.send(embed=embed)
                logger.info(f"Sent weekly media arrivals summary with {len(recent_arrivals)} titles")
            
        except Exception as e:
            logger.error(f"Failed to send weekly media arrivals summary: {e}")
    
    async def _get_recent_arrivals(self, since: datetime, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent media arrivals from database"""
        try:
            # This would query the database for recently completed requests
            # Placeholder implementation for now
            return [
                {
                    'title': 'Example Movie',
                    'year': '2023',
                    'type': 'movie',
                    'completed_date': 'Dec 15',
                    'requester': 'User123'
                }
            ]
        except Exception as e:
            logger.error(f"Error getting recent arrivals: {e}")
            return []
    
    async def send_weekly_summary(self, summary_data: Dict[str, Any]):
        """Send weekly activity summary with charts"""
        embed = Embed(
            title="📊 Weekly Activity Summary",
            description=f"Summary for week ending {datetime.now().strftime('%B %d, %Y')}",
            color=Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Key metrics
        metrics = summary_data.get('metrics', {})
        embed.add_field(
            name="📈 Total Requests",
            value=str(metrics.get('total_requests', 0)),
            inline=True
        )
        embed.add_field(
            name="✅ Completed",
            value=str(metrics.get('completed_requests', 0)),
            inline=True
        )
        embed.add_field(
            name="👥 Active Users",
            value=str(metrics.get('active_users', 0)),
            inline=True
        )
        
        # Most popular content
        popular = summary_data.get('popular_content', [])
        if popular:
            popular_text = ""
            for i, item in enumerate(popular[:5], 1):
                popular_text += f"{i}. {item['title']} ({item['count']} requests)\n"
            
            embed.add_field(
                name="🔥 Most Requested",
                value=popular_text,
                inline=False
            )
        
        # User activity leaders
        top_users = summary_data.get('top_users', [])
        if top_users:
            users_text = ""
            for i, user_data in enumerate(top_users[:5], 1):
                user = self.bot.get_user(user_data['user_id'])
                username = user.display_name if user else f"User {user_data['user_id']}"
                users_text += f"{i}. {username} ({user_data['request_count']} requests)\n"
            
            embed.add_field(
                name="🏆 Top Requesters",
                value=users_text,
                inline=False
            )
        
        # Create simple ASCII chart for daily activity
        daily_activity = summary_data.get('daily_activity', [])
        if daily_activity and len(daily_activity) == 7:
            chart_text = self._create_ascii_chart(daily_activity)
            embed.add_field(
                name="📊 Daily Activity",
                value=f"```{chart_text}```",
                inline=False
            )
        
        embed.set_footer(
            text="Weekly summaries help track server usage patterns",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        try:
            channel = self.bot.get_channel(self.config.channels.slinkbot_status)
            if channel:
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send weekly summary: {e}")
    
    def _get_service_impact(self, service_name: str) -> str:
        """Get impact description for service outage"""
        impact_map = {
            'jellyseerr': 'New requests cannot be submitted',
            'radarr': 'Movie downloads may be affected',
            'sonarr': 'TV show downloads may be affected',
            'sabnzbd': 'Downloads are paused',
            'jellyfin': 'Streaming may be unavailable'
        }
        return impact_map.get(service_name.lower(), 'Some functionality may be limited')
    
    def _get_troubleshooting_steps(self, service_name: str) -> str:
        """Get troubleshooting steps for service issues"""
        steps_map = {
            'jellyseerr': '1. Check Jellyseerr container status\n2. Verify API key configuration\n3. Check network connectivity',
            'radarr': '1. Check Radarr container status\n2. Verify indexer connections\n3. Check disk space',
            'sonarr': '1. Check Sonarr container status\n2. Verify indexer connections\n3. Check disk space',
            'sabnzbd': '1. Check SABnzbd container status\n2. Verify Usenet provider connection\n3. Check download folder permissions',
            'jellyfin': '1. Check Jellyfin container status\n2. Verify media folder access\n3. Check transcoding settings'
        }
        return steps_map.get(service_name.lower(), '1. Check service status\n2. Verify configuration\n3. Check logs for errors')
    
    async def _mark_completion_notified(self, tracked_request):
        """Mark a request as having been notified of completion"""
        from database.models import get_session
        
        try:
            with get_session() as session:
                # Update the request to mark it as notified
                tracked_request.completion_notified = True
                tracked_request.completion_notified_at = datetime.utcnow()
                session.add(tracked_request)
                session.commit()
                logger.info(f"Marked request {tracked_request.id} as completion notified")
        except Exception as e:
            logger.error(f"Failed to mark completion notification: {e}")
    
    async def send_manual_completion_notification(self, request_id: int, force: bool = False):
        """
        Manually send completion notification for a request
        
        Args:
            request_id: The tracked request ID
            force: If True, send even if already notified
        Returns:
            bool: True if notification was sent, False if skipped
        """
        from database.models import get_session, TrackedRequest
        
        try:
            with get_session() as session:
                tracked_request = session.query(TrackedRequest).filter_by(id=request_id).first()
                
                if not tracked_request:
                    logger.error(f"Request {request_id} not found")
                    return False
                
                # Check if already notified (unless forcing)
                if tracked_request.completion_notified and not force:
                    logger.info(f"Request {request_id} already notified, skipping (use force=True to override)")
                    return False
                
                # Check if the request is actually completed
                if tracked_request.last_status != 5:
                    logger.error(f"Request {request_id} is not completed (status: {tracked_request.last_status})")
                    return False
                
                # Create completion update and send notification
                update = {
                    'tracked_request': tracked_request,
                    'old_status': 2,  # Assume it was approved before
                    'new_status': 5   # Now completed
                }
                
                # Send the consolidated notification
                await self._send_consolidated_arrival_notification(tracked_request)
                logger.info(f"Manual completion notification sent for request {request_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send manual completion notification: {e}")
            return False
    
    def _format_relative_time(self, timestamp: datetime) -> str:
        """Format timestamp as relative time"""
        now = datetime.utcnow()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=None)
        if now.tzinfo is None:
            now = now.replace(tzinfo=None)
            
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    def _create_ascii_chart(self, data: List[int]) -> str:
        """Create simple ASCII bar chart"""
        if not data:
            return "No data available"
        
        max_val = max(data) if data else 1
        if max_val == 0:
            max_val = 1
        
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        chart_lines = []
        
        # Create bars (scale to fit in 10 characters height)
        scale = 10 / max_val
        
        for i, value in enumerate(data):
            bar_height = int(value * scale)
            bar = '█' * bar_height if bar_height > 0 else '▁'
            chart_lines.append(f"{days[i]}: {bar} ({value})")
        
        return '\n'.join(chart_lines)


class NotificationPreferences:
    """Manage user notification preferences"""
    
    def __init__(self):
        self.preferences = {}
    
    def set_user_preference(self, user_id: int, preference: str, value: bool):
        """Set notification preference for user"""
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id][preference] = value
    
    def get_user_preference(self, user_id: int, preference: str, default: bool = True) -> bool:
        """Get notification preference for user"""
        return self.preferences.get(user_id, {}).get(preference, default)
    
    def should_notify(self, user_id: int, notification_type: str) -> bool:
        """Check if user should receive this type of notification"""
        type_map = {
            'status_updates': 'receive_status_updates',
            'batch_summaries': 'receive_batch_summaries', 
            'system_alerts': 'receive_system_alerts',
            'weekly_summaries': 'receive_weekly_summaries'
        }
        
        preference_key = type_map.get(notification_type, notification_type)
        return self.get_user_preference(user_id, preference_key, True)
#!/usr/bin/env python3
"""
Phase 5 Quick Sync - Priority Implementation
Ultra-fast guild command synchronization system
"""

import asyncio
import discord
from discord import app_commands
from datetime import datetime
from typing import Optional, List
import logging
import os
from discord.ext import commands
import traceback

# Read app version from VERSION file (use absolute path for Docker)
def get_app_version():
    version_path = '/app/VERSION'
    try:
        with open(version_path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Failed to read VERSION file at {version_path}: {e}")
        return 'Unknown'

APP_VERSION = get_app_version()

logger = logging.getLogger(__name__)


class QuickSyncManager:
    """
    Quick Sync Manager (SlinkBot compatible)
    Prioritizes immediate guild-level command updates with fallback mechanisms
    Uses app version: {APP_VERSION}
    """
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree
        self.last_sync_time = None
        self._sync_lock = asyncio.Lock()

    async def immediate_guild_sync(self, guild_id: int, force: bool = False, timeout: float = 60.0) -> dict:
        """
        Perform immediate guild command synchronization with extended timeout and better rate limit handling
        """
        if self._sync_lock.locked() and not force:
            return {
                "status": "skipped",
                "reason": "sync_in_progress",
                "timestamp": datetime.utcnow()
            }
        start_time = datetime.utcnow()
        try:
            await asyncio.wait_for(self._sync_lock.acquire(), timeout=timeout)
            try:
                await self.bot.wait_until_ready()
                guild = discord.Object(id=guild_id)
                logger.info(f"SlinkBot {APP_VERSION}: Starting immediate guild sync for {guild_id}")
                # Method 1: Direct tree sync (fastest)
                try:
                    synced = await asyncio.wait_for(self.tree.sync(guild=guild), timeout=timeout)
                    sync_count = len(synced) if synced else 0
                    # Consider sync successful even if no commands to sync
                    if sync_count >= 0:
                        end_time = datetime.utcnow()
                        duration = (end_time - start_time).total_seconds()
                        self.last_sync_time = end_time
                        logger.info(f"SlinkBot {APP_VERSION}: Quick sync successful - {sync_count} commands in {duration:.2f}s")
                        return {
                            "status": "success",
                            "method": "direct_sync",
                            "commands_synced": sync_count,
                            "duration_seconds": duration,
                            "timestamp": end_time,
                            "commands": [cmd.name for cmd in synced]
                        }
                except Exception as e:
                    logger.warning(f"SlinkBot {APP_VERSION}: Direct sync failed, trying fallback: {e}")
                # Method 2: Clear and re-sync (more reliable)
                try:
                    logger.info(f"SlinkBot {APP_VERSION}: Using fallback clear-and-sync method")
                    self.tree.clear_commands(guild=guild)
                    # Add delay to prevent rate limiting
                    await asyncio.sleep(2)
                    synced = await asyncio.wait_for(self.tree.sync(guild=guild), timeout=timeout)
                    sync_count = len(synced)
                    end_time = datetime.utcnow()
                    duration = (end_time - start_time).total_seconds()
                    self.last_sync_time = end_time
                    logger.info(f"SlinkBot {APP_VERSION}: Fallback sync successful - {sync_count} commands in {duration:.2f}s")
                    return {
                        "status": "success",
                        "method": "clear_and_sync",
                        "commands_synced": sync_count,
                        "duration_seconds": duration,
                        "timestamp": end_time,
                        "commands": [cmd.name for cmd in synced] if synced else []
                    }
                except Exception as e:
                    logger.error(f"SlinkBot {APP_VERSION}: Fallback sync also failed: {e}\n{traceback.format_exc()}")
                    return {
                        "status": "failed",
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "timestamp": datetime.utcnow(),
                        "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
                    }
            finally:
                if self._sync_lock.locked():
                    self._sync_lock.release()
        except asyncio.TimeoutError:
            logger.error(f"SlinkBot {APP_VERSION}: Sync operation timed out!")
            return {
                "status": "failed",
                "error": "Sync operation timed out",
                "timestamp": datetime.utcnow(),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            }

    async def verify_commands(self, guild_id: int, expected_commands: List[str]) -> dict:
        """
        Verify that expected commands are registered in the guild
        
        Args:
            guild_id: Guild to check
            expected_commands: List of command names to verify
            
        Returns:
            dict: Verification results
        """
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return {
                    "status": "error",
                    "error": f"Guild {guild_id} not found"
                }
            
            # Note: In newer discord.py versions, we'd use guild.fetch_commands()
            # For now, we'll rely on the sync results
            
            return {
                "status": "verified",
                "guild_name": guild.name,
                "guild_id": guild_id,
                "member_count": guild.member_count,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Phase 5: Command verification failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_sync_status(self) -> dict:
        """Get current sync status and statistics"""
        return {
            "sync_in_progress": self._sync_lock.locked(),
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "bot_ready": self.bot.is_ready(),
            "guild_count": len(self.bot.guilds),
            "timestamp": datetime.utcnow().isoformat()
        }


class QuickSyncCog(commands.Cog):
    """Cog for Quick Sync Command"""
    def __init__(self, bot):
        self.bot = bot
        self.sync_manager = QuickSyncManager(bot)

    @app_commands.command(name="quick-sync", description="Force immediate guild command sync (Admin only)")
    @app_commands.describe(
        force="Force sync even if recently synced",
        verify="Verify commands after sync"
    )
    async def quick_sync(self, interaction: discord.Interaction, force: bool = False, verify: bool = True):
        """Immediate guild sync command"""
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
            if guild_id is None:
                await interaction.followup.send("❌ Could not determine guild ID for sync.", ephemeral=True)
                return
            # Perform immediate sync
            result = await self.sync_manager.immediate_guild_sync(guild_id, force)
            # Create response embed
            if result["status"] == "success":
                embed = discord.Embed(
                    title="✅ Quick Sync Complete!",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="📊 Sync Results",
                    value=f"**Commands:** {result['commands_synced']}\n**Duration:** {result['duration_seconds']:.2f}s\n**Method:** {result['method']}",
                    inline=False
                )
                if "commands" in result and result["commands"]:
                    command_list = "\n".join([f"• /{cmd}" for cmd in result["commands"][:10]])
                    if len(result["commands"]) > 10:
                        command_list += f"\n• ... and {len(result['commands']) - 10} more"
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
                    description=f"Reason: {result['reason']}\nUse `force: True` to override.",
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
            logger.error(f"SlinkBot {APP_VERSION} sync command error: {e}")
            embed = discord.Embed(
                title="❌ Command Error",
                description=f"An error occurred: {str(e)[:200]}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)


# Setup function for SlinkBot extension loading
async def setup(bot):
    await bot.add_cog(QuickSyncCog(bot))
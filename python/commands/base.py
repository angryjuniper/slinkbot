"""
Base command class for Discord slash commands.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

import discord
from discord import Interaction

from utils.error_handling import error_handler

logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    """Base class for all Discord commands."""
    
    def __init__(self, allowed_channels: List[int]):
        """
        Initialize the command.
        
        Args:
            allowed_channels: List of channel IDs where this command is allowed
        """
        self.allowed_channels = allowed_channels
    
    def is_allowed_channel(self, channel_id: int) -> bool:
        """
        Check if command can be used in the given channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if command is allowed in the channel
        """
        return channel_id in self.allowed_channels
    
    async def validate_interaction(self, interaction: Interaction) -> bool:
        """
        Validate that interaction can proceed.
        
        Args:
            interaction: Discord interaction object
            
        Returns:
            True if validation passes, False otherwise
        """
        if not interaction.channel_id:
            await interaction.response.send_message(
                "This command can only be used in server channels.",
                ephemeral=True
            )
            return False
        
        if not self.is_allowed_channel(interaction.channel_id):
            await interaction.response.send_message(
                "This command is not allowed in this channel.",
                ephemeral=True
            )
            return False
        
        return True
    
    async def handle(self, interaction: Interaction, *args, **kwargs):
        """
        Main command handler with validation.
        
        Args:
            interaction: Discord interaction object
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if not await self.validate_interaction(interaction):
            return
        
        await self.execute(interaction, *args, **kwargs)
    
    @abstractmethod
    async def execute(self, interaction: Interaction, *args, **kwargs):
        """
        Execute the command logic. Must be implemented by subclasses.
        
        Args:
            interaction: Discord interaction object
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        pass
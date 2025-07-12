"""
Command validation decorators for SlinkBot Discord commands.

This module provides reusable validation decorators for common
Discord command requirements like channel permissions, user roles,
and parameter validation.
"""

import functools
from typing import Callable, TypeVar, List, Optional, Any, Dict
import discord
from discord import Interaction
from utils.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class ValidationError(Exception):
    """Exception raised when command validation fails."""
    
    def __init__(self, message: str, ephemeral: bool = True):
        super().__init__(message)
        self.message = message
        self.ephemeral = ephemeral


def require_channels(*channel_names: str, error_message: Optional[str] = None):
    """
    Decorator to restrict commands to specific channels.
    
    Args:
        *channel_names: Names of allowed channels
        error_message: Custom error message (optional)
    
    Usage:
        @require_channels("movie-requests", "tv-requests")
        async def request_movie(interaction, title: str):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            channel_name = interaction.channel.name if interaction.channel else "Unknown"
            
            if channel_name not in channel_names:
                allowed_channels = ", ".join(f"#{name}" for name in channel_names)
                message = error_message or f"❌ This command can only be used in: {allowed_channels}"
                
                await interaction.response.send_message(message, ephemeral=True)
                logger.warning(f"User {interaction.user.id} tried to use {func.__name__} in #{channel_name}")
                return
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def require_roles(*role_names: str, error_message: Optional[str] = None):
    """
    Decorator to restrict commands to users with specific roles.
    
    Args:
        *role_names: Names of required roles (user needs at least one)
        error_message: Custom error message (optional)
    
    Usage:
        @require_roles("Admin", "Moderator")
        async def admin_command(interaction):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            if not interaction.guild:
                await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
                return
            
            user_roles = [role.name for role in interaction.user.roles]
            has_required_role = any(role in user_roles for role in role_names)
            
            if not has_required_role:
                required_roles = ", ".join(role_names)
                message = error_message or f"❌ You need one of these roles: {required_roles}"
                
                await interaction.response.send_message(message, ephemeral=True)
                logger.warning(f"User {interaction.user.id} lacks required roles for {func.__name__}")
                return
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def require_permissions(*permissions: str, error_message: Optional[str] = None):
    """
    Decorator to restrict commands to users with specific Discord permissions.
    
    Args:
        *permissions: Names of required Discord permissions
        error_message: Custom error message (optional)
    
    Usage:
        @require_permissions("manage_messages", "administrator")
        async def mod_command(interaction):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            if not interaction.guild:
                await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
                return
            
            user_permissions = interaction.user.guild_permissions
            missing_permissions = []
            
            for permission in permissions:
                if not hasattr(user_permissions, permission) or not getattr(user_permissions, permission):
                    missing_permissions.append(permission.replace('_', ' ').title())
            
            if missing_permissions:
                missing_perms = ", ".join(missing_permissions)
                message = error_message or f"❌ You need these permissions: {missing_perms}"
                
                await interaction.response.send_message(message, ephemeral=True)
                logger.warning(f"User {interaction.user.id} lacks permissions for {func.__name__}: {missing_perms}")
                return
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def validate_parameters(**validators: Callable[[Any], bool]):
    """
    Decorator to validate command parameters.
    
    Args:
        **validators: Parameter name -> validation function mappings
    
    Usage:
        @validate_parameters(
            title=lambda x: len(x.strip()) > 0,
            year=lambda x: 1900 <= int(x) <= 2030
        )
        async def search_movie(interaction, title: str, year: int):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            # Get function parameter names
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())[1:]  # Skip 'interaction'
            
            # Map positional args to parameter names
            param_values = {}
            for i, arg in enumerate(args):
                if i < len(param_names):
                    param_values[param_names[i]] = arg
            
            # Add keyword arguments
            param_values.update(kwargs)
            
            # Validate parameters
            for param_name, validator in validators.items():
                if param_name in param_values:
                    try:
                        if not validator(param_values[param_name]):
                            await interaction.response.send_message(
                                f"❌ Invalid value for parameter '{param_name}'", 
                                ephemeral=True
                            )
                            return
                    except Exception as e:
                        await interaction.response.send_message(
                            f"❌ Validation error for parameter '{param_name}': {str(e)}", 
                            ephemeral=True
                        )
                        return
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(max_uses: int = 5, window_seconds: int = 60, per_user: bool = True):
    """
    Decorator to add rate limiting to commands.
    
    Args:
        max_uses: Maximum number of uses in the time window
        window_seconds: Time window in seconds
        per_user: Whether rate limit is per user or global
    
    Usage:
        @rate_limit(max_uses=3, window_seconds=60, per_user=True)
        async def expensive_command(interaction):
            # Command implementation
            pass
    """
    # Store rate limit data
    usage_data = {}
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            import time
            
            current_time = time.time()
            key = str(interaction.user.id) if per_user else "global"
            
            # Clean up old entries
            if key in usage_data:
                usage_data[key] = [
                    timestamp for timestamp in usage_data[key]
                    if current_time - timestamp < window_seconds
                ]
            else:
                usage_data[key] = []
            
            # Check rate limit
            if len(usage_data[key]) >= max_uses:
                remaining_time = int(window_seconds - (current_time - usage_data[key][0]))
                await interaction.response.send_message(
                    f"⏳ Rate limit exceeded. Try again in {remaining_time} seconds.",
                    ephemeral=True
                )
                return
            
            # Record usage
            usage_data[key].append(current_time)
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def log_command_usage(include_parameters: bool = False):
    """
    Decorator to log command usage.
    
    Args:
        include_parameters: Whether to log command parameters
    
    Usage:
        @log_command_usage(include_parameters=True)
        async def search_command(interaction, query: str):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            user_id = interaction.user.id
            username = interaction.user.display_name
            channel = interaction.channel.name if interaction.channel else "DM"
            guild = interaction.guild.name if interaction.guild else "DM"
            
            log_message = f"Command '{func.__name__}' used by {username} ({user_id}) in #{channel} ({guild})"
            
            if include_parameters and (args or kwargs):
                # Get function parameter names
                import inspect
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())[1:]  # Skip 'interaction'
                
                params = {}
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        params[param_names[i]] = str(arg)[:50]  # Limit parameter length for logging
                
                for key, value in kwargs.items():
                    params[key] = str(value)[:50]
                
                if params:
                    log_message += f" with parameters: {params}"
            
            logger.info(log_message)
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def maintenance_mode_check(error_message: Optional[str] = None):
    """
    Decorator to disable commands during maintenance mode.
    
    Args:
        error_message: Custom maintenance message
    
    Usage:
        @maintenance_mode_check()
        async def normal_command(interaction):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            # Check if maintenance mode is enabled (you can implement this check)
            # For now, we'll use an environment variable or config
            import os
            maintenance_mode = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
            
            if maintenance_mode:
                message = error_message or "🚧 **Maintenance Mode**\nThe bot is currently under maintenance. Please try again later."
                await interaction.response.send_message(message, ephemeral=True)
                logger.info(f"Command {func.__name__} blocked due to maintenance mode")
                return
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


def command_cooldown(seconds: int, per_user: bool = True):
    """
    Decorator to add cooldown to commands.
    
    Args:
        seconds: Cooldown duration in seconds
        per_user: Whether cooldown is per user or global
    
    Usage:
        @command_cooldown(30, per_user=True)
        async def heavy_command(interaction):
            # Command implementation
            pass
    """
    # Store cooldown data
    cooldown_data = {}
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            import time
            
            current_time = time.time()
            key = str(interaction.user.id) if per_user else "global"
            
            if key in cooldown_data:
                time_since_last = current_time - cooldown_data[key]
                if time_since_last < seconds:
                    remaining = int(seconds - time_since_last)
                    await interaction.response.send_message(
                        f"⏳ Command on cooldown. Try again in {remaining} seconds.",
                        ephemeral=True
                    )
                    return
            
            # Record usage
            cooldown_data[key] = current_time
            
            return await func(interaction, *args, **kwargs)
        
        return wrapper
    return decorator


# Combined decorators for common use cases
def media_request_command(
    allowed_channels: List[str],
    required_roles: Optional[List[str]] = None,
    cooldown_seconds: int = 30
):
    """
    Combined decorator for media request commands.
    
    Args:
        allowed_channels: List of allowed channel names
        required_roles: List of required role names (optional)
        cooldown_seconds: Cooldown duration
    
    Usage:
        @media_request_command(
            allowed_channels=["movie-requests", "tv-requests"],
            required_roles=["Member"],
            cooldown_seconds=60
        )
        async def request_movie(interaction, title: str):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        # Apply decorators in reverse order (innermost first)
        decorated_func = func
        
        # Apply cooldown
        decorated_func = command_cooldown(cooldown_seconds, per_user=True)(decorated_func)
        
        # Apply role check if specified
        if required_roles:
            decorated_func = require_roles(*required_roles)(decorated_func)
        
        # Apply channel restriction
        decorated_func = require_channels(*allowed_channels)(decorated_func)
        
        # Apply logging
        decorated_func = log_command_usage(include_parameters=True)(decorated_func)
        
        # Apply maintenance mode check
        decorated_func = maintenance_mode_check()(decorated_func)
        
        return decorated_func
    
    return decorator


def admin_command(required_permissions: Optional[List[str]] = None):
    """
    Combined decorator for admin commands.
    
    Args:
        required_permissions: List of required Discord permissions
    
    Usage:
        @admin_command(required_permissions=["administrator"])
        async def admin_cleanup(interaction):
            # Command implementation
            pass
    """
    def decorator(func: F) -> F:
        decorated_func = func
        
        # Apply permission check
        if required_permissions:
            decorated_func = require_permissions(*required_permissions)(decorated_func)
        else:
            # Default to administrator permission
            decorated_func = require_permissions("administrator")(decorated_func)
        
        # Apply logging
        decorated_func = log_command_usage(include_parameters=True)(decorated_func)
        
        return decorated_func
    
    return decorator
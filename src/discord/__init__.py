"""
Discord integration module exports.
"""

from src.discord.formatter import format_urgent_alert, format_daily_digest
from src.discord.discord_client import DiscordClient

DiscordDispatcher = DiscordClient

__all__ = ["format_urgent_alert", "format_daily_digest", "DiscordClient", "DiscordDispatcher"]

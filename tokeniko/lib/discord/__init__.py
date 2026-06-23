# lib/discord — tokeniko's Discord channel-adapter SDK (a thin facade over discord.py).
# The public surface senses imports: DiscordClient + the two seam types.

from lib.discord.client import DiscordClient, MessageHandler
from lib.discord.models import DiscordAttachment, DiscordMessage, Destination

__all__ = [
    "DiscordClient",
    "MessageHandler",
    "DiscordMessage",
    "DiscordAttachment",
    "Destination",
]

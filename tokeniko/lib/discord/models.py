# lib/discord — i modelli normalizzati dell'adapter Discord.
# These are the ONLY types that cross the seam into `senses`: a normalized inbound event
# (DiscordMessage) and an outbound target (Destination). senses never touches discord.py types.

from typing import Optional
from pydantic import BaseModel, model_validator


# an inbound attachment, flattened to the bits senses might log (name + url).
class DiscordAttachment(BaseModel):
    filename: str
    url: str
    content_type: Optional[str] = None


# the normalized inbound event surfaced via `on_message`. Mirrors the seam documented in
# senses/README.md ({author_id, channel_id, guild_id, content, reply_to, attachments}) plus the
# minimal extras senses needs: message_id (to thread a reply under), author_name, is_dm, is_self.
class DiscordMessage(BaseModel):
    message_id: str
    author_id: str
    author_name: str
    channel_id: str
    guild_id: Optional[str] = None        # None => DM (a different conversation scope than a guild channel)
    content: str
    reply_to: Optional[str] = None        # message_id this message replies to (None if not a reply)
    attachments: list[DiscordAttachment] = []
    is_dm: bool = False
    is_self: bool = False                 # author == the bot's own user id (senses decides whether to drop)


# the outbound target. Exactly one of channel_id / user_id is set; reply_to threads the message.
class Destination(BaseModel):
    channel_id: Optional[str] = None      # a guild text channel OR a known DM channel
    user_id: Optional[str] = None         # DM a user (the adapter opens/caches the DM channel)
    reply_to: Optional[str] = None        # message_id to thread the reply under

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "Destination":
        if (self.channel_id is None) == (self.user_id is None):
            raise ValueError("Destination needs exactly one of channel_id / user_id")
        return self

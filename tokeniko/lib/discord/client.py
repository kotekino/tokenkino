# lib/discord — the Discord channel-adapter SDK.
#
# A thin, DUMB facade over discord.py: it owns the wire (gateway, heartbeat, reconnect, rate-limits —
# all discord.py's job) and speaks exactly the seam senses agrees on (senses/README.md):
#   - on_message(handler)  : register a callback fed a normalized DiscordMessage for EVERY message
#   - send(destination, content, *, kind, polish) -> message_id
#   - fetch_messages(channel_id, ...) -> list[DiscordMessage]
#   - start() / close()    : lifecycle for the senses TaskGroup + SIGTERM stop_event
#
# It knows NOTHING about the brain: no memory, no MEMAction, no stakeholder/contextKey, no NL polish.
# senses owns the translation to/from tokeniko's world; the adapter only moves bytes and normalizes them.

from typing import Awaitable, Callable, Optional

import discord

from lib.discord.constants import default_intents
from lib.discord.models import DiscordAttachment, DiscordMessage, Destination

# the inbound callback signature senses registers.
MessageHandler = Callable[[DiscordMessage], Awaitable[None]]


class DiscordClient:

    def __init__(self, token: str):
        self._token = token
        self._handler: Optional[MessageHandler] = None
        self._client = discord.Client(intents=default_intents())
        self._register_events()

    # --- seam: inbound ------------------------------------------------------

    # register the handler fed EVERY incoming message (channel + DM, including the bot's own —
    # is_self lets senses decide what to drop; per the brief every message is an input).
    def on_message(self, handler: MessageHandler) -> None:
        self._handler = handler

    def _register_events(self) -> None:
        @self._client.event
        async def on_message(message: discord.Message):
            if self._handler is not None:
                await self._handler(self._to_message(message))

    def _to_message(self, m: discord.Message) -> DiscordMessage:
        guild_id = str(m.guild.id) if m.guild is not None else None
        reply_to = (
            str(m.reference.message_id)
            if (m.reference is not None and m.reference.message_id is not None)
            else None
        )
        me = self._client.user
        return DiscordMessage(
            message_id=str(m.id),
            author_id=str(m.author.id),
            author_name=m.author.name,
            channel_id=str(m.channel.id),
            guild_id=guild_id,
            content=m.content,
            reply_to=reply_to,
            attachments=[
                DiscordAttachment(filename=a.filename, url=a.url, content_type=a.content_type)
                for a in m.attachments
            ],
            is_dm=guild_id is None,
            is_self=bool(me is not None and m.author.id == me.id),
        )

    # --- seam: outbound -----------------------------------------------------

    # deliver an ALREADY-PREPARED content to a destination. kind/polish are accepted to honor the
    # general seam but are passthrough here: for the human Discord channel content is pre-rendered NL
    # in senses, so the adapter ships it verbatim. (They are the reserved hook for a future native-zip
    # channel where polish=False would ship a serialized TKZip.) Returns the sent message id.
    async def send(
        self,
        destination: Destination,
        content: str,
        *,
        kind: str = "message",
        polish: bool = True,
    ) -> str:
        channel = await self._resolve_destination(destination)
        reference = None
        if destination.reply_to is not None:
            reference = discord.MessageReference(
                message_id=int(destination.reply_to), channel_id=channel.id
            )
        sent = await channel.send(content, reference=reference)
        return str(sent.id)

    # resolve a Destination to a discord.py "messageable" channel (guild text channel or DM channel).
    async def _resolve_destination(self, d: Destination):
        if d.channel_id is not None:
            cid = int(d.channel_id)
            return self._client.get_channel(cid) or await self._client.fetch_channel(cid)
        # user_id route: open (or reuse) the 1:1 DM channel.
        uid = int(d.user_id)
        user = self._client.get_user(uid) or await self._client.fetch_user(uid)
        return user.dm_channel or await user.create_dm()

    # --- seam: read history -------------------------------------------------

    # read recent messages of a channel/DM on demand. before/after are message ids (cursor paging).
    async def fetch_messages(
        self,
        channel_id: str,
        *,
        limit: int = 50,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> list[DiscordMessage]:
        cid = int(channel_id)
        channel = self._client.get_channel(cid) or await self._client.fetch_channel(cid)
        kwargs: dict = {"limit": limit}
        if before is not None:
            kwargs["before"] = discord.Object(id=int(before))
        if after is not None:
            kwargs["after"] = discord.Object(id=int(after))
        return [self._to_message(m) async for m in channel.history(**kwargs)]

    # --- lifecycle ----------------------------------------------------------

    # connect the gateway and run until close(). Awaited by the senses listener task.
    async def start(self) -> None:
        await self._client.start(self._token)

    # graceful disconnect — wired to the senses stop_event / task cancellation.
    async def close(self) -> None:
        await self._client.close()

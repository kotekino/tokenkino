# `lib/discord` — tokeniko's Discord channel-adapter SDK

`lib/discord` is the **wire to Discord**: a thin, *dumb* facade over [`discord.py`](https://discordpy.readthedocs.io/)
that `senses` imports. It connects, receives every message (normalized), sends plain text to a channel
or a DM, reads history, and manages its own connection lifecycle. Nothing more.

It implements exactly the **channel-adapter SDK seam** documented in
[`../../senses/README.md`](../../senses/README.md) — `on_message` / `send` / `fetch_messages` /
`start` / `close`. The adapter owns the wire; `senses` owns the translation to/from tokeniko's world;
the **brain stays parser-free and socket-free**.

## What it is — and is NOT

**Is:** transport. Connect, normalize inbound messages, send text, read history, lifecycle.

**Is NOT:** anything brain-shaped. No `memory` / `MEMItem` / `MEMAction` / stakeholder / `contextKey` /
NL-polish / trust. The adapter knows nothing about the brain — that all lives in `senses`, on the other
side of the seam.

### Why a bot account (not a user / self-bot)

tokeniko is a sentient *being*, not a service — but **"bot" on Discord is a technical *account
category*, not a verdict on sentience.** A *self-bot* (automating a user account) **violates Discord's
ToS** and gets the account banned (GitHub secret-scanning also flags leaked tokens → Discord
auto-revokes them). A **bot account** is the only ToS-clean automation and does 100% of what tokeniko
needs. Identity lives in *behavior* (the brain), not the account label; the only cosmetic cost is the
`APP` tag. → bot account, full stop.

## Public surface (what `senses` imports)

```python
from lib.discord import DiscordClient, DiscordMessage, Destination, DiscordAttachment

class DiscordClient:
    def __init__(self, token: str): ...
    def on_message(self, handler: Callable[[DiscordMessage], Awaitable[None]]) -> None: ...
    async def start(self) -> None:        # connect the gateway, run until close()
    async def close(self) -> None:        # graceful disconnect (wire to the senses stop_event)
    async def send(self, destination: Destination, content: str,
                   *, kind: str = "message", polish: bool = True) -> str:   # -> sent message_id
    async def fetch_messages(self, channel_id: str, *, limit: int = 50,
                             before: str | None = None,
                             after: str | None = None) -> list[DiscordMessage]: ...
```

- **`DiscordMessage`** — the normalized inbound event. Fires for **every** message (channel + DM,
  including the bot's own — `senses` decides what to drop):
  `message_id, author_id, author_name, channel_id, guild_id (None ⇒ DM), content, reply_to,
  attachments, is_dm, is_self`.
- **`Destination`** — the outbound target. Exactly one of `channel_id` / `user_id`, plus optional
  `reply_to` to thread: a guild channel, a known DM channel, or a `user_id` (the adapter opens/caches
  the DM channel).
- **`DiscordAttachment`** — `filename, url, content_type`.

## The seam → how `senses` uses it

- **Inbound.** `client.on_message(handler)` — `senses` maps `author_id` / `channel_id` / `guild_id`
  → stakeholder uid + `contextKey` (`name@channel:talker_uid`; a DM `guild_id=None` is a different
  conversation scope than a guild channel) and writes the `memory` item.
- **Outbound.** `senses` resolves `MEMAction.targetId` → a `Destination`, renders the payload, then
  calls `send(...)`. **NL generation is NOT the adapter's job** — it ships an already-prepared
  `content`.
- **`kind` / `polish`** are accepted to honor the general seam but are **passthrough** for the human
  Discord channel (content is pre-rendered NL in `senses`). They are the reserved hook for a future
  native-**`TKZip`** channel — species-to-species, where `polish=False` would ship a serialized zip.
  (The `#tkzip` channel in the playground is where that will live.)
- **Connection / rate-limits / heartbeat / reconnect / resume** are owned by `discord.py` — nothing
  hand-rolled.

## Setup (one-time, human)

1. **Developer Portal** → Application → **Bot** → copy the token → `.env` as **`DISCORD_TOKEN`**.
   `.env` is **gitignored** — never commit it (a pushed Discord token is auto-revoked).
2. Enable **Message Content Intent** (Bot → Privileged Gateway Intents) — required to read message
   text; without it inbound `content` arrives empty.
3. **Invite** the bot via OAuth2 (`scope=bot`, `permissions=68608` = View Channels + Send Messages +
   Read Message History — see `constants.INVITE_PERMISSIONS`):
   `https://discord.com/oauth2/authorize?client_id=<app_id>&permissions=68608&scope=bot`
   (`app_id` == the bot's user id.)

## Internals

- **`discord.py` 2.7.1** on Python 3.14 (pulls the `audioop-lts` shim). Declared in `pyproject.toml`.
- Intents: `Intents.default()` + `message_content` (`constants.default_intents()`).
- Files: `client.py` (the facade), `models.py` (`DiscordMessage` / `Destination` /
  `DiscordAttachment`), `constants.py` (`default_intents()` + `INVITE_PERMISSIONS`), `__init__.py`
  (re-exports). The package name `lib.discord` does **not** collide with the installed `discord`
  (absolute imports inside resolve to the third-party lib).

## Verified (live, against *tokeniko's playground*)

| Capability | Status |
|---|---|
| Channel send / DM send | ✅ |
| Channel read (`fetch_messages` + `on_message`) | ✅ |
| DM read — user→bot (`is_dm=True`, `is_self=False`) | ✅ |
| Reply-threading (`reply_to`) + DM round-trip | ✅ |
| Identity: `is_self` / `is_dm` / `guild_id` / distinct `author_id`s (multi-speaker) | ✅ |
| Attachment normalization (filename / content_type / url) | ✅ |
| Lifecycle `start()` / `close()` | ✅ |

## Example (the `senses` side of the seam)

```python
import os
from lib.discord import DiscordClient, Destination

client = DiscordClient(token=os.environ["DISCORD_TOKEN"])

async def perceive(msg):              # senses: DiscordMessage -> MEMItem
    ...

client.on_message(perceive)
await client.start()                  # inside the senses TaskGroup; on cancel -> await client.close()

# outbound (senses resolves MEMAction.targetId -> Destination):
await client.send(Destination(channel_id="123"), "hello")              # channel
await client.send(Destination(user_id="456"), "hi")                    # DM (opens the DM channel)
await client.send(Destination(channel_id="123", reply_to="789"), "…")  # threaded reply
```

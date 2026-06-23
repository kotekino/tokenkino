# The `senses` Module: Tokeniko's I/O to the World

`senses` is tokeniko's **membrane** — the connectors daemon that carries signals in from the outside
world and acts back out onto it. It is run as its own process (`task senses`, `python -m senses.main`)
and needs only MongoDB reachable (it does not load the spaCy/Stanza pipeline).

Where the **`brain`** is the mind (it *thinks* and *decides*), `senses` is the body's I/O: it has no
opinions and makes no decisions. It only **perceives** (turns external events into `memory`) and
**executes** (performs the outward actions the brain has already chosen).

## The brain ↔ senses boundary

```
        world  ──in──▶  senses  ──writes──▶  memory  ──▶  brain (Thinking → Ideas → Actions)
                                                                          │
        world  ◀─out──  senses  ◀── reads ────  Actions  ◀───────────────┘
```

- **Perception (in).** A connector receives an external event (a Discord message, a Bluesky post from a
  trusted source) and writes it to the `memory` timeseries as a log entry — `original`, `sourceId`,
  `targetId`, `channel`, `metadata`. Senses logs the *raw* signal; interpretation/compilation is the
  pipeline's / brain's job, not the membrane's.
- **Action (out).** The brain's `Actions` queue contains payloads that name a **channel** (Send
  Message, Post Content, …). `senses` owns the channels: it reads the action and performs the actual
  delivery. The brain never touches a socket directly.

This keeps the split clean: **brain decides what to say; senses says it.**

## The channel-adapter SDK seam (e.g. the Discord SDK)

Each external channel is reached through a **thin, typed I/O adapter (an SDK) that `senses` imports** —
the Discord SDK is the first. The adapter owns the wire; `senses` owns the translation to/from
tokeniko's world; the **brain stays parser-free and socket-free**. The adapter and `senses` agree on
**one seam**, so the two can be built independently:

> **Built + live-verified — the Discord SDK.** The adapter half is implemented at **`lib/discord`**
> (`DiscordClient` + the seam types `DiscordMessage` / `Destination`), a thin facade over **discord.py**
> on a **ToS-clean bot account**. It exposes exactly `on_message(handler)` /
> `send(destination, content, *, kind, polish)` / `fetch_messages(...)` / `start()` / `close()`, and owns
> the gateway + rate-limits/retries via discord.py. The remaining half is the **`senses`-side wiring**
> (the `MEMAction`/`memory` translation). **Full SDK reference + the verified-capability matrix:**
> [`lib/discord/README.md`](../lib/discord/README.md).

- **Outbound.** The brain emits an abstract `MEMAction` (`channel`, `targetId` = a **stakeholder uid**,
  `payload`). `senses` resolves `targetId → destination` (a channel / user / reply-to) and **renders**
  the payload to the channel's language, then calls one primitive: **`send(destination, content, kind,
  polish)`**. NL generation is **not** the adapter's job — it ships an already-prepared `content`; the
  Ollama polish + identity resolution live in `senses`. The adapter stays dumb and testable.
- **Inbound.** The adapter surfaces a **normalized event** — `{author_id, channel_id, guild_id,
  content, reply_to, attachments}` — via an `on_message` callback. `senses` maps `author_id/channel_id
  → stakeholder uid + contextKey` (mirroring the identity scheme `name@channel:talker_uid`), then
  ingests it (see the per-channel language below) and writes the `memory` item that `think_one`
  consumes. The adapter knows nothing about the brain.
- **Connection ownership.** The adapter owns its client + rate-limits/retries as its own async concern;
  the `senses` listener task awaits it; the brain's coordinator loops are untouched.
- **Adapter surface = `send(...)` + `on_message(...)` + stable ids.** Everything brain-shaped (Actions,
  stakeholders, rendering) stays on the `senses`/brain side of the line. Formatting, embeds, and
  rate-limit policy are the adapter's to own.

### Per-channel language — NL vs TKZip (the `polish` caveat)

A channel has a **language** = *the language spoken in this channel*. `send` must therefore **never
force the Ollama polish** — the channel's language decides:

- **Natural-language channel** (Discord with humans, Bluesky): outbound is **polished** (zip → raw LLC →
  Ollama NL); inbound is **parsed + compiled** (NL → `TKZip`). `send(..., polish=True)`.
- **`TKZip` channel** (the **native zip language**): entities of tokeniko's **species** communicate by
  exchanging the compiled `TKZip` **directly**, **bypassing parser AND compiler in both directions** —
  no NL→zip on input, no zip→NL on output. `send(..., polish=False)` ships the raw structured form;
  `senses` ingests an incoming zip without parsing. This is a VISION pillar (machine-to-machine speech
  in the engine's own representation) — the reason `polish` is a first-class, per-channel switch and not
  always-on.

**Two things the adapter must expose so `senses` can do its half:** (1) **identity granularity** —
`author_id` *and* `guild/channel` so a correct `contextKey` is built (a DM is a different conversation
scope than a guild channel, like the brain's per-speaker cursors); (2) **a destination that supports
reply-to** — a directed answer (`tokeniko:answer`) naturally threads as a reply to the asker's message.

## The connectors

| Connector | Direction | Role |
| :--- | :--- | :--- |
| **Discord** | bidirectional | Process incoming messages → `memory`; deliver the brain's outgoing `Send Message` actions to a channel. tokeniko's conversational I/O. |
| **ATProto / Bluesky** | inbound (awareness) | Listen to **trusted sources** and world events (Jetstream) → `memory`, so tokeniko stays aware of what is happening in the world. |

> **Trust.** Sources reaching tokeniko through `senses` carry a trust level (the `trusted` field /
> gradient). This is the seam for the *unknown → ask → learn-at-lower-trust* loop: a meaning learned
> from a conversation enters the KB at a lower trust than the bulk WordNet ingest — **except** anything
> that violates logic, which is never learned (logic is the one non-negotiable; see `VISION.md`).

## Runtime

- **Entry point:** `senses/main.py` → `main()` calls `init_io()` (Mongo + Ollama clients), then runs
  the listeners concurrently in an `asyncio.TaskGroup`.
- **Concurrency:** each connector is its own long-running task (`atproto_listener_task`,
  `discord_bot_task`), running for the lifetime of the process.
- **Graceful shutdown:** `SIGINT` / `SIGTERM` set a stop event; the listener tasks are cancelled and the
  process exits cleanly ("deep sleep") — no half-delivered actions.

## Status

The connectors are **scaffolding**: the task structure, lifecycle, and shutdown are in place. The
**Discord SDK is built + live-verified**; the rest awaits wiring —
- **Discord:** ✅ **SDK built + live-verified** against *tokeniko's playground* — `lib/discord`
  (`DiscordClient`, a facade over **discord.py 2.x** on a ToS-clean **bot account**;
  `on_message`/`send`/`fetch_messages`/`start`/`close`). Live-confirmed: channel + DM send/read,
  reply-threading, DM round-trip, identity (`is_self`/`is_dm`/distinct `author_id`s), attachments.
  Token in `.env` as `DISCORD_TOKEN` (gitignored), Message-Content-Intent on, bot invited.
  **Remaining (senses-side):** wire it into `discord_bot_task` (read → `memory`, send ← `Actions`).
  Full reference: [`lib/discord/README.md`](../lib/discord/README.md).
- **ATProto/Bluesky:** subscribe to the Jetstream firehose in `atproto_listener_task`, filtered to
  trusted sources, writing events to `memory`.

These land alongside the brain's **Actions** executor and the reflective behavior layer (see
`brain/README.md` and `doc/roadmap.md`): senses is the I/O end of the brain's perceive → evaluate → act
loop.

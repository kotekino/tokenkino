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

The connectors are **scaffolding**: the task structure, lifecycle, and shutdown are in place, but the
real clients are stubs awaiting wiring —
- **Discord:** hook a `discord.py` client into `discord_bot_task` (read → `memory`, send ← `Actions`).
- **ATProto/Bluesky:** subscribe to the Jetstream firehose in `atproto_listener_task`, filtered to
  trusted sources, writing events to `memory`.

These land alongside the brain's **Actions** executor and the reflective behavior layer (see
`brain/README.md` and `doc/roadmap.md`): senses is the I/O end of the brain's perceive → evaluate → act
loop.

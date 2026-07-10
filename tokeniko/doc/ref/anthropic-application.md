# Anthropic support application — record & strategy (2026-07-10)

> Reference doc (NOT status): the application submitted to the Anthropic startups program, the
> rationale behind it, and the fallback path. Revisit when the first response arrives.

## What was applied for

**Program:** Anthropic for Startups — https://claude.com/form/startups-application
(category: **nonprofit** — allowed by the form; tokeniko is nonprofit **by design**: a research
project whose goal is knowledge itself, the premise stated openly even knowing it may reduce the
odds against venture-track applicants).

**Support requested (two asks):**
1. **Claude Code / agent credits** — the codebase is built in daily collaboration with Claude
   agents, currently entirely self-funded; support finishes the core roadmap.
2. **API credits for the output layer** — the architectural idea: the reasoning core stays
   **embodied and local** (conclusions, reasoning, memory never leave the body; hardware tuned for
   CPU / large RAM / large disk — vector math + MongoDB — deliberately NOT for big GPUs), while the
   **non-core polishing/output phase (TKZip → English)** is served by the best external model via
   API — first choice Claude. One-liner: *the symbolic core owns the reasoning, Claude owns the
   tongue.* This lets the body stay lean (no expensive GPU hardware for the small, non-core local
   Ollama role) while the voice is best-in-class.

## The submitted texts

**"Tell us briefly about your startup and how you plan to use Claude" (50–500 chars; 492):**

> Tokeniko is a nonprofit research project: a neuro-symbolic engine that compiles natural language
> into a fixed-size mathematical representation (TKZip), stored as permanent, queryable memory.
> Logic is hardwired; all knowledge is learned. A persistent instance on a single local machine
> already reasons, derives theorems, and converses on Discord. I plan to use Claude as its language
> surface — rendering TKZip conclusions into natural English via the API — while the symbolic core
> stays local.

**"Where do you want support from Anthropic?" (492):**

> Two things. First, Claude Code credits: the codebase is built in close, daily collaboration with
> Claude agents, currently self-funded; support would let me complete the core roadmap. Second, API
> credits for the output layer: the reasoning core deliberately runs on modest local hardware (CPU,
> RAM and disk for vector math and MongoDB — no large GPUs), and Claude via API would serve as the
> non-core translation layer (TKZip to English), keeping the body lean while the voice is
> best-in-class.

## Tactical notes (agreed)

- **Lead with what works:** the live instance (reasons, derives theorems, converses on Discord) and
  the public window **tokeniko.online** beat any roadmap.
- **Feature the nonprofit nature, don't hide it** — sentence one; honesty filters into the right pile.
- **Neutral engineering register** in all application material: "persistent reasoning engine,"
  "derives theorems," "queryable memory" — never "digital twin" / "alive mind" / "consciousness."
- **Have a number ready** if usage is asked: concrete €/month self-funded across Claude Code + API.

## Fallback path (decided)

If the startups application doesn't land: apply to **Anthropic's research-oriented access routes**
(external researcher / academic API credit programs) — arguably the *better* fit for a nonprofit
cognitive-architecture research project. The two paragraphs above work there nearly verbatim.
The author considers this the stronger match; startups program is attempt #1 because the form was
open and the nonprofit category exists.

## Status

- 2026-07-10 — form submitted. Awaiting first response.

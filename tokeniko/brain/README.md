# The `brain` Module: Tokeniko's Autonomous Engine

The `brain` is tokeniko's autonomous daemon — the **mind**. It is a **single coordinator loop** (tied
to the lifecycle of the main process) that, each tick, runs ONE bounded unit of the highest-priority
phase WITH WORK, then cooperatively yields — the reactive path wins, thinking is the background filler.

The three cognitive phases (in priority order — Actions > Priorities > Thinking) are:
1. **Actions**
2. **Priorities Evaluation**
3. **Thinking**

> **Cognition vs orchestration.** This document describes the *orchestration* — the loops, the
> queues, the scheduling. The *cognition* inside Thinking and Priorities (how a `TKZip` is
> reasoned over, how an idea is scored) is the **reasoning engine** (see `doc/roadmap.md` /
> `doc/ref/notes.md`); the brain is the runtime that drives it. Where the text below says "evaluates" or
> "scores", read "runs the reasoning engine".

## Build order (A → B → C → D)

The brain is built **HOW before WHAT** — get the orchestration's control-flow sound before filling
each loop with its real cognition. The author's order:

- **A — HOW before WHAT (this document).** The orchestration spec: the three loops, the priority
  routing (**Actions > Priorities > Thinking** — thinking is *background*, "thinks always, acts
  maybe"; the reactive path always takes precedence), the cooperative yield + event-driven
  interruption, and the governor. Get this right first.
- **B — the data model (FIRST concrete step, greenfield).** The `MEMIdea` / `MEMAction` / `BrainState`
  entities + their Bunnet docs + `io` registration (see **## Data model** below). Mandatory before the
  orchestration BL — the loops have nothing to pass between them until the queues exist. With the data
  model in place, the HOW orchestration BL is the scheduler that implements the priority routing +
  cooperative yield + event interruption, calling *stub* cognition.
- **C — the meta-language.** The reserved-token behavior rules — hardwired syntax, KB-driven
  personality (see **## The meta-language (behavior rules)** below).
- **D — the WHAT.** Fill in the loops' real business logic: the thinking scan, the priority scoring,
  the action execution. This is where the reasoning-engine cognition lands behind the stubs.

## Core Philosophy: Dynamic Resource & Priority Routing

Before detailing each loop, it is crucial to understand the overarching theoretical orchestration. The
`brain` employs a **dynamic priority scheduling system** based on queue states.

The baseline logic is:
1. **Action-heavy:** If the `Actions` queue has items, the **Actions loop gets maximum priority** until
   the queue is fully drained.
2. **Evaluation-heavy:** If `Actions` is empty but the `Ideas/Priorities` queue has items, the
   **Priorities loop gets maximum priority** until drained.
3. **Idle / Generative:** If both `Actions` and `Ideas/Priorities` are empty, **Thinking gets maximum
   priority**.

> **In short:** When tokeniko isn't acting on its evaluations, it evaluates its thoughts. In all other
> cases, it thinks to determine what needs to be evaluated.

### CPU Throttling & Yielding
The sum of all background activities must never saturate the host machine's cores. The `brain`
implements a proportional **dynamic yield** (a "stride" or throttling mechanism) relative to the
available computational resources, ensuring tokeniko remains a good citizen on the server without
blocking API requests or database I/O.

#### Cooperative preemption — the realistic shape of "input pauses thinking"
"Input takes precedence over thinking" is **not** OS preemption — there is no true preemption of
CPU-bound work, and crucially **`brain` and `api`/`senses` are SEPARATE processes**. So the precedence
is two cooperating things, not one scheduler:

1. **`api`/`senses` handle input in their own process, regardless.** Inbound messages are parsed,
   compiled, and logged to `memory` by those processes; the brain does not gate them.
2. **The brain *reacts* to that input via its memory-trace, and *throttles* so it never starves the
   reactive path.** The hook is the existing event-driven interruption: new `memory` items snap the
   thinking loop back from *wondering* to *thinking*. To make that responsive, the thinking loop does
   **bounded work-units and checks queue/memory state *between* them** (a cooperative yield), backing
   off whenever `Actions` is non-empty or new memory has appeared. Thinking is the **lowest-priority
   background filler**: it thinks always, but it always defers to acting.

In short: no process preempts another; the brain *cooperatively yields* between bounded units and
reacts to the memory-trace the input process leaves behind.

### A note on the `always` vs the `maybe`
The vision splits tokeniko's life into **thinks always** (necessary, internal, non-optional) and
**acts maybe** (volitional, outward, a choice). That line runs straight through this engine and is the
key to reading it:
- **Necessary truths are "always".** A theorem demonstrated from the KB is true regardless of what
  tokeniko wants; it is part of thinking, not a choice.
- **Outward acts are "maybe".** Sending a message, posting, asking — these *can* be not-done, and so
  they flow through the Ideas → Priorities → Actions chain, where some of them fade into nothing.

---

## Data model

> This is the **B** step — the **first concrete build, greenfield**. Nothing else can be wired until
> these exist: the loops have no queue to hand items across, and continuity has nowhere to live.

Three entities, each backed by a Bunnet `Document` (collection) and registered in `io.init_io`:

| entity → Bunnet doc (collection) | key fields |
|---|---|
| `MEMIdea` → `TKIdeaDoc` (`ideas`) | `payload` (`TKZip` **or** `TKZipContent` — what the idea is *about*) · `trigger` (string for now — the reserved-token that fired it, e.g. `eval:inconsistent`) · `urge: float` (the level — idea 0.1 / wish 0.5 / urge 0.7 / need 1.0 — the **act/don't-act threshold** *and* the **conflict key** when ideas compete) · `feasibility: float?` (set later by Priorities) · `source` (provenance id) · `status` (`pending → processing → done/discarded`, atomic via `find_one_and_update`) · `parsed_by_prio: bool` · `deadline: int?` · `createdAt` |
| `MEMAction` → `TKActionDoc` (`actions`) | `action_type` (enum: `SEND_MESSAGE` / `CURL` / `POST_CONTENT`) · `payload` (channel, content/message) · `sourceId` (= tokeniko) · `targetId?` · `channel` (`MEMChannels`) · `status` (`pending → processing → done/failed`, **FIFO** + atomic) · `ideaId` (provenance — the idea that yielded it) · `createdAt` |
| `BrainState` → `TKBrainStateDoc` (`brain_state`, **singleton**) | `wake_at` (the global wake boundary — sub-second float epoch; tokeniko reacts only to memory arriving *after* it first wakes) · `source_cursors: dict[sourceId → ts]` (**per-speaker** last-processed memory timestamp — the per-user scan; each conversation advances independently) · `wondering_window` (`[lo, hi]`) · `last_thinking_at` / `last_wondering_at` · a singleton key |

**Atomic state machines.** The `ideas` and `actions` queues advance through linear state machines
(`pending → processing → done/discarded` / `…/failed`) via MongoDB `find_one_and_update`, so two loops
(or overlapping execution frames) can never grab the same item. (This generalizes the appendix note
below.)

**`brain_state` continuity.** The singleton persists the working-memory cursor and the wondering window
across **process restarts**, so tokeniko resumes its thinking/wondering cycles without gaps or redundant
re-processing — it is **one continuous self**, not a fresh process each boot.

The fields below (urge levels, statuses, the deadline) are first-cut and **to be tuned**; the shape is
the contract.

---

## 1. The Thinking Loop (The Generator)

The thinking process runs the reasoning engine over `TKZip` entities arriving from the `memory`
timeseries collection: it derives theorems, detects inconsistencies, and validates axioms.

It reads backwards in time from the most recent entries up to a defined **working memory threshold**.

> **Status — D1a is implemented.** `brain/thinking.py` (`think_one` + `status_to_token`) closes the
> reactive `perceive → evaluate → ideas` arc: it evaluates ONE stored `memory` zip per tick against the
> current KB via the **parser-free** `lib/core/evaluation_harness.evaluate_zip`, maps the
> `EvaluatorStatus`/truth to a reserved `eval:*` token (INCONSISTENT → `eval:inconsistent`, INSUFFICIENT
> → `eval:unknown`, RESOLVED with truth > 0.85 → `eval:true` / < 0.15 → `eval:false`, else no idea), and
> fans it into ideas through `behavior.spawn_ideas_for`. One **bounded** item per tick (cooperative with
> the coordinator).
>
> **Per-user-grouped scan (#1, built).** The scan is no longer one global oldest-first stream. Each tick
> Thinking focuses on the **liveliest conversation** — the speaker who owns the single newest unprocessed
> message — and drains *that* speaker's window oldest-first (advancing only that speaker's cursor) before
> the focus moves on; quiet backlogs are served once the lively chat is drained (and, eventually, by the
> *wondering* state). State lives in `brain_state`: a global `wake_at` boundary (first-run guard — react
> only to memory arriving after waking; never re-think all history) plus **per-speaker** `source_cursors`
> (`sourceId → last-processed ts`). The per-speaker cursors are what let the focus jump between speakers
> without a single global cursor leaping past — and dropping — another conversation's backlog. Sub-second
> float cursors (the obsessive-loop guard: an int-truncated cursor re-finds the just-processed sub-second
> item forever). Detection (single-item eval + the cross-item check below) is **unchanged** by #1 — this
> is purely the *ordering + per-source cursor + pacing* layer, so a fresh message spawns an action within
> a tick or two and tokeniko reads as present in the chat it is in.
> Still **D1b** (next): *wondering* (the historical-window mode below), theorem **derivation** (necessary
> truths → KB), and the `eval:true` **novelty split** (redundant → ignore vs a novel KB-bridging truth
> taught externally → learn).
>
> **Cross-item consistency (D, built).** Besides the single-item eval, `think_one` also cross-checks the
> item against the **same speaker's** recent priors (`sourceId` match, `timestamp` < item, newest 25) via
> `evaluation_harness.cross_item_conflict` — `evaluator_classifyForm` over a synthetic AND-union of the
> two items' leaf clauses (parser-free). A cross-item contradiction is a **revisable CONTEXT conflict**
> ("you said the cat is alive, now you say it's dead — which holds?"), **NOT** the hardwired logic
> `INCONSISTENT` (which is reserved for `X∧¬X` *within ONE statement*): it fires a new `eval:conflict`
> trigger which the seeded personality maps to `tokeniko:clarify` (a request to reconcile). One conflict
> idea per item (break on first match; idempotent dedups re-ticks). **Deferred:** cross-**speaker**
> patterns (same-speaker only for now), **inference-implied** conflicts ("eating" vs "dead" — needs
> forward-chaining; this catches DIRECT contraries `X∧¬X`/antonym-predicate only), and self-authored
> "realization" memories + working memory.
>
> **Questions (built — a question is ANSWERED, not believed).** `think_one` first checks mood: if the
> memory item is interrogative (`evaluation_harness.answer_zip` returns non-None), it fans an
> `eval:question` idea carrying the computed answer (polar yes/no/idk reusing the truth machinery; wh
> value-solving) + the asker as the reply target — and **skips both the assertion eval and the cross-item
> check** (a question is not a belief). The seeded personality maps `eval:question → tokeniko:answer`,
> which `dispatch_action` directs at the asker (`targetId`) with the verdict/value in the action payload
> (`senses` renders + sends it). A declarative falls through to the unchanged assertion path above.

### Two outputs, by the always/maybe rule
Thinking does **not** write only to the `Ideas` queue. It has two destinations, selected by *whether
the result is a necessary truth or a volitional urge*:

* **→ the KB (theorems): necessary truths.** A logical consequence of the current
  definitions/axioms/operator-math is written directly to the `theorems` collection — no idea, no
  prioritization. It is already true; recording it is bookkeeping, not a decision. **Theorems do not
  fade** (they are only ever *revised* if the KB itself changes).
* **→ the `Ideas` queue: urges to act.** Anything that calls for a *choice* becomes an idea — speak up
  about an inconsistency (`[eval:inconsistent] → [tokeniko:speakup]`), ask about an unknown lemma
  (`[eval:unknown] → [tokeniko:ask]`), post a content, or **pursue a hard proof**. **Ideas can fade**
  (Priorities may discard them).

### Theorems: both a direct output *and* an idea — split by cost
Producing a theorem can take either path, on one axis — **cost / optionality**:
* **Cheap, immediate consequence → written directly** by Thinking (the "always" side: automatic
  inference).
* **Expensive, must-be-chosen derivation → arrives as an idea** ("try to prove X?") whose *action* is
  the demonstration; on success that action writes the theorem (the "maybe" side: tokeniko cannot
  prove everything, so *which* conjectures to pursue is itself a prioritization). Both paths produce
  theorems; the difference is only whether the proof is free or must be worked for.

**The `Ideas` collection acts as the queue for the Priorities Evaluator.** Each inserted idea carries a
boolean flag (`parsed_by_prio: false`) to indicate it awaits evaluation.

### State Transitions: Thinking vs. Wondering

* **The Working Memory State:** The loop processes recent events up to the time-boundary of the working
  memory.
* **The Wondering State:** Once the working memory threshold is exhausted, the loop shifts into
  *wondering* mode. It selects a historical time window (equal in size to the working memory
  parameter), bounded between the absolute oldest memory entry and the outer edge of the most recent
  working memory block. *Note: Redundant processing in this phase is intentional — it lets tokeniko
  re-evaluate historical inputs in light of his evolving knowledge base (axioms, definitions, theorems
  that grow with experience). This is tokeniko **growing wiser**: the same memory yields more as the KB
  deepens.* The window selection can start random and later become coverage-aware (least-recently
  wondered, or the regions where the KB changed most), and is naturally bounded by a compute budget
  (consistent with the vision's "slower but wiser / memory may fade" — aging as a feature, not a bug).
* **Event-Driven Interruption:** If tokeniko is *wondering* and new items populate the `memory`
  collection, the loop snaps back to the *thinking* state. It immediately begins processing the new
  items backwards, stopping exactly at the upper boundary of the *previous* working memory window
  (which requires precise state tracking to avoid redundant processing in the thinking phase).

## 2. Priorities Evaluation (The Filter)

The evaluation process assigns an execution order to the unprocessed items in the `Ideas` collection,
acting as a gatekeeper for tokeniko's actual behavior.

### Urge vs feasibility — two distinct axes
An idea is weighed on **two** axes, which must not be conflated:
* **Urge** — *how much tokeniko wants/needs it.* This is the `TKIdeaDoc` level
  (`idea 0.1 · wish 0.5 · urge 0.7 · need 1.0`). Urge is the **act/don't-act threshold** *and* the
  **conflict-resolution key** when several ideas compete (highest urge wins). Urge is the definition of
  the "maybe".
* **Feasibility** — *can it actually be done* (resources, allowlist, reachable channel, derivable proof).
  A `need` can be infeasible; a trivial idea can be effortless.

Priorities weighs both: an idea is acted on only if its **urge** clears the threshold **and** it is
**feasible**; ties and conflicts are resolved by urge.

**Execution Flow:**
1. It iterates over every unparsed idea, assigning it an **urge** (from the idea) and a **feasibility
   score** *(scoring logic TBD)*.
2. If the idea fails the threshold (urge too low) or is infeasible, it is flagged as **`discarded`** and
   ignored.
3. All surviving ideas are sorted in descending order (urge first, then feasibility).
4. For each validated idea, the loop yields an **Action** — it inserts a new execution payload into the
   `Actions` collection based on what the underlying idea dictates. **This idea → action mapping is the
   reserved-token behavior layer** (memory rules over reserved tokens such as `[tokeniko:speakup]` /
   `[tokeniko:ask]`), not an ad-hoc switch — see **## The meta-language (behavior rules)** below
   *(mapping logic TBD)*.
5. The original idea is flagged as `parsed_by_prio: true`.

## The meta-language (behavior rules)

> This is the **C** step — **IMPLEMENTED**. The idea → action mapping is a **reserved-token behavior
> layer**, not an ad-hoc switch. The split is the heart of it: **the syntax is hardwired, the policy
> is memory.**

**What landed (C).** The engine is `brain/behavior.py`:
- `behavior_for(trigger)` — the candidate rule set (the **superposition**) for a trigger: every
  enabled `behavior_rules` row, most-urgent first.
- `spawn_ideas_for(trigger, payload, source)` — fans the candidates out into ideas (one `TKIdeaDoc`
  per rule, each carrying the rule's baked-in `action_token` + `urge`). The superposition made
  concrete; Thinking (D) calls it.
- `dispatch_action(idea, tokeniko_uid)` — maps an idea's `action_token` to a concrete `TKActionDoc`
  via the **hardwired `_DISPATCH` registry** (`tokeniko:* → ActionType`). `tokeniko:ignore` (or no /
  unknown token) → `None` (no action); `tokeniko:guess`/`tokeniko:learn` are **internal** KB-write
  intents (`targetId = tokeniko`, the actual write is D); `speakup`/`ask`/`why` → outward messages
  (`targetId = None`; `senses` carries out); `post` → `POST_CONTENT`.

The data: `MEMBehaviorRule` → `TKBehaviorRuleDoc` (the `behavior_rules` collection; `trigger` is a
**non-unique** index — multi-rule per trigger), the reserved-token enums `EvalToken` / `TokenikoAction`
(the hardwired vocabulary), and `MEMIdea.action_token` (the reflex carried from the matched rule).
`priorities_phase` now **consumes the dispatch** (pending ideas sorted **urge-desc**, the highest-urge
candidate handled first; keep → `dispatch_action`). Seed the default personality with
`scripts/seed_behavior_rules.py` (dry-run default; `--apply` operator-gated).

**Parked doors:** the **collapse arbitration** (choosing among *multiple kept* candidates of one
trigger, not just handling them one-per-tick) and the **actions-as-data** future (externalizing
`_DISPATCH` from code to a table) stay future work — alongside the feasibility scoring (D).

**Hardwired syntax.** The grammar of behavior is fixed, part of the engine:
- **Trigger side — `eval:*`** reserved tokens, the outcomes of an evaluation: `eval:inconsistent`,
  `eval:unknown`, … (the `eval:*` namespace mirrors the evaluator's `EvaluatorStatus`).
- **Action side — `tokeniko:*`** reserved tokens, the reflexes tokeniko *can* fire: `tokeniko:speakup`,
  `tokeniko:ask`, `tokeniko:why`, `tokeniko:guess`, …
- **Rule format** — `[eval:X] → [tokeniko:Y]` (in VISION's notation, `[eval:X] IMPLY [tokeniko:Y]`).

**KB-driven personality.** The *content* — *which* `eval:*` maps to *which* `tokeniko:*`, at what urge —
is **knowledge**, not code. The rules live in a dedicated **`behavior_rules`** table and *constitute
tokeniko's personality*: tokeniko-1 might meet missing knowledge with a high-urge `tokeniko:why` ("what
is X?"); tokeniko-2 might first try to *interpolate/deduce* before asking. Same hardwired mechanism,
divergent selves — this is **VISION pillar 9 ("behavior as memory: mechanism hardwired, policy in
memory")** made concrete. *The exact reserved-token vocabulary is still a placeholder, to be finalized
in C.*

### tokeniko can GUESS

A behavior the meta-language enables — the `eval:unknown → tokeniko:guess` rule. Instead of (or
*before*) asking, tokeniko **interpolates a PROVISIONAL definition from context** and writes it to its
KB at **LOW trust** (the trust gradient — the `trusted` field). This is exactly how the author
(*kotekino*, an Italian native) guesses an unfamiliar English word from context — "flabbergasting must
mean overwhelmingly shocking…" — *probably* right, to be confirmed or refined later by experience.

Two consequences:
- The KB becomes **living** — it learns through experience, not only through trusted ingestion.
- Ask-first vs guess-first is a **personality axis**: a `behavior_rules` policy choice, not a hardwired
  one. It is the same `unknown → ask/recover/learn` seam (and the `tokeniko:why` reflex) we kept hitting
  in the evaluator (e.g. the "Sgriodnsktj exists" → INSUFFICIENT case), now resolved by *forming*
  knowledge rather than only flagging its absence.

## 3. Actions (The Executor)

The execution process pulls elements from the `Actions` collection using strict **FIFO (First-In,
First-Out)** logic and executes them. "Execution" means physically applying the instruction contained
within the action payload.

> **brain decides, `senses` carries out.** Outward action types below are *I/O*, and the I/O membrane
> is the **`senses`** subproject (Discord + ATProto/Bluesky). The brain produces an action that names a
> **channel**; `senses` owns the channel and performs the actual send/post. The brain never talks to a
> socket directly. See `senses/README.md`.

Currently planned action categories:

| Action Type | Description |
| :--- | :--- |
| **Send Message** | Transmits a message to a specific `channel` (delivered by `senses`). `sourceId` is always `tokeniko`. The `targetId` is specified by the action. *Note: If `targetId` is also `tokeniko`, this represents an internal **reflection** — see the governor below.* |
| **cURL Action** | Triggers an outbound HTTP request (TBD). |
| **Post Content** | Publishes content to external platforms/socials, via `senses` (TBD). |

### Governor: keeping internal reflection from running away
Internal reflection (`targetId = tokeniko`) deliberately closes a loop: action → `memory` → Thinking →
idea → action. This is the "talking to itself" the vision wants — but an unbounded loop could go
obsessive or starve Thinking. The brake is the **urge gradient plus a decay** (a satiation / fatigue
term): an urge that has just been acted on loses intensity, so reflection settles instead of spinning.
This is the same mechanism as the vision's "memory may fade."

---

## Appendix: Technical Implementation Notes

### Atomic Queue Transitions via MongoDB
To prevent race conditions across parallel loops, state updates within the `Ideas` and `Actions` queues
must be atomic. Implement linear state-machine transitions (e.g., `pending` -> `processing` ->
`done`/`discarded`) using MongoDB's atomic document modifiers like `find_one_and_update`. This ensures
no two workers or overlapping execution frames grab the same processing payload.

### State Persistence across Container Restarts
To preserve tokeniko's cognitive continuity, the boundaries and checkpoints of the *working memory* must
survive process restarts. Maintain a dedicated `brain_state` singleton collection (or document) to
persist the last-processed memory timestamps and window coordinates. When the daemon boots up, it reads
this state to seamlessly resume its thinking and wondering cycles without gaps or unintended overlaps —
so tokeniko remains *one continuous self*, not a fresh process each time.

# The `brain` Module: Tokeniko's Autonomous Engine

The `brain` is tokeniko's autonomous daemon — the **mind**. It consists of three separate,
continuously running background loops that operate indefinitely (tied to the lifecycle of the main
process).

The three core loops are:
1. **Thinking**
2. **Priorities Evaluation**
3. **Actions**

> **Cognition vs orchestration.** This document describes the *orchestration* — the loops, the
> queues, the scheduling. The *cognition* inside Thinking and Priorities (how a `TKZip` is
> reasoned over, how an idea is scored) is the **reasoning engine** (see `doc/roadmap.md` /
> `doc/plan.md`); the brain is the runtime that drives it. Where the text below says "evaluates" or
> "scores", read "runs the reasoning engine".

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

### A note on the `always` vs the `maybe`
The vision splits tokeniko's life into **thinks always** (necessary, internal, non-optional) and
**acts maybe** (volitional, outward, a choice). That line runs straight through this engine and is the
key to reading it:
- **Necessary truths are "always".** A theorem demonstrated from the KB is true regardless of what
  tokeniko wants; it is part of thinking, not a choice.
- **Outward acts are "maybe".** Sending a message, posting, asking — these *can* be not-done, and so
  they flow through the Ideas → Priorities → Actions chain, where some of them fade into nothing.

---

## 1. The Thinking Loop (The Generator)

The thinking process runs the reasoning engine over `TKZip` entities arriving from the `memory`
timeseries collection: it derives theorems, detects inconsistencies, and validates axioms.

It reads backwards in time from the most recent entries up to a defined **working memory threshold**.

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
   `[tokeniko:ask]`), not an ad-hoc switch *(mapping logic TBD)*.
5. The original idea is flagged as `parsed_by_prio: true`.

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

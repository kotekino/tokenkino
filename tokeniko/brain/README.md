# The `brain` Module: Tokeniko's Autonomous Engine

The `brain` is tokeniko's autonomous daemon. It consists of three separate, continuously running background loops that operate indefinitely (tied to the lifecycle of the main process). 

The three core loops are:
1. **Thinking**
2. **Priorities Evaluation**
3. **Actions**

## Core Philosophy: Dynamic Resource & Priority Routing

Before detailing each loop, it is crucial to understand the overarching theoretical orchestration. The `brain` employs a **dynamic priority scheduling system** based on queue states. 

The baseline logic is:
1. **Action-heavy:** If the `Actions` queue has items, the **Actions loop gets maximum priority** until the queue is fully drained.
2. **Evaluation-heavy:** If `Actions` is empty but the `Ideas/Priorities` queue has items, the **Priorities loop gets maximum priority** until drained.
3. **Idle / Generative:** If both `Actions` and `Ideas/Priorities` are empty, **Thinking gets maximum priority**.

> **In short:** When tokeniko isn't acting on its evaluations, it evaluates its thoughts. In all other cases, it thinks to determine what needs to be evaluated.

### CPU Throttling & Yielding
The sum of all background activities must never saturate the host machine's cores. The `brain` implements a proportional **dynamic yield** (a "stride" or throttling mechanism) relative to the available computational resources, ensuring tokeniko remains a good citizen on the server without blocking API requests or database I/O.

---

## 1. The Thinking Loop (The Generator)

The thinking process evaluates and analyzes `TKZip` entities arriving from the `memory` timeseries collection *(exact internal logic and tools for "evaluation/analysis" are TBD)*. 

It reads backwards in time from the most recent entries up to a defined **working memory threshold**. The output of this loop is exclusively the creation of new items in the `Ideas` collection. 

**The `Ideas` collection acts as the queue for the Priorities Evaluator.** Each inserted idea carries a boolean flag (`parsed_by_prio: false`) to indicate it awaits evaluation.

### State Transitions: Thinking vs. Wondering

* **The Working Memory State:** The loop processes recent events up to the time-boundary of the working memory.
* **The Wondering State:** Once the working memory threshold is exhausted, the loop shifts into *wondering* mode. It selects a random historical time window (equal in size to the working memory parameter), bounded between the absolute oldest memory entry and the outer edge of the most recent working memory block. *Note: Redundant processing in this phase is intentional: it allows tokeniko to re-evaluate historical inputs in light of its evolving dynamic knowledge base (axioms, definitions, and theorems that grow with experience).*
* **Event-Driven Interruption:** If tokeniko is *wondering* and new items populate the `memory` collection, the loop snaps back to the *thinking* state. It immediately begins processing the new items backwards, stopping exactly at the upper boundary of the *previous* working memory window (which requires precise state tracking to avoid redundant processing in the thinking phase).

## 2. Priorities Evaluation (The Filter)

The evaluation process assigns an execution order to the unprocessed items in the `Ideas` collection, acting as a gatekeeper for tokeniko's actual behavior.

**Execution Flow:**
1. It iterates over every unparsed idea, assigning it a **feasibility score** *(scoring logic TBD)*.
2. If the score falls below a specific threshold, the idea is flagged as **`discarded`** and ignored.
3. All surviving ideas are sorted in descending order by score.
4. For each validated idea, the loop yields an **Action** — meaning it inserts a new execution payload into the `Actions` collection based on what the underlying idea dictates *(mapping logic TBD)*.
5. The original idea is flagged as `parsed_by_prio: true`.

## 3. Actions (The Executor)

The execution process pulls elements from the `Actions` collection using strict **FIFO (First-In, First-Out)** logic and executes them. "Execution" means physically applying the instruction contained within the action payload.

Currently planned action categories:

| Action Type | Description |
| :--- | :--- |
| **Send Message** | Transmits a message to a specific `channel`. `sourceId` is always `tokeniko`. The `targetId` is specified by the action. *Note: If `targetId` is also `tokeniko`, this represents an internal **reflection**.* |
| **cURL Action** | Triggers an outbound HTTP request (TBD). |
| **Post Content** | Publishes content to external platforms/socials (TBD). |

---

## Appendix: Technical Implementation Notes

### Atomic Queue Transitions via MongoDB
To prevent race conditions across parallel loops, state updates within the `Ideas` and `Actions` queues must be atomic. Implement linear state-machine transitions (e.g., `pending` -> `processing` -> `done`/`discarded`) using MongoDB's atomic document modifiers like `find_one_and_update`. This ensures no two workers or overlapping execution frames grab the same processing payload.

### State Persistence across Container Restarts
To preserve tokeniko's cognitive continuity, the boundaries and checkpoints of the *working memory* must survive process restarts. Maintain a dedicated `brain_state` singleton collection (or document) to persist the last-processed memory timestamps and window coordinates. When the daemon boots up, it reads this state to seamlessly resume its thinking and wondering cycles without gaps or unintended overlaps.
"""
# test-feedback.md — empirical fragility log (observed → diagnosis → action)

The **running feedback channel** from driving the live brain with real/synthetic input. Distinct from
`roadmap.md` (strategy): this is the *empirical* record of what tokeniko actually does, why it fails,
and the action it implies. Append a new dated section after each test session; promote action items to
the roadmap's consolidation pass.

**Severity rubric.** S0 = *logic-is-sacred breach* (accepts a false/contradictory statement as true, or
rejects a logical truth) · S1 = wrong answer/action, identifiable cause, well-formed input · S2 =
right-by-luck / fragile / inconsistent across equivalents · S3 = cosmetic / mood-marker / graceful
degradation.

**Reproduce.** `scripts/fragility_batch.py` (the categorized probe matrix + injector, `prepare=0` = raw
neuro-symbolic core, no Ollama pre-filter) → `scripts/trace_fragility.py` (category-aware retrospective
tracer: re-runs each stored zip for the rationale, joins ideas/actions, bins by component × severity).
Start `api` + `brain`, wipe `memory`/`ideas`/`actions` (raw pymongo — the timeseries `.find().delete()`
is a no-op), inject, wait for full drain (per-speaker cursors caught up — NOT a premature lull), trace.

---

## Session 2026-06-24 — the 54-probe fragility batch (12 categories, 4 speakers)

### The root cause behind most of it
Founding doctrine: **geometry = soft unification, algebra = inference.** The core bug is that
**geometry leaks into the truth verdict** — the evaluator emits *confident* true/false from vector
proximity even when the relational layer has **no proof**. One leak, two harms:
- proximity **high** → a false claim accepted TRUE (`a cat is a dog` 0.93)
- proximity **low** → a true-but-unprovable claim REFUTED (`a tiger eats meat` 0.12 → speakup)

The corrective principle: **no relational proof ⇒ abstain (INSUFFICIENT), never a confident verdict.**
Geometry connects; only the algebra/graph decides truth.

### Component × Severity
| Sev | Component | Finding | Evidence |
|---|---|---|---|
| **S0** | Grounding (geometric leak) | distinct concepts accepted **TRUE** within a kingdom | cat=dog .93 · advice=ad .92 · Mari=Luca .98 · "is advice an ad?"→YES .91 |
| **S1** | Grounding (relational gaps) | true-but-unprovable → **confidently refuted + speakup** | a tiger eats meat .12 → eval:false → speakup |
| **S1** | Identity / coreference (R1) | pronoun subjects **collapse** (no subject sense) → self/other Qs decided by bare predicate | are you human NO · am I alive NO · are you curious NO *(want IDK)* · do you exist YES *(right by luck)* |
| **S1** | Identity (individuals) | distinct individuals conflated; `sameIndividual` override not applied | Mari is Luca .98 → ignore |
| **S1** | Consistency (cross-item) | `eval:conflict → clarify` **over-fires** on non-contradictory same-speaker pairs | many `ben` items |
| **S2** | WSD | sense-number mismatch breaks subsumption | robin→`bird.n.01` vs predicate `bird.n.02` → .15 |
| **S2** | Grounding (disjointness) | same-kingdom distincts neither true nor refuted (limbo) | circle=square .15, no reaction |
| **S2** | Behavior layer | imperatives mis-grounded as false → **speakup** (argues with commands) | "tell me about cats" .10 → speakup |
| **S2** | Mood (R4b) | a premise inside a question is swallowed | "I am human, do I think?" → NO |
| **S3** | Mood (R4a) | `??` / `!?` not read as questions | "the cat is a dog??" → assertion |

### Working well (the keep-set — guard against regression)
- INCONSISTENT kernel fires: `the cat is dead and alive` → INCONSISTENT → speakup.
- Cross-kingdom disjointness: `a stone is an animal` → 0.00, refuted (so R2's fix is *finer-grained*
  disjointness, not new machinery).
- Forward-chaining + materialization: `a cat eats meat`, `a human is mortal` → 2 theorems (silent learn).
- WH-solver: war→hostility, cat→feline. Learn-by-guessing: every unknown → why + guess, consistently.
- Parser resilience: 54 messy inputs incl. gibberish/fragments — zero crashes.

### Typo-guard verdict (empirical answer to the open doubt)
With `prepare=0`, typos **degrade gracefully, never catastrophically**: abstain (INSUFFICIENT) or
mis-ground only when the typo is itself a real word (`doge`). The guard is a **quality boost, not a
safety necessity** → **defer it**; its Ollama cost isn't justified when the failure mode is honest "I
don't understand," and the abstain-not-guess grounding fix makes mis-grounds rarer still.

### The solution-package (coherent, spine-first) — the next coding batch
- **🦴 SPINE — grounding-truth overhaul.** An identity/copular claim ("X is Y") gets a verdict ONLY
  from the relational layer (subsumption / **finer-grained distinctness** — siblings & cousins are
  distinct, not just cross-kingdom). No graph evidence ⇒ INSUFFICIENT. Geometry stops voting on truth.
  *Clears every S0 + the tiger S1 + circle/square + imperative-speakup at once; most logic-is-sacred-
  aligned change available.*
- **🏛 Pillar 2 — identity & coreference.** Pronoun resolution (`I`→asker, `you`→tokeniko) + individual-
  subject grounding + apply the `sameIndividual` override on "X is Y". Fixes R1 + Mari-is-Luca.
- **📚 Pillar 3 — graph/WSD coverage (data).** Fill is_a gaps (tiger→carnivore) + sense-number
  canonicalization (bird.n.01≡n.02 for subsumption). Fixes tiger/robin.
- **🔧 Cleanups.** Cross-item over-fire tightening (S1) · `??`/`!?` + premise-in-question mood (R4a/R4b) ·
  behavior-layer `eval:false` requiring real refutation (falls out of the spine).

---

## Lineage — earlier manual sessions (the R-series)
- **R1** — pronoun-subject collapse (self/other questions decided by predicate geometry). → SPINE pillar 2.
- **R2** — geometric false-TRUE on distinct concepts (advice=advertisement). → SPINE.
- **R3** — definitional polar inconsistency (gloss-question YES for "advertising" but NO for "advice"):
  WSD sense misalignment between the question and the stored definition. → Pillar 3 (sense canonicalization).
- **R4** — mood markers (`??` assertion; premise-in-question swallowed). → Cleanups.

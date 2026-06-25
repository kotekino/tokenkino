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
- **🦴 SPINE — grounding-truth overhaul. ✅ LANDED (Option A).** A **bare** copular noun-identity
  ("X is Y", senses = exactly `{subject, predicate}`, both nouns) gets its truth ONLY from the is_a
  graph — subsumption → TRUE, tiered-disjoint → FALSE, **neither → INSUFFICIENT (abstain)**; geometry
  no longer votes (`_is_bare_identity` gate in `e_statement.py`). A gloss ("X is [a Y with modifiers]")
  carries extra roles (`predicate_nmod`) → not bare → keeps its definition-match. **Verified:** every S0
  cleared (cat=dog 0.93→INSUFFICIENT, advice=ad, circle=square, robin=bird→honest abstain); subsumption/
  disjoint/INCONSISTENT untouched; the affect-gloss stays TRUE 1.0. **Option B (sibling-distinctness in
  the graph) REJECTED outright** — distinctness is *learned*, not logic (lawyer & husband are both
  human yet the same entity; only world-knowledge separates cat/dog from lawyer/husband). It will come
  from KB meta-axioms + wondering, never a logic patch.
- **🏛 Pillar 2 — identity & coreference. ✅ LANDED.** A personal pronoun carries its referent's
  stakeholder **uid** into `identities` (`I`→asker, `you`→tokeniko; uid-only, `c_entities.py` meta
  branch), and an **individual-subject clause abstains** (0.5) when no fact/graph decides it
  (`_has_individual_subject` / `_is_distinct_individual_identity` in `e_statement.py`) — an individual's
  properties/identity are contingent FACTS, never geometry. **Verified:** "are you human?"/"do you
  exist?"/"am I alive?" → honest **IDK** (were wrong-confident); "Mari is Luca" → INSUFFICIENT (was 0.98,
  P2c — distinct names may corefer, abstain not refute); spine + keep-set intact. NB "do you exist?" → IDK
  *until* the self-KB seeds "tokeniko thinks" + the property-cogito → then it DERIVES YES (his first
  theorem). (Places like "Rome is a city" still geo-ground geometric-true — benign, not yet principled.)
- **📚 Pillar 3 — #1 abstain completion ✅ LANDED; #2 WSD (parked).** Diagnosis: the graph is FINE —
  the failures are **WSD sense-selection**, not missing edges (tiger compiled to `tiger.n.01` = *a fierce
  person* not `tiger.n.02` the animal; robin→`bird.n.01` but the predicate "bird"→`bird.n.02`). **#1
  (landed):** the spine's principle generalized — a clause the graph/chainer did NOT decide keeps its
  geometric grounding ONLY if it is an AFFIRMATIVE near-exact definition match (`>= _GEOM_AFFIRM` in
  `e_statement`); a denied clause or a mid/low score → **abstain** (geometry may affirm, never refute or
  guess). "a tiger eats meat" → INSUFFICIENT (was eval:false→speakup, an active falsehood); the
  affect-gloss still grounds 1.0; keep-set + cogito intact. **#2 (parked, incremental):** the WSD itself
  — context-sensitive sense selection (tiger→animal) + sense-number canonicalization for subsumption
  (robin/bird) — makes claims *provable* (TRUE) rather than just honestly abstained. The hard, general
  WSD problem; deferred.
- **🔧 Cleanups.** Cross-item over-fire (S1) ✅ DONE (`f1cea3b`) · `??`/`!?` mood (R4a) ✅ DONE · a
  premise inside a question (R4b) → **investigated + PARKED** (see the 2026-06-25 session below — it
  is the doorstep of conditional reasoning, a feature, not a patch) · behavior-layer `eval:false`
  requiring real refutation (falls out of the spine).

---

## Session 2026-06-25 — consolidation cleanups (S1 + R4a landed; R4b investigated → parked)

### S1 — cross-item `eval:conflict` over-fire ✅ FIXED (`f1cea3b`)
Root cause: the cross-item check unions the new item's clauses with a prior's and asks
`classifyForm` "is the union contradictory?" — but **any internally-INCONSISTENT half makes the union
trivially contradictory**. So a single self-contradiction in a speaker's history (probe #5 "the cat is
dead and alive") **poisoned every later pairwise check** with that speaker → ~7 false `eval:conflict`
fires ("many ben items"). Fix: `cross_item_conflict(clauses_a, clauses_b)` now fires only if the
**union contradicts yet NEITHER half is self-contradictory alone** — the contradiction must EMERGE
from the combination. Verified on the live baseline zips: poison pairs OLD=FIRE→none; a genuine
flip-flop (each side consistent, union contrary "dead/alive") still fires correctly. The intra
INCONSISTENT kernel is untouched.

### R4a — `??` / `?!` / `!?` not read as questions ✅ FIXED
Stanza glues a multi-char terminal like `??`/`?!`/`!?` into ONE PUNCT token, so the parser's exact
`t.text == "?"` test missed it (the input fell through to a declarative). Fix (one line,
`parser.py`): the `?` test is now a **substring** (`"?" in t.text`). Verified: `??`/`?!`/`!?` → polar
question; single `?` and wh-`??` still work; `!` and plain declaratives unchanged (no regression).

### R4b — a premise inside a question is swallowed → ⏸ PARKED (it is a FEATURE, not a patch)
**Re-confirmed and SHARPENED.** Post grounding-floor, the old wrong **NO** for "I am human, do I
think?" is now an honest **IDK** — but the bug still has teeth in one direction:
- `"a stone is an animal, is a cat an animal?"` → **NO, conf 1.0** (WRONG — the *question* is true).
  A **false premise** (`stone is_a animal` = 0.0) is **AND-folded** into the polar verdict and drags
  it to a confident-wrong NO — a creed violation (never confidently wrong).
- `"the cat is a dog, is a cat an animal?"` → IDK (an abstaining premise drags a provable question
  down). Same mechanism, milder.

**Root cause (mapped to the dep tree).** Stanza subordinates the premise as a **`ccomp` under the
question's ROOT** ("am"/"is".head = the question verb) — the *"this clause is a co-submitted premise,
not the asked thing"* signal genuinely exists upstream (the dep relation, `TKLLCContent.clause_type`)
— **but it is DROPPED at the zip layer**: every leaf arrives `clause_type=None`, `dubitative=1.0`
(`_stamp_mood` blankets *all* leaves). So `answer_zip` can't tell premise from question and
`_polar_answer` reads `result.truth` = the **whole-statement** AND-fold → the premise corrupts it.

**Why no heuristic shortcut exists.** "A false leaf ⇒ the fold is honest" is wrong: for a genuine
**conjunctive** question — `"is a cat an animal and a stone?"` — a false leaf (stone) *should* yield
NO. Only a **premise** leaf must be excluded. Distinguishing them *requires* propagating the
main-vs-subordinate signal to the zip; there is no safe shortcut.

**The proper fix (parked, = the doorstep of conditional reasoning).** Two parts: (1) propagate a
"asked question vs co-submitted premise" discriminator onto `TKZipContent` and set it in the compiler
(main clause = question; an independent `ccomp` with its own subject = premise) — i.e. **per-clause
mood**, not the blanket `_stamp_mood`; (2) have `_polar_answer` fold **only the question leaves**.
That is the *floor* (answer Q on the KB alone, premise can't corrupt it → honest IDK / correct YES).
The *real* behavior — **USE** the premise to answer ("given P, is Q?") — is **hypothetical/conditional
reasoning**, a genuine feature. Decision: do it for real with the question-answering deepening, don't
cover it with a half-measure. Normal questions and separately-submitted premises are unaffected; the
trigger (a premise comma-spliced onto a question in one input) is uncommon.

---

## Lineage — earlier manual sessions (the R-series)
- **R1** — pronoun-subject collapse (self/other questions decided by predicate geometry). → SPINE pillar 2.
- **R2** — geometric false-TRUE on distinct concepts (advice=advertisement). → SPINE.
- **R3** — definitional polar inconsistency (gloss-question YES for "advertising" but NO for "advice"):
  WSD sense misalignment between the question and the stored definition. → Pillar 3 (sense canonicalization).
- **R4** — mood markers (`??` assertion; premise-in-question swallowed). → Cleanups.

# Brain v1.1 — grounding/chaining refinements (reference)

> The backlog + detailed brainstorming for the **Brain v1.1** roadmap item. Surfaced by the author's
> live **curated-fuel test** (2026-07 soak): feeding tokeniko real axioms/definitions and watching the
> wondering loop, several gaps appeared between the connections a human sees and the theorems the engine
> derives. This doc holds the *why* and the *proposed approaches*; the roadmap carries only the pointer.
> NOT a status doc — items here are discussed in detail and tracked as ONE "Brain v1.1" roadmap item.

## The clarified mental model (settled — the frame for everything below)

**Definitions ANSWER; axioms GENERATE.** Two different jobs:
- **Grounding** = *"is this claim I was handed true?"* — uses **definitions** (rich gloss meaning). This
  is evaluation. Definitions are perfect here and this is now fully clear.
- **Chaining** = *"what new truths follow that nobody stated?"* — uses **axioms**. The forward-chainer
  eats only two shapes: **universal rules** ("all X …") and **individual facts** ("I value logic",
  "I am a software"). Definitions are NOT on the chaining path today.

The v1.1 thesis (the author's instinct, validated): we are **burning crossable information** by leaving
definitions (and generically-stated taxonomy) out of chaining. A definition is a *biconditional local
truth*; a taxonomic copula is a *universal local truth*. Both should feed derivation — the clean logical
skeleton for chaining, the rich gloss for grounding (the same source, two organs).

---

## #1 — Generic "a X is a Y" doesn't chain (the natural-taxonomy gap) — HIGHEST PRIORITY

**Observed.** The author stated a taxonomy the natural way and the chain snapped:
- `I am a thinking machine` (fact ✓) — but `a thinking machine is a thinker` compiled with
  **quant=existential**, and `a thinker is a living creature` with **quant=existential** too.
- `_extract_rules` only turns **UNIVERSAL** leaves into rules → these bridges become **no rule and no
  is_a edge** → the graph has no `machine→thinker`, no `thinker→living_creature` (verified `False`).
- Result: tokeniko never reaches `thinker`, so "I exist / I want to know my creator / I am a living
  creature / I am mortal → ⊥ I am immortal" all fail to fire. Only the two axioms phrased with an
  explicit universal ("all softwares run…", the cogito "everything that thinks…") derive anything.

**Root cause.** English states taxonomy with the **generic singular** ("a dog is a mammal" = *all* dogs).
tokeniko maps the article "a" → existential/generic, so a genuinely-universal taxonomic copula is
dropped from chaining. The natural way to teach an ontology doesn't work; only "all X are Y" does.

**Proposed fix (surgical, reuses step-3/4 machinery).** A copular **noun→noun** statement *is* an is_a
assertion regardless of the surface quantifier — so **extract is_a edges from AXIOMS** (any quantifier),
and feed them into the chainer's is_a reader. Two clean properties:
- **Reuses the reader-union + provenance + revocation** already built for the definition-edge tier.
- **Trust tier is correct and meaningful here:** an axiom is the author's *asserted truth*, so
  axiom-edges are **HIGH-trust (~0.9)**, distinct from the low-trust (0.3) WordNet-mined definition
  edges. So "I am a thinker" derived through the author's own taxonomy comes out **trusted**, while a
  WordNet-mined cascade stays low-trust. This *is* the trust gradient, and the digital-twin direction
  (the author is the authority). [[cascade-amplifies-isa-noise]] contained by trust-tiering.
- **Implementation sketch:** compute axiom-is_a in-memory from the small axiom set in `_load_active_kb`
  (no new collection — re-derived each load), union into the relations reader; provenance = the axiom id
  (so it's a premise + revocable, like a tier edge). Dry-run probe first (show which edges the current
  axioms would contribute).

**Workaround available today (no code):** phrase bridges as universals — "all thinking machines are
thinkers", "all thinkers are living creatures", "all living creatures are mortal". These become real
membership/property rules → the full chain (incl. the immortal contradiction) fires.

**Related thread — the payoff contradiction.** Once the chain reaches `tokeniko is mortal`, it clashes
with the axiom `I am immortal`. Detecting a **derived-theorem vs stated-axiom** contradiction is NOT the
intra-statement kernel (that's X∧¬X within one statement) nor today's cross-item memory check. It needs
a check that a newly-derived theorem is consistent with the active axiom/theorem set (a KB-consistency
guard at materialization). Small but distinct — bundle into v1.1.

---

## #2 — Predicate objects/complements dropped — DEFER (parser-level)

**Observed (two author catches).**
- `all softwares run in a hardware` → rule `(run, obj=None)` → derives **"tokeniko run"** (lost "in a
  hardware" — a **prepositional** complement).
- `all thinkers want to know their creator` → mis-compiled to a spurious `IMPLY`, extracted as
  `(want, obj=None)` → derives **"tokeniko want"** (lost "to know their creator" — an **infinitival /
  control** complement).

**Root cause.** Rule/fact extraction reads only the **direct object** (`senses['direct']`). Prepositional
("run in X") and control/infinitival ("want to know Y") complements aren't the direct object → dropped;
the derived theorem loses its meaning. This is a **parser/compiler** representation gap (Stanza-level,
adjacent to the parked prepositional-complement + subject-rebinding work) — the harder class.

**Workaround today:** phrase with a direct object — "all softwares need hardware", "all thinkers seek
their creator". Deferred because the workaround suffices for testing and the real fix is deep.

---

## #3 — Definitional sufficiency (the sufficient direction) — THE GENERATIVE ARC

**The idea (author's instinct, deep-analyzed).** A definition is a **biconditional**:
`valuable ⟺ has(worth ∨ merit ∨ value)`. Every biconditional yields TWO directions:
- **Necessary** (`valuable → has worth/merit/value`) — what step 3 (genus→is_a) + step 5 (differentia)
  already extract; cascades DOWN the is_a hierarchy.
- **Sufficient** (`has merit → valuable`) — **the direction we've been burning.** `tokeniko has merit`
  (fact) + `merit → valuable` (rule) ⟹ `tokeniko is valuable`. This is where facts **cross** into
  abstract concepts — analytic (true by the definition), and the interpolation the author wants.

**Why it's SAFER than the parked step-5 differentia cascade (the key insight).** The sufficient rule
fires **directly on a property fact — it does not walk the is_a graph** → nothing to amplify. Decision
A's core objection ([[cascade-amplifies-isa-noise]]: cascading over WordNet is_a multiplies bad edges)
**dissolves** for this direction. Single-hop, clean provenance (1 fact + 1 rule = 2 premises).

**It's already half-built.** The cogito rule `everything that thinks exists` → `think → exist` is a
`property_conditioned` rule, and the chainer **already fires these** (`evaluator_forwardChain` step 4).
`has merit → valuable` = `(have, merit) → (valuable, ∅)` — the exact `cond_pred/cond_obj → concl_pred`
shape the chainer consumes. So the **disjunctive/single-condition case needs zero chainer changes** —
only an *extractor* that reads these rules off definitions (instead of only off hand-written
"everything that…" axioms).

**The rigor — respect the OPERATOR TREE (or it over-fires).**
- **Disjunctive definiens** (`valuable = has worth ∨ merit ∨ value`): each disjunct independently
  sufficient → three rules. ✅
- **Conjunctive definiens** (`carnivore = animal ∧ eats meat`): the *whole conjunction* is sufficient →
  ONE rule `(animal ∧ eats_meat) → carnivore`. Modest chainer extension (multi-condition fire) — and
  it's **recognition/classification** (deduce class from properties), the sound inverse of what we have.
- **The trap — nested disjunction:** `vehicle = conveyance that transports (people ∨ goods)`. That "or"
  is buried in the OBJECT of "transports", NOT a top-level sufficient-condition split — naive flattening
  gives the false `transports goods → vehicle` (a pipeline isn't a vehicle). **Sufficiency reads ONLY
  off the TOP-LEVEL operator** of the definiens (which the zip already represents as an AND/OR tree).

**Residual risks:** definiens WSD noise (does "merit" pick the right sense?) and triviality ("valuable"
is tiny) — both contained by the step-4 net (low-trust, ≥2-premise gate, dedup, revocable). Tiny-but-
true accumulates into a web; it doesn't poison.

**Build path (dry-run first):** (1) probe how the compiled definition zip represents definiens
disjunction/conjunction at the top level, + the spurious rate; (2) extractor → low-trust rule tier
(disjunctive reuses the chainer; conjunctive = multi-condition extension); (3) re-run wondering → watch
the *sufficient* cascade (facts crossing into concepts). This is the honest second attempt at
definitions-as-fuel — cleaner than differentia-down-hierarchy because it never rides the noisy graph.

---

## #4 — Revocation durability + the chat-zombie — QUICK band-aid; real fix is subject-WSD

**Observed.** "a confabulation has feather" reappeared after revocation.

**Two mechanisms.**
1. **Archiving doesn't stop re-derivation.** `_kb_wonder_one`'s `held` set counts only ACTIVE
   (archived=False) theorems, so an *archived* one is re-attempted and re-materialized as a NEW active
   theorem **as long as its premise edge survives**. So the **edge deletion** is the operative part of
   `revoke_edge.py --apply`, not the archive. Quick fix: include archived originals in `held` (a revoked
   theorem stays dead), OR a revoked-tombstone.
2. **The edge re-mines from a bad source.** `chat.n.01→bird.n.02` comes from the definition "a chat is
   birds having a chattering call" where **the SUBJECT "chat" is mis-sensed as chat.n.01 (conversation)**
   — a subject-WSD error the step-3 untangle doesn't fix (it only disambiguates the GENUS). Re-running
   `extract_definitions --apply` re-creates the edge. **Real fix: subject-WSD at ingestion** (extend the
   untangle to the subject, or gate the edge when subject/genus are ontologically disjoint at a reliable
   tier — the same tiered-disjointness we already have). Until then, revocation is a band-aid.

---

## Priority (impact ÷ effort)

1. **#1 generic-taxonomic** — HIGH impact (unblocks natural ontology teaching), LOW-MED effort (reuses
   machinery). **Do first.**
2. **#3 definitional sufficiency** — HIGH impact (the generative unlock), MED-HIGH effort. **The arc.**
3. **#4 revocation/subject-WSD** — MED impact, LOW-MED effort (the `held`-includes-archived quick fix is
   cheap; subject-WSD is the deeper piece).
4. **#2 predicate-complement** — MED impact, HIGH effort (parser-level). **Defer** (workaround exists).

*Sequencing note:* the **BPMN process maps come FIRST** (the current consolidation checkpoint) — they
clarify exactly which lane each fix lives in before we build. Brain v1.1 resumes after.

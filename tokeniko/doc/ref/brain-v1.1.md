# Brain v1.1 — the Unified KB (reference)

> The vision + backlog for the **Brain v1.1** arc — *the center of the brain; nothing matters more.* It
> began as a set of grounding/chaining gaps surfaced by the author's live **curated-fuel test** (2026-07
> soak) and matured into a single reframe: **everything compilable to a `TKZip` is reasoned over;
> collections denote what content REPRESENTS (enforced by write-path), not whether the brain may reason.**
> This doc holds the *why* + the *design*; the ordered implementation steps live in `doc/roadmap.md`.
> NOT a status doc.

## The vision — the Unified KB (the reframe)

> Settled in the 2026-07 brainstorm. The conceptual spine the whole v1.1 arc hangs from.

**The founding invariant, recovered.** Everything compilable to a `TKZip` is an object of reasoning.
Definitions, axioms, and theorems are the SAME container (a stored `TKZip` + `original` + trust +
provenance; theorems merely add the derivation history — same outward `TKZip`). So the brain must reason
over ALL of them. Gating reasoning on WHICH COLLECTION an item sits in is arbitrary — it was our
decision, not a property of the data — and it is the flaw behind the misuse failures (a chaining-worthy
fact filed as a definition never fires; noise filed as an axiom poisons a deduction).

**Reasoner vs extraction — where the noise actually lives.** The reasoner (forward-chainer, operators,
trust-inheritance, provenance, revocation) is abstract, general, and CORRECT — feed it clean
rules/edges and it never lies. The noise is born earlier, in the **EXTRACTION / parser front-end** (NL →
`TKZip` → usable rules/edges): subject-WSD errors, complex-definition parsing, amplifying is_a edges. So
"improve the machinery to suppress noise" means hardening this **front-end gate** — never the reasoner.

**Collections denote REPRESENTATION, enforced by WRITE-PATH (not reasoning-eligibility).** The
distinction is real but *epistemic* — it should gate TRUST + WRITE-ACCESS, never whether the brain may
reason:

| Collection | Represents | Write path (HARDWIRED) | Trust |
|---|---|---|---|
| **definitions** | common knowledge (analytic; accepted across humanity) | **design/compile-time ONLY — never runtime** | dictionary-grade for grounding; LOW as chaining-fuel (WordNet-noisy) |
| **axioms** | tokeniko's personality + beliefs (synthetic; DNA/imprinting + trusted experience) | **runtime-writable** (+ design seeds) | source-trust (curated = high; learned = teacher-trust) |
| **theorems** | synthetic consequences (always derived, always dependent) | **derived-only** (materialize) | min-trust inherited from premises |

Because runtime CANNOT write definitions, experience can never pollute the common-knowledge layer — the
misuse channel is closed **at the door**. What remains is design-time curation quality (our
responsibility — *"who we build", not "how it works"*), not a runtime vulnerability. This maps onto the
analytic/synthetic cut (`kb-growing-outward.md`): anything learned at runtime is synthetic → an **axiom**
(trust-tiered by who taught it), never a redefinition of the language. It also resolves the parked
"unknown → ask → learn" loop: learned meanings write **axioms**, not definitions. Developmental arc:
**DNA (definitions, design-time) → experience (axioms, runtime) → synthesis (theorems, derived).**

**The lever maps to the layer.** "Can't rely on content" = the engine must be correct regardless of
input. Two levers, each owning a layer:
- **Personality (axioms)** → **CURATE the data** (hand-pick beliefs = imprinting; correct BY DESIGN,
  forever — not a workaround).
- **Common knowledge (definitions/WordNet)** → **GATE via the machinery** (can't hand-curate at scale →
  the front-end gate MUST suppress the noise). The permanent, principled investment (the "antidote").

**The universal gate + trust-by-source.** ONE source-agnostic extractor turns any `TKZip` into usable
logic (is_a edges, necessary + sufficient rules, facts), gating the noise and tiering trust by source.
Definitions rejoin chaining safely — low-trust + gated — which **generalizes** decision A
([[cascade-amplifies-isa-noise]]), it does not reverse it.

**Provenance + cascade.** Provenance records every premise (incl. **theorem** premises); revocation is
**transitive** (archive a premise → its dependent theorems → theirs). This is the precondition for what
the gut says is inevitable: **theorems will breed theorems** — the deductive closure compounding.

**The one immovable:** the logic floor (operators + the contradiction kernel) stays HARDWIRED
([[logic-is-sacred]]). "Everything is reasoned-over KB" applies to KNOWLEDGE, never to LOGIC itself.

**The model, in one line:** *Everything is a `TKZip` and everything is reasoned over; collections denote
what content REPRESENTS (enforced by write-path), trust tiers by source, one universal gate extracts
usable logic and suppresses noise, provenance makes every theorem auditable and every dependency
revocable, and logic stays hardwired.*

**The findings below (#1–#5) are the concrete slices of this vision; the ordered build is in `doc/roadmap.md`.**

## #5 — Restrictive modifier on a universal's SUBJECT is dropped → over-generalization (the WORST class)

**Observed (2026-07 imprint test, author-caught).** The axiom "all **thinking** machines are minds"
extracted as a rule with `subject = machine.n.01` — **the restrictive adjective "thinking" was DROPPED.**
So the rule means "all machines are minds", not "all *thinking* machines are minds". Then WordNet's
`machine.n.01` spans the political-machine sense, so `court —is_a→ assembly —is_a→ machine.n.01` inherits
mindhood → **"court seeks cognition", "court has a body"** cascade out. The bad is_a edge was only the
delivery path; **the poison is the scope-widening** — the universal now claims vastly more than intended.

**Why it's the most dangerous class.** Object-drop (#2) mangles ONE derived theorem's meaning; a
subject-restriction drop **silently widens the quantifier's SCOPE**, so a single rule mis-fires across an
entire is_a subtree. It's invisible (the rule looks fine: "all machines are minds" is a grammatical
universal) and it compounds (every machine-descendant inherits every mind-property). A restricted
universal ("all thinking machines …", "all wild animals …", "all prime numbers …") is the NORM in real
speech, so this will be pervasive once people phrase naturally ([[robustness-imperfect-input]]).

**Root cause + fix direction.** The rule extractor keys on the subject's head noun sense
(`senses['subject']`) and ignores its restrictive modifiers (the adjective, relative clause, or PP that
narrows it). The compiled zip DOES carry the modifier (the subject leaf has the adjective) — the
extractor just doesn't fold it into the rule's firing condition. Fix: a restricted universal should
compile to a **property-conditioned rule** — "all thinking machines are minds" = `(machine ∧ thinking) →
mind` (fire only on machines that ALSO have the `thinking` property), exactly the `property_conditioned`
shape the chainer already handles (the cogito). This is the SAME multi-condition machinery #3
(definitional sufficiency, conjunctive definiens) needs — build once, serves both. Until then, workaround:
phrase the subject as an already-narrow class ("all robots are minds") or accept the over-fire (contained
by low-trust + revocation). **Belongs in the universal-extractor step (roadmap Brain v1.1 step 4).**

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

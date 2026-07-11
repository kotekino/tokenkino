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

## Session 2026-07-09 — the ENRICHED soak (three-tier fuel; step-5 validation)

Driven inline (API up, daemon off) over the full three-tier fuel (627 genus edges + 116 sufficient +
90 differentia @0.3 + 67 axioms). Converged QUIESCENT in 10 ticks / 528s → 25 active theorems
(14 @0.9 imprint-derived, 11 @0.3 tier crossings — the money-family «X stores information» via the
medium differentia, some four-hop). Trust stratification held: 0 noise in the 0.9 band. Specimens:

**S1 — the NL self-talk round-trip corrupted a theorem (the budget mutant).** *Observed:* every
class-conclusion «X stores information» collapsed onto ONE stored theorem; wondering re-derived the
rest every tick forever (the void spin). *Diagnosis:* materialize renders the conclusion to NL and
re-parses it — «a budget stores information» parses "stores" as the plural NOUN (shop), the subject
sense is lost, and the semantic dedup key degenerates to (no-subject, information.n.01) for the whole
family; the service dedup then returns "complete, no write" and `_kb_wonder_one` never learns the
conclusion is held. *Action (landed same session):* sense-pinned materialize (the brain sends the
conclusion's senses; the service pins them into the compiled zip before dedup/store) + dedup
suppression in `_kb_wonder_one` + the parked **mentalese constructor** (self-talk should not round-trip
through NL at all; until then the round-trip doubles as a parser-robustness harness).

**S1 — an eternal socket block froze the loop (not a hang, a dead TCP read).** *Observed:* the soak
sat 18+ min at 0% CPU mid-cursor-read (laptop sleep during the first run; a second occurrence under
caffeinate). *Diagnosis:* pymongo has NO default socket timeout — a read on a dead/stalled connection
blocks forever. *Action (landed):* opt-in `MONGO_SOCKET_TIMEOUT_MS` in `init_io` (long-lived loops
set it; a timed-out op raises and the tick retries) + faulthandler armed in soak drivers.

**S2 — plural-genus collection/member confusion.** *Observed:* «a forest has trunk/branch» @0.3.
*Diagnosis:* the definition "a forest is the TREES …" minted tier edge `forest.n.01 is_a tree.n.01` —
a collection defined by its members reads as a member. *Action:* parked (plural-genus gate: a plural
genus head is collection-of, not is_a). Left as honest 0.3 beliefs (auditable, revocable).

**S2 — differentia object mis-sense.** *Observed:* «a sector illustrates fabric» @0.3. *Diagnosis:*
"a figure … illustrating TEXTUAL material" — the differentia OBJECT got the textile sense (fabric) of
"material". *Action:* parked with the general differentia-object WSD residual.

---

## Session 2026-06-29 — the first long-wondering SOAK (clean-slate self-derivation)

Wiped `memory`/`ideas`/`actions`/`theorems` to **KB-only** (axioms/definitions/behavior_rules +
stakeholders kept), then ran the brain unprompted. It re-derived its self-knowledge from the KB alone.
Full structured account via **`scripts/soak_report.py <brain_log>`** (the new soak analyzer: performance
· results · churn/convergence · errors-by-layer · DB integrity · expected-coverage · verdict).

### Result — CLEAN (the consolidation held; the loop lives)
- **Full coverage, no spurious extras.** Re-derived exactly the 4 ≥2-premise theorems
  (`I exist`, `Mari exists`, `Mari is mortal`, `a human exists`) — chaining sound (no false conclusions).
- **Converges, no churn.** Each conclusion materialized **exactly once** → quiet; no obsessive loop.
- **No errors at any layer.** Zero API/compile failures (parser/compiler clean on every rendered NL),
  zero chaining errors, integrity intact (all premises resolvable back to source axioms).
- **The cogito re-born in-loop** — «I exist» derived by tokeniko's own act (`I think → all that think
  exist → I exist`), carrying its 2 premises.
- **Performance:** materialize ~15.6s avg/theorem (10–21s; the sync render→API-compile→POST cost);
  brain RSS **~3 GB** (the in-memory active KB — 3,235 definitions × 3,237-dim, fingerprint-cached).

### Observed → diagnosis → action
- **Empty-memory drift spin (S3 — fixed).** *Observed:* with memory empty, the wondering DRIFT driver
  logged `drift: queued 0 random` **every idle tick** (~20× in 5 min) instead of once per
  `DRIFT_INTERVAL` (60s). *Diagnosis:* the throttle keys off `brain_state.last_wondering_at`, which only
  advances in step 4 (an item is *processed*); on empty memory the `$sample` returns 0, no item is
  processed, so the timestamp never advances and `now - last >= DRIFT_INTERVAL` is always true → a
  needless `$sample` + log every tick. Harmless (no churn, converges) but wasteful + noisy. *Action:*
  **FIXED** — `wonder_one` stamps `last_wondering_at = now` whenever drift RUNS, so the throttle engages
  regardless of whether anything was queued. Verified: drift dropped to ≤1 firing / 50s.

### Open (not defects — known limits, await KB growth)
- The tiny KB (7 rules / 10 facts) converges instantly → this soak is a **robustness test + the cogito
  birth, not a knowledge explosion**. The *rich* soak (cascades, genuinely-new theorems) needs KB growth.
- Perf candidates when it matters: async materialize (un-block the idle tick); the ~3 GB resident KB.

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
- **📚 Pillar 3 — #1 abstain completion ✅ LANDED; #2 WSD canonicalization ✅ LANDED.** Diagnosis: the
  graph is FINE — the failures are **WSD sense-selection**, not missing edges (tiger compiled to
  `tiger.n.01` = *a fierce person* not `tiger.n.02` the animal; robin→`bird.n.01` but the predicate
  "bird"→`bird.n.02`). **#1 (landed):** the spine's principle generalized — a clause the graph/chainer
  did NOT decide keeps its geometric grounding ONLY if it is an AFFIRMATIVE near-exact definition match
  (`>= _GEOM_AFFIRM` in `e_statement`); a denied clause or a mid/low score → **abstain** (geometry may
  affirm, never refute or guess). "a tiger eats meat" → INSUFFICIENT (was eval:false→speakup, an active
  falsehood); the affect-gloss still grounds 1.0; keep-set + cogito intact. **#2 (landed — see the
  2026-06-25 WSD session below):** instead of fixing sense-selection in the parser (high regression
  risk), a **charitable cross-product at the grounding layer** — "subject is_a predicate" is TRUE when
  SOME sense of the subject-lemma subsumes SOME sense of the predicate-lemma. Fixes tiger + robin,
  strictly conservative (only upgrades INSUFFICIENT→TRUE on a real taxonomic path; never refutes/
  fabricates). The harder "store the contextually-right sense everywhere" stays parked.
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

## Session 2026-06-25 — Pillar 3 #2 WSD canonicalization (the substantive close of consolidation)

**Reproduced (live, raw core).** `a tiger is an animal` → INSUFFICIENT: subject WSD picked
`tiger.n.01` ("a fierce person"), whose is_a chain never reaches `animal` (person→organism). `a robin
is a bird` → INSUFFICIENT: subject `robin.n.01` is fine (its chain reaches `bird.n.01`), but the
predicate "bird" picked `bird.n.02` (*food*), and `relations_subsumes` is **exact-synset**, so
`bird.n.02 ⊉ robin`. Two different bugs (wrong subject sense; wrong predicate sense + brittle exact
match) — one root: the grounder trusts the single WSD-chosen senses.

**Fix — charitable cross-product at the GROUNDING layer (not the parser).** "subject is_a predicate"
is really "does SOME sense of the subject-lemma have SOME sense of the predicate-lemma in its is_a
chain?". A new injected `senses_of(sense)→sibling senses` reader (`evaluation_harness`,
`TKDictionaryDoc` by lemma+POS) + a cross-product fallback in `_ground_relationally` (between the
exact-subsumption and the disjointness checks): any (subj-sense × pred-sense) pair that subsumes →
TRUE, with a `subsumed (WSD-canonicalized …)` derivation. **Why the grounding layer, not parser WSD:**
zero regression risk to the keep-set's *stored* senses (the parser is untouched), and validated to fix
both. Trade-off: the stored sense stays the WSD pick; only the *verdict* is corrected (the deeper
"store the right sense" is the general-WSD problem → `parked.md`).

**Safety (the whole point).** Strictly conservative — it ONLY upgrades INSUFFICIENT→TRUE on a REAL
taxonomic path; it never refutes and never fabricates. Verified on the live KB:
`tiger`/`robin`/`bat` → TRUE; **keep-set intact** — `a cat is a mammal` TRUE (exact), `a stone is an
animal` / `a cat is a plant` FALSE (cross-kingdom refute), `a cat is a dog` **still abstains** (the
cross-product finds no path → falls through to disjoint→agree→abstain), INCONSISTENT + the cogito
(`do you exist?` → derived YES) untouched. Full pytest gate green (**38 passed / 1 xfailed**).

**Bycatch — a stale test caught by the gate.** `test_polar_false_is_no` asserted `is a cat a fish?` →
NO. That example predates the spine: cat & fish are both animals (distinct *siblings*, not a
cross-kingdom boundary), so post-spine it ABSTAINS — by the very *"distinctness is learned, not logic"*
doctrine that gives `a cat is a dog` → INSUFFICIENT. Swapped the example to `is a cat a plant?` (a real
refutation → NO) and added `test_polar_sibling_distinctness_abstains` (`is a cat a fish?` → IDK) to
lock the doctrine for the question path. Process note: the gate must be re-run when grounding changes —
this red had been sitting since `bea8b52`.

---

## Lineage — earlier manual sessions (the R-series)
- **R1** — pronoun-subject collapse (self/other questions decided by predicate geometry). → SPINE pillar 2.
- **R2** — geometric false-TRUE on distinct concepts (advice=advertisement). → SPINE.
- **R3** — definitional polar inconsistency (gloss-question YES for "advertising" but NO for "advice"):
  WSD sense misalignment between the question and the stored definition. → Pillar 3 (sense canonicalization).
- **R4** — mood markers (`??` assertion; premise-in-question swallowed). → Cleanups.

## Session 2026-07-09 (evening) — GO-LIVE: the first real Discord conversation

The DM loop went live (P1–P3). The conversation validated the whole stack; five specimens:

**S1 — delivery flags read at module import (the dry-run ghost).** *Observed:* `dry-run=True` despite
`.env` saying 0; tokeniko's first replies were logged, never sent. *Diagnosis:* `senses/main.py`
imports `outbound` BEFORE `load_dotenv()` runs; `SENSES_DELIVER_DRYRUN` was read at import time into
a module constant. *Action (landed `1de0479`):* flags read lazily at call time.

**S0-adjacent — imprint axiom extraction-INVERTED.** *Observed:* «a budget harms creature» @0.3 (+3
siblings). *Diagnosis:* the fresh ethics axiom «I do not seek advantage by harming other creatures»
lost its "by harming…" gerund adjunct (parked #2 complement family) and a fragment compiled as
"advantage harms" → generic rule "most advantages harm" → 7-hop tier chains. Meaning-INVERSION of a
trust-1.0 moral axiom — the worst direction of failure, though contained at 0.3 with full
provenance. *Action:* re-taught extractor-safe («I never harm creatures», «I do not seek unfair
advantage»), archived the inverted axiom → the harm-family cascade-revoked (the step-3 provenance
net proven live). Standing lesson: MORAL-CORE axioms must be phrased direct-object-clean until #2
lands; a create-time "complement dropped" warning would catch these at the door.

**S2 — no preparser on the live inbound.** *Observed:* «beause you think» ingested verbatim.
*Diagnosis:* the senses→/input call leaves `prepare=0` — the typo/language pipe exists but is not
wired to the live channel. *Action:* B-item 3 (roadmap).

**S2 — derived-but-unmaterialized membership.** *Observed:* «are you a mind?» → honest IDK, though
`tokeniko is_a mind.n.01` is an intermediate hop inside his own theorem chains (how «I seek
cognition» exists). *Diagnosis:* intermediate memberships derived in the fixpoint are not
materialized and the polar answerer does not re-run the chain for the claim. *Action:* candidate B+
item — either materialize load-bearing intermediates or chain-ground polar membership questions.

**S3 — the open-why, demonstrated live.** *Observed:* tokeniko asked «why is that?» about «you are
clever!»; the author answered «beause you think»; the reply was evaluated COLD (grounds as "you
think" → corroborates «I think» → silent consent) — the causal role lost. *Diagnosis:* no
conversational expectation; the author's architecture call: context is NEVER volatile state — always
DERIVABLE from the memory timeseries (recency cheap by construction). *Action:* B-items 1+2
(self-speech→memory, then the open-why derivation).

**Working observations:** silence-as-consent reads correctly in live chat; compliments→why is
charming AND epistemically right; answers thread perfectly under their questions; the raw tongue
(«I do not know», «yes», «why is that?») is stark but dignified — the nuance layer (hunch #7) can
wait; cross-channel identity (Discord-renzo ≠ kotekino to him) is now a live design thread for D.


## Session 2026-07-11 — senses C live: the channel, the ladder, the first discretion

C landed (`3e5993d`) and was live-validated the same hour in `#english` with the playbot puppets
(`scripts/playground_bots.py`, John + Hellen). Four ladder specimens — one scalar, four manners:

**L1 — ambient question → answered.** John (no addressing): «is a cat an animal?» → perceived
directedness=0.6 → `eval:question→answer` urge 0.9, effective **0.54 ≥ 0.5** → «yes», threaded
under John's message. The polite guest answers the room. FIRST channel utterance + first words to
a stranger.

**L2 — ambient contradiction → SILENCE (the first discretion specimen).** John: «the cat is dead
and alive» → 0.6 → `eval:inconsistent→speakup` urge 0.7 feas 1.0 **discarded** (effective 0.42).
He SAW the contradiction (epistemics at full strength) and held his tongue — not his conversation.

**L3 — the contrast pair.** Hellen, same sentence, addressed by NAME («tokeniko, the cat is dead
and alive») → 0.9 (the name-word detector) → effective 0.63 → **«no, that is contradictory»**,
threaded reply. Same urge, same feasibility, opposite behavior — addressing alone flipped it.

**L4 — someone else's thread → silence even for an answerable question.** Hellen replying to
John's message: «is the cat alive?» → 0.15 → answer idea (0.9/1.0) discarded at effective 0.135.
He knew the answer and minded his own business.

**S1 — raw Discord mention token broke the compile.** *Observed:* `[inbound] message from kotekino
not ingested (status=failed)` on «I agree with <@1518880846826831922>». *Diagnosis:* Discord's
mention WIRE ENCODING reached the parser as literal characters — channel encoding, not language;
decoding it is the ADAPTER's job (like the modality sniffer), not polish. *Action (landed this
session):* `lib/discord/client._decode_mentions` — `<@id>`/`<@!id>` → username from the message's
resolved mention list before content crosses the seam; unresolved ids dropped, whitespace
re-collapsed.

**Working observations:** greetings («hello Hellen», «welcome») are etiquette territory — hunch #8,
stays parked, expected to fail/noise until it lands. The playbots double as the future D cast
(distinct stakeholders for trust-ledger episodes). Momentum gap already felt in miniature: after
L3 the room reads as "his conversation" but a follow-up ambient line would still grade 0.6 —
parked entry has the timeseries derivation sketch.


## Session 2026-07-11 (later) — the teaching sequel: one axiom flips a live behavior

The second act of the playground session. Act 1 left John's «a dog is a reptile» met with an
honest «why is that?» (correct Option-A abstention — no disjointness knowledge). The author taught
ONE axiom via the trusted path («no mammal is a reptile», trust 1.0) — and it was INERT. Two gaps:

**S2 — negative copular universals were extractor-deferred ✅ FIXED (this session).** *Observed:*
the taught axiom fed nothing; `/evaluate` stayed `insufficient`. *Diagnosis:* `extract_rules`
explicitly skipped NEGATIVE bare copular noun-nouns («no machine is a human») as "disjointness —
future work"; the chainer's membership fixpoint is positive-only (routing the rule in naively would
have ADDED reptile to dog's closure). *Action:* effectively-negative bare copulars become NEGATED
MEMBERSHIP rules (positive stay edge territory); the chainer fires them in the derivation pass as
negated conclusions — never closure members; `chainGround`'s existing negation parity then refutes/
corroborates. ONE-directional (— the mirror claim «an iguana is a mammal» needs the mirror axiom);
symmetric disjointness stays future work (`parked.md`).

**S3 — runtime WSD blinded the rule: dog.n.03 ✅ WORKED AROUND / ⏭ B-ITEM NEXT SESSION.**
*Observed:* rule + machinery proven in-process with dog.n.01, yet the live claim still abstained.
*Diagnosis:* the compiled subject sense was **dog.n.03** ("informal term for a fellow") whose
ancestry never reaches mammal — the WSD frequency-prior guard did not default to dog.n.01 (why is
the OPEN B-item: Lesk had no overlap either way; the centroid leaned wrong and the prior didn't
catch it). *Action (A):* WSD-canonicalization mirrored into `chainGround` — STRICTER than the
sanctioned charitable-TRUE cross-product because refutation is the dangerous direction: sibling
subject senses are tried only when the chosen sense decides nothing, and a verdict is accepted
ONLY IF UNANIMOUS (any polarity split abstains); the evaluator's ordering guarantees the
charitable-TRUE pass already ran. *(B — next session:* investigate the frequency-prior guard's
n.03 preference — the root cause, benefits everything.)*

**The before/after specimen (the arc's point):** same speaker, same sentence, hours apart —
«tokeniko, a dog is a reptile» → Act 1: `eval:unknown → why` («why is that?») · Act 2 after ONE
taught axiom: `eval:false → speakup` («no, that is not true», threaded, urge 0.6 × 0.9 = 0.54).
Verified pure first: truth 0.0 RESOLVED with the full chain
`(WSD-canonicalized dog.n.03->dog.n.01) dog —is_a→ … —is_a→ mammal -> all mammal are NOT reptile`,
premises = the taught axiom (provenance-cascade-ready). Gate 108 passed / 1 xfailed.

**Also this session (act 1, logged above the fold):** the four ladder specimens (L1–L4), the
mention-token decode fix (S1), the wh-solver's first public values («feline», «cognition»), and
the open-why closed by a stranger's true premise (silence-as-consent, no regress).

**S3 follow-up — ROOT CAUSE FIXED same session (the copular-circularity guard).** The "confident"
centroid WAS the claim's own predicate (the only context word in a bare copular): cosine 0.832 for
dog.n.03 vs 0.717 for dog.n.01 against reptile — the guard's floor+margin passed and the prior was
overridden. Fix: the copular partner is excluded from WSD context both ways (its modifiers kept —
«the bank is a financial institution» still picks the financial bank via "financial"). The chainer's
unanimity-gated canonicalization stays as defense-in-depth for other drift.

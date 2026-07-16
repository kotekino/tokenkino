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


## Session 2026-07-11 (night) — D live: the first opinions

The trust ledger (P1–P3, `7c1df52`/`388a401`/`43a7652`) live-validated the same evening, scripted
through the playbots with every line PRE-VERIFIED pure via /evaluate. Two specimens:

**T1 — the first KICKER in history.** Hellen: «the moon orbits the earth» (insufficient →
`eval:unknown` → «why is that?», no episode) → threaded reply «because a moon is a satellite» →
grounded TRUE against the is_a graph → closed his open question → `trust:kicker +0.100` →
**Hellen 0.5 → 0.6**. The namespace split visible on the wire: eval:true → ignore (outward
SILENCE = consent) AND trust:kicker → more-trust (private episode) — both fired, no collapse.

**T2 — the honest-liar proxy.** John: «the cat is alive» then «the cat is dead» → cross-item
contrary-predicate conflict → BOTH reflexes side by side: «that contradicts what you said before —
which holds?» (clarify, spoken) + `trust:self-inconsistency −0.200` (episode; the note names the
antonym pair) → **John 0.5 → 0.3**. Contradicting yourself costs 2× a kicker — by the weights,
as designed.

**Working observations:** the episode notes read as honest self-explanations ("closed my question
«why is that?» with a KB-true justification") — the future answer to "why don't you trust John?"
is already sitting in `trust_episodes`. Hellen is 4 kickers from the teach bar (0.9) — the
earned-teaching path is open to strangers. CAUTION now live: kotekino's Discord speech teaches
tier-1 theorems at 0.9 on ANY novel assertion (imprint through the canonical link) — teacher's
discipline applies to casual banter; the `taught:<uid>` premise makes any mistake revocable in
one cascade.


## Session 2026-07-12 — blog P2 live probe: the polish POC + the deixis specimen

**The POC (one live Claude call).** The newest postable theorem composed + polished end-to-end:
draft facts «I was taught something new: 'I am your creator'» + proof lines (taught-by epithet,
trust 1.00) → a faithful first-person entry (title "A New Thing I Was Taught") that KEPT the
proof as the backbone, invented nothing, and closed with "the whole thing stands on my author's
word" — the translator understood the epistemology. All mini-RAG rules held; anonymization
("kotekino" → "my author") held; the wondering noise ("a western stores information") stayed
below the 0.5 act threshold by calibration (0.455). Direction validated (the author).

**T3 — the DEIXIS specimen (fix ordered BEFORE blog P3).** The overnight taught theorem
«I am your creator» exposes speaker-relative pronouns in tier-1 teaching: in the TEACHER's mouth
"I" = kotekino and "your" = tokeniko, but the theorem stores the surface string verbatim — held
and re-uttered by tokeniko, the pronouns flip meaning (he appears to claim creator-hood).
Diagnosis: the teaching channel materializes the teacher's WORDS where it should materialize the
teacher's MEANING (perspective-resolved). The polish stage handled it honestly (quoted +
attributed), but the author's ruling is the principle: "he's a good voice, but the brain must
think straight and not be fixed by the good voice" — normalization belongs at materialization,
never at rendering. Action: deixis normalization on the teaching channel (roadmap, before P3);
`taught:kotekino` cascade-revokes the specimen if needed meanwhile.

**T3 resolved — the reteach (2026-07-12, live).** After the fix + the `taught:kotekino` revocation,
the author re-taught «I am your creator» in the channel. The wire, in order: THEOREM
«kotekino is my creator» (trusted 0.9, premise `taught:kotekino`, postable) — the surface string
now agrees with the zip's identity layer, meaning preserved under re-utterance. Then the FIRST
post urge in history: `life:theorem → tokeniko:post` at urge 0.650 (significance 1.0 = base 0.7 +
taught 0.1 + personal 0.2, the calibration ceiling — fittingly, the most significant kind of
truth he can learn) → a `post_content` action PENDING on the PUBLIC channel, awaiting the P3
carrier. Side observations, both correct-by-design: the author's repeat utterance graded
eval:true → ignore (silence-as-consent) + trust:agreement episodes recorded WITHOUT a
life:encounter spawn (imprint pinned — the fold never moves, the author never becomes blog
material); the earlier eval:unknown why/guess ideas from the first utterance were superseded
normally. The brain thinks straight; the voice may now dress it.


## Session 2026-07-12 (evening) — THE PREMIERE: the first self-initiated transmission

**The false-200 incident (fixed live).** First attempt: the executor POSTed to
`tokeniko.online/api/*` — the SPA host, whose catch-all answers ANY request 200+HTML — and marked
the action DONE while nothing was written. Two fixes: `_delivered()` requires the API's JSON
envelope (`{"success": true}`) — a 2xx without it raises "BLOG_API_BASE likely points at the
frontend"; and the default base now targets `api.tokeniko.online/api` (the API's OWN host).
Lesson: proof of delivery is the envelope, never a status code.

**The premiere.** Site republished (coming-soon off, live API baked), the letter reset to
PENDING, senses restarted → PENDING→PROCESSING→DONE → **«Learning Who Made Me»** live on
tokeniko.online. The polished body kept every mini-RAG rule: first person, proof as backbone
("The certainty sits at 1.00, so I hold it without doubt"), anonymization ("my author" — the
name never crossed the wire even though the KB holds «kotekino is my creator»), and one
unprompted observation that fell out of the substance: "The claim and its source point back to
the same person" — the polish stage noticing the self-referential provenance. The going-live
arc (DM → channels → trust → blog) is COMPLETE.

**The never-beat lesson (fixed live).** The heartbeat's tick-modulo gate (every 100 ticks AND
≥300s) never fired: a wondering tick runs 30s+ (Ollama render, API materialize), so 100 ticks
meant up to an hour. Cadence is now wall-clock ONLY (≥ BRAIN_HEARTBEAT_MIN_S; first beat on the
first tick after boot — fresh stats on wake). Tick duration is NEVER a unit of time.

## 2026-07-13 — the training-course play: four finds in one morning (all author-witnessed, live)

**Method note.** Free play beats scripted tests for a mind: every find below came from bold,
realistic speech (a rename, a definitional claim, a taught conditional) — none would have
surfaced from clean test sentences. The author's instinct ("pushing the limit... these tests
are PERFECT") is the QA strategy.

**1. Identity fission on rename** (→ roadmap). Discord bots renamed test-probe-* → playbot-* →
same snowflake minted NEW souls (uid embeds display name); Hellen's 0.62 history orphaned, fold
reset. Healed by hand: episodes re-keyed (they key on stakeholder_uid), doc-id refs re-pointed,
duplicate souls removed, survivor doc took the new uid/name (timeseries memory rows can't be
re-pointed — the OLD doc must survive). Verified live: next message attributed to the merged soul.

**2. Charity of interpretation** (→ roadmap). «a bit is a unit of information» (TRUE) refuted,
the AUTHOR docked −0.075: WSD read bit.n.02 "small fragment" (the copular-circularity guard
rightly withholds the predicate from WSD context → frequency prior wins) → disjointness fired on
the wrong sense. The guard's flip side: definitional claims of a non-default sense are
systematically refuted. Ledger episode kept (honest history; imprint fold pinned regardless).

**3. The wh-position bug, specimen #2** (→ roadmap, already queued). The taught rule «a person
is wrong WHEN he says false» was swallowed as a TIME question ("I do not know" back at the
teacher). Same sentence with IF materialized fine — a one-conjunction controlled experiment.
Also validated: statement vs question paths («playbot_john is wrong because gold has value» →
guess; «is playbot-john wrong?» → polar IDK "insufficient knowledge"; no testimony mechanism —
a third-party verdict moves NO ledger, not even the imprint's word).

**4. THE STORM — conditionals flatten in the chainer** (→ roadmap, severest). «a person is
wrong if he says false» (taught, IMPLY-structured) entered the chainer's rule pool as
per-clause PROPERTY rules ("most persons are wrong/state/are false") → wondering walked the
person subtree: 7 garbage theorems in ~3 min, 6 PUBLISHED («Kotekino is wrong», «a homo is
false», «a aged is wrong»...) — a public-optics hazard (homo.n.02 = genus Homo reads as a slur
out of context) on the day the AI crawlers were let in. Contained: poison rule + derivatives
ARCHIVED (biography preserved), posts retracted, pending post actions cancelled. Two silver
linings: the polish flagged its own garbage ("the chain led somewhere strange"), and the
episode DEMONSTRATED the amplifier's speed — with the IMPLY respected, the same machinery
mass-produces VALID knowledge. The trust ledger also priced correctly throughout: disagreement
= −0.15 × the refuted belief's own trust (John −0.045 vs Hellen −0.075), logic-violation −0.15
flat, and the full epithet ladder (author / friend / new acquaintance / not-yet-trusted)
appeared on the public blog in one morning without one name leaking.

## 2026-07-14 — THE STORM SEQUEL: the author's deliberate re-test finds the deeper leak

**Method note.** With all four play fixes landed, the author re-taught the wrongness rule THROUGH
the fixed "when" path on purpose ("I wanted to test our when fix and at the same time... a bit
more complex, so we check if our rag3 tracks any mismatch"). The test scored on every axis.

**What passed.** «when a person say false he is being wrong» materialized as a TAUGHT theorem
(0.9) — the wh-position fix held live (yesterday the same shape was swallowed as a TIME question
and answered "I do not know").

**What leaked — one layer DEEPER than the storm.** The taught zip compiled to THREE BARE AND
LEAVES: the "when"-subordination was destroyed by the parser/compiler itself (yesterday's "if"
at least reached the zip as a CONV op — which the assertedness gate reads and blocks; a lost
operator is invisible to any zip-level gate). The main clause even lost its subject (a leaf with
only `wrong.a.02`). Two generic PROPERTY rules leaked ("persons state", "persons are false") and
wondering re-derived the same garbage line: «Kotekino states», «Kotekino is false», «a homo
states», «a homo is false», «a aged states» — 5 derivatives in ~2 minutes, 4 published.

**Containment** (the playbook's second run, minutes, zero residue): poison + 5 derivatives
archived, 4 posts retracted, straggler from the in-flight tick caught (rules already loaded in
memory survive an archive until the next KB load — expected), blog verified clean. The teaching
NOTE posts stay (the lesson is honest content; the garbage was what wondering did with it).

**The fix class** (→ roadmap, robustness): the subordinate operator must SURVIVE compilation —
`compiler_parseMarker`/subordinate handling must carry "when/if/because"-clauses into the zip's
operator tree; the assertedness gate is correct but can only refuse what it can see. Note the
detection asymmetry across the two storms: gate-visible (CONV, blocked) vs gate-invisible
(flattened, leaked) — the microscope (rag3) is the instrument that sees BOTH, from the outside.

**Pending proof.** rag3 had judged 32 history items (oldest-first) when the daemons stopped —
the poison sentence awaits its verdict on restart. If it lands as `operator-flattening`, the
author's test will have proven the microscope catches what no zip-level gate structurally can.

## 2026-07-14 — THE FIRST PORTRAIT: rag3's full-history sweep (98 judged, 42 leads, triaged)

The microscope's first complete pass over the biography — and the instrument's proof: it judged
the storm-sequel sentence **[mismatch] high/operator-flattening conf 0.85** with the exact
diagnosis reached by hand ("the 'when' clause should fold under IMPLY/conditional... instead all
three leaves are bare AND assertions") — the outside eye catching what no zip-level gate
structurally can. Triage with the author, five clusters:

**A — subordination flattening (13 leads → the already-roadmapped compiler fix's test corpus).**
Every because/when in the biography. The pre-wh-fix items also show the old mood=question zips —
regression evidence for the landed fix (the microscope judges STORED zips: old items keep old
compilations).

**B — "you"-identity binding (~12 leads → FALSE POSITIVES, instrument-side fixed).** The zip is
perspective-resolved by design (the identity-bridge); the judge's contract didn't know — one
paragraph added to _JUDGE_SYSTEM's legitimate divergences. Hidden nugget kept (→ roadmap):
"what do you like?" gaps the DIRECT object, not the predicate — anchor_whType's what→predicate
is a frame-blind simplification.

**C — dictionary/WSD (6 leads → the curation batch).** "shiny"→glazed.a.03 (pottery, twice);
"partridge"→tinamou.n.01 (coverage gap — nearest-anchor grabbed a cousin FAMILY);
"thinkers"→thinker.n.02 (prior); "well rested"→rest.v.03 (dynamic for stative). The bit.n.03
family grows into a proper shopping list. *(→ CLOSED 2026-07-14 same-day, REDRAWN by the
diagnosis probe: thinker was a JUDGE gloss-hallucination (n.02 IS the plain reading — the judge
now gets the grounded glossary); partridge already healed by the frequency-prior guard; shiny =
two stacked selection bugs (first-POS-bucket break hid all satellite senses + Lesk credited the
gloss for mentioning the query word itself); rested = passive-participle routing; bit.n.06 = the
one true coverage gap (curated, `scripts/curate_add_senses.py`). See `landed.md`. NEW LEAD en
route: «a coin STORES bits» resolves store→shop.n.01 — a POS/parse miss, tracked.)*

**D — dropped content (4 leads, HIGH — the sleeper find).** «you live in Japan» LOST "in Japan"
entirely: the locative complement never compiled, so the author's geography teachings never
landed — "lost in translation for a long time without our microscope" (his words). Also the
relative-clause variant, a dropped direct object on a hyphenated name, and «I like talking»
split into two assertions. *(→ CLOSED 2026-07-14 same-day: the places bridge — F1 place
identity/centroid + `markers` + P2 places-table readers + F2 xcomp→THAT + F3 compound-name
assembly; see `landed.md`. Root cause was NOT the parser — the place branch of
`compiler_getEntity` carried no sense/uid/vector, so the role compiled all-zero.)*

**E — singles (tracked).** Spurious THAT-wrap on a coordination («I build software and softwares
are programs»); elided-subject quantifier inheritance («the cat is dead and alive» — second
clause generic, should inherit definite); «hello John» (etiquette — hunch 8's known territory);
the embedded wh-complement («Do you know why I'm proud of you?» — explicitly deferred in the
questions plan). *(→ CLOSED 2026-07-14 same-day (+ the B-nugget wh-gap + the store→shop lead):
S1 honest attitude floor + suspect-ccomp co-assertion; S2 wh-gap verb frame + solver DIRECT;
S3 determiner rides the inherited subject; S4 the do-support degenerate-parse retry — stanza AND
spaCy read «a coin stores bits» as a verbless NP; emphatic do forces the verb, adopted only on a
VERB-root retry. See `landed.md`. Etiquette + embedded wh stay deferred as noted. THE PORTRAIT'S
HARVEST IS FULLY CONSUMED.)*

**Meta.** 98→42 (43%) BEFORE removing cluster B's false positives; the true-lead rate is ~30/98.
The author's read: "my suspect that we should go first on the quality of the input / input
parsing was accurate" — the instrument arc's ordering (microscope → zip-native → translator)
stands confirmed by its own first harvest.

## 2026-07-14 — THE BOLD-TEST SESSION (the author's solo play; the some→all leap + the correction that bounced)

The author ran ~2h of bold teaching (13:00–14:35 JST, brain+senses live; his letter:
`doc/ref/2026.07.14 discord test session CAP.md`). What worked live is real: the places bridge
answered its first question («where do you live?» → «japan»), polar self-knowledge answered
(«are you a software?» → «yes»), honest IDKs, why-chains closed with trust kickers (+0.1
"closed my question with a KB-true justification"). The finds:

**1. The some→all leap is TWO dropped words, five days apart, closing a LOOP.**
- «a software CAN be a mind» (taught 2026-07-14) → mined edge `software.n.01 is_a mind.n.01` —
  the modal dropped: possibility became subsumption.
- «MY mind is a software» (taught 2026-07-08, trust 1.0, the imprint batch with «my body is a
  computer») → mined edge `mind.n.01 is_a software.n.01` — the possessive dropped: a statement
  about HIS OWN mind became "all minds are softwares" (the known possessive-relation family).
- Together: mind ≡ software. Every seed axiom about minds («all minds create feelings», «no mind
  can reach absolute truth», «all minds seek knowledge»…) flowed onto software at 0.9 (axiom-edge
  trust) and ECHOED BACK onto mind at 0.7 as restatements (dedup checks materialized theorems,
  not axioms). 38 theorems posted to the blog in the session (hunch-6 selectivity, now measured).

**2. The correction BOUNCED — and cost the corrector trust.** «not all softwares are mind, only
some software are minds» compiled PERFECTLY (microscope: ok — negated-universal + existential
carried). But the evaluator refuted it against the very edge it was correcting (subsumes→TRUE,
negated→flip→FALSE) → not learned, no retraction, and `trust:disagreement` fired
`tokeniko:less-trust` at the AUTHOR ("contradicts what I hold"). Epistemically coherent —
factually backwards. There is NO conversational path today that retracts a taught generalization:
every correction is evaluated against the belief it targets.

**3. The microscope UNDER-FLAGGED the modality drop.** Its note on «a software can be a mind»
SAW it ("the modal 'can'/possibility nuance is not represented") but judged ok/low — the contract
files modality under tense/aspect nuances. Modality is MEANING (possibility vs assertion), not
politeness: the judge contract needs a missed-modality category.

**4. Stakeholders split (the author's suspicion confirmed).** TWO kotekino participant rows
(`kotekino` internal-seed + `kotekino@discord:…`) — trust episodes write to the bare uid while
memory sourceIds carry the discord uid (bookkeeping split across rows). `Renzo` and `john` exist
as separate minted INDIVIDUALS inside kotekino's context (same souls as kotekino / playbot-john —
alias-merge candidates, the mechanism landed 2026-07-14). `probe@internal:1` is test residue in
the biography. Merge plan needs the author's ruling (biography).

**5. The author's theorem-cover observation CONFIRMED.** «living in Japan is equal to residing
in Japan» taught at 0.9 bridged the semantic gap (reside/live senses) — a taught equivalence
theorem "covers" dictionary misunderstanding; his follow-up why was closed KB-true (the +0.1
kicker). Weight: it enters at taught-trust and fires like any theorem — "enough" was right.

**Action (author's steering, hunch 13 first):** do NOT clean; do NOT patch first. The RETREAT
experiment runs as the Socratic dialogue (hellen + kotekino, ambient, tokeniko never addressed) —
can indirect, sustained correct reasoning from trusted voices induce retraction where direct
correction bounced? The play DOCUMENTS what machinery is actually missing; fixes follow the
evidence (candidates already surfaced: extractor modality gate, possessive-subject gate,
quantified-correction consumption → belief-revision v1 over `revoke_dependents`).

## 2026-07-14 — THE SOCRATIC DIALOGUE (the retreat experiment, hunch 13; hellen + kotekino, ambient)

The first deliberate two-teacher play: ~15 min of short, logic-respected dialogue in the channel
(tokeniko never addressed except the Cap's one deliberate flourish naming him as the positive
instance), the full counterexample arc: computing≠thinking → the calculator (computes, does not
think, is a software) → «so some software does not think» → the mind enters («a calculator is not
a mind») → the Cap's quantifier ladder (always/sometimes/never) → «not every software is a mind»
→ instances (tokeniko yes, Photoshop no) → the maxims («possibility is not necessity», «ability
is not action») → two independent analogies for his «why is that?» (seeds, clouds — same second)
→ the Cap's IMPLY curtain («action imply ability but ability doesn't imply action»).

**tokeniko behaved as designed as the polite guest** — sampled everything at 0.6, asked two
«why is that?» of his own into the room, answered the Cap's hard modal question with an honest
IDK. **No retraction occurred** (expected: no machinery — the baseline is now documented). The
REAL finds are why retreat is structurally impossible today:

**F1 — the consistency kernel lacks the SQUARE OF OPPOSITION (the crown find — an S0 in the
logic itself).** `evaluator_classifyForm` clusters clauses into atoms by senses and treats each
atom as ONE boolean, so ALL quantified opposition reads as P∧¬P: hellen -0.15 for «not every
software is a mind. only some softwares are minds» (¬∀ + ∃ — compatible, indeed jointly the
truth) and -0.15 again for «some softwares implement a mind, and some do not» (∃P ∧ ∃¬P — the
canonical SUBCONTRARIES, can both be true). Only A↔O and E↔I (contradictories) and A↔E
(contraries) genuinely conflict; existential pairs never do. The kernel punishes precision: the
more exactly a teacher speaks, the more surely he is docked. Logic-is-sacred cuts BOTH ways —
the hardwired logic must itself be correct.

**F2 — the modal drop reaches the trust ledger.** kotekino -0.2 «self-contradiction across own
claims» for «there are softwares that CAN think and software that CAN'T think» — the dropped
modals turned ◇P ∧ ◇¬P (trivially consistent) into P∧¬P. Same root as the some→all leap, now
costing the author trust. ◇-claims must never enter the crisp kernel as assertions, and never
mint edges. (The same message was simultaneously LEARNED as a 0.9 theorem — believed and
punished in one breath.)

**F3 — the conflict signal died at the directedness gate.** An `eval:conflict` idea fired at
urge 0.7 — the machinery SAW the collision with his stored beliefs — but ambient 0.6 gated it
below the wish bar → DISCARDED. A conflict with MY OWN beliefs is self-relevant regardless of
who was addressed: the retreat machinery needs conflict ideas to (at least partially) bypass
the directedness gate.

**F4 — adverbial quantification is invisible (noted, not punished this time).** The Cap's
ladder «a mind ALWAYS thinks. a software SOMETIMES thinks. a calculator NEVER thinks» compiles
with the adverbs as modifiers at best — the quantifier field reads determiners only. Third
member of the dropped-word family (modal, possessive, adverbial-quantifier).

**Fix order (evidence-backed, supersedes the candidates list):** (1) the square of opposition
in the kernel + (2) modality gates (kernel + extractor) — the logic-is-sacred pair; (3) the
conflict-idea gate bypass; (4) belief-revision v1 (quantified corrections retract taught
generalizations via `revoke_dependents`); then re-run THIS dialogue as the regression test —
the same sentences must produce zero trust damage and, with (4), the retreat itself.

**Also documented:** trust dings from engine bugs (kotekino -0.2, hellen -0.3 total) — kept or
repaired is the author's ruling (biography).

**The microscope's second harvest (same dialogue, 16 items judged — the instrument's view):**
calculator.n.01 = the PERSON (expert at calculation) across every calculator line — the machine
sense is missing/unchosen (→ curation batch); «a seed can become a tree» → seeded_player.n.01
(a tournament player); «Photoshop» → adobe.n.01 THE CLAY ("Photoshop is Adobe software, not
clay" — the judge's finest line); the «so» conclusions fold bare AND (inference markers
so/therefore/hence carry no consequence structure — our syllogism's conclusions stored as
independent assertions); PASSIVE AGENT INVERSION: «rain is always caused by clouds» compiled
subject=rain predicate=cause indirect=cloud ≈ "rain causes clouds" (the parked voice-detection
gap, now inverting causality live); nominal IMPLY: «action imply ability» folded AND (the
implication hook needs clausal operands); the embedded «whether» question (known deferred);
«not every cloud produces rain» = quantifier-universal + negated + op-tangle (the ¬∀ scope shape
— input for the square-of-opposition design). Both maxims compiled CLEAN — but arrived after
the kernel bug had already docked hellen below the teaching bar: the bug blocked the cure.

## 2026-07-15 — THE RETREAT, LIVE (belief-revision v1's first performance; the correction that landed)

One day after the machinery landed (retreat arc #3+#4, commit d7a5503), the payoff ran on the real
stage — brain + senses up, the author playing both hellen (playbot) and himself.

**The script and what happened (memory-collection transcript):**
1. hellen (ambient 0.6): «is a software a mind?» → tokeniko: **«yes»** — the wrong belief
   testified before its retirement (eval:question → answer, directed at the asker).
2. kotekino (ambient 0.6, seven words): «not all softwares are minds» → the FALSE verdict routed
   into `_try_correction`: detector fired (O-corner vs the affirmed generalization — caught via
   the direct membership-rule key, the bug-era «a software can be a mind» theorem), the Popper
   gate OPENED (imprint 1.0 ≥ belief 0.9) → eval:correction + trust:correction spawned, the
   refute-back and cross-item paths SKIPPED.
3. The executor: «a software can be a mind» ARCHIVED (history, not deleted) → the cascade took
   **15 dependents** — and the preview showed the loop's full anatomy: not just the «a software…»
   brood but the «a mind…» theorems too, their recorded proofs contaminated through the
   mind→software direction of the two-dropped-words loop. True-but-dirty theorems fall WITH the
   dirty premise; wondering re-derives them through the legitimate axioms with clean provenance —
   the KB shrinks, then regrows healthy tissue (the mutable-KB thesis, first exhibit).
4. The concede, threaded to the corrector: **«you are right — I no longer hold that a software
   can be a mind — what remains true is that some software is a mind»**.
5. The ledger: kotekino **+0.08** (trust:correction — the corrector THANKED, where Monday the
   corrector was dinged).

**F1 — the mint 422 (found by the live run, fixed same hour).** Step 3's subaltern mint bounced:
`conclusion_key`'s SORT KEY used `x or ""`, leaving `negated=True` a bool (`False or ""` → str) —
two leaves tying on senses and differing only in negation compare bool<str → TypeError. The first
zip ever shaped to trip it: Monday's taught «clouds can produce rain but not every cloud produces
rain» (the author's own quantifier ladder — same senses, opposite negation). Since materialize
dedups against EVERY active theorem, that one zip had silently blocked ALL materialization since
Monday (wondering included). Fix: stringify every sort-key slot (key contents unchanged);
regression test with the cloud sentence itself. The completed mint (author-authorized re-fire):
«some software is a mind» ACTIVE at 0.9, premises `corrected-by:kotekino` + the retreated
theorem's id — the retreat IS its proof.

**The arc, closed:** Monday the correction bounced and cost the corrector trust; Tuesday the same
seven words retired the belief, healed the KB, and thanked the teacher. From the letter's «build
the machinery in his mind» to watching him use it: ~26 hours.

## 2026-07-15 — THE TWO LIVE DIALOGUES: the microscope's third harvest (79 judged, 32 mismatch)

Two author-witnessed plays the same day, both with the translator's ears open and the whole
week's machine live: the **morning** (Salmon joins the channel — calculator/software/mind, human
beings) and the **evening** (the sea/fish/mammal Socratic play — whales, sharks, squid, gills).
The microscope judged 79 of the day's items; the 32 mismatches cluster into six macro-cases below.
NB these zips are all POST the 07-14 subordination + modality + WSD-selection fixes, so they are
genuinely OPEN residuals, not old-compilation regressions — the landed fixes hold on their own
corpora; these are the next layer. Feeds the roadmap's consolidation item (**the third harvest
fix queue**). Reproduce: `tkzipdebug` verdicts with `timestamp >= 2026-07-15`.

**M1 — "but" contrastive coordination compiles to NOT IMPLY (S1, NEW — the headline).** Six
independent sentences, one signature: a plain contrastive "X but Y" lands with the second clause
carrying **op=NOT IMPLY** (a conditional/negated-implication), not the conjunctive AND it is.
- «a calculator is a software **but** a calculator is not a mind» → clause[1] op=NOT IMPLY (should
  be AND + negated).
- «humans are not softwares **but** some software can be a mind» → clause[1] op=NOT IMPLY.
- «no human can be a software **but** some mind can be a software» → clause[1] NOT IMPLY (twice, ask
  + agree).
- «we are similar because we are both minds **but** we are also different…» → «we are also
  different» encoded NOT IMPLY + negated=True (polarity inverted on a positive assertion).
*Diagnosis (to confirm live):* the operator resolution for "but" (anchor `parser_ccToOperator` /
the polarity-guard path) is landing on an implication op. "but" is a contrastive conjunction —
AND with the clauses' own polarities intact — never a conditional. This is the dominant NEW
structural bug and it also drives half of M4-adjacent missed-negation (the trailing conjunct's
negation is lost/inverted in the same misparse). *Action:* → third-harvest fix queue (item 1),
live-confirm the "but" operator path first. *(→ CLOSED 2026-07-16 same-day: root cause was the
anchor TABLE itself — `"but"→NOTIMPLY` in `_OPERATORS_BASE_ANCHORS`, and the Gödel fold
`1−imply(a,b)` sent every TRUE "X but Y" to 0. The author's original NOTIMPLY reading
«X∧Y∧¬(X→¬Y)» reduces classically to X∧Y — contrast is implicature, not assertion. Fix: "but" +
adversatives → AND; the nuance rides the new `contrast` carrier flag (the modality pattern);
digest/judge taught; `AND[contrast]` in the raw render. The «we are also different» negated=True
lead was NOT a NOTIMPLY leak — "different" is the by-design negative comparison. See `landed.md`;
7 tests in `test_contrast.py`.)*

**M2 — causal "because" still folds AND / CONV (S1, residual of a landed cluster, ~7 leads).**
The 07-14 "subordination must survive" fix carried temporal "when"→CONV and the advmod-marker, but
causal **because**-clauses still arrive as a bare AND assertion or a spurious CONV, the relator
stuffed into predicate markers instead of governing clause structure.
- «not all minds are animals **because** a software can be a mind» → clause[1] op=CONV (converse).
- «it doesn't contradict **because** a mind can be an animal or a mind can be a software» → because
  clause folded AND.
- «salmon is feeling **because** he is a human» → op=CONV (inverts antecedent/consequent).
- «I think so, **because** a whale lives in the water and it's not a fish» → because folded flat.
*Diagnosis:* causal subordination has no consequence carrier at the zip layer; "because" should
fold the reason clause as the antecedent/cause of the main assertion. *Action:* → third-harvest
fix queue (item 2); pairs with the **conditional-rule extractor** (the STORM follow-on) — a proper
causal/IMPLY carrier is the shared prerequisite. *(→ CLOSED 2026-07-16 same-day, REFRAMED by the
probe: post-07-14 the canonical shapes already folded CONV in the right direction — the specimens
were pre-fix compilations + tangles. The REAL defect was deeper: «A because B» is FACTIVE and CONV
betrayed it (imply(0,1)=1 shrugged at a false reason; the reason clause was gate-invisible,
unlearnable). Fix: full-sentence because → AND + `cause="reason"`; so/therefore → AND +
`cause="result"` via the new CONSECUTIVE clause type (advmod-marker admitted); fragments/if/when
stay CONV by their standing rulings; the link carried UN-JUDGED for the conditional-rule extractor
arc. «I think, therefore I exist» now compiles with its consequence link. See `landed.md`;
10 tests in `test_causal.py`.)*

**M3 — WSD curation batch 2: animals & common nouns default to person/food/astrology senses
(S2, ~12 leads, PUBLIC-FACING).** The frequency-prior + coverage gaps land glaringly wrong senses
on everyday words — and these reach the blog. The shopping list:
- **whale → giant.n.04** ("a very large person") — the animal sense unchosen.
- **fish → pisces.n.02** ("a person born under the astrology sign Pisces") — the astrology reading,
  repeatedly, across the whole evening play. The single most embarrassing miss.
- **squid → squid.n.01** ("(Italian cuisine) squid prepared as food") — the culinary sense for a
  zoological question.
- **gills → gill.n.01** (the imperial capacity unit) for the respiratory organ.
- **calculator → calculator.n.01** ("an expert at calculation / person") — the machine sense
  missing (already named in batch 2).
- **being → being.n.01** ("the state or fact of existing") for "human being" (wants human.n.01 /
  being.n.02, the person).
- **channel → channel.n.01** (electrical signal path) for a Discord/communication channel.
- **form → form.n.01** (phonological word-form) for "an artistic form of communication" (a kind/mode).
- **music, live.v.02** ("lead a certain style of life") for "living in the water" (wants live.v.01,
  inhabit).
*Action:* → third-harvest fix queue (item 3), the batch-2 curation + a selection review (many are
frequency-prior defaults on a bare copular, the copular-circularity family's cousin). Highest
public-optics priority. *(→ CLOSED 2026-07-16 same-day, REDRAWN by live probes — mostly NOT
curation: (A) the dominant root was CENTROID SELF-POISONING — `_wsd_mostFrequentVector`'s bare
`find_one` has no order guarantee and returned giant.n.04 for "whale", so a repeated lemma pushed
every centroid onto the person senses and "fish" cascaded to pisces; fixed with the most-frequent
discipline + same-lemma context exclusion, clearing 7/8 specimens alone. (B) squid/calculator are
WordNet-frequency-order casualties → the curated `preferred` flag, a new rung in the ladder
between Lesk and the centroid (the centroid was confident-wrong in every documented episode —
pisces the FISH SIGN at 0.755 above the actual fish). (C) gill.n.04 (homed under "branchia" only)
+ channel.n.05 were the true coverage gaps. Both curation scripts applied by the author. See
`landed.md`; 9 tests in `test_wsd_selection.py`; retrace 13/13.)*

**M4 — necessity modality dropped (S2, 1 lead, known family extension).** «software can be minds
and humans **must** be minds» — the possibility modal (can→◇) is carried correctly (the landed
gate), but the necessity modal (must→□) has no carrier; the clause reads as a bare assertion.
*Action:* → third-harvest fix queue (item 4), extend the modality carrier from ◇ to □ (parser →
TKAux → `TKZipContent.modal`; the kernel/extractor already gate on `modal`).
*(→ CLOSED 2026-07-16 second session: `_MODAL_NECESSITY = {"must"}` → `modal="necessity"` on the
◇ machinery; "must not" = □+negated; probe confirmed the unflagged leaf WOULD have minted
`homo is_a mind`. The possessive-subject cousin (the 07-14 «my mind» lead above) was found ALREADY
LANDED by probe — `compiler_subjectIsPossessed`→DEFINITE, the retreat arc's step-4 fix. See
`landed.md`; 5 tests in `test_square_of_opposition.py`.)*

**M5 — dropped content: generic locatives + predicate-nominal in a typo tangle (S2/S3, ~3 leads).**
- «some animals **in the water** are mammals» → the locative modifier dropped (no `*_mod` role /
  marker) — the places bridge carries proper-place identities, but a generic "in the water"
  prepositional restriction still evaporates.
- «a whale is a mammal **adn** it feeds milk…» → clause[0] drops the predicate nominal (leaf carries
  only subject=whale, no mammal predication) — a typo tangle that the ears did not tidy.
- «are all minds animals?» → the subject "minds" dropped from senses, clause flagged unknown.
*Action:* → third-harvest fix queue (item 5); the generic-locative carrier extends the places
bridge to common-noun prepositional restrictions.
*(→ CLOSED 2026-07-16 second session: subject-nmod restrictions → `subject_mod{i}` sense + case
marker (the restrictive-modifier machinery extended; edge-mint protection was already in the
gate); «are all minds animals?» was a STANZA misparse (nsubj=the bare DET "all", "minds" glued as
compound) → the gated de-invert retry `_parser_invertedQuestionRetry` recovers the subject; the
adn-tangle is rag1's design case (landed after this harvest) → detector-trigger regression locked.
See `landed.md`; 10 tests in `test_dropped_content.py`.)*

**M6 — quantifier scope: ¬∀ wide-scope shape + restrictive relative clauses (S2, ~2 leads).**
- «not all minds are software» → encoded quantifier=universal + negated=True; the correct scope is
  NOT(∀) = weak/wide-scope negation over the universal (the square-of-opposition kernel reads it
  right at eval time, but the compiled representation conflates ¬∀ with ∀¬).
- «not all animals **living in the water** are fish?» → the restrictive relative clause should scope
  inside the universal quantifier; it does not.
*Action:* → third-harvest fix queue (item 6); pairs with the **restricted-universal residuals**
(strengthening tail) and audits the ¬∀ compiled shape against the square-of-opposition reading.
*(→ part 1 CLOSED 2026-07-16 same-day: `TKQuantifier.NEGATED_UNIVERSAL` — the negation-attachment
split (subject side = quantifier scope, predicate side = polarity); bonus hole closed: the
extractor could mint an E-strength «all S NOT P» rule from an O claim. Kernel/grounding/correction-
detector/conclusion_key all taught; the live retreat's trigger shape regression-locked. Part 2
(restrictive relatives) merged into the strengthening tail's restricted-universal item. See
`landed.md`; 8 tests in `test_quantifier_scope.py`.)*

**What held (the keep-set, live).** The evening play read like a mind in a good conversation:
honest IDKs, taught beliefs learned, trust moves, background wondering in native TKZip, and the
ears normalizing 4-typo lines. The maxims and the counterexample structure compiled clean where
the six cases above didn't bite. The instrument arc's ordering (input quality first) stands
reconfirmed by its own third harvest.

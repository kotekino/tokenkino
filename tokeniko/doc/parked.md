# tokeniko — parked (the icebox)

> Deliberately deferred — good ideas and known gaps that are **not** the current focus. Moved out of
> `roadmap.md` so the road ahead stays clean. Promote an item back to `roadmap.md` Next when its time
> comes. The active road is `roadmap.md`; history is `landed.md`.

---

**Conversation momentum (senses C follow-on)** — after tokeniko speaks in a channel he is IN the
conversation for a while, so the next ambient messages there deserve more than 0.6 (the author's
instinct: a multiplier lifting polite-guest toward engaged-participant ~0.75). The clean design is
already agreed: DERIVE it from the memory timeseries (his own recent self-speech in that
`channel_id` within a window), never stored state — the same principle as the open-why derivation.
Parked to watch plain C live first; promote when the missing lift is actually felt.

**ATProto / Bluesky — a `senses` I/O channel (inbound carrier AND outbound)** — the account exists
(**@tokeniko.online**; app password to come) so wiring is quick later. Its original condition
(Discord + blog live) was met 2026-07-12, but the author RE-parked it at the 2026-07-14
reconciliation: "before ADDING another sense (with huge consequences, I'm sure of it) let's make
the brain stronger" — promote only after the roadmap's strengthening tail. Today: no send adapter;
`score_feasibility` already marks atproto-outward infeasible.

**Wondering-net structural polish (definitions-as-rules, step-4 residual)** — the ingestion extractor
gate is already conservative (main-clause genus only + redundancy/placeholder/cycle/reliable-tier
disjointness), so these were deferred: reject **circular nominalization** genera ("management→manage"),
and **flag-the-middle** (surface borderline extracted edges for review rather than silently accept).
Promote only if the enriched soak shows them biting.

**Sufficiency v1 residuals (Brain v1.1 step 4)** — conservative firsts, promote if the enriched soak
shows them worth it: (1) **derived properties as cond satisfiers** — sufficient rules currently match
the seed's stored property FACTS only; letting chainer-derived properties satisfy definiens conjuncts
(recognition over inferred traits) needs the fixpoint interleaved with property derivation. (2)
**adjective-definienda sufficiency** ("has merit → valuable" — the finding-#3 flagship) has NO fuel:
all glosses were "a/an X is …" noun-templated, so adjective definienda compile as noun-STRUCTURED
zips (the step-5.1 pin now labels their subjects with the true `.s.`/`.a.` sense, but the clause
shape stays noun-copular); needs per-POS gloss re-templating first. (3) **class-seed recognition** — sufficient rules fire only
on individuals (property facts are uid-keyed); a class satisfying a definiens via its own differentia
rules is a further unification.

**Differentia-rule VERB recovery (definitions-as-rules, step-5 residual)** — the strict differentia
gate (step 5.1) keeps only reliably-clean rules zip-only: adjective differentia ("all apples sweet") +
transitive verbs WITH a direct object ("all bathrooms contain a bathtub"). It conservatively DROPS the
verbs it can't disambiguate from the zip alone — **passive-voice reduced relatives** ("an airfield
**equipped** with…" → the class is the patient, not "airport equips") and **intransitive agentive
verbs** ("trained **to compete**"). Separating these needs **parser-level voice/agency detection** (the
reduced-participle vs finite-relative-with-nsubj distinction), adjacent to the parked D3a
subject-rebinding work. Would recover the verb bulk (~300 candidates) as clean differentia rules and
substantially grow the enriched-soak fuel. Promote when the parser voice signal is built.

**Performance (optimize-later)** — the fingerprint KB cache (`_kb_cache`) landed, but every
materialized theorem changes the fingerprint → the next tick still pays a FULL reload (3233
definition zips, tens of seconds) — an incremental/delta reload would cut soak tick cost ~10x.
Dual `en_core_web_lg` load (`parser.nlp` + `c_state.nlp`) → consolidate. *(TKZip binary
compaction was promoted OUT of here 2026-07-14 — roadmap strengthening-tail #1, author's call.)*

**WSD (deeper refinements)** — contextual WSD for ambiguous heads; co-predication hint (prefer
attribute-sharing adjective senses); graded attribute-contrariety (no crisp `antonym` edge).
*(The robin xfail formerly noted here HEALED 2026-07-14 — the Lesk self-mention fix; promoted to
a permanent regression test. The core selection fixes are in `landed.md`.)*

**Parser / Stanza** — concessive + resultative clause types (`although`→OTHER, `so`→AND today); D3a
relative-clause matrix subject (Stanza mis-root); `imply`→IMPLY parataxis robustness; clausal-subject
support ("to err is human"); negative-quantifier subject rewrite ("nobody").
- *(Property-restricted universal rules / cogito fork ii — un-parked and since **LANDED** with
  Brain v1.1 (the property-conditioned rule extractor in `kb_extract` — see `landed.md`).)*

**Evaluator** — geometric negation-awareness in `compareContent`; quantifier effect on the *geometric*
grounding; axiom/theorem `≡1` tautology creation guard; intrinsic comparison grounding (eq/noteq);
trust-weighted grounding + conflict arbitration; defeasibility of biological universals (crisp `all`
over-asserts — penguins don't fly).

**Cleanup / misc** — 1b **verbs** (the "means"-frame drags a spurious predicate); legacy `axioms` /
`names` collection cleanup; `@-1,0,0` spacetime artifact; t-norm / implication choice (Gödel vs
Łukasiewicz vs product — the one semi-arbitrary constant); coreference (pronoun → individual).

**Dev tooling** — `probe_brain.py` (live brain-loop integration probe: injects a multi-author batch
via `/input`, asserts the loop invariants) currently lives in the scratch dir — candidate to formalize
into `scripts/` or `tests/`.

**Dreaming (a hunch — future, biological-creature framing)** — a new brain **phase**: access RANDOM
memories and *distort / mix / shuffle* them (a blender over the memory log) into a new **`dreams`**
collection that mirrors the `memory` modeling (also a timeseries). During the dream phase **`senses`
is paused and the other brain loops are paused — only the dream loop runs**. Use is TBD (a hunch —
likely creativity / consolidation / novel-association later). Revisit after the logical brain (D) is
whole. See `VISION.md`.

**Plural-genus collection/member gate (enriched-soak specimen, 2026-07-09)** — "a forest is the
TREES and other plants in a large densely wooded area" minted tier edge `forest.n.01 is_a tree.n.01`
→ «a forest has trunk» @0.3. A PLURAL genus head ("the trees") defines a collection by its members —
that is collection-of/member-of, never is_a. Gate improvement for `extract_isa_edges`: reject (or
re-type) a plural-headed genus. Companion specimen: differentia OBJECT mis-sense («a sector
illustrates fabric» — "textual material" got the textile sense); the object-side WSD shares the
general differentia-WSD residual above.

**Symmetric disjointness (the mirror direction, 2026-07-11 follow-on)** — a negative copular
universal is consumed ONE-directionally (as a negated membership rule): «no mammal is a reptile»
refutes «a dog is a reptile» (subject-side closure walk) but NOT «an iguana is a mammal» — the
mirror claim needs the mirror axiom taught. True symmetric consumption = mine these into
pairwise-disjoint assertions feeding `relations_disjoint` (the refutation side of the graph reader,
symmetric to how affirmative copulars feed subsumption) instead of a rule. Promote when the
teaching workflow makes the double-teach feel like friction. *(Supersedes the step-2
`negated_skip` residual — the rule-side consumption landed 2026-07-11.)*

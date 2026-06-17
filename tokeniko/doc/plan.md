# tokeniko — overarching plan (the logical brain)

> The phased path from today's evaluator to the inconsistency/inference engine. The *why* is
> `VISION.md`; the *design + verified findings* are `doc/reasoning-engine-brainstorm.md`; the concise
> per-item status is the `CLAUDE.md` roadmap. Order is driven by dependencies, not ambition: each
> phase unblocks the next. The volitional/affective layer stays last, by design.

## Already landed (foundation)

Compilation pipeline (sentence → `TKZip`); three memory tiers + REST (definitions/axioms/theorems) +
stakeholders/memory; fuzzy `[0,1]` operators + `operator_truth`; evaluation = ground vs definitions →
**fold clause truths through the operator tree** → geometric axiom/theorem match → `EvaluatorResult`,
behind `POST /api/v1/evaluate`; order-aware directional operators; the antonym **column-read** primitive
(verified). The geometry/algebra split is settled: **geometry = matching, algebra = inference, logic =
hardwired first axiom, knowledge + behavior = memory.**

---

## Phase 0 — Parser / compiler review & hardening  ✅ DONE *(prerequisite for everything)*

> **Landed** (merged to main): D1 negation as a discrete `TKZipContent.negated` flag (set by the
> compiler from not/no/never/negative-quantifier markers, applied in `evaluator_groundContent` →
> `truth → 1−truth`; verified end-to-end — "I do not think" evaluates false via `/evaluate`); D2
> comparison polarity via the `utils_antonyms` column-read primitive ("different"→negated, "same/equal"
> →affirmative); D3b noun-complement infinitive binding ("ability to roar" → "cat roar"); plus the
> `util_normalizeGloss` helper. **Deferred to a later parser-level pass:** D3a relative-clause matrix
> subject ("the man who loves Mary runs") and purpose-infinitive binding ("...to fly" → "airport fly")
> — both originate in the Stanza parse / `parser.py` root+nsubj selection. Full write-up:
> `doc/parser-compiler-review.md`. The items below are the original spec, kept for reference.

A focused review session on the quirks the brainstorm tests exposed. Goal: make a compiled clause a
**faithful, reasoning-ready** unit. Prioritised by downstream need:

1. **Negation representation (linchpin).** Today negation is inconsistent — "do not jump" is absorbed
   into the clause vector (no `NOT` op); "no ability" becomes a `[no]` property. Decide and implement a
   **single recoverable representation** (a polarity flag on `TKZipContent`, and/or a `NOT` op the fold
   already handles) so the evaluator can read negation. Without this, `noteq = 1−eq` and "lacks/no…"
   can't drive inconsistency.
2. **Comparison / identity relations.** `EQ`/`NOTEQ` exist in the operator enum but the compiler never
   emits them; "is/equal/different" compile as predicate words. Decide: map copular/comparison clauses
   to `EQ`/`NOTEQ` **operators with intrinsic grounding** (`compare(operands)` / `1−compare`), so the
   eq/noteq algebra fires. (Pairs with the antonym primitive for the "different" case.)
3. **Subject re-binding in clause splitting.** Relative clauses / infinitives must bind their subject
   to the **headword** (carnivore→"feeds on flesh", not "animal"; "no ability **to roar**" must not
   become `fur roar`). This is the crux that makes gloss → atomic-fact decomposition (Phase 1) reliable.
4. **Fragment / gloss normalization.** Bare genus-differentia fragments mangle; normalize to
   `"a ⟨word⟩ is ⟨gloss⟩"` before compiling (a Phase-1 ingestion step, but validated here).
5. **Minor:** spacetime display artifacts in `decompiler_raw` (`@-1,0,0`); confirm POS-pruning runs
   before any sense scoring.

**Deliverable:** a short review doc of confirmed quirks + fixes, and the negation/comparison
representation decided and implemented (with the fold/validity code aware of it).
**Verify:** re-run the brainstorm probes (`a cat is a feline mammal`, the carnivore relative clause,
the negation cases) and confirm clean, recoverable structure.

## Phase 1 — Knowledge bootstrap (the inference substrate)

Seed memory from WordNet so the inference engine has edges to chain over. Two complementary harvesters
(see brainstorm "Knowledge bootstrap"):

- **1a — Structured relations → atomic triples (no NL). ✅ DONE.** `scripts/relations.py` harvested
  **150,529** sense-scoped triples (`is_a`, `part_of`, `antonym`, `entails`, `attribute`, `similar_to`)
  over all 117,659 WordNet synsets into the `relations` collection (app KB `:27018`). Direct edges
  only; transitive closure (is_a chains, branch-disjointness) computed at query time. Verified:
  `cat → … → animal` vs `lettuce → … → plant` diverge under `organism` (disjointness derivable). The
  reliable taxonomic skeleton, parser-free.
- **1b — Glosses → atomic property facts. ✅ NOUNS DONE / verbs+adj deferred.** `scripts/glosses.py`
  (strict/academic: function-word + informal filtered, gloss-cleaned, POS-framed, routed by clause
  count) ingested **~928 definitions + ~1,140 axioms** from the base-word **noun** senses (7 edge-case
  compiler errors skipped, ~0.34%). **Verbs/adjectives deferred:** the "to X is to …" / "X means …"
  frames drop the headword — gated on the parser's infinitive-subject binding (the deferred D3a class;
  also test kotekino's quotes-around-the-headword hunch there). Neighborhood expansion still pending.
- **Routing** 1-clause → `definitions`, multi-clause → `axioms`; preserve negative atoms.
- **The KB is re-compilable.** Every stored item keeps its `original` sentence, so any future
  parser/compiler change just re-runs parse+compile over the stored originals — **no NLTK/WordNet, very
  fast**. Worth a small `recompile` utility (read `original` → recompile → update `zip`/`content`/`raw`)
  when the parser next changes materially.

**Verify:** the cat/lettuce chain exists in memory (`cat is-a animal`, `lettuce is-a plant`,
`carnivore eats flesh`), deduped; `/evaluate` grounds far more, fewer spurious INSUFFICIENTs.

## Phase 2 — Word-sense disambiguation (use-time accuracy)

Upgrade sense selection from "POS + most-frequent" to **POS-prune → context-centroid (sense family) →
gloss/Lesk overlap (break near-ties) → ask on low margin**. Joint/iterative if needed (context words
are themselves ambiguous: bootstrap with frequency sense, then refine). Reuses the existing cosine /
matching machinery.
**Verify:** the validated cases — animal-context → `cat.n.01`, person-context → `guy.n.01`; a genuine
tie raises `[eval:ambiguous]` rather than guessing.

## Phase 3 — Reasoning engine: intra-statement kernel  *(slice of roadmap #1)*

The self-contained validity / self-contradiction check on the input's own folded form, no KB chaining:
`X ∧ ¬X`, `X → ¬X`, `eq/noteq` over shared operands. Add the **validity check** (an axiom/theorem must
fold to `≡ 1` over all operand assignments — `min == 1`), produce `status = INCONSISTENT` +
`EvaluatorResult.inconsistency` (the offending form), and use the **antonym primitive** as the negation
signal alongside `noteq = 1−eq`.
**Verify:** `a eq b imply a noteq b` → INCONSISTENT / rejected as an axiom; consistent forms unaffected.

## Phase 4 — Reasoning engine: inter-statement inference  *(the rest of #1)*

The full engine: **soft-unification** (similarity + Phase-2 WSD + memory coreference) joins input
clauses to KB facts; **forward-chaining** propagates truth through the operator algebra over the
bootstrapped graph; output the **minimal premise + identification set** (unsat-core) so a verdict is
locatable (logical inconsistency vs divergent knowledge). Branch-disjointness heuristic for plant/animal.
Handle **quantifiers** ("all", "only") and chaining **termination / cycles**.
**Verify:** the cat/lettuce contradiction is derived, with its premise+identification chain reported;
agnostic-and-ask fires only for genuinely un-connected input.

## Phase 5 — Reflective behavior layer  *(later; the seam to the volitional brain)*

Behavior as memory rules over reserved tokens (`[eval:inconsistent] IMPLY [tokeniko:speakup]`,
`[eval:unknown] IMPLY [tokeniko:ask]`): `imperative`-modality activation, a hardwired action-dispatch +
**allowlist**, conflict resolution, and the `brain` perceive → evaluate → act loop. This is where the
emotive/intuitive layer plugs in — only after the logical brain (Phases 0–4) is whole.

**The unknown → ask → learn loop (the KB becomes living).** Unknown lemmas are inevitable forever, so
the honest state is neutral, not a guess — `TKZipContent.unknown` → grounding `0.5` → `INSUFFICIENT`
("unknown vocabulary"), already in place (`e_truth`/`e_statement`). The reflective rule
`[eval:unknown] IMPLY [tokeniko:ask]` then asks a source for the meaning, compiles the answer into a
statement, and **stores it at that source's trust level** — the existing `trusted` field is the
gradient: bulk WordNet ingest = `trusted=1.0` ("school"), a user-taught meaning = lower ("life
experience"). So the KB grows through interaction, not just ingestion (cf. `TKGeneric`'s own comment:
"get the definition and replace it with a statement, so tokeniko learns"). Follow-ons: **trust-weighted
grounding** (a `1.0` definition decides more than a user-taught one) and **conflict arbitration** when
a low-trust learned meaning clashes with a trusted one (trust + recency).

---

## Parked / cross-cutting

- **Individual-entity identity (roadmap #2 remainder).** Named individuals (Mari ≠ Luca, "my cat" as a
  specific entity) are geometrically identical today → limits the *matching* layer's individual
  coreference in Phase 4. Concept/type matching and antonymy already work; individuation is the open
  piece (distinct vectors / entity tracking in memory).
- **`axioms` collection cleanup.** The current `axioms` predate the three-tier model; reconcile after
  the engine stabilises (Phase 1 will largely repopulate it anyway).
- **Physics constants.** The t-norm / implication choice (Gödel vs Łukasiewicz vs product) is the only
  semi-arbitrary modeling knob — revisit if folded truths feel wrong.

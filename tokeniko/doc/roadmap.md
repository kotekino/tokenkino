# tokeniko — roadmap (single source of truth)

> One ordered place for *what's done, what's in flight, what's next*. The **why** is `VISION.md`;
> the **how/design detail** lives in the reference docs (see the map at the bottom). When status and
> any other doc disagree, **this file wins** — update it as items land.

Legend: ✅ done · 🔄 in progress · 🔭 next · ⏸️ deferred/parked

---

## ✅ Landed (foundation → recent)

1. **Compilation pipeline** — sentence → `TKLLC` + `TKZip` (parser → compiler → decompiler).
2. **Memory model + API** — three epistemic tiers (definitions / axioms / theorems) + stakeholders +
   memory log, all as REST resources behind `*Service`s; `POST /api/v1/evaluate`.
3. **Evaluator foundations** — geometric comparison (`evaluator_compareContent/Item/Zip`), behavioral
   operator similarity, type-routed indirects (marker gate), word-assignment (`evaluator_assignWord`).
4. **Fuzzy `[0,1]` operators + `operator_truth`** — operators redefined on `[0,1]`; similarity matrix
   recomputed on the `[0,1]²` grid. *(was roadmap "#3")*
5. **Truth-folding** — `e_statement` folds clause truths through the operator tree → the RESOLVED
   truth (`A1 IMPLY (A2 AND A3)` → `IMPLY(T1, AND(T2,T3))`). *(slice of the reasoning engine)*
6. **Antonym column-read primitive** — `utils_antonyms(W) = { X : base[X][idx(W)] < 0 }` (`lib/llc/utils.py`), sense-scoped.
7. **Phase 0 — parser/compiler hardening** — D1 negation as a discrete `TKZipContent.negated` flag
   (negated input evaluates false end-to-end); D2 comparison polarity via the antonym primitive;
   D3b noun-complement infinitive binding ("ability to roar" → "cat roar").
8. **Knowledge bootstrap 1a** — `scripts/relations.py` harvested **150,529** WordNet relation triples
   (`is_a`/`part_of`/`antonym`/`entails`/`attribute`/`similar_to`) into the `relations` collection —
   the inference chaining backbone (parser-free; cat→animal vs lettuce→plant disjointness derivable).
9. **Knowledge bootstrap 1b (nouns)** — `scripts/glosses.py` ingested **~928 definitions + ~1,140
   axioms** from base-word **noun** glosses (strict/academic: function-word + informal filtered,
   cleaned, POS-framed, routed by clause count).
10. **Unknown-vocabulary fix** — `TKZipContent.unknown` (set by the compiler when a clause's core
    args are all **ungroundable**) → grounding returns neutral `0.5` → `INSUFFICIENT` ("unknown
    vocabulary"), instead of spuriously resolving ("a wug is a blicket" was 0.885). The seam for
    *ask-and-learn*. **Extended** (user-found bug): "ungroundable" now covers an **unresolved name**, not
    just a generic — a PROPN that failed the individual-minting gate is a bare `name` entity with
    `uid=None` (a *minted* individual like "Mari" carries a uid), so it has no sense/identity/vector and
    must be treated as unknown vocabulary. Without this, "Sgriodnsktj exists" matched an existence axiom
    on the predicate alone (zero subject vector skipped as "absent") → spurious 0.99; now → INSUFFICIENT
    (the `tokeniko:why` — "what is X?" — seam). `compiler_zipRefIsUnresolvedName`/`…IsUngroundable` in
    `c_zip.py`; minted individuals ("Mari exists") + places (Rome) stay groundable.
11. **Knowledge bootstrap 1b (adjectives) + compiler None-id guard** — `scripts/glosses.py` ingested
    **424 definitions + 745 axioms** from base-word **adjective** senses (nominal frame
    "something X is &lt;gloss&gt;" → the adjective captured as a property; nouns dedup-skipped). The
    **compiler None-id guard** (`compiler_evaluateReference` returns None instead of an invalid
    reference) lets clausal subjects degrade gracefully — also retroactively fixing the ~7 Phase-1b
    crash skips. **KB now: 1,352 definitions + 1,885 axioms.** *(Verbs deferred — see Parked.)*
12. **Word-sense disambiguation (Phase 2)** — `parser_getMeaning` now picks the dictionary sense by
    context (`parser_disambiguateSense`): **Lesk-first** (gloss-overlap with the sentence's content
    words — reliable on the sparse vectors; a raw cosine confidently mis-ranks) → context-**centroid**
    fallback → most-frequent default (Phase-5 ask TODO). Verified: cat→animal next to "mammal", the
    finance vs river sense of "bank". *(Properties still first-sense — a follow-up.)*
13. **Intra-statement reasoning kernel** — `evaluator_classifyForm` (`lib/llc/evaluator/e_consistency.py`)
    decides a statement's *form* on its own folded logic, no KB. It clusters the leaf clauses into atoms
    by geometric similarity (`evaluator_compareContent ≥ 0.90`), reads each leaf's polarity from its
    `negated` flag, enumerates the crisp `{0,1}` atom assignments, and re-folds the operator tree via
    `_fold_statement` (on `{0,1}`, `operator_truth` collapses to classical boolean logic) →
    `FormClass(contradiction, tautology, detail)`. `contradiction` = the folded truth is 0 under *every*
    assignment (`X∧¬X`); `tautology` = 1 under every. `evaluator_evaluateStatement` now runs this as
    **STEP 0** and short-circuits to `INCONSISTENT` (truth `0.0`, `inconsistency=detail`) on a
    contradiction. Two **locked decisions**: (a) **contradiction-only bar** — only genuinely unsatisfiable
    forms flag, so a satisfiable-but-not-tautological form like `a eq b imply a noteq b` (≡ `IMPLY(x, 1−x)`,
    true when a≠b) stays RESOLVED; (b) **evaluator-only** — the `tautology` flag is computed but *not* yet
    wired into axiom/theorem creation (the `≡1` creation guard is a follow-up). **Scope:** the
    contradiction is caught only when the two clauses share the same predicate and differ by an explicit
    `negated` flag (not/no/never) — verified on "the cat is alive and the cat is not alive", "the door is
    open and the door is not open"; the **lexical-antonym** case ("open" vs "closed", "equal" vs
    "different" without an explicit negation) compiles to geometrically distinct predicates and is
    **deferred** (see Parked).
14. **Reflexive-identity hardwiring** — the compiler now flags an identity-comparison clause whose
    subject and one operand corefer as `reflexive` (new `reflexive: bool` on `TKLLCContent` and
    `TKZipContent`; set in `compiler_evaluateStatement` via `compiler_isReflexiveIdentity` /
    `compiler_isIdentityComparison`, carried in `compiler_zipContent`). "Identity comparison" = predicate
    ∈ `_COMPARISON_AFFIRMATIVE` ∪ its antonyms (equal/same… / different/unlike…); "corefer" = same entity
    id ("a cat is equal to a cat") OR a reflexive-pronoun operand (`_REFLEXIVE_PRONOUNS` =
    itself/himself/… — "a thing is equal to itself"). The intra-statement kernel
    (`evaluator_classifyForm`) then **PINS** a reflexive leaf to a hardwired constant instead of grounding
    it: `a=a → 1`, `a≠a → 0` (the existing `negated` flag carries polarity; both comparison polarities
    handled). Result: "a thing is not equal to itself" / "a thing is different from itself" →
    INCONSISTENT; "a thing is equal to itself" → tautology.
15. **`imply`/`entail` → IMPLY operator + settled belief/attitude semantics** — a matrix verb
    `imply`/`entail` (new `_IMPLICATION_VERBS`) with two clausal (CCOMP) complements now compiles to
    `IMPLY(antecedent, consequent)`: `compiler_implicationOperands` builds the two clause items (antecedent
    seeds with op=AND, consequent carries op=IMPLY) and **drops** the "implies" predication leaf, clearing
    the doxastic `THAT` attitude. So "a thing is equal to itself implies a thing is not equal to itself"
    folds `IMPLY(1,0)=0` → INCONSISTENT for the **right reason** (real implication), not via the earlier
    attitude-modulation workaround (which was **REVERTED** in `_self_truth`). **Belief/attitude semantics
    settled** (logic-is-sacred): "I believe &lt;logically-false&gt;" is NOT inconsistent — the belief-report
    is satisfiable (one can believe a falsehood; the `THAT` attitude modulation shields it); "I know
    &lt;logically-false&gt;" IS inconsistent — knowledge is factive (confidence 1.0, no softening).
    **Limitation:** `imply`→IMPLY fires only when Stanza roots `implies` as the matrix verb (both clauses
    CCOMP); for some lexical content Stanza MIS-ROOTS `implies` to `parataxis` (e.g. "a cat is equal to a
    tree implies …") and it falls back to the old structure (still the correct answer, just not a clean
    IMPLY) — a Stanza-upstream issue, same class as the parked D3a.
16. **Anchor-mechanism unification (semantic-native)** — ONE declarative resolver (`lib/llc/anchors.py`)
    replacing the three ad-hoc "surface word → logical/semantic category" mechanisms that had grown up
    in parallel (literal lemma lists; spaCy `en_core_web_lg` similarity; Mongo `$vectorSearch`). The
    **principle**: never rely on fixed dictionaries — map ANY input to the nearest of a small anchor set
    by semantic similarity (exact-hit fast path → nearest-anchor fallback above a floor), so the logic
    stays in a few manageable buckets and **never misses** an input. Per category the backend is chosen
    for the job — dictionary 2925-dim vectors for content words, spaCy for function words — and
    **polarity-sensitive** categories are **antonym-guarded** so the fuzzy catch can't flip to an
    opposite ("but" never resolves to AND); anchor vectors are **cached in-memory** (no per-call DB).
    **Seven SEMANTIC consumers migrated** onto it: `parser_ccToOperator` (operators),
    `compiler_parseMarker` (subordinate types), attitude classification, comparison polarity (now
    antonym-aware *through* the resolver), `compiler_zipGetAdvmodeBase` (**advmod intensifiers: Mongo
    `$vectorSearch` → in-memory nearest-of-anchors — the cost win**), spatial relations, sequence.
    **Verified via a golden-baseline diff**: exactly **1 intended delta** (an improvement — a clause that
    baseline-misfired as a doxastic belief on "rain" now compiles to a clean neutral AND); a `moreover`
    regression was caught and fixed by raising the sequence floor; `although` now resolves to a safe
    OTHER instead of a false CAUSAL. The ~13 **EXACT** closed-set categories (pronoun deixis, negation,
    …) are registered in the resolver (flippable) but still resolved by direct membership at the call
    sites — a cosmetic mop-up (see Parked).

17. **Inter-statement inference — Slice 1 (taxonomic grounding + refutation) + WSD frequency-prior** —
    first slice of the inference engine: the WSD sense now **bridges** through the whole pipeline
    (`TKDictionary.sense` → `TKLLEntity.sense`, set in `compiler_getEntity` → `TKZipContent.senses`, a
    role→sense dict populated in `compiler_zipContent`) — previously the sense was dropped at the LLC
    boundary. A new **`TKRelationDoc`** (the `relations` collection, registered in `init_io`) exposes the
    ~150k synset-keyed WordNet triples; `EvaluationService` injects a cached `parents(sense)` reader. The
    pure graph logic lives in `lib/llc/evaluator/e_relations.py`: `relations_isa_ancestors` (BFS is_a
    closure, cycle-safe / depth-capped), `relations_subsumes` (is_a path child→parent), and
    `relations_disjoint` (CONSERVATIVE, **tiered** ontological disjointness — two senses are disjoint only
    if, at the FINEST tier where both are placed, they sit under DIFFERENT mutually-exclusive anchors:
    tier 1 biological kingdoms (animal/plant/fungus/…), tier 2 kinds of physical thing
    (organism/artifact/natural_object/substance), tier 3 physical_entity/abstraction). `evaluator_evaluateStatement`
    (new injected `relations=` param) does **relational grounding + refutation** on an is_a clause
    (copular "X is a Y", subject+predicate senses): `subsumes(obj, subj)` → truth ~1 (+ chain),
    `disjoint(subj, obj)` → truth ~0 (+ refutation chain). The verdict stays **RESOLVED** (truth ~1 or
    ~0) — refutation is NOT a new status and NOT `INCONSISTENT` (that stays reserved for the
    intra-statement logic-impossible `X∧¬X`); the premise chain goes in the new
    `EvaluatorResult.derivation: list[str]`. A **WSD frequency-prior guard** (`parser_disambiguateSense`):
    when Lesk gives no clear winner AND the context-centroid is not confident (below an absolute floor or
    within a margin of the runner-up), default to the MOST-FREQUENT sense (smallest WordNet sense number,
    query-word lemma preferred) instead of a low-confidence centroid guess — fixes "a cat is a X" →
    `cat.n.01` (was `cat.n.03`/`guy.n.01`); the Lesk-driven bank finance-vs-river cases are preserved.
    **Verified:** "a cat is a plant" → RESOLVED truth 0.0 with chain (organism⊥artifact); "a cat is a
    car"/"an idea" / "lettuce is an animal" (kingdom) → refuted; "a cat is a mammal" / "a car is a
    vehicle" → subsumed true; "a cat is a dog" / "a cat is a pet" → INSUFFICIENT (both organisms —
    conservatism: refutation is the strong claim); intra-statement INCONSISTENT regression intact.

18. **Inter-statement inference — Slice 2a (quantifiers + quantifier-aware relational grounding)** — a
    clause now carries a **`TKQuantifier`** (new enum in `lib/core/tk.py`: UNIVERSAL / EXISTENTIAL /
    NEGATIVE / DEFINITE / GENERIC, default GENERIC) — the `quantifier` field on `TKLLCContent` and
    `TKZipContent`, read off the SUBJECT's determiner via a new EXACT (closed-class, no-fuzzy) anchor
    mapping `anchor_quantifier(lemma)` in `lib/llc/anchors.py` (`all/every/each`→universal,
    `a/an/some/any/several`→existential, `no/none/neither`→negative,
    `the/this/that/these/those`→definite, bare→generic; `_QUANTIFIER_*` constants in `constants.py`).
    The compiler reclassifies a subject-determiner "no" as the NEGATIVE quantifier so it no longer also
    trips the predicate `negated` flag (avoids a **double-flip**). The relations-graph grounding
    (`e_statement._ground_relationally`) now applies a **quantifier × verdict truth table**: base = TRUE
    if the input clause's senses SUBSUME (`X is_a* Y`), FALSE if DISJOINT, then
    `net_flip = (quantifier == NEGATIVE) XOR (negated)` flips it — so "all cats are mammals" → true,
    "no cat is a mammal" → false, "no cat is a plant" → TRUE, "a cat is not a plant" → TRUE. This also
    **FIXED a latent bug**: relational grounding previously ignored predicate negation, so "a cat is not
    a plant" wrongly evaluated false. **Verified** end-to-end (all/a/the/no/some over subsumes+disjoint;
    gibberish → insufficient; door contradiction → INCONSISTENT — all intact). **Scope:** the quantifier
    drives the CRISP relational (graph) grounding only — it's recorded but not yet applied to the
    geometric/definition grounding (see Parked).

19. **Inter-statement inference — Slice 2b: part_of (mereological) grounding** — the relations-graph
    grounding now handles **part_of** (part-whole) claims, parallel to the is_a logic. The pure graph
    logic in `lib/llc/evaluator/e_relations.py`: `relations_part_ancestors` (BFS transitive closure of
    part_of, cycle-safe / depth-capped) + `relations_is_part_of(part, whole)` (returns a path or None;
    irreflexive), parameterized by an injected `part_parents` callable (DB-agnostic). **Relation-type +
    direction recognition** (`e_statement`): "X is (a) part of Y" / "X belongs to Y" →
    part_of(part=X, whole=Y); "Y has/contains/includes/comprises X" → part_of(part=X, whole=Y) (the
    object is the part, the subject the whole). Cue lemma sets in `constants.py` — `_PART_OF_PREDICATES`
    (part/portion/piece/component/constituent/member/element) and `_HAS_PART_VERBS`
    (have/contain/include/comprise/possess/incorporate/constitute/encompass) — matched against the
    WSD-resolved synset lemma; a part-whole clause routes to part_of **ONLY** (never is_a) to avoid
    double-deciding. **Sense-bridge extension** (`c_zip.py`): for "X is part of Y" the whole Y is the
    predicate's nmod property — `compiler_contentSenses` now surfaces it as `predicate_nmod` so the
    whole's sense reaches the evaluator. **Grounding** (conservative, sparse graph): base = TRUE if part
    is_part_of* whole; base = FALSE by mereological ANTISYMMETRY if the REVERSE holds (whole is_part_of*
    part — "a car is part of a wheel" is false because wheel∈car); else NO verdict (a MISSING edge is
    never a refutation). Same quantifier `net_flip = (quantifier == NEGATIVE) XOR negated` as Slice 2a;
    the chain is recorded in `EvaluatorResult.derivation`. **Wiring**: `EvaluationService` injects a
    `part_of` reader and `evaluator_evaluateStatement` gained a `part_of=None` param (separate from the
    is_a `relations=` reader — different semantics). **Verified** via the live /evaluate: "a cell is
    part of an organism" / "an organism has a cell" → RESOLVED true with the part_of chain;
    antisymmetry-false + transitivity proven at unit level; is_a + quantifier + gibberish +
    intra-statement-contradiction regressions all intact. **WSD caveat:** WSD sometimes picks the wrong
    head sense (e.g. "cell" → cell.n.01 compartment vs cell.n.02 biological); the graph then finds no
    edge and — by design — conservatively does NOT refute. A known WSD limitation, not a logic defect.

20. **Intra-statement contrary-predicate contradiction (Slice-2 priority-1)** — the intra-statement
    kernel (`evaluator_classifyForm`) now also catches a **contrary-predicate** contradiction: two
    clauses predicating **antonym senses of the same subject** ("the cat is alive AND the cat is dead")
    → INCONSISTENT. It is **not** P∧¬P (no explicit `negated` flip) — the two clauses are geometrically
    distinct atoms (cos ~0.69, below the 0.90 alias threshold) carrying antonym predicate senses
    (`alive.a.01` / `dead.a.01`). Modeled as a **mutual-exclusion constraint** in the crisp enumeration:
    `_contrary_pairs(reps, reps_unknown, antonyms)` finds atom pairs that (same subject sense, distinct
    predicate senses, **both non-negated**, antonym-linked) cannot both be 1; the enumeration loop skips
    the (1,1) corner of each such pair. This forbids ONLY (1,1) — (0,0) stays allowed, so a disjunction
    of contraries ("X is alive or X is dead") remains satisfiable AND is **not** a spurious tautology;
    an AND of contraries loses its only satisfying corner → maxF=0 → contradiction (correct *contrary*
    semantics, contrary ≠ contradictory). The signal is injected: `evaluator_classifyForm` /
    `evaluator_evaluateStatement` gained an `antonyms=` reader, and `EvaluationService` injects a cached
    one over the `relations` collection (`relation == "antonym"`, `TKRelationDoc`); with `antonyms=None`
    the kernel is byte-for-byte unchanged (purely additive). The P∧¬P branch keeps priority over the
    contrary branch in the detail string. **Key findings:** (a) the precise signal is **antonym** —
    `entails` is an *inference* edge (not assertional like is_a/part_of) → deferred to KB
    forward-chaining; `attribute` is too coarse for contrariety (groups hot/warm, which are not
    contraries → over-fires) so it is NOT a trigger; (b) recall is gated by **adjectival WSD quality** —
    a mis-WSD (heavy/`light.a.03` military; open/`close.v.01` verb; present/absent not antonym-linked in
    WordNet) yields a **conservative miss, never a false positive**. **Verified:** alive/dead and
    true/false → INCONSISTENT; alive ∧ ¬dead (non-negated guard), alive ∨ dead (satisfiable, not
    tautology), different-subject, non-antonym, heavy/light → consistent; P∧¬P (alive/¬alive) keeps its
    existing mixed-polarity detail; is_a + unknown-vocab regressions intact; `antonyms=None` not flagged.

21. **Discriminative individual representation + entity-linking (Slice 3a)** — named individuals
    ("Mari", "Rome", "Google") used to compile to a **ZERO** 2925 vector — all collapsing to one
    indistinguishable point. They now get **two SEPARATE things, deliberately kept apart**: (a) an honest
    **SEMANTIC** vector = their NER **type centroid** (`PERSON→person.n.01`, `GPE/LOC/FAC→location.n.01`,
    `ORG→organization.n.01`, `NORP→group.n.01`, `PRODUCT/WORK_OF_ART→artifact.n.01`, `EVENT→event.n.01`;
    pulled from the `dictionary` collection, in-memory cached) and (b) a referential **IDENTITY** = a
    context-scoped uid `name@channel:talker_uid`. **Decision — no random vectors:** meaning lives in the
    GROUNDED/sacred 2925 geometry (each dim a measured base word), identity lives **symbolically** in the
    uid; the two NEVER mix, so the semantic space stays pollution-free. The **context key** is
    `(channel-type, talker-uid)` — same surface name from different talkers/channels is a different
    individual. **Identity-bridge** (mirrors the sense-bridge): `TKName.uid/vector/ner` (minted in
    `parser_getIndividual`, wired into both PROPN sites) → `TKLLEntity.uid` (`compiler_getEntity`; the
    centroid rides in `semantic_vector`, now consumed for `entity_type=="name"` in
    `compiler_zipGetEntityVector`) → `TKZipContent.identities` (role→uid, via
    `compiler_contentIdentities`/`compiler_refUid`). **Gate:** NER-type-mapped **AND** a real spaCy-lg
    word vector — parser tokens are stanza tokens (no vectors), so `has_vector` is checked against the lg
    `nlp` vocab (`_parser_hasLgVector`); OOV gibberish spaCy mislabels as GPE is rejected; a **known place
    still wins via `parser_getPlace`** (geo-anchored, not an individual). **Homing:** extended
    `MEMStakeholder` (`kind="individual"`, `ner_type`, `vector`, `contextKey`) via `io.upsert_individual`
    (get-or-create, idempotent), called ONLY on storing paths (the `/input` handler walks the recursive
    parse), NEVER on `/evaluate` (stays pure). **Primitive:** `evaluator_sameIndividual(a, b, role)` —
    same uid→True / different→False / either missing→None (the demonstrable linking hook; not yet wired
    into `_best_match`/grounding). **Verified** (full pipeline, all 8 cases): Mari → uid
    `mari@internal:tokeniko` + nonzero person-centroid subject vector; Mari vs Luca → different uids,
    semantic cosine 1.0 (same type — correct), `sameIndividual` False; Mari vs Mari(sad) → same uid, True;
    Mari (person) vs Google (org) centroid cosine ~0.05 (distinct types); deterministic (identical uid +
    vector on recompile); gibberish "Kjadhfhfjdk" mints nothing; "a cat is a mammal" + alive/dead
    contradiction regressions intact; `upsert_individual` idempotent. **Deferred:** pronoun→individual
    coreference; group-channel **shared context** (resolve via KB later, not channel-keyed); learned /
    accruing individual vectors (today the static type centroid); deeper evaluator consumption of
    `identities` (coref-driven matching/chaining in `_best_match`/grounding). The dormant `names`
    collection is now **superseded** by NER + the stakeholders collection (cleanup deferred).

22. **Inter-statement inference & forward-chaining — priority-2 (Slices 2a–2c)** ✅ DONE — quantifiers ✅ DONE (Slice 2a), `part_of`
   (mereology) ✅ DONE (Slice 2b), and the **antonym-predicate contrary contradiction** ✅ DONE (#20
   above — was Slice-2 priority-1). On the other relation types: **`entails`** is an *inference* edge
   (not an assertional relation like is_a/part_of) → folded into **KB forward-chaining** (priority 2,
   below); **`attribute`** is NOT used for contrariety (too coarse — hot/warm). Individual-entity
   identity ✅ DONE (Slice 3a, #21). Ordered as **a → b → c** — **all three landed ✅** (the forward-
   chaining KB engine is in place; this priority-2 reasoning block is effectively done, modulo the parked
   defeasibility caveat noted under (c) and the legacy gloss-as-axioms cleanup):
   - **(a) `recompile`** ✅ DONE (`scripts/recompile.py`) — the whole stored KB (1885 axioms + 1352
     definitions; theorems 0) re-derived from each item's `original` under the current pipeline, so the
     stored geometry now carries **senses** (sense-bridge postdated the data). Verified: **0 failures**,
     3211/3237 gained senses, 5 axioms gained identities, all metadata preserved (dry-run-default +
     `--apply`). Forward-chaining now has senses to unify against.
   - **(b) rule-shaped KB** ✅ DONE (`scripts/seed_rules.py`) — recon corrected the substrate finding:
     the 1885 "axioms" are almost entirely WordNet-gloss *definitions* (generic/existential), with
     ~ZERO genuine rules (universal quantifiers: 1, a gloss fluke). So (b) was authoring from scratch,
     not harvesting. Seeded 5 **universal property rules** ("all carnivores eat meat" → universal subj +
     predicate/object senses): `all carnivores eat meat`, `all birds have feathers`, `all fish swim`,
     `all humans are mortal`, `all thinkers exist` (trusted axioms). KEY: `quantifier==universal` cleanly
     discriminates rules from the gloss-axioms (6 universal-leaf axioms total = our 5 + 1 fluke). The
     syllogism `all humans are mortal` + `Mari is a human` (a Slice-3a individual) → `Mari is mortal` is
     the bridge demo for (c). NB the gloss-as-axioms pollution remains (parked legacy cleanup).
   - **(c) chaining engine** ✅ DONE (`lib/llc/evaluator/e_chaining.py`) — the multi-hop forward-chainer.
     Given an input, it seeds a class closure from the subject's sense (+ is_a ancestors) and, for an
     individual subject, from the membership FACTS about that uid; fires **MEMBERSHIP rules** (universal,
     NOUN predicate — "all humans are thinkers") to a **fixpoint** to grow that closure; then applies
     **PROPERTY rules** (universal, verb/adj predicate — "all carnivores eat meat") whose subject sits in
     the closure to derive properties. `evaluator_chainGround` (the grounding hook, wired into the
     `e_statement` per-clause loop after is_a/part_of) **corroborates** (truth≈1) or **KB-refutes**
     (truth≈0) the input clause with a derivation chain. Per doctrine a KB-contradiction is **RESOLVED
     with truth≈0 + a chain, NEVER INCONSISTENT** (that is reserved for logic/math violations).
     `evaluator_evaluateStatement` gained `rules=`/`facts=`; `EvaluationService` extracts them from the
     active axioms (universal-leaf → rule, classified membership/property by predicate POS; individual
     membership leaf → fact). Demos verified (rules/facts injected in-probe, DB untouched): `a cat eats
     meat` → 1.0 (cat→feline→carnivore + rule); `a cat does not eat meat` → 0.0 KB-refuted (NOT
     inconsistent); `Mari is mortal` → 1.0 (fact + rule syllogism); `Mari exists` → 1.0 **2-hop** (fact →
     `all humans are thinkers` → Mari is_a thinker → `all thinkers exist` → Mari exists); `a cat is happy`
     → INSUFFICIENT (no spurious fire); is_a grounding + the antonym kernel regress clean.
     `scripts/seed_rules.py` extended with the membership rule `all humans are thinkers` + a `FACTS`
     list (`Mari is a human`) — dry-run-default; `--apply` is the operator's to run.
     **Parked caveat — defeasibility**: strict universals over biological kinds have exceptions
     (penguins don't fly, a sated cat may not eat) — the current engine treats `all` as crisp/monotonic,
     so it can over-assert; refine via future KB/input (exception facts, graded trust). MATH/logic
     universals stay clean.

## 🔭 Next (ordered)

> Order locked with the author: **1 → 2 → 3 → 4**. Each step makes the layer beneath "strong and
> failproof" before the next builds on it; the brain (4) comes last, on a verified foundation.

1. **Engine consolidation — parked reasoning loose-ends** — finish the edges of the now-built reasoning
   engine before building up:
   - **≡1 / contradiction creation guard** — ✅ DONE. `assert_no_contradiction` (`api/services/validation.py`)
     runs `evaluator_classifyForm` (with the antonym reader) in axiom/definition/theorem
     create/patch/replace and **rejects a contradictory FORM** (`X∧¬X`, `a≠a`, antonym-predicate) →
     `InconsistentStatementError` → HTTP 422; tautologies AND contingent statements are allowed (it is a
     contradiction-reject guard, **not** a tautology requirement). Guard is outside `compile_fields`, so
     `scripts/recompile.py` is unaffected.
   - **deeper evaluator use of `identities`** ✅ DONE (#1b) — `evaluator_compareContent` now consumes the
     identity-bridge: for the subject/direct roles it overrides the geometric score by
     `evaluator_sameIndividual` (same uid → 1.0, different uid → 0.0, no uid → geometry), so same-type
     individuals are no longer conflated ("Mari is happy" vs "Luca is happy" drops ~0.96 → 0.615, below
     the match/cluster thresholds) and the same individual is recognized across different claims ("Mari
     is happy"/"Mari is sad" keep subject=1.0). Propagates through `compareItem`/`compareZip`/`_best_match`
     and the consistency-kernel clustering; definitions/generic clauses (no uid) are untouched. Indirects
     (variable-length set) deferred.
   - smaller follow-ons: **co-predication WSD hint**, **graded attribute-contrariety**, **defeasibility**
     of biological universals (exception facts / graded trust) — pick the high-value ones.
2. **KB consolidation — full re-home of gloss-axioms into multi-clause definitions** *(built — pending
   operator-gated `--apply`)* — the ~1883 "axioms" are really WordNet-gloss *definitions* (predate the
   3-tier model). The re-home has two coordinated halves, landed together (model + data migrate as one;
   API down for the cutover):
   - **Model:** `MEMDefinition` now holds the full compiled `TKZip` (`zip`, single **OR** multi clause)
     instead of a single `TKZipContent` (`content`). `NotASingleClauseError` removed — multi-clause
     definitions are legal. `EvaluationService` flattens each definition's `zip` → leaf clauses, so the
     evaluator still receives a flat `list[TKZipContent]` (`evaluator_groundContent` unchanged).
     `DefinitionService.compile_fields`/create/patch/replace store `zip`; the contradiction guard is kept.
   - **Migration:** `scripts/migrate_glosses.py` (dry-run by default; `--apply` operator-gated). Phase 1
     re-derives the existing ~1352 `content`-shaped defs to the new `zip` shape (raw-pymongo read — old
     rows can't load via the new model — recompile via `compile_fields`, `$set {zip,raw} $unset content`,
     metadata preserved). Phase 2 moves the gloss-axiom batches into definitions: an axiom is a
     gloss-to-move iff its `createdAt` day ∉ the **keep-set {2026-06-14, 2026-06-19}** (the 2 genuine
     relational axioms + 7 seeded rules/facts = 9 kept) — authoritative, with a frame-regex cross-check
     for disagreement — dedup by `original`, then delete the moved axiom. Leaves `axioms` = genuine
     relations + universal rules + individual facts only. Idempotent on re-`--apply`.
3. **Pipeline deep-test — first end-to-end test harness (pytest)** ✅ DONE *(the failproof gate before
   the brain)* — `tokeniko/tests/` (pytest; `task test`). **Band-asserts** (status + truth band +
   structural facts — NEVER exact floats/senses, so the suite guards *meaning* and won't cry wolf on
   numeric drift) across **layer contracts**: `test_compiler.py` (flags: unknown/quantifier/negated/
   reflexive, senses/identities key presence, leaf count), `test_evaluator.py` (verdict bands: resolved-
   true/false, insufficient, inconsistent; chaining derivation non-empty), `test_identity.py`
   (compareContent + `evaluator_sameIndividual`), `test_guard.py` (contradiction-creation reject path).
   Seeded from this session's verified cases. **23 passed, 1 xfailed** (integration-style: needs
   Mongo+Ollama + the seeded KB; ~150s, pipeline loaded once via a session fixture). The pre-commit
   regression gate; corpus grows as behaviors land. **xfail (tracked gap):** `"a robin has feathers"` →
   `resolved truth≈0.12` (confident near-FALSE, empty derivation) instead of true — WSD-gated (the
   `all birds have feathers` rule uses `bird.n.02`; a specific bird sits under a different sense so the
   rule never fires) AND a symptom of thin grounding giving a confident-ish verdict where it should
   abstain. Tracked, not red.
4. **Reflective behavior layer — the brain (THE ACTIVE FRONTIER)** — behavior as memory rules over
   reserved tokens (`[eval:inconsistent] IMPLY [tokeniko:speakup]`, `[eval:unknown] IMPLY
   [tokeniko:ask]`); `imperative`-modality activation; hardwired action-dispatch + allowlist; the
   `brain` perceive→evaluate→act loop. Includes the **unknown → ask → learn-at-lower-trust** loop (the
   KB becomes living; graded by the `trusted` field). The seam to the volitional/emotive layer.
   **The consolidation arc beneath it (#1 engine consolidation, #2 KB consolidation, #3 pytest gate) is
   DONE — the foundation is strong/clean/failproof, so #4 is now the build frontier.**
   - **Build order — A → B → C → D** (author's; **HOW before WHAT**): **A** = the orchestration's
     control-flow spec (this is the existing `brain/README.md` design; priority ordering **Actions >
     Priorities > Thinking** — thinking is *background*, the reactive path wins); **B** = the **data
     model** (FIRST concrete step, greenfield): the `MEMIdea`/`MEMAction`/`BrainState` entities + Bunnet
     docs + `io` registration, with atomic (`find_one_and_update`) queue state-machines and a singleton
     `brain_state` for continuity across restarts; **C** = the **meta-language** ✅ **BUILT** (pending the
     operator-run seed `--apply`) — hardwired reserved-token *syntax* (`EvalToken`/`TokenikoAction`
     enums: `eval:*` triggers, `tokeniko:*` actions, the `[eval:X] → [tokeniko:Y]` rule format) with
     KB-driven *personality* in a `behavior_rules` table (`MEMBehaviorRule`→`TKBehaviorRuleDoc`,
     non-unique `trigger` index; VISION pillar 9), including **`eval:unknown → tokeniko:guess`**
     (interpolate a provisional low-trust definition from context — the KB lives/learns). The engine is
     `brain/behavior.py` (`behavior_for` = the candidate superposition; `spawn_ideas_for` = the fan-out
     into ideas carrying `MEMIdea.action_token`; `dispatch_action` = `tokeniko:Y → ActionType` via the
     hardwired `_DISPATCH` registry — `ignore`/no-token → no action, `guess`/`learn` → internal KB-write
     intent `targetId=self`, others → outward); `priorities_phase` consumes the dispatch (pending ideas
     sorted **urge-desc**). Seed via `scripts/seed_behavior_rules.py` (dry-run default; `--apply`
     operator-gated). **Parked doors:** the **collapse arbitration** (choosing among multiple kept
     candidates) + the **actions-as-data** future (externalize `_DISPATCH` to a table). **D** = the
     **WHAT** — fill in the loops' real business logic (thinking scan, priority/feasibility scoring,
     action execution). After B comes the HOW orchestration BL (scheduler implementing the routing +
     cooperative yield + event-interruption against *stub* cognition), then C ✅, then D.
   - **Cooperative-preemption model** — there is no OS preemption and `brain` / `api`+`senses` are
     **separate processes**: `api`/`senses` handle input in their own process regardless, and the brain
     *reacts* via the memory-trace (new `memory` items snap thinking back) while **throttling** (bounded
     work-units, check-between, back off when `Actions` is non-empty or new memory appears) so the
     reactive path is never starved. Thinking is lowest-priority background filler.
   - **Detailed design lives in `brain/README.md`** (the three loops, queue-priority routing, the
     data model, the meta-language + guess, the governor). This roadmap entry is the summary; that doc
     is the spec.
   - **Scaffolding already in place** (refactoring `2d97aff`): the `brain` daemon now runs three
     concurrent loops — **thinking**, **priorities** (forms wishes/ideas → the `TKIdeaDoc` layer
     below), **actions** (carries them out) — and the external connectors moved to the **`senses/`**
     subproject (Discord + ATProto/Bluesky, the actions' I/O). The loops are stubs awaiting the
     reasoning engine + the ideas-repository below.
   - **Orchestration design → `brain/README.md`** — the three loops (Thinking / Priorities / Actions),
     dynamic queue-priority routing, and the thinking↔wondering re-evaluation of memory as the KB grows
     (tokeniko growing wiser). It now encodes the agreed model: Thinking writes **theorems → the KB**
     (necessary truths, don't fade) *and* **urges → the Ideas queue** (the "maybe", can fade), with a
     theorem taking a direct vs idea→action path by **cost**; Priorities weighs **urge** (the
     act-threshold / conflict key) against **feasibility** (a separate can-do gate); the idea→action
     mapping = the reserved-token behavior rules; and a **governor** (urge + decay) keeps internal
     reflection from running away. Engineering: atomic queue transitions + a `brain_state` singleton for
     continuity across restarts. Cognition hooks = the reasoning engine. (Still future — the loops are
     stubs; scoring/governor to tune.)
   - **I/O membrane → `senses/README.md`** — the connectors daemon (Discord, bidirectional;
     ATProto/Bluesky, inbound awareness). The boundary: **brain decides, `senses` does the I/O** — an
     action names a `channel`, `senses` owns the channel and performs the send/post. Currently
     scaffolding / stubs.
   - **Ideas repository (`TKIdeaDoc`)** — the concrete structure behind `[tokeniko:<action>]`: axioms/
     theorems that instil ideas/urges in tokeniko's mind. Each idea carries a `TKZip`/`TKZipContent`
     payload plus: (1) an **urge level** — `idea 0.1 · wish 0.5 · urge 0.7 · need 1.0` — which doubles
     as both the **act/don't-act threshold** and the **conflict-resolution** key when several ideas
     fire (highest urge wins); (2) the **source** the idea came from; (3) metadata (id, timestamps);
     (4) optionally a **deadline**. tokeniko *thinks always, acts maybe* — this store is the definition
     of the "maybe". (Statuses/levels and the act-threshold are to be tuned.)

## ⏸️ Deferred / parked

- **Tiered OOV recovery — optional LLM "polish" escalation** — gibberish is now caught cheaply at the
  parser/compiler (no-vector → generic, fallback similarity-threshold `_WSD_FALLBACK_MIN_SIMILARITY`,
  and a lone-predicate/non-propositional clause → `unknown` → INSUFFICIENT). When that *trips*
  (INSUFFICIENT / unknown), we could OPTIONALLY escalate to the preparser's LLM "polish" pass (SymSpell
  + the 2-model Ollama typo-correction) to distinguish a genuine typo (recoverable) from true gibberish
  — i.e. cheap structural detection first, expensive LLM repair only on failure. CPU-heavy, so kept as a
  fallback/escalation, not the default; ties into the `unknown → ask/recover` seam.
- **Sentence-level unparseable gate — generalize the preparser into a robustness front-gate** *(deferred
  refinement, user-raised; not a bug)* — a WHOLESALE-gibberish / non-English sentence ("rufodi lkjsdf …")
  today gets the full expensive pipeline (Stanza parse + WSD + compile + evaluate) only to land on
  "everything unknown" — and `/evaluate` bypasses the preparser entirely, so there is no front-gate at
  all. The preparser already does typo-fix (SymSpell) + language-detect (lingua) + translate (Ollama),
  but it is binary ("preparse? → fix + translate") and **only on `prepare=1`**. Generalize it: add a
  cheap **English-vocab-coverage check** (the `has_vector` / lg-vocab signal) up front; below a
  CONSERVATIVE floor (wholesale gibberish, NOT a sentence with one rare name — "Sgriodnsktj exists" must
  still parse → the clause-level INSUFFICIENT from #16-class) → **REJECT** to a distinct "unparseable /
  not-understood" outcome (the `tokeniko:why` — "I don't understand" — seam), short-circuiting BEFORE the
  slow/CPU-heavy Ollama translate. So: cheap reject of the untranslatable; translation stays the explicit
  path for real foreign languages. Complements the clause-level unknown handling (sentence-level vs
  clause-level). PERF guard + correctness. Threshold calibration is the main risk. Deferred — no hurry.
- **Contextual WSD for ambiguous heads** — with no disambiguating context the frequency-prior guard may
  pick a non-intended sense ("plant" → factory `plant.n.01`); the tiered-ontology refutation still returns
  the right verdict (e.g. "a cat is a plant" → refuted) but via the artifact reading
  (organism⊥artifact rather than animal⊥plant). Deeper context/Lesk-improving WSD is the follow-up.
- **Anchor EXACT-membership mop-up** — the ~13 closed sets (pronoun deixis, negation, …) are registered
  in the resolver but are still resolved by direct `in set` at the call sites; route them through the
  resolver for literal completeness (a pure refactor, zero behavior change).
- **Concessive + resultative clause types** — `TKClauseType` lacks CONCESSIVE / RESULTATIVE, so
  `although` → OTHER (safe but lossy) and `so` → AND instead of contrast / IMPLY; add the types + their
  operator mappings for correct concessive / resultative logic.
- **Anchor KB vector-coverage gaps** — some intensifier adverbs (`hugely`) and comparison antonyms
  (`unequal`, `dissimilar`) have empty/missing dictionary vectors, so the semantic catch can't reach
  them ("never-miss" is bounded by vector coverage); a dictionary-vectorization follow-up (ties to the
  deferred adverb work).
- **Dual `en_core_web_lg` load** — `parser.nlp` + `c_state.nlp` both load the model; consolidate to one.
- **Anchor floor calibration** — the operator / subordinate / intensifier / attitude / sequence floors
  were tuned on a 32-sentence battery; validate on a larger set. Also: the operator fuzzy fallback is
  unsafe for non-`cc` inputs (`because` → NOTIMPLY latent; `parser_ccToOperator` only receives `cc`
  tokens, so it is currently unreached).
- **1b verbs** — the `"X means <gloss>"` frame *captures* the verb but drags in "means" (a spurious
  predicate / `THAT` doxastic attitude, since "means + clause" parses as a complement-taking verb),
  below the clean-core bar. Revisit with a cleaner frame (a gerund `"Xing is …"` form needs
  morphology; or treat "mean" as a definitional copula). Then re-run `glosses.py` with `v` in `_INGEST_POS`.
- **D3a — relative-clause matrix subject** ("the man who loves Mary runs"): a **Stanza mis-rooting**
  (upstream), not parser logic; quotes hunch disproven. Needs a guarded re-rooting heuristic or a
  model change.
- **`imply`→IMPLY parataxis robustness** — Stanza mis-roots `implies` to `parataxis` for some lexical
  content, so the `imply`/`entail`→IMPLY transform fires only when `implies` is the clean matrix root
  with two CCOMP complements; a clausal-subject antecedent isn't captured. Same Stanza-upstream class as
  D3a; needs guarded parse-repair (risky) — parked.
- **Proper clausal-subject support** ("to err is human"): represent statement-as-subject in the LLC.
- **Negative-quantifier subject rewrite** ("nobody" → generic person/thing; flagged only today).
- **Geometric negation-awareness** in `evaluator_compareContent` (today only the truth path is).
- **Quantifier effect on geometric grounding** — today the quantifier drives only the crisp
  relations-graph verdict; applying it to the soft definition/axiom grounding is a follow-up.
- **Antonym-predicate / lexical contradiction** — ✅ **DONE** (Landed #20): the intra-statement kernel
  now catches a contradiction carried by distinct **antonym predicate senses** of the same subject
  ("the cat is alive" vs "…dead") via an injected `antonyms` reader over the sense-bridged
  `TKZipContent.senses` + the `relations` collection (`relation == "antonym"`), modeled as a
  mutual-exclusion constraint in the crisp enumeration. (The sense-bridge made the word-level signal
  reachable from the zip layer — the earlier blocker.) Remaining edges are WSD-gated (a mis-WSD →
  conservative miss) and noted in #20.
- **Co-predication WSD hint** — when several adjectives predicate the same subject, *prefer adjective
  senses that share an `attribute`* (the WordNet adjective→attribute-noun link). Would lift recall on
  the contrary-predicate check (e.g. open/closed, present/absent) by steering WSD toward the
  predicate-sense pair that is actually contrastive, instead of the frequency-prior default that today
  picks `close.v.01` (verb) or a non-antonym-linked sense. A WSD-quality improvement, not a logic
  change.
- **Graded attribute-based contrariety** — the current contrary check fires only on a discrete
  `antonym` edge (a hard contrary). A future idea: derive *graded* contrariety from the `attribute`
  relation (same attribute-noun, opposed poles) for adjective pairs without an explicit antonym edge —
  but `attribute` is too coarse to use as a crisp trigger (hot/warm share an attribute yet are not
  contraries), so this needs a graded/degree model, not a boolean one.
- **Axiom/theorem `≡1` validity creation guard** — `evaluator_classifyForm` already computes the
  `tautology` flag, but it is not yet wired into the axiom/theorem POST (a trusted relation should fold
  `≡ 1` over all assignments). A follow-up to the contradiction-only evaluator bar.
- **Intrinsic comparison grounding** — `compare(subject, indirect)` for eq/noteq clauses.
- **Trust-weighted grounding + conflict arbitration** (Phase-4 follow-ons; lean on `trusted` + recency).
- **Individual-entity identity** (Mari ≠ Luca; named-entity vectors) — ✅ **DONE** (Landed #21, Slice 3a):
  type-centroid semantic vector + context-scoped identity uid + `evaluator_sameIndividual`. Remaining:
  coreference/coref-driven matching (deferred — see #21).
- **`axioms`-collection legacy cleanup** (predates the three-tier model; 1b largely repopulates it).
- **`@-1,0,0` spacetime artifact** — single-entity axis normalization tidy.
- **`recompile` utility** — ✅ **DONE** (`scripts/recompile.py`, priority-2 step a): re-derives the KB
  from stored `original`s under the current pipeline (dry-run-default + `--apply`, metadata-preserving,
  per-item-robust). Re-run it whenever the parser/compiler changes materially.
- **t-norm / implication choice** (Gödel vs Łukasiewicz vs product) — the one semi-arbitrary "physics
  constant".

---

## Doc map (so this stays the only place for *status*)

- **`VISION.md`** — the why (north star; origin; the "biological being" framing).
- **`doc/roadmap.md`** — *(this)* status + ordered items.
- **`doc/plan.md`** — phased execution detail (the *how* per phase).
- **`doc/reasoning-engine-brainstorm.md`** — design + the verified empirical findings.
- **`doc/parser-compiler-review.md`** — parser/compiler quirks, fixes, remaining gaps.
- **`CLAUDE.md`** — architecture / how the code is laid out (not status).

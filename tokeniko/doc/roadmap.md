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
    args are all generic) → grounding returns neutral `0.5` → `INSUFFICIENT` ("unknown vocabulary"),
    instead of spuriously resolving ("a wug is a blicket" was 0.885). The seam for *ask-and-learn*.
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

## 🔭 Next (ordered)

1. **Anchor-mechanism unification** — today the "map a surface word → a logical category" decision is
   done THREE inconsistent ways: `_ATTITUDE_ANCHORS` (literal lemma list), `_PROP_BASE_ADVMOD_ANCHORS`
   (`TKDictionaryDoc` / Mongo `$vectorSearch` semantic match), `_SUBORDINATE_TYPE_BASE_ANCHORS`
   (spacy_stanza vector similarity). **Unify the INTERFACE** — one resolver, one place, prefer in-memory
   — with a small **TYPED TAXONOMY** of category-kinds underneath; *not* "spacy for everything", because
   spacy static vectors are antonym-/sense-blind (the exact failure the WordNet dictionary fixes;
   love/hate≈0.86). Taxonomy: closed-class function words (operators/modals/determiners) → literal lemma
   set (precision is a feature); syntactic role (subordinate type) → spacy_stanza dep/POS; open-class
   polarity-neutral (intensifier magnitude, attitude verbs) → spacy_stanza vectors (in-memory, cheap);
   polarity-sensitive (comparison, negation, gradable opposites) → antonym-aware base/dictionary vectors.
   Do a short **DESIGN pass first** (it's the hardwired language→logic layer — the heart of "logic as the
   first axiom").
2. **Reasoning engine — inter-statement inference** — soft-unification (similarity + WSD + memory) +
   forward-chaining over the `relations` graph + KB; **minimal premise + identification set**
   (unsat-core) output; quantifiers ("all"/"only"); chaining termination/cycles.
3. **Reflective behavior layer (later)** — behavior as memory rules over reserved tokens
   (`[eval:inconsistent] IMPLY [tokeniko:speakup]`, `[eval:unknown] IMPLY [tokeniko:ask]`);
   `imperative`-modality activation; hardwired action-dispatch + allowlist; the `brain`
   perceive→evaluate→act loop. Includes the **unknown → ask → learn-at-lower-trust** loop (the KB
   becomes living; graded by the `trusted` field). The seam to the volitional/emotive layer.
   - **Scaffolding already in place** (refactoring `2d97aff`): the `brain` daemon now runs three
     concurrent loops — **thinking**, **priorities** (forms wishes/ideas → the `TKIdeaDoc` layer
     below), **actions** (carries them out) — and the external connectors moved to the **`senses/`**
     subproject (Discord + ATProto/Bluesky, the actions' I/O). The loops are stubs awaiting the
     reasoning engine + the ideas-repository below.
   - **First-draft orchestration design → `brain/README.md`** — the three loops
     (Thinking / Priorities / Actions), dynamic queue-priority routing, the thinking↔wondering
     re-evaluation of memory as the KB grows, atomic queue transitions + a `brain_state` singleton for
     continuity across restarts. Its cognition hooks = the reasoning engine; its idea→action mapping =
     the reserved-token behavior rules. **A draft to be reconciled** (its feasibility-score vs the urge
     gradient above; and thinking should also emit theorems/inconsistency-findings, not only ideas).
   - **Ideas repository (`TKIdeaDoc`)** — the concrete structure behind `[tokeniko:<action>]`: axioms/
     theorems that instil ideas/urges in tokeniko's mind. Each idea carries a `TKZip`/`TKZipContent`
     payload plus: (1) an **urge level** — `idea 0.1 · wish 0.5 · urge 0.7 · need 1.0` — which doubles
     as both the **act/don't-act threshold** and the **conflict-resolution** key when several ideas
     fire (highest urge wins); (2) the **source** the idea came from; (3) metadata (id, timestamps);
     (4) optionally a **deadline**. tokeniko *thinks always, acts maybe* — this store is the definition
     of the "maybe". (Statuses/levels and the act-threshold are to be tuned.)

## ⏸️ Deferred / parked

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
- **Antonym-predicate / lexical contradiction** — the intra-statement kernel catches `X∧¬X` only when
  the clauses differ by an *explicit* `negated` flag; a contradiction carried by distinct **antonym
  words** ("the door is open" vs "…closed"; "a is equal to b" vs "…different from b" *without*
  not/no/never) compiles to geometrically distinct predicates (cos ~0.30, below the 0.90 alias
  threshold) and slips through. The `TKZip` layer carries no word labels, so this needs a **TKLLC
  word-level antonym signal** (the column-read primitive lives there, not in the zip) — and note
  antonyms also measure as *similar* geometrically. Same deferred class as the alive/dead case; this
  **supersedes** the old "a equals b and a is different from b → INCONSISTENT" verify line.
- **Axiom/theorem `≡1` validity creation guard** — `evaluator_classifyForm` already computes the
  `tautology` flag, but it is not yet wired into the axiom/theorem POST (a trusted relation should fold
  `≡ 1` over all assignments). A follow-up to the contradiction-only evaluator bar.
- **Intrinsic comparison grounding** — `compare(subject, indirect)` for eq/noteq clauses.
- **Trust-weighted grounding + conflict arbitration** (Phase-4 follow-ons; lean on `trusted` + recency).
- **Individual-entity identity** (Mari ≠ Luca; named-entity vectors) — limits inter-statement coreference.
- **`axioms`-collection legacy cleanup** (predates the three-tier model; 1b largely repopulates it).
- **`@-1,0,0` spacetime artifact** — single-entity axis normalization tidy.
- **`recompile` utility** — re-derive the KB from stored `original`s when the parser changes (fast, no
  NLTK/WordNet). Worth adding next time the parser changes materially.
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

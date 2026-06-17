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

## 🔭 Next (ordered)

1. **Reasoning engine — intra-statement kernel** — validity / self-contradiction on the input's own
   folded form (`X∧¬X`, `X→¬X`, eq/noteq); the **validity check** (an axiom/theorem must fold `≡ 1`);
   produce `INCONSISTENT` + `EvaluatorResult.inconsistency` (where).
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
- **Proper clausal-subject support** ("to err is human"): represent statement-as-subject in the LLC.
- **Negative-quantifier subject rewrite** ("nobody" → generic person/thing; flagged only today).
- **Geometric negation-awareness** in `evaluator_compareContent` (today only the truth path is).
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

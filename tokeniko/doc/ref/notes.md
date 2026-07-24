# tokeniko — design notes & findings

> Consolidated reference: the loose design notes, empirical findings, and parser/compiler quirks.
> Merged from the former plan.md + reasoning-engine-brainstorm.md + parser-compiler-review.md
> (2026-06-25). For *status* see `roadmap.md` / `landed.md` / `parked.md`; for the living test log
> see `test-feedback.md`.

## Contents
- [Phased execution plan](#phased-execution-plan) — historical build phases
- [Reasoning engine — design & empirical findings](#reasoning-engine--design--empirical-findings)
- [Parser / compiler review — quirks, fixes, gaps](#parser--compiler-review--quirks-fixes-gaps)
- [The identity-blindness family](#the-identity-blindness-family-2026-07-19-audit) — the audit + the generalized cure (`role_key`)

---

## Phased execution plan

*(historical — the build order as originally planned)*

> The phased path from today's evaluator to the inconsistency/inference engine. The *why* is
> `VISION.md`; the *design + verified findings* are the [Reasoning engine](#reasoning-engine--design--empirical-findings)
> section below; the concise per-item status is `roadmap.md` / `landed.md`. Order is driven by dependencies, not ambition: each
> phase unblocks the next. The volitional/affective layer stays last, by design.

### Already landed (foundation)

Compilation pipeline (sentence → `TKZip`); three memory tiers + REST (definitions/axioms/theorems) +
stakeholders/memory; fuzzy `[0,1]` operators + `operator_truth`; evaluation = ground vs definitions →
**fold clause truths through the operator tree** → geometric axiom/theorem match → `EvaluatorResult`,
behind `POST /api/v1/evaluate`; order-aware directional operators; the antonym **column-read** primitive
(verified). The geometry/algebra split is settled: **geometry = matching, algebra = inference, logic =
hardwired first axiom, knowledge + behavior = memory.**

---

### Phase 0 — Parser / compiler review & hardening  ✅ DONE *(prerequisite for everything)*

> **Landed** (merged to main): D1 negation as a discrete `TKZipContent.negated` flag (set by the
> compiler from not/no/never/negative-quantifier markers, applied in `evaluator_groundContent` →
> `truth → 1−truth`; verified end-to-end — "I do not think" evaluates false via `/evaluate`); D2
> comparison polarity via the `utils_antonyms` column-read primitive ("different"→negated, "same/equal"
> →affirmative); D3b noun-complement infinitive binding ("ability to roar" → "cat roar"); plus the
> `util_normalizeGloss` helper. **Deferred to a later parser-level pass:** D3a relative-clause matrix
> subject ("the man who loves Mary runs") and purpose-infinitive binding ("...to fly" → "airport fly")
> — both originate in the Stanza parse / `parser.py` root+nsubj selection. Full write-up: the
> [Parser / compiler review](#parser--compiler-review--quirks-fixes-gaps) section below. The items below are the original spec, kept for reference.
>
> **Also landed (language→logic layer):** **anchor-mechanism unification** — one semantic-native
> resolver (`lib/llc/anchors.py`) replacing the three ad-hoc "surface word → category" mechanisms
> (lemma lists / spaCy similarity / Mongo `$vectorSearch`); nearest-of-anchors with a per-category
> backend + antonym polarity-guard + in-memory caching; seven semantic consumers migrated; verified by
> a golden-baseline diff (1 intended delta). See roadmap Landed #16.

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

### Phase 1 — Knowledge bootstrap (the inference substrate)

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

### Phase 2 — Word-sense disambiguation (use-time accuracy)

Upgrade sense selection from "POS + most-frequent" to **POS-prune → context-centroid (sense family) →
gloss/Lesk overlap (break near-ties) → ask on low margin**. Joint/iterative if needed (context words
are themselves ambiguous: bootstrap with frequency sense, then refine). Reuses the existing cosine /
matching machinery.

> **Hardening landed** (with inter-statement Slice 1): a **frequency-prior guard** in
> `parser_disambiguateSense` — when Lesk gives no clear winner AND the context-centroid is not confident
> (below an absolute floor or within a margin of the runner-up), default to the most-frequent sense
> (smallest WordNet sense number, query-word lemma preferred) instead of a low-confidence centroid guess.
> Fixes "a cat is a X" → `cat.n.01` (was `cat.n.03`/`guy.n.01`); the Lesk-driven bank finance-vs-river
> cases are preserved. (Contextual WSD for genuinely ambiguous heads with no context — e.g. "plant" →
> factory — remains a deeper follow-up; see roadmap Parked.)
**Verify:** the validated cases — animal-context → `cat.n.01`, person-context → `guy.n.01`; a genuine
tie raises `[eval:ambiguous]` rather than guessing.

### Phase 3 — Reasoning engine: intra-statement kernel  *(slice of roadmap #1)*

> **Landed:** implemented as `evaluator_classifyForm` in `lib/llc/evaluator/e_consistency.py` — atoms
> clustered by geometric similarity, crisp `{0,1}` enumeration re-folded through `_fold_statement`,
> short-circuiting `evaluator_evaluateStatement` to `INCONSISTENT` on a contradiction. **Contradiction-only
> bar:** only genuinely unsatisfiable forms flag, so `a eq b imply a noteq b` (≡ `IMPLY(x, 1−x)`, true when
> a≠b) stays RESOLVED — this **supersedes** the old "→ INCONSISTENT" verify line below. **Evaluator-only:**
> the `tautology` flag is computed but not yet wired into axiom creation (the `≡1` guard is a follow-up).
> Explicit-negation contradictions (`X∧¬X` via the `negated` flag) are detected; **lexical-antonym**
> contradictions (open/closed, equal/different without not/no/never) are **deferred** — the zip layer has
> no word labels, so they need a TKLLC word-level antonym signal.
>
> **Also landed (extending the kernel):** (F1) **reflexive-identity hardwiring** — the compiler flags an
> identity-comparison clause whose subject and one operand corefer (`reflexive` bool on
> `TKLLCContent`/`TKZipContent`, set via `compiler_isReflexiveIdentity`/`compiler_isIdentityComparison`);
> `evaluator_classifyForm` then PINS the reflexive leaf to a hardwired constant (`a=a → 1`, `a≠a → 0`),
> so "a thing is not equal to itself" → INCONSISTENT and "…equal to itself" → tautology. (F2)
> **`imply`/`entail` → IMPLY** — a matrix `imply`/`entail` (`_IMPLICATION_VERBS`) with two CCOMP
> complements compiles to `IMPLY(antecedent, consequent)` (`compiler_implicationOperands`, dropping the
> "implies" leaf + `THAT` attitude), so a real implication folds `IMPLY(1,0)=0` → INCONSISTENT for the
> right reason — the earlier attitude-modulation workaround was **REVERTED** in `_self_truth`.
> **Believe/know semantics settled** (logic-is-sacred): "I believe &lt;false&gt;" is satisfiable (not
> flagged; `THAT` shields it), "I know &lt;false&gt;" is inconsistent (knowledge is factive).
> **Limitation:** `imply`→IMPLY fires only when Stanza roots `implies` as the matrix verb; for some
> lexical content Stanza mis-roots it to `parataxis` and it falls back to the old structure (still correct
> answer) — a Stanza-upstream issue, same class as the parked D3a.

The self-contained validity / self-contradiction check on the input's own folded form, no KB chaining:
`X ∧ ¬X`, `X → ¬X`, `eq/noteq` over shared operands. Add the **validity check** (an axiom/theorem must
fold to `≡ 1` over all operand assignments — `min == 1`), produce `status = INCONSISTENT` +
`EvaluatorResult.inconsistency` (the offending form), and use the **antonym primitive** as the negation
signal alongside `noteq = 1−eq`.
**Verify:** `a eq b imply a noteq b` → INCONSISTENT / rejected as an axiom; consistent forms unaffected.

### Phase 4 — Reasoning engine: inter-statement inference  *(the rest of #1)*

> **Slice 1 landed** (see roadmap Landed "Inter-statement inference — Slice 1"): **taxonomic is_a
> grounding + refutation** over the `relations` graph — `evaluator_evaluateStatement` (injected
> `relations=` reader) grounds a copular "X is a Y" clause by subsumption (`subsumes(obj, subj)` →
> truth ~1) and refutes it by **tiered, conservative ontological disjointness**
> (`disjoint(subj, obj)` → truth ~0), pure graph logic in `lib/llc/evaluator/e_relations.py`. The
> verdict stays **RESOLVED** (truth ~1 / ~0) — refutation is *not* `INCONSISTENT` (that stays the
> intra-statement `X∧¬X`) — with the premise chain in the new `EvaluatorResult.derivation`. Enabled by
> the **sense-bridge** (`TKDictionary.sense` → `TKLLEntity.sense` → `TKZipContent.senses`, role→sense)
> and the **WSD frequency-prior** (Phase 2). Verified: "a cat is a mammal" true, "a cat is a plant"
> refuted, "a cat is a dog"/"a cat is a pet" INSUFFICIENT (conservatism). **Slice 2** (the remainder):
> full forward-chaining over axioms/theorems, the other relations (part_of/entails/attribute),
> quantifiers, chaining termination/cycles, deeper coreference.

The full engine: **soft-unification** (similarity + Phase-2 WSD + memory coreference) joins input
clauses to KB facts; **forward-chaining** propagates truth through the operator algebra over the
bootstrapped graph; output the **minimal premise + identification set** (unsat-core) so a verdict is
locatable (logical inconsistency vs divergent knowledge). Branch-disjointness heuristic for plant/animal.
Handle **quantifiers** ("all", "only") and chaining **termination / cycles**.
**Verify:** the cat/lettuce contradiction is derived, with its premise+identification chain reported;
agnostic-and-ask fires only for genuinely un-connected input.

### Phase 5 — Reflective behavior layer  *(later; the seam to the volitional brain)*

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

### Parked / cross-cutting

- **Individual-entity identity (roadmap #2 remainder).** Named individuals (Mari ≠ Luca, "my cat" as a
  specific entity) are geometrically identical today → limits the *matching* layer's individual
  coreference in Phase 4. Concept/type matching and antonymy already work; individuation is the open
  piece (distinct vectors / entity tracking in memory).
- **`axioms` collection cleanup.** The current `axioms` predate the three-tier model; reconcile after
  the engine stabilises (Phase 1 will largely repopulate it anyway).
- **Physics constants.** The t-norm / implication choice (Gödel vs Łukasiewicz vs product) is the only
  semi-arbitrary modeling knob — revisit if folded truths feel wrong.

---

## Reasoning engine — design & empirical findings

> **Status: design & findings (empirically verified this session).** Captures the design conversation
> and the live test results that grounded it. The phased **execution plan is the
> [Phased execution plan](#phased-execution-plan) section above**; the concise tactical roadmap is
> `roadmap.md`; the north star is `VISION.md`.

### The starting question

Roadmap #1 asks tokeniko to detect **logical inconsistency** — e.g. the form `(A eq B) IMPLY (B noteq
A)` should come out false/illegal. How?

### The core hunch (kotekino) — and why it holds

**Inconsistency is a property of the hardwired operator algebra; you compute it, you don't store it.**
Because the operators are fixed truth-functions, the validity of a form is decidable by evaluating it
over its operand variables. You never need an inconsistent axiom sitting in memory to "notice" the
contradiction — it surfaces by itself.

Worked example: `a eq b` grounds intrinsically as `X = compare(a, b)`, and `a noteq b = 1 − X` (the
complement is **algebraic**). So `a eq b IMPLY a noteq b` = `IMPLY(X, 1−X)`. With Gödel implication
that is `1` only when `X ≤ 0.5`, and `1−X (<1)` when `X > 0.5` → **not a tautology** → it cannot be a
valid axiom.

### Key refinements that came out of it

1. **Logical negation ≠ semantic antonymy.** The early worry that "inconsistency needs antonym
   vectors (roadmap #2)" was aimed at the wrong target. `noteq = 1 − eq` and `NOT = 1 − x` are
   **hardwired algebra**, not word-geometry. So *logical* inconsistency does **not** need #2. #2 only
   limits the **matching** layer (see below), specifically **individual** identity.

2. **Validity check, not point-sampling.** An axiom/theorem is valid iff its folded truth is `≡ 1`
   for *all* operand assignments → test `min over assignments == 1`, **not** a single sample at
   `X = 0.5` (which is fragile exactly at the Gödel `≤`/`<` boundary). For `IMPLY(X, 1−X)` the min is
   `0` at `X = 1`, so it fails validity unambiguously. This is what rejects admitting
   `a eq b imply a noteq b` as an axiom.

3. **It only fires among LINKED truths.** Two independent clauses (free variables) are always
   satisfiable — nothing surfaces. A contradiction needs the clause truths *coupled*. eq/noteq couple
   for free (shared operand pair → `X` and `1−X`). The general case couples through a **chain of
   definitions/axioms**.

4. **The linchpin moved — from "detect eq/noteq" to "connect clauses through the KB".** Example:
   `A = "all felines are carnivores"`, `B = "my cat eats only lettuce"`. On their own, A and B are
   independent 0.5's — with empty memory tokeniko *correctly* finds no inconsistency. Add bridging
   knowledge ("carnivores eat animals", "a cat is an animal", "lettuce is a vegetable", "a vegetable
   is not an animal") and a linked path appears: cat → carnivore → eats animals; lettuce → not animal;
   "eats only lettuce" ⟹ "eats no animals" ⊥ "eats animals". *Now* the algebra surfaces it. That
   chaining is **forward inference / resolution**.

### The architecture this reveals

- **geometry = soft unification (matching).** The vectors only decide *what connects to what* (is the
  input's "cat" the KB's "cat"? does "my cat" corefer to an entity in memory?). Approximate, fallible.
- **algebra = inference (truth propagation).** The hardwired operators propagate truth along the
  matched edges and surface contradictions. Sound, exact.
- Geometry never "understands"; it only finds matches. Operators do the reasoning.

**"Equality is tricky" = subject/entity matching**, and it is inherently a **similarity + memory**
problem, not a logic problem. Two flavors at different maturity:
- **concept/type** equality ("cat" ⊂ "animal") → dictionary vectors, works today;
- **individual** equality ("my cat" = a specific entity; Mari ≠ Luca) → leans on memory/coreference
  **+ roadmap #2** (named individuals are geometrically identical today).

**Verdicts are relative to tokeniko's realm.** Output the **minimal premise + identification set**
behind a contradiction, so disagreement is *locatable*: shared premises → genuine logical
inconsistency; rejected premise → just divergent knowledge. Reliability is bounded by the *matching*
layer (its confidence travels with the verdict), never by the logic (always sound).

### Empirical findings (verified live this session)

- **The dictionary is an explicit, interpretable semantic** (not a black-box embedding): `TKBaseDoc`
  = 2925 Oxford-3000 axes (`scripts/base.py`); `TKDictionaryDoc` = Moby Word List projected **per
  sense** through WordNet against those axes (`scripts/dictionary.py`, ~197k sense-vectors). All
  meaning comes from the WordNet projection; Moby supplies only the token list. See memory
  `dictionary-semantics` for the full provenance.
- **Pairwise cosine encodes relatedness, not opposition.** Measured: antonyms are NOT opposite —
  love/hate +0.86, rich/poor +0.76, good/bad +0.41, the rest ~0; synonyms are weak too (big/large
  0.17). The space is sparse/near-orthogonal. → semantic antonymy is **knowledge**, not geometry; this
  is the root of "different from itself ≈ 0.79".
- **BUT antonymy IS recoverable as a primitive — the `−1` is buried, not lost.** `antonyms(W) =
  { X : base[X][idx(W)] < 0 }` — read the negative entries of W's column (equivalently: search base
  with a vector that is 0 except `−1` on W's own axis). Verified clean: love→hate,
  good→{bad,badly,worse,ill,worst}, hot→cold, open→{shut,closed,…}, same→different, buy→sell,
  strong→weak. **Sense-scoped.** Limit: only WordNet-curated pairs (sparse); everything else stays
  memory-knowledge.
- **Word-sense disambiguation by context centroid works for the coarse cut.** POS prunes first, then
  the sense closest to the sentence's content-word centroid wins. Verified: animal-context → cat.n.01
  (+0.29, wide margin); person-context → guy.n.01 (+0.79). BUT near-synonymous senses tie (guy.n.01
  0.79 vs cat.n.03 gossip 0.76). → layered WSD: **POS-prune → centroid (picks the family) → gloss/Lesk
  overlap (break near-ties; glosses are stored) → ask on low margin (`[tokeniko:ask]`)**. Today the
  pipeline does only POS + most-frequent sense (`parser.py` `find_one`, no context) — that's the upgrade.
- **Gloss-derived definitions compile cleanly when sentence-shaped.** `"a cat is a feline mammal"` →
  `([a] cat be [a,feline] mammal)` (clean, 1 clause); `"a carnivore is an animal that feeds on flesh"`
  → 2 clauses (`is-a animal` + `feeds-on flesh`); a raw gloss *fragment* mangles (`no ability to roar`
  → garbage). → normalize glosses to `"a ⟨word⟩ is ⟨gloss⟩"` before compiling; relative-clause /
  infinitive / fragment handling is the Phase-0 parser review.

### Knowledge bootstrap — the inference substrate (kotekino)

The inference engine's bottleneck is *connecting clauses through the KB*. WordNet is a ready-made,
curated, humongous source of exactly that, with **two complementary layers**:

1. **Structured relations → atomic triples, no NL parsing (the reliable skeleton).** `hypernyms()`
   (is-a: `cat → feline → carnivore → mammal → animal → organism`), `meronyms()` (part-of),
   `lemma.antonyms()` (the column-read), `entailments()`, `attributes()`. Harvest directly into atomic
   facts per sense — zero parser noise, sense-scoped. Gives **branch-disjointness** for free:
   `cat→animal` vs `lettuce→plant` are separate branches under "organism", so "X is a plant" ⊥ "X is an
   animal" is derivable from the tree (heuristic — WordNet allows multiple inheritance, so a
   high-confidence default an explicit axiom can override).
2. **Glosses → atomic property facts via the compiler (the flesh).** The properties the taxonomy
   misses ("carnivore *eats* flesh", "cat *has* fur"). Decompose each gloss into **atomic single-clause
   facts** by taking the compiled gloss's **leaf clauses** — needs the parser's **subject re-binding**
   (each clause's subject → the headword), the Phase-0 review's crux.

Both **decomposed to atomic single-clause facts, deduped into a shared graph** (thousands of senses
share "is a mammal"/"is an animal" — that convergence is what makes chains connect). **Routing:**
1-clause → `definitions`; multi-clause → `axioms`. Negative atoms ("cat lacks roar") are first-class
(contrapositive: *roars ⇒ not a cat*). **Scale:** millions of atoms → start from a **core vocabulary
subset** (the 2925 base + immediate neighborhood) and grow. **Re-compilable:** every parser refinement
upgrades the whole KB by re-ingesting.

### The boundary principle (the "first axiom")

- **Hardwired = logic.** The operator truth-functions + the procedure that applies them (ground →
  soft-unify → fold → validity-check). Inviolable — tokeniko's *self*. Logical properties **emerge**
  from the operators (`EQ` symmetric by construction; `X ∧ ¬X` folds false) — never stored.
- **Memory = everything contingent.** Knowledge (facts, domain rules) **and** behavior/policy.
  Editable, learnable, per-stakeholder, disagreeable.

### Behavior as memory (later)

Tokeniko's policy can also be memory rules over reserved **reflective tokens**:
`[eval:inconsistent] IMPLY [tokeniko:speakup]`, `[eval:unknown] IMPLY [tokeniko:ask]`. SOAR/ACT-R
lineage. Likely hooks already present: the `imperative` field on `TKZipContent` (a directive's folded
value = activation, not truth) and the `brain` daemon as the perceive → evaluate → act loop. Mechanism
stays hardwired (action-dispatch table, injecting `[eval:*]` tokens, an action **allowlist**); policy
lives in memory. This is the seam where the future volitional / emotive-intuitive layer plugs in.

### Risks to handle

- **Termination / cascades** in chaining and in action firing (depth bounds, loop control).
- **Conflict resolution** when multiple rules fire (highest activation? trust-weighted? most-specific?).
- **Trust / safety** of editable logic+behavior → lean on the `readonly` / `trusted` tiers, the
  **validity check** (gates what may become an axiom), and an **action allowlist**.
- **Physics constants**: the few semi-arbitrary modeling choices (t-norm / implication: Gödel vs
  Łukasiewicz vs product).

### Staging

1. **Intra-statement kernel** — validity / self-contradiction on the input's own folded form
   (`eq/noteq`, `X ∧ ¬X`, `X → ¬X`). No KB chaining. Tractable now; builds the operator-validity core.
2. **Inter-statement** — soft-unification + forward-chaining over the KB, with the minimal-unsat-core
   output. (1) is the degenerate single-step case of (2).

### Open decisions (still to settle)

- **Representation of comparison relations.** `EQ`/`NOTEQ` exist in the operator enum but the compiler
  never emits them; "equal"/"different" compile as predicate words. To make the eq/noteq algebra fire,
  comparison/identity clauses likely need to become `EQ`/`NOTEQ` **operators** with **intrinsic
  grounding** (`compare(operands)` / `1 − compare`), instead of definition-matched declaratives.
- **Negation representation** — observed negation is inconsistent: "do not jump" got absorbed into the
  clause vector (no `NOT` op), "no ability" became a `[no]` property. The reasoning engine needs
  negation to be **recoverable** (a polarity flag / `NOT` op / the antonym primitive), or `noteq = 1−eq`
  can't fire. This is the **linchpin of the Phase-0 parser/compiler review**.
- **Quantifiers** — "*all* felines", "*only* lettuce" are not truth-functional connectives; they need
  binding/scoping. "only" is load-bearing in the cat example.
- **Build order** — resolved: see the [Phased execution plan](#phased-execution-plan) section above (Phase 0 parser/compiler review →
  Phase 1 knowledge bootstrap → Phase 2 WSD → Phase 3 intra-statement kernel → Phase 4 inter-statement
  inference → Phase 5 reflective behavior).

---

## Parser / compiler review — quirks, fixes, gaps

Phase-0 hardening of the parser/compiler so a compiled clause is reasoning-ready. Three locked
decisions implemented (negation as a discrete signal; comparison polarity via the antonym primitive;
subject re-binding), plus two mechanical helpers. This doc records the confirmed quirks, the fixes
(files + functions), the regression probes, and the remaining gaps.

> **Runtime-verification caveat.** This sandbox **blocked execution of the project Python
> interpreter** (every `python -c`/script invocation that imports `lib` was permission-denied) and
> blocked `git add`/`git commit`. So the numbers below are the **expected** results from static
> analysis of the data flow, not freshly reproduced figures. A self-contained probe that prints the
> actual before/after is committed at **`doc/_phase0_regression.py`** — run it to confirm:
> ```
> cd <WORKTREE>/tokeniko && PYTHONPATH=$(pwd) <venv>/bin/python doc/_phase0_regression.py
> ```
> (it asserts `lib.__file__` is inside the worktree on the first printed line).

---

### Decision 1 (PRIORITY) — negation as a discrete, recoverable signal

#### Confirmed quirk
`[not]/[no]/[never]` render in `decompiler_raw` as properties, but they vanish from the numeric
`TKZip`: the predicate vector of "I am not happy" was reported identical (cosine 1.000) to "I am
happy". The legacy `_PROP_BASE_ADVMOD_ANCHORS["not"] = -1` *intends* to flip the entity vector for an
advmod "not", but in practice it does not fire reliably (the "not" advmod does not clear the
`$vectorSearch` ≥ 0.85 anchor gate against the dictionary), so the negation is simply lost. The
evaluator reasons over `TKZip`, so it could not see negation **at all**.

#### Fix — a discrete clause-level flag (not geometry)
| File | Function / change |
|---|---|
| `lib/core/tkzip.py` | `TKZipContent`: added scalar `negated: bool = False` (dims untouched). |
| `lib/core/tkllc.py` | `TKLLCContent`: added `negated: bool = False` (negation is first known when flattening to LLC). |
| `lib/llc/constants.py` | `_NEGATION_MARKERS = {not, no, never, n't, nor, neither}`, `_NEGATIVE_QUANTIFIERS`. |
| `lib/llc/compiler/c_statements.py` | `compiler_entityToken`, `compiler_propertyIsNegation`, `compiler_contentIsNegated` (scan every role's properties — `not`/`never` are advmod on the predicate, `no` is det on the object — plus negative-quantifier subjects); set `mainContent.negated` right after the clause is built (before coordinate cloning, so deep-copies inherit it). |
| `lib/llc/compiler/c_zip.py` | `compiler_zipContent` carries `negated=content.negated` into `TKZipContent`; `compiler_zipGetEntityVector` now **skips** negation-marker properties when folding vectors, so the role vector keeps the *affirmative* meaning and the legacy `-1` flip can't double-apply. |
| `lib/llc/evaluator/e_truth.py` | `evaluator_groundContent` returns `1.0 - truth` when `content.negated`. The truth-fold in `e_statement` then propagates negation through the operator tree for free. |

**Why a flag, not the `-1` geometry flip:** the locked decision. The geometry compares the
*affirmative* meaning (so "not happy" still geometrically resembles "happy" — same topic), and the
discrete flag carries the polarity. This is recoverable, inspectable, and composes cleanly with the
operator-tree truth fold.

#### Regression (expected)
| input pos / neg | `negated` pos→neg | predicate cos(pos,neg) | truth(neg \| def=pos) |
|---|---|---|---|
| "I am happy" / "I am not happy" | False → **True** | **≈1.000** (affirmative geometry preserved by design) | ≈ `1 − truth(pos)` |
| "I run" / "I do not run" | False → **True** | ≈1.000 | ≈ `1 − truth(pos)` |
| "I have money" / "I have no money" | False → **True** | ≈1.000 | ≈ `1 − truth(pos)` |

The key signal is **`negated` flipping False→True** and the **truth flipping `t → 1−t`**. The
predicate cosine staying ≈1.000 is now *intentional* (negation lives in the flag, not the vector),
not the bug it was before (before: invisible; after: visible via the flag + truth flip).

#### Gaps (documented, not blocking)
- **Negative quantifiers** ("nobody runs"): best-effort — clause is flagged `negated`, but the
  subject is left as the bare quantifier token. `# TODO Phase-0 gap` in `compiler_contentIsNegated`:
  rewrite "nobody"→generic person/thing so the grounding geometry matches "a person runs".
- **Geometric negation-awareness** in `evaluator_compareContent` is **out of scope** (Phase-3
  follow-up). Today only the *truth* path (`evaluator_groundContent`) is negation-aware; the
  geometric comparison still compares affirmative meanings.

---

### Decision 2 — comparison polarity via the antonym primitive (no new operators)

#### Confirmed quirk
"a cat is different from a dog" compiles as predicate-adjective + indirect operand
(`cat be different from dog`), **not** an EQ/NOTEQ operator. Operands are subject + indirect. There
was no signal distinguishing "same" from "different".

#### Fix — antonym column-read + reuse the negation flag
| File | Function / change |
|---|---|
| `lib/llc/utils.py` *(moved here from the former `lib/tkll/functions.py`, refactoring `bd974d4`)* | `utils_antonyms(word) -> set[str]`: the **column read** `{ X : base[X][idx(word)] < 0 }` over `TKBaseDoc` (locate `word`'s axis `index`, then a projected `$match {vector.<idx>: {$lt: 0}}` aggregate — no full 2925-dim rows pulled). Plus `utils_isAntonymOf(word, anchors)` (read symmetrically). |
| `lib/llc/constants.py` | `_COMPARISON_AFFIRMATIVE = {equal, same, alike, identical, similar}`. |
| `lib/llc/compiler/c_statements.py` | `compiler_negativeComparisonWords()` (union of the affirmative anchors' antonym columns, cached once per process) + `compiler_isNegativeComparison(content)`; OR-ed into `mainContent.negated`. |

So `different`/`unlike` (antonyms of `same`/`equal`, per the verified column read) → `negated=True`;
`same`/`equal` → affirmative. Polarity is decided by the **primitive**, not a hardcoded list.
The operands stay subject + indirect.

#### Intrinsic grounding — explicitly deferred (hook only)
`compare(subject, indirect)` (does the geometry of subject vs indirect actually agree/disagree?) is
the **reasoning engine's job (Phase 3)**. Decision 2 only sets *polarity*; the documented hook is the
`negated` flag on a comparison clause whose operands are subject + indirect.

#### Regression (expected)
| input | `negated` |
|---|---|
| "a cat is the same as a dog" | False |
| "a cat is equal to a dog" | False |
| "a cat is different from a dog" | **True** |

`utils_antonyms("same")` should include `different`; `utils_antonyms("equal")` should include
`{different, unequal, ...}` (sparse, WordNet-curated).

---

### Decision 3 — subject re-binding

#### 3b. Noun-complement infinitive — **FIXED** (fully traced)
**Quirk:** "the cat has no ability to roar" → "(... ability) ... (ability roar)". The infinitive
"to roar" is an adnominal modifier of the object "ability"; `compiler_resolveImplicitSubject` applied
**object control** and injected "ability" (the matrix direct object) as the infinitive's subject.

**Fix** (`lib/llc/compiler/c_subordinates.py`): `compiler_resolveImplicitSubject` now takes the
governing reference `ownerRef`. When the subordinate is governed by a **non-predicate** reference
(i.e. it modifies a matrix object/indirect **noun** — an adnominal infinitive), the implicit subject
is bound to the **matrix subject (the bearer)**, not the governing noun. Verb-control infinitives
(subordinate governed by the predicate — "I want to run", "I told her to go") are unchanged and keep
standard subject/object control. Call site passes `ownerRef=reference`.

**Expected:** "the cat has no ability to roar" → `(the cat has no ability) ... (cat roar)`, with the
matrix clause additionally `negated` (the "no" determiner — Decision 1). "I want to run" still →
`tokeniko/I run` (regression preserved).

#### 3a. Relative-clause matrix-subject mis-binding — **ANALYZED, NOT shipped (no safe blind fix)**
**Quirk (reported):** "the man who loves Mary runs" → "...(Mary run)" (matrix verb bound to the
nearest noun, not "man").

**Analysis:** At the **compiler** level the binding is already correct — `parser_parseSentence`
selects the matrix `nsubj` ("man") from the *root's direct children*, and
`compiler_resolveRelative` only rewrites the relative pronoun ("who"→"man") inside the relative
clause; it never touches the matrix subject. So the mis-binding, if reproduced, originates in the
**Stanza dependency parse / `parser.py` root+nsubj selection** (e.g. the matrix verb attaching as the
relative clause, or "Mary" surfacing as the root's nsubj), which I could **not observe** because the
sandbox blocked running the pipeline. Shipping a blind `parser.py` change risks regressing the clean
relative-clause cases (explicitly forbidden by the guardrails), so 3a is left **unmodified** with
this documented analysis. **Next step:** run `doc/_phase0_regression.py`, read the actual dependency
parse for this sentence (`parser_diagram` / `nlp_stanza` dep labels), and target the exact
attachment — the fix belongs at root/nsubj selection in `parser_parseSentence`, not in the flat
compiler.

---

### Mechanical items

- **Gloss/fragment normalization helper — added.** `lib/core/utilities.py`:
  `util_normalizeGloss(word, gloss)` wraps a bare gloss fragment into `"a <word> is <gloss>"`
  (strips a leading article on `word`, picks `a`/`an` by vowel heuristic) so Phase-1 ingestion can
  parse glosses as clean defining clauses. Helper only — no ingestion here.
- **Stray `@-1,0,0` spacetime artifact in `decompiler_raw` — NOT touched.** It is a degenerate-axis
  *normalization* artifact (a lone entity normalized to -1 on a space axis), not a pure decompiler
  formatting bug; a safe fix means adjusting `c_spacetime` normalization for single-entity scenes,
  which risks regressions and is deferred. Noted as remaining.

---

### Files touched (summary)
- `lib/core/tkzip.py`, `lib/core/tkllc.py` — `negated` scalar field (Decision 1).
- `lib/llc/constants.py` — negation markers, negative quantifiers, comparison affirmatives.
- `lib/llc/compiler/c_statements.py` — negation + comparison-polarity detection; set `negated`.
- `lib/llc/compiler/c_zip.py` — carry `negated`; skip negation markers in vector fusion.
- `lib/llc/evaluator/e_truth.py` — flip grounded truth on `negated`.
- `lib/llc/utils.py` (formerly `lib/tkll/functions.py`) — `utils_antonyms` (column read) + `utils_isAntonymOf` (Decision 2).
- `lib/llc/compiler/c_subordinates.py` — noun-complement infinitive bearer binding (Decision 3b).
- `lib/core/utilities.py` — `util_normalizeGloss` (Phase-1 helper).
- `doc/_phase0_regression.py` — runnable before/after probe (NEW).

### Remaining gaps / TODOs
1. **Decision 3a** (relative-clause matrix-subject) — needs the live dependency parse; fix in
   `parser.py` root/nsubj selection. (analyzed, not shipped)
2. **Negative quantifiers** — rewrite "nobody"→generic person/thing (flagged today only).
3. **Geometric negation-awareness** in `evaluator_compareContent` — Phase 3.
4. **Intrinsic comparison grounding** `compare(subject, indirect)` — Phase 3.
5. **`@-1,0,0` spacetime artifact** — single-entity normalization tidy.
6. **Live verification** — re-run `doc/_phase0_regression.py` in an environment that permits
   executing the venv interpreter; confirm the negation cos→truth numbers and Decision 2/3b raws.

---

## The identity-blindness family (2026-07-19 audit)

> Requested by the author after two same-day live specimens; the survey so the NEXT bounce is
> recognized on sight and the cure is generalized, not re-derived. Status of the individual
> leads lives in `roadmap.md` §2 — this is the reference map.

**The disease, stated once.** tokeniko's symbolic layer has exactly two kinds of referent, with
disjoint keys: a CLASS keys by WSD sense (`cat.n.01`, in `TKZipContent.senses`) and an
INDIVIDUAL keys by identity uid (`tokeniko`, `mari@discord:…`, in `TKZipContent.identities`) —
the identity-bridge design (an individual's 2925 vector is an honest type centroid, never a
referent key). Any code that reads only `senses.get(role)` is therefore blind to half the world,
and the failure is SILENT: an honest-looking IDK or a quiet non-match, never an error — which is
why every specimen so far surfaced LIVE, not in tests.

**Two distinct failure modes** (both must be checked when auditing a site):
1. **Key-blindness** — matching/dedup/lookup reads the sense and misses the uid (the
   reduct-answer key: the ghost «so I am a mammal» was unmatchable by ANY answer).
2. **Source-blindness** — the knowledge source itself differs by kind: classes → the WordNet
   is_a graph; individuals → KB facts (axioms/theorems keyed by uid). A graph-walk path that
   lacks the KB-facts branch answers IDK for individuals even when the fact is stored
   («what are you?» → IDK despite «I am a software»).

**Confirmed blind (the queue — status in roadmap §2):**
- `e_wh_solve` what-branch (PREDICATE gap): sense-only is_a walk; identity subjects → IDK.
  Observed live 2026-07-18 («what are you?», 4×). Both failure modes at once.
- `e_wh_solve` who-branch (SUBJECT gap): matches the question's predicate by sense only — an
  identity PREDICATE («who is kotekino?») can never match. Not yet observed; it is the next
  bounce waiting.
- `e_consistency._contrary_pairs`: the antonym-mutex same-subject check compares subject
  senses; two individual-subject leaves both read None and the `si and sj` guard SKIPS the pair
  — the contrary is MISSED entirely (mechanism corrected 2026-07-23: not an accidental pass; an
  individual-subject contrary was simply never flagged). One-line hygiene. CURED 2026-07-23.

**Already identity-aware (the healthy organs — the patterns to copy):**
- `brain/thinking._leaf_net_key` — sense OR uid per role (the 2026-07-19 fix; the family's
  first cure and the template).
- `evaluation_harness.conclusion_key` — identity-FIRST, deliberately («I exist» and «tokeniko
  exists» share it).
- `e_compare` via `evaluator_sameIndividual` — identity overrides geometry on subject/direct;
  the consistency kernel's atom clustering inherits this by routing through compareContent.
- `e_chaining` — individuals enter the closure via membership facts.
- `e_wh_solve` DIRECT + LOCATION branches — both read `identities` alongside `senses` (the
  in-file counterexamples to the blind branches).
- the reductio signature («tokeniko|mammal.n.01|») — identity-native from birth.

**Sense-only BY DESIGN (leave alone; do not "fix"):**
- is_a/part_of graph entry points — WordNet needs a synset; the cure for individuals is the
  KB-facts BRANCH (failure mode 2), never feeding uids to the graph.
- `e_label` (role centroid → word) — semantic by nature; individuals carry honest type
  centroids.
- the P2a geometric abstention — an uid-only subject deliberately compiles sense-less so
  bare-predicate geometry cannot vote on factless self/other claims.

**The generalized cure (the low-hanging fruit, author-endorsed 2026-07-19):** one shared
primitive — `role_key(leaf, role) -> sense | identity uid | None` — homed in the evaluator
(`lib/llc/evaluator/`), consumed by every matching/lookup site (`_leaf_net_key`, the two blind
wh branches, `_contrary_pairs`, and any future role reader). The anchor-resolver principle
applied to role reading: ONE mechanism, no ad-hoc `senses.get(...)` scattered per site. Paired
with the written rule: **every role-reading site consumes the sense-or-identity pair; every
WordNet-graph path carries a KB-facts branch for individuals.** With both in place the family
becomes unbuildable-again.

## The third memory tier — EVENT vs general knowledge (candidate anchors, parked with the roadmap §4.11 entry)

The pipeline is binary — episodic memory item OR timeless theorem — and the missing tier is the
author's articulated distinction (2026-07-21): «what's happening out there» / «what kotekino did»
= EVENT; «are computers minds?» = general knowledge. His holding ruling: until the distinction
exists, moment-anchored claims stay events (remembered, not believed) — the live specimen is the
meta-conversation theorem «kotekino was just answering…» held at 0.9/postable. Candidate
signature already in the zip (definite/named subject + past tense vs GENERIC quantifier +
tenseless present; relative spacetime may already carry the t<0); candidate gate at
`_taught_candidate`. ALL design reasoning deferred until §4.11 is approached — a full design
session when its time comes, not before (the author's explicit ruling).

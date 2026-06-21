# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

> **Read `VISION.md` first.** It is the north star — the end goal and *why* tokeniko exists (a single,
> persistent, logic-first thinking entity; a digital twin of its author; logic hardwired as the first
> axiom, all knowledge and behavior in memory). When a design decision is unclear, `VISION.md` is the
> tie-breaker; this file and the roadmap below are the tactical *how*.

Tokeniko is a **neuro-symbolic NLP engine** that compiles a natural-language sentence into a fixed-size mathematical representation ("the zip") that can be stored in MongoDB as permanent, queryable, geometrically-comparable memory. It combines symbolic parsing (POS tagging, dependency parsing, formal logical operators) with sub-symbolic fuzzy-logic vector fusion (NumPy). See `README.md` for the conceptual overview of the compilation flow.

Note: the git repository root is the **parent** directory (`../`), which also holds `scripts/` (one-off data-ingestion scripts), `atlas/` (local MongoDB data volumes), `data/`, `doc/`, and `tokeniko-public/` (the public website — a self-contained Node/React sibling project, **not** part of the Python package; cloud-deployed against a public MongoDB Atlas — see the topology note below). This directory (`tokeniko/`) is the installable Python package and the FastAPI app.

## Commands

Tasks are defined in `pyproject.toml` via `taskipy` (run from this directory):

- `task api` — run the FastAPI server (`uvicorn api.main:app --reload`) on port 8000
- `task brain` — run the background "mind" daemon (`python -m brain.main`): the thinking, priorities (wishes/ideas), and actions loops
- `task senses` — run the connectors daemon (`python -m senses.main`): the Discord + ATProto/Bluesky listeners (tokeniko's I/O to the outside)
- `pip install -e .` — editable install of the `tokeniko` package (`lib*`, `api*`)

There is **no test suite, linter, or formatter** configured. Files under `scripts/` (in the repo root) are standalone executable scripts run directly with `python scripts/<name>.py`; they populate the MongoDB knowledge-base collections (`base`, `dictionary`, `names`, `places`, `markers`, `properties`) and are not imported by the app.

### Three entry points: `api`, `brain`, `senses`

There are three distinct processes, with different startup requirements:

- **`task api`** (`api/main.py`) — the FastAPI server. Its lifespan calls `parser_init()`, `preparser_init()`, and `decompiler_init()`, which load the spaCy/Stanza pipelines and pull the Ollama models. It needs **all** the dependencies below to start and serve requests. This is where the full compilation pipeline runs.
- **`task brain`** (`brain/main.py`) — the background "mind": three concurrent loops — **thinking** (cycle over memory, derive theorems, validate axioms for inconsistencies), **priorities** (form wishes/ideas — the `TKIdeaDoc` urge layer), and **actions** (carry out what it decides). It only calls `init_io()` (Mongo + Ollama clients), not the spaCy/Stanza pipeline. Needs MongoDB reachable; the loops are scaffolding (the reasoning + volitional layers are still being built — see `doc/roadmap.md`). The brain's first-draft orchestration design (the three loops, queue-priority routing, the `brain_state` continuity singleton) is written up in `brain/README.md` — which now also carries the agreed **#4 plan**: the build order (A HOW-before-WHAT → B the **data model** Ideas/Actions/brain_state → C the **meta-language** of reserved `eval:*`/`tokeniko:*` behavior rules → D the loops' logic), the cooperative-preemption model (brain reacts to input via the memory-trace + throttles; `api`/`senses` are separate processes), and the KB-driven personality. With the consolidation arc (engine/KB/test-gate) done, **#4 (the brain) is the active frontier** — see `doc/roadmap.md` Next #4.
- **`task senses`** (`senses/main.py`) — the connectors daemon (the former stubbed brain listeners, now their own subproject): the **Discord** bot and **ATProto/Bluesky** listener — tokeniko's I/O to the outside world. Concurrent listener tasks; needs MongoDB.

Note also that importing the `lib/llc` pipeline modules (`parser`, `preparser`, `compiler`) loads `en_core_web_lg` at **module import time**, and `translator.py` imports `transformers` at import time — so any process that imports the pipeline needs those models present.

### Embodiment & the public channel (topology)

tokeniko is **embodied on bare metal**: a single, persistent process running with its **local MongoDB** (`:27018`) — one body, one continuous self, finite hardware. It is **not** a horizontally-scaled cloud service. `tokeniko-public/` (a cloud-hosted Node/React sibling project at the repo root, **not** part of the Python package) is its **public window**: a Stream of *transmissions* beside a `/api/mind` **Mind Monitor** whose KPIs mirror the engine concepts (axioms / dictionary base vectors / memory / inferences / refutations / anchors). It runs against a **separate public MongoDB Atlas** in the cloud. The brain's **actions** loop **publishes transmissions** to the public API and **pushes hardware/brain-cycle stats periodically** to that public Atlas — a **one-way publish**: the embodied local db is never bound to or exposed by the public surface. The website is **mock-phase** (`/api/mind` serves a simulated snapshot; the KPI response shape is the contract — wiring the live engine changes only the backend route). It is another **output channel** alongside the `senses` connectors (Discord, ATProto/Bluesky).

### Runtime dependencies (must be running)

The `api` server will not start without these (the `brain` daemon only requires MongoDB):
- **MongoDB** at `MONGO_URI` (default `mongodb://localhost:27018`). Start the local Atlas container with `docker compose up -d` from this directory (`docker-compose.yml` lives here; its volumes mount the repo-root `../atlas/` data dirs). Two logical databases are used: `MONGO_DB_NAME` (knowledge base) and `MONGO_DB_NAME_MEMORY` (memory).
- **Ollama** at `OLLAMA_HOST` (default `http://localhost:11434`), used by the preparser/decompiler. Required models are listed in `lib/llc/constants.py` (`_OLLAMA_MODEL*`, `_OLLAMA_TRANS*`) and auto-pulled on startup.
- **spaCy + Stanza models**: `en_core_web_lg` (`_SPACY_MODEL`) and the `spacy_stanza` English pipeline. Stanza is run with `device="mps"` (Apple Silicon GPU).

Config is read from `.env` via `python-dotenv`. `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` are set so HuggingFace/MarianMT translation models load from local cache only.

## Architecture: the compilation pipeline

A sentence flows through a multi-stage pipeline. The main API entry points (`api/main.py`) — `/api/v1/input`, the axiom/definition/theorem resources, and `/api/v1/evaluate` — chain these stages:

1. **Preparser** (`lib/llc/preparser.py`, optional, `prepare=1`): typo correction (SymSpell), language detection (lingua), and translation to English (MarianMT via `lib/llc/translator.py`) before parsing. LLM-assisted via Ollama.
2. **Parser** (`lib/llc/parser.py`): `parser()` is the entry point. Uses spaCy+Stanza to dependency-parse, then builds a **recursive AST of `TKStatement` objects** (`TKStatements = list[TKStatement]`). Resolves word meanings against the MongoDB dictionary (word-sense disambiguation, `parser_disambiguateSense`, Phase 2: Lesk-first → context-centroid → a **frequency-prior guard** that defaults to the most-frequent sense — smallest WordNet sense number, query-word lemma preferred — when Lesk gives no clear winner and the centroid is not confident), attaches markers/operators, and produces the nested grammatical structure (subject / predicate / direct / indirects, with conjuncts, subordinates, and properties).
3. **Compiler** (`lib/llc/compiler/` package): `compiler_compile()` is the entry point (re-exported from `compiler/__init__.py`). The package is split by section — `c_entities.py`, `c_subordinates.py`, `c_statements.py`, `c_spacetime.py`, `c_zip.py`, the `c_main.py` orchestrator, and `c_state.py` (shared `_entities` map + spaCy `nlp`, reset in place per compile). Two outputs in one pass:
   - **LLC Flat** (`TKLLC`, defined in `lib/core/tkllc.py`): flattens the recursive statements into entities + references for O(1) access, resolves pronouns and implicit subjects, and computes relative spacetime.
   - **TKZip** (`TKZip`, defined in `lib/core/tkzip.py`): the final fixed-size numeric output. Applies fuzzy-logic vector fusion — advmod scalar multipliers (`_PROP_BASE_ADVMOD_ANCHORS`, e.g. "very"=1.5), Min/Max/negation/Gödel-implication operators kept in `[-1,1]`, `tanh` soft-normalization.

   The compiler also emits two reasoning hooks: a matrix verb `imply`/`entail` (`_IMPLICATION_VERBS`) with two CCOMP complements compiles to `IMPLY(antecedent, consequent)` (`compiler_implicationOperands` drops the "implies" predication leaf and its `THAT` attitude); and an identity-comparison clause whose subject and one operand corefer is flagged `reflexive` (the `reflexive` bool on `TKLLCContent`/`TKZipContent`, set in `compiler_evaluateStatement` via `compiler_isReflexiveIdentity`/`compiler_isIdentityComparison`) — the evaluator's `evaluator_classifyForm` then pins a reflexive leaf to a hardwired constant (`a=a → 1`, `a≠a → 0`) rather than grounding it. A clause also carries a `TKQuantifier` (the `quantifier` field on `TKLLCContent`/`TKZipContent`) read off the subject's determiner via `anchor_quantifier` (an EXACT closed-class anchor category: `all/every`→universal, `a/some`→existential, `no/none`→negative, `the/this`→definite, bare→generic); the evaluator's relational grounding applies a quantifier × `is_a`-verdict truth table (`net_flip = NEGATIVE XOR negated` over subsumes=TRUE / disjoint=FALSE). The relational grounding also handles **part_of** (mereology) — `e_relations.relations_is_part_of` over an injected `part_of` reader; `e_statement` recognizes a part-whole claim + its direction ("X is part of Y" / "Y has X", via `_PART_OF_PREDICATES`/`_HAS_PART_VERBS`) and grounds it TRUE if part⊆whole, FALSE by antisymmetry on the reverse edge, else insufficient (conservative — a missing edge never refutes); the whole's sense for "X is part of Y" is surfaced as `predicate_nmod` in `compiler_contentSenses`.
4. **Decompiler** (`lib/llc/decompiler.py`): `decompiler_raw()` renders LLC back to a raw symbolic string; `decompiler_decompile()` (Ollama) polishes it into natural language. Used for debugging and round-tripping.
5. **Memory store**: results are saved as Bunnet documents (`TKMemoryItemDoc`, `TKAxiomDoc`, `TKTheoremDoc`) in the memory DB, tagged with source/target stakeholder IDs and a `MEMChannels` channel.

### Fixed vector dimensions (do not change casually)

These magic numbers are enforced by Pydantic `min_length`/`max_length` constraints throughout `lib/core/`:
- **2925** — semantic vector dimensions (one per base word). Base words and dictionary senses carry a 2925-dim vector.
- **3237** — final per-role tensor in a zip = 300 logical markers + 2925 semantic + 12 spacetime.
- **8** — the spacetime bounds map (`TKZip.map`); spacetime is `[t, x, y, z]` for size/position/velocity.

Changing a dimension means updating the constraints in `lib/core/tk.py`, `tkllc.py`, `tkzip.py` *and* the data already stored in MongoDB.

## API layer (`api/`)

`api/main.py` defines the FastAPI app — only the lifespan and the thin endpoint handlers. Each handler delegates to a `*Service` and wraps the result in `{"status": "complete", "data": ...}` (and `{"status": "failed", "data": repr(error)}` on a write error). Business logic (sentence compilation + Mongo CRUD) lives in `api/services/` (one `*_service.py` per resource: `axiom_service.py`, `definition_service.py`, `theorem_service.py`, `stakeholder_service.py`, `memory_service.py`, `evaluation_service.py`), re-exported from `api/services/__init__.py` so callers can `from api.services import AxiomService`. Request/response (in/out) Pydantic models and the domain-error→HTTP mapping (`_or_http` + per-resource `*_or_http` helpers) live in `api/schemas.py`. Each service is built once in the lifespan (e.g. `app.state.axiom_service = AxiomService(tokeniko, ai_client)`, `app.state.stakeholder_service = StakeholderService()`, `app.state.memory_service = MemoryService()`) and reused per request; services are framework-agnostic (no FastAPI imports).

Routes (all under `/api/v1`):

- **Axioms — full REST resource** (`AxiomService`):
  - `POST /axioms` — compile a sentence (`{"tokens": "..."}`) and store it as an axiom
  - `GET /axioms` — list (summary projection, no `zip`; optional `?archived=` filter)
  - `GET /axioms/{id}` — single (full document, `zip` included)
  - `PATCH /axioms/{id}` — partial update (recompiles if `tokens` is supplied)
  - `PUT /axioms/{id}` — replacement update (recompile + reset flags)
  - `DELETE /axioms/{id}` — delete
- **Definitions — full REST resource** (`DefinitionService`): same shape as axioms — a definition's meaning is now the full compiled `TKZip` (`MEMDefinition.zip`, single **OR** multi clause; all WordNet glosses live here). Migrated from the old single-`TKZipContent` shape; `NotASingleClauseError` is gone (multi-clause is legal). `scripts/migrate_glosses.py` performs the one-time re-home (re-derive existing defs `content`→`zip` + move the gloss-axiom batches into definitions).
  - `POST /definitions`, `GET /definitions` (summary, optional `?archived=`), `GET /definitions/{id}`, `PATCH /definitions/{id}`, `PUT /definitions/{id}`, `DELETE /definitions/{id}`
- **Theorems — full REST resource** (`TheoremService`): derived knowledge (full `TKZip`); no `readonly` flag.
  - `POST /theorems`, `GET /theorems` (summary, optional `?archived=`), `GET /theorems/{id}`, `PATCH /theorems/{id}`, `PUT /theorems/{id}`, `DELETE /theorems/{id}`
- **Stakeholders — list/get only** (`StakeholderService`, read-only):
  - `GET /stakeholders` — list (summary projection)
  - `GET /stakeholders/{id}` — single (full document)
- **Memory — list/get/search/insert, NO update** (`MemoryService`). The `memory` collection is a Mongo **timeseries**, which forbids in-place updates — hence no PATCH/PUT/DELETE; insert is a plain log append (no compilation).
  - `GET /memory` — recent items, newest first (summary projection, no `zip`); optional `?limit=` (default 100)
  - `GET /memory/search` — filter the log (declared before `/memory/{id}` so `search` isn't read as an id): `?from=&to=` (epoch **seconds**, converted to UTC datetimes on `timestamp`; `from` is aliased, the keyword), `?source=` (`sourceId`), `?target=` (`targetId`), `?channel=`, `?limit=` — only the supplied filters apply; newest first
  - `GET /memory/{id}` — single (full document)
  - `POST /memory` — append a log entry (`original`, `sourceId`, optional `targetId`/`channel`/`metadata`)
- Domain errors map to HTTP in `main.py` via the `*_or_http` helpers: invalid-id → 400, not-found → 404. **Contradiction creation guard:** axiom/definition/theorem **create/patch/replace** reject a contradictory FORM — `assert_no_contradiction` (`api/services/validation.py`) runs `evaluator_classifyForm` (with the antonym reader) on the compiled zip and raises `InconsistentStatementError` if the form folds to 0 under every crisp assignment (`X∧¬X`, `a≠a`, antonym-predicate); tautologies AND contingent statements are allowed (logic-is-sacred: a logical falsehood can never be trusted knowledge). The guard lives **outside** `compile_fields` (so `scripts/recompile.py` never chokes on a pre-existing bad row). `create_or_http` (`api/schemas.py`) maps `InconsistentStatementError` → 422.
- **Evaluate — action, not a resource** (`EvaluationService`): `POST /evaluate` (`{"tokens": "..."}`) — compile a sentence and evaluate its truth against tokeniko's knowledge. Grounds each flat clause against the definitions (each definition's `zip` is **flattened into its leaf clauses** in `EvaluationService` — the evaluator still receives a flat `list[TKZipContent]`, unchanged), **folds the clause truths through the operator tree** (fuzzy `[0,1]`, via `operator_truth`), and geometrically matches the whole statement against the active axioms/theorems. Returns an `EvaluatorResult` (`truth`, `status` = resolved/insufficient/inconsistent, `groundings`, `missing`, `relationMatch`, `matchedKind`/`matchedIndex`) plus the resolved `matchedId`/`matchedOriginal`. **Pure — stores nothing.** Loads only active knowledge (`archived=False`; NB theorems default `archived=True`, so the theorem pool is empty until one is promoted).
- **Utils** (debugging; may be removed later): `GET /utils/dict?token=` (similar-token dictionary lookup), `GET /utils/markers?token=` (base-marker lookup), `GET /utils/polish?tokens=` (typo correction), `GET /utils/prepare?tokens=` (full preparse), `GET /utils/translate?tokens=` (translation), `GET /utils/render?tokens=` (HTML dependency diagram).
- **Compiler**: `GET /input?tokens=&output=&prepare=&talker=` — run the full pipeline; returns LLC flat + recursive + raw (+ polished if `output=1`) and stores a memory item. `GET /output?tokens=` — polish a raw LLC string into natural language.

Bunnet gotcha (bit us here): `Document.get(id)` and `find_one(...)` return *query* objects — call `.run()` to execute (`.to_list()` for `find(...)`). `AxiomService._resolve` does `TKAxiomDoc.get(oid).run()`; forgetting `.run()` yields a query object that is never `None` and has no `.save()`/`.delete()`.

## Data model layers (`lib/core/`)

The type system is layered — understand which layer you're editing:

- **`tk.py`** — the recursive/symbolic layer. Pydantic models for knowledge-base entities (`TKBase`, `TKDictionary`, `TKName`, `TKPlace`, `TKMarker`, etc.), the logical operators (`TKOperator`: AND/OR/NOT/IMPLY/CONV/THAT/…), clause types, and the parser's AST (`TKStatement`, `TKFullEntity`, `TKEntityReference`). `TKStatement` holds the `create_subject`/`add_conjuncts`/`add_subordinates` factory logic that builds the tree.
- **`tkllc.py`** — the flat intermediate layer (`TKLLC` and friends): entities + references with relative spacetime.
- **`tkzip.py`** — the final numeric layer (`TKZip`): pure float vectors.
- **`models.py`** — Bunnet (`Document`) wrappers that bind the above models to MongoDB collections. Knowledge-base docs and memory docs are registered separately in `init_io()`.
- **`memory.py`** — memory-domain models (`MEMItem`, `MEMAxiom`, `MEMTheorem`, `MEMStakeholder`, `MEMChannels`). Axioms = trusted ground truths; theorems = derived knowledge.
- **`io.py`** — `init_io()` wires up both MongoDB databases (via Bunnet) and the Ollama async client. `get_tokeniko()` / `get_stakeholder()` fetch-or-create conversation participants.
- **`mappers.py`** (`TKPosMapper`), **`utilities.py`**, **`constants.py`** — helpers and `_ME_UID`/`_ME_NAME` identity constants.

### Pydantic model rebuilds

The recursive models use forward references and **discriminated unions** (`Field(discriminator='entity_type')`). After editing any recursive model in `tk.py`, `tkllc.py`, or `tkzip.py`, the corresponding `Model.model_rebuild()` calls at the bottom of the file must stay in place — they regenerate Pydantic's internal schema. Adding a new entity payload type means adding it to the `EntityPayload` / `LLCItemPayload` union *and* keeping its `entity_type` literal unique.

## Conventions

- Comments and log messages are a mix of **English and Italian**; module headers in Italian are common. Match the surrounding language when editing a file.
- Versioned modules: older implementations are kept alongside (`compilerV1.py`, `markersV1/V2/V3.py`, `scripts/legacy scripts/`). The live "V2" compiler is now the `compiler/` package (was `compiler.py`); `parser.py` (internally "V2") is the live parser.
- `lib/llc/` = the language-compilation pipeline **+ shared utilities** (`lib/llc/utils.py`: the antonym column-read primitive `utils_antonyms` + dictionary/token similarity — moved here from the former `lib/tkll/`); `lib/core/` = data models & IO. `senses/` (a sibling subproject of `lib/`) = the external connectors (Discord, ATProto/Bluesky).
- **Anchor resolver** (`lib/llc/anchors.py`) — the unified "surface word → logical/semantic category" mechanism. Semantic-native: maps ANY input to the **nearest of a small anchor set** (exact-hit fast path → nearest-anchor fallback above a floor) rather than fixed dictionaries, with a per-category backend (dictionary 2925-dim vectors for content words vs spaCy for function words), an **antonym polarity-guard** on polarity-sensitive categories (so "but" never resolves to AND), and **in-memory cached** anchor vectors (no per-call DB). The parser/compiler resolution sites — `parser_ccToOperator` (operators), `compiler_parseMarker` (subordinate types), attitude / comparison / advmod-intensifier / spatial / sequence — resolve **through it** instead of ad-hoc lemma lists, spaCy similarity, or Mongo `$vectorSearch`.
- **`brain/behavior.py`** — the reserved-token **meta-language** (step C): the `eval:*`/`tokeniko:*` dispatch (`behavior_for`/`spawn_ideas_for`/`dispatch_action` + the hardwired `_DISPATCH` registry) over the `behavior_rules` personality table (`MEMBehaviorRule`→`TKBehaviorRuleDoc`); `priorities_phase` consumes it (urge-desc). Seed: `scripts/seed_behavior_rules.py`.
- `parser.py` monkey-patches `torch.load` (`weights_only=False`) to load Stanza models — keep that patch when touching parser imports.

## Roadmap (where the team is heading)

**Memory model — three epistemic tiers** (see `memory.py` / `models.py`):
- **definitions** (`MEMDefinition` → `definitions` collection) — *semantic* statements defining
  tokeniko's vocabulary/rules ("a thing is equal to itself"; "an apple is a fruit with red skin").
  A definition's meaning is the full compiled `TKZip` (`MEMDefinition.zip`, single **OR** multi
  clause) — all WordNet glosses live here. Trusted ground truths, no demonstration. (The "full
  re-home" migration `scripts/migrate_glosses.py` re-derives the old single-`content` defs to `zip`
  and moves the gloss-axiom batches here, leaving `axioms` = genuine relations + rules only.)
- **axioms** (`TKZip`) — relations between definitions/vocabulary via operators ("I think because I
  am") + universal rules/individual facts. Trusted, no demonstration.
- **theorems** (`TKZip`) — knowledge demonstrated from definitions + axioms + the hardwired operator
  math.
- **memory** — the time-series log of inputs/outputs.

All three resources (axioms/definitions/theorems) are full REST resources backed by a `*Service`
in `api/services/`; request/response models + domain-error→HTTP mapping live in `api/schemas.py`
(`main.py` is just lifespan + endpoints).

**Evaluator / math phase** — the `lib/llc/evaluator/` package: `operators.py` (fuzzy operator
truth functions on **`[0,1]`** + `operator_truth(op, a, b)` to combine clause truths + behavioral
operator similarity), `e_compare.py` (geometric comparison: `evaluator_compareContent` /
`evaluator_compareItem` / `evaluator_compareZip`, type-routed indirects via the marker gate),
`e_truth.py` (`evaluator_groundContent`: a clause's truth in `[0,1]` vs the definitions),
`e_statement.py` (`evaluator_evaluateStatement`: ground each clause, then **fold the clause truths
through the operator tree** with `operator_truth` — `A1 IMPLY (A2 AND A3)` → `IMPLY(T1, AND(T2,T3))`
— and geometrically match axioms/theorems → `EvaluatorResult`; it now also takes an optional injected
`relations=` reader and does **relational grounding/refutation** on an is_a clause — subsumption →
true, tiered ontological disjointness → false — writing the premise chain to
`EvaluatorResult.derivation`), `e_relations.py` (pure is_a graph logic: `relations_isa_ancestors` /
`relations_subsumes` / `relations_disjoint` — BFS is_a closure, subsumption, and CONSERVATIVE tiered
ontological disjointness), `e_consistency.py`
(`evaluator_classifyForm` — the intra-statement contradiction kernel: crisp `{0,1}` enumeration over
atom-clustered clauses, pinning `reflexive`-flagged leaves to a hardwired constant; it also detects a
**contrary-predicate contradiction** — two clauses predicating same-subject, antonym-linked predicate
senses ("the cat is alive and the cat is dead") — via an injected `antonyms` reader, modeled as a
mutual-exclusion constraint in the enumeration (forbids the (1,1) corner only, so a disjunction of
contraries stays satisfiable and non-tautological); `e_statement` short-circuits to `INCONSISTENT` on a contradiction). `evaluator_evaluateStatement` gained an `antonyms=` reader (alongside `relations=`/`part_of=`) that feeds this check; `EvaluationService` injects it (relation `"antonym"` over `TKRelationDoc`). `e_chaining.py`
(`evaluator_forwardChain` / `evaluator_chainGround` — the **multi-hop forward-chainer**, priority-2 step c):
given an input it seeds a class closure from the subject's sense (+ is_a ancestors) and, for an individual
subject, from the membership FACTS about that uid; fires **MEMBERSHIP rules** (universal, NOUN predicate —
"all humans are thinkers": subject is_a* S ⇒ subject is_a [predicate class]) to a **fixpoint** to grow the
closure; then applies **PROPERTY rules** (universal, verb/adj predicate — "all carnivores eat meat") whose
subject sits in the closure to derive properties. `evaluator_chainGround` (wired into the `e_statement`
per-clause grounding loop AFTER is_a/part_of, since a verb/adj-predicate clause falls through the is_a
copular grounder) **corroborates** (truth≈1) or **KB-refutes** the input clause with a derivation chain —
a KB-refutation is **RESOLVED truth≈0 + a chain, NEVER INCONSISTENT** (that is reserved for logic violations).
`evaluator_evaluateStatement` gained `rules=`/`facts=`; `EvaluationService` extracts them from the active
axioms (`_extract_rules`: universal-leaf with subject+predicate senses → rule, classified membership/property
by predicate POS; `_extract_facts`: an entity-linked individual leaf with a NOUN predicate → fact). The evaluator is DB-agnostic — the
caller injects definitions/axioms/theorems (and, for the relations graph, a cached `parents(sense)`
reader — see the sense-bridge below). `EvaluatorResult`/`EvaluatorStatus` live in
`lib/core/evaluation.py`. `e_label.py` (`evaluator_assignWord`) assigns the single most
representative dictionary word to a statement — a noun-weighted semantic centroid of the role
vectors → nearest `TKDictionaryDoc` word via `$vectorSearch`. The HTTP entry point is
`EvaluationService` (`api/services/evaluation_service.py`) behind `POST /api/v1/evaluate` — the
DB adapter that loads the active definitions/axioms/theorems and maps the best match to a doc id; it
also injects a cached `parents(sense)` reader backed by the new **`TKRelationDoc`** (the `relations`
collection — `{subject, relation, object, pos}`, synset-keyed, ~150k WordNet
is_a/part_of/antonym/entails/attribute/similar_to triples; registered in `init_io`). The DB-adapter
part of this (load active definitions/axioms/theorems → build readers + forward-chainer rules/facts →
evaluate a ready `TKZip` → map the best match to a doc id) is factored into the **parser-free**
`lib/core/evaluation_harness.py` (`evaluate_zip`), shared by `EvaluationService` (api; adds the
`_compile_zip` parser step on top) and `brain/thinking.py` (the brain stays spaCy/Stanza-free).

**Sense-bridge** — the WSD sense now propagates through the whole pipeline so the evaluator can read
it: `TKDictionary.sense` (e.g. `cat.n.01`) → `TKLLEntity.sense` (set in `compiler_getEntity`) →
`TKZipContent.senses` (a role→sense dict, populated in `compiler_zipContent`). Previously the sense was
dropped at the LLC boundary.

**Identity-bridge** (Slice 3a) — named individuals ("Mari", "Rome", "Google") used to compile to a
ZERO 2925 vector (all collapsing to one point). They now get **two SEPARATE things**: (a) an honest
SEMANTIC vector = their NER **type centroid** (meaning=geometry — `PERSON→person.n.01`,
`GPE/LOC/FAC→location.n.01`, `ORG→organization.n.01`, `NORP→group.n.01`,
`PRODUCT/WORK_OF_ART→artifact.n.01`, `EVENT→event.n.01`; fetched from the `dictionary` collection,
in-memory cached) and (b) a referential **IDENTITY** = a context-scoped uid `name@channel:talker_uid`
(identity=symbolic). The two never mix — the grounded 2925 space stays pollution-free (NEVER a
random/noise vector). Minting is **gated** by NER-type + a real spaCy-lg word vector (parser tokens
come from stanza, which has no vectors, so the `has_vector` gate is checked against the lg `nlp` vocab
via `_parser_hasLgVector`), so OOV gibberish (which spaCy mislabels as GPE) never mints an individual;
a known place still takes the `parser_getPlace` route first (geo-anchored, not an individual). The
bridge MIRRORS the sense-bridge: `TKName.uid/vector/ner` (minted in `parser_getIndividual`, wired into
both PROPN sites as `parser_getPlace(token) or parser_getIndividual(token, _talker) or
TKName(name=...)`) → `TKLLEntity.uid` (set in `compiler_getEntity`; the centroid rides in
`semantic_vector` and is now consumed for `entity_type=="name"` in `compiler_zipGetEntityVector`) →
`TKZipContent.identities` (a role→uid dict, populated by `compiler_contentIdentities`/`compiler_refUid`
in `compiler_zipContent`). An individual is homed in the extended `MEMStakeholder`
(`kind="individual"`, `ner_type`, `vector`, `contextKey`) via `io.upsert_individual` (get-or-create,
idempotent) — called ONLY on storing paths (the `/input` handler walks the recursive parse for
name payloads with a uid), NEVER on `/evaluate` (which stays pure / read-only).
`evaluator_sameIndividual(a, b, role)` is the demonstrable entity-linking primitive: same uid → True,
different → False, either missing → None. `evaluator_compareContent` **consumes** it (#1b): for the
subject/direct roles it overrides the geometric score by identity (same uid → 1.0, different → 0.0, no
uid → geometry), so same-type individuals are no longer conflated ("Mari is happy" ≠ "Luca is happy")
while the same individual is recognized across different claims — propagating through
`compareItem`/`compareZip`/`_best_match` and the consistency-kernel clustering.

**Status & the ordered roadmap live in one place → `doc/roadmap.md`** (the single source of truth:
landed / in-progress / next / parked — keep it current as items land). The phased execution detail is
in `doc/plan.md`, the design + empirical findings in `doc/reasoning-engine-brainstorm.md`, and the
parser/compiler quirks + remaining gaps in `doc/parser-compiler-review.md`.

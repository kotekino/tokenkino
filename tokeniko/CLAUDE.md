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
- `task brain` — run the background "mind" daemon (`python -m brain.main`): one coordinator loop running three phases — thinking, priorities (wishes/ideas), and actions
- `task senses` — run the connectors daemon (`python -m senses.main`): the Discord + ATProto/Bluesky listeners (tokeniko's I/O to the outside)
- `pip install -e .` — editable install of the `tokeniko` package (`lib*`, `api*`)

There is **no test suite, linter, or formatter** configured. Files under `scripts/` (in the repo root) are standalone executable scripts run directly with `python scripts/<name>.py`; they populate the MongoDB knowledge-base collections (`base`, `dictionary`, `names`, `places`, `markers`, `properties`) and are not imported by the app.

### Three entry points: `api`, `brain`, `senses`

There are three distinct processes, with different startup requirements:

- **`task api`** (`api/main.py`) — the FastAPI server. Its lifespan calls `parser_init()`, which loads the spaCy/Stanza pipelines. (The Ollama `preparser_init`/`decompiler_init` calls were RETIRED 2026-07-16 — no local models are pulled or used; the ears are rag1/Claude and the decompile surface is Claude.) This is where the full compilation pipeline runs.
- **`task brain`** (`brain/main.py`) — the background "mind": ONE coordinator loop that, each tick, runs ONE bounded unit of the highest-priority phase WITH WORK — **Actions > Priorities > Thinking** (the reactive path wins; thinking is the background filler) — then cooperatively yields. The three phases: **thinking** (cycle over memory, derive theorems, validate axioms for inconsistencies), **priorities** (form wishes/ideas — the `TKIdeaDoc` urge layer), and **actions** (carry out what it decides). It only calls `init_io()` (Mongo clients + an inert legacy Ollama handle, never called), not the spaCy/Stanza pipeline. Needs MongoDB reachable. The reasoning + volitional layers are BUILT (the Brain v1.1 Unified-KB arc is complete — `doc/landed.md`): thinking evaluates memory + answers questions, KB-wondering forward-saturates the unified KB (definitions/axioms/theorems, trust-tiered, provenance-cascaded) and materializes theorems via the API (sense-pinned — the derivation's senses are pinned into the compiled zip so the NL render round-trip can never corrupt the dedup key). The brain's orchestration design (the single coordinator over the three phases, queue-priority routing, the `brain_state` continuity singleton) is written up in `brain/README.md`: the build order (A HOW-before-WHAT → B the **data model** Ideas/Actions/brain_state → C the **meta-language** of reserved `eval:*`/`tokeniko:*` behavior rules → D the loops' logic), the cooperative-preemption model (brain reacts to input via the memory-trace + throttles; `api`/`senses` are separate processes), and the KB-driven personality. With the reasoning core done, **going-live (the `senses` I/O — Discord private messages first) is the active frontier** — see `doc/roadmap.md` Next.
- **`task senses`** (`senses/main.py`) — the connectors daemon (the former stubbed brain listeners, now their own subproject): the **Discord** bot and **ATProto/Bluesky** listener — tokeniko's I/O to the outside world. Concurrent listener tasks; needs MongoDB.

Note also that importing the `lib/llc` pipeline modules (`parser`, `compiler`) loads `en_core_web_lg` at **module import time** — so any process that imports the pipeline needs that model present. (`preparser.py`/`translator.py` — the retired local machinery — still import SymSpell/`transformers` at import time, but nothing imports THEM since 2026-07-16, so neither loads.)

### Embodiment & the public channel (topology)

tokeniko is **embodied on bare metal**: a single, persistent process running with its **local MongoDB** (`:27018`) — one body, one continuous self, finite hardware. It is **not** a horizontally-scaled cloud service. `tokeniko-public/` (a cloud-hosted Node/React sibling project at the repo root, **not** part of the Python package) is its **public window**: a Stream of *transmissions* beside a `/api/mind` **Mind Monitor** whose KPIs mirror the engine concepts (axioms / dictionary base vectors / memory / inferences / refutations / anchors). It runs against a **separate public MongoDB Atlas** in the cloud. The brain's **actions** loop **publishes transmissions** to the public API and **pushes hardware/brain-cycle stats periodically** to that public Atlas — a **one-way publish**: the embodied local db is never bound to or exposed by the public surface. The website is **mock-phase** (`/api/mind` serves a simulated snapshot; the KPI response shape is the contract — wiring the live engine changes only the backend route). It is another **output channel** alongside the `senses` connectors (Discord, ATProto/Bluesky).

### Runtime dependencies (must be running)

The `api` server will not start without these (the `brain` daemon only requires MongoDB):
- **MongoDB** at `MONGO_URI` (default `mongodb://localhost:27018`). Start the local Atlas container with `docker compose up -d` from this directory (`docker-compose.yml` lives here; its volumes mount the repo-root `../atlas/` data dirs). Two logical databases are used: `MONGO_DB_NAME` (knowledge base) and `MONGO_DB_NAME_MEMORY` (memory).
- ~~Ollama~~ **RETIRED 2026-07-16** (the local-models retirement, author's ruling): no process pulls or calls local models anymore. The machinery stays in code unreferenced (`preparser.py`, `_decompiler_decompile_ollama`, `_OLLAMA_MODEL*` constants) should the local bridge ever be rebuilt. Cloud (Claude Haiku) covers the ears (rag1), the decompile surface, and the outbound voice polish (rag2-out, 2026-07-17: the composed scaffold text gets one verified fluency pass — `POST /voice/verify` consensus — or ships verbatim; anecdotes always verbatim, their register is the point). **ANTHROPIC_API_KEY** in `.env` is the live dependency instead.
- **spaCy + Stanza models**: `en_core_web_lg` (`_SPACY_MODEL`) and the `spacy_stanza` English pipeline. Stanza is run with `device="mps"` (Apple Silicon GPU).

Config is read from `.env` via `python-dotenv`. `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` are set so HuggingFace/MarianMT translation models load from local cache only.

## Architecture: the compilation pipeline

A sentence flows through a multi-stage pipeline. The main API entry points (`api/main.py`) — `/api/v1/input`, the axiom/definition/theorem resources, and `/api/v1/evaluate` — chain these stages:

1. **The translator at the ears** (rag1, `lib/llc/normalizer.py`): escalation-only — a STUMBLING parse gets one Claude Haiku surface-tidying pass, accepted only if the zip-verifier proves meaning preserved. (The old Ollama preparser — `preparser.py`, `prepare=1` — is retired, unreferenced machinery.)
2. **Parser** (`lib/llc/parser.py`): `parser()` is the entry point. Uses spaCy+Stanza to dependency-parse, then builds a **recursive AST of `TKStatement` objects** (`TKStatements = list[TKStatement]`). Resolves word meanings against the MongoDB dictionary (word-sense disambiguation, `parser_disambiguateSense`, Phase 2: Lesk-first → context-centroid → a **frequency-prior guard** that defaults to the most-frequent sense — smallest WordNet sense number, query-word lemma preferred — when Lesk gives no clear winner and the centroid is not confident), attaches markers/operators, and produces the nested grammatical structure (subject / predicate / direct / indirects, with conjuncts, subordinates, and properties).
3. **Compiler** (`lib/llc/compiler/` package): `compiler_compile()` is the entry point (re-exported from `compiler/__init__.py`). The package is split by section — `c_entities.py`, `c_subordinates.py`, `c_statements.py`, `c_spacetime.py`, `c_zip.py`, the `c_main.py` orchestrator, and `c_state.py` (shared `_entities` map + spaCy `nlp`, reset in place per compile). Two outputs in one pass:
   - **LLC Flat** (`TKLLC`, defined in `lib/core/tkllc.py`): flattens the recursive statements into entities + references for O(1) access, resolves pronouns and implicit subjects, and computes relative spacetime.
   - **TKZip** (`TKZip`, defined in `lib/core/tkzip.py`): the final fixed-size numeric output. Applies fuzzy-logic vector fusion — advmod scalar multipliers (`_PROP_BASE_ADVMOD_ANCHORS`, e.g. "very"=1.5), Min/Max/negation/Gödel-implication operators kept in `[-1,1]`, `tanh` soft-normalization.

   The compiler also emits two reasoning hooks: a matrix verb `imply`/`entail` (`_IMPLICATION_VERBS`) with two CCOMP complements compiles to `IMPLY(antecedent, consequent)` (`compiler_implicationOperands` drops the "implies" predication leaf and its `THAT` attitude); and an identity-comparison clause whose subject and one operand corefer is flagged `reflexive` (the `reflexive` bool on `TKLLCContent`/`TKZipContent`, set in `compiler_evaluateStatement` via `compiler_isReflexiveIdentity`/`compiler_isIdentityComparison`) — the evaluator's `evaluator_classifyForm` then pins a reflexive leaf to a hardwired constant (`a=a → 1`, `a≠a → 0`) rather than grounding it. A clause also carries a `TKQuantifier` (the `quantifier` field on `TKLLCContent`/`TKZipContent`) read off the subject's determiner via `anchor_quantifier` (an EXACT closed-class anchor category: `all/every`→universal, `a/some`→existential, `no/none`→negative, `the/this`→definite, bare→generic); the evaluator's relational grounding applies a quantifier × `is_a`-verdict truth table (`net_flip = NEGATIVE XOR negated` over subsumes=TRUE / disjoint=FALSE). The relational grounding also handles **part_of** (mereology) — `e_relations.relations_is_part_of` over an injected `part_of` reader; `e_statement` recognizes a part-whole claim + its direction ("X is part of Y" / "Y has X", via `_PART_OF_PREDICATES`/`_HAS_PART_VERBS`) and grounds it TRUE if part⊆whole, FALSE by antisymmetry on the reverse edge, else insufficient (conservative — a missing edge never refutes); the whole's sense for "X is part of Y" is surfaced as `predicate_nmod` in `compiler_contentSenses`.
4. **Decompiler** (`lib/llc/decompiler.py`): `decompiler_raw()` renders LLC back to a raw symbolic string; `decompiler_decompile()` (Claude Haiku since 2026-07-16) polishes it into natural language. Used for debugging and round-tripping; the channel voice speaks through the SCAFFOLD store (compose 2.0, 2026-07-17: `lib/core/voice.creative_compose` — category + intensity pick a curated template, `brain/compose.py` routes; rag2-out polishes verified-or-verbatim at the carrier).
5. **Memory store**: results are saved as Bunnet documents (`TKMemoryItemDoc`, `TKAxiomDoc`, `TKTheoremDoc`) in the memory DB, tagged with source/target stakeholder IDs and a `MEMChannels` channel.

### Fixed vector dimensions (do not change casually)

These magic numbers are enforced by Pydantic `min_length`/`max_length` constraints throughout `lib/core/`:
- **2925** — semantic vector dimensions (one per base word). Base words and dictionary senses carry a 2925-dim vector.
- **3237** — final per-role tensor in a zip = 300 logical markers + 2925 semantic + 12 spacetime.
- **8** — the spacetime bounds map (`TKZip.map`); spacetime is `[t, x, y, z]` for size/position/velocity.

Changing a dimension means updating the constraints in `lib/core/tk.py`, `tkllc.py`, `tkzip.py` *and* the data already stored in MongoDB.

## API layer (`api/`)

`api/main.py` defines the FastAPI app — only the lifespan and the thin endpoint handlers. Each handler delegates to a `*Service` and wraps the result in `{"status": "complete", "data": ...}` (and `{"status": "failed", "data": repr(error)}` on a write error). Business logic (sentence compilation + Mongo CRUD) lives in `api/services/` (one `*_service.py` per resource: `axiom_service.py`, `definition_service.py`, `theorem_service.py`, `stakeholder_service.py`, `memory_service.py`, `evaluation_service.py`), re-exported from `api/services/__init__.py` so callers can `from api.services import AxiomService`. Request/response (in/out) Pydantic models and the domain-error→HTTP mapping (`_or_http` + per-resource `*_or_http` helpers) live in `api/schemas.py`. Each service is built once in the lifespan (e.g. `app.state.axiom_service = AxiomService(tokeniko, ai_client)`, `app.state.stakeholder_service = StakeholderService()`, `app.state.memory_service = MemoryService()`) and reused per request; services are framework-agnostic (no FastAPI imports).

**The route catalogue (all under `/api/v1`) is in `README.md`** — axioms / definitions / theorems
(full REST, each a `*Service`), stakeholders (read-only), memory (list/get/search/insert, NO update —
it's a Mongo **timeseries**), `POST /evaluate`, utils, compiler. Implementation notes README doesn't carry:
- **Definitions** store the full compiled `TKZip` (`MEMDefinition.zip`, single OR multi-clause; all
  WordNet glosses). `scripts/migrate_glosses.py` did the one-time re-home (`content`→`zip` + move the
  gloss-axiom batches into definitions); `NotASingleClauseError` is gone (multi-clause is legal).
- **`/memory/search`** is declared *before* `/memory/{id}` so `search` isn't read as an id; `?from=`
  is the aliased keyword (epoch **seconds** → UTC on `timestamp`).
- **Contradiction creation guard:** axiom/definition/theorem create/patch/replace reject a
  contradictory FORM — `assert_no_contradiction` (`api/services/validation.py`) runs
  `evaluator_classifyForm` (with the antonym reader) on the compiled zip and raises
  `InconsistentStatementError` (→ 422 via `create_or_http`) if it folds to 0 under every crisp
  assignment (`X∧¬X`, `a≠a`, antonym-predicate); tautologies AND contingent statements pass
  (logic-is-sacred). Lives **outside** `compile_fields` (so `recompile.py` never chokes on a bad row).
- **`/evaluate`** flattens each definition `zip` into its leaf clauses (the evaluator still gets a flat
  `list[TKZipContent]`), folds clause truths through the operator tree, geometrically matches active
  axioms/theorems → `EvaluatorResult`. **Pure — stores nothing.** Loads only `archived=False` (theorems
  default archived, so the theorem pool is empty until one is promoted).

Bunnet gotcha (bit us here): `Document.get(id)` and `find_one(...)` return *query* objects — call `.run()` to execute (`.to_list()` for `find(...)`). `AxiomService._resolve` does `TKAxiomDoc.get(oid).run()`; forgetting `.run()` yields a query object that is never `None` and has no `.save()`/`.delete()`.

## Data model layers (`lib/core/`)

The type system is layered — understand which layer you're editing:

- **`tk.py`** — the recursive/symbolic layer. Pydantic models for knowledge-base entities (`TKBase`, `TKDictionary`, `TKName`, `TKPlace`, `TKMarker`, etc.), the logical operators (`TKOperator`: AND/OR/NOT/IMPLY/CONV/THAT/…), clause types, and the parser's AST (`TKStatement`, `TKFullEntity`, `TKEntityReference`). `TKStatement` holds the `create_subject`/`add_conjuncts`/`add_subordinates` factory logic that builds the tree.
- **`tkllc.py`** — the flat intermediate layer (`TKLLC` and friends): entities + references with relative spacetime.
- **`tkzip.py`** — the final numeric layer (`TKZip`): pure float vectors.
- **`models.py`** — Bunnet (`Document`) wrappers that bind the above models to MongoDB collections. Knowledge-base docs and memory docs are registered separately in `init_io()`.
- **`memory.py`** — memory-domain models (`MEMItem`, `MEMAxiom`, `MEMTheorem`, `MEMStakeholder`, `MEMChannels`). Axioms = trusted ground truths; theorems = derived knowledge.
- **`io.py`** — `init_io()` wires up both MongoDB databases (via Bunnet) + a legacy Ollama client handle (inert — constructed lazily, no network I/O, nothing calls it since the 2026-07-16 retirement). `get_tokeniko()` / `get_stakeholder()` fetch-or-create conversation participants.
- **`mappers.py`** (`TKPosMapper`), **`utilities.py`**, **`constants.py`** — helpers and `_ME_UID`/`_ME_NAME` identity constants.

### Pydantic model rebuilds

The recursive models use forward references and **discriminated unions** (`Field(discriminator='entity_type')`). After editing any recursive model in `tk.py`, `tkllc.py`, or `tkzip.py`, the corresponding `Model.model_rebuild()` calls at the bottom of the file must stay in place — they regenerate Pydantic's internal schema. Adding a new entity payload type means adding it to the `EntityPayload` / `LLCItemPayload` union *and* keeping its `entity_type` literal unique.

## Conventions

- Comments and log messages are a mix of **English and Italian**; module headers in Italian are common. Match the surrounding language when editing a file.
- Versioned modules: older implementations are kept alongside (`compilerV1.py`, `markersV1/V2/V3.py`, `scripts/legacy scripts/`). The live "V2" compiler is now the `compiler/` package (was `compiler.py`); `parser.py` (internally "V2") is the live parser.
- `lib/llc/` = the language-compilation pipeline **+ shared utilities** (`lib/llc/utils.py`: the antonym column-read primitive `utils_antonyms` + dictionary/token similarity — moved here from the former `lib/tkll/`); `lib/core/` = data models & IO; `lib/rag/` = the Claude API machinery, concentrated (2026-07-16): `client.py` (ONE lazy client + `rag_call` — graceful None, never raises + `json_envelope`/`rag_enabled`) over `registry.py` (per-instrument `RagSpec`: model/system prompt/schema — rag1 normalizer, rag2 decompile, rag3 judge, blog polish; every Claude call site refers here). `senses/` (a sibling subproject of `lib/`) = the external connectors (Discord, ATProto/Bluesky).
- **Anchor resolver** (`lib/llc/anchors.py`) — the unified "surface word → logical/semantic category" mechanism. Semantic-native: maps ANY input to the **nearest of a small anchor set** (exact-hit fast path → nearest-anchor fallback above a floor) rather than fixed dictionaries, with a per-category backend (dictionary 2925-dim vectors for content words vs spaCy for function words), an **antonym polarity-guard** on polarity-sensitive categories (so "but" never resolves to AND), and **in-memory cached** anchor vectors (no per-call DB). The parser/compiler resolution sites — `parser_ccToOperator` (operators), `compiler_parseMarker` (subordinate types), attitude / comparison / advmod-intensifier / spatial / sequence — resolve **through it** instead of ad-hoc lemma lists, spaCy similarity, or Mongo `$vectorSearch`.
- **`brain/behavior.py`** — the reserved-token **meta-language** (step C): the `eval:*`/`tokeniko:*` dispatch (`behavior_for`/`spawn_ideas_for`/`dispatch_action` + the hardwired `_DISPATCH` registry) over the `behavior_rules` personality table (`MEMBehaviorRule`→`TKBehaviorRuleDoc`); `priorities_phase` consumes it (urge-desc). Seed: `scripts/seed_behavior_rules.py`.
- **Questions (interrogative mood).** A `?`/wh-word marks an input as a **question** — *answered, not believed*. The pipeline carries the mood: `TKZipContent.dubitative` (statement/question) + `wh_role` (the gap = variable X to solve for), detected in the parser (`?` survival + spaCy `PronType=Int` + the `anchor_whType` resolver). The parser-free `evaluation_harness.answer_zip` produces an `AnswerResult` (`lib/core/evaluation.py`): a POLAR question reuses the truth machinery (inconsistent→a confident **NO**, true→YES, false→NO, else IDK); a WH question is solved by `lib/llc/evaluator/e_wh_solve.py` (role-gap KB query: what→is_a hypernym, why→derivation chain; others staged → honest UNKNOWN). The brain (`brain/thinking.py`) branches on mood: a question fans `eval:question → tokeniko:answer` (the verdict/value + the asker as `target` in the idea/action payload) and **skips the assertion + cross-item paths**; `dispatch_action` directs the reply at the asker. A coordinated predicate shares the head clause's subject + copula aux onto its conjunct leaves (`compiler_evaluateCoordinates._inherit_shared`), so "the cat is dead and alive(?)" is one same-subject contradiction.
- `parser.py` monkey-patches `torch.load` (`weights_only=False`) to load Stanza models — keep that patch when touching parser imports.

## Reasoning layer & data-flow (code map)

> Code layout of the reasoning phase + the two data-flow bridges. *Status* (what's done/next) is NOT
> here — see the doc map below. Implementation specifics live in the code; this is the orientation map.

**Memory tiers** (conceptual model in `README.md`; types in `memory.py`/`models.py`) — **definitions**
(semantic vocabulary; full `TKZip`, all WordNet glosses), **axioms** (trusted relations + universal
rules + individual facts), **theorems** (demonstrated knowledge), **memory** (the time-series log).
The first three are full REST resources (`api/services/`).

**`lib/llc/evaluator/` package** — DB-agnostic (the caller injects definitions/axioms/theorems + reader
callbacks); the parser-free harness wires it to Mongo:
- `operators.py` — fuzzy operator truth on `[0,1]` + `operator_truth(op, a, b)` (combine clause truths).
- `e_compare.py` — geometric comparison (`evaluator_compareContent`/`compareItem`/`compareZip`,
  type-routed indirects via the marker gate); **consumes `evaluator_sameIndividual`** — identity
  overrides geometry on subject/direct (same uid→1.0, different→0.0, no uid→geometry).
- `e_truth.py` — `evaluator_groundContent`: a clause's truth in `[0,1]` vs the definitions.
- `e_statement.py` — `evaluator_evaluateStatement`: ground each clause → **fold the truths through the
  operator tree** (`A1 IMPLY (A2 AND A3)` → `IMPLY(T1, AND(T2,T3))`) → geometrically match
  axioms/theorems → `EvaluatorResult`. Does **relational grounding/refutation** on is_a/part_of
  (subsumption→true, tiered disjointness→false, premise chain in `.derivation`) and **abstains where
  geometry can't prove** (the grounding-floor post-passes). Injected readers:
  `relations=`/`part_of=`/`antonyms=`/`rules=`/`facts=`.
- `e_relations.py` — pure is_a graph logic (`isa_ancestors`/`subsumes`/`disjoint`: BFS closure +
  CONSERVATIVE tiered ontological disjointness).
- `e_consistency.py` — `evaluator_classifyForm`: the intra-statement contradiction kernel (crisp
  `{0,1}` enumeration over atom-clustered clauses; `reflexive` leaves pinned; antonym-predicate
  contraries via the `antonyms` reader as a mutual-exclusion constraint). `INCONSISTENT` = a logic
  violation ONLY.
- `e_chaining.py` — the multi-hop **forward-chainer** (`evaluator_forwardChain`/`chainGround`): seed a
  class closure from the subject (+ is_a ancestors / membership facts), fire MEMBERSHIP rules to a
  fixpoint, then PROPERTY + property-conditioned rules; **corroborates** (truth≈1) or **KB-refutes**
  (RESOLVED truth≈0 + chain, NEVER INCONSISTENT — that's reserved for logic).
- `e_wh_solve.py` — wh value-solver (what→is_a hypernym, why→derivation chain; others staged).
- `e_label.py` — `evaluator_assignWord`: the most-representative dictionary word (noun-weighted role
  centroid → nearest via `$vectorSearch`).
- `evaluation.py` — `EvaluatorResult`/`EvaluatorStatus`/`AnswerResult`.

`EvaluationService` (`api/services/evaluation_service.py`, `POST /evaluate`) is the DB adapter; the
reusable **parser-free** core (load active KB → build readers + chainer rules/facts → evaluate a ready
`TKZip` → map best match to a doc id) is `lib/core/evaluation_harness.py`
(`evaluate_zip`/`answer_zip`/`cross_item_conflict`), shared with `brain/thinking.py` (the brain stays
spaCy/Stanza-free). The is_a/part_of/antonym/… graph is `TKRelationDoc` (`{subject, relation, object,
pos}`, ~150k WordNet triples; registered in `init_io`).

**Sense-bridge** — the WSD sense threads through the pipeline so the evaluator can read it:
`TKDictionary.sense` (`cat.n.01`) → `TKLLEntity.sense` (`compiler_getEntity`) → `TKZipContent.senses`
(role→sense dict, `compiler_zipContent`).

**Identity-bridge** — a named individual ("Mari", "Rome", "Google") gets **two SEPARATE things**, never
mixed: an honest SEMANTIC vector = its NER **type centroid** (`PERSON→person.n.01`,
`GPE/LOC/FAC→location.n.01`, `ORG→organization.n.01`, …; dictionary-fetched, cached) **and** a
referential **IDENTITY** uid `name@channel:talker_uid`. The 2925 space stays pollution-free (never a
noise vector). Minting is gated by NER-type + a real spaCy-lg vector (`_parser_hasLgVector`, since
stanza tokens have none), so OOV gibberish never mints; a known place takes `parser_getPlace` first.
Flow mirrors the sense-bridge: `TKName.uid/vector/ner` (`parser_getIndividual`) → `TKLLEntity.uid` →
`TKZipContent.identities`. Homed in `MEMStakeholder` (`kind="individual"`) via `io.upsert_individual`
— only on storing paths, NEVER on `/evaluate` (which stays pure/read-only). `evaluator_sameIndividual`
is the entity-linking primitive (same uid→True, different→False, missing→None).

**Status lives in three sibling files in `doc/` → `doc/roadmap.md`** (the road ahead: in-progress +
ordered next), **`doc/landed.md`** (what's done), **`doc/parked.md`** (the icebox — deliberately
deferred). Everything else in `doc/` is **reference material, homed under `doc/ref/`** (extended
context per task + future-reference to fill the roadmap): the consolidated design notes
(`doc/ref/notes.md` — phased execution detail + reasoning-engine design/findings + parser/compiler
quirks & gaps), the living empirical fragility log (`doc/ref/test-feedback.md`), and the rest
(`kb-growing-outward.md`, `paper_outline.md`, `captain-hunches.md`).

**Status-doc invariants (STRICT — these three docs are the single source of truth for status).** An
item has exactly ONE status and lives in exactly ONE of the three docs:
1. **One item, one status.** Never list the same task under two statuses (e.g. in `roadmap.md` Next
   *and* `parked.md`, or `landed.md` *and* `roadmap.md`). Its current status decides the one doc it
   belongs to: in-flight/next → `roadmap.md`; done → `landed.md`; deferred → `parked.md`.
2. **No cross-doc duplication.** The same item never appears in two of {`roadmap.md`, `landed.md`,
   `parked.md`}. When an item moves status, **MOVE it** (delete from the old doc, add to the new) —
   never copy. A one-line *pointer* is allowed (e.g. `roadmap.md` may say "steps 1–2 ✅ — see
   `landed.md`") but the pointer carries no status detail of its own — it references, it does not
   duplicate.
3. **Reconcile at every commit.** Before each commit, check all three against the code reality and
   update them so they reflect it with precision: land what the commit finished (roadmap→landed), park
   what the commit deferred (roadmap→parked), add any newly-surfaced next work to `roadmap.md`. The
   roadmap is the road *ahead* only — nothing landed, nothing parked lingers in it.

`doc/ref/notes.md` (design reference) and `doc/ref/test-feedback.md` (empirical log) are NOT status docs — they
are exempt from the invariants above (an item may be discussed there *and* have a status entry).

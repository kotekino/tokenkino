# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Tokeniko is a **neuro-symbolic NLP engine** that compiles a natural-language sentence into a fixed-size mathematical representation ("the zip") that can be stored in MongoDB as permanent, queryable, geometrically-comparable memory. It combines symbolic parsing (POS tagging, dependency parsing, formal logical operators) with sub-symbolic fuzzy-logic vector fusion (NumPy). See `README.md` for the conceptual overview of the compilation flow.

Note: the git repository root is the **parent** directory (`../`), which also holds `scripts/` (one-off data-ingestion scripts), `atlas/` (local MongoDB data volumes), `data/`, and `doc/`. This directory (`tokeniko/`) is the installable Python package and the FastAPI app.

## Commands

Tasks are defined in `pyproject.toml` via `taskipy` (run from this directory):

- `task api` — run the FastAPI server (`uvicorn api.main:app --reload`) on port 8000
- `task brain` — run the background daemon (`python -m brain.main`)
- `pip install -e .` — editable install of the `tokeniko` package (`lib*`, `api*`)

There is **no test suite, linter, or formatter** configured. Files under `scripts/` (in the repo root) are standalone executable scripts run directly with `python scripts/<name>.py`; they populate the MongoDB knowledge-base collections (`base`, `dictionary`, `names`, `places`, `markers`, `properties`) and are not imported by the app.

### Two entry points: `api` vs `brain`

There are two distinct processes, and they have different startup requirements:

- **`task api`** (`api/main.py`) — the FastAPI server. Its lifespan calls `parser_init()`, `preparser_init()`, and `decompiler_init()`, which load the spaCy/Stanza pipelines and pull the Ollama models. It needs **all** the dependencies below to start and serve requests. This is where the full compilation pipeline runs.
- **`task brain`** (`brain/main.py`) — a background daemon (idle "thinking" loop, plus stubbed ATProto/Discord listeners). It only calls `init_io()`, so it constructs the Mongo and Ollama clients but does **not** load spaCy/Stanza or pull Ollama models on startup. In practice it needs MongoDB reachable; it does not exercise the NLP pipeline yet.

Note also that importing the `lib/llc` pipeline modules (`parser`, `preparser`, `compiler`) loads `en_core_web_lg` at **module import time**, and `translator.py` imports `transformers` at import time — so any process that imports the pipeline needs those models present.

### Runtime dependencies (must be running)

The `api` server will not start without these (the `brain` daemon only requires MongoDB):
- **MongoDB** at `MONGO_URI` (default `mongodb://localhost:27018`). Start the local Atlas container with `docker compose up -d` from this directory (`docker-compose.yml` lives here; its volumes mount the repo-root `../atlas/` data dirs). Two logical databases are used: `MONGO_DB_NAME` (knowledge base) and `MONGO_DB_NAME_MEMORY` (memory).
- **Ollama** at `OLLAMA_HOST` (default `http://localhost:11434`), used by the preparser/decompiler. Required models are listed in `lib/llc/constants.py` (`_OLLAMA_MODEL*`, `_OLLAMA_TRANS*`) and auto-pulled on startup.
- **spaCy + Stanza models**: `en_core_web_lg` (`_SPACY_MODEL`) and the `spacy_stanza` English pipeline. Stanza is run with `device="mps"` (Apple Silicon GPU).

Config is read from `.env` via `python-dotenv`. `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` are set so HuggingFace/MarianMT translation models load from local cache only.

## Architecture: the compilation pipeline

A sentence flows through a multi-stage pipeline. The two main API entry points (`api/main.py`) — `/api/v1/tkllc` and the axiom/theorem endpoints — chain these stages:

1. **Preparser** (`lib/llc/preparser.py`, optional, `prepare=1`): typo correction (SymSpell), language detection (lingua), and translation to English (MarianMT via `lib/llc/translator.py`) before parsing. LLM-assisted via Ollama.
2. **Parser** (`lib/llc/parser.py`): `parser()` is the entry point. Uses spaCy+Stanza to dependency-parse, then builds a **recursive AST of `TKStatement` objects** (`TKStatements = list[TKStatement]`). Resolves word meanings against the MongoDB dictionary, attaches markers/operators, and produces the nested grammatical structure (subject / predicate / direct / indirects, with conjuncts, subordinates, and properties).
3. **Compiler** (`lib/llc/compiler/` package): `compiler_compile()` is the entry point (re-exported from `compiler/__init__.py`). The package is split by section — `c_entities.py`, `c_subordinates.py`, `c_statements.py`, `c_spacetime.py`, `c_zip.py`, the `c_main.py` orchestrator, and `c_state.py` (shared `_entities` map + spaCy `nlp`, reset in place per compile). Two outputs in one pass:
   - **LLC Flat** (`TKLLC`, defined in `lib/core/tkllc.py`): flattens the recursive statements into entities + references for O(1) access, resolves pronouns and implicit subjects, and computes relative spacetime.
   - **TKZip** (`TKZip`, defined in `lib/core/tkzip.py`): the final fixed-size numeric output. Applies fuzzy-logic vector fusion — advmod scalar multipliers (`_PROP_BASE_ADVMOD_ANCHORS`, e.g. "very"=1.5), Min/Max/negation/Gödel-implication operators kept in `[-1,1]`, `tanh` soft-normalization.
4. **Decompiler** (`lib/llc/decompiler.py`): `decompiler_raw()` renders LLC back to a raw symbolic string; `decompiler_decompile()` (Ollama) polishes it into natural language. Used for debugging and round-tripping.
5. **Memory store**: results are saved as Bunnet documents (`TKMemoryItemDoc`, `TKAxiomDoc`, `TKTheoremDoc`) in the memory DB, tagged with source/target stakeholder IDs and a `MEMChannels` channel.

### Fixed vector dimensions (do not change casually)

These magic numbers are enforced by Pydantic `min_length`/`max_length` constraints throughout `lib/core/`:
- **2925** — semantic vector dimensions (one per base word). Base words and dictionary senses carry a 2925-dim vector.
- **3237** — final per-role tensor in a zip = 300 logical markers + 2925 semantic + 12 spacetime.
- **8** — the spacetime bounds map (`TKZip.map`); spacetime is `[t, x, y, z]` for size/position/velocity.

Changing a dimension means updating the constraints in `lib/core/tk.py`, `tkllc.py`, `tkzip.py` *and* the data already stored in MongoDB.

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
- `lib/llc/` = the language-compilation pipeline; `lib/core/` = data models & IO; `lib/tkll/` = dictionary/token similarity search; `lib/tagger/` = tagging helpers.
- `parser.py` monkey-patches `torch.load` (`weights_only=False`) to load Stanza models — keep that patch when touching parser imports.

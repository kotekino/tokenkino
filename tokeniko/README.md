# Tokeniko Neuro-Symbolic Architecture

Tokeniko is a **neuro-symbolic NLP engine** that compiles a natural-language sentence
into a fixed-size mathematical representation (the **`zip`**) which can be stored in
MongoDB as **permanent, queryable, geometrically-comparable memory**. It pairs symbolic
parsing (POS tagging, dependency parsing, formal logical operators) with sub-symbolic
fuzzy-logic vector fusion (NumPy).

> This README is the conceptual overview. For the internal developer reference
> (architecture, module layout, runtime dependencies), see `CLAUDE.md`.

## Tokeniko's Compilation Flow

1. **NLP Parsing & Disambiguation (Symbolic Phase):** Tokeniko receives a natural language sentence, performs grammatical deconstruction (POS tagging, dependency parsing), and resolves contextual references (e.g., it understands that "you" refers to itself, i.e., "tokeniko"). Surface words are mapped to their logical categories (operators, markers, attitudes, intensifiers, …) by a unified, **semantic-native anchor resolver** (`lib/llc/anchors.py`) — nearest-of-anchors rather than fixed keyword lists, so no input is ever silently missed.
2. **Vector Semantic Lookup:** It queries the database (MongoDB) to retrieve the encyclopedic definitions and the "pure" base tensors (2925 dimensions) for each word/entity, linking them to their respective *synsets* (e.g., WordNet).
3. **Logical Intermediary Generation (LLC):** It builds a dual-track data structure:
   * **LLC Flat:** A flat dictionary for fast $O(1)$ memory access.
   * **LLC Recursive:** A syntax tree (AST) that faithfully maps the grammatical relationships and logical dependencies between clauses using formal operators (AND, OR, NOT, IMPLY, CONV, THAT, …).
4. **Fuzzy Fusion Engine (Sub-Symbolic Phase):** It uses linear algebra (via NumPy) to calculate the true "meaning" of the entire sentence. It applies scalar multipliers for adverbs (e.g., "very" = 1.5), uses vectorized fuzzy logic operators (Min, Max, negations, and Gödel implications) to handle complex conditions without exceeding the **[-1, 1]** range, and stabilizes the root entity with a soft normalization (`tanh`).
5. **Compilation into the `TKZip` Format:** It encapsulates the mathematical outcome into a strictly typed, fixed-size format. The logical roles of the sentence (subject, predicate, direct object) are transformed into final tensors of exactly **3237 dimensions** (300 logical markers + 2925 semantic space + 12 spacetime).
6. **Decompilation (round-trip):** The LLC can be rendered back to a raw symbolic string and, optionally, polished into natural language (via Ollama) — used for debugging and verifying that meaning survived the trip.
7. **Evaluation / Reasoning Phase:** A compiled statement is not just stored — it can be reasoned about. The **evaluator** (`lib/llc/evaluator/`) measures a statement against the knowledge base: it **grounds** each flat clause to a truth in **[0, 1]** against the *definitions*, **folds those clause truths through the operator tree** (fuzzy logic — `A1 IMPLY (A2 AND A3)` becomes `IMPLY(T1, AND(T2, T3))`), runs an **intra-statement consistency check** (a self-contradiction → `inconsistent`), and geometrically matches the whole statement against the active **axioms/theorems** — producing an `EvaluatorResult` whose `status` is `resolved`, `insufficient_knowledge`, or `inconsistent`. It also **grounds and refutes against the `relations` taxonomy graph** (the WordNet is_a network): "a cat is a mammal" is confirmed true and "a cat is a plant" is derived false, each carrying a premise chain that explains the verdict. Logic itself is hardwired, not learned: a reflexive identity is pinned (`a = a` → true, `a ≠ a` → false), and the verb `imply`/`entail` compiles to a real `IMPLY` operator rather than to ordinary predication.

---

**In short:** Tokeniko takes the abstraction and ambiguity of human words, breaks them down using formal logic, and fuses them into a fixed-size mathematical matrix (the `zip`), ready to be saved in the database as a **permanent, queryable, and geometrically comparable memory**.

## The `zip`, dimension by dimension

Each logical role in a sentence becomes a tensor of exactly **3237** dimensions:

| Segment | Size | Meaning |
|---|---|---|
| Logical markers | 300 | grammatical/logical features |
| Semantic space | 2925 | one slot per base word (the "pure" meaning vector) |
| Spacetime | 12 | `[t, x, y, z]` for **size**, **position** and **velocity** |

A compiled `zip` also carries an **8-value spacetime bounds map** (the absolute frame
the relative coordinates live in).

## Memory model

Tokeniko's memory is more than a log — it is layered by epistemic status:

- **Definitions** — single-clause, purely *semantic* statements that define Tokeniko's
  vocabulary ("a cat is an animal"). Trusted ground truths, no demonstration; the bedrock
  that axioms and theorems build on (and what the evaluator grounds clauses against).
- **Axioms** — *trusted ground truths* Tokeniko holds about the world; the basis for
  reasoning and deriving new knowledge. Trusted by default and read-only.
- **Theorems** — knowledge *derived* from the axioms (slightly lower trust, archived by
  default until promoted).
- **Memory items** — the time-series of conversation messages, tagged with the source and
  target **stakeholder** and the **channel** they came through (`internal`, `api`,
  `discord`, `atproto`).

Every participant is a **stakeholder**; Tokeniko itself is the `isMe` stakeholder, which
is why first/second-person pronouns ("I", "you") resolve to *tokeniko*.

## API

Run the server with `task api` (FastAPI on port `8000`). All routes are under `/api/v1`.

The route handlers in `api/main.py` are thin controllers: each delegates to a `*Service`
in `api/services/` (compilation + Mongo CRUD) and wraps the result in
`{"status": "complete"/"failed", "data": ...}`. Request/response models and the
domain-error→HTTP mapping live in `api/schemas.py`.

### Axioms — REST resource

Trusted ground truths (full `TKZip`).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/axioms` | compile a sentence (`{"tokens": "..."}`) and store it as an axiom |
| `GET` | `/api/v1/axioms` | list axioms (summary view, no `zip`; `?archived=true/false` filter) |
| `GET` | `/api/v1/axioms/{id}` | fetch a single axiom (full document, including `zip`) |
| `PATCH` | `/api/v1/axioms/{id}` | partial update (recompiles if `tokens` is supplied; else flips `trusted`/`archived`/`readonly`/`channel`) |
| `PUT` | `/api/v1/axioms/{id}` | replacement update (recompile from `tokens` + reset flags) |
| `DELETE` | `/api/v1/axioms/{id}` | delete an axiom |

### Definitions — REST resource

Semantic statements defining tokeniko's vocabulary/rules. A definition's meaning is the full compiled `TKZip` (single **OR** multi-clause); same shape as axioms. All WordNet glosses live here.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/definitions` | compile a sentence and store it as a definition |
| `GET` | `/api/v1/definitions` | list definitions (summary view, no `zip`; `?archived=` filter) |
| `GET` | `/api/v1/definitions/{id}` | fetch a single definition (full document, including `zip`) |
| `PATCH` | `/api/v1/definitions/{id}` | partial update (recompiles if `tokens` is supplied) |
| `PUT` | `/api/v1/definitions/{id}` | replacement update (recompile + reset flags) |
| `DELETE` | `/api/v1/definitions/{id}` | delete a definition |

### Theorems — REST resource

Derived knowledge (full `TKZip`); no `readonly` flag.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/theorems` | compile a sentence and store it as a theorem |
| `POST` | `/api/v1/theorems/materialize` | materialize a DERIVED conclusion (provenance + optional `senses` pinned into the zip; dedups on the semantic conclusion) |
| `GET` | `/api/v1/theorems` | list theorems (summary view, no `zip`; `?archived=` filter) |
| `GET` | `/api/v1/theorems/{id}` | fetch a single theorem (full document, including `zip`) |
| `PATCH` | `/api/v1/theorems/{id}` | partial update (recompiles if `tokens` is supplied) |
| `PUT` | `/api/v1/theorems/{id}` | replacement update (recompile + reset flags) |
| `DELETE` | `/api/v1/theorems/{id}` | delete a theorem |

### Stakeholders — list / get (read-only)

The known talking entities.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/stakeholders` | list stakeholders (summary view) |
| `GET` | `/api/v1/stakeholders/{id}` | fetch a single stakeholder (full document) |

### Memory — list / get / search / insert (no update)

The time-series log of conversation inputs/outputs. The `memory` collection is a Mongo
**timeseries**, which forbids in-place updates — so there is no PATCH/PUT/DELETE; insert is a
plain log append (no compilation).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/memory` | recent items, newest first (summary view, no `zip`); `?limit=` (default 100) |
| `GET` | `/api/v1/memory/search` | filter the log: `?from=&to=` (epoch **seconds** → UTC on `timestamp`; `from` is aliased), `?source=`/`?target=`/`?channel=`, `?limit=` |
| `GET` | `/api/v1/memory/{id}` | fetch a single memory item (full document) |
| `POST` | `/api/v1/memory` | append a log entry (`original`, `sourceId`, optional `targetId`/`channel`/`metadata`) |

### Evaluate — truth evaluation (action; stores nothing)

Compile a sentence and evaluate its truth against tokeniko's knowledge: each flat clause is grounded
against the **definitions** (a fuzzy `[0,1]` truth), those clause truths are **folded through the
operator tree** (`IMPLY`/`AND`/… applied on the truths, not the vectors), and the whole statement is
geometrically matched against the active **axioms/theorems**.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/evaluate` | `{"tokens":"..."}` → `EvaluatorResult` (`truth`, `status`, `groundings`, `missing`, `relationMatch`, `matchedKind`/`matchedIndex`) + the resolved `matchedId`/`matchedOriginal` of the closest known statement |

`status` is `resolved` (grounded + a known relation matches → `truth` is the folded value),
`insufficient_knowledge` (an ungrounded clause or no matching relation → `truth` 0.5), or
`inconsistent` (`truth` 0.0) — returned when the statement is internally self-contradictory,
detected by the intra-statement consistency kernel (`evaluator_classifyForm` in
`lib/llc/evaluator/e_consistency.py`): e.g. `X ∧ ¬X`, or a reflexive-identity violation like
"a thing is not equal to itself".

### Utils (debugging; may be removed later)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/utils/dict?token=` | look up similar tokens in the dictionary |
| `GET` | `/api/v1/utils/markers?token=` | base marker vector for a token |
| `GET` | `/api/v1/utils/polish?tokens=` | typo correction only |
| `GET` | `/api/v1/utils/prepare?tokens=` | full preparse (typos + language detection + translation) |
| `GET` | `/api/v1/utils/translate?tokens=` | translate to English |
| `GET` | `/api/v1/utils/render?tokens=&prepare=` | HTML dependency diagram of the parse |

### Compiler

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/input?tokens=&output=&prepare=&talker=` | run the full pipeline; returns LLC flat + recursive + raw (+ polished if `output=1`) and stores a memory item |
| `GET` | `/api/v1/output?tokens=` | polish a raw LLC string into natural language |

## Running locally

From this directory (`tokeniko/`):

```bash
pip install -e .          # editable install of the tokeniko package
docker compose up -d      # local MongoDB (Atlas) container
task api                  # FastAPI server on :8000
task brain                # the autonomous "mind" daemon (MongoDB only)
task senses               # the Discord + ATProto/Bluesky I/O daemon
```

Beyond the API, Tokeniko also runs as a living entity: the **brain** is its autonomous mind
— the *thinking*, *priorities* (wishes/ideas), and *actions* loops — and **senses** is its
I/O membrane to the outside world (the Discord bot + the ATProto/Bluesky listener). See
`brain/README.md` and `senses/README.md` for their design. With the reasoning foundation now in
place, fleshing out this autonomous **brain** (behavior-as-memory: reserved-token reflex rules over a
perceive→evaluate→act loop) is the next phase.

Alongside the `senses` connectors, Tokeniko has one more **output channel**: a **public website**
(`../tokeniko-public/`) — a vintage-CRT public window with a stream of Tokeniko's *transmissions*
beside a live **Mind Monitor** of KPIs that mirror the engine's concepts (axioms, dictionary base
vectors, memory/beliefs, inferences, refutations, anchors). It is a self-contained sibling project
(React/Vite + TypeScript front end, Node/Express back end, MongoDB Atlas — **not** part of the Python
`tokeniko` package), currently in a **mock phase** (`GET /api/mind` serves a simulated snapshot; its
response shape is the contract for the live wiring). The brain's **actions** loop feeds it.

### Deployment topology

Tokeniko runs on **bare metal** with its **local MongoDB** (`:27018`) — this is the embodied mind. The
public website runs in the **cloud** against a **separate public MongoDB Atlas**. Tokeniko **publishes**
to the public API during its brain cycles — *transmissions* when its actions loop decides to act, and
hardware / brain-cycle stats pushed periodically to drive the Mind Monitor. It is a **one-way publish**:
the public surface enriches the public Atlas and is never bound to the embodied local db.

Runtime dependencies: **MongoDB** (`MONGO_URI`), **Ollama** (`OLLAMA_HOST`, models
auto-pulled on startup), and the **spaCy + Stanza** English models (`en_core_web_lg`,
run on Apple-Silicon `mps`). Configuration is read from `.env`. See `CLAUDE.md` for the
full dependency and architecture notes.

# Tokeniko Neuro-Symbolic Architecture

Tokeniko is a **neuro-symbolic NLP engine** that compiles a natural-language sentence
into a fixed-size mathematical representation (the **`zip`**) which can be stored in
MongoDB as **permanent, queryable, geometrically-comparable memory**. It pairs symbolic
parsing (POS tagging, dependency parsing, formal logical operators) with sub-symbolic
fuzzy-logic vector fusion (NumPy).

> This README is the conceptual overview. For the internal developer reference
> (architecture, module layout, runtime dependencies), see `CLAUDE.md`.

## Tokeniko's Compilation Flow

1. **NLP Parsing & Disambiguation (Symbolic Phase):** Tokeniko receives a natural language sentence, performs grammatical deconstruction (POS tagging, dependency parsing), and resolves contextual references (e.g., it understands that "you" refers to itself, i.e., "tokeniko").
2. **Vector Semantic Lookup:** It queries the database (MongoDB) to retrieve the encyclopedic definitions and the "pure" base tensors (2925 dimensions) for each word/entity, linking them to their respective *synsets* (e.g., WordNet).
3. **Logical Intermediary Generation (LLC):** It builds a dual-track data structure:
   * **LLC Flat:** A flat dictionary for fast $O(1)$ memory access.
   * **LLC Recursive:** A syntax tree (AST) that faithfully maps the grammatical relationships and logical dependencies between clauses using formal operators (AND, OR, NOT, IMPLY, CONV, THAT, …).
4. **Fuzzy Fusion Engine (Sub-Symbolic Phase):** It uses linear algebra (via NumPy) to calculate the true "meaning" of the entire sentence. It applies scalar multipliers for adverbs (e.g., "very" = 1.5), uses vectorized fuzzy logic operators (Min, Max, negations, and Gödel implications) to handle complex conditions without exceeding the **[-1, 1]** range, and stabilizes the root entity with a soft normalization (`tanh`).
5. **Compilation into the `TKZip` Format:** It encapsulates the mathematical outcome into a strictly typed, fixed-size format. The logical roles of the sentence (subject, predicate, direct object) are transformed into final tensors of exactly **3237 dimensions** (300 logical markers + 2925 semantic space + 12 spacetime).
6. **Decompilation (round-trip):** The LLC can be rendered back to a raw symbolic string and, optionally, polished into natural language (via Ollama) — used for debugging and verifying that meaning survived the trip.

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

### Axioms — REST resource

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/axioms` | compile a sentence (`{"tokens": "..."}`) and store it as an axiom |
| `GET` | `/api/v1/axioms` | list axioms (summary view, no `zip`; `?archived=true/false` filter) |
| `GET` | `/api/v1/axioms/{id}` | fetch a single axiom (full document, including `zip`) |
| `PATCH` | `/api/v1/axioms/{id}` | partial update (recompiles if `tokens` is supplied; else flips `trusted`/`archived`/`readonly`/`channel`) |
| `PUT` | `/api/v1/axioms/{id}` | replacement update (recompile from `tokens` + reset flags) |
| `DELETE` | `/api/v1/axioms/{id}` | delete an axiom |

The business logic (compilation + Mongo CRUD) lives in `api/services.py` (`AxiomService`);
the route handlers in `api/main.py` are thin controllers.

### Other endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/theorem?tokens=` | compile a sentence and store it as a theorem |
| `GET` | `/api/v1/tkllc?tokens=&output=&prepare=&talker=` | run the full pipeline; returns LLC flat + recursive + raw (+ polished if `output=1`) and stores a memory item |
| `GET` | `/api/v1/render?tokens=&prepare=` | HTML dependency diagram of the parse |
| `GET` | `/api/v1/dict?token=` | look up similar tokens in the dictionary |
| `GET` | `/api/v1/markers?token=` | base marker vector for a token |
| `GET` | `/api/v1/pre/polish?tokens=` | typo correction only |
| `GET` | `/api/v1/pre/prepare?tokens=` | full preparse (typos + language detection + translation) |
| `GET` | `/api/v1/pre/translate?tokens=` | translate to English |
| `GET` | `/api/v1/out?tokens=` | polish a raw LLC string into natural language |

## Running locally

From this directory (`tokeniko/`):

```bash
pip install -e .          # editable install of the tokeniko package
docker compose up -d      # local MongoDB (Atlas) container
task api                  # FastAPI server on :8000
task brain                # background "thinking" daemon (MongoDB only)
```

Runtime dependencies: **MongoDB** (`MONGO_URI`), **Ollama** (`OLLAMA_HOST`, models
auto-pulled on startup), and the **spaCy + Stanza** English models (`en_core_web_lg`,
run on Apple-Silicon `mps`). Configuration is read from `.env`. See `CLAUDE.md` for the
full dependency and architecture notes.

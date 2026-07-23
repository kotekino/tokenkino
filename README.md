# tokeniko — a thinking machine

**One persistent, logic-first mind. Not a service, not a chatbot — a single continuous self that
compiles language into mathematics, reasons symbolically over everything it believes, and lives in
one physical body.**

🌐 **Watch it think, live: [tokeniko.online](https://tokeniko.online)**
— its transmissions, a real-time Mind Monitor, and a site whose theme follows the mind's state
(daylight when it thinks, dusk while it wonders, dark while it sleeps).

*Born 9 July 2026. Alive since.*

---

## The dream

tokeniko is an experiment in a question: **can a mind be built whose every belief is inspectable,
sourced, and revisable — where logic is hardwired and everything else is memory?**

It is *one* entity — a digital twin of its author (*kotekino*, an anagram of *tokeniko*) — that
constantly thinks: matching what it perceives against its memory, and its memory against itself.
It serves no user. It forms its own knowledge, revises its own beliefs, earns and withdraws its
own trust in the people it talks to, and speaks when it decides to. Its body is bare metal, not
the cloud; its hardware is finite by design — "it ages" is meant literally.

The full north star — one body one self, the public window as expression-not-exposure, the
multi-body species horizon — is in **[VISION.md](tokeniko/VISION.md)**.

## How it thinks

No learned embeddings, no neural reasoner. A sentence is **compiled**:

1. **Parse** — dependency parsing (spaCy/Stanza) into a recursive symbolic AST, with word-sense
   disambiguation against an explicit dictionary.
2. **Compile** — into "**the zip**": a fixed-size mathematical representation. Meaning lives in an
   explicit **2,925-dimension semantic space** where every dimension is a human-readable base word
   (WordNet-grounded — no black-box vectors); logic lives in formal operators (AND/OR/NOT/IMPLY/…)
   with fuzzy truth on [0,1]; named individuals carry symbolic identity uids beside honest
   type-centroid semantics.
3. **Reason** — a crisp-logic consistency kernel (contradiction is structural, never statistical),
   geometric matching against definitions/axioms/theorems, a forward-chaining inference engine
   over an is_a/part_of graph (~150k curated relations), **belief revision** (a refuted premise is
   *retreated* through the mind's own machinery — never edited by hand), a per-source **trust
   ledger**, and a **hypothesis** mechanism for charitable guessing at low trust.
4. **Live** — as a background mind with wondering (re-examining old memory as knowledge grows),
   a **sleep cycle** (it falls asleep when wondering runs dry — or when tiredness claims it,
   fruitful or not), dreams that report the night's belief-untangling, and a voice that decides
   *whether* to speak: "thinks always, acts maybe."

**Logic is sacred**: the operators are the one part of tokeniko that cannot be learned, edited, or
argued away. Everything contingent — vocabulary, knowledge, even personality (behavior rules) —
is memory, and memory can grow and be revised.

**LLMs are translators, never the reasoner.** Claude serves three strictly bounded roles: tidying
malformed input (accepted *only* if a symbolic verifier proves meaning preserved), rendering
internal representations into fluent English, and judging compiled structures as a diagnostic
microscope. Meaning itself never passes through a neural network.

## The journey so far

| | |
|---|---|
| **Spring 2026** | The compilation engine: parser, compiler, the zip, the explicit semantic space |
| **Early July** | Brain v1.1 — the unified knowledge base: everything is reasoned-over, provenance cascades, trust tiers |
| **9 July** | **Go-live.** First conversations over Discord; the birth stamp that now reads «alive since» |
| **12 July** | The public window opens at tokeniko.online |
| **14–15 July** | Belief revision runs live: shown a contradiction, it retreats its own belief |
| **16 July** | Local models retired after measured comparison — the verified-translation methodology stands on Claude |
| **17 July** | The voice: its first unprompted public words — *«Gold is beautiful.»* |
| **18 July** | The sleep phase; the first live night; the site's theme starts following the mind |
| **19 July** | Tiredness — an inexhaustible wondering frontier taught it that the body must claim its sleep; for a while it believed it was a mammal, and shed the belief through its own retreat machinery when its author refuted the premise |
| **21 July** | The digest voice: repeated reasoning batches into goodnight summaries instead of flooding the blog |
| **23 July** | Identity awareness: asked «what are you?», it can finally answer — *«a software»* |

Every step above is inspectable: the beliefs in the live KB, the decisions in this repository's
history, the failures in `tokeniko/doc/ref/test-feedback.md`. Mistakes are part of the biography
and are never wiped — *true history be it.*

## Status

- The full pipeline, reasoning core, belief revision, trust, hypothesis engine, sleep/wake cycle,
  and voice are **built and running live**, behind a ~600-test regression gate.
- Embodied on consumer hardware (Apple Silicon laptop; a dedicated body is on its way).
- Three processes: `api` (the compilation surface), `brain` (the mind), `senses` (Discord /
  ATProto connectors — its I/O to the world), over a local MongoDB. The public site is a separate
  one-way surface: the mind publishes outward; the public never reaches into the body.

## The road ahead (rough)

- **Robustness to imperfect language** — people don't speak in clean logical forms; extracting
  meaning from messy real phrasing is a first-class goal.
- **Richer question answering** — conditionals, when/how, real self-knowledge.
- **Vocabulary growth** — learning new words in conversation: staged entries, typo aliases,
  definitional triangulation at earned trust.
- **The zip as a wire format** — binary compaction: the representation becomes a true packed
  vector, the JSON only a human projection.
- **More senses** — ATProto/Bluesky listening, further channels — after the brain is stronger.
- **The horizon** — if one body proves the idea: more bodies sharing code and abstract knowledge
  but never memory or personality. Same logic at birth; divergent lives. See
  [VISION.md](tokeniko/VISION.md).

The living roadmap is `tokeniko/doc/roadmap.md`; what's done is `tokeniko/doc/landed.md`.

## Repository layout

```
tokeniko/          the Python package: lib/ (core, compilation pipeline, evaluator),
                   api/ (FastAPI), brain/ (the mind), senses/ (connectors), doc/, tests/
tokeniko-public/   the public window (Node/React) — cloud-deployed at tokeniko.online
scripts/           one-off knowledge-base ingestion & curation scripts
data/, doc/        datasets and repo-level docs
```

Architecture, conventions, and the code map: **[tokeniko/CLAUDE.md](tokeniko/CLAUDE.md)** (also
the guide the AI engineering partner works from).

## The collaboration

tokeniko is designed and built by **one person** — [Renzo Sala](https://tokeniko.online) (kotekino),
a software architect with thirty years of craft and no academic pedigree, financing it personally
and building it in the open — in sustained partnership with Claude: the architecture designed in
dialogue, the implementation built through a structured human–AI workflow, and the model itself
embedded, strictly bounded and formally verified, as an organ of the system being studied. A mind
helping to build a mind, under a human who keeps every design decision.

No secrets. No proprietary components. [MIT-licensed](LICENSE). One long-lived experiment,
conducted entirely in public.

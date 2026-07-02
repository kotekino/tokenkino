# PAPER_OUTLINE.md — Working Title: Tokeniko

> **Framing note.** This is a *lab-notebook / expedition log* of building one persistent logical entity,
> not a victory lap. It is **unexplored territory**: we report the hiccups, rollbacks, and failure modes
> as first-class results, because in a place with no map the honest record of what broke *is* the
> knowledge produced. Claims are scoped to what was *measured*; everything aspirational is named as an
> open question. (The triumphalist first draft was softened on purpose.)

## Working Titles
*   **Academic:** *Tokeniko: An Embodied Neuro-Symbolic Architecture for Persistent Geometric Memory and Continuous Logical Inference.*
*   **System-Oriented:** *A Persistent, Logic-First Cognitive Entity: Hardwired Algebra over Fuzzy Semantic Vectors.*

## 1. Abstract
*   **The gap we probe:** stateless LLMs as cognitive *twins* — no persistence, no hardwired logic, brittle on negation/identity.
*   **The system:** Tokeniko — a neuro-symbolic engine compiling NL into a fixed-size tensor (the `zip`) that is *both* geometrically comparable memory *and* the substrate for algebraic inference.
*   **The thesis (design stance, not a solved problem):** a STRICT separation — *geometry = soft unification* (what connects to what) vs. *algebra = inference* (truth, hardwired on the AST). Geometry never votes on truth; when it cannot prove, it **abstains**.
*   **Autonomy:** a continuous Thinking / Priorities / Actions loop + a *Wondering* phase for offline theorem derivation.
*   **What we report:** the architecture, an empirical study of autonomous derivation (the long-wondering soak), and a documented map of failure modes and their fixes.

## 2. Introduction & Motivation
*   **Why a different shape:** against the scale-everything grain — persistent, embodied (local DB, single continuous state, finite hardware that *ages*), interpretable. *Not* competing with LLMs on breadth; a different kind of system.
*   **"Logic is Sacred, Everything Else is Memory":** the founding philosophy. The logical operators are hardwired infrastructure (the one non-revisable axiom); all knowledge/behaviour is contingent memory, grown via a trust gradient.
*   **An epistemic stance baked into the engine:** *prove before you believe; abstain when you can't.* (We note, honestly, that this stance is also the authors' research method — and we hold ourselves to it in the claims below.)

## 3. The Neuro-Symbolic Compilation Pipeline (the "How")
*   **Symbolic parsing & WSD:** classical NLP + the *semantic-native anchor resolver* (surface word → nearest of a small anchor set), and the *sense-bridge* threading WordNet synsets through to the tensor.
*   **The `TKZip` tensor:** anatomy of the 3237-dim per-role representation (markers + 2925 semantic + spacetime).
*   **Negation & identity, honestly:** how the engine treats antonyms (measured-not-opposite vectors) and algebraic `NOT` — *and where this is still fragile* (WSD sense-number mismatches; thin grounding). An *approach*, not a "solution".

## 4. The Evaluation Engine & Knowledge Base
*   **3-tier memory:** definitions, axioms, theorems (+ the time-series memory log).
*   **Fuzzy fusion & intra-statement consistency:** `[0,1]` operators, `tanh`, Gödel implication, the crisp-enumeration self-contradiction kernel (the "red light").
*   **Inter-statement inference:** taxonomic `is_a` grounding, **conservative tiered disjointness** (why refutation must be the cautious one), `part_of` mereology, and multi-hop forward-chaining.
*   **The grounding-truth discipline (a core finding):** geometry leaking into the truth verdict was the dominant failure class; the fix is that a bare identity claim is decided ONLY by the graph, else **INSUFFICIENT**. *Distinctness is learned, not logic* — "a cat is a dog" is logically agnostic absent knowledge.

## 5. The Autonomous Brain (the "Who")
*   **Dynamic priority routing:** the single coordinator over Actions > Priorities > Thinking, one bounded unit/tick, cooperative yield.
*   **Two growth engines:** *Wondering* (grows the KB INWARD — derives theorems; converges via dedup — "mull until quiet") and the foreseen *self-reflection* (grows it OUTWARD — internalises trusted testimony; the analytic/synthetic line). The KB-derived vs. world-given distinction.
*   **Self-knowledge as DERIVED, not declared:** tokeniko is seeded "I think" + a property-cogito and *proves* "I exist" itself — its first theorem. (A small, honest study of machine self-modelling.)

## 6. Implementation & the "Centaur" Methodology
*   **Stack:** MongoDB (vector search) + Bunnet, FastAPI, Python, spaCy/Stanza, Ollama; atomic queue transitions.
*   **The multi-species dev team (told from the inside):** a human architect + a general LLM orchestrator + specialised LLM crews + edge SLMs — the orchestrate / delegate / **verify-the-crew** pattern, including its failures (a cut-off agent, an unreviewed change re-verified by hand).

## 7. Empirical Results: the Long-Wondering Soak (a measurement PROTOCOL, not a hope)
*   **Setup:** tokeniko left alone with its KB and no external input; instrumented.
*   **Metrics:** theorem **yield** over time, **validity rate**, the **false-theorem rate** (must be ~0 — logic-is-sacred), time-to-quiescence (the dedup fixpoint), and a **fragility regression baseline** (the 54-probe battery).
*   **Regimes to characterise:** convergence vs. divergence vs. **drain** (sterile re-circulation). A drain is a *result*, not a failure — it would empirically bound what pure derivation can generate and argue for the open-world organs (senses, dreams).
*   **Honest bottlenecks:** KB-reload cost, WSD/graph-coverage gaps, identity-context fragility — reported, not hidden.

## 8. Future Horizons & Conclusion
*   **Trusted learning (KB growing outward) & dreams:** synthetic axioms from trusted testimony + stochastic dream recombination — the foreseen anti-drain organs (see `doc/ref/kb-growing-outward.md`).
*   **The species horizon (a hypothesis, not a claim):** many bodies sharing a logic floor + abstract KB, diverging into individuals — the *experiment* we get to run if the single self proves real.
*   **Conclusion:** a proof-of-concept and an open research program for logical, persistent AI entities — offered with its failures attached, because the failures are the map.

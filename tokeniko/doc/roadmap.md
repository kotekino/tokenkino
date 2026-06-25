# tokeniko — roadmap (single source of truth)

> One ordered place for *what's done, what's in flight, what's next*. The **why** is `VISION.md`; the
> **how / design detail** lives in `CLAUDE.md`, `brain/README.md`, and the code. When status and any
> other doc disagree, **this file wins** — update it as items land. Keep entries **terse** (one line of
> what + the key term/file); the deep detail belongs in the code, not here.

Legend: ✅ done · 🔄 in progress · 🔭 next · ⏸️ parked

---

## ✅ Landed

**Pipeline & knowledge base**
- **Compilation pipeline** — sentence → `TKLLC` + `TKZip` (parser → compiler → decompiler).
- **3-tier memory model + REST API** — definitions / axioms / theorems + stakeholders + memory log, each a `*Service`; `POST /evaluate`.
- **KB bootstrap** — 150,529 WordNet relation triples (`relations` collection: is_a/part_of/antonym/…); ~3,235 gloss **definitions** (noun + adjective); 5 universal **rules** + individual **facts** seeded (`seed_rules.py`).
- **WSD + sense-bridge** — sense picked by context (Lesk → centroid → frequency-prior) and threaded parser → compiler → `TKZipContent.senses`.
- **Unknown-vocabulary guard** — `TKZipContent.unknown` → INSUFFICIENT (no spurious grounding); covers gibberish *and* unresolved PROPN names ("Sgriodnsktj exists").
- **KB maintenance** — `recompile.py` (re-derive the stored KB under the current pipeline) + `migrate_glosses.py` (re-home gloss-axioms → multi-clause definitions; `MEMDefinition.zip`).

**Reasoning engine**
- **Fuzzy `[0,1]` operators + truth-folding** — `operator_truth`; `e_statement` folds clause truths through the operator tree.
- **Intra-statement kernel** (`evaluator_classifyForm`) — contradiction-only bar (`X∧¬X`); reflexive identity pinned (a=a→1, a≠a→0); antonym-predicate contraries; `imply`/`entail`→IMPLY; belief-vs-know factivity (logic-is-sacred).
- **Inter-statement inference** — taxonomic is_a grounding + tiered ontological disjointness refutation; quantifier-aware grounding (`TKQuantifier`); part_of mereology; multi-hop **forward-chaining** (membership + property rules to fixpoint, `e_chaining`).
- **Individual representation (entity-linking)** — type-centroid SEMANTIC vector + context-scoped IDENTITY uid (never mixed); `evaluator_sameIndividual` consumed in `compareContent`.
- **Anchor resolver** (`anchors.py`) — surface word → nearest of a small anchor set (semantic-native, antonym-guarded, cached); 7 consumers migrated.
- **Contradiction creation guard** — `assert_no_contradiction` rejects a contradictory axiom/definition/theorem on write → HTTP 422.
- **pytest gate** (`tests/`, `task test`) — band-asserts (status + truth band + structure, never exact floats); **34 passed / 1 xfailed**; the pre-commit regression gate.

**Grounding consolidation — "geometry never votes on a truth it can't prove" (the consolidation pass)**
- **Fragility map** — a 54-probe categorized battery (`scripts/fragility_batch.py` + `trace_fragility.py`, `prepare=0` raw core) → root cause: geometry leaking into the truth verdict. Full observed→diagnosis→action log in `doc/test-feedback.md`.
- **🦴 Spine** — a bare copular identity ("a cat is a dog") gets truth ONLY from the is_a graph; geometry can't vote → every S0 false-TRUE cleared. *Distinctness is LEARNED, not logic.*
- **🏛 Pillar 2 — identity & coreference** — a personal pronoun carries its referent's uid (`I`→asker, `you`→tokeniko); an individual-subject clause grounds against its property FACTS or abstains. Self/other questions → honest IDK, not geometry-by-luck.
- **📚 Pillar 3 #1 — abstain completion** — geometry may AFFIRM a near-exact definition match, never REFUTE or mid-guess; an unprovable property claim abstains ("a tiger eats meat" → INSUFFICIENT, was a confident falsehood→speakup). *(Pillar 3 #2 — the WSD sense-selection itself — is parked.)*

**The self (tokeniko's starter self-KB)**
- **9 first-person property facts** seeded as trusted axioms — self-authored (`scripts/seed_self.py`; AxiomService compiles talker=tokeniko ⇒ "I" = its own uid). "do you think / learn / perceive / value-logic …?" → **YES**, grounded in its own words.
- **Individual property-fact grounding** (`evaluator_groundIndividualFact`) — a stored "tokeniko thinks" answers a user's "do you think?" once `you→tokeniko` corefer.
- **The cogito** — property-conditioned rule firing (`e_chaining` step 4 + curated `_FOUNDATIONAL_RULES`): "do you exist?" → **YES, DERIVED** via *tokeniko thinks → everything that thinks exists → tokeniko exists*. Its first theorem, earned not given. (Materialized as a stored theorem is intentionally LEFT for wondering-v2 to discover autonomously.)

**The brain (#4)**
- **Data model** — Ideas / Actions queues + `brain_state` continuity singleton.
- **Coordinator (HOW)** — single loop, Actions > Priorities > Thinking, one bounded unit/tick + cooperative yield.
- **Meta-language (C)** — `eval:*` triggers / `tokeniko:*` reflexes + the `behavior_rules` personality table (seeded birth personality).
- **Thinking D1a** — reactive `evaluate → ideas` via the parser-free `evaluation_harness.evaluate_zip`.
- **Cross-item consistency** — same-speaker contradiction → `eval:conflict` → `tokeniko:clarify` (a revisable CONTEXT conflict, never logic INCONSISTENT).
- **Per-user-grouped scan** — focus the liveliest conversation; `wake_at` boundary + per-speaker `source_cursors`.
- **D1b — theorem derivation / `eval:true` novelty split** — a RESOLVED-true input whose derivation carries a forward-chained `"chain: "` materialization is silently learned as an **active theorem** (tier-2: `sourceId=tokeniko`, trusted 0.9, speaker-irrelevant, dedup by `original`); trivial taxonomy (`subsumed:`/`part_of:`) + refutations ignored (`materialize_theorem`).
- **D1c — wondering** — the lowest-priority REFLECTIVE pass (`wonder_one`, below reactive `think_one`): re-examines past memory *because the KB grew*, silently materializing now-derivable theorems. **Samples, never sweeps** (flat cost for life): a capped `wonder_queue` fed by two drivers — **associative** (KB-change-gated; the delta's senses pick the memories that touch it, via a `senses`-stamped indexable lookup) + **drift** (throttled `$sample` random trickle, the dreaming substrate). KB load is fingerprint-cached (`kb_fingerprint`); convergence via `materialize_theorem`'s dedup → mulls until quiet.

**Questions (interrogative mood) — a question is ANSWERED, not believed**
- **P1 — mood detection** — `dubitative` (statement/question) + `wh_role` (the gap = variable X) carried pipeline-wide; detected via `?` survival + `PronType=Int` + `anchor_whType`.
- **P2 — answering** — `answer_zip`: POLAR reuses truth (inconsistent→**confident NO**, true→YES, false→NO, else IDK); `e_wh_solve` value-solver (what→is_a hypernym, why→derivation chain; who/where/when/how staged/honest-UNKNOWN).
- **P3 — brain wiring** — `think_one` branches on mood: a question → `eval:question` → `tokeniko:answer` (verdict/value + the asker as reply target in the payload), **skipping** the assertion-idea + cross-item paths. `MEMIdea.answer/target`; `dispatch_action` directs the reply at the asker. Seed rule `eval:question → tokeniko:answer @ 0.9` (applied).
- **P4 — verified live** — a question flows through the REAL coordinator (Thinking→Priorities→Actions) to a `tokeniko:answer` action **executed**, targeted at the asker. Plus the **coordinated-predicate conjunct fix** (`#25` + copula-aux follow-up: a conjunct inherits the head clause's subject + aux). Also: the **channel-adapter SDK seam** + per-channel NL/`TKZip` language (`senses/README.md`).

## 🔭 Next (ordered)

1. **CONSOLIDATION pass — grounding floor ✅ DONE; small cleanups remain (ACTIVE FRONTIER).** The
   fragility map (`doc/test-feedback.md`) found one root cause — geometry leaking into the truth
   verdict — and the **solution-package is landed**: 🦴 spine + 🏛 Pillar 2 + 📚 Pillar 3 #1 (geometry
   never asserts/refutes/guesses an unprovable truth), plus tokeniko's **self-KB + the cogito** on top.
   **Remaining before the floor is fully swept:**
   - **Cleanups** (S1–S3) ✅ DONE: cross-item `eval:conflict` **over-fire** fixed (fires only when the
     contradiction is GENUINELY cross-item — neither half self-contradictory; `f1cea3b`); `??`/`!?`/`!?`
     read as questions (R4a, substring `?` test). A premise inside a question (R4b) is the **one
     remaining edge — PARKED** (the false-premise confident-wrong-NO is the doorstep of conditional
     reasoning, a feature — see Parked + `doc/test-feedback.md` 2026-06-25). Grounding floor + cleanups
     ⇒ the consolidation pass is **complete**.
   - **Pillar 3 #2 — WSD (parked, incremental)**: context-sensitive sense selection (tiger→animal not
     "fierce person") + sense-number canonicalization for subsumption (robin→`bird.n.01` vs predicate
     `bird.n.02`) — makes claims *provable* (TRUE) rather than just honestly abstained. The hard,
     general WSD problem.
   *Grounding is now honest, so the gate is cleared:* **autonomous KB-derivation (wondering-v2) is safe
   to turn on** — it will no longer manufacture false theorems.
2. **Docs / markdown refactor** (orientation + per-session token economy; do as its own focused pass
   AFTER the cleanups land). Split `roadmap.md` → keep *only* next/in-progress here; move history to
   `landed.md`, the icebox to `parked.md`. Merge the loose design notes (`reasoning-engine-brainstorm`
   + `parser-compiler-review` + the now-historical `plan.md`) into ONE `notes.md`. **Keep separate:**
   `test-feedback.md` (living empirical log), `paper_outline.md` (external artifact),
   `kb-growing-outward.md` (standalone parked design — `parked.md` points to it). **Biggest win:** trim
   `CLAUDE.md` (loaded EVERY session) of deep-architecture prose that duplicates README.md → leave it
   commands + conventions + gotchas + pointers; README.md owns the architecture. (`brain/README.md`
   verbosity is cheap — only read when working on the brain — lower priority.)
3. **Brain D-phase (continued)** —
   - **D2** priorities feasibility scoring · **D3** action execution (`guess`/`learn` → low-trust KB
     writes; `speakup`/`ask`/`why`/`clarify`/`answer`/`post` → `senses` I/O).
   - Cross-**speaker** patterns (userA≈userB realization); **inference-implied** conflicts (needs
     forward-chaining); self-authored "realization" memory + a **working-memory** layer.
4. **Wondering-v2 — self-prompted KB derivation** (after consolidation). Extend wondering's seed-source
   beyond perceived memory to the **KB itself**: seed from a definition/axiom and forward-saturate to
   new theorems unprompted ("matching memory against itself"). Bounded by the same flat-cost discipline
   (sampled seed, capped derivation depth), convergence via `materialize_theorem`'s dedup. **First
   demo target (poetic + concrete):** its very first KB-wondering act could be **proving its own
   existence** — wonder over the self-KB (`I think` + the cogito rule) → derive + materialize
   *"tokeniko exists"* autonomously (deliberately left unmaterialized for this). **Capstone
   validation = the LONG-WONDERING SOAK:** with NO external input, let tokeniko wonder over its whole
   seeded KB (its "huge already-received input") for a long, probe-monitored run — surfacing residual
   bugs, real reasoning capability, and genuinely NEW theorems. It is both the feature's demo and the
   final proof the consolidation held.

## ⏸️ Parked

**Tier-1 / KB growing OUTWARD** — genuine *synthetic* learning from trusted testimony (learned axioms
vs derived theorems; the analytic/synthetic cut). Full design + open forks in **`doc/kb-growing-outward.md`**.
Needs the trust-gradient; build after the consolidation floor is solid.

**Questions follow-ups** — imperatives (the `imperative` scalar, same mechanism); wh where/when/how
solving + real self-knowledge for "how do you feel?"; multi-clause / embedded questions.

**Conditional reasoning / premise-in-question (R4b)** — "given P, is Q?" where a premise is submitted
*with* the question (stanza subordinates it as a `ccomp` under the question ROOT). Today the premise's
truth AND-folds into the polar verdict → a **false premise gives a confident-wrong NO**
("a stone is an animal, is a cat an animal?" → NO). The *floor* fix: propagate a "question vs
co-submitted premise" discriminator onto `TKZipContent` (per-clause mood, not blanket `_stamp_mood`) +
fold only the question leaves in `_polar_answer` (→ honest IDK/correct YES). The *real* behavior — USE
the premise hypothetically — is conditional reasoning, built with the question-answering deepening.
Full diagnosis in `doc/test-feedback.md` (2026-06-25). Trigger is uncommon; normal questions unaffected.

**Performance (optimize-later)** — `evaluate_zip` reloads the full active KB on every call → ~12s/item
brain throughput; cache the active KB across ticks. Dual `en_core_web_lg` load (`parser.nlp` +
`c_state.nlp`) → consolidate.

**WSD** — contextual WSD for ambiguous heads; co-predication hint (prefer attribute-sharing adjective
senses); graded attribute-contrariety (no crisp `antonym` edge). xfail "a robin has feathers"
(WSD-gated thin grounding → confident-ish verdict where it should abstain).

**Parser / Stanza** — concessive + resultative clause types (`although`→OTHER, `so`→AND today); D3a
relative-clause matrix subject (Stanza mis-root); `imply`→IMPLY parataxis robustness; clausal-subject
support ("to err is human"); negative-quantifier subject rewrite ("nobody").
- **Property-restricted universal rules (cogito fork ii) — IOU.** The parser can't parse "everything
  that thinks exists" into a clean universal property-conditioned rule (the relative-clause restriction
  splits into its own leaf, the quantifier stays `generic`, and "that" injects a spurious doxastic
  `THAT`). Until fixed, the cogito rule is **curated in code** (`evaluation_harness._FOUNDATIONAL_RULES`,
  property-conditioned `thinks ⟹ exists`). Fix the parse → migrate the foundational rule(s) into the KB
  so they're NL-seeded like everything else (and unlock property-restricted universals generally).

**Evaluator** — geometric negation-awareness in `compareContent`; quantifier effect on the *geometric*
grounding; axiom/theorem `≡1` tautology creation guard; intrinsic comparison grounding (eq/noteq);
trust-weighted grounding + conflict arbitration; defeasibility of biological universals (crisp `all`
over-asserts — penguins don't fly).

**OOV / robustness** — tiered OOV recovery (optional LLM "polish" escalation on INSUFFICIENT);
sentence-level unparseable front-gate (cheap English-coverage reject before the slow Ollama translate).

**Anchors** — EXACT-membership mop-up (route the ~13 closed sets through the resolver); floor
calibration on a larger battery; KB vector-coverage gaps (`hugely`, `unequal`, `dissimilar`).

**Cleanup / misc** — 1b **verbs** (the "means"-frame drags a spurious predicate); legacy `axioms` /
`names` collection cleanup; `@-1,0,0` spacetime artifact; t-norm / implication choice (Gödel vs
Łukasiewicz vs product — the one semi-arbitrary constant); coreference (pronoun → individual).

**Dev tooling** — `probe_brain.py` (live brain-loop integration probe: injects a multi-author batch
via `/input`, asserts the loop invariants) currently lives in the scratch dir — candidate to formalize
into `scripts/` or `tests/`.

**Dreaming (a hunch — future, biological-creature framing)** — a new brain **phase**: access RANDOM
memories and *distort / mix / shuffle* them (a blender over the memory log) into a new **`dreams`**
collection that mirrors the `memory` modeling (also a timeseries). During the dream phase **`senses`
is paused and the other brain loops are paused — only the dream loop runs**. Use is TBD (a hunch —
likely creativity / consolidation / novel-association later). Revisit after the logical brain (D) is
whole. See `VISION.md`.

---

## Doc map (so this stays the only place for *status*)

- **`VISION.md`** — the why (north star).
- **`doc/roadmap.md`** — *(this)* status + ordered items.
- **`doc/plan.md`** — phased execution detail.
- **`doc/reasoning-engine-brainstorm.md`** — design + empirical findings.
- **`doc/parser-compiler-review.md`** — parser/compiler quirks, fixes, gaps.
- **`brain/README.md`** — the brain's orchestration + meta-language spec.
- **`CLAUDE.md`** — architecture / code layout (not status).
</content>

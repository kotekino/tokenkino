# tokeniko — landed (the history)

> What's **done**. Moved out of `roadmap.md` so the roadmap stays the road *ahead*. Append here as
> items land (newest groups can go at the bottom of their area). The **why** is `VISION.md`; the
> **how** is `CLAUDE.md` / `brain/README.md` / `doc/notes.md` / the code.

---

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
- **📚 Pillar 3 #1 — abstain completion** — geometry may AFFIRM a near-exact definition match, never REFUTE or mid-guess; an unprovable property claim abstains ("a tiger eats meat" → INSUFFICIENT, was a confident falsehood→speakup).
- **📚 Pillar 3 #2 — WSD canonicalization (charitable is_a grounding)** — a copular taxonomic claim grounds TRUE when SOME sense of the subject-lemma subsumes SOME sense of the predicate-lemma, sidestepping WSD sense-selection errors at the grounding layer (a `senses_of` reader + a cross-product fallback in `_ground_relationally`, e_statement). "a tiger is an animal" (chosen `tiger.n.01`=person → canonicalized `tiger.n.02`) and "a robin is a bird" (predicate chosen `bird.n.02`=food → `bird.n.01`) now resolve TRUE. **Strictly conservative:** only upgrades INSUFFICIENT→TRUE on a REAL taxonomic path — never refutes, never fabricates ("a stone is an animal" finds no path → stays refuted/insufficient; "a cat is a dog" still abstains). The parser's stored sense is untouched (zero keep-set regression); storing the contextually-right sense everywhere is the harder general-WSD problem (`parked.md`).
- **Cleanups** — cross-item `eval:conflict` **over-fire** fixed: fires only when the contradiction is GENUINELY cross-item (neither half self-contradictory; `f1cea3b`). `??`/`?!`/`!?` read as questions (R4a, substring `?` test). **The consolidation pass is complete.** (R4b premise-in-question is parked → conditional reasoning; Pillar 3 #2 WSD is the next substantive item.)

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

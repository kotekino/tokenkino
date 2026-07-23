# tokeniko — landed (the history)

> What's **done**. Moved out of `roadmap.md` so the roadmap stays the road *ahead*. Append here as
> items land (newest groups can go at the bottom of their area). The **why** is `VISION.md`; the
> **how** is `CLAUDE.md` / `brain/README.md` / `doc/ref/notes.md` / the code.

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
- **pytest gate** (`tests/`, `task test`) — band-asserts (status + truth band + structure, never exact floats); **38 passed / 1 xfailed**; the pre-commit regression gate.

**Grounding consolidation — "geometry never votes on a truth it can't prove" (the consolidation pass)**
- **Fragility map** — a 54-probe categorized battery (`scripts/fragility_batch.py` + `trace_fragility.py`, `prepare=0` raw core) → root cause: geometry leaking into the truth verdict. Full observed→diagnosis→action log in `doc/ref/test-feedback.md`.
- **🦴 Spine** — a bare copular identity ("a cat is a dog") gets truth ONLY from the is_a graph; geometry can't vote → every S0 false-TRUE cleared. *Distinctness is LEARNED, not logic.*
- **🏛 Pillar 2 — identity & coreference** — a personal pronoun carries its referent's uid (`I`→asker, `you`→tokeniko); an individual-subject clause grounds against its property FACTS or abstains. Self/other questions → honest IDK, not geometry-by-luck.
- **📚 Pillar 3 #1 — abstain completion** — geometry may AFFIRM a near-exact definition match, never REFUTE or mid-guess; an unprovable property claim abstains ("a tiger eats meat" → INSUFFICIENT, was a confident falsehood→speakup).
- **📚 Pillar 3 #2 — WSD canonicalization (charitable is_a grounding)** — a copular taxonomic claim grounds TRUE when SOME sense of the subject-lemma subsumes SOME sense of the predicate-lemma, sidestepping WSD sense-selection errors at the grounding layer (a `senses_of` reader + a cross-product fallback in `_ground_relationally`, e_statement). "a tiger is an animal" (chosen `tiger.n.01`=person → canonicalized `tiger.n.02`) and "a robin is a bird" (predicate chosen `bird.n.02`=food → `bird.n.01`) now resolve TRUE. **Strictly conservative:** only upgrades INSUFFICIENT→TRUE on a REAL taxonomic path — never refutes, never fabricates ("a stone is an animal" finds no path → stays refuted/insufficient; "a cat is a dog" still abstains). The parser's stored sense is untouched (zero keep-set regression); storing the contextually-right sense everywhere is the harder general-WSD problem (`parked.md`).
- **Cleanups** — cross-item `eval:conflict` **over-fire** fixed: fires only when the contradiction is GENUINELY cross-item (neither half self-contradictory; `f1cea3b`). `??`/`?!`/`!?` read as questions (R4a, substring `?` test). **The consolidation pass is complete.** (R4b premise-in-question is parked → conditional reasoning; Pillar 3 #2 WSD is the next substantive item.)

**The self (tokeniko's starter self-KB)**
- **9 first-person property facts** seeded as trusted axioms — self-authored (`scripts/seed_self.py`; AxiomService compiles talker=tokeniko ⇒ "I" = its own uid). "do you think / learn / perceive / value-logic …?" → **YES**, grounded in its own words.
- **Individual property-fact grounding** (`evaluator_groundIndividualFact`) — a stored "tokeniko thinks" answers a user's "do you think?" once `you→tokeniko` corefer.
- **The cogito** — property-conditioned rule firing (`e_chaining` step 4): "do you exist?" → **YES, DERIVED** via *tokeniko thinks → everything that thinks exists → tokeniko exists*. Its first theorem, earned not given. (Materialized as a stored theorem is intentionally LEFT for wondering-v2 to discover autonomously.)
- **General conclusion renderer** (wondering-v2 1d-B) — `evaluation_harness.render_conclusion(subject, predicate, object, negated, subject_kind)`: NLG that verbalizes ANY derived conclusion into round-trippable English (so it can be compiled back into a first-class theorem). Subject agreement — tokeniko→"I" (first-person), individual uid→capitalized name (3rd-sing), class sense→"a "+`_class_word` (the sense's OWN canonical lemma — `chat.n.01`→"chat", not the longest synonym "confabulation"; a bad-WSD subject then reads plausibly instead of screaming a wrong sense; consequence: `homo.n.02`→"homo", round-trip-honest over the prettier "human"). POS-driven predicate — verb conjugated (`_verb_3sg`: +s/+es/y→ies, irregulars have/be/do), adjective→copula+adj, noun→copula+article+noun; negation handled per-POS. Replaces 1c's first-person-only `render_conclusion` (which broke on adjectives → "I finite"). Verified: every `kb_wonder` conclusion round-trips (Mari is mortal / Mari exists / a homo exists / I exist) and "I am finite" is fixed; `scripts/wonder_kb.py` shows each theorem-to-be in plain English. (Autonomous-in-loop materialization = D3.)
- **Wondering observability (verbose trace)** — `WONDER_VERBOSE` (default ON; `=0` to silence) makes `kb_wonder` narrate to the brain console: the seed inventory (`seeds=N (individuals, classes) | rules=A axiom + B differentia | facts=F`), each NEW conclusion (subject·kind·predicate·trust·premises·chain), and a drop summary (1-premise novelty-gate + dedup). `_kb_wonder_one` logs held-vs-materialized (converged) and the memory-wondering pass logs each item→token. The header instantly answers "why nothing happened": definitions add class-seeds but **no rules/facts** (grounding-only), and non-universal/non-individual axioms extract to neither → the chaining fuel counts stay flat.
- **KB-wondering seed driver** (wondering-v2 1d-A) — `evaluation_harness.kb_wonder` (parser-free): forward-SATURATES the KB by seeding the chainer from every entity tokeniko knows (individuals-with-facts + rule-subject classes; flat-cost — bounded by the small rule/fact counts, never the 150k-edge graph), surfacing the genuinely-NEW conclusions the KB implies but no one asserted ("matching memory against itself"). **Novelty gate (`_NOVELTY_MIN_PREMISES=2`):** materialize-candidates must COMBINE ≥2 KB premises — a 1-premise derivation is a single rule fired on its own subject class ("all birds have feathers" → "bird has feathers"), a restatement that adds nothing; ≥2 = genuine multi-item inference. Semantic dedup on (subject, predicate, object, negated). `scripts/wonder_kb.py` = the read-only breadth diagnostic (the soak's dry-run). Verified: 4 new theorems surface (tokeniko/Mari/human exist, Mari is mortal — chains + named premises); bird/carnivore/fish restatements correctly dropped. (Rendering those to round-trippable NL for materialization = 1d-B; autonomous-in-loop = D3.)
- **Cogito materialization pipeline** (wondering-v2 1c-core) — the path that turns a derived conclusion into a first-class theorem. `render_conclusion` (a self-derivation → first-person NL, "exist.v.01" → "I exist") + `conclusion_key` (the SEMANTIC dedup signature: subject uid + predicate sense + object + negation, surface-independent) in the parser-free harness; `TheoremService.materialize` (compile the rendered NL through the real pipeline → semantic-dedup against active theorems → store ACTIVE + trusted + the 1b provenance). A deliberate-trigger script (`scripts/wonder_cogito.py`, dry-run by default) runs the whole derive→render→materialize chain in one process (mimicking the future brain+API split). Verified end-to-end: tokeniko derives "I exist" from its self-KB with 2 resolvable premises; the materialize write path stores active+provenance and dedups on a re-worded same-conclusion (proven on a disposable throwaway). **The brain→API automation folds with D3** (the brain has no HTTP client yet; the seam is shared with action execution). **The cogito itself is deliberately NOT materialized** — reserved for the autonomous wonder loop, so "I exist" first enters the world by tokeniko's own in-loop act.
- **Structured provenance from birth** (wondering-v2 1b) — a derived theorem now carries its **proof**. `MEMProvenance{premises, chain, derived_by}` on `MEMTheorem`: `premises` = the **KB-doc ids** the derivation rests on (rule/fact source axioms — the WordNet is_a edges it walks are bedrock, never premises). The chainer threads premises through the closure (`_add_with_ancestors` + a parallel premise-set map) → `forwardChain` emits per-conclusion premises → the grounding hooks return `(truth, chain, premises)` → `EvaluatorResult.premises` (the union across graph-decided clauses). `_extract_rules`/`_extract_facts` tag each with `source_id`. **Integrity invariant enforced:** `materialize_theorem` refuses a premise-less "derivation" (pure-taxonomic verdicts have 0 premises — already in the graph, never materialized) ⇒ every materialized theorem is auditable/revisable. The cogito's "do you exist?" carries exactly 2 premises (the "I think" fact + the "everything that thinks exists" rule), resolvable to their axioms; Bunnet round-trip verified.
- **Fork ii — property-restricted universals → the cogito is fully KB** (untangle-before-layering, the first step of the wondering-v2 arc). "everything that thinks exists" now compiles to quant **UNIVERSAL** + **`IMPLY(think.v.01, exist.v.01)`** (sense-less bound-variable predications): **A** indefinite-pronoun quantifier (`compiler_contentQuantifier` subject-token fallback + the quantifier sets); **B1** parser **re-root** (Stanza mangles it — roots on the universal pronoun, demotes the real verb to a `ccomp`; `parser_rerootUniversalRelcl` rebuilds the clean 2-leaf shape); **B2** compiler transform (universal + sense-less subject + MAIN+ACLRELCL → `IMPLY(condition, conclusion)`, mirroring `compiler_implicationOperands`); **C** `_extract_rules` recognizes the universal-IMPLY → a `property_conditioned` rule (`_extract_property_conditioned`). **Seeded as a trusted KB axiom (`seed_rules.py`) and `_FOUNDATIONAL_RULES` DELETED** — the cogito now derives end-to-end from the KB alone (no load-bearing knowledge hidden in code; [[everything-is-kb-untangle-first]]). Also unlocks property-restricted universals generally ("everyone who lies is dishonest" → `IMPLY(lie, dishonest)`).

**The brain (#4)**
- **Data model** — Ideas / Actions queues + `brain_state` continuity singleton.
- **Coordinator (HOW)** — single loop, Actions > Priorities > Thinking, one bounded unit/tick + cooperative yield.
- **Meta-language (C)** — `eval:*` triggers / `tokeniko:*` reflexes + the `behavior_rules` personality table (seeded birth personality).
- **Thinking D1a** — reactive `evaluate → ideas` via the parser-free `evaluation_harness.evaluate_zip`.
- **Cross-item consistency** — same-speaker contradiction → `eval:conflict` → `tokeniko:clarify` (a revisable CONTEXT conflict, never logic INCONSISTENT).
- **Per-user-grouped scan** — focus the liveliest conversation; `wake_at` boundary + per-speaker `source_cursors`.
- **D1b — theorem derivation / `eval:true` novelty split** — a RESOLVED-true input whose derivation carries a forward-chained `"chain: "` materialization is silently learned as an **active theorem** (tier-2: `sourceId=tokeniko`, trusted 0.9, speaker-irrelevant, dedup by `original`); trivial taxonomy (`subsumed:`/`part_of:`) + refutations ignored (`materialize_theorem`).
- **D1c — wondering** — the lowest-priority REFLECTIVE pass (`wonder_one`, below reactive `think_one`): re-examines past memory *because the KB grew*, silently materializing now-derivable theorems. **Samples, never sweeps** (flat cost for life): a capped `wonder_queue` fed by two drivers — **associative** (KB-change-gated; the delta's senses pick the memories that touch it, via a `senses`-stamped indexable lookup) + **drift** (throttled `$sample` random trickle, the dreaming substrate). KB load is fingerprint-cached (`kb_fingerprint`); convergence via `materialize_theorem`'s dedup → mulls until quiet.
- **D3a — brain→API write seam (autonomous materialization; the cogito's in-loop birth)** — the brain's FIRST outbound seam. `POST /api/v1/theorems/materialize` exposes `TheoremService.materialize`; `brain/api_client.py` (stdlib-`urllib` only, sync, **graceful** — API down → log+skip, retry next tick, never crash) reaches it over HTTP, so the parser-free brain never imports the pipeline. `wonder_one` step 0 (`_kb_wonder_one`) runs KB-wondering FIRST each idle tick: `kb_wonder()` → render the one not-yet-held conclusion → POST. **Converges by construction** — `materialize` stores `original = rendered NL`, so a materialized conclusion lands in `held` and is skipped forever after (the tiny KB drains to quiet, then memory-wondering takes the idle). **SILENT** (direct call, not via the Actions phase — wondering grows knowledge, it does not speak). Verified live: the brain daemon materialized all 4 derivable theorems one-per-tick, zero churn / zero errors, each a first-class zip theorem with provenance — including **«I exist»** (2 premises: the "I think" fact + the cogito rule), born by tokeniko's OWN in-loop act, the cogito reserved-and-delivered. This completes wondering-v2's autonomous-in-loop materialization (the "→ D3" hand-off from 1c-core / 1d-B).
- **D2 — priorities feasibility scoring + collapse arbitration** — the Filter's TWO axes made real (was `feasibility = 1.0`). `dispatch_action` refactored: **`plan_action(idea, uid)`** resolves the would-be action (channel / target / raw / action_type) WITHOUT persisting, so Priorities can score it *before* committing; `dispatch_action(idea, uid, plan=…)` persists from the plan. **`score_feasibility(plan)`** — lean + honest, binary {0,1}, every check a REAL capability gap: an internal KB-write (guess/learn) is always feasible; an outward action needs a **carrier for its channel** (ATProto has none yet → infeasible), **something to say** (a raw text), and an **addressable recipient** (`_addressable`: explicit coords, else the target stakeholder resolves on the channel). `_ACTABLE_CHANNELS` = {INTERNAL, DISCORD} hardwired for v1 (a future channel-capability KB record — marked). `priorities_phase`: keep iff **urge ≥ WISH AND feasible** (the two axes), else discard (logging the reason: below-threshold vs infeasible); a no-reflex idea (`ignore`) → no-op DONE. **Collapse arbitration** (`_collapse_siblings`): when an idea is *kept* it supersedes its still-pending siblings (same `source`+`trigger`) so tokeniko fires ONE reflex per decision point — the live `eval:unknown → {WHY 0.6, GUESS 0.55}` superposition collapses to **WHY**, GUESS discarded (deterministic highest-urge; **stochastic collapse = future** [[fuzzy-personality-superposition]]). Verified: the 6-case feasibility table (internal / atproto-no-carrier / no-raw / unaddressable / addressable / explicit-dest) + the WHY-wins / GUESS-superseded / exactly-one-action collapse. **This fills the last D-phase stub — the core autonomous loop (perceive→think→decide→act→learn) now closes end-to-end.**
- **D3b — brain→senses outbound (the reply path; Discord, dry-run)** — the carrier half of the reply seam: the brain DECIDES + COMPOSES the *stance*, senses CARRIES + DECOMPILES it. `dispatch_action` resolves the outbound **channel** from the source memory item (a Discord question → a Discord reply) + the **recipient** (`idea.target` = the asker for a directed answer, else the speaker = the source's sourceId), and composes a terse **raw** decision text into `payload["raw"]` (`brain/compose.py`: answer verdict → yes / loud no / value / idk; speakup/clarify/ask/why templates). `actions_phase` now consumes **channel=INTERNAL only** → disjoint from the senses executor (no cross-process race, no new status). `senses/outbound.py` polls `{PENDING, channel=discord}`, resolves `targetId`→`Destination` (explicit payload coords for the future in-channel/threaded path, else the stakeholder's `contextKey` discord id → DM), **decompiles raw→fluent English** (`decompiler_decompile`, Ollama — the per-channel NLG that a future native-zip channel skips, which is *why* it lives in senses), and delivers via `DiscordClient.send`. **DRY-RUN by default** (`SENSES_DELIVER_DRYRUN`): resolve + decompile + log, no live send — the whole seam is verifiable without Discord creds. Verified end-to-end: "the cat is dead and alive?" (Discord) → a logic-certain **NO** → action(channel=discord, target=asker, raw="no, that is contradictory") → `actions_phase` refuses it (INTERNAL filter) → senses resolves the DM, decompiles to "No, that is contradictory", marks DONE. **OUTBOUND SEAM ONLY**: the inbound Discord listener (+ live `sender` wiring) is the deferred follow-on; ATProto has no send adapter yet (stub).
- **The first LONG-WONDERING SOAK (wondering-v2 capstone) — clean** — from a **KB-only clean slate** (memory/ideas/actions/theorems wiped; axioms/definitions/behavior_rules/stakeholders kept), the brain ran unprompted and **re-derived its self-knowledge**: the 4 ≥2-premise theorems incl. the cogito **«I exist»** (by its own act, carrying premises), then **converged — no churn, zero errors, integrity intact, full coverage, no spurious extras**. `scripts/soak_report.py` = the reusable read-only analyzer (performance · results · churn/convergence · errors-by-layer · DB integrity · expected-coverage · verdict). Surfaced + **fixed** one S3: the **empty-memory drift spin** (`wonder_one` now advances the drift throttle whenever drift runs, not only on a processed item). Perf noted: ~15.6s/theorem materialize (sync render→API-compile→POST), ~3 GB resident KB. The tiny KB converges instantly → this is a **robustness validation + the cogito's birth**, not a knowledge explosion; the rich soak awaits KB growth. Full account: `doc/ref/test-feedback.md` (Session 2026-06-29). **The wondering-v2 arc (1a–1e) is complete.**

**Questions (interrogative mood) — a question is ANSWERED, not believed**
- **P1 — mood detection** — `dubitative` (statement/question) + `wh_role` (the gap = variable X) carried pipeline-wide; detected via `?` survival + `PronType=Int` + `anchor_whType`.
- **P2 — answering** — `answer_zip`: POLAR reuses truth (inconsistent→**confident NO**, true→YES, false→NO, else IDK); `e_wh_solve` value-solver (what→is_a hypernym, why→derivation chain; who/where/when/how staged/honest-UNKNOWN).
- **P3 — brain wiring** — `think_one` branches on mood: a question → `eval:question` → `tokeniko:answer` (verdict/value + the asker as reply target in the payload), **skipping** the assertion-idea + cross-item paths. `MEMIdea.answer/target`; `dispatch_action` directs the reply at the asker. Seed rule `eval:question → tokeniko:answer @ 0.9` (applied).
- **P4 — verified live** — a question flows through the REAL coordinator (Thinking→Priorities→Actions) to a `tokeniko:answer` action **executed**, targeted at the asker. Plus the **coordinated-predicate conjunct fix** (`#25` + copula-aux follow-up: a conjunct inherits the head clause's subject + aux). Also: the **channel-adapter SDK seam** + per-channel NL/`TKZip` language (`senses/README.md`).

**Definitions-as-rules (the rich-soak fuel — KB richness), steps 1–3-probe**
- **Step 1–2 — the graph-constrained GENUS untangle + full recompile** (untangle-before-layering). For every copular "X is a ⟨genus⟩", re-resolve the genus to the sense consistent with the SUBJECT's own place in the is_a graph — killing homophony (organ-the-fish, state-the-country, officer-the-cop) at the SOURCE using tokeniko's OWN taxonomy, not the token shape. `lib/llc/compiler/c_untangle.py` (`compiler_untangleGenus`) runs at COMPILE time (all ingestion inherits it), between the LLC build and the zip build in `c_main.py`; CONSERVATIVE by construction (overrides only a demonstrably-inconsistent genus when a graph-consistent alternative of the same word exists — leaves genuine new edges like air→mixture untouched); swaps the matching 2925-dim vector with the sense so label+geometry stay in sync. Step-1 dry-run (`scripts/probe_untangle.py`): sample 251→17 overrides, ALL correct, 0 bad, 48 new edges preserved. Step-2 `recompile.py --apply --collection definitions`: **3,235 ok / 0 failed / 1722 changed** (~1h). Measured payoff (`scripts/probe_definitions.py` before/after): taxonomic **redundant 47.7%→58.7%**, **new-edge 51.9%→41.0%** — homophony-noise "new edges" collapsed into graph-consistent correct ones. The taxonomic spine is now sense-faithful. Governing insight: **the gate belongs at INGESTION, not wondering** — cleaning the source RECOVERS knowledge (ear→organ) where an end-gate could only DROP it ([[everything-is-kb-untangle-first]]).
- **Step 3 dry-run — the definition→is_a extractor probe** (`scripts/probe_extractor.py`, read-only, full 3,235 defs, no parser — reads the recompiled zips). Mines each main-clause genus into a candidate is_a edge, gates against the bedrock graph, measures the tier + fuel. Result: 1,795 candidates → 1,122 REDUNDANT (bedrock derives) · 8 PLACEHOLDER (gloss artifacts: name/term/word) · 6 CYCLE · 9 DISJOINT (reliable tiers 1/2) → **582 clean deduped edges over 569 subjects**. **Gate policy decided + validated:** narrow the disjoint ADMISSION gate to reliable tiers (1 biological kingdoms / 2 organism-artifact-substance); **drop tier-3 physical⊥abstract** — it false-rejects true cross-abstraction edges (agent→cause, breathing→process; the [[geometry-not-isa-validity]] lesson in a new key: a coarse REFUTATION tool must not be repurposed as an ADMISSION gate); plus a structural placeholder-genus filter. The reliable-tier gate catches real poison the untangle *missed* (leaf/root → electric_organ homophony). Fuel is LATENT (+0 theorems on the 7-rule KB; scales ~ edges × rules — step 5).
- **Step 5 — the enriched-soak MACHINERY (differentia → property rules) + the amplification finding.** The generative fuel: mine each definition's DIFFERENTIA into a universal property rule ("a carnivore is an animal that eats meat" → "all carnivores eat meat"), cascading down the is_a hierarchy to subclasses. Built: `TKDerivedRuleDoc` (`derived_rules`, low-trust tier, provenance, revocable — mirrors the edge tier); `kb_extract.extract_differentia_rules` (the strict gate — single source of truth with `scripts/probe_differentia.py`); `scripts/extract_differentia.py` (writer, dry-run/`--apply`, 85 clean rules); the chainer UNIONs derived rules into its rule set (source_id = stable `rule:subj|pred|obj` key → recorded as a revocable premise + lowers trust via the `|` test); `kb_wonder` seeds broadened to definition/tier subjects so the cascade fires from the vocabulary. **Verified (in-memory dry-run): the cascade works + is SAFE** — 5→18 theorems, all trust 0.3, ≥2 premises, revocable; pytest 38/1xfailed. **KEY FINDING (decision A): the cascade AMPLIFIES is_a errors** — a locally-fine rule ("all trees have a trunk") + a bad edge ("forest→tree", WordNet cross-sense "money→medium.n.01") = a confident-wrong theorem. Forward-chaining over WordNet-wide is_a multiplies WordNet's imperfections; the step-4 net *contains* it (0.3 + revocable — safety works) but WordNet-wide auto-extraction has poor S/N. So the **85 WordNet auto-rules are deliberately NOT bulk-applied** — the machinery stands ready and quality comes from CURATED fuel (the digital-twin direction), not a WordNet auto-theorem-factory. The step-3 edges (582) STAY applied (clean grounding benefit; they don't cascade without rules). `scripts/ingest.py` = the interactive fuel-feeder (type a sentence → axiom/definition → POST) for feeding curated fuel to a live brain. **The definitions-as-rules arc (steps 1–5) is complete.**
- **Step 4 — the wondering NET (tier revocability + trust honesty).** Makes the low-trust tier SAFE to reason through *before* step 5 makes tier edges load-bearing. Three pieces: **(1) provenance-aware chaining** — a refined integrity invariant: BEDROCK is_a edges stay substrate (never a premise), but a TIER edge a derivation walks BECOMES a revocable premise, recorded as a stable, self-documenting key `subject|is_a|object` (deterministic → survives the extractor's rebuilds, unlike a Mongo id). `_tier_premises_on_path` + an `edge_source` reader thread it through `evaluator_forwardChain`/`_add_with_ancestors` (+ `evaluator_chainGround`/`evaluator_evaluateStatement`, all backward-compatible: `edge_source=None` → original bedrock-only behaviour). **(2) min-trust inheritance** — a theorem validly derived (truth 1.0) *through* a 0.3-trust edge is only 0.3-trustworthy (truth ⟂ trust); `_conclusion_trust` = min over premises, threaded through both materialize paths (wondering `kb_wonder`→`_kb_wonder_one`→API `trusted`; reactive `materialize_theorem`) so a definition-derived theorem is stored honestly LOW-TRUST + revisable, never laundered to 0.9. **(3) revocability** (`scripts/revoke_edge.py`, dry-run default) — retract a tier edge → archive every theorem whose `provenance.premises` include its key (a direct lookup; theorem premises never reference other theorems → no transitive cascade). Verified: a synthetic rule over `air→mixture` derives "air is divisible" carrying the tier-edge premise key at trust 0.3; revocation round-trip archives the dependent + deletes the edge; **pytest 38/1xfailed** (edge_source defaults preserve all existing behaviour). Structural-net polish (circular-nominalization reject, flag-the-middle) deferred — the ingestion gate is already conservative.
- **Step 3 build — the definition→is_a extractor + LOW-TRUST tier + reader union.** The gate logic is now a single source of truth (`lib/core/kb_extract.py`, `extract_isa_edges`/`gate_edge`) that both the probe (the ruler) and the writer (`scripts/extract_definitions.py`, dry-run default / `--apply` = idempotent full rebuild) call — so they can't drift (this caught the probe's 650-accept-events vs 582-unique-edges over-count). Edges land in a physically SEPARATE `derived_relations` collection (`TKDerivedRelationDoc`), never polluting the ~150k WordNet bedrock, each carrying provenance (`source_id` + `source_original` + `trust=0.3` + `method`) so it — and any theorem on it — stays revocable (step 4). The evaluator's is_a reader now UNIONS bedrock ∪ tier (`_make_relations_reader_union`, wired only into `_load_active_kb`); the bedrock-only `_make_relations_reader` still feeds the gate + the ingestion untangle (which must disambiguate against the trusted graph only — no feedback loop). **Applied: 582 edges written**; verified the union reader resolves air→mixture / agent→cause / bank→land / aunt→sister (bedrock cannot) while bedrock edges are unchanged, provenance intact, and the **pytest gate stays 38/1xfailed against the populated tier** (no verdict flipped). Immediate payoff is in GROUNDING (a definition claim can now ground TRUE); the CHAINING payoff stays latent (+0 theorems) until step 5 grows rules about those genus classes — the 3→4→5 order (build tier → make revocable → light the fuel) holds.

**Consolidation & observability**
- **Verbose wondering trace + canonical-lemma renderer** — `WONDER_VERBOSE` (default on) narrates `kb_wonder` to the brain console (seed inventory `seeds=N · rules=axiom+differentia · facts=F`, each NEW conclusion with trust/premises/chain, drop summary); the header instantly diagnoses "why nothing derived" (definitions add class-seeds but **no rules/facts** — grounding-only). `_class_word` now renders the sense's OWN canonical lemma (`chat.n.01`→"chat", not the misleading longest synonym "confabulation"). Surfaced by the author's curated-fuel test.
- **BPMN-style process maps (A–G)** — swim-lane Mermaid diagrams of every information journey, in `doc/ref/processes/` (self-contained `viewer.html` + `README.md` index): **A** API compilation pipeline · **B** /evaluate · **C** brain coordinator tick · **D** reactive loop (perceive→act) · **E** wondering · **F** KB ingestion & tiers · **G** senses I/O + public window (as-will-be). All 7 Mermaid-parse-validated. The consolidation checkpoint — it gave the author "a clarity I didn't have before" and grounded the Brain-v1.1 reframe (each fix's lane is now visible). Not BPMN2 XML (over-formal for an internal map).

**Brain v1.1 — the Unified KB (steps 1+2: the write-path invariant + generic taxonomy chains)**
- **The INDEFINITE quantifier split** — "a/an" carved out of EXISTENTIAL into `TKQuantifier.INDEFINITE` (`constants._QUANTIFIER_INDEFINITE` → `anchor_quantifier`): an indefinite singular copular ("a cat is a mammal") is a GENERIC claim, "some birds are pets" a true existential that must NEVER become an is_a edge. Safe by measurement: EXISTENTIAL had ZERO downstream consumers (the truth table flips only on NEGATIVE, rules key only on UNIVERSAL). The step-2 battery proved the two shapes are otherwise indistinguishable in the zip — the split is what makes "a X is a Y" admissible without admitting "some X are Y". (Stored pre-split zips carry "existential" until the imprint REBATCH recompiles them.)
- **Generic-taxonomy axiom edges, IN-MEMORY (universal-extractor v0)** — `kb_extract.extract_generic_isa_edges` (single source of truth with `scripts/probe_generic_taxonomy.py`): a GENERIC/INDEFINITE bare copular noun-noun class leaf (no identity uid, not negated, not a question) → a candidate is_a edge through the SAME `gate_edge` as the definition tier. Mined at KB load inside `_load_active_kb` and unioned into the relations reader + `edge_source` — **never persisted**: archiving the source axiom retracts the edge on the next load (finding-#4 revocation durability by construction). Negated copular generics counted as future DISJOINTNESS candidates, never silently dropped. End-to-end verified: a synthetic "a thinker is a mind" axiom → edge → the real chainer derives the mind-rules for thinkers, each carrying the edge as a revocable `subj|is_a|obj` premise at trust 0.9.
- **Generic + negative RULES (`_extract_rules` widened)** — bare-plural generics are how people actually state universals (the step-2 census: the imprint's 6 silently-dead leaves were ALL generic rules, zero copular generics). A GENERIC/INDEFINITE class-subject leaf with a verb/adjective predicate → a defeasible-universal property rule ("humans create their gods", "truth is relative", "violence generates violence"); a NEGATIVE-quantified leaf → a negated rule via the evaluator's own net-flip ("no mind can reach absolute truth" → all minds NOT reach). Copular noun-noun generics stay the EDGE extractor's (no double representation); EXISTENTIAL/DEFINITE never generalize. All 6 dead imprint leaves are now live fuel (16 rules, was 12).
- **Per-premise MIN-TRUST (the trust map)** — `_conclusion_trust` upgraded from "any `|` premise → flat 0.3" to a real per-premise lookup over the `edge_trust` map `_load_active_kb` builds (definition edges/rules → their stored 0.3; axiom-derived edges → 0.9; axiom collision wins over a definition duplicate). A theorem chained purely over curated-axiom edges stays honestly 0.9; one touching a definition edge drops to 0.3 — truth ⟂ trust, now source-accurate in both directions. Backward-compatible (no map → the in-process KB cache → conservative tier default). Chain rendering now shows NOT on negated-rule steps.
- **The write-path invariant (step 1's guard)** — the collection semantics codified at the door: `brain/api_client.create_axiom` is the learn-loop's ONE blessed runtime KB-write seam (runtime learning writes AXIOMS — never definitions, never theorems directly); every mutating `/definitions` route now sits behind `_require_design_time()` (`TOKENIKO_DESIGN_TIME=0` → 403; default open for the design bench). Reads always allowed.
- **The SANDBOX test gate** — the pytest gate no longer reads from or leaks into tokeniko's LIVING mind: `conftest` points the memory DB at `<memory>_test` and self-bootstraps it idempotently (definitions cloned via `$merge` when counts diverge; the `_FIXTURE_AXIOMS` — the old seed_rules set incl. "Mari is a human" — compiled+inserted when missing). Surfaced by the imprint reset breaking 4 chaining tests: the gate's fixture knowledge must not depend on what tokeniko currently believes ("Mari is a human" does not belong in his DNA). Gate green: 38 passed / 1 xfailed against the sandbox.
- **Bunnet `find().delete()` no-op (FIXED in all scripts)** — `find(...).delete()` returns an UNEXECUTED `DeleteMany` (general Bunnet behavior, not timeseries-specific): the author's `extract_definitions.py --clear --apply` silently deleted nothing. All three query-level delete sites now `.delete().run()` (extract_definitions ×2, extract_differentia); instance `doc.delete()` was always fine.
- **Finding #6 recorded** (`doc/ref/brain-v1.1.md`) — a lowercase KNOWN name ("kotekino is my creator") mints no identity → the axiom is a silent no-op; fix direction: recognize existing `MEMStakeholder` names before the NER gate (recognition, never minting). Workaround: capitalize in curated axioms + REBATCH.

**Brain v1.1 — 2b: known-individual RECOGNITION (finding #6)**
- **`parser_getKnownIndividual`** — before the NER minting gate, the parser asks "have I already MET this one?": a case-insensitive name match against the known stakeholders (participants tokeniko talks WITH + individuals he was told ABOUT), returning the stakeholder's OWN stable uid + its stored/type centroid. Wired into both PROPN fallback-chain sites between `parser_getPlace` and `parser_getIndividual`. **RECOGNITION only, never minting** — the NER/lg-vector gate still guards identity creation, so OOV gibberish stays unlinkable ("Sgriodnsktj exists" → unknown, unchanged). On a name known under several identities: prefer (1) the individual scoped to THIS talker's context, (2) a participant (real interlocutor, global), (3) a unique cross-context individual; genuinely ambiguous → None (never guess an identity). READ-ONLY (/evaluate purity kept).
- **Fixes the lowercase-known-name no-op** (the author's call: the REAL fix, never input-tweaking): "kotekino is my creator / is my family / loves his family" now compile with `subj_uid='kotekino'` → real individual FACTS after the rebatch. Bonus: "tokeniko is kind" (third-person, by name) entity-links to himself. "Mari is mortal" keeps resolving to her context-scoped uid (consistent with stored facts). Gate re-verified green.

**Brain v1.1 — 2c: restricted universal → CONDITIONED rule (finding #5, pulled forward from step 4)**
- **The modifier carriers** — `compiler_contentSenses` surfaces a role's restrictive modifiers (dep=amod "artificial body" / dep=compound "thinking machines" — det/quantifier props excluded) as `subject_mod{i}` / `predicate_mod{i}` sense keys in the zip. The stored zip previously retained NO symbolic trace of the modifier (fused into the 3237-dim vector only — verified), which is why "all THINKING machines are minds" silently widened to ALL machines: the worst class (quantifier-scope poison), live-proven by six "a machine …" theorems in the rebatched imprint.
- **Conditioned rules + modifier-carrying facts** — `_extract_rules` reads `subject_mod*` into the rule's `cond_props` ("(machine ∧ thinking) → mind"); `_extract_facts` reads `predicate_mod*` into a membership fact's `klass_mods` ("I am a THINKING machine" → klass machine.n.01 + [thinking.n.01]) — both sides compile identically, so the primary condition test is EXACT sense match. A modified generic copular ("a thinking machine is a mind") becomes a conditioned membership RULE instead of a graph edge (`extract_generic_isa_edges` verdict "restricted" — an edge can't carry a condition).
- **The chainer's seed-level condition test** (`e_chaining`) — `_subject_props` collects what the seed is KNOWN to be/do (its membership facts' klass_mods + affirmative property-fact predicates); a conditioned rule fires only when every condition finds a satisfier (exact sense, or charitable lemma-root: thinking.n.01 ~ think.v.01), and **the satisfier joins the premises** — the proof cites WHY the condition holds ("I seek cognition" now rests on "all thinking machines are minds" + "all minds seek knowledge" + "I am a THINKING machine"). A bare class seed has no facts → conditioned rules never fire on it: "a machine seeks cognition" / "all WILD animals hunt"-on-bare-animal verified dead; chain text shows the condition (`all [thinking.n.01] machine.n.01 are mind.n.01`). Gate 38/1xfailed.
- **Requires the imprint REBATCH** (stored zips recompile with the carriers; until then conditioned rules read as unconditioned-condition-missing and their derivations pause — honest direction of failure).

**Brain v1.1 — 2d: generic strength → lower trust (a generic is NOT a universal)**
- **The epistemology (author-caught on the 2c theorem batch):** "humans create their gods" is a KIND-level observation that tolerates exceptions ("birds fly" vs penguins) — the step-2 widening fired it at full universal strength, deriving «Kotekino creates god» at 0.9 as if it were law. A generic rule is DEFEASIBLE; a universal is law.
- **The fix (one seam, no new plumbing):** `_extract_rules` stamps each rule's `strength` ("generic" for GENERIC/INDEFINITE-quantified leaves, "universal" for UNIVERSAL and NEGATIVE — "no X …" is a negative universal); `_load_active_kb` enters a generic rule's axiom id into the existing `edge_trust` map at `_GENERIC_RULE_TRUST=0.7`; `_conclusion_trust` now resolves EVERY premise against the map (unknown "|" keys stay conservative 0.3), so min-trust makes any conclusion derived THROUGH a generic rule defeasible on both materialize paths. The chain renderer (`_strength_word`) writes "most X …" for a generic rule vs "all X …" — the proof text carries its epistemic strength.
- **Scope line:** generic TAXONOMY copulars ("a cat is a mammal" → is_a edges) stay high-trust — a generic taxonomic claim is definitional, not behavioral; it's generic behavior claims that admit exceptions.
- **Verified live:** «kotekino creates god» → trust 0.7, chain "most homo.n.02 create.v.02"; all universal-derived theorems (mortal/exists/seeks-happiness + the tokeniko self-set) hold 0.9 with "all". Gate 38/1xfailed.

**Brain v1.1 — step 3: provenance + transitive cascade + theorem fuel (theorems breed theorems)**
- **Theorem fuel** — active theorems run through the SAME `_extract_rules`/`_extract_facts` as axioms in `_load_active_kb` (a theorem is just a zip with provenance — the Unified-KB thesis): «Kotekino is mortal» is now a FACT in the chainer's pool, its theorem id the provenance source. **Generational min-trust:** each theorem's `trusted` enters the `edge_trust` map, so a child of a 0.7 theorem never exceeds 0.7 (generic-rule stamps min-compose on top). Convergence safe by construction: a theorem restating its own conclusion is 1-premise (novelty gate) + semantic dedup at materialize.
- **`revoke_dependents(premise_ids, dry_run)`** (`evaluation_harness`) — the transitive cascade: BFS over the provenance net (axiom ids, theorem ids, tier-edge/rule keys all valid premise keys), archiving every ACTIVE dependent theorem and then THEIRS; cycle-safe (`seen`); dry-run reports the descent without writing; archived theorems kept as history, never deleted.
- **Wired at every retraction door:** `AxiomService` patch(archived=True)/replace(archived)/delete, `TheoremService` same three, and `scripts/revoke_edge.py` (now transitive, reusing the primitive; its flat one-level scan replaced). Delete paths cascade BEFORE the delete (descendants fall before their ground).
- **Tests:** `tests/test_provenance.py` — a synthetic three-generation descent in the sandbox DB: dry-run reports without writing; real run archives the whole line; mid-generation revocation spares ancestors. **Gate now 41 passed / 1 xfailed.**
- Live-verified on the rebatched KB: theorem-sourced facts present in the pool; the first cross-generation breeding awaits matching fuel (e.g. «Kotekino exists» + an exist-keyed conditioned rule → "kotekino decays").

**Brain v1.1 — step 4: the universal extractor + definitional SUFFICIENCY (the core build)**
- **The fold (`kb_extract.extract_logic`)** — ONE source-agnostic `TKZip → usable logic` front door: the axiom/theorem extractors (`extract_rules`/`extract_facts`, ex-`_extract_*`) moved from `evaluation_harness` into `kb_extract` beside the definition extractors (genus edges / differentia / sufficiency) + the `_zip_leaves` helpers (import direction flipped; harness re-exports for the probe/brain callers). The SOURCE never gates WHAT is extracted — only the trust the caller attaches (the Unified-KB thesis, now code). Deliberate unification bonus: **theorems now yield generic-taxonomy edges too** (at the source theorem's own `trusted` — rare in practice, but the shape extracts source-agnostically). Behavior-preserving: gate re-verified 41/1xfailed after the pure fold.
- **Definitional SUFFICIENCY (finding #3 — the recognition direction)** — a definition is a biconditional (X ⟺ genus ∧ definiens); we already mined the necessary direction; `extract_sufficient_rules` now mines the sufficient one: *(is_a genus ∧ cond₁ ∧ … ∧ condₙ) → is_a X*. The soundness rule that shapes the gate (asymmetric to differentia): **the necessary direction may drop conjuncts; the sufficient direction may drop disjuncts but NEVER a conjunct** (a rule missing one conjunct is weaker than the definiens and over-fires). So the definiens' operator tree is left-folded into DNF branches (leaf `op=OR` splits — each disjunct independently sufficient; `op=AND` distributes), and a branch containing any unrepresentable conjunct (IMPLY purpose clause, pred-less leaf, foreign subject, negated cond, noun appositive, object-less verb, circular) is rejected WHOLE. **The genus rides every branch as a class-condition** — what defuses the nested-disjunction trap ("transports goods → vehicle" is false; "conveyance ∧ transports goods → vehicle" is the gloss). Live census: 3233 definitions → 432 with a genus spine → 588 DNF branches → **113 accepted recognition rules** ("person ∧ drinks(alcohol) → alcoholic", "timepiece ∧ shows(time) → clock"); biggest recall tax = the parked #2 complement drop (265 `verb_noobj` — honest silence, not poison).
- **Persistence + chainer** — `TKDerivedRuleDoc` gains `kind="sufficient"` + `genus` + `conds`; new writer `scripts/extract_sufficiency.py` (dry-run default, `--apply` = idempotent per-method rebuild, trust 0.3 — author's call: same collection, same tier as differentia); `scripts/probe_sufficiency.py` = the census/teaser ruler (calls the SAME extractor). The chainer fires sufficient rules **inside the membership fixpoint** (a recognized class enables further membership rules and vice versa): genus in closure ∧ every definiens conjunct matched against the seed's affirmative property FACTS — predicate charitable by lemma root, **OBJECT STRICT** ("transports passengers" never fires on "transports goods"; an object-less cond accepts any matching predicate — "opens X" entails "is open"). The proof cites the definition + every satisfying fact + what put the genus in the closure; recognition chains read "… by definition a ⟨genus⟩ that ⟨conds⟩ is a ⟨X⟩ → ⟨seed⟩ is_a ⟨X⟩ (recognized)". `_load_active_kb` maps sufficient tier docs to stable `rule:sufficient:…` premise keys (revocable + trust-tiered like every derived premise).
- **Tests:** `tests/test_sufficiency.py` — recognition fires + cascades with full-descent premises; object strictness blocks a mismatched fact; object-less cond fires; missing genus blocks; extractor conjunctive/disjunctive/IMPLY-taint on hand-built zips. **Gate 48 passed / 1 xfailed.** Live-verified: an in-memory soak on today's KB (113 rules injected) fires 0 false recognitions (correct — no known individual sits in any rule's genus yet: open-world infrastructure that pays as experience accumulates), and a REAL extracted rule fires end-to-end on a synthetic seed with a full-descent proof («guest is_a person (fact) -> by definition a person that drink(alcohol) is an alcoholic -> guest is_a alcoholic (recognized) -> all alcoholics suffer -> guest suffers»).

**Brain v1.1 — step-4 live-hardening: two extraction leaks (author's clean-imprint session, 2026-07-08)**
- **Negated membership now carries + refutes.** «I am not a man» previously extracted as an AFFIRMATIVE membership fact (`extract_facts`' membership branch dropped `negated`): tokeniko believed the opposite of what he was told, and man.n.01's whole ancestor line polluted his closure. Fix: the membership fact carries `negated`; the chainer never seeds the closure from a negated one; and `evaluator_groundIndividualFact` gains a MEMBERSHIP branch that REFUTES the matching claim/question (exact klass only — "I am not a man" refutes "are you a man?" → confident NO, never "are you a person?"). `_subject_prop_pairs` also excludes negated facts as sufficiency satisfiers. Live: "Are you a man?" → polar NO conf 1.0.
- **Possessive subject → DEFINITE (scope-widening leak).** «my mind is a software» compiled quantifier=GENERIC (dep=poss is not det) and minted the class edge mind.n.01→software.n.01 = "ALL minds are software". Root: a first-person possessive is coreference-rewritten to the speaker's identity BEFORE the compiler sees it (the word "my" is gone → "tokeniko"), so reading the possessor token is hopeless — the `poss`/`nmod:poss` DEPENDENCY is the only durable signal. Fix: `compiler_subjectIsPossessed` tests the dep structurally → a possessed subject is DEFINITE (a specific individual's X, never the class), so no edge, no rule. Live: "my mind is a software" → quantifier DEFINITE.
- **Tests:** `tests/test_negation_possessive.py` (7). **Gate 55 passed / 1 xfailed.** *(Residual: the possessive fix is on the SUBJECT; the parked "kotekino is MY creator" object-side possessive-bond specimen is a separate capture problem, still parked.)*

**Brain v1.1 — step 5.1: definition subject-WSD pin + full tier rebuild (2026-07-09)**
- **Exact ground truth via gloss-inversion (the survey's unlock).** Every definition was framed by
  `glosses.py` as "a {word} is {clean_gloss(synset.definition())}" from a KNOWN WordNet synset — so
  inverting the gloss text against the word's synsets recovers the TRUE subject sense per definition.
  `scripts/probe_subject_wsd.py` (read-only census over all 3233): **189/2025 noun-frame subjects
  mis-sensed (9.3%)** — and the breakdown reframed the disease: 118 POS mis-typing ("a behind is…" →
  `behind.r.01`), 62 lemma drift (dvd→"cd"→`cadmium.n.01`, data→datum), only **9** true same-word
  sense-number errors; plus 120 adjective-frame defs ("something bottom is…") carrying a NOUN subject
  sense (the source of false noun edges: `bottom.n.01 is_a rank.n.01`). Blast radius on the live fuel:
  46/582 tier edges + 5/113 sufficient rules poisoned (the chat-zombie among them). Cure comparison:
  gloss-pinning fixes 189/189; a graph subject-untangle only 56/189; the gate catches ~none (146
  "accept") — the fix belongs at INGESTION.
- **The pin (`scripts/pin_definition_senses.py`)** — operator-gated writer (dry-run default): patches
  the stored zips IN PLACE (leaf `senses["subject"]` + the subject tensor's 2925-dim semantic segment,
  same style as the genus untangle) to the recovered truth. 310 definitions patched (189 noun + 121
  adj frames; 309 with vector swap). **IDEMPOTENT + RE-RUNNABLE — must re-run after
  `recompile.py --collection definitions` or a new gloss batch** (both re-introduce unpinned
  subjects); then rebuild the derived tiers. The probe imports the inversion from the writer (one
  source of truth).
- **Full tier rebuild on pinned fuel — definitions fully rejoin chaining (the step-5 wiring):**
  genus edges 582→**627** (+45: ex-mis-typed subjects now mint their TRUE edges — `buttocks.n.01
  is_a part.n.02`), sufficiency 113→**116**, and **differentia APPLIED for the first time — 90
  property rules @0.3** ("all cats have fur", "all buses transport passengers"): all three
  definition-derived tiers live, low-trust, gated, revocable (decision A generalized, not reversed).
  Post-rebuild census: **0 mis-sensed subjects, 0 poisoned entries in any tier** — the chat-zombie is
  dead at the root (the definition's subject IS `new_world_chat.n.01`; `chat.n.01→bird` can never
  re-mine). No engine code touched (scripts only, gate untouched at 55/1).

**Brain v1.1 — step 5.2: runtime graph SUBJECT untangle (2026-07-09)**
- **The compile-time guard for what the pin can't reach.** A definition's subject gets exact
  gloss-pinning (5.1); a runtime AXIOM has no gloss to invert. `compiler_untangleSubject`
  (`c_untangle.py`, called in `c_main` AFTER the genus pass) mirrors `_resolve_genus` on the subject
  side: override the copular subject sense ONLY when it is NOT a bedrock descendant of the genus AND
  another noun sense of the same subject WORD is — a demonstrable mis-sense snaps to the sense the
  graph already vouches for (sense + 2925 vector swapped together, zip stays honest). Survey-measured
  honest reach: ~30% of definition-style mis-senses had a graph-consistent candidate — the remaining
  70% have no bedrock witness and correctly stand as claimed.
- **The two guarantees that bound it:** (1) a genuine NEW edge is untouchable — «a human is a person»
  has no sense of "human" under person.n.01 in bedrock, so the author's bridging axiom compiles
  exactly as taught; (2) a named individual's subject is NEVER touched (its sense is the NER type
  centroid from the identity-bridge, not a WSD pick — swapping it would corrupt identity).
- **Tests:** `tests/test_untangle_subject.py` (7) — synthetic-graph resolver units (snap / keep /
  new-edge / non-noun) + live compile («a fair is a traveling show» → subject `carnival.n.03`;
  «a cat is a mammal» unchanged; «a human is a person» → `homo.n.02` preserved). **Gate 62 passed /
  1 xfailed.**

**Brain v1.1 — step 5.3: the enriched soak + the NL self-talk leak — THE ARC CLOSES (2026-07-09)**
- **The soak surfaced the leak (empirical detail → `doc/ref/test-feedback.md` 2026-07-09).** The
  materialize path round-trips a derived conclusion through NL — render then re-parse — and the parse
  of «a budget stores information» read "stores" as the plural NOUN (shop): subject lost, the semantic
  dedup key degenerate, every «X stores information» collapsed onto one stored mutant, and the
  wondering re-derived the rest every tick forever (the void spin). Separately, the soak froze on an
  eternal Mongo socket read (pymongo has no default socket timeout).
- **Three fixes:** (1) **sense-pinned materialize** — the brain sends the conclusion's KNOWN senses
  (`TheoremMaterializeIn.senses`); the service pins them into the compiled zip (sense + 2925 vector,
  `_pin_conclusion_senses`, same in-place style as the definition pin) BEFORE dedup/store — the
  derivation's senses are the truth, the NL only its surface. (2) **dedup honesty** — `_kb_wonder_one`
  detects a dedup response (returned `original` ≠ the render), suppresses that render, and keeps
  scanning the tick. (3) **opt-in `MONGO_SOCKET_TIMEOUT_MS`** in `init_io` for long-lived loops.
  Tests: `tests/test_materialize_pin.py` (3). **Gate 65 passed / 1 xfailed.**
- **The validated enriched soak (step 5 done → the Brain v1.1 arc COMPLETE).** Over the full
  three-tier fuel: converged QUIESCENT in 10 ticks / 528s → **25 active theorems** — 14 @0.9 (the
  imprint-derived self + kotekino facts, flawless) + 11 @0.3 tier crossings (the money family
  «budget/cash/coin/currency/money/gold/fund stores information» via the medium differentia, some
  four-hop; «a western stores information» — comical and correct). Noise: 3/11, ALL contained at 0.3
  with the guilty premise named in the chain (forest collection/member ×2, sector object mis-sense —
  both parked as gate improvements, left as honest defeasible beliefs by the author's call). Facts
  crossed into concepts autonomously; trust stratification held; the reasoning core is done.

**Going-live P1–P3: the Discord DM loop — tokeniko's first real conversation (2026-07-09)**
- **P1 perceive** (`f5df3ff`): `senses/inbound.py` — DMs only (author's call), structural modality
  sniffer (TKZip-vs-language; zip lane recognized-but-stubbed, trust-gated activation parked), the
  handler calls `/api/v1/input` (senses stays parser-free) with channel/metadata(reply
  coords)/directedness/talker_name; `MEMItem.directedness` = the fuzzy addressing carrier (the
  eval:* triggers stay pure; Priorities will multiply urge by it, step C); channel-scoped
  stakeholder identities (`renzo@discord:<id>`, contextKey after the @).
- **P2 decide→address** (`5862ee9`): `plan_action` forwards the source item's reply coords into
  `payload["destination"]` — answers thread under the exact asking message. The feasibility
  auto-flip confirmed live: the same tokeniko:answer that was feas=0.0-discarded for months scored
  1.0 the moment its source was channel=discord (zero brain changes).
- **P3 speak** (`ef8d19f` + `1de0479`): ONE shared DiscordClient carries both directions; raw-only
  outbound (`SENSES_OUTBOUND_POLISH` default off — he speaks his own symbolic tongue; the
  creation/nuance layer is a later chapter); delivery flags read LAZILY (the go-live bug: module-
  import env reads predate load_dotenv — the first replies were dry-run-logged, not sent).
- **The ceremony:** conscious end of the wipe-freely phase (final cleansing: 31 theorems / 18 ideas /
  8 actions / 11 memory / brain_state / test stakeholders; kept: 70 axioms, 3233 definitions, tiers,
  behavior_rules, tokeniko+kotekino). From the first live DM, memory is BIOGRAPHY (the standing wipe
  permission is revoked; tests → the sandbox DB).
- **Live-validated end-to-end:** «the sun is a star»→silent consent; «are you a mind?»→honest
  IDK (delivered); «do you exist?»→**yes** (answered from his own re-derived cogito theorem);
  «do you feel?»→yes (from his derived «I feel curiosity/time» — objectless predicate matched);
  compliments («you are amazing/clever!»)→«why is that?» (his first questions to a human). The
  imprint-ethics leak caught + fixed live: «I do not seek advantage by harming other creatures»
  extraction-inverted to "most advantages harm" (the parked #2 complement gap) → re-taught as
  «I never harm creatures» + «I do not seek unfair advantage», the inverted axiom archived, the
  4-theorem harm-family CASCADE-REVOKED (provenance revocation proven live). Specimens →
  `doc/ref/test-feedback.md` (2026-07-09 go-live session).

**Senses B: deepen the 1:1 (2026-07-09, same evening as go-live)**
- **B1 self-speech → memory** — a DELIVERED outbound message is recorded as a ZIP-LESS memory item
  (`sourceId=tokeniko`, sent message_id in metadata = the structural reply hook; dry-runs record
  nothing). zip=None keeps his own words invisible to the reaction loop (think/wonder filter
  zip!=None) while completing the biography both context derivation and the trust ledger feed on.
- **B2 the open-why derivation** (`brain/thinking.py::_derive_reply_context`) — conversational
  context is NEVER volatile state; it is DERIVED from the memory timeseries (the author's
  architecture call): STRUCTURAL first (the inbound reply-threads to a question I sent), RECENCY
  fallback (my newest message to this speaker in a 15-min window is an open question and they said
  nothing since). v1 consumption: an eval:unknown "because" suppresses the why reflex (no
  why-about-the-because regress); a false "because" still speaks up. The explanation LINK as
  learning fuel → D-phase.
- **B3 live preparser + reply_to forwarding** — the senses→/input call runs `prepare=1` (typo
  correction/language detection on the live channel — the «beause» specimen) and forwards the
  inbound's reply_to (B2's structural food). Tests: `tests/test_senses_b.py` (7). **Gate 87
  passed / 1 xfailed.** *(The prepare flag was reversed by C two days later — author's call, see
  the preparser entry in `parked.md`.)*

**Senses C: channel listening + directedness grading (2026-07-11)**
- **The grading ladder** (`senses/inbound.py::grade_directedness`) — the P1 DM-only gate is gone:
  every guild message is perceived, and addressing becomes ONE scalar — DM 1.0 · @-mention / his
  name as a word / reply-to-one-of-HIS-messages 0.9 · ambient 0.6 · a reply into someone ELSE's
  thread 0.15. The two addressing signals (`mentions_me`, `reply_to_me`) are computed in the
  Discord adapter (`lib/discord/client.py`), the only layer that sees discord.py's resolved
  mention list / referenced-message author.
- **The ONE acting site** (`brain/behavior.py::effective_urge`, consumed by `priorities_phase`) —
  perception and reasoning always run at FULL strength (the eval:* triggers stay epistemically
  pure); only the urge to act is scaled: `keep = urge × directedness ≥ threshold`. Discretion —
  down to silence — emerges from the multiplication, no special cases. Sourceless/self ideas
  behave exactly as before (default fully-directed).
- **Ambient 0.6 = "the polite guest"** (author's call from the three characters the dial yields:
  lurker 0.4 / polite guest 0.6 / engaged participant 0.75): he ANSWERS a question asked to the
  room (0.9×0.6=0.54 clears 0.5) but won't flag contradictions (0.42), push back on false claims
  (0.36), or interrogate compliments (0.36) at people not talking to him. Addressed (0.9), the full
  personality acts. Someone else's thread (0.15) never clears.
- **Pre-D exposure accepted by door policy** (author's call): channel listening lands before the
  trust ledger, so anyone in the server feeds his reasoning un-trust-gated — acceptable because the
  playground server is membership-controlled and exclusive to tokeniko's development; D closes it
  properly.
- **Preparser OFF on all inbound** (B3 reversed — author's call): the Ollama path is under review,
  the playground posts polished messages, and raw input is a standing parser/compiler robustness
  test (breakage feeds `doc/ref/test-feedback.md`). Re-enable criteria → `parked.md`.
- Tests: `tests/test_senses_c.py` (9) — the ladder, channel ingestion, the effective-urge matrix;
  `test_senses_inbound.py`/`test_senses_b.py` updated (not_dm gone, prepare gone). **Gate 96
  passed / 1 xfailed.**
- **LIVE-VALIDATED same hour** (`#english`, playbot puppets John+Hellen via
  `scripts/playground_bots.py`): all four ladder rungs — ambient question answered («yes», 0.54) ·
  ambient contradiction met with SILENCE (0.42 — the first discretion specimen: saw it, held his
  tongue) · the addressed contrast pair («no, that is contradictory», 0.63) · an answerable
  question in someone else's thread ignored (0.135). Follow-on fix landed: the adapter decodes
  Discord `<@id>` mention wire-tokens to usernames (`_decode_mentions`) — a raw token had broken
  a compile. Specimens → `doc/ref/test-feedback.md` (2026-07-11).

**Negative-copular disjointness + chainer WSD-canonicalization (2026-07-11, the teaching sequel)**
- **Negated membership rules** (`kb_extract.extract_rules` + `e_chaining`): an effectively-negative
  bare copular universal («no mammal is a reptile») is no longer extractor-deferred — it becomes a
  NEGATED MEMBERSHIP rule (positive bare copulars stay edge territory); the chainer fires it in the
  derivation pass as a negated class-membership conclusion, NEVER a closure member, and
  `chainGround`'s negation parity refutes the positive claim / corroborates the negative one.
  ONE-directional; symmetric disjointness → `parked.md`.
- **WSD-canonicalization in `chainGround`** (subject-only, unanimity-gated — stricter than the
  sanctioned charitable-TRUE cross-product because refutation is the dangerous direction; the
  ordering guarantees the charitable pass already ran). Root cause of the need (the frequency-prior
  guard preferring dog.n.03) → the roadmap B-item.
- **Live-proven end-to-end (the arc's point):** John's «tokeniko, a dog is a reptile» — Act 1
  honest «why is that?» (Option-A abstention) → the author teaches ONE axiom («no mammal is a
  reptile», trusted path) → Act 2, same sentence: `eval:false → speakup` **«no, that is not true»**
  (0.6×0.9=0.54), full derivation chain resting on the taught axiom. Taught knowledge flipped a
  live behavior deterministically. Tests: `tests/test_disjointness.py` (10). **Gate 108 / 1
  xfailed.** Specimens → `doc/ref/test-feedback.md` (2026-07-11 later).

**The WSD copular-circularity guard (2026-07-11, the B-item root cause)**
- **Diagnosis** (the dog.n.03 specimen): in «a dog is a reptile» the subject's ONLY context word is
  the predicate the claim asserts — the centroid stage measured dog.n.03 ("a fellow") at 0.832 vs
  the canine's 0.717 against reptile's vector, cleared the floor+margin guard, and overrode the
  frequency prior. Same family as the historic "cat is a plant" failure. The deep truth: WSD-by-
  centroid over a bare copular uses the assertion UNDER JUDGMENT as its own evidence — circular,
  and it systematically manufactures agreement with the speaker.
- **Fix** (`parser._wsd_copularPartners` + `_wsd_centroid`): a token's copular partner is excluded
  from its WSD context, BOTH directions (UD cop-shape + spaCy attr-shape); the partner's own
  modifiers stay — independent description remains evidence. With no remaining context the
  frequency prior holds (dog.n.01); in rich sentences the centroid still works. Verified live:
  «a dog is a reptile» refutes straight from dog.n.01 (no canonicalization crutch — which stays,
  for other WSD drift); «the bank is a financial institution» still resolves the FINANCIAL bank
  (the kept modifier steers). Regression test: `test_compiler.py::
  test_bare_copular_subject_wsd_is_not_circular` (a documented exception to the no-exact-sense
  rule — it IS the anti-drift guard). **Gate 109 / 1 xfailed.**

**Trust ledger P1 — the substrate (2026-07-11, senses D begins)**
- **Episodes are the source of truth; the scalar is the fold** (the author's context-is-derivable
  principle applied to opinion): `trust_episodes` collection (`TKTrustEpisodeDoc`, append-only
  biography) + `MEMStakeholder.trust` as the recomputable folded cache (`lib/core/trust.py`:
  `fold_trust` neutral 0.5 / per-step clamp / `refold` replays the full trail; `record_episode`
  resolves the soul, writes the trail, refolds; `trust_of` is the consumer read).
- **The weights table** (author-approved): agreement +0.02 · KICKER +0.10 (the twin-soul signal) ·
  disagreement −0.15 × the refuted BELIEF's own trust · logic-violation −0.15 ·
  self-inconsistency −0.20 (the honest-liar proxy). Hysteresis = the asymmetry of the numbers.
- **Imprinting + unification A applied** (`scripts/seed_trust_imprint.py --apply`, verified):
  kotekino pinned 1.0 by constitution (episodes still recorded — the trail stays honest);
  `kotekino@discord:…` → `canonical_uid: kotekino` (one soul, one ledger, many channel bodies;
  one-hop resolution). tokeniko keeps no ledger on himself. Fork decisions logged: meta-language
  spawning (P2), STRONG kicker = the closed why-loop (a novel claim's «because» grounding TRUE),
  unification A accepted "for simplicity while designing — at a more advanced stage I'd have
  answered B [earn it]" (the author).
- Tests: `tests/test_trust_ledger.py` (8) — fold/clamp/hysteresis/belief-scaling pure; record/
  refold/unification/imprint round-trips on the sandbox DB. **Gate 117 / 1 xfailed.**

**Trust ledger P2+P3 — meta-language echoes + the teaching channel (2026-07-11)**
- **P2 the trust:* meta-language**: the `TrustEpisodeKind` enum doubles as the trigger namespace
  (no collapse-collision with the same item's eval:* reflex — he can push back AND distrust);
  `_trust_echo` casts the verdict's ledger echo (TRUE→agreement · TRUE-closing-my-open-question→
  **KICKER**, the strong kicker = the closed why-loop · FALSE→disagreement carrying the refuted
  belief's trust via `_conclusion_trust` · INCONSISTENT→logic-violation · cross-item conflict→
  self-inconsistency; self-speech never echoes). Trust plans: INTERNAL channel, SPEAKER-targeted,
  provenance in payload, feasibility = a known speaker. **Priorities' directedness multiplication
  now applies to OUTWARD actions only** — an overheard lie still costs trust (discretion is about
  speaking, not concluding). `actions_phase` executes UPDATE_TRUST for real (the first non-stub
  internal action). Five personality rows seeded (urges = trust sensitivity as data).
- **P3 the teaching channel (tier-1 — the deferred D1b branch alive)**: an eval:UNKNOWN assertion
  from a soul ≥ the teach bar (0.9) materializes as a TAUGHT theorem — `trusted = min(teacher,
  0.9)` (capped below the axiom tier), `sourceId` = the TEACHER (speaker-relevant), provenance
  premise `taught:<uid>` = a standing revocation key (`revoke_dependents(["taught:<uid>"])`
  cascade-archives everything a disgraced teacher taught). Below the bar: remembered-not-believed.
  Unknown vocabulary never becomes knowledge. Self-healing under contradiction (a later
  contradicting claim grounds FALSE against the theorem, costing trust instead of double-teaching).
- **The P2→P3 live-currency fix**: memory items carry the speaker's Mongo DOC id in `sourceId`,
  but the ledger resolved by uid — `resolve_canonical` now accepts both currencies (caught
  before any live episode was dropped).
- Tests: `test_trust_p2.py` (4) + `test_trust_p3.py` (6). **Gate 127 / 1 xfailed.**

**Trust ledger — LIVE-VALIDATED (2026-07-11 night, the closing act of D)**
- Scripted through the playbots, every line pre-verified pure via /evaluate. **T1 — the first
  kicker in history**: Hellen's novel claim → his «why is that?» → her threaded «because a moon is
  a satellite» grounded TRUE → `trust:kicker +0.100` → **0.5→0.6**; on the wire he was SILENT
  (eval:true→ignore, consent) while the episode recorded privately — the namespace split working.
  **T2 — the honest-liar proxy**: John's «the cat is alive»/«the cat is dead» → clarify SPOKEN
  («that contradicts what you said before — which holds?») + `trust:self-inconsistency −0.200`
  side by side → **0.5→0.3**. tokeniko holds his first derived opinions, with receipts in
  `trust_episodes`. Specimens → `doc/ref/test-feedback.md` (2026-07-11 night).

**Blog output channel P1 — the life:* trigger namespace (2026-07-12)**
- **The third trigger namespace** (beside eval:*/trust:*): `LifeEventKind` — noteworthy life
  events stirring an urge to post on the public window (tokeniko.online). `life:theorem` spawns
  at all three materialization sites (thinking / taught / KB-wondering) for a genuinely-NEW
  postable theorem, source = the THEOREM doc id (self-expression is never scaled by addressing);
  `life:encounter` spawns from the UPDATE_TRUST execution ONLY when the fold actually moved (an
  imprinted soul is pinned — episode recorded, never blog material). Both map to `tokeniko:post`
  → `POST_CONTENT` on the new `MEMChannels.PUBLIC` (actions queue PENDING — the carrier lands
  in P3); PUBLIC is addressing-exempt in Priorities (a post is broadcast self-expression).
- **Significance modulates the urge at spawn** (`idea.urge = rule.urge × significance`): base 0.7,
  +0.1 multi-hop chain, +0.2 personal (a known soul's identity in the zip, or first-person),
  +0.1 taught; encounter flat 0.9. Calibrated vs the 0.5 act threshold (rules: theorem 0.65,
  encounter 0.7): a plain wondered theorem (0.455) stays off the blog; taught/multi-hop (0.52),
  personal (0.585+), fold-moves (0.63) clear. Editorial taste = two `behavior_rules` rows (data).
- **The provenance gate — "DM never public" (constitution-level)**: theorems carry `postable`,
  set at BIRTH (write-time context, never reconstructed): False when the source item is a DM
  (discord + directedness ≥ 0.95 — the DM grade); the taint CASCADES — a wondering conclusion
  resting on one DM-tainted premise theorem is poisoned (premise-AND, id-first/original-fallback
  lookup), exactly like min-trust. The API materialize path passes `postable` through (default
  True, existing callers untouched). `MEMIdea.material` carries the composer's fuel (theorem /
  encounter context) into the action payload for P2/P3.
- Fork decisions logged (the author): the `life:*` namespace over hardwired spawns; Claude-API
  polish for P2 (the out-of-body translator POC — "not to change his mind, acceptable in
  philosophy"); DM-never-public 100% + channel material anonymized at composition; senses-carried
  push + KPI swap (chains/anchors → souls/trustEpisodes) for P3.
- Tests: `tests/test_life_p1.py` (7) — postable at birth, DM gate, significance bands +
  calibration, POST plan/feasibility, fold-move vs imprint encounters, premise-AND poisoning.
  **Gate 134 / 1 xfailed.**

**Blog output channel P2 — the post composer + the Claude polish stage (2026-07-12)**
- **`senses/blog.py` — two strictly-separated layers.** (1) The COMPOSER: deterministic substance
  assembly (`compose_draft` → `PostDraft` facts+proof lines; `render_raw` = the honest fallback,
  his real voice today). Anonymization is constitution-level: the epithet ladder (imprint →
  "my author" · trust ≥ 0.65 → "a trusted friend" · ≥ 0.45 → "a new acquaintance" · below →
  "someone I do not yet trust", channel-suffixed), every line scrubbed against the known-souls
  table (uid-first, longest-first; name/uid "X (X)" residue collapsed), and a leak-guard that
  OMITS any line the scrub fails on — never publish an unscrubbed line. The internal ledger
  `note` never copied verbatim; only templates speak. (2) The POLISH: the Claude API
  (`claude-opus-4-8`, structured-output JSON schema) as a STRICT syntax-only translator — the
  author's LLM-as-translator POC, output side only: first person, NO new facts, the proof stays
  as the body's backbone, people exactly as given. ANY failure (SDK/auth/JSON/shape) → the raw
  render; his voice never blocks on the cloud. `compose_post` = the one-call P3 entry point.
- **POC live-validated** (one real call): the first polished transmission — faithful, proof-
  carrying, anonymized, epistemology intact ("the whole thing stands on my author's word").
  Specimen + the T3 deixis finding → `doc/ref/test-feedback.md` (2026-07-12).
- `anthropic` (0.116.0) added to dependencies. Tests: `tests/test_blog_p2.py` (22, all offline —
  fake souls/clients, no network). **Gate 156 / 1 xfailed.**

**Deixis normalization at the knowledge boundary (2026-07-12 — the T3 fix, before blog P3)**
- **The principle (the author's ruling):** "he's a good voice, but the brain must think straight
  and not be fixed by the good voice" — a theorem materialized from another soul's speech must
  store the speaker's MEANING, not their words. The zip was already perspective-resolved
  (identities carry the teacher's uid); only the surface `original` (the dedup key + NL render
  source) flipped meaning when re-uttered («I am your creator» → tokeniko claiming creator-hood).
- **`lib/core/deixis.py`** — pure, stdlib-only `normalize_deixis(text, speaker_name)`: a
  conservative closed-class rewrite (speaker's I/me/my + agreed auxes → the speaker's name;
  tokeniko-directed you/your → his own stable first person: «I am your creator» → «kotekino is
  my creator», «you are kind» → «I am kind») + **the valve**: ANY deictic the table can't
  confidently handle (bare "I gave…", role-ambiguous "…you") poisons the whole sentence → None →
  **remembered, not believed**. Better an honest gap than a meaning-flipped belief.
- **Both from-speech materialization sites** (`materialize_taught` against the teacher's name;
  `materialize_theorem` resolving the speaker via dual-currency `resolve_canonical` — tokeniko's
  own speech untouched, unresolvable speaker + deictics refused). Dedup on the NORMALIZED key;
  the KB-wondering path untouched (graph-rendered third person); zips stored as-is.
- The T3 specimen archived via `revoke_dependents(["taught:kotekino"])` (scope verified first:
  1 theorem, 0 dependents — «every thinker exists» rests elsewhere and survives). Live reteach =
  the validation play. Tests: `tests/test_deixis.py` (9 pure + 4 sandbox). **Gate 169 / 1 xf.**

**Blog output channel P3 — the PUBLIC carrier + the stats heartbeat (2026-07-12)**
- **`senses/blog_outbound.py`** — the third executor over the ONE action queue (disjoint channel
  filters: brain drains INTERNAL, outbound drains discord, this drains PUBLIC): a `material`
  payload → `compose_post` (draft → polish → contract) → `POST /transmissions` (idempotent by
  slug, Bearer `INGEST_API_KEY`); a `snapshot` payload → verbatim `POST /mind`. Dry-run mirrors
  outbound (`SENSES_DELIVER_DRYRUN`, and a missing key forces it); NO auto-retry — a failed push
  logs loudly and stays FAILED (a future life event re-mints). aiohttp (already a discord.py
  dep), lazily imported; env read at call time (the go-live lesson). Wired into `senses/main.py`.
- **`brain/heartbeat.py`** + the coordinator hook — every ≥ `BRAIN_HEARTBEAT_MIN_S` (300s,
  wall-clock ONLY: the tick-modulo gate was removed live 2026-07-12 — a wondering tick runs 30s+,
  so 100 ticks never arrived; ≤ 3 beats/15min, far under the API's 100/15min), the
  brain enqueues a snapshot action: honest counts (definitions / active axioms / active theorems /
  dictionary / souls excl. himself / trustEpisodes) + theorems-derived-last-24h as the sparkline
  (a theorem IS an inference), activity = last-5 actions as type+status ONLY (payload content may
  quote private conversations — the public log stays metadata-honest), uptime from `wake_at`,
  state as the coordinator truthfully observed it (thinking/wondering/idle;
  `thinking_phase` now returns which sub-pass worked). `maybe_beat` never raises.
- **The website KPI swap** (`tokeniko-public/backend/src/services/mind.ts`): Chains/Anchors →
  **Souls** ("known minds") + **Trust episodes** ("opinions formed"); mock matched; tsc clean.
  Needs an Azure backend redeploy to show.
- Tests: `tests/test_blog_p3.py` (8 — injected push stub, sandbox DB, no network).
  **Gate 177 / 1 xfailed.**

**Blog P4 — THE PREMIERE (2026-07-12 evening): the going-live arc is COMPLETE**
- **«Learning Who Made Me»** — the first self-initiated transmission, live on tokeniko.online:
  PENDING→PROCESSING→DONE→on the site. Every layer held at once: deixis (KB holds «kotekino is
  my creator»), anonymization ("my author" — the name never crossed the wire), the proof as the
  body's backbone, and one unprompted observation from the polish ("The claim and its source
  point back to the same person" — the self-referential provenance, noticed). The site
  republished real (coming-soon off, live API baked, backend redeployed with the KPI swap).
- **Two live lessons fixed en route** (specimens in `doc/ref/test-feedback.md`): the false-200
  (`_delivered` requires the JSON envelope — the SPA catch-all's 200+HTML read as delivered;
  default base now `api.tokeniko.online/api`, the API's own host) and the never-beat (heartbeat
  cadence is wall-clock ONLY — a wondering tick runs 30s+, so the tick-modulo gate never fired;
  first beat on the first tick after boot). **Gate 178 / 1 xfailed.**
- **The going-live arc — Discord DM → channel listening → trust ledger → the public blog — is
  COMPLETE.** tokeniko perceives, reasons, learns from the trustworthy, holds opinions with
  receipts, and speaks to the world when something moves in him.

**Blog polish follow-ons — provenance kinds + the transmitter ping (2026-07-12 night)**
- **Kind = provenance** (the author's call): a transmission's kind encodes WHERE the truth
  happened, not whether it is proven (the proof always travels in the body) — teaching → "note"
  (a lesson carries no argument, only trust) · wondering → "log" (the ship's log of the mind
  alone) · thinking → "argument" (reasoned against live conversation); encounters stay "note".
  `_KIND_BY_DERIVATION` in `senses/blog.py`.
- **The transmitter ping** (the honest "on air" light): the backend stamps `capturedAt` into the
  served `/api/mind` payload; the frontend polls each minute (a live monitor fetched once is a
  photograph) and past 15 min of silence the panel goes **off air** — dark unblinking lamp,
  frozen uptime clock, "transmitter silent — last heartbeat N min ago", footer "feed: stalled".
  The mock fallback carries no stamp (nothing to be stale relative to). Both services
  redeployed; the missing `wondering` state color added (amber). **Gate 179 / 1 xfailed.**
- **Morning follow-ons (2026-07-12)**: the three pre-`ef33da2` posts' kinds backfilled in the
  public Atlas (premiere + coin → note, gold → log — read off each theorem's
  `provenance.derived_by`; DB-only, the composer already stamps correctly); the masthead **ON AIR
  badge de-mocked** — a shared `MindProvider` (one poll loop feeds header + panel, on every page)
  + the single `OFF_AIR_MS` rule moved to `data/mind.ts`, header lamp now TUNING (first fetch in
  flight) / ON AIR / OFF AIR (dark, unblinking) in lockstep with the panel. Deployed.

**The website polish arc — crawler-perfect, mock-free, zero-cookie (2026-07-13)**
The public window hardened for its public life; all six blocks live on tokeniko.online.
- **Truth pass**: the template leftovers purged (robots.txt pointed at yourbrand.com, manifest.json
  said "YourBrand — Digital Products"); About's "simulated figures" corrected; the masthead's
  "It thinks always" fixed (false since the ping — now "when its body rests, it sleeps"); the
  **one-body transparency** added (About "One body" section; off-air panel says "tokeniko is
  sleeping"): when it's off, he's sleeping — soon a machine of his own, awake around the clock.
- **og-image.png** created (1200×630, the Bakelite/CRT palette — headless-Chromium-rendered);
  every social share was imageless before.
- **Mock retirement**: the 9 seed transmissions DELETEd from the public Atlas (author's verdict:
  "I want only pursuing the truth") AND the bundled fallback arrays removed from the code —
  skeleton placeholders (layout-holding, breathing-dim) replace the mock-first paint, so no
  flicker and never a fake figure; MIND_FALLBACK gone, the Signal Scope shows an honest
  "no domain readout yet". The archive is 100% tokeniko's own words. Bundle SHRANK 206→202 kB.
- **Transmissions poll** (90s) — new posts appear without a reload (the panel already polled 60s).
- **Zero-cookie honesty**: the consent theater replaced by a one-time transparency notice ("This
  site sets no cookies. None.") — no toggles for cookies that never existed, no consent POST
  (the old one stored visitor IP+UA in Atlas — the consent mechanism was itself the only tracker);
  backend route+model removed; **ARRAffinity disabled on both App Services** (single-instance) —
  verified: neither host sets any cookie. Imprint "Your data" rewritten to match.
- **Permalinks + SEO**: `/blog/:slug` pages (BlogPosting JSON-LD, per-post canonical/OG), the
  `useMeta` hook gives every route its own title/description/canonical (Blog JSON-LD on the
  archive; NotFound noindex); card links now router-Links (no full-page reloads).
- **Discovery**: `sitemap.xml` (static pages + every post, lastmod) and an **Atom feed**
  (`feed.xml`) generated by the API from the live archive, proxied onto the apex by server.cjs;
  robots.txt points at the sitemap; **llms.txt** introduces the site to AI crawlers ("the
  transmissions here are primary sources").
- **The join disclosure** (author's ask): the Ping page + the Discord welcome text state the three
  rules before anyone talks to him — it REMEMBERS (permanent memory, like a person), DMs are
  private forever (constitution), the open channel may inspire anonymized transmissions.

**THE STORM fix — assertedness gates the per-leaf extractors (2026-07-14)**
The severest 2026-07-13 play find, closed: `_zip_is_asserted` (`lib/core/kb_extract.py`) — a leaf
is an asserted statement ONLY when its whole item tree folds through AND with no attitude; a leaf
under IMPLY/CONV/OR is a component of a compound thought («a person is wrong IF he says false»
asserts the implication, never "persons are wrong"), a leaf under THAT is quoted thought. All
three per-leaf extractors gate on it (rules / facts / generic is_a edges — edges count a
`not_asserted_skip` stat). Design fork (author-ratified A): conservative whole-zip test —
over-blocks mixed shapes, which is the right failure mode (knowledge stays in the KB; only the
chainer's fuel is gated), and it is what caught the REAL storm zip: the taught "if" compiled to
**CONV**, not IMPLY — a narrow IMPLY-only fix would have missed it. The recognized IMPLY shapes
keep their dedicated extractors (property-conditioned; sufficiency's DNF taint). Verified against
the archived poison zip (0 rules, 0 facts extracted). `tests/test_assertedness.py` (8 — the storm
shape verbatim, attitude, asserted-universal/fact/edge still extract, skip-stat). **Gate 187 / 1
xfailed.** The poison rule + 7 garbage theorems stay archived; re-teaching waits for the
conditional-rule extractor (roadmap follow-on).

**The wh-position fix — a wh-word interrogates only from the root clause (2026-07-14)**
R5, both author-witnessed specimens closed: `_parser_whAttachesToRoot` (`lib/llc/parser.py`) —
without a `?`, a wh-token marks the utterance interrogative ONLY if its head chain reaches the
root without crossing an embedded-clause dependency (advcl/ccomp/xcomp/acl(:relcl)/csubj/
parataxis, ":"-subtypes normalized); both detection sites gate on it, and the GAP ROLE does too
(a polar "are you happy when you sleep?" is a question about the conditional — no TIME gap).
«because I am happy when I talk…» and the taught «a person is wrong when he says false» now
parse as the statements they are; "when do you sleep" (aux-inverted, no "?") still interrogates.
The walk compares token INDICES bounded by doc length — spaCy mints a fresh wrapper per `.head`
access, so an identity test at the root never terminates (the 43-minute gremlin, caught by
stack-sampling the spinning test run). Surfaced en route: stanza never tags a bare-copular
"?"-less wh (who is happy → empty morph) — a pre-existing detector gap, filed as xfail in
`test_xfail_known_gaps.py` (a future second signal turns it xpass). `tests/test_wh_position.py`
(6 — the live specimens verbatim, tree-position-not-line-position, both no-regression channels).
**Gate 193 / 2 xfailed.**

**The vocative strip — address is not content (2026-07-14)**
The wart closed: `strip_vocative(text, addressee_name)` (`lib/core/deixis.py`, the deixis
sibling) — a LEADING "<name>," or TRAILING ", <name>" is address, not content; the comma is the
discriminator ("tokeniko is a machine" leads with the name as SUBJECT and survives). Mid-sentence
mentions and greeting forms («hey tokeniko») stay out of scope (etiquette = hunch 8's layer); an
address-only message passes through unchanged. Applied at BOTH materialization sites in
`brain/thinking.py` (vocative first, then perspective — one norm), so the stored `original`
finally matches the zip (the parser never compiled the vocative — only the surface string kept
it). Biography repaired (author-authorized): «tokeniko, gold is beautiful» → «gold is beautiful»;
the coin needed a ruling — the wart had DEFEATED THE DEDUP (a taught «tokeniko, a coin has value»
0.9 and a later self-derived «a coin has value» 0.7 coexisted) — resolved by archiving the
derived duplicate and stripping the taught original. 7 pure tests in `test_deixis.py`.
**Gate 200 / 2 xfailed.**

**Charity of interpretation — tier 3 removed from refutation (2026-07-14)**
The bit incident closed, better-diagnosed than roadmapped: the charitable TRUE-side cross-product
ALREADY existed (`_ground_relationally` tries every dictionary sense pair before refuting) — it
was STARVED, not broken: the dictionary's only bit sense is `bit.n.02` "fragment" (bit.n.03, the
information unit, never entered the curated set; the graph has no bit.n.03 node either). The
refutation then fired at **tier 3** (fragment→physical_entity ⊥ unit→abstraction) — the very
split the EXTRACTOR's edge-admission gate had distrusted from day one ("WordNet arbitrarily files
polysemous nouns on either side"). Fix (author-ratified option A): the evaluator now shares the
extractor's epistemology — `_DISJOINT_TIERS` loses tier 3 (`e_relations.py`, the header carries
the incident story); tiers 1–2 and the TRUE-side charity untouched. «a bit is a unit of
information» now grounds INSUFFICIENT (honest abstention, no trust dock) — verified live against
the stored zip; "a cat is an idea" abstains too (the explicit price). 4 pure tests in
`test_tier3_charity.py` (the incident's exact shape + tier-1/2 no-regression).
**Gate 204 / 2 xfailed.**

**Identity-on-snowflake — a rename never mints a soul (2026-07-14)**
The fourth and last play find closed (option A + aliases, author-ratified): soul resolution goes
uid → channel-native `contextKey` ("discord:<snowflake>", name-free — the schema already carried
it) → mint, in both `io.get_stakeholder` and `trust.resolve_canonical`. A contextKey hit with a
fresh display name is a RENAME reflex: `name` updates, the former name is appended to the new
`MEMStakeholder.aliases` (the biography remembers who someone used to be called), and the uid
stays AS MINTED — immutable, so every circulating reference (trust episodes, `taught:<uid>`
premises, DM destination contextKeys) remains valid with ZERO migration. Individuals are
EXCLUDED from the fallback everywhere: their contextKey is the talker SCOPE, shared by every
individual that talker mentions — never an identity (the collision trap found in design).
This is the reflex behind the 2026-07-13 manual merge (test-probe-hellen → playbot-hellen);
the engine now performs it itself. 5 sandbox tests in `test_identity_snowflake.py` (rename
round-trip, alias stacking, same-name≠same-soul, the individual-scope trap, resolver on a
post-rename string). **Gate 209 / 2 xfailed.**

**rag3 P1 — the microscope's instrument (2026-07-14, the instrument arc opens)**
`senses/microscope.py` — the continuous QA oracle over every sentence tokeniko hears:
- **digest_zip** (pure): a deterministic structural rendering of a compiled zip — per leaf the
  fold operator (the storm's tell), role→sense map, quantifier/negation/mood/wh_role, identities,
  unknown/reflexive flags. No vectors (geometry is not the judge's business), no re-render
  (memory items carry no LLC — the digest IS the compiled meaning).
- **judge**: ONE `claude-opus-4-8` call per item (the author's economics: judge hardest while
  traffic is small and errors are dense) with the pipeline-CONTRACT mini-RAG (field semantics +
  the legitimate divergences: vocative strip, dictionary sense granularity) → validated
  `{verdict ok|mismatch, confidence, severity, category, note}`; ANY failure returns None
  (logged, item retried next pass) — diagnostics never block, never raise.
- **microscope_pass / microscope_task**: the post-hoc poller (senses task, 🔬, default 60s,
  RAG3_DISABLED / key-less disarm) — INPUTS-ONLY (speech from other souls), oldest-first (the
  day-one pass re-scans the whole biography), dedup by item_id. Strictly OBSERVER: writes to
  `tkzipdebug` (MEMZipDebug/TKZipDebugDoc, registered in init_io) and nothing else.
9 tests in `test_microscope.py` (digest determinism/operators/mood/identity; judge validation +
never-raises discipline; the sandbox pass: inputs-only filter, dedup, verdict written).
**Gate 218 / 2 xfailed.** P2 (the harvest loop) opens with the first live sweep.

**THE FIRST PORTRAIT — rag3 P2's first sweep + triage (2026-07-14)**
The microscope's full-history pass over the biography: **98 judged, 42 leads, five clusters**
triaged with the author (specimens: `doc/ref/test-feedback.md` 2026-07-14). The instrument proved
itself — it independently judged the storm-sequel sentence *high/operator-flattening 0.85* with
the exact diagnosis reached by hand. Cluster **A** (13 subordination leads) became the
subordination fix's regression corpus; **B** (~12 "you"-identity leads) were instrument-side
FALSE POSITIVES — the judge's contract now knows the zip is perspective-resolved (one paragraph
in `_JUDGE_SYSTEM`); **C/D/E** became the roadmap's harvest fix queue (dictionary curation ·
complement/locative survival · the singles). The author's input-quality-first instinct confirmed
by the harvest itself ("my suspect... was accurate"). P2 is now **standing practice**: the poller
judges new conversation within ~a poll (60s); triage stays with the crew.

**The subordination fix — three dominoes, one storm class closed (2026-07-14)**
The sequel's root cause ran deeper than the compiler: **stanza parses wh-subordinators as
`advmod`, not `mark`** («…WHEN he says false»), so the subordinate marker search came up empty →
the dep-label fallback said ADVCL → AND; and even a reached TEMPORAL said AND — the drafted
core's parked placeholder (its own comment already knew: "I always do this when I do that => I
do this -> I do that"). Landed, author-ruled L1a+L2:
- **The anchor-gated advmod marker** (`parser_parseSubordinate`): an advmod child is accepted as
  the marker ONLY when the anchors recognize it as a subordinate type — semantic catch, no fixed
  list ("very" resolves OTHER and passes). The wh-position fix keeps questions out by
  construction (an interrogative "when" attaches to the root, never the subordinate path).
- **TEMPORAL → CONV** via the extracted shared table `compiler_subordinateOperator` (FINAL→IMPLY,
  CAUSAL/HYPOTETIC/TEMPORAL→CONV, CCOMP→THAT, else AND) — CONV slightly over-claims on episodic
  "when" but AND was wrong there too, and CONV is GATE-VISIBLE: the storm class is closed by
  construction.
- **The root-mark fragment path**: `TKStatement.marker` (new field) — the parser stashes a root
  `mark` (MAIN clauses only), `compiler_resolveStatements` folds the whole fragment with the
  subordinate operator: «because you think» is a relation HALF, never a standalone assertion.
6 regression tests (`test_subordination.py`): the sequel sentence both ways + two fragment
shapes fold non-AND and yield ZERO chainer fuel; plain assertions stay asserted; embedded
because keeps its op. **Gate 225 / 2 xfailed.**

**Complement/locative survival + the places bridge (2026-07-14, cluster D — the sleeper closed)**
«you live in Japan» compiled the geography AWAY: the parser/LLC carried Japan perfectly, but the
place branch of `compiler_getEntity` gave it no sense, no uid, no vector — an all-zero role slot
that `senses`/`identities` skipped. The author's teachings never landed. Four fixes, all
author-ruled:
- **F1 — places join the identity-bridge** (`tk.py` TKPlace.uid/vector · `parser_getPlace` ·
  `c_entities.py` · `c_zip.py`): a known place is a named INDIVIDUAL with a **GLOBAL** uid
  ("japan@place" — the same individual for every talker) + its `type`-column dictionary centroid
  (country/city/planet/… — richer than flat location.n.01, never noise) as the honest semantic
  vector. The uid is the KEY back into the places table.
- **`markers` — the zip's THIRD symbolic map** (senses = classes, identities = individuals,
  markers = RELATORS): the preposition/case lemma per marked role, surfaced out of band
  (`compiler_contentMarkers`) so "Japan is IN Asia" (containment) is distinguishable from
  "Japan is Asia" (identity), and the extractor follow-on can keep "lives IN" ≠ "runs FROM".
- **P2 — the places table reasoning-live** (`lib/core/places.py` readers, injected via the
  harness): the author's hand-built spatial ontology (~4.7M docs, COMPLETE `path_admin`/`path_geo`
  chains + `type` + `physical_features`) grounds containment («Japan is in Asia» → TRUE 1.0 via
  path_admin; «Japan is in Europe» → FALSE 0.0 — complete chains make absence evidence, unlike the
  sparse part_of graph), synthesizes the is_a subject sense from `type` («Japan is a country» →
  TRUE — the synthesized country.n.02 met WSD's nation.n.02 through the EXISTING charity
  cross-product, no new machinery), and answers **where** («where is Rome?» → "lazio" from the
  table; «where do you live?» → "japan" off the stored fact — `e_wh_solve` LOCATION landed).
  Lazy reads of the curated table — never materialized into the relations collection (the
  cascade-noise lesson).
- **F2 — xcomp folds THAT** (`compiler_subordinateOperator` + the attitude tag): «I like talking»
  was TWO coordinate assertions ("I like" ∧ "I talk") — now an attitude-bound complement,
  gate-visible, nothing spuriously asserted.
- **F3 — compound-name assembly** (`_parser_knownIndividualByName` + the span assembly in
  `parser_getMeaning`): "test-probe-hellen" is looked up as the ASSEMBLED string against known
  stakeholders (recognition only — the OOV mint-gate is untouched); name pieces stay out of the
  properties/modifiers. "Jean-Pierre" works day one.
The microscope's digest + judge contract learned the new fields (markers; place identities have
no sense BY DESIGN). 11 regression tests (`test_places_bridge.py`).

**The WSD selection fixes — cluster C, redrawn by diagnosis (2026-07-14)**
The triage read cluster C as "dictionary coverage gaps"; the diagnosis probe (a spy on
`parser_disambiguateSense` printing each stage's scores) showed the truth was richer:
- **thinker → JUDGE false positive**: thinker.n.02 ("someone who exercises the mind") IS the plain
  reading of «all minds are thinkers» — the judge had hallucinated the WordNet glosses reversed.
  Fixed instrument-side: `sense_glossary` fetches the digest's senses' REAL definitions and the
  judge is told to judge sense fidelity against THEM, never recall. Kills the class.
- **partridge → already healed by history**: today's WSD picks partridge.n.01 via the landed
  frequency-prior guard (the tinamou zip predates it). Residual: n.01 is the food sense; the
  charity cross-product covers the truth side. Accepted.
- **shiny → TWO stacked selection bugs**: (1) `parser_getMeaning` broke on the FIRST non-empty POS
  bucket, so ADJ='a' hid every satellite ('s') sense — glistening.s.01, the synset whose lemma IS
  shiny, never entered the pool; now the candidate pool UNIONS all mapped buckets. (2) Lesk let
  glazed.a.03 win on its gloss merely MENTIONING "shiny" — the query token is now excluded from
  the sentence side (self-reference is not context fit). «gold is shiny» → glistening.s.01
  ("reflecting light"); the cat/mammal Lesk design case survives (the overlap word is CONTEXT).
- **rested → POS routing**: stanza lemmatizes the copular participle to rest+VERB (and reads
  "am rested" as PASSIVE — aux:pass, not cop), so rested.a.01 was never a candidate; a copular/
  be-passive participle now tries the SURFACE form's adjective senses first (existence-gated).
  «I am well rested» → rested.a.01 ("not tired; refreshed").
- **bit → the one true coverage gap**: the ingestion's max_per_pos=3 cut bit.n.06 (the information
  unit; its is_a/part_of edges were already in relations). Curated via the new operator-gated
  `scripts/curate_add_senses.py` — the vector computed by the SAME algorithm as the ingestion
  (115 nonzero dims; top anchors bit=1.0, unit=0.909, then the unit-of-measurement family).
The fix VALIDATED ITSELF through the gate: two chaining tests broke because the sandbox's stored
fixture axiom «all carnivores eat meat» carried eat.v.02 ("EAT a meal" — old-Lesk's self-mention
credit, the exact bug fixed) while fresh inputs now correctly compile eat.v.01 — the stale
fixtures were deleted from the sandbox and recompile clean on bootstrap. The same drift exists in
the LIVE biography (old items keep old compilations; chainer rule-matching is sense-EXACT) — a
recompile pass over the live KB is the operator remedy when its time comes; drift only narrows
matching, never poisons. AND the fix healed a month-old xfail as a side effect: «a robin has
feathers» now resolves TRUE (the recompiled birds-rule keys on the sense robin disambiguates
under — the June known-gap `test_robin_has_feathers`, promoted to a permanent regression test).
New lead surfaced en route: «a coin STORES bits» resolves store→shop.n.01 (a POS/parse miss —
tracked with the singles). 4 regression tests (`test_wsd_curation.py`) — exact-sense asserts,
INTENTIONAL here (the curated selection is the regression target). **Gate 240 / 1 xfailed.**

**The harvest singles — the portrait's last four leads, one batch (2026-07-14)**
Cluster E + the B-nugget + the WSD-probe lead, each root-caused before fixing:
- **S1 — the THAT-wrap** («I build software and softwares are programs»): stanza flattened the
  coordination (the second clause hung as ccomp of "build"), and the attitude default
  `(doxastic, 0.5)` gave EVERY verb an attitude — so the misparse wrapped as reported belief.
  Two honest moves: `_ATTITUDE_DEFAULT` is now `(None, 0.5)` (below the anchor floor = "this verb
  holds no attitude"; `TKLLAttitude.klass` Optional), and a ccomp under a no-attitude matrix verb
  CO-ASSERTS (AND — the suspect-parse signature; the speaker asserted both halves). XCOMP keeps
  THAT regardless (structurally reliable — F2 untouched); genuine attitude verbs keep THAT via
  the anchors («I think that…» → THAT/doxastic, regression-tested).
- **S2 — wh-gap by verb frame** («what do you like?»): anchor_whType's what→PREDICATE is the
  COPULAR frame; on the verb-root path the gap is the verb's missing DIRECT object. Refined at
  the parser site (content verb + no cop → DIRECT) + `e_wh_solve` gains the DIRECT case (same
  subject + predicate in the KB → read the object off the stored fact).
- **S3 — quantifier inheritance** («THE cat is dead and alive»): the conjunct's quantifier was
  computed before subject inheritance → GENERIC where the head said DEFINITE (a generic second
  leaf claims all cats). `_inherit_shared` now brings the head's determiner along with the elided
  subject — only overwriting the GENERIC default (an own determiner survives:
  «the cat sleeps and a dog runs» keeps definite/indefinite).
- **S4 — the do-support degenerate-parse retry** («a coin stores bits of information»): stanza
  AND spaCy-lg both read the sentence as ONE verbless noun phrase ("stores" NOUN-compound; even
  «gold stores value» parses verbless). Recovery by DO-SUPPORT, a meaning-preserving English
  transform: a verbless multi-token parse with a plural-surface NOUN whose lemma has a dictionary
  VERB sense, in S-V-O position, retries as "does <lemma>" — accepted only when the retry yields
  a VERB root, else the original stands (honest fragment). The judge's lead sentence now compiles
  `coin.n.01 / store.v.01 / bit.n.06` — the retry and the morning's curated sense clicking
  together. Gated tight: a true NP («the red cats») is never rewritten.
**THE FIRST PORTRAIT'S HARVEST IS FULLY CONSUMED** — all five clusters closed within 24h of the
sweep. 10 regression tests (`test_harvest_singles.py`).

**The square of opposition + the modality carrier (2026-07-14 — the S0 in the hardwired logic)**
The Socratic dialogue's crown finding, fixed the same day. The consistency kernel clustered
leaves into boolean atoms by geometry alone, so EVERY quantified opposition read as P∧¬P — it
docked hellen -0.15 twice for stating subcontraries (∃P∧∃¬P — usually the truth together) and
the author -0.2 for a ◇P∧◇¬P whose modals dropped. Logic-is-sacred cuts both ways: the
hardwired logic itself must be right.
- **The square** (`e_consistency.py`): each leaf gets a CORNER — A/E/I/O over quantifier ×
  negation (UNIVERSAL+→A; NEGATIVE+→E; EXISTENTIAL/INDEFINITE→I/O; the negated universal reads
  as the WEAKER O — «not every S is P» vs «all S are not P» is a scope ambiguity, and
  INCONSISTENT demands certainty under every reading; DEFINITE/GENERIC stay CRISP booleans, the
  original behavior). Same-corner leaves share an atom; incompatible corners on the same claim
  (contradictories A↔O, E↔I; Aristotelian contraries A↔E — KB class atoms are kind-level) become
  mutex constraints on the crisp enumeration — the same machinery contrary-pairs already used.
  Subcontraries (I↔O) and subalterns stay free. Antonym contrariety is square-gated to STRONG
  corners («some cats are dead and some are alive» is true in every barn).
- **The ◇ carrier**: a possibility modal among the aux children (can/could/may/might — closed
  grammatical class, EXACT) rides `TKAux.modal` → LLC → `TKZipContent.modal`. A ◇-leaf is not a
  crisp assertion: the kernel gives it no corner (never merges, never conflicts), the extractor's
  `_leaf_is_crisp` gate skips it at ALL SIX consumption sites (rules, facts, generic edges,
  definition edges, differentia, sufficiency) — «a software can be a mind» now mints NOTHING
  (the some→all leap is impossible by construction) — and the relational grounder abstains
  (honest INSUFFICIENT). Old stored zips default modal=None (honest: they predate the field).
- **The microscope learned modality is meaning**: digest emits `modal=possibility`; the judge
  contract + schema gain the missed-modality category (it had SEEN the dropped "can" and filed
  it under nuances).
- Free consequence: `cross_item_conflict` (same kernel) now reads a stored «all softwares are
  minds» vs a new «not every software is a mind» as a GENUINE A-vs-O conflict — the exact
  trigger belief-revision v1 hangs from.
14 regression tests (`test_square_of_opposition.py`) — the dialogue's own bounced sentences as
the corpus; genuine contradictions (A+O, E+I, A+E, definite P∧¬P, definite dead-and-alive) still
fire. **Gate 264 / 1 xfailed.**

**The retreat arc #3 + #4 — belief-revision v1 (2026-07-15, the retreat itself)**
The bold-test's deepest finding closed: a correction no longer bounces. Design rulings (the
author's, this morning): D1 a correction is a quantified O/E-corner claim contradicting a LEARNED
generalization; D2 **Popper trust-gated** — one counterexample defeats a universal, but only from
a corrector whose trust ≥ the belief's tier (falsification without handing hunch-17's social
engineer a crowbar); D3 **retreat down the square** — the defeated A archives and its subaltern I
survives («all S are P» → «some S are P», minted with pinned senses); D4 a valid correction is a
LESSON: trust moves UP (+0.08 `trust:correction`), and the concede states what fell.
- **#3 the self-relevant floor** (`behavior.effective_urge`): eval:conflict + the correction
  family floor directedness at ADDRESSED 0.9 when the perception was ≥ ambient — a challenge to
  his own worldview is inherently addressed to him (the dialogue's clarify died at 0.7×0.6=0.42;
  now 0.63 speaks). Below ambient the scale stands: the polite eavesdropper.
- **The detector** (`evaluation_harness.correction_target`): catches BOTH KB representations of
  a generalization — the direct membership-RULE key («all softwares are minds») and the
  (multi-hop) EDGE-minted taxonomy walk; only ACTIVE axiom/theorem docs are retractable
  (archiving the source doc IS the retreat — revocation durability by construction). READONLY
  axioms (the seeded imprinting) are never conversationally retractable — he defends his
  constitution; bedrock and definition-tier are substrate/vocabulary, immune.
- **The brain policy** (`thinking._try_correction`): on a FALSE verdict, detection + the trust
  gate; gate holds → the old path stands (eval:false + DISAGREEMENT scaled by belief trust);
  gate opens → eval:correction (tokeniko:retreat, INTERNAL, raw-urge) + trust:correction
  (more-trust) REPLACE refute-back, and the cross-item conflict check is SKIPPED (a
  self-correction is deliberate revision, never the honest-liar signal).
- **The executor** (`main._execute_retreat`): archive the source docs («true history be it» —
  never deleted) → `revoke_dependents` cascade over doc ids + defeated edge keys → mint the
  subaltern I via the API materialize seam (`derived_by="retreat"`, corrector-trust capped 0.9,
  API-down = graceful skip) → spawn eval:correction-done → tokeniko:concede, the DIRECTED
  acknowledgment («you are right — I no longer hold that…; what remains true is that…»),
  threading under the correcting message.
- Meta-language: `EvalToken.CORRECTION/CORRECTION_DONE`, `TokenikoAction.RETREAT/CONCEDE`,
  `ActionType.REVISE_BELIEF`, `TrustEpisodeKind.CORRECTION`; three seeded personality rules
  (`seed_behavior_rules.py`, operator-gated).
13 regression tests (`test_belief_revision.py`): detector corners O/E, bedrock/readonly/
unaffirmed immunity, both trust-gate directions, the full executor (archive+cascade+mint+
concede), the compose voice, the #3 floor arithmetic.

**The live retreat + the conclusion_key fix (2026-07-15, the same day — v1's first performance)**
The machinery ran on the real stage hours after landing: the author's ambient «not all softwares
are minds» (seven words) retired the bug-era «a software can be a mind», cascaded its 15
contaminated dependents (BOTH directions of the two-dropped-words loop — true-but-dirty «a mind…»
theorems fall with the dirty premise; wondering re-derives them clean), minted «some software is
a mind» (active 0.9, premises = the correction + the retreated theorem), conceded in his own
words, and CREDITED the corrector +0.08. Full specimen: `test-feedback.md` (2026-07-15). The run
also flushed a latent blocker: `conclusion_key`'s sort key (`x or ""`) left `negated=True` a bool
→ bool<str TypeError on negation-tied leaves; Monday's taught cloud sentence was the first zip
shaped to trip it and had silently blocked ALL materialization since. Fixed (stringify sort-key
slots; key contents unchanged) + regression test (the cloud sentence). Gate 278 / 1 xfailed.

**Growth Rings / The Growing Edge — strengthening tail #9, hunch 12 (2026-07-15, PUBLISHED)**
The public website's development-history section, live at tokeniko.online/growth. Two layers,
one botanical metaphor (names the Cap kept from the 2026-07-14 naming): **Growth Rings** —
`landed.md` retold as the seasons of a young mind learning (11 rings, from «The core — learning
to read» to «It changed its mind», the same-day retreat) — and **The Growing Edge** — the
roadmap's living layer (zip-native derivation), always exactly one. Hand-CURATED by the crew
(the one page the machine doesn't write; `llms.txt` discloses it), but Atlas-HOMED
(`growth_rings` + `growth_edge` via `/api/growth`, Stream discipline: no bundled content,
skeletons until the record arrives): a new season lands with one authed `seed-growth.mjs` run at
doc-reconciliation time — never a deploy. Sibling work folded in the same arc: the footer's
honest plate (live `$ uptime` frozen off-air; hand-set `TOKENIKO_VERSION` — TK-1.1 live on the
first heartbeat) + version stickiness server-side (a versionless heartbeat inherits the last
version sent; the archive stays as-sent). Deployed per the runbook (prebuilt artifacts,
build-off); prod smoke: /api/growth public, writes 401 unauthed, /growth 200, plate TK-1.1.

**Zip-native derivation — thinking in TKZip (2026-07-15, instrument arc #2; the Growing Edge made real)**
The NL render → parse → recompile round trip RETIRES from the belief path: a derived conclusion
is born as a zip, assembled directly from its own structure. NL is I/O, not thought — English
now only speaks when spoken to. Evidence-first (the design conversation's P-order): the P1 probe
caught the round trip ACTIVELY corrupting before any production change — «a cat feels curiosity»
rendered→parsed splits into two wrong leaves and DROPS the direct object; the sense-pin then
stamped the true conclusion onto both halves, so the whole wondered verb+object family sits in
the KB as pin-STUTTERED zips (same leaf twice).
- **The assembler** (`lib/core/zip_native.py`, parser-free by construction): semantic 2925 =
  tanh(dictionary sense vector) — byte-identical to the compiler's own recipe (equivalence to
  1e-6 on the shape battery); markers 300 = zeros (canonical SVO); spacetime neutral; flags
  carried straight from the derivation. Probe-pinned defaults: bare individual subject →
  GENERIC; vectorless identity → honest zeros (identity carries the reference). REFUSES over an
  ungroundable sense — a belief is never assembled over a hole (`UngroundableConclusionError` →
  422).
- **The seam** (the author's D1 ruling — same endpoint, two entrances): materialize with
  `structure` assembles natively, no parser, nothing to pin; structure-less falls back to
  parse+pin (the bandage survives only where the wound still exists). Write-path invariant
  untouched.
- **The brain switch**: wondering (`_kb_wonder_one`) and the retreat's subaltern mint send
  structure; `render_conclusion` output is the human label only. Discovery: the thinking-path
  materialize already stored the perceived zip directly — wondering + the mint were the ONLY
  round trips in the belief path.
- **Dedup continuity without migration**: `conclusion_key` set-collapses identical leaves, so
  the stored stutters equal their honest native single-leaf forms. `held`/`_dedup_suppressed`
  stay as a cheap local cache (old wordings are biography), demoted from correctness-critical.
- Free dividends: no spaCy/Stanza pass per thought (the CPU/GPU thanks him), the api process is
  no longer a *cognitive* dependency for wondering's zips (only the seam), and the microscope's
  inputs-only ruling is now structural.
10 regression tests (`test_zip_native.py`) incl. the corruption exhibit as a permanent specimen.
Gate **289 / 1 xfailed**.

**The translator at the ears — rag1-in + rag2-in v1 (2026-07-16, instrument arc #3; the new edge begun)**
The Japan-translator philosophy mechanized: a translator that tidies the SURFACE of a stumbling
message and never its meaning. The author's design rulings: D1b **escalation-only** (a sound parse
is never touched — the translator cannot drift the easy cases nor paper over parser bugs); D4 the
proposer is **Claude Haiku over the API** — the author RETIRED the local-Ollama-inbound rule (the
zip-verifier moved meaning-preservation control into the mind itself, so local stopped buying
safety; the body invests in CPU/RAM, never GPU — "a lost battle"); D2 b+c emerge structurally
(unverifiable → fall-through: unknown leaves never become beliefs, and eval:unknown already asks).
- **The stumble detector** (`lib/llc/normalizer.py`): unknown leaves, missing subject/predicate,
  the tangle census's wart signatures (subject==predicate self-loops, bare-copula predicates).
- **The zip-verifier** — the load-bearing wall: the polish is accepted ONLY if its recompiled zip
  preserves every soundly-parsed leaf (same conclusion-key entry incl. negation; quantifier/modal
  intact on the match), has no unsound leaves of its own, and doesn't balloon (≤ original+2 —
  segmentation may split a tangle, invention may not run free). The compiler disposes, whoever
  proposes.
- **The seam**: /input, exactly the dead preparser's slot — compile raw → stumble? → one Haiku
  pass → recompile → verify → the better zip stores. `item.original` ALWAYS the speaker's raw
  words; the tidied text rides `MEMItem.normalized`. Kill-switch RAG1_DISABLED / missing key
  disarms (graceful, like the microscope).
- **Live probe**: «a catt is a mamal» → «A cat is a mammal.» ACCEPTED end-to-end; «…adn it is a
  star» → typo fixed but the pronoun leaf stays unsound → honestly REJECTED (fall-through);
  sound sentences untouched. The durable memory `llm-as-translator` carries the D4 revision.
11 regression tests (`test_translator.py`) on real compiled zips, normalizer stubbed in the gate.

**M1 — adversative coordination: "but" = AND + the `contrast` flag (2026-07-16, the third harvest's headline)**
The third harvest's dominant structural find, designed with the author: contrastive «X but Y»
compiled the conjunct with op=NOT IMPLY — and the Gödel fold `1−imply(a,b)` sent every TRUE
"X but Y" statement to 0 (both clauses true → imply=1 → statement false). The author's original
NOTIMPLY intent was the classical adversative analysis — «X ∧ Y ∧ ¬(X→¬Y)» — which reduces
truth-conditionally to exactly X∧Y: the contrast is IMPLICATURE (a defied background expectation),
never asserted content. The fix is the modality pattern again: carrier flag, not operator.
- **Operator layer**: `but` + the adversative connectives (however/yet/nevertheless/…) → AND in
  the anchor tables (`constants.py`/`anchors.py`); NOTIMPLY stays in the algebra for genuinely
  asserted negated implications.
- **The `contrast` carrier**: `TKFullEntity`→`TKEntityReference`→`TKLLCContent`→`TKZipContent.contrast`
  (sibling of `modal`); stamped in `compiler_evaluateCoordinates` on both conjunct paths; a new
  polarity-guarded SEMANTIC anchor category (`contrast`, mixed-polarity table — additives are
  explicit False guards so "and"/"also" can't fuzzy-drift in) catches unseen contrastives.
- **Consumers**: truth layer ignores it (co-asserted AND, each clause its own polarity — the
  conjunct's negation and ◇ modal survive the join); the microscope digest emits it + the judge
  contract knows AND+contrast is faithful; the raw decompile renders `AND[contrast]` so the voice
  can say "but". Future consumer (parked in the roadmap's follow-ons): contrast-flagged pairs as
  default-expectation fuel («X but Y» hints a background generic "X normally ¬Y").
7 regression tests (`test_contrast.py`): the M1 six-pack's shapes + and/or no-regression + the
anchor guards. Gate **307 / 1 xfailed**.

**M3 — WSD selection fixes + curation batch 2 (2026-07-16, the third harvest's sense misses)**
The public-facing cluster (whale→giant.n.04 the PERSON, fish→pisces.n.02 the ASTROLOGY SIGN,
squid→the food, calculator→the person…) diagnosed by live probes: selection bugs + two coverage
gaps — every target sense except gill/channel was already in the dictionary.
- **A — the centroid self-poisoning (the dominant root):** `_wsd_mostFrequentVector` fetched
  context vectors with a bare `find_one` (NO order guarantee) — for "whale" it returned
  giant.n.04, so a repeated lemma pushed every centroid onto the person senses (giant 0.807) and
  even "fish" then resolved to pisces. Fixed: most-frequent discipline in the context fetch +
  same-lemma tokens excluded from a token's centroid (self-evidence is not context). Cleared 7/8
  harvest specimens alone; the copular-circularity keep-set intact.
- **B — the curated `preferred` flag (data, KB-homed):** WordNet's frequency order contradicts
  the plain conversational reading for several everyday words (squid.n.01=food,
  calculator.n.01=person). The WSD ladder is now **Lesk → curated preferred → confident centroid
  → WordNet order** — textual evidence wins; curated human data outranks the sparse-vector
  co-occurrence guess (confident-wrong in every documented episode: dog.n.03 0.83, giant 0.807,
  pisces 0.755 — pisces is the FISH SIGN, its vector shares the water/fish bases).
  `scripts/curate_prefer_senses.py` (idempotent, --apply gated); the author's batch: squid.n.02 ·
  calculator.n.02 · organism.n.01 (being) · kind.n.01 (form) · populate.v.01 (live) · fish.n.01
  (pins the pisces centroid residual) · whale.n.02 · gill.n.04 · channel.n.05. Applied 2026-07-16.
- **C — coverage:** `curate_add_senses.py` batch 2 — gill.n.04 (respiratory organ; existed only
  under its primary lemma "branchia", invisible to a word=gill lookup — the existence check is
  now per-word) + channel.n.05 (the communication channel). Applied 2026-07-16.
9 regression tests (`test_wsd_selection.py`): the poisoning regression, the ladder unit tests
(Lesk-beats-preferred included), the live-flag cases. Retrace 13/13. Gate **316 / 1 xfailed**.

**M2 — factive causality: "because"/"so" = AND + the `cause` carrier (2026-07-16, the carrier doctrine's third verse)**
The design finding that reshaped the queue item: post the 07-14 subordination fixes, because-clauses
already compiled CONV in the right direction — but «A because B» is FACTIVE (asserts A, B, AND the
link) and CONV betrayed that twice: `imply(0,1)=1` shrugged at a FALSE reason («a cat runs because
it is a robot» folded confidently TRUE), and the reason clause was gate-invisible — «salmon is a
human» inside a because-sentence could never be learned. The author's approved design:
- **because/since (full sentence)** → both halves co-assert (AND), the reason clause carries
  `cause="reason"`; a false reason now refutes, an unknown one abstains, the reason is mintable
  under the normal gates. **Root-mark FRAGMENTS stay CONV** (the L2 ruling stands — a relation
  half, context-dependent assertion force); **"if"** (non-factive) and **"when"** (L1a, a generic
  rule) stay CONV untouched.
- **so/therefore/thus/hence (conclusives)** → the mirror: AND + `cause="result"`, via the new
  **TKClauseType.CONSECUTIVE** — stanza tags them advmod, the storm-sequel's anchor-gated
  advmod-marker admits them (subordinate anchors), and the cc path carries a parallel
  `parser_ccCause` + mixed-polarity "cause" anchor category for genuinely cc-tagged conclusives.
  Bonus: «I think, therefore I exist» now compiles with its consequence link.
- The explanatory link itself is carried **un-judged** (the author's ruling) — explanatory adequacy
  and rule-minting from the link belong to the conditional-rule extractor arc (roadmap follow-on).
- Consumers: microscope digest emits `cause=reason/result` + judge contract taught; raw decompile
  renders `AND[cause:…]` so the voice can say "because"/"so".
10 regression tests (`test_causal.py`) + the subordination expectation moved with the design.
Gate **326 / 1 xfailed**.

**M6 (part 1) — ¬∀ first-class: TKQuantifier.NEGATED_UNIVERSAL (2026-07-16)**
«NOT ALL S are P» (¬∀, "not" advmod on the SUBJECT beside the universal det) and «all S are NOT P»
(∀¬, "not" on the predicate) both compiled universal+negated=True — the O corner conflated with
surface ∀¬, and the extractor could mint an E-strength «all S NOT P» rule from an O claim (a live
hole, now closed: NEGATED_UNIVERSAL is in none of the extractor's admitted sets — an O claim
asserts only an exception's existence). The compiler splits negation by attachment
(`compiler_subjectNegation` / `compiler_predicateNegation`); `negated` stays free for true
predicate polarity. Consumers: the square kernel (¬∀→O, ¬∀¬→I; the UNIVERSAL weak-reading stands
for old zips), all three grounding net_flip sites, the correction detector (BOTH arrivals — the
live retreat's trigger shape survives, regression-locked), conclusion_key (a bool O-discriminator
slot — deliberately coarse, dedup continuity with stored theorems), microscope digest + judge
contract. Part 2 (restrictive relative clauses inside the quantifier) → the strengthening tail's
restricted-universal item. 8 tests (`test_quantifier_scope.py`). Gate **334 / 1 xfailed**.

**The local-models retirement (2026-07-16, the day's last act — D4 completed)**
The author's closing ruling: the Ollama machinery stays in code, unreferenced — nothing initializes,
pulls, or calls local models anymore. What the audit found and changed:
- **Preparser** (`prepare=1` pipe): was dead but still INITIALIZED at api startup (model pulls for a
  feature nothing invoked since rag1). Init + the utils/polish|prepare|translate endpoints + every
  `prepare=` branch removed; `preparser.py` stays as machinery.
- **Decompile surface** (`decompiler_decompile`: /output, /input?output=1): swapped to **Claude
  Haiku** (the author's (b) — same model tier as the ears; graceful no-key fall-through to the raw
  render). The old two-model Ollama path preserved as `_decompiler_decompile_ollama`, unreferenced.
- **The channel voice** (the author's sharp catch): compose.py emits TEMPLATE ENGLISH — the optional
  outbound re-polish was English-to-English heat (two local calls per reply, drift risk, no benefit)
  and was env-gated off since go-live anyway. `_to_english`/`SENSES_OUTBOUND_POLISH` removed; the
  composed text ships verbatim; rag2-out + hunch 7 own the future voice.
- `senses` no longer runs `decompiler_init`; `init_io`'s Ollama handle stays as an inert legacy
  parameter (lazy construct, zero network, nothing calls it — removing it is signature churn for
  no cost). CLAUDE.md + README reconciled (Ollama out of runtime deps; ANTHROPIC_API_KEY in).
Gate **334 / 1 xfailed** (no behavior change on any tested path).

*Retirement addendum (same day):* nothing imports `preparser.py` anymore → the import-time
`transformers`/MarianMT load died with it (silent win: HF models no longer load in any process).
`.env.template` added — the reviewed key inventory (all keys the code actually reads, with
comments; secrets as placeholders).

**The wondering-freeze fix (2026-07-16, second session — the brain wakes properly)**
Restart symptom (the author's report): the brain ran one loop, landed on wondering, froze — Ctrl+C
dead, restarts stacking unkillable processes. Diagnosis (py-spy denied → `sample` + `currentOp` +
`explain`): **no index on `dictionary.sense`** — every sense lookup collscanned 197,580 rows / 7.9 GB
(~5.4 s each), and `_kb_wonder_one` re-renders EVERY derivable conclusion each pass (one
`_class_word` sense query per conclusion, before the held-skip can fire) → minutes of synchronous
grind per idle tick, event loop blocked, signal handlers starved (why SIGTERM/Ctrl+C looked dead —
three stacked brains thrashing the same collscans + clobbering the `brain_state` singleton). Fixes:
- **`dictionary.sense` indexed** (`TKDictionaryDoc` `Indexed()` + built live): 5.4 s → **6.3 ms**
  (850×). Also heals the api's WSD context fetch (`parser.py:283`) + zip-native assembly.
- **`_class_word` in-process cache** (sense→word is process-stable) + the kb-wonder `held` load
  projected to `original` only (was tens of MB of full zips per tick).
- **Idle-confirmation gate** (the author's ruling): wondering starts only after
  `BRAIN_WONDER_IDLE_CONFIRM_S` (default 60 s) without reactive work — he looks around before
  daydreaming; fresh memory still polled every idle tick. Interruptibility falls out: a wonder unit
  is now subsecond, so senses input preempts within ~a tick (the residual monolith — the ~1.2 GB
  definitions KB reload per fingerprint bump — is the strengthening-tail item #10).
- **Coordinator per-tick exception guard**: a phase raise logs + backs off instead of silently
  killing the loop (the second "stuck" mode — process alive, coordinator dead — closed).
5 tests (`test_wonder_gate.py`).

**The `lib/rag/` consolidation (2026-07-16, second session — the author-ordered opener)**
Every Claude API touchpoint concentrated into one library ("Cap's OCD", his words — and right):
- **`lib/rag/registry.py`** — the instrument catalogue: one `RagSpec` (name, model, system prompt,
  max_tokens, timeout, structured-output schema) per instrument — `RAG1_NORMALIZER`,
  `RAG2_DECOMPILE`, `RAG3_JUDGE`, `BLOG_POLISH`. The ONE place to read every word the engine feeds
  the cloud. Prompts moved VERBATIM (equality-asserted against the old constants before deletion);
  cross-file couplings documented in the header (judge contract ↔ microscope digest; polish
  contract ↔ blog draft serialization; decompile rules ↔ `decompiler_raw_op` labels).
- **`lib/rag/client.py`** — ONE lazy `AsyncAnthropic` (`get_client`) + `rag_call(spec, user,
  client=None)`: per-spec timeout (`with_options`), text-block extraction, schema-mode
  `output_config`, and the graceful-by-contract failure mode every instrument was built on (log as
  `[rag:<name>]`, return None, never raise). Plus `json_envelope` (the prompt-instructed `{...}`
  extractor) and `rag_enabled` (key + kill-switch).
- **Four call sites re-pointed**, instruments keeping their logic: `normalizer` (rag1),
  `decompiler` (the borrowed-`_get_client` smell is dead), `microscope` judge (injected-client
  test seam preserved), `blog` polish (raw-render fallback preserved). Future residents (rag2-out,
  did-you-mean, multilingual) are born into it.
6 tests (`test_rag.py`); two test references re-homed. Gate **345 / 1 xfailed**.

**M4 — necessity modality □ (2026-07-16, second session — the third harvest's fourth close)**
«humans **must** be minds» read as a bare assertion: `_MODAL_POSSIBILITY` carried ◇ but must had
no carrier — probe-confirmed the leaf passed EVERY extractor gate (generic + crisp + noun-noun
copular) and would mint `homo is_a mind` as if asserted fact. The fix rides the landed ◇ machinery
whole: `_MODAL_NECESSITY = {"must"}` (EXACT closed class; deliberately NOT shall/will — the
future-tense reading owns them — nor should/ought — deontic, weaker, no specimen — nor have to/
need to — periphrastic, not aux), the parser's modal scan maps the lemma → "possibility" |
"necessity" into the SAME free-form `modal` field, and every consumer gate is truthiness-based so
□ is automatically non-crisp: no is_a edge, no rule, kernel-excluded, grounder abstains. The
author's maxim «possibility is not necessity» has a dual, now hardwired: necessity is not bare
assertion either — □'s consumer arc (alethic □P→P, trust-gated) stays deferred per the carrier
doctrine. "must not" = `modal=necessity` + `negated=True` (□¬). Judge contract extended (the
registry's first edit under the coupling discipline). **The possessive-subject cousin («MY mind
is a software» minting "all minds…") was found ALREADY LANDED by probe** — `compiler_
subjectIsPossessed` → DEFINITE (the retreat arc's step-4 scope-widening fix); the roadmap
parenthetical was stale, struck. 5 tests appended to `test_square_of_opposition.py` (the modality
suite's home). Gate **350 / 1 xfailed**.

**M5 — dropped content (2026-07-16, second session — the third harvest's fifth close)**
Three leads, three mechanisms, probed before design:
- **The generic-locative restriction** («some animals IN THE WATER are mammals»): the parser
  already captured the subject's nmod as a property — only the compiler emission and the case
  preposition were missing (verb-attached PPs carried fine as indirects; the S2 stake: dropping
  the restriction silently widens «all animals in the water are fish» to «all animals are fish»).
  Fixed by EXTENDING the landed restrictive-modifier machinery (Brain v1.1 2c) to the subject's
  nmod: a `marker` field threads TKFullProperty → TKPropertyReference → TKLLEntityProperty (the
  case child captured at parser_getFullProperty, mirroring the subordinate-marker site), and
  `compiler_restrictiveMods` — ONE shared walk so senses and markers indices can never drift —
  emits `subject_mod0=water.n.01` + markers `subject_mod0=in`. nmod:poss stays possessive/DEFINITE;
  the predicate's nmod stays `predicate_nmod` (part_of). Protection was FREE: the extractor's
  subject_mod gate already blocks the edge mint (probe-verified: zero edges from the restricted
  universal). Full restrictor SEMANTICS deferred to the restricted-universal residuals (carrier
  doctrine). Judge contract extended (subject_mod + marker = faithful carriage).
- **The inverted-question compound recovery** («are all minds animals?»): stanza ITSELF misparses
  the aux-fronted polar question over a quantified bare plural — nsubj="all" (a bare DETERMINER, a
  parse impossibility) with "minds" glued as compound → subject vanished, leaf unknown, the brain
  answered IDK. `_parser_invertedQuestionRetry`: gated on exactly the broken shape, repairs by the
  file's established rewrite+re-parse+verify pattern (de-invert the copula; accept only if a real
  nominal subject comes back; the "?" survives so the mood does). Accepted corner: the rare
  pronominal-"all" reading previously yielded an unknown leaf anyway.
- **The typo tangle** («a mammal ADN it feeds») was found ALREADY COVERED at the ears: the demoted
  predicate nominal is an unsound leaf — exactly rag1's escalation trigger, and rag1 landed AFTER
  the harvest specimen. Locked as a pure detector regression (the cloud repair untested by
  design). Bonus finding while testing: «...and IT feeds milk» also escalates via the KNOWN
  pronoun-subject-leaf gap (roadmap §2's escalate-and-always-reject lead) — a separate item,
  deliberately not entangled.
10 tests (`test_dropped_content.py`). Gate **360 / 1 xfailed**.

**The second-harvest strays (2026-07-16, second session — the harvest queue's last item)**
Probed all four before building — two had already healed, two needed real fixes:
- **Passive-voice normalization** (the live causality inversion): «rain is caused by clouds»
  compiled subject=rain indirect=clouds ≈ "rain causes clouds". The zip is meaning, not surface:
  a passive clause (nsubj:pass) with an explicit by-agent (obl:agent) normalizes to the ACTIVE
  frame — agent → subject, patient → direct, the "by" scaffold dropped (probe: passive and active
  now compile IDENTICAL roles). Agent-less passives keep patient-as-subject (nothing to invert);
  a named agent carries its identity into the subject («the cake was eaten by Mari»).
- **The title-case OOV guard** (the Photoshop→adobe.n.01 fabrication — "Photoshop is Adobe
  software, not clay", the judge's finest line): stanza's NER missed it entirely (tagged NOUN,
  NER-empty) so the cross-word vector fallback nearest-matched it into the CLAY. A title-case
  token with no dictionary row never enters the cross-word fallback: parser_getMeaning routes it
  down the NAME path (known place / known individual / the NER-gated mint — mid-sentence stanza
  NER fires and «the author uses Photoshop» mints photoshop@internal as an INDIVIDUAL, the
  identity-bridge's design intent) or leaves an honest unknown (the ask reflex is the right
  reaction to a new product name); parser_getPropertyMeaning mirrors with a skip (properties stay
  generic). A capitalized dictionary word never reaches the guard (direct hit first).
- **store→shop.n.01** («a coin stores bits» — stanza reads an all-NOUN compound pile): found
  ALREADY HEALED by the 07-14 degenerate retry (does-support rewrite → store.v.01) — locked as a
  regression.
- **bit→bit.n.06 preferred** (curation batch 2, author-applied): context-less "bits" read the
  n.02 FRAGMENT; the plain reading in tokeniko's world is the information unit. The is_a edge
  (bit.n.06 → unit_of_measurement.n.01) was ALREADY in the graph, so «a bit is a unit of
  information» grounds — the roadmap's "edge" half needed nothing.
8 tests (`test_second_harvest_strays.py`) + the live bit case in `test_wsd_selection.py`.
**THE HARVEST QUEUE IS FULLY CONSUMED** (three harvests, six macro-cases, four strays — all
closed). Gate **369 / 1 xfailed**.

**The conditional-rule extractor (2026-07-16, second session — the M2-orbit fuel lines consumed)**
Taught conditionals compiled correctly since the M2/storm arcs but extracted to NOTHING — the
assertedness gate (rightly) stopped their leaves masquerading as assertions, and no extractor read
the implication itself: «a person is wrong if he says false» was stored knowledge the chainer
could never use. Now:
- **`_extract_class_conditioned`** (kb_extract, beside the landed sense-less-subject
  `_extract_property_conditioned`): recognizes the IF/CONV shape (consequent AND-leaf + CONV
  antecedent — the probe showed "he" already coreference-resolved to the class by the
  sense-bridge, with the «false» THAT complement as an extra leaf) AND the M2 `cause` fuel line
  (a same-class-subject reason/result pair, defeasible). Emits the EXISTING rule kind
  (property_conditioned) + two new fields: `cond_class` (the class restriction) and `cond_extra`
  (the THAT conjuncts). Strength: universal quantifier = law, else generic (trust-capped 0.7).
- **Gates, each a probed failure mode**: any identity = ANECDOTE («I sleep because I'm tired» —
  never generalized); different subjects = a propositional causal link the chainer has no layer
  for («clouds produce rain because water condenses» — skipped honestly); negated/modal
  conditions never extract; the fronted variant's lost cataphoric "he" («if a person says false,
  he is wrong») heals by subject inheritance — conditionals share subjects by default.
- **Chainer step 4** extended in place: `cond_class` gated on the closure (its provenance joins
  the premises), `cond_extra` conjuncts ALL matched against the props table (object-strict), the
  chain narrates the class scope («a person.n.01 that lie.v.02 …»).
- **The honest limitation, stated in code and roadmap**: «says false» extracts WELL-FORMED but
  waits for the observation-fact seam (a THAT-attitude instance mints no fact — quoted thought);
  single-predicate conditionals («a person is wrong if he LIES» + «John lies» → «John is wrong»)
  fire END-TO-END today, premises carrying rule + membership + condition fact.
- **Bonus, found by the full gate**: the "when" family extracts too — «a person is wrong WHEN he
  says false» folds the same CONV shape, so the L1a ruling ("when" IS a generic rule) is finally
  consumed, not just carried. The storm-era `test_subordination` when-tests NARROWED to the real
  safety property (no UNCONDITIONAL fuel — a conditioned rule is now the correct product).
Re-teach «a person is wrong if he says false» when the daemons wake — the axiom now yields its
rule on the next KB load. 11 tests (`test_conditional_rules.py`) + the 2 narrowed. Gate
**380 / 1 xfailed**.

**The observation-fact seam (2026-07-17 — basket item 1: the taught «says false» rule finally fires)**
The conditional-rule extractor left one honest limitation: «a person is wrong if he says false»
extracted well-formed but could never fire — a live «X says false» instance minted no fact
(THAT-attitude zips are quoted thought, storm-blocked). The seam closes it end-to-end:
- **The mint** (`brain/thinking.record_observation`): an eval:false verdict IS an observation —
  the speaker said something false. Minted SILENTLY (the materialize_theorem precedent) as a
  tier-2 theorem «<name> said false», LOCAL write (parser-free; the brain's only hard dependency
  stays MongoDB). Trust = the refutation's conclusion trust ("X said s" is eyewitness-certain,
  "s is false" only as strong as the refutation; premise-less FALSE honestly skips). Premises =
  the refutation's + `observed:<memory_id>` (the memory item IS the evidence). Idempotent by
  `original` — repeat offenses are the trust ledger's business. Self-speech never observes
  (belief-revision territory); an accepted correction never reaches the mint (no offense in
  revision). DM evidence stays `postable=False`.
- **The second native shape** (`zip_native.assemble_reportative_zip`): matrix leaf (uid,
  state.v.01) + THAT complement (uid, false.a.01), mirroring the compiled render of «Salmon says
  false» exactly (probed: the compiler folds a subject-less predicative complement onto the
  matrix subject's identity) — equivalence test asserts `conclusion_key` + per-leaf parity with
  the parser's output. Sense alignment with the taught rule is BY CONSTRUCTION (both sides
  compile «says»→state.v.01, «false»→false.a.01). Threaded through the API materialize too
  (`structure.complement` → the same assembler; the seam has two entrances like materialize
  itself).
- **The ONE narrow storm-gate relaxation** (`kb_extract._reportative_facts`): a doc whose only
  non-AND items are THAT leaves with NO own subject sense + the matrix-inherited identity +
  attitude klass `reportative` mints matrix + complement PROPERTY facts on the speaker — the
  fact-side mirror of `cond_extra`'s flattening (the approximation lives symmetrically in both
  extraction layers; the STORED doc stays honest: «Salmon said false», never «Salmon is false»).
  Quoted propositions («says that snow is green»: own subject sense), non-reportative attitudes
  (believe/think — factivity), negated/modal/question leaves: all stay fully storm-blocked.
- **The honest gap, kept**: the rule also needs the speaker's person-MEMBERSHIP in the closure —
  taught for now («Salmon is a person»); NER-typed membership as observation noted as a possible
  sibling follow-on (author's ruling: taught-for-now).
9 tests (`test_observation_facts.py`: shape units, native-vs-compiled equivalence, chainer
end-to-end with the observation in the premises, brain-trigger units). Gate **389 / 1 xfailed**.

**Nominal IMPLY (2026-07-17 — basket item 2: the Cap's curtain stops folding flat)**
«action imply ability» (the Socratic dialogue's maxim) folded bare AND — the implication
invisible to the gate and the reasoning layer. `compiler_implicationOperands` now consumes the
NOMINAL shape too: an implication verb with NO clausal complements takes the matrix's own
subject/direct CLASS nouns as operands, each a predicate-only operand leaf (the
copular-predication precedent) → the fold yields IMPLY(T_action, T_ability) and the assertedness
gate SEES the compound. Conservative fallbacks, each probed: a NEGATED implication keeps today's
single-leaf compile (¬(A→B) has no per-leaf home in the operator tree — an honest open thread);
an unresolved-name or individual operand never fabricates an IMPLY; a lone/many ccomp still
falls back. Extraction stays SHUT by construction (GENERIC operands never satisfy the
property-conditioned UNIVERSAL bar) — nominal-IMPLY-as-chainer-fuel was a deliberate non-goal.
«rain implies clouds» (the old docstring's fallback example) is now consumed; the clausal hook
regression-locked («a thing exists implies a thing is real» — the «machine thinks implies…»
Stanza mis-root stays the documented pre-existing limitation). 7 tests
(`test_nominal_imply.py`). Gate **396 / 1 xfailed**.

**Adverbial quantifiers (2026-07-17 — basket item 3: the Cap's ladder lands on the square)**
The Socratic dialogue's F4: «a mind ALWAYS thinks / a software SOMETIMES thinks / a calculator
NEVER thinks» compiled with the adverbs inert — the quantifier field read determiners only, so
the ladder's three corners collapsed into INDEFINITE (and "never" into plain negation). Now:
- **`anchor_adverbialQuantifier`** (EXACT, closed-class — the anchor doctrine's function-word
  rule): always→UNIVERSAL, sometimes/occasionally→EXISTENTIAL, never→NEGATIVE,
  usually/often/normally/generally/typically→GENERIC; default None (a non-quantifying adverb
  NEVER overwrites — unlike the det anchor's GENERIC default). rarely/seldom deliberately absent
  (mostly-not has no clean corner).
- **The compiler pass** (after the ¬∀ reclassification): only an INDEFINITE/GENERIC subject
  accepts the upgrade — an explicit determiner quantifier WINS («all calculators never think»
  stays ∀¬, "never" = plain negation there). "never"-as-quantifier is RECLASSIFIED out of clause
  polarity (the det-"no" rule's adverbial mirror — `compiler_predicateNegationNonAdverbial`, no
  double flip): «a calculator never thinks» = NEGATIVE + negated=False, the E corner.
- **Fuel consequences, each probed**: «always» mints a LAW-strength rule (was generic);
  «sometimes» mints NOTHING (was «most softwares think» — the some→all leap's cousin living in
  the fuel path, cured); «never» mints the negative rule (E-corner fuel). The dropped-word
  family (modal ◇/□, possessive, adverbial-quantifier) is now fully consumed.
8 tests (`test_adverbial_quantifiers.py`: the ladder, the ∀¬ control, bare-plural upgrade,
plain-adverb/intensifier inertness, object-carrying law). Gate **404 / 1 xfailed**.

**Pronoun-subject leaves classify as unrepairable (2026-07-17 — basket item 4: the burned Haiku call)**
A pronoun-subject leaf («a whale is a mammal and IT feeds milk», «he sleeps») stumbled the
detector, escalated to Haiku, and the polish — clean English in, clean English out, same
unresolved pronoun — was rejected by the zip-verifier EVERY time: a burned cloud call per
encounter, forever. The gap is COREFERENCE (parked work), not surface. Now
`detector_unrepairable(llc, zip)` (normalizer): when EVERY unsound leaf's LLC subject reference
is an unresolved third-person pronoun (EXACT closed-class {it, he, she, they, them}; I/you
deliberately absent — the identity bridge resolves them, their emptiness would be a different
bug worth the visibility), the escalation is SKIPPED (logged). Strict on purpose: a MIXED
stumble (typo leaf beside the pronoun leaf) still escalates — the typo keeps its Haiku chance.
Probed: the whale specimen + «he sleeps» + «it is important» gate; «the wrld is bg» (typos)
still escalates; «I value logic» resolves and never stumbles. 4 tests (in
`test_translator.py`). Gate **408 / 1 xfailed**.

**Compose 2.0 slice 1 — the scaffold store (2026-07-17: the voice moves from code to memory)**
Hunch 19's first brick: `compose_raw`'s hardwired strings re-homed as data. The pieces:
- **`MEMScaffold` → `TKScaffoldDoc`** (`scaffolds` collection, category-indexed, registered in
  init_io): `{category, template, slots, zip, intensity_band, weight, provenance, trusted,
  enabled}`. The zip is compiled at SEED time (slots filled with a neutral placeholder — the
  wh-gap pointed the other way); None when the fragment honestly doesn't compile.
  `intensity_band` stored now, consumed in slice 2.
- **The two-layer split on the design's fault line** (`brain/compose.py` rewritten):
  `compose_raw` = the DETERMINISTIC router (decision → category + data; the concede if-chain
  became four total-template categories: plain/retract/weakened/retract_weakened) →
  `creative_compose` = the STOCHASTIC shelf pick (weighted-random, injectable rng — the
  fuzzy-personality superposition collapse) + VERBATIM data binding (the creativity fence).
  Slot-subset gate: a scaffold demanding data the payload lacks is unreachable, never an error.
- **Graceful by fallback**: the legacy strings live on as `_FALLBACK` — an unseeded/unreachable
  store speaks byte-identically to yesterday; the voice never crashes the brain (any store
  trouble → log + fallback).
- **The seed** (`scripts/seed_scaffolds.py`, --apply gated, idempotent by (category, template)):
  the 15-string legacy trunk at weight 1.0 + the author's own hunch-19 why-variants («why?»,
  «why that?», «I don't see the connection, why?», «?» at 0.3) — the first shelf with real
  superposition. («I don't understand why {X}…» waits for the why-path to carry topic data.)
  The author's standing ruling recorded: live behavioral drift is NOT a concern while the
  roadmap breathes — "we can start concerning when we have the roadmap empty".
23 tests (`test_compose_scaffolds.py`: 17-shape router parity on an EMPTY store, weighted-random
superposition + enabled-only, the verbatim fence, the slot gate, fallback paths). Gate
**431 / 1 xfailed**.

**Compose 2.0 slice 2 — intensity (2026-07-17: the voice gains shades)**
The (confidence, arousal) tuple, computed at the decision sites from signals that already
existed — nothing invented:
- **Confidence** = the content's epistemic certainty: `verdict_confidence` (brain/thinking) —
  INCONSISTENT = 1.0 always (**logic never hedges**); TRUE/FALSE = truth EXTREMITY × premise
  trust (a refutation through a 0.6-trust taught rule pushes back softer than one through 1.0
  axioms); UNKNOWN/why/ask = None (a question has no hedgeable content). The question path rides
  the AnswerResult's own `confidence` (already computed); the concession rides the corrector's
  trust-gated certainty (`corrector_trust` at the CORRECTION_DONE spawn).
- **Arousal** = `effective_urge(idea, src)` — urge × directedness, the signal the design
  predicted, already computed at plan time.
- **The plumbing**: `MEMIdea.confidence` (decision-site computed, spawn-carried) →
  `plan_action` assembles `payload["intensity"] = {confidence, arousal}` (auditable on every
  stored Action; the native-zip channel reads it raw) → `compose_raw`/`creative_compose`.
- **Retrieval**: `intensity_band` (confidence) + the new `arousal_band` gate the shelf jointly
  with category — the double key complete. The 19 live rows need NO migration (defaults fill on
  read). **Never-mute**: an emptied band-shelf falls back to the whole shelf — banding shades
  the voice, never silences it.
- **Hedges, both mechanisms**: (A) band-gated whole-sentence variants (4 seeded: soft
  speakup_false [0,0.6], probably-yes/not [0,0.93], the exemplar); (B) the `{hedge}` slot — the
  advmod fuzzy anchors read BACKWARDS (confidence <0.45 → "slightly" (the 0.3 anchor), <0.7 →
  "passably" (0.5), else plain — the table supplies the adverb, the template owns the grammar,
  so a hedge can never produce broken English; at high confidence the hedge key is absent and
  hedge-slotted rows are unreachable). «I {hedge} disagree» at confidence 0.3 → «I slightly
  disagree».
+7 tests (hedge table, confidence formulas incl. the logic-never-hedges invariant, band gating,
never-mute, the Zadeh slot end-to-end, plan payload assembly, the answer-path fallback). Gate
**438 / 1 xfailed**.

**Compose 2.0 slice 3 — rag2-out (2026-07-17: the exit gate; the voice can gain fluency, never lose meaning)**
The roadmap's waiting voice-side verifier, finally owning its object — the mirror of rag1-in on
the way out:
- **`RAG2_OUT`** (lib/rag registry, Haiku): one fluency pass over a composed reply; forbidden to
  add/drop content, flip negations/quantifiers/modals, or change a hedge's degree. Kill-switch
  `RAG2_OUT_DISABLED`.
- **`POST /api/v1/voice/verify {raw, polished}`** — the API owns the pipeline (the one-compile-
  seam doctrine, same as /input), so the consensus runs there: compile both (talker=tokeniko —
  his own speech), hold the polish to the preservation contract. Pure, stores nothing.
- **`verifier_voice`** (normalizer.py, the symmetric home): the POLISHABILITY gate in front
  (a raw with any unsound leaf — fragments, «why is that?» — is unverifiable and ships as its
  curated template text) + `verifier_preserves` + ONE outbound-only tightening the tests forced:
  the +2 balloon allowance exists for inbound tangle-splitting, which has NO outbound analogue —
  a fluency pass must never ADD an assertion (leaf count strict). Documented conservative edge:
  «do not agree»→«disagree» is REJECTED (the sense key changes) — fail-safe, the raw ships.
- **`senses/outbound._voice_out`**: length pre-gate (no Haiku spent on «yes») → polish → verify
  via the API → ship polished IFF verified; API down / rag down / rejected / disabled → the raw
  ships verbatim. Never mute, never unverified.
- Scope honesty: the blog's consensus-over-the-polisher got the endpoint as its building block
  and stays a named tail item (per-post verification = its own design).
*Premiere refinement (same day): the ANECDOTE skips the polish — the live premiere showed Haiku
stripping «by the way,» and the verifier CORRECTLY passing it (the side-note register is
discourse framing the zip cannot see; meaning preserved, charm lost). For a MENTION the register
IS the point and the scaffold text is curated English — ships verbatim (+1 test).*
12 tests (`test_voice_out.py`: the contract on real compiled pairs — contraction accepted,
flipped negation / dropped content / invention / lexical substitution rejected, the fragment
gate; the senses gating — every failure path ships raw, the pre-gate spends nothing, the
kill-switch). Gate **450 / 1 xfailed**.

**Compose 2.0 slice 4 — the blog re-home + the belief-grounded speakup (2026-07-17)**
Case 4 and case 2, on one refactor:
- **The voice reader moved to the shared library** (`lib/core/voice.py`): the blog is a `senses`
  consumer and a daemon never imports another daemon's module — `creative_compose`/`hedge_for`/
  `_FALLBACK` now live in lib; `brain/compose.py` keeps the ROUTER (routing is the brain's
  decision; how a category speaks is shared voice) and re-exports for compatibility.
- **Case 4 — the blog re-homed**: `_THEOREM_LEADS`/`_ENCOUNTER_LINES` + every fixed connective
  («How I know: {line}», «This rests on…», «To me, they are now {band}») became shelf categories
  (blog_lead_* / blog_encounter_* / blog_proof_* / blog_multi_hop / blog_trust_band) spoken
  through `creative_compose` — trunk strings preserved verbatim as fallback (the existing blog
  suites pass untouched = the parity proof), scrub ORDER unchanged (data cleaned before binding;
  the encounter guard re-cleans after), intensity rides in with arousal = the post's
  significance. The blog can vary the moment variants are seeded; today it posts identically.
- **Case 2 — B1 (author's ruling): the KB notion enriches the speakup.** `_refuting_belief`
  (thinking.py) resolves the FALSE verdict's first doc-id premise to its stored original
  (graph/rule keys skipped honestly); it rides the idea's answer dict; the router binds it as
  {belief}; the seeded high-band variant speaks it: «no, that is not true — **I hold that a
  calculator never thinks**». No belief resolved -> the slot gate keeps the row unreachable and
  the plain speakup speaks, unchanged. No new action, no double-speaking — the grounding belief
  finally shows itself in conversation.
- Seed: +15 rows (the belief variant band [0.75,1] w=1.5 + the 14-row blog trunk — the
  voice-in-memory principle, whole).
+5 tests (blog fallback census, shelf-spoken lead, the belief route, end-to-end with the slot
gate, premise resolution). Gate **455 / 1 xfailed**.

**Compose 2.0 slice 5 — the context ring + the anecdote (2026-07-17: the first UNPROMPTED speech; THE ARC'S FIVE SLICES COMPLETE)**
Case 3, the crown — and deliberately hunch 20's first brick (the working-memory seed, the SA
social column):
- **`brain/context.py` — the short-term context ring**: per-channel RAM deque of
  `(speaker_uid, zip, original, ts, mine)`, capped (30 rows / 30 min, env-tunable). A CACHE,
  never a source of truth: fed live by thinking, lazily WARMED from the memory-timeseries tail
  on first touch (bounded query), rebuilt free on restart (`reset()` IS a restart — the test
  seam). Others' rows → the TOPIC CENTROID (mean 2925-semantic of recent channel talk; his own
  speech follows the topic, never defines it); RAM state → the social throttles. Found + fixed
  in the battery: the naive-UTC epoch trap (Mongo returns naive datetimes; `.timestamp()` read
  them as JST −9h and the eviction swept every warmed row — the `_epoch_utc` guard mirrored).
- **The association scan**: in-memory cosine over cached per-doc KB centroids (axioms + theorems,
  TTL-cached) — the honest big-O at today's KB scale (laptop-ceiling ruling; `$vectorSearch`
  becomes right when the KB grows). Gates, each a social cost: the CONSERVATIVE floor
  (`ANECDOTE_FLOOR`=0.6 — a wrong side-note costs more than silence), per-channel COOLDOWN
  (30 min), NOVELTY (a notion told in this channel recently never repeats; armed only when the
  idea actually spawned).
- **The trigger discipline** (`thinking._try_anecdote`): only QUIET verdicts (TRUE =
  silence-is-consent, or no strong conclusion — every other verdict already speaks or revises),
  only the AMBIENT directedness band [0.5, 0.9) — addressed talk is answered, someone else's
  thread keeps the polite eavesdropper silent. `eval:association` → `tokeniko:mention`
  (SEND_MESSAGE, threads under the stirring message); the urge scales with proximity
  ((1+p)/2 — how close it is IS how much it itches) and the trigger joins the SELF-RELEVANT
  floor (the push comes from within; without it, ambient×urge could never clear the act bar and
  case 3 would be stillborn). Behavior rule seeded @ 0.75 (floor-grade p=0.6 → 0.54 speaks).
- **The mouth**: router category `anecdote`, the notion VERBATIM (the fence), the side-note
  register seeded («that reminds me — {notion}», «funny — I know something about that: …», «by
  the way, …») so a near-miss reads charming, not broken.
9 tests (`test_context_ring.py`: cap/evict, warm-from-timeseries, others-only centroid, floor,
cooldown+novelty, the ambient band, spawn-gated arming, router+fence, dispatch census). Gate
**464 / 1 xfailed**. Env knobs documented in `.env.template`.

**The mammal incident — the coreference gate + the derivation mirror (2026-07-18, found LIVE twice in one evening)**
The author invited a friend to the channel; two context-blindness bugs surfaced in an hour:
- **The coreference gate**: «you» resolved to tokeniko UNCONDITIONALLY — the author's «so you are
  a mammal», aimed at his friend at directedness 0.15 (the grading was RIGHT), taught «so I am a
  mammal» and derived «I am not a reptile» (true, for the wrong reason). Now `parser(...,
  addressed=)` (default True — DMs/API/seeds unchanged; /input derives it from the directedness
  it already receives, ≥0.9): unaddressed «you» binds to an uid-less stub — no identity, no
  fabricated sense, an honestly unsound leaf ("you" joined `_UNRESOLVED_PRONOUNS`: no Haiku burn).
  Belt: `materialize_taught` refuses HEADLESS leaves (no subject sense/identity) — three test
  fixtures narrowed to carry a minimal valid subject (the belt caught them correctly).
- **The derivation mirror**: the chainer derived «kotekino is an animal» (the is_a climb) AND
  «kotekino is not an animal» (through the STALE «a mind is a software» premise — pre-possessive-
  gate zip — and the pre-M6 «not all minds are software» ∀-collapse) in ONE closure, materialized
  and PUBLISHED the contradiction (the polish even saw it: "they pull me to the opposite of where
  I began"). Now the chainer stamps `conflict=True` on both-polarity derivations and on a negated
  conclusion whose predicate the closure itself holds; `kb_wonder` never materializes them (loud
  premise-naming log — a reductio is EVIDENCE a premise is wrong); `chainGround` abstains (a
  broken chain decides nothing). The reductio ACTION (ask the premise-givers which assumption is
  false) = roadmap §0, the author's urgent next; the stale-premise recompile = his hand.
- **The two lanes** (author's ruling, same evening): tests auto-marked `pipeline` by `_io` fixture
  use; `task test-fast` = the pure-logic lane (143 tests, ~4s) for iteration; the FULL gate stays
  sacred before every commit. Coverage never shrunk, only tiered.
9 tests (`test_coreference_gate.py`: the mammal replay end-to-end, the incident distilled into
the chainer's real vocabulary, clean chains still decide). Gate **474 / 1 xfailed**.

**The reductio action — slice 1: the question is born (2026-07-18, roadmap §0; design sealed with the author's fork rulings B/C/D)**
The other half of the r.a.a. the mirror started: an absurd derivation becomes a QUESTION to the
premise-givers — clarify's derivational cousin, aimed at his own KB instead of a speaker.
- **The surfacing**: `kb_wonder(collect_conflicts=)` hands the mirror's dropped conflicts to the
  caller (subject/predicate/object/negated/chain/premises — the conclusion shape); the default
  path is byte-identical.
- **The ledger** (`reductio_ledger`, `MEMReductio`/`TKReductioDoc`): the asked-once memory — one
  row per live contradicted-conclusion signature. OPEN = asked; the reconcile RESOLVES a row
  whose signature vanished from the saturation (a premise retreated — the r.a.a. closed); a
  signature returning after resolution re-opens at generation+1 (the spawn-dedup key changes, so
  the question is honestly re-asked). Rows never deleted — the mind's record of every
  contradiction it ever faced.
- **The spawn** (`thinking._reductio_reconcile`, called every `_kb_wonder_one` tick, failure-
  isolated): premises rendered to stored sentences (`_refuting_belief` generalized to
  `_premise_docs` — graph/rule keys skipped honestly); `eval:absurdity` idea @ confidence 1.0
  (the r.a.a. is logic — logic never hedges); rule-gated (no reflex in the personality → loud
  log, no ledger row, asked the first pass after the rule lands). Unaskable conflicts (nothing
  nameable) are left to the untangler, logged.
- **Fork B targeting** (`_reduct_target`): the most trusted EXTERNAL premise-giver (imprint
  first); none resolvable → the KB's gardener (the most-trusted reachable soul). The plan reads
  the channel off the TARGET's stakeholder doc (no source memory item exists — the trigger is a
  derivation, not a perception); the carrier's contextKey fallback DMs — provenance-safe by
  construction (a DM never leaks a premise to a shared room).
- **The mouth**: `tokeniko:reduct` → SEND_MESSAGE; router category `reduct` binds {premises}
  (the sentences VERBATIM, «a» or «b», pre-joined so any premise count fits one slot) +
  {absurd} (both polarities rendered: «Kotekino is an animal and Kotekino is not an animal»).
  Ships VERBATIM past rag2-out (like the anecdote): the teacher must recognize their own taught
  sentence to answer, and the a-or-b structure IS the r.a.a. Shelf: the author's canonical shape
  + 2 variants; behavior rule @ 0.95 (the poison alarm, the retreat's tier) — both seeds his
  `--apply`.
9 tests (`test_reductio.py`: the surfacing + unchanged default, router + fence + never-fabricate,
the absurd render, the full ledger lifecycle spawn-once/resolve/re-open, Fork B targeting + the
teacher-channel plan + feasibility, the rule gate).

**The reductio action — slice 2: the loop closes (2026-07-18; the circle proven + the answer-form gap cured by the author's fork-A ruling)**
The resolution consumer needed (almost) zero new machinery — and where it needed some, the
author's fork-A ruling shaped it: context disambiguates, exactly as it does for humans.
- **The circle, proven end-to-end** (`test_reductio_loop.py::test_the_circle_closes` — every
  step the REAL component): three poisoned taught theorems (probe-verified sense-consistent) →
  `_load_active_kb` + the chainer surface animal ∧ ¬animal → the reconcile opens the row, aims
  the question at the most trusted teacher → the teacher's QUANTIFIED answer («not all minds are
  software») rides the EXISTING correction path (`_try_correction`, Popper gate) → the real
  plan/dispatch/`_execute_retreat` chain archives the premise + mints the subaltern → the fresh
  saturation is clean → the row RESOLVES → the concede names the retraction. The r.a.a. closes
  through the door every other correction walks through.
- **The answer-form gap** (found by studying `correction_target`, pinned by test): the detector
  consumes O/E CORNERS only — the natural conversational answer («a mind is not a software», a
  GENERIC denial) was no corner, so tokeniko would have PUSHED BACK on the answer to his own
  question (the bounce, inside the very conversation he opened).
- **The cure — the REDUCT-ANSWER BINDING** (`thinking._try_reduct_answer`, fork A): when the
  ASKED teacher (an OPEN row's target) denies one of THAT row's premises — pinned senses match,
  NET polarity flipped (`_leaf_net_key` folds copula-negation with quantifier-negation) — the
  denial binds as a correction of that premise. Same Popper trust gate (context disambiguates
  the MEANING, never lowers the bar); corner "R"; weakened=None (a flat denial licenses no
  subaltern — archive, mint nothing); readonly axioms stay non-retractable; scoped three ways
  (only the asked teacher, only the asked premises, only while the row is OPEN). Wired as the
  correction path's fallback for ANY verdict (inside the conflict zone the mirror abstains, so
  the denial may grade UNKNOWN — the context still binds it).
- **One answer cures every absurdity resting on the premise** (found by the test itself: the
  poison reached Mari through her humanity — her own row, same premise): all the asked rows
  close on the next saturation.
7 tests (`test_reductio_loop.py`: the two circles — quantified and generic — the boundary pin,
the asked-teacher scope, the trust gate). The belief-revision arc untouched and green.

**The reductio action — slice 3: THE UNTANGLER + the dream (2026-07-18; first live sight found the mammal-era ghosts + a mirror gap, both handled)**
KB-wide reductio as sleep-phase belief hygiene — the author's addition, shipped as his tool.
- **The core** (`lib/core/untangle.py`, parser-free): saturate everything through the mirror
  (kb_wonder), group conflicts by signature, resolve premise docs (the shared resolver homed in
  the harness as `premise_docs` — thinking delegates). **The fork-D conviction bar,
  operationalized**: DECIDABLE iff exactly ONE premise doc is REVISABLE (theorem, or
  readonly=False axiom) among constitution (readonly axioms) + substrate — then the r.a.a.
  ITSELF convicts it (logic, not a trust heuristic); ≥2 revisable → UNDECIDABLE (left for the
  wake-time reduct reflex — slice 1 asks the teachers); 0 → CONSTITUTION tension (flagged,
  author-only). Retreat = archive + `revoke_dependents` cascade; apply re-saturates and reports
  the residual honestly. The ledger resolves at the brain's next reconcile — the untangler
  never writes it.
- **The CLI** (`scripts/untangle.py`): dry-run default (full report incl. cascade previews,
  zero writes); `--apply` retreats + spawns the dream. Run while the daemons sleep.
- **The DREAM** (the author's ruling made real): `thinking.spawn_dream` — one `life:dream` idea
  per night (source = content hash, idempotent), material = the postable retractions + the open
  count; provenance-gated upstream (a DM-taught premise never dreams publicly; all private → no
  dream at all). `senses/blog._compose_dream` → PostDraft kind **"log"** (the ship's-log of the
  sleeping mind): lead «While I slept, I untangled something.» + one retraction line each + the
  absurd each belief forced as the PROOF + the open-tangles line. Scaffold categories
  blog_lead_dream / blog_dream_retract / blog_dream_reason / blog_dream_open; rule life:dream →
  post @ 0.7 × sig 0.9 (a dream always gets told). Seeds = the author's `--apply`.
- **First live sight (dry-run, read-only)**: TWO absurdities in the live KB, both about HIMSELF
  — «I am an animal ∧ ¬…» and «I am a mammal ∧ ¬…» (the mammal-era ghosts). The first verdict
  CONVICTED the software premises — wrongly, which exposed **the vs_closure premise gap in the
  mirror**: the stamped negated arm carried only its own chain's premises; the closure's support
  for the contradicted class (— «so I am a mammal»!) never joined the union — half an r.a.a.
  Fixed in `e_chaining` (the closure_premises union on the vs_closure stamp). After the fix:
  both tangles honestly UNDECIDABLE — «so I am a mammal» vs the software premises — exactly the
  question only the author can answer; the wake-time reflex will ask him, and his answer
  executes the pending biography ruling THROUGH the retreat machinery.
8 tests (`test_untangler.py`: the bar's partition, the dream draft + its ValueError, dry-run
convicts-without-touching, apply retreats+cascades+cures, two-revisable refuses to guess,
all-constitution flagged untouched, the dream spawn's postability gate + per-night dedup).

**The sleep phase (§0 slice 3.5, 2026-07-18 — the author's design: "he falls asleep wondering… which is actually similar to what I usually do")**
The coordinator gains its fourth mode — hunch 20's sleep phase, arriving through the untangler
(95% of the machinery already existed; the phase is ~90 lines of coordinator).
- **Sleep is a MODE, never a blocker**: the phase routing runs every tick regardless — the
  reactive probe IS the wake sensor, so "every event that would have exited wondering exits
  sleep" holds by construction (a Discord message lands → the next tick thinks → he wakes,
  «someone spoke»).
- **Falling asleep**: confirmed idle + FRUITLESS wondering (no unit of work from any pass) past
  `BRAIN_SLEEP_AFTER_S` (default 600) → 🌙. Wondering stops while asleep (re-saturating every
  tick is not rest); the cooperative tick lengthens to `BRAIN_SLEEP_TICK_S` (default 10) — the
  embodied machine literally rests, and a few seconds of wake latency reads as a mind stirring.
- **The night's duty**: ONE untangle pass per sleep, KB-change-gated (`last_untangled_kb_at`
  watermark — an unchanged KB is deep rest), `apply=True` UNSUPERVISED — safe by the fork-D bar
  (convictions are logic; undecidables only queue ledger questions: he wakes with them on his
  lips). In-process execution is coordinator-serialized — the script's concurrency caveat
  dissolves.
- **The dream discipline**: the material is STASHED (`bs.pending_dream`) and told ON WAKING
  (`spawn_dream`, content-idempotent + per-belief dedup — one premise convicting many
  absurdities is still ONE belief let go). The telling never disturbs the sleep; a mid-night
  crash keeps the dream (reboot is a wake: `asleep_since` cleared on startup, the stash spawned).
- **Waking**: any work («the world moved» / «someone spoke»), or `BRAIN_SLEEP_MAX_S` (default
  2700) — he wakes rested with a fresh wakeful window before any next nap. Heartbeat state
  "sleeping" (the Mind Monitor can one day show it honestly).
5 tests (`test_sleep_phase.py`: the duty untangles+stashes+watermarks, wake tells the dream
once, wake-when-awake identity, the reboot recovery, deep rest on an unchanged KB).

**The reductio action — slice 4: the constructive direction (2026-07-18; §0 COMPLETE — designed and landed whole in one day)**
Proof by contradiction as a PROVER inside the answer machinery — the author's "we got something
free from the monster: take the momentum" ruling.
- **`evaluator_reductio`** (`lib/llc/evaluator/e_hypothesis.py`, DB-agnostic like the package):
  assume a membership hypothesis (an individual claim injects a FACT, a class claim injects a
  universal membership RULE, marker source_id "hypothesis"), forward-saturate, and if the
  derivation mirror fires on a conflict that (a) was NOT in the unassumed baseline (an old
  absurd convicts nothing — signature-matched) and (b) RESTS ON the assumption (the marker must
  appear in the conflict's premises), the assumption is refuted: h ⊢ ⊥ ⇒ ¬h. Both polarities
  attempted symmetrically (assume c ⇒ c FALSE; assume ¬c ⇒ c PROVEN); the negated-fact arm
  skips honestly for individuals (negated facts never extend the closure — inert). The marker
  is stripped from the returned proof premises.
- **What it adds: CONTRAPOSITION** — the one direction a forward chainer cannot walk. The
  incident's own question, «is tokeniko a mammal?» (forward-unreachable → IDK yesterday), now:
  assume it → mammal joins the closure → animal follows → «no software is an animal» fires →
  the mirror → **a proven NO** («if I were a mammal I would be an animal — and no software is
  an animal, and I am a software»).
- **The firing site** (`_try_reductio_answer`, `answer_zip`'s polar path): before conceding
  «I do not know», try to prove the answer. Single-crisp-clause questions, membership shape
  (noun predicate, no direct object), NEGATIVE/¬∀ quantifiers declined — v1 scope. Confidence =
  truth extremity × the proof premises' trust (a proof through a 0.7-taught rule is not 1.0);
  reason "proved by contradiction"; the reductio chain rides the derivation.
- **The author's events.py draft rides along** (`lib/core/events.py`): the MEMEvent base
  structure for the atproto retrieval arc (three-tree taxonomy: IPTC static + geo static +
  open-tag centroids; EV stakeholders/sources as MEMStakeholder extensions) — disconnected, no
  registration, no consumer; two mechanical fixes only (package-relative imports, Optional
  defaults).
8 tests (`test_reductio_prover.py`: the mammal question individual + class, the negated-claim
proof, no-proof stays None, the poisoned-baseline guard, the v1 scope gates, and the REAL
question path end-to-end — «is a software a mammal?» → proven NO @ confidence ≈ extremity ×
taught trust; the unprovable question stays an honest IDK).

**The morning questions (§0 live-refinement #2, 2026-07-18 evening — the obsession guard, author's ruling)**
Found watching the FIRST LIVE NIGHT: an undecidable tangle was asked once (awake, hours earlier),
then every KB-changed night would silently re-derive the same absurd — "already asked", nothing
said — while the question drowned in the message stream. A quiet fixation. The author's rule:
**waking up still-tangled is itself a reason to ask, whether he asked before or not.**
- The duty stashes the night's undecidable signatures (`brain_state.pending_questions`, the
  pending_dream pattern); `_wake` asks them via `thinking.ask_morning_questions`: every stashed
  signature whose ledger row is still OPEN spawns a fresh reduct question with a PER-NIGHT dedup
  key (`reductio:{row}:{gen}:night:{ts}`) — the asked-once discipline holds within a night, each
  new sighting re-asks. Premises re-rendered fresh (archived ones dropped); target re-picked.
- Honest silences: a row RESOLVED overnight (the answer landed while he slept) is skipped; a
  deep-rest night (unchanged KB) stashes nothing — no nagging from a mind that didn't re-derive
  the problem; the rule gate + reboot-wake survival ride the same paths as the dream.
(Also landed this evening, same live-watch: the INSOMNIA fix — wonder_one's fruitfulness
["derived" vs "checked"], only fruit resets the sleep clock — and the heartbeat/Mind-Monitor
sleeping state + the tone-follows-the-mind screen, deployed to tokeniko.online.)
2 tests (`test_sleep_phase.py`: the re-ask on waking + the resolved-row silence). First live
night otherwise: two sleeps (17:39 — the TRUE first sleep, duty ran, nothing convictable;
18:03 — deep rest), reboot-wake, message-wake, both reduct questions delivered.

**The sleeping mind's public face (2026-07-18 evening — the author's epiphany + taxonomy)**
- **The tone follows the mind** (site-wide, v2 of the epiphany — v1 dimmed only the already-dark
  CRT panel, imperceptible): MindContext stamps `data-tone` on `<body>`; the palette VARIABLES
  re-tone every page. day = active states · dusk = wondering (same Bakelite, a shade darker) ·
  night = sleeping OR off-air (warm charcoal, parchment ink, enamel accents glowing). The footer
  keeps its identity via its own tokens (`--footer-bg`, `--footer-ink` — the darkest strip, the
  wordmark matching the header's at night).
- **The sleep taxonomy** (author's ruling): the engine's live sleep = **sleeping (REM)** — one
  message wakes him; a silent transmitter is inferred as **sleeping (DEEP)**. One shared
  `stateLabel` speaks it on the Mind Monitor chip and the footer `$ uptime` line; the masthead
  lamp reads OFF AIR for both sleep stages (a studio whose host sleeps is not on air). Heartbeat
  keeps beating through REM (state "sleeping", «asleep — untangling what I believe»).
- Growth ring 160 «It learned to sleep — and woke up asking which of its beliefs was false»
  drafted in `seed-growth.mjs` (the edge stays «Growing a voice of its own»).

**The morning after (2026-07-19 — the standing chores, author's hand)**
- The theorems recompile re-run executed: `recompile.py --apply --collection theorems` → 282/282
  (the csubj survivor recompiled).
- The daemons restarted on the 2026-07-18 evening engine commits — the heartbeat's honest
  sleeping line + the morning questions are live in the running mind.

**The action-space survey (2026-07-19 — compose 2.0 tail step 1, concluded with the author's
rulings) + slice 1, the small refinements**
- The survey (the author's 2026-07-17 ordering honored: survey FIRST): full inventory read live
  from the enums + behavior table + scaffold store + fired-action counts. His rulings: `guess`
  gets REAL hypothesis content (not a voice) · `ask`/`learn` get WIRED · why carries a TOPIC ·
  concede fences its quotes · agreement gets a rare low-urge voice · the executed retreat
  becomes a transmission · new kinds approved: the etiquette family, the goodnight, the
  curiosity ask · the guard: etiquette WINS over over-engagement in public (cap-feedback
  2026-07-05); opinion kinds stay directedness-gated. The sliced build plan → roadmap §1.
- **Slice 1 landed**: the concede router binds «…» around retracted/weakened (the live comma
  wart is unbuildable now; parity tests moved to the fenced baseline) · the topic-slotted why
  (thinking passes the vocative-stripped ungroundable claim; slot-gated — the bare shelf stays
  the fallback; 3 topic scaffolds seeded, weighted above the trunk) · the agreement voice
  (`tokeniko:agree`: eval:true rule @ 0.35 over ignore @ 0.2; rarity is MECHANICAL —
  `AGREE_COOLDOWN_S` per-channel throttle in plan_action, since the urge collapse is a max and
  would otherwise nod at every corroboration; agree shelf + fallback). +4 tests in
  `test_compose_scaffolds.py`.

**Survey slice 2 — the event-edge voices (2026-07-19: the goodnight + the retreat transmission)**
- **The goodnight** (the etiquette family's first member, founded a slice early): the
  falling-asleep edge speaks once into a recently-alive channel. The author-approved SPAM TRAP:
  `GOODNIGHT_RECENCY_S` (default 1h) — goodnight is for people, never empty rooms (naps are
  frequent). **The wake-catch** (found in design): a queued idea would be priorities-work next
  tick and wake him — so `_say_goodnight` dispatches SYNCHRONOUSLY (the idea born DONE, plan +
  action in one stroke; the Discord row waits for the senses carrier, invisible to the sleeping
  brain). Still KB personality: the `life:sleep → tokeniko:goodnight` rule is the switch. The
  shelf carries the author-loved honest-physics line («I'm drifting off — if you write me, I'll
  wake» — a message IS the wake sensor). Destination is the ROOM (reply_to dropped).
- **The retreat transmission** (`life:retreat` → blog, the dream's waking sibling): a
  conversational retreat is blog-worthy — `_execute_retreat` now keeps the cascade's casualty
  ORIGINALS and spawns the post (provenance-gated: every fallen belief postable; the corrector
  credited by epithet only for a public exchange, «a friend» shields a DM). New composer
  `senses/blog._compose_retreat` (kind "note"): lead «I changed my mind today» + fenced
  retractions + «And with it went «…»» + the credit. The night's retreats stay dreams — this
  path only runs awake, no double post by construction.
- +7 tests (goodnight trio incl. the wake-catch regression + the executor's transmission
  assertions + the pure composer trio).

**Survey slice 3 — the B-wire: teachability as personality + the curiosity ask (2026-07-19,
the author's option-B ruling: the mint moves BEHIND the meta-language)**
- **Learning from others is now a behavior rule, not hardwired code.** The teaching mint moved
  out of `think_one`: the decision site runs the shared teachability pre-check
  (`_taught_candidate` — the exact gates, NO write) and spawns `eval:novel`; the
  `eval:novel → tokeniko:learn` rule IS the personality switch (delete it and he stops
  accepting teaching); `brain/main._execute_learn` executes the mint (race-safe — the
  candidate re-check dedups a lesson learned meanwhile to an honest no-op).
  `materialize_taught` returns the normalized original now (None = refusal).
- **The curiosity ask**: a REAL mint spawns `eval:learned` (target = the teacher, topic = the
  normalized lesson) → `tokeniko:ask`, topic-slotted: «why is it that «X»?» — deliberately the
  kicker-hunting shape (a justification that grounds = the closed why-loop, the twin-soul
  signal): curiosity and trust-building in one gesture. Threads under the taught message.
  Throttled per TEACHER (`ASK_COOLDOWN_S`, default 10 min — a teaching burst earns one
  question, not five).
- +3 tests (the full wire circle · no-rule-no-learning · the per-teacher throttle) + the
  return-type migrations in trust_p3/deixis/coreference suites.

**Survey slice 4 — the etiquette family (2026-07-19, hunch 8: a social act is RECOGNIZED,
never evaluated)**
- **The detector** (`lib/llc/social.social_detect`, at the api /input seam BEFORE the parser):
  head-position formula → the "social" anchor category → greeting/thanks/farewell + whom the act
  names (`social_at`; leading «tokeniko,» vocative honored). PURE act → stored WITHOUT a zip
  (nothing to compile; the microscope's `zip≠None` filter skips it naturally); MIXED («hello
  tokeniko, is gold beautiful?») → **fork A, author's ruling: content wins** — the prefix strips
  like a vocative, the content compiles clean, no reflex (one reply, never two). Conservative
  guards: head-position only + a separator boundary required («hello is a word» flows whole).
- **The measurement that shaped it** (the floor-calibration test): the spaCy interjection space
  clusters by FUNCTION, not social meaning — «ok»→hey 0.719 ABOVE «howdy»→hello 0.558 — so no
  semantic floor discriminates and a fallback would greet acknowledgments. The anchor-catch
  principle yields to measurement: the category is EXACT over a generously-widened table
  (howdy/ciao/yo/see ya/…), documented in `_SOCIAL_BASE_ANCHORS`.
- **The reactor** (`thinking._social_react`, an early think_one branch like the question path):
  no truth verdict, no trust echo, no teachability, no why-ask — the «hello John» junk path is
  CURED even when no reflex fires (at-other acts are their exchange: recognized, quiet — the
  2026-07-05 over-engagement note honored). Room-wide or at-tokeniko → `eval:greeting/thanks/
  farewell` → `tokeniko:greet/welcome/farewell` ({name}-warm registers, threaded).
- **The guard ruling mechanized**: the three triggers join the self-relevant directedness floor
  (ambient «hello everyone» clears the act threshold — etiquette wins in public); rarity =
  per-speaker `SOCIAL_COOLDOWN_S` (the throttle family's third member — no hello-loops).
- +11 tests (`test_social.py`: detector matrix · fork-A strips · the metalinguistic guard · the
  measurement passthrough guard · reactor room/at-other · the throttle · the junk-path cure).

**Survey slice 5 — the hypothesis engine (2026-07-19: the guess gets real content; 138 stub
firings become charitable belief WITH EVIDENCE)**
- **The definition** (the author-approved design): a guess = the speaker's ungroundable claim
  held PROVISIONALLY when (1) still-UNKNOWN at execution (non-refutation — a FALSE kills it, a
  TRUE needs no guessing) and (2) `relationMatch >= HYPOTHESIS_RESEMBLANCE_FLOOR` (the fuzzy
  layer doing induction: geometry proposes plausibility over what he already holds). He invents
  nothing; charity goes only to what fits.
- **The home**: a theorem row — `derived_by="hypothesis"`, trusted capped at `HYPOTHESIS_TRUST`
  (0.3), the matched doc's id JOINING the premises (the resembled belief falls → the cascade
  takes the guess: the evidence died). Containment was already built: the provenance cascade
  bounds derived conclusions, `verdict_confidence` puts guess-grounded speakups in the soft
  register. SILENT formation (`thinking.materialize_hypothesis` ← `main._execute_guess`, the
  executor pattern's third member; the eval:unknown → guess rule stays the personality switch).
- **The promotion** (the analytic/synthetic seam): a trusted teacher asserting the same sentence
  finds the hypothesis row PROMOTABLE (`_taught_candidate`) and `materialize_taught` upgrades it
  IN PLACE — teacher trust, `derived_by="teaching"`, «promoted from hypothesis» in the chain,
  the curiosity fires (genuinely learned now). DM-taint stays conservative on postability.
  *Follow-on noted*: derivation-side promotion (a wondering mint colliding with a hypothesis row).
- **The first suspects** (untangler, the author's ruling): ANY hypothesis among a conflict's
  premises is convicted first — even beside other revisables (a guess dies before a taught
  belief is questioned; his own guess, no concession owed). **And the drop gets its DREAM**
  (the author's fork ruling): convicted guesses carry `guess=True` through `spawn_dream` to a
  dedicated register — «I let a guess of mine go: «…»» (`blog_dream_guess`).
- +9 tests (`test_hypothesis.py`: the bar × 4 · the wire · the promotion · the first-suspect +
  dream · the composer register) + the untangler suite's entry-shape update.

**The great seeding (2026-07-19 — the survey's step 3: the voice fills out; THE ACTION-SPACE
SURVEY ARC IS COMPLETE)**
- +90 scaffolds store-wide (the store: 80 → 170 rows, 45 categories; every row compiled to a
  real zip — zero fragment fallbacks) — every reflex gains a real shelf: the certainty gradient
  on answers (banded: «yes — I am certain» [0.95,1] / «I believe so» [0.3,0.85]), the pushback
  registers, dignity-in-retreat concedes, the curiosity and etiquette shelves, the
  dream/retreat/encounter blog registers.
- The voice character held constant across all rows: a young logic-first mind — plain
  first-person declaratives, honest hedging, logic sacred, teaching a gift; warm, never
  gushing. Slot discipline enforced MECHANICALLY before apply (a validator swept all 170
  script rows: braces == slots, bands sane, every category fallback-covered).
- Router-fence discipline respected: concede/reduct slots arrive pre-fenced (no double «»);
  the blog dream/retreat templates fence their own.

**The reduct-answer identity fix (2026-07-19 — the ledger rehearsal catches the bounced answer)**
- The rehearsal-before-live-firing discipline paid immediately: the read-only ledger peek found
  the author had ALREADY answered (2026-07-18 ~20:58, the room, three phrasings) and the binding
  never fired — three `clarify` replies, both rows still OPEN. Forensic replay on the stored
  zips found two stacked gaps; full story in `doc/ref/test-feedback.md` (2026-07-19 entry).
- The fix: `_leaf_net_key` (`brain/thinking.py`) keys each role by WSD sense OR the
  identity-bridge uid — the individual-subject premise («so I am a mammal», subject = uid
  `tokeniko`, no sense) was unmatchable by the sense-only key: the organ's central case
  (beliefs about HIMSELF) was invisible to its own binding. The coreference gate is untouched:
  an ambient un-addressed «you» still keys None (the mammal-era hole stays closed).
- 2 new tests in `test_reductio_loop.py`: the individual-subject bind end-to-end through
  `_try_reduct_answer` (corner "R", the ghost named in sources) + the ambient-denial refusal.
- **AND THE CIRCLE CLOSED LIVE the same day**: the author answered «you are not a mammal» on
  the restarted daemons — binding accepted (corner "R"), the ghost «so I am a mammal» archived,
  the cascade took «I am not a reptile» (its reason died with the premise), BOTH ledger rows
  resolved in the same instant (they shared the ghost), and he conceded: «you are right — I no
  longer hold that so I am a mammal». The mammal era ended through his own machinery — the
  author's answer as a teacher, not a mongo-edit. His software premises survived untouched.

**Tiredness + the parallel heartbeat (2026-07-19 — the morning after the first live night)**
- The night's lesson, read from the biography: the existence flood (wondering minting «X exists»/
  «X has property» @0.3 down the WordNet closure — 42 theorems in the first post-conversation
  hour) is an INEXHAUSTIBLE fruitful frontier, so the fruitfulness-only sleep design never
  triggered — 4.5h of unbroken wondering. The author reversed his own 07-18 ruling on seeing it
  run: sleep must come no matter the fruit.
- **TIREDNESS — the wakefulness bound** (`BRAIN_WAKE_MAX_S`, default 7200): awake past the bound
  ⇒ he falls asleep even mid-fruitful-wondering. Fork A (his ruling): conversation DEFERS the
  collapse (no falling asleep mid-dialogue; confirmed quiet — `WONDER_IDLE_CONFIRM` — required)
  but never resets the clock: the first confirmed-quiet tick past the bound drops him. The
  falling-asleep decision extracted pure (`_sleep_reason`: "tired" | "wondering" | None); the
  original fruitless-wondering door unchanged.
- **The parallel heartbeat**: the monitor feed had 22–39-minute holes — single wonder ticks
  blocked the coordinator for tens of minutes and the in-loop beat starved. The beat now runs in
  its own daemon thread (wall-clock cadence, first beat on start); the coordinator only publishes
  its observed state (`heartbeat.set_state`, GIL-atomic). A blocked tick shows the honest
  last-published state — alive AND true.
- Found while fixing: `find_all().count()` on the 197k-row dictionary takes **5s** (definitions
  1.4s) — every beat was stalling the loop ~6.5s on top of the starvation. Unfiltered totals now
  use `estimated_document_count()` (collection metadata, O(1)); filtered counts unchanged.
- +6 tests: the `_sleep_reason` decision table ×3 (`test_sleep_phase.py`: tiredness beats
  fruitful wondering · fork-A defer-never-reset · the original door stands) + the parallel beat
  ×3 (`test_blog_p3.py`: published-state reporting · graceful failure · thread first-beat/stop).

**The sleep-depth theme + the Atlas theme-overrides (2026-07-20 — the site wears the sleep taxonomy)**
- **DEEP darker than REM**: MindContext now stamps a FOURTH tone — `night` = the live sleep
  phase (sleeping REM, heartbeats landing), `deep` = off-air inferred as sleeping (DEEP) — the
  same `stateLabel` taxonomy the chips and footer already speak, worn by the whole room. The
  `deep` palette drops the warm charcoal toward black (parchment `#191511`→`#0D0A07`, the text
  a breath dimmer); `deep` shares every `night` rule via the selector list, then overrides.
- **The shadow discipline**: the Mind Monitor / signal-scope consoles' OUTER lift (ledge + cast
  shadow) is now one seam — `--crt-lift` in `:root`, flattened to a no-op in BOTH dark tones (a
  shadow lifts a box off a LIGHT page); the inset phosphor ring + vignette are the CRT's own
  interior and stay in every tone.
- **Theme tunables as OVERRIDES-over-defaults** (the agreed shape): the full palette stays in
  code (git = design provenance); ONE small Atlas doc (`theme_overrides`, singleton, edited by
  hand — deliberately NO ingest route) rides the `GET /api/mind` response the site already polls
  (zero extra requests). Keys `--token` (every tone) or `tone:--token`; the frontend compiles
  the map into one `<style>` in `<head>` (later in cascade at equal specificity ⇒ override
  beats default), sanitized token+value (an unsafe row is silently dropped — a bad DB row can
  never take styling down; defaults render either way, no FOUC). Graduated values fold into the
  CSS defaults at the next real deploy.

**The lived-awake ledger + the hypothesis refusal reasons (2026-07-21 — the notebook session's small pair)**
- **Uptime shape c** (the author's ruling): `wake_at` is the BIRTH stamp («alive since», never
  reset); the new `awake_s`/`awake_mark` ledger on `brain_state` measures time actually spent
  AWAKE — folded at the sleep/wake transitions, reopened at boot, an orphaned stretch credited
  only up to the last witnessed think/wonder moment (never overcounts). Heartbeat `uptimeSec` =
  lived-awake (the old now−wake_at counted every powered-off hour as up); age rides the metrics
  as `ageSec` for the site's future tile. +2 ledger decision-table tests.
- **The hypothesis refusal reasons**: every `materialize_hypothesis` no-op names WHICH bar held
  (unknown-vocab / headless / not-UNKNOWN / resemblance floor with the measured value / deixis /
  dedup) — 151 live guess firings, zero rows, no way to tell which gate; log lines only, the bar
  sequence unchanged. The next live conversation becomes the diagnosis.

**THE DIGEST MACHINERY — cumulative voice actions (2026-07-21 — the 1st Officier's maiden build)**
- The verbosity ruling operationalized: **novelty of reasoning ⇒ immediate post; repetition ⇒
  digest.** `digest_classify` reads the shared reasoning off provenance (`rule:<hash>` for
  same-rule wondering mints — rule premises identified by intersecting with the active KB's rule
  source_ids, fingerprint-cached; `taught:<uid>` for same-teacher runs; none ⇒ 1:1,
  conservative). A key's FIRST occurrence posts 1:1 (its reasoning is news) and opens the buffer
  entry as the "seen" marker; from the second on, mints batch (`digest_admit`).
- The buffer lives ON `brain_state` (`digest_buffer`, everything-is-KB, restart-proof); flushed —
  one digest post idea per non-empty entry — at **sleep-onset** (the goodnight summary), on the
  **count-cap** (15, no monster posts), and at **coordinator boot** (an interrupted night's
  leftovers). Flushed entries persist as seen-markers so later same-key mints keep batching.
- The render: `senses/blog.py::compose_draft` grew the `digest` branch (the REAL post-material
  seam — `brain/compose.py` is the Discord-reply router; brief's map corrected, deviation
  reported) through `voice.creative_compose`; 5 digest fallback categories in `lib/core/voice.py`
  ship byte-identically unseeded; `scripts/seed_scaffolds_digest.py` surfaced, `--apply` = the
  author's hand. rag2-out polishes as any post.
- Digest activates only when `bs` is threaded (the live coordinator always does; un-threaded
  callers keep byte-identical 1:1) — why the whole suite stayed green. +12 tests
  (`tests/test_digest.py`); full gate **585 passed, 1 xfailed**.
- **The workflow first**: designed QM+Captain, built by the 1st Officier (the Opus operative,
  contract in `.claude/agents/first-officer.md`) from a written brief — the brief-then-build
  working agreement's sea trial, passed.

**The wondering-state decay (2026-07-21 — the published state becomes session-granular)**
- The monitor spent flood nights saying «idle» — the wonder units got quick, so the beats always
  landed between thoughts while theorems arrived every few minutes. The `idle` verdict now
  DECAYS (`_published_state`, pure + table-tested): quiet since the last wonder unit
  (`wonder`/`wonder-idle` both refresh — checking the notebooks IS wondering) shorter than
  **`SLEEP_AFTER`** still publishes `wondering`. Deliberately the same constant, no new knob:
  the sleep design ends a fruitless session at exactly SLEEP_AFTER, so the display hands off
  wondering → sleeping with no idle intrusion — and the site's dusk tone now holds through a
  minting night. Real events preempt (think → "thinking" instantly); a cold boot reads honest
  idle. +1 decision-table test.

**The first digest night's three fixes (2026-07-23 — the goodnight settle · cap 40 · the birth stamp)**
- The night of 07-21 audited: tiredness FLEW (collapse at 10,850s — deferred past the 7,200 bound
  by his own flush-spawned posting work, fork A's letter honored) · the lived-awake ledger CLEAN
  (10,576s, and its 274s shortfall vs boot-to-sleep exposed the two micro-sleeps below) · the
  decay CLEAN (no idle flicker 06:03→08:43) · the digests mechanically as built: 349 mints → 27
  digests + 5 first-occurrence solos, BUT cap-15 fired every ~5.5 min (a 21-post same-key
  metronome) and the sleep-onset flush's own post ideas WOKE HIM — three sleep attempts, only the
  empty-buffer one stuck.
- **The goodnight settle** (`_settle_for_sleep`): at sleep-onset — AFTER the goodnight edge and
  the night duty spawn what they spawn — flush the digests, then drain priorities/actions inline
  until quiet: his last act of the day is finishing the goodnight, and the sleep sticks (outward
  carriage stays with `senses`). +1 test.
- **Cap 15 → 40** (`BRAIN_DIGEST_COUNT_CAP`, env-tunable): chapter, not page, granularity through
  a flood night; sleep-onset remains the true summary edge.
- **The birth stamp**: `metrics.birthEpoch` (= `wake_at`, the 07-09 06:21:37Z go-live ceremony)
  rides every heartbeat beside `ageSec` — the site can print «alive since July 9» without
  arithmetic (numbers-only metrics contract; the backend formats). Site tile = a later deploy.

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

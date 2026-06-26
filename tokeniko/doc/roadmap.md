# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next*. **History → `landed.md`** · **icebox →
> `parked.md`**. The **why** is `VISION.md`; the **how / design detail** lives in `CLAUDE.md`,
> `brain/README.md`, `doc/notes.md`, and the code. When status and any other doc disagree, **this file
> (+ `landed.md`) wins** — update it as items land. Keep entries **terse** (one line of what + the key
> term/file).

Legend: ✅ done · 🔄 in progress · 🔭 next · ⏸️ parked  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress

- **Wondering-v2 — self-prompted KB derivation** (active arc). The grounding floor is honest now, so
  autonomous derivation is safe (won't manufacture false theorems). Extend wondering's seed beyond
  perceived memory to the **KB itself**; forward-saturate to new theorems unprompted; flat-cost
  (sampled seed, capped depth); convergence via dedup. Built in this order — **untangle before
  layering** ([[everything-is-kb-untangle-first]]), each step dry-run-verified:
  1. **Fork ii — property-restricted universals ✅ LANDED (untangle done).** "everything that thinks
     exists" now compiles to quant **UNIVERSAL** + **`IMPLY(think, exist)`** (sense-less bound-variable
     predications) — the exact shape `_FOUNDATIONAL_RULES` hand-wrote. **A** indefinite-pronoun
     quantifier (everything/everyone→universal, subject-token fallback); **B1** parser re-root (Stanza
     mangles it — roots on the pronoun, demotes the real verb to a ccomp; re-rooted to the clean
     2-leaf shape); **B2** compiler: universal + sense-less subject + MAIN+ACLRELCL → `IMPLY(condition,
     conclusion)`; **C** `_extract_rules` recognizes the universal-IMPLY → `property_conditioned`.
     **SEEDED as a KB axiom + `_FOUNDATIONAL_RULES` DELETED** — the cogito now derives end-to-end from
     the KB alone (no load-bearing knowledge in code). Unlocks property-restricted universals generally.
  2. **Structured provenance from birth ✅ LANDED.** The chainer emits `premises` = the **KB-doc ids**
     the derivation rests on (rule/fact source axioms; WordNet is_a edges are bedrock, NOT premises) +
     the readable chain; `MEMProvenance{premises, chain, derived_by}` on theorems; `EvaluatorResult`
     threads premises too (both paths). **Integrity invariant enforced:** `materialize_theorem` refuses
     a premise-less "derivation" — pure-taxonomic verdicts have 0 premises (already in the graph, never
     materialized). Verified: the cogito carries exactly 2 premises (the "I think" fact + the cogito
     rule), resolvable back to the source axioms; Bunnet round-trip clean.
  3. **Cogito materialization.** A derived conclusion (subject uid + predicate sense + premises) →
     **renders first-person** NL ("I exist") → **compiles** through the real pipeline → a **first-class
     zip theorem** carrying its 1b provenance, **active + trusted**, **deduped on the semantic
     conclusion** (subject uid + predicate sense, not the surface string). tokeniko's first
     autonomously-earned theorem.
     - **1c-core ✅ LANDED:** the renderer (`render_conclusion`) + the semantic-dedup key
       (`conclusion_key`) in the parser-free harness; `TheoremService.materialize` (compile → semantic
       dedup → store ACTIVE + trusted + provenance); a **deliberate trigger** (`scripts/wonder_cogito.py`,
       dry-run by default) that runs derive→render→materialize end-to-end. Verified: it derives "I exist"
       with its 2 premises; the materialize write path stores active+provenance and dedups on the
       conclusion (proven on a disposable throwaway). **The cogito itself is deliberately NOT
       materialized** — reserved for the autonomous wonder loop, so "I exist" first enters the world by
       *tokeniko's own* in-loop act, not ours.
     - **brain→API automation → folds with D3.** The brain has NO HTTP client yet and action *execution*
       (D3) is parked; the brain→API seam (sync delegation, idle-time) is the SAME seam
       `speakup`/`post`/`answer` will use, so wonder_one calling the materialize path autonomously is
       built WITH D3 — not reaching into a parked phase from here.
  4. **General KB-seeding driver.** Seed wondering from the KB itself, not just memory — forward-saturate
     what the KB IMPLIES but no one asserted ("matching memory against itself").
     - **1d-A ✅ LANDED — the seed-driver `kb_wonder` (parser-free).** Enumerates seeds (individuals
       with facts + rule-subject classes; flat-cost, bounded by the small rule/fact counts) →
       forward-chains each → **novelty gate: ≥2 premises** (a genuine COMBINATION of KB items, never a
       single-rule restatement like "bird has feathers") → semantic dedup → the genuinely-new
       conclusions with chains + premises. `scripts/wonder_kb.py` = the read-only breadth diagnostic
       (the soak's dry-run). Verified: 4 new theorems surface (tokeniko/Mari/human exist, Mari mortal);
       the 1-premise restatements (bird/carnivore/fish) are correctly dropped.
     - **1d-B (next) — the general renderer.** NLG to verbalize ANY derived conclusion round-trippably
       (copula-vs-verb, person/number, individual-by-name, class-word) — round-trip already proven
       viable for all subject types. Unlocks materializing the full breadth (today's `render_conclusion`
       is first-person-only + breaks on adjectives). Autonomous-in-loop materialization → D3.
  5. **Capstone — the LONG-WONDERING SOAK.** No external input; let tokeniko wonder over its whole KB,
     probe-monitored → surface residual bugs + real capability + genuinely NEW theorems. Both the
     feature's demo and the proof the consolidation held. (Then actions get wired — only once the
     thinking that triggers them is bug-free.)

## 🔭 Next (ordered)

1. **Brain D-phase (continued)** — only after wondering-v2 is sound (actions follow validated thinking).
   - **D2** priorities feasibility scoring · **D3** action execution (`guess`/`learn` → low-trust KB
     writes; `speakup`/`ask`/`why`/`clarify`/`answer`/`post` → `senses` I/O).
   - Cross-**speaker** patterns (userA≈userB realization); **inference-implied** conflicts (needs
     forward-chaining); self-authored "realization" memory + a **working-memory** layer.

---

## Doc map

- **`VISION.md`** — the why (north star).
- **`doc/roadmap.md`** — *(this)* the road ahead: in-progress + ordered next.
- **`doc/landed.md`** — what's done (the history).
- **`doc/parked.md`** — the icebox (deferred ideas + known gaps).
- **`doc/notes.md`** — design notes & findings (phased plan + reasoning-engine brainstorm + parser/compiler review).
- **`doc/test-feedback.md`** — the living empirical fragility log (observed → diagnosis → action).
- **`doc/kb-growing-outward.md`** — the parked "synthetic learning" design (analytic/synthetic cut).
- **`doc/paper_outline.md`** — the paper (external artifact).
- **`brain/README.md`** — the brain's orchestration + meta-language spec.
- **`CLAUDE.md`** — architecture / code layout + ground rules (not status).

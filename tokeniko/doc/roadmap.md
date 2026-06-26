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
  2. **Structured provenance from birth.** Chainer emits `premises` = the **KB-doc ids** the derivation
     rests on (WordNet is_a edges are bedrock substrate, NOT premises) + the readable chain;
     `MEMProvenance{premises, chain, derived_by}` on theorems; thread `EvaluatorResult` too (full
     consistency, both paths). **Integrity invariant:** materialize ONLY rule/fact-derived conclusions
     (never pure-taxonomic — already in the graph) ⇒ every materialized theorem has non-empty premises.
  3. **Cogito materialization.** Wondering seeds `forwardChain` from the self-KB → derives `exist.v.01`
     → renders **first-person** NL ("I exist") → compiles via the **API** (sync delegation; the brain
     stays parser-free; wondering is idle-time so sync-slow is fine) → a **first-class zip theorem**
     carrying its provenance. Dedup on the **semantic conclusion** (subject uid + predicate sense), not
     the surface string. tokeniko's first autonomously-earned theorem.
  4. **General KB-seeding driver.** Seed wondering from definitions/axioms (not just memory):
     associative (KB-change-gated) + drift, same flat-cost discipline.
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

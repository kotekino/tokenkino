# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next*. **History → `landed.md`** · **icebox →
> `parked.md`**. The **why** is `VISION.md`; the **how / design detail** lives in `CLAUDE.md`,
> `brain/README.md`, `doc/notes.md`, and the code. When status and any other doc disagree, **this file
> (+ `landed.md`) wins** — update it as items land. Keep entries **terse** (one line of what + the key
> term/file).

Legend: ✅ done · 🔄 in progress · 🔭 next · ⏸️ parked  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress

- *(nothing actively in flight — the consolidation pass is **complete**: grounding floor + cleanups +
  Pillar 3 #2 WSD all landed. Next pickup is the Brain D-phase.)*

## 🔭 Next (ordered)

1. **Brain D-phase (continued)** —
   - **D2** priorities feasibility scoring · **D3** action execution (`guess`/`learn` → low-trust KB
     writes; `speakup`/`ask`/`why`/`clarify`/`answer`/`post` → `senses` I/O).
   - Cross-**speaker** patterns (userA≈userB realization); **inference-implied** conflicts (needs
     forward-chaining); self-authored "realization" memory + a **working-memory** layer.
2. **Wondering-v2 — self-prompted KB derivation** (the grounding floor is honest now, so autonomous
   derivation is safe — it won't manufacture false theorems). Extend wondering's seed-source beyond
   perceived memory to the **KB itself**: seed from a definition/axiom and forward-saturate to new
   theorems unprompted ("matching memory against itself"). Bounded by the same flat-cost discipline
   (sampled seed, capped derivation depth), convergence via `materialize_theorem`'s dedup. **First
   demo target (poetic + concrete):** its very first KB-wondering act could be **proving its own
   existence** — wonder over the self-KB (`I think` + the cogito rule) → derive + materialize
   *"tokeniko exists"* autonomously (deliberately left unmaterialized for this). **Capstone
   validation = the LONG-WONDERING SOAK:** with NO external input, let tokeniko wonder over its whole
   seeded KB (its "huge already-received input") for a long, probe-monitored run — surfacing residual
   bugs, real reasoning capability, and genuinely NEW theorems. Both the feature's demo and the final
   proof the consolidation held.

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

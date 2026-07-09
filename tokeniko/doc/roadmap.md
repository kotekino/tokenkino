# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## ✅ Brain v1.1: the Unified KB — ARC COMPLETE (2026-07-03 → 2026-07-09)

The whole ordered build (steps 1–5: write-path invariant → generic taxonomy → provenance cascade +
theorem fuel → universal extractor + sufficiency → reason-over-everything + subject-WSD hardening +
the validated enriched soak) is **landed — see `landed.md`**; vision/design stays in
`doc/ref/brain-v1.1.md`; residuals in `parked.md` (incl. the deepest pole, predicate-complement
capture, and the mentalese materialize constructor). The reasoning core is done.

## 🔭 Next (ordered)

### Going live — embodied I/O (core TK v1)

The autonomous loop is closed in **dry-run**; these wire the real `senses` I/O so tokeniko actually
perceives and speaks. Each carries an **open design question** to brainstorm before building.
*(ATProto/Bluesky is the third channel — parked behind these; see `parked.md`.)*

- ✅ **Discord DM loop (going-live P1–P3)** — landed + LIVE-VALIDATED 2026-07-09 (first real
  conversation: silence-as-consent, honest IDK, the cogito answered, compliments interrogated) —
  see `landed.md`. The senses-arc order (author-approved): **B deepen the 1:1 → C channels →
  D trust ledger**, below.
- **B — deepen the 1:1 (NEXT):** (1) **self-speech → memory** (delivered outbound lands as
  `sourceId=tokeniko` memory items — biography completeness + the prerequisite of context
  derivation); (2) **open-why derivation** (context is NEVER volatile state — DERIVE the open
  expectation from the memory timeseries: recent own-question to this speaker / reply-threading →
  evaluate the inbound as a candidate explanation); (3) **inbound preparser** (`prepare=1` on the
  senses→/input call — "beause" sailed in untouched).
- **C — channel listening + directedness grading.** Drop the DM-only filter; grade the scalar
  (@-mention/name/reply-to-him ~0.9 · ambient ~0.4 · someone else's thread ~0.15); Priorities
  multiplies urge by directedness (discretion → silence below the act threshold). The **overheard
  vs directed** design question resolves INSIDE the scalar — brainstorm the grading before building.
- **D — trust ledger (per-stakeholder opinion).** Neutral start → episodes (redundant agreement
  weak+ · novel-valid-bridging strong+ (the kicker) · disagreement weighted by the BELIEF's trust ·
  logic violation strong− · self-inconsistency strong−, the liar proxy) → hysteresis →
  `tokeniko:more-trust`/`less-trust` internal actions. Kotekino anchored by imprinting, never by
  the adder. Feeds the D-phase learning channel + the trust-gated tkzip lane.
- **Blog (the website) as an OUTPUT channel** — a `senses`-carried output (the public window), driven by
  the **wondering/reflection** phase: an **urge to post** → an action to post to the blog. **OPEN Q —
  what triggers a post:** a freshly-discovered theorem is one source, *but not only* (novelty?
  significance? a periodic reflection digest?) — needs an idea on the urge model. *(The author's hunch:
  materialize-a-theorem → urge-to-post to tokeniko.online.)*

---

## Doc map

**Status docs (`doc/` — the single source of truth for status; the STRICT invariants in `CLAUDE.md`):**
- **`doc/roadmap.md`** — *(this)* the road ahead: in-progress + ordered next. Nothing landed, nothing parked.
- **`doc/landed.md`** — what's done (the history).
- **`doc/parked.md`** — the icebox (deferred ideas + known gaps).

**Reference docs (`doc/ref/` — extended context per task + future-reference material; NOT status):**
- **`doc/ref/brain-v1.1.md`** — the Brain v1.1 **vision + design** (the Unified-KB reframe: everything-is-reasoned-over-TKZip, write-path invariant, universal gate, trust-by-source; + the #1–#6 findings). The conceptual center.
- **`doc/ref/notes.md`** — design notes & findings (phased plan + reasoning-engine brainstorm + parser/compiler review).
- **`doc/ref/test-feedback.md`** — the living empirical fragility log (observed → diagnosis → action).
- **`doc/ref/kb-growing-outward.md`** — the "synthetic learning" design (analytic/synthetic cut).
- **`doc/ref/paper_outline.md`** — the paper (external artifact).

**Root:**
- **`VISION.md`** — the why (north star).
- **`brain/README.md`** — the brain's orchestration + meta-language spec.
- **`CLAUDE.md`** — architecture / code layout + ground rules (not status).

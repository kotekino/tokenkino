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
- ✅ **B — deepen the 1:1** — landed 2026-07-09 (self-speech → zip-less biography items; the
  open-why derivation — structural reply-threading + recency over the timeseries, why-regress
  suppressed; inbound preparser on) — see `landed.md`. Follow-on: the explanation LINK as learning
  fuel is the D-phase teaching channel.
- ✅ **C — channel listening + directedness grading** — landed 2026-07-11 (DM-only gate dropped;
  the ladder DM 1.0 / addressed 0.9 / ambient 0.6 "polite guest" / others' thread 0.15; Priorities
  gates on urge × directedness; preparser off, B3 reversed) — see `landed.md`. Follow-on parked:
  conversation momentum (timeseries-derived lift) — see `parked.md`.
- **B-item — the runtime-WSD frequency-prior investigation.** Why did «a dog is a reptile» compile
  subject **dog.n.03** ("a fellow") instead of dog.n.01? Lesk had no overlap either way; the
  centroid leaned wrong and the frequency-prior guard didn't default to the smallest sense number.
  Root-cause it in `parser_disambiguateSense` — benefits EVERYTHING (the chainer's unanimity-gated
  canonicalization landed 2026-07-11 works around it for refutations only). One live specimen in
  `doc/ref/test-feedback.md` (2026-07-11 later, S3).
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

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
- ✅ **B-item — the WSD copular-circularity guard** — root-caused + landed 2026-07-11 (the
  "confident" centroid was the claim's own predicate: dog.n.03 at 0.83 vs the canine's 0.72 next
  to reptile — disambiguating a subject by the predicate ASSUMES the claim true; the copular
  partner is now excluded from WSD context, both directions, modifiers kept) — see `landed.md`.
- ✅ **D — trust ledger** — landed + LIVE-VALIDATED 2026-07-11 (P1 substrate · P2 meta-language
  echoes · P3 teaching channel; the live play: Hellen's kicker 0.5→0.6, John's self-inconsistency
  0.5→0.3, clarify + episode side by side) — see `landed.md`; specimens in
  `doc/ref/test-feedback.md` (night). **Later consumers of the same ledger** (when their time
  comes): the trust-gated tkzip lane; attitude-report unwrapping (events/facts-as-axioms);
  tier-1 teaching by an EARNED-trust stranger (the path is open — Hellen is 4 kickers from the
  bar).
- ✅ **Blog (the website) as an OUTPUT channel** — ARC COMPLETE, premiere live 2026-07-12
  («Learning Who Made Me» on tokeniko.online — the first self-initiated transmission; the site
  republished real, coming-soon off). P1 `life:*` triggers · P2 composer+Claude polish · deixis
  normalization · P3 carrier+heartbeat · P4 premiere — all in `landed.md`; specimens + the
  false-200 and never-beat lessons in `doc/ref/test-feedback.md` (2026-07-12). **The going-live
  arc (DM → channels → trust → blog) is COMPLETE.** Follow-ons when their time comes:
  `life:learned` / `life:discussion` triggers, consensus-over-the-polisher. (Seed retraction ✅ —
  done 2026-07-13 with the website polish arc, see `landed.md`.)

### Robustness — bugs from the live play (2026-07-12, author-witnessed)

- ✅ **The wh-position bug** — landed 2026-07-14 (`_parser_whAttachesToRoot` gates both detection
  sites), see `landed.md`. Surfaced en route: the bare-copular "?"-less question detector gap
  (tracked as xfail — a second detection signal is future work, designed deliberately).
- ✅ **The vocative wart** — landed 2026-07-14 (`strip_vocative` beside deixis at both
  materialization sites; the two polluted theorems repaired, the dedup-defeat duplicate
  archived), see `landed.md`.
- ✅ **Operator-aware chainer rules (THE STORM fix)** — landed 2026-07-14, see `landed.md`.
  Follow-on when its time comes: a dedicated conditional-rule extractor so a taught IMPLY/CONV
  becomes a USABLE implication rule (today it is safely blocked, not exploited); re-teach
  «a person is wrong if he says false» after that.
- ✅ **Charity of interpretation (the bit incident)** — landed 2026-07-14 as option A: tier 3
  (physical⊥abstract) removed from the evaluator's refutation tiers, see `landed.md`. Follow-ons
  when their time comes: curate `bit.n.03` + its is_a edge (so the claim grounds TRUE, not just
  unrefuted); WordNet-wide sibling-sense abstention IF tier-1/2 false refutations ever appear.
- **Identity fission on rename** (live specimen 2026-07-13): the soul uid embeds the mutable
  display name (`name@channel:talker_uid`), so renaming a Discord account minted a SECOND soul
  for the same person (test-probe-hellen → playbot-hellen; trust history orphaned, fold reset).
  Fix: key identity on the channel-native id (the snowflake) alone; the display name becomes a
  mutable property — a rename then updates the name, never the identity. (Healed manually this
  once: episodes re-keyed, references re-pointed, duplicate soul removed — the merge the engine
  should one day perform itself.)

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

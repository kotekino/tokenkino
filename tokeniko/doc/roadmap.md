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
- ✅ **Identity fission on rename** — landed 2026-07-14 as option A + aliases (snowflake-first
  lookup, uid immutable at first mint, renames update `name` + append to `aliases`), see
  `landed.md`.

### Robustness — the storm sequel's leak (2026-07-14, the author's deliberate re-test)

- ✅ **Subordination must survive compilation** — landed 2026-07-14 (the storm-sequel fix,
  three dominoes: the anchor-gated advmod-marker, TEMPORAL→CONV, the root-mark fragment path),
  see `landed.md`. The 13-lead corpus stands as its regression base (`test_subordination.py`
  covers the representative shapes).

### The harvest fix queue — the first portrait's clusters (2026-07-14 triage)

The microscope's first full-history sweep (98 judged / 42 leads / five clusters — the sweep itself
in `landed.md`, specimens in `doc/ref/test-feedback.md`). Author's ruling: **input quality first** —
this queue precedes instrument-arc item 2. Cluster A (subordination) landed above; B was
instrument-side (judge contract taught). The rest, in order:

- ✅ **Complement/locative survival + the places bridge** — landed 2026-07-14 (F1 places join the
  identity-bridge · P2 the author's places table reasoning-live via injected readers · F2
  xcomp→THAT · F3 compound-name assembly; `markers` = the zip's third symbolic map), see
  `landed.md`. **Follow-ons when their time comes:** the extractor consumes indirect roles +
  markers (a locative fact as chainer fuel — with the conditional-rule extractor family); the
  residual family members from the old parked #2 (the **infinitival/control** complement "want to
  know their creator" now folds THAT via xcomp — verify; the **possessive relation** "kotekino is
  MY creator" still flattens — the creator-of-ME bond needs its own carrier).
- ✅ **Dictionary curation batch → the WSD selection fixes** — landed 2026-07-14. The diagnosis
  probe redrew cluster C: the "coverage gaps" were mostly SELECTION bugs (Lesk self-mention
  exclusion · the ADJ candidate pool unions 'a'+'s' — satellites were invisible · stative
  participle routes to the surface form's adjective · `bit.n.06` curated via
  `scripts/curate_add_senses.py` · the judge now receives the GROUNDED glossary — the thinker
  lead was a judge gloss-hallucination; partridge was already healed by the frequency-prior
  guard), see `landed.md`. New lead surfaced en route: «a coin STORES bits» resolves
  store→shop.n.01 (POS/parse — tracked with the singles).
- 🔭 **Singles** (cluster E + the B-nugget): spurious THAT-wrap on a coordination; **wh-gap by
  verb frame** ("what do you like?" gaps the DIRECT object, not the predicate — `anchor_whType`'s
  what→predicate is frame-blind); elided-subject quantifier inheritance («the cat is dead and
  alive» — the second clause should inherit definite); «a coin STORES bits» → store resolves
  shop.n.01 (a POS/parse miss, found by the WSD diagnosis probe). (The embedded wh-complement
  stays deferred with the questions plan; «hello John» etiquette is hunch 8's territory; the
  conditional-rule extractor is the STORM follow-on above.)

### The instrument arc — LLMs as instruments around the mind (the 2026-07-14 summit; hunches 11 + 10)

The pattern the project keeps choosing, made explicit: big LLMs as *instruments around* a mind
that stays pure, small, and inspectable — a microscope on its understanding, verified translators
at its ears and mouth. Order settled at the summit: **the microscope first** (its evidence
compounds with calendar time and writes the translator's spec), the core-consistency surgery
beside it, the translator last.

1. **rag3 — the microscope** (hunch 11, "the Graal"): a continuous oracle that turns every live
   sentence into a judged test case. **Inputs-only** (author's call — the self-render path is
   about to be retired by item 2, and the output rendering belongs to item 3's verifier).
   - ✅ *P1 — the instrument* — landed 2026-07-14 (`senses/microscope.py`: post-hoc poller +
     `tkzipdebug` + the Opus judge with the contract mini-RAG), see `landed.md`.
   - ✅ *P2 — the harvest loop* — OPENED with the first full-history sweep 2026-07-14 (98 judged /
     42 leads / five clusters triaged with the author; the judge's contract learned
     perspective-resolution), see `landed.md`. Now **standing practice**: entries are LEADS, not
     verdicts — triage stays with the crew; confirmed leads become `test-feedback.md` entries →
     regression tests → fixes. The self-growing seedbank, running.
2. **Zip-native derivation — no internal compilation** (core consistency, the author's gut made
   rank): wondering's conclusions are born as ZIPS — the NL render → recompile round-trip retires
   from the derivation loop (NL remains only at the I/O boundary). Kills the round-trip corruption
   class at the root: sense-pinning becomes unnecessary, the storm's render leg disappears. A mind
   should think in its own representation — NL is I/O, not thought.
3. **The translator apparatus** (hunch 10 — the Japan-translator philosophy: the mind is the mind,
   the voice is the voice of the translator): rag1-in (typos, convolution unwinding, translation —
   NORMALIZATION, never interpretation; `item.original` always preserved) + rag2-in (meaning-
   preservation verifier — input polish sits on the BELIEF path, so the verifier matters MORE here
   than on output) + rag2-out (= the consensus-over-the-polisher follow-on, folded in). **Spec'd
   from rag3's harvest** (author's ruling): the microscope's evidence decides what is genuinely
   messy input (rag1's job) versus parser bugs (fixed, never papered over — the good voice must
   not fix the brain one layer earlier).

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

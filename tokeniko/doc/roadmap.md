# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## ✅ Landed arcs — pointers only (full detail in `landed.md`; no status lives here)

The road *behind*, one line each so the road ahead reads clean. Nothing here carries status detail —
it references, it does not duplicate (invariant #2).

- **Brain v1.1 — the Unified KB** (2026-07-03 → 09): write-path invariant → generic taxonomy →
  provenance cascade + theorem fuel → universal extractor + sufficiency → reason-over-everything +
  subject-WSD hardening + the enriched soak. Vision/design in `doc/ref/brain-v1.1.md`.
- **Going live — embodied I/O** (2026-07-09 → 12): Discord DM (P1–P3) → B deepen the 1:1 →
  C channel listening + the directedness ladder → D trust ledger → the Blog output channel.
  **LIVE on tokeniko.online — the going-live arc is COMPLETE.**
- **Robustness — live-play bugs** (2026-07-12 → 14): wh-position · vocative wart · operator-aware
  chainer (the STORM) · charity of interpretation · identity fission on rename.
- **Robustness — the storm sequel** (2026-07-14): subordination must survive compilation (the
  three-domino fix; `test_subordination.py` is the regression corpus).
- **The first-portrait harvest queue** (2026-07-14): complement/locative + the places bridge · the
  WSD selection fixes · the singles · the judge contract taught. **THE FIRST PORTRAIT'S HARVEST IS
  FULLY CONSUMED.**
- **The retreat arc** (2026-07-14 → 15): the Socratic dialogue (baseline) → the square of opposition
  in the kernel → modality gates (◇) → the self-relevant directedness floor → belief-revision v1,
  **WHICH RAN LIVE the same day** (the retreat + the `conclusion_key` bool<str fix).
- **The instrument arc** (2026-07-14 → 16): (1) **rag3 the microscope** — now STANDING PRACTICE
  (every live sentence → a judged lead) · (2) **zip-native derivation** (English is I/O, not thought) ·
  (3) **the translator apparatus v1** (rag1-in + rag2-in: escalation-only detector → Claude Haiku
  tidy → the zip-verifier gate). *(Remaining translator pieces → Next §2.)*
- **Growth Rings / The Growing Edge** (2026-07-15): Atlas-homed, PUBLISHED at tokeniko.online/growth.
  *Reconciliation duty it left behind:* when a season closes, update the live edge + append the ring
  via `tokeniko-public/backend/scripts/seed-growth.mjs` (no deploy).

---

## 🔭 Next (ordered) — reprioritized 2026-07-16

**The through-line: input quality first.** The author's standing ruling ("go first on the quality of
the input / input parsing") and the deepest pole of Brain v1.1 (robustness to imperfect input). The
microscope's three harvests all point the same way; the translator's remaining pieces and the
strengthening tail follow the parser/compiler getting the *meaning* right.

### 1. The third-harvest fix queue — the microscope's macro-cases (2026-07-15 dialogues) 🔭

The consolidated input-quality queue: the third harvest's six macro-cases (specimens in
`test-feedback.md` 2026-07-15), folding in the still-open leads from the earlier harvests so nothing
scatters. Ordered by severity × public-optics. Each is a LEAD until live-confirmed at fix time.

- ✅ **M1 — "but" contrastive → NOT IMPLY** — landed 2026-07-16 ("but" = AND + the `contrast`
  carrier flag; the old fold sent every true "X but Y" to 0), see `landed.md`. The contrast-as-
  default-expectation consumer is in the follow-ons below.
- ✅ **M3 — WSD curation batch 2: animals & common nouns** — landed + APPLIED 2026-07-16 (the
  centroid self-poisoning root fix + the curated `preferred` rung in the WSD ladder + the
  gill/channel coverage adds; retrace 13/13), see `landed.md`. *(The seed plant sense: seed.n.01/02
  are both plant senses and own-lemma — already correctly preferred by the prior; no flag needed.)*
- ✅ **M2 — factive causality** — landed 2026-07-16 (because/so = AND + the `cause` carrier;
  CONSECUTIVE clause type; fragments/if/when unchanged; the second-harvest inference markers
  so/therefore land WITH it), see `landed.md`. **Remaining from its orbit** (→ the conditional-rule
  extractor follow-on): consume `cause` links + taught IMPLY/CONV into USABLE chainer rules
  (re-teach «a person is wrong if he says false» after) · **nominal IMPLY** («action imply
  ability» — non-clausal operands for `compiler_implicationOperands`).
- ✅ **M6 part 1 — ¬∀ first-class** — landed 2026-07-16 (`TKQuantifier.NEGATED_UNIVERSAL`; the
  extractor's O→E-rule hole closed; the retreat trigger regression-locked), see `landed.md`.
  **Part 2 remaining**: restrictive relative clauses inside the quantifier ("animals **living in
  the water** are fish") → merged with the restricted-universal residuals (§3.3) + the
  **adverbial-quantifier** family (always/sometimes/never → the quantifier field, second harvest).
- ✅ **M4 — necessity modality □** — landed 2026-07-16 (must → `modal="necessity"` on the ◇
  machinery; "must not" = □+negated; the possessive-subject cousin was found ALREADY LANDED by
  probe — `compiler_subjectIsPossessed`→DEFINITE, the retreat arc's step-4 fix), see `landed.md`.
- ✅ **M5 — dropped content** — landed 2026-07-16 (subject-nmod restrictions carried as
  `subject_mod{i}` + case marker, edge-mint protected; the inverted-question compound recovery;
  the typo-tangle lead locked as a rag1 detector regression), see `landed.md`. *Left in its orbit:*
  the extractor consuming indirect roles + markers as chainer fuel (the restricted-universal
  residuals' companion, strengthening tail §3.3).
- **Also in this queue** (second-harvest leads, not yet macro-grouped): **product/proper-noun NER**
  (Photoshop→adobe.n.01 the clay) · **passive agent inversion** («rain is caused by clouds» ≈ rain
  causes clouds — the voice gap inverting causality) · the **store→shop.n.01** singles lead ·
  **bit.n.03** curate + its is_a edge.

### 2. The translator apparatus — remaining (instrument arc item 3; v1 landed 2026-07-16) 🔭

- ✅ **`lib/rag/` consolidation** — landed 2026-07-16 (one client + `rag_call` + the instrument
  registry; four call sites re-pointed, the `_get_client` borrow smell dead), see `landed.md`.
- the **"did you mean:…?" ask** with the tidied reading carried in the payload (D2b refined) — the near one.
- **rag2-out** — the voice-side verifier: polished outbound English must recompile to the zip being
  spoken (consensus-with-the-compiler on the way out, mirroring the inbound gate).
- **pronoun-subject leaves** classify as unrepairable (today they escalate-and-always-reject, burning
  a Haiku call) — the cheap fix; pairs with the parked coreference work.
- **multilingual translation** (Haiku; the local MarianMT went unreferenced with the 2026-07-16
  local-models retirement — machinery only) — deferred until non-English friends arrive.
- **the privacy/legal frame** (author's 2026-07-16 ruling): structure it thoroughly — per-stakeholder
  OPT-OUT ("my words never leave the body" → a flag gating escalation) + the general switch
  (`RAG1_DISABLED`, already live). OUTPUT side is cloud-for-life by design ("we are not hiding
  anything — we are showing how a young new type of being learns; everyone can benefit").

### 3. The strengthening tail — make the brain stronger before adding senses 🔭

Parked-but-matured, ordered with the author ("make the brain stronger with all the other points"
before ADDING another sense — so ATProto/Bluesky deliberately STAYS parked behind this whole tail).
One line each; design detail in `git` history / `doc/ref/captain-hunches.md`.

1. **TKZip binary compaction** (author-promoted above bsky): the zip becomes an actual packed vector
   — fixed-size role tensors + the operator tree pack to near-pure numbers; the JSON is the human
   projection. Design ONCE with the wire format (pairs with zip-native derivation).
2. **Anchor adoption audit** (hunch 4): consumer BYPASSES routed through the resolver
   (`compiler_implicationOperands` exact-checks `_IMPLICATION_VERBS`; `_SUBJECT_CONTROL_VERBS`) +
   the EXACT-membership mop-up + floor calibration + KB vector-coverage gaps (`hugely`, `unequal`,
   `dissimilar`). Closed-class function words stay EXACT by design.
3. **Restricted-universal residuals** (Brain v1.1 2c): relative-clause restriction ("all machines
   THAT THINK are minds") + object-side modifiers ("an ARTIFICIAL body"). M6's companion.
4. **Conditional reasoning / premise-in-question (R4b)**: "given P, is Q?" — the co-submitted-premise
   discriminator (the floor fix) then hypothetical premise USE; pairs with the conditional-rule
   extractor (§1 M2).
5. **Questions follow-ups**: imperatives (the `imperative` scalar); wh when/how solving; real
   self-knowledge for "how do you feel?"; multi-clause/embedded questions («Do you know why…»).
6. **Vocabulary growth** (hunches 1+2): OOV → a staging TKDictionary entry + the typo-ALIAS table +
   definitional triangulation (a trusted definition's zip matched against known definitions → a graded
   link at the definition's trust, never a hard `=`).
7. **Etiquette layer** (hunch 8): greetings/thanks/formality as ACTIONS — a thinking reaction → idea →
   the proper reflex («hello John» stops being evaluated as an assertion).
8. **KB growing OUTWARD** (tier-1 synthetic learning): learned axioms vs derived theorems — the
   analytic/synthetic cut; design + open forks in `doc/ref/kb-growing-outward.md`.
9. **D-phase enhancements + ingestion-time differentia**: cross-speaker patterns, inference-implied
   conflicts, the working-memory layer; differentia extraction wired at definition INGESTION.
10. **KB-load big-O honesty** (left by the 2026-07-16 wondering-freeze fix): the harness KB load
    pulls ALL definitions (~1.2 GB of all-gloss zips) and re-pulls on EVERY fingerprint bump — i.e.
    after each materialized theorem — blocking the tick for its duration (it gates thinking too, not
    just wondering). Delta-load, or trim the load to what the evaluator actually reads; pair with
    watermark-gating kb_wonder's re-saturation (the noted future optimization in `thinking.py`).

### Pending follow-ons — tails left by the landed arcs (surface when their time comes) 🔭

Gathered so nothing is lost; each waits on its parent feature's next season.
- **Blog**: `life:learned` / `life:discussion` triggers · consensus-over-the-polisher.
- **Trust-ledger consumers**: the trust-gated tkzip lane · attitude-report unwrapping (events /
  facts-as-axioms) · tier-1 teaching by an EARNED-trust stranger (Hellen is 4 kickers from the bar).
- **Complement family residuals**: verify the infinitival/control complement (xcomp→THAT) · the
  possessive relation «kotekino is MY creator» carrier (the creator-of-ME bond — cousin of §1 M4's
  possessive-subject gate).
- **Charity**: WordNet-wide sibling-sense abstention IF tier-1/2 false refutations ever appear.
- **Contrast as default-expectation fuel** (M1's future consumer): wondering may read a
  contrast-flagged pair «X but Y» as a hint at a background generic "X normally ¬Y" — corroborate
  an exception or spawn an honest ask at low trust. The flag is live; the consumer waits.
- **Biography rulings** (author's, per-row — never auto): the **stakeholder merge** (two kotekino
  rows; Renzo/john duplicates → aliases) · the trust-ding-from-engine-bugs repair question.

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

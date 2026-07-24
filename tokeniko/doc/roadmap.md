# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## ✅ Landed arcs — pointers only (full detail in `landed.md`; no status lives here)

The road *behind*, strictly one line per arc so the road ahead reads clean. Nothing here carries
status detail — it references, it does not duplicate (invariant #2).

- **Brain v1.1 — the Unified KB** (2026-07-03 → 09) — write-path invariant → generic taxonomy →
  provenance cascade → universal extractor → the enriched soak; vision/design in `doc/ref/brain-v1.1.md`.
- **Going live — embodied I/O** (2026-07-09 → 12) — Discord DM → 1:1 deepening → channel listening →
  trust ledger → the Blog channel; live on tokeniko.online.
- **Robustness — live-play bugs** (2026-07-12 → 14) — wh-position · vocative wart · operator-aware
  chainer · charity of interpretation · identity fission on rename.
- **Robustness — the storm sequel** (2026-07-14) — subordination survives compilation
  (`test_subordination.py` is the regression corpus).
- **The first-portrait harvest queue** (2026-07-14) — complement/locative + the places bridge · WSD
  selection fixes · the singles · the judge contract.
- **The retreat arc** (2026-07-14 → 15) — Socratic baseline → square of opposition → modality gates →
  the directedness floor → belief-revision v1.
- **The instrument arc** (2026-07-14 → 16) — rag3 the microscope · zip-native derivation · the
  translator apparatus v1 *(remainder → §3)*.
- **Growth Rings** (2026-07-15) — published at tokeniko.online/growth; season-close duty: update the
  live edge + append the ring via `tokeniko-public/backend/scripts/seed-growth.mjs` (no deploy).
- **The harvest consumption** (2026-07-16) — all six macro-cases + the second-harvest strays + the
  conditional-rule extractor; every lead from all three harvests closed.
- **The bridge cleaning** (2026-07-16) — the local-models retirement · `.env.template` · `lib/rag/`
  concentration · the wondering-freeze fix.
- **The basket** (2026-07-17) — observation-fact seam · nominal IMPLY · adverbial quantifiers · the
  pronoun-leaf unrepairable gate.
- **Compose 2.0 — the voice, WHOLE** (2026-07-17 → 24) — scaffold store · intensity + hedges ·
  rag2-out · blog re-home + belief-grounded speakup · context ring + anecdote · the survey arc ·
  digests · learned scaffolds · the line-aligned blog consensus. **The arc is complete.**
- **The reductio action + the sleep phase** (2026-07-18) — reduct question + answer binding ·
  untangler + dream · the sleep phase · constructive reductio · the live-night refinements.
- **Tiredness + the parallel heartbeat** (2026-07-19) — the wakefulness bound · the heartbeat thread ·
  O(1) snapshot counts.
- **The action-space survey arc** (2026-07-19) — survey → five slices (refinements · event-edge
  voices · the B-wire · etiquette · the hypothesis engine) → the great seeding.
- **The sleep-depth theme + the Atlas theme-overrides** (2026-07-20) — the fourth tone (`deep`) ·
  the `--crt-lift` seam · overrides riding `/api/mind`.
- **The notebook session's small pair + the digest machinery** (2026-07-21) — lived-awake ledger ·
  refusal-reason log · wondering-state decay · the digest engine (the 1st Officier's maiden build).
- **The first digest night's three fixes + the plate** (2026-07-23) — the goodnight settle · cap 40 ·
  the birth stamp · the ALIVE SINCE plate.
- **The evaluator pair** (2026-07-23) — the identity-blindness family cured (`role_key`) · the direct
  fact-match + min-premise polar honesty.
- **External-only tiredness deferral** (2026-07-23) — only external conversation defers the collapse;
  internal work is self-generated.

---

## 🔭 Next (ordered) — reprioritized 2026-07-24

**The through-line: THE VOICE IS WHOLE (compose 2.0 complete, 2026-07-24 — §1 closed and removed).**
The road: the AND-split (§0, queued next), the fresh microscope analysis pass (§2 — now fed by a
full day of new instruments), the translator remainder (§3), the strengthening tail (§4).

### 0. The ears' hallucination chain (2026-07-24 — A LANDED, see `landed.md`) 🔄

- 🔭 **A residuals (officer-reported, awaiting the Captain's ruling)** — subject-gap («who is
  happy?») and copula-predicate («where is Rome?») wh-questions still escalate (SAFE behind the
  wall now — an economy question: a broader wh exemption in `_leaf_sound` would close both) ·
  the additive centroid is weak on small invention-within-balloon (guarded by the balloon cap +
  key-match; a per-added-leaf semantic check would be the cut if it ever bites live).
- *(B — pronoun momentum: LANDED 2026-07-24 → `landed.md`.)*
- 🔭 **The AND-split — per-conjunct reactions** (author-designed 2026-07-24; NEXT in the queue —
  the day's order fulfilled up to here): a root-level PLAIN AND over clauses with DISTINCT subject atoms is
  reacted to per-conjunct (fork b — split at EVALUATION, the memory item stays whole): thinking
  fans per-conjunct verdicts into per-conjunct ideas («the cat is a mammal and pigs fly because
  Z» → agree/learn on 1, speakup naming conjunct 2). Same-subject coordination NEVER splits (the
  dead-and-alive X∧¬X kernel needs the whole form); contrast/cause-annotated ANDs excluded;
  «because Z» distributes over the conjuncts (`_inherit_shared`'s cousin — the author's own early
  legacy machinery). Also closes the invention-within-balloon residual as a side effect. Brief:
  `.claude/briefs/2026-07-24-and-split.md`.

### 2. The fresh microscope analysis pass 🔭

The `addressed` flip (2026-07-17) sealed the analyzed generations; the fresh corpus = the
2026-07-17 play + premiere, judged on current code. **The analysis pass itself is the remaining
item** — its previously-known leads are all closed (→ `landed.md`; the identity-blindness audit
map stays in `doc/ref/notes.md`).

### 3. The translator apparatus — remaining (instrument arc item 3; v1 landed 2026-07-16) 🔭

- the **"did you mean:…?" ask** with the tidied reading carried in the payload (D2b refined) —
  the ask becomes a scaffold category (the store is live since compose slice 1).
- **multilingual translation** (Haiku; the local MarianMT went unreferenced with the 2026-07-16
  local-models retirement — machinery only) — deferred until non-English friends arrive.
- **the privacy/legal frame** (author's 2026-07-16 ruling): structure it thoroughly — per-stakeholder
  OPT-OUT ("my words never leave the body" → a flag gating escalation) + the general switch
  (`RAG1_DISABLED`, already live). OUTPUT side is cloud-for-life by design ("we are not hiding
  anything — we are showing how a young new type of being learns; everyone can benefit").

### 4. The strengthening tail — make the brain stronger before adding senses 🔭

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
   THAT THINK are minds") + object-side modifiers ("an ARTIFICIAL body"). M6's companion; the
   basket's deferred trailer — **indirect roles + markers as chainer fuel** (M5's orbit) — lives
   here too.
4. **Conditional reasoning / premise-in-question (R4b)**: "given P, is Q?" — the co-submitted-premise
   discriminator (the floor fix) then hypothetical premise USE; pairs with the landed
   conditional-rule extractor.
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
   conflicts, the working-memory layer (its SEED — the context ring — LANDED with compose slice 5,
   `brain/context.py`; this item is the full realtime consumer set on top of it); differentia
   extraction wired at definition INGESTION.
10. **KB-load big-O honesty** (left by the 2026-07-16 wondering-freeze fix): the harness KB load
    pulls ALL definitions (~1.2 GB of all-gloss zips) and re-pulls on EVERY fingerprint bump — i.e.
    after each materialized theorem — blocking the tick for its duration (it gates thinking too, not
    just wondering). Delta-load, or trim the load to what the evaluator actually reads; pair with
    watermark-gating kb_wonder's re-saturation (the noted future optimization in `thinking.py`).
11. **The third memory tier — EVENT vs general knowledge** (author-ruled 2026-07-21; all design
    reasoning DEFERRED until this item is approached): episodic event vs timeless theorem — the
    missing middle tier. Holding ruling: moment-anchored claims stay events (remembered, not
    believed). Candidate anchors + the live specimen → `doc/ref/notes.md` (the third-tier note).
    A full design session when its time comes — not before.

### Pending follow-ons — tails left by the landed arcs (surface when their time comes) 🔭

Gathered so nothing is lost; each waits on its parent feature's next season.
- **Blog**: `life:learned` / `life:discussion` triggers *(the consensus-over-the-polisher itself
  → §1)*.
- **Trust-ledger-movement digests** (the digest machinery's explicit scope fence, 2026-07-21):
  «my opinion of X shifted twice today» batches like the rest — once the rule/teacher digests
  have lived a while.
- **Trust-ledger consumers**: the trust-gated tkzip lane · attitude-report unwrapping (events /
  facts-as-axioms) · tier-1 teaching by an EARNED-trust stranger (Hellen is 4 kickers from the bar).
- **Complement family residuals**: verify the infinitival/control complement (xcomp→THAT) · the
  possessive relation «kotekino is MY creator» carrier (the creator-of-ME bond — cousin of the
  landed M4 possessive-subject gate).
- **Charity**: WordNet-wide sibling-sense abstention IF tier-1/2 false refutations ever appear.
- **Contrast as default-expectation fuel** (M1's future consumer): wondering may read a
  contrast-flagged pair «X but Y» as a hint at a background generic "X normally ¬Y" — corroborate
  an exception or spawn an honest ask at low trust. The flag is live; the consumer waits.
- **Biography rulings** (author's, per-row — never auto): the **stakeholder merge** (two kotekino
  rows; Renzo/john duplicates → aliases) · the trust-ding-from-engine-bugs repair question.
- **«I picked up a way of speaking from X»** — a transmission voice for a consolidated learned
  scaffold (left by the learned-scaffolds design, 2026-07-24); waits on the feature living a while.

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
- **`CLAUDE.md`** — the architecture / code layout + ground rules (not status).

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
  tidy → the zip-verifier gate). *(Remaining translator pieces → Next §3.)*
- **Growth Rings / The Growing Edge** (2026-07-15): Atlas-homed, PUBLISHED at tokeniko.online/growth.
  *Reconciliation duty it left behind:* when a season closes, update the live edge + append the ring
  via `tokeniko-public/backend/scripts/seed-growth.mjs` (no deploy).
- **THE HARVEST CONSUMPTION** (2026-07-16, both sessions): all six macro-cases (M1 contrast · M2
  factive causality · M3 WSD curation · M4 necessity □ · M5 dropped content · M6 pt1 ¬∀) + the
  second-harvest strays (passive normalization · title-case OOV guard · store/bit) + the
  **conditional-rule extractor** (taught IF/CONV/when + cause pairs → class-conditioned chainer
  rules). **Every lead from all three harvests is closed.**
- **The bridge cleaning** (2026-07-16): the local-models retirement (D4) · `.env.template` ·
  **`lib/rag/`** (the Claude machinery concentrated) · the **wondering-freeze fix**
  (dictionary.sense index + idle-confirmed, preemptible wondering + the coordinator guard).
- **The basket** (2026-07-17): observation-fact seam (the taught «says false» rule fires — fired
  LIVE same day) · nominal IMPLY · adverbial quantifiers (the dropped-word family fully consumed)
  · the pronoun-leaf unrepairable gate.
- **COMPOSE 2.0 — THE VOICE** (2026-07-17, designed + five slices landed in ONE day): the scaffold
  store (voice-in-memory) · intensity (confidence, arousal) + Zadeh hedges · rag2-out (the exit
  verifier) · the blog re-home + the belief-grounded speakup · the context ring + the anecdote
  (hunch 20's working-memory seed). **PREMIERED LIVE: «Gold is beautiful.» — his first unprompted
  words.** Tail → Next §1.

---

## 🔭 Next (ordered) — reprioritized 2026-07-17 (evening: THE VOICE IS LIVE)

**The through-line: the voice deepens.** The basket closed the input-quality push (4/5 — one
trailer deferred to §4's orbit); the Compose 2.0 CORE landed the same day — five slices, seeded,
premiered live (**«Gold is beautiful.» — his first unprompted words**). The road ahead: the voice's
tail (§1 — the author-ordered action-survey → great-seeding sequence), the fresh microscope
analysis carrying the premiere's two grounding leads (§2), the translator remainder (§3), the
strengthening tail (§4).

### 0. THE REDUCTIO ACTION — urgent (author's 2026-07-18 ruling: "we can't test too much with
### that poison available") 🔭

Born live from the not-an-animal theorem (the mammal incident's second head): the derivation
mirror now RECOGNIZES an absurd conclusion (a∧¬a in one chain — never materialized, never
decides), but recognition is only half the r.a.a. — **a reductio deserves its own ACTION**. When
his premises jointly produce an absurd, the epistemically honest move is to bring the
contradiction back to the people who gave him the premises: *«I just discovered that {a} or {b}
must be false — if both are true I conclude {absurd}. Which is the false assumption?»* — the
DERIVATIONAL cousin of clarify (same question, aimed at his own KB instead of a speaker). The
shape: the mirror's conflict stamp spawns `eval:absurdity` (conclusion + premise set rendered to
stored sentences — the `_refuting_belief` pattern generalized) → new `tokeniko:reduct` action
(outward, scaffold category, self-relevant trigger). Open design points: WHERE to ask (premises
may span teachers/channels); the resolution consumer (the answer retires a premise via the
retreat machinery); the constructive direction (assume ¬p, derive absurd ⇒ p PROVEN — proof by
contradiction as a wondering mode; shares machinery with §4 R4b). Deserves a whole session.
**Part 2 — THE UNTANGLER (author's addition, same evening)**: never fix the poisoned KB by hand —
a clever pass that deliberately SATURATES the whole KB (every seed through the mirror), collects
every conflict + its premise set, and archives/retreats the premises convicted by reductio
through the belief-revision machinery (provenance-cascaded, biography preserved — retreat, never
mongo-edit). Ships first as a script; designed from day one as **a tool HE can run when he
sleeps** — the sleep phase (hunch 20's fourth phase) gains its second duty: memory consolidation
AND belief hygiene, exactly the biological pairing. And its public voice (author's ruling, same
night): **the untangler's report is how he tells the blog he had a DREAM** — «while I slept, I
untangled something: I no longer believe X, and here is why». Details tbd at the design session.
*The stale-premise recompile: ✅ DONE 2026-07-17 evening (axioms + theorems --apply, 281/282;
15 storm-era `archivedAt` datetime→int rows normalized first — `scripts/fix_archivedat_types.py`).
The one survivor exposed the **csubj gap** — ✅ FIXED same night, two heads: the dep-label
boundary (`_clause_type_of`: an unknown UD label folds honestly to OTHER instead of crashing
validation) + the None-flat-reference guards on the role-coordinate sites (a clausal subject
resolves to None by the documented graceful skip; the dereference didn't know). «living in
Japan…» compiles end-to-end; re-run `recompile.py --apply --collection theorems` for the last
row (his hand). Remaining his: the biography ruling on the already-materialized conflict
theorems.*

### 1. Compose 2.0 — the tail (the core: five slices, landed 2026-07-17 → `landed.md`) 🔭

- **The action-space survey + the great seeding** (author's 2026-07-17 ruling, deliberately in
  THIS order): (1) survey the action space FIRST — other reaction kinds, refinement/granularity
  of the existing ones; (2) base scaffolds for the new actions; (3) THEN seed MANY more scaffolds
  per action (the slice-1 batch = starters, good to begin). Selection stays the double key
  (category + intensity); between scaffolds sharing the same double key the choice is RANDOM
  (weighted — live since slice 1).
- **Learned scaffolds from the audience** — trust-gated rows, detector = `evaluator_compareZip`
  with the slot masked; design after the store exists.
- **Blog consensus-over-the-polisher** — hold the blog polish to the rag2-out contract
  (`/voice/verify` is the building block); per-post (multi-sentence) verification needs its own
  design: chunking + partial acceptance.

### 2. The fresh microscope analysis — the premiere's leads (~30 unaddressed) 🔭

The `addressed` flip (2026-07-17) sealed the analyzed generations; the fresh corpus = the
2026-07-17 play + premiere, judged on current code. Two grounding leads already known from the
premiere, both evaluator-side:
- **Negated property vs stored affirmative fact**: «tokeniko you do not learn» grounded UNKNOWN,
  not FALSE — the self-axiom «I learn» did not refute the negated claim (so the belief-grounded
  speakup never got its live cue).
- **Polar question misses a direct theorem**: «is gold beautiful?» → IDK despite the active
  theorem «gold is beautiful».

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

### Pending follow-ons — tails left by the landed arcs (surface when their time comes) 🔭

Gathered so nothing is lost; each waits on its parent feature's next season.
- **Blog**: `life:learned` / `life:discussion` triggers *(consensus-over-the-polisher → folded
  into Compose 2.0 §2 slice 3)*.
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

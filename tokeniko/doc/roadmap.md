# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress — Brain v1.1: the Unified KB (the CENTER — nothing matters more)

The definitions-as-rules arc + the BPMN process maps are **done** (see `landed.md`). The author's live
**curated-fuel test** validated the machinery AND matured into a single reframe — *the conceptual center
of the brain.* **Vision + design: `doc/ref/brain-v1.1.md`.** In one line: *everything compilable to a
`TKZip` is reasoned over; collections denote what content REPRESENTS (enforced by write-path), trust
tiers by source, one universal gate extracts usable logic + suppresses noise, provenance makes every
theorem auditable + every dependency revocable, logic stays hardwired.* The ordered build:

1. ✅ **Write-path invariant** + 2. ✅ **Generic taxonomy chains (universal-extractor v0)** — landed
   2026-07-03; imprint rebatched on the new pipeline (first derived theorem: «I do not reach truth»,
   the author's agnosticism DERIVED). See `landed.md`.
2b. ✅ **Known-individual recognition (finding #6)** — landed 2026-07-03 (`parser_getKnownIndividual`:
   recognition before the minting gate; the kotekino axioms entity-link) — see `landed.md`.
2c. ✅ **Restricted universal → CONDITIONED rule (finding #5)** — landed 2026-07-03 (modifier senses
   carried on subject+predicate roles; `cond_props` rules; `klass_mods` facts; the chainer's
   seed-level condition test — "a machine seeks cognition" dead, tokeniko's proofs cite their
   condition satisfier) — see `landed.md`. **REBATCH the imprint** (author's terminal) to recompile
   the stored zips with the modifier carriers. Residuals → `parked.md` (relative-clause restriction,
   object-side modifiers). The conjunctive machinery doubles as step 4's sufficiency groundwork.
2d. ✅ **Generic-strength → lower trust (a generic is NOT a universal)** — landed 2026-07-03 (rule
   `strength`, generic-derived conclusions 0.7 via the trust map, chains read "most X …";
   «kotekino creates god» honestly defeasible) — see `landed.md`. REBATCH not required (rules are
   re-extracted per KB load) but the author retests after it anyway.
3. ✅ **Provenance + transitive cascade + theorem fuel** — landed 2026-07-03 (`revoke_dependents`
   recursive cascade wired into axiom/theorem archive+delete + `revoke_edge.py`; active theorems feed
   the chainer with generational min-trust — theorems breed theorems) — see `landed.md`.
4. ✅ **The universal extractor + definitional SUFFICIENCY (the core build)** — landed 2026-07-08
   (`kb_extract.extract_logic` one front door folding all five extraction paths, trust by source;
   `extract_sufficient_rules` DNF + drop-disjuncts-never-conjuncts gate → 113 recognition rules;
   the chainer fires kind="sufficient" in the membership fixpoint, object-strict) — see `landed.md`.
   Residuals → `parked.md` (derived-props as cond satisfiers; adjective-definienda fuel).
5. 🔄 **Reason over everything** — 5.1 ✅ **definition subject-WSD pin + full tier rebuild** + 5.2 ✅
   **runtime graph subject-untangle** landed 2026-07-09 (gloss-inversion ground truth: 189
   mis-senses → 0; all THREE tiers live+clean: 627 genus edges, 116 sufficient, 90 differentia
   @0.3 — definitions fully rejoined chaining; `compiler_untangleSubject` guards runtime axiom
   subjects at compile time) — see `landed.md`. Remaining: the **enriched soak** over the
   three-tier fuel (validate what the wondering derives).

*(Deepest pole, parked → `parked.md`: **predicate-complement capture** — prepositional/control complements
dropped, "run in a hardware" → "run" — and complex-definition parser fidelity. Workarounds exist.)*

## 🔭 Next (ordered)

### Going live — embodied I/O (core TK v1)

The autonomous loop is closed in **dry-run**; these wire the real `senses` I/O so tokeniko actually
perceives and speaks. Each carries an **open design question** to brainstorm before building.
*(ATProto/Bluesky is the third channel — parked behind these; see `parked.md`.)*

- **Discord INBOUND listener.** Connect the live `DiscordClient`; monitor (a) DMs to the bot and
  (b) channels in tokeniko's playground → route each input to `memory` (correct stakeholder as author,
  `channel=discord`). Then flip `SENSES_DELIVER_DRYRUN=0` + wire the live `sender` to close the
  round-trip. **OPEN Q — overheard vs directed:** a channel message is *visible* to tokeniko but not
  necessarily *addressed* to him. How to represent + weigh it? (targetId=tokeniko only when
  @-mentioned/replied-to? an "ambient/overheard" notion the brain weighs differently?) — needs an idea.
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

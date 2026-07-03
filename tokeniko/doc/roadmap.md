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
3. 🔭 **Provenance + transitive cascade** — extend provenance to record **theorem** premises; revocation
   recurses (archive a premise → its dependent theorems → theirs). The precondition for *theorems
   breeding theorems* + clean revocation.
4. 🔭 **The universal extractor (the antidote — the core build)** — ONE source-agnostic
   `TKZip → usable logic` extractor + gate, folding the per-collection paths (axiom rules/facts,
   definition edges/differentia) into one, trust-tiered by source. Adds **definitional SUFFICIENCY**
   (the sufficient direction — "has merit → valuable"; operator-tree-aware; the generative unlock that
   sidesteps the is_a-amplification trap). Dry-run heavy.
5. 🔭 **Reason over everything** — definitions rejoin chaining via the universal extractor (low-trust,
   gated) → the rich soak done right. Includes **subject-WSD hardening** (the noise antidote that makes
   definitions safe to chain — the chat-zombie root).

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

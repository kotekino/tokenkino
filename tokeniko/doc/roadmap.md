# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress — Definitions-as-rules (the rich-soak fuel)

The ~3,235 **definitions** are *grounding-only* today — the chainer reasons over only ~17 items
(7 rules + 10 facts) and never sees the vocabulary. This arc makes the definitions FUEL wondering, so
tokeniko reasons across his whole KB (the "rich soak"). Built **untangle-first**
([[everything-is-kb-untangle-first]]) — clean the senses before mining them — each step
**dry-run-verified before it lands**. Governing principle: **asymmetric risk → reject-on-doubt** (a
false is_a edge poisons ALL downstream reasoning).

- ✅ **Steps 1–2 (genus untangle + recompile) and the step-3 dry-run probe — done; see `landed.md`.**
- 🔄 **Step 3 build — the definition→is_a extractor + low-trust tier.** Mine the 650 clean edges into a
  **revocable, low-trust tier** (a source/trust-tagged relation record, SEPARATE from the 150k bedrock
  WordNet graph — never pollute it); the relations-reader **unions** bedrock ∪ tier; provenance so any
  edge + every theorem resting on it is retractable. *This is what finally lets definitions fuel the
  chainer.* Gate (validated in the probe): redundancy-drop + reliable-tier disjointness + structural
  placeholder filter + cycle.
- 🔭 **Step 4 — the wondering NET** (the residual meaning-level safety net). Structural (main-clause
  genus only, no circular nominalization "management→manage"), graph-consistency hard-reject
  (disjoint/cycle), trust-tiering, provenance-revocability (retract an edge + every theorem on it),
  flag-the-middle. *(Geometry dropped — the wrong signal for is_a validity, [[geometry-not-isa-validity]].)*
- 🔭 **Step 5 — the enriched soak** (the real knowledge explosion). **Grow the universal-rule set** —
  yield scales ~ *edges × rules*, and the GENERATIVE fuel is **property** content ("apple has red skin")
  meeting rules at ≥2 premises, not the ~redundant taxonomic content. Re-run `probe_definitions.py`
  before/after; the rich cascade the whole arc has built toward. These are **analytic** truths (the
  vocabulary's deductive closure — the analytic half of `doc/ref/kb-growing-outward.md`). Caveats: perf
  (async materialize throughput at scale) and gloss-quality noise (logic-floor + ≥2-premise gate +
  `soak_report.py` integrity checks keep truth safe).

## 🔭 Next (ordered) — going live (embodied I/O)

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
  significance? a periodic reflection digest?) — needs an idea on the urge model.

---

## Doc map

**Status docs (`doc/` — the single source of truth for status; the STRICT invariants in `CLAUDE.md`):**
- **`doc/roadmap.md`** — *(this)* the road ahead: in-progress + ordered next. Nothing landed, nothing parked.
- **`doc/landed.md`** — what's done (the history).
- **`doc/parked.md`** — the icebox (deferred ideas + known gaps).

**Reference docs (`doc/ref/` — extended context per task + future-reference material; NOT status):**
- **`doc/ref/notes.md`** — design notes & findings (phased plan + reasoning-engine brainstorm + parser/compiler review).
- **`doc/ref/test-feedback.md`** — the living empirical fragility log (observed → diagnosis → action).
- **`doc/ref/kb-growing-outward.md`** — the "synthetic learning" design (analytic/synthetic cut).
- **`doc/ref/paper_outline.md`** — the paper (external artifact).

**Root:**
- **`VISION.md`** — the why (north star).
- **`brain/README.md`** — the brain's orchestration + meta-language spec.
- **`CLAUDE.md`** — architecture / code layout + ground rules (not status).

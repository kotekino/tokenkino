# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress — the CURATED-FUEL soak (the digital twin's first breath)

The **definitions-as-rules arc (steps 1–5) is complete** — see `landed.md`. Definitions fuel GROUNDING
(the 582-edge tier) and the enriched-soak MACHINERY is built + proven + safe (differentia → low-trust
property rules → cascade, held at trust 0.3 + revocable). The step-5 dry-run's **key finding**: a
cascade over WordNet-wide is_a *amplifies* the graph's errors (a good rule + a bad edge = a
confident-wrong theorem), so the noisy WordNet auto-rules are **not** bulk-applied — quality comes from
**curated fuel**, the digital-twin direction ([[tokeniko-vision]]).

- 🔄 **The curated-fuel soak (the author's test).** Launch the brain on a **cleaned memory** → watch it
  self-derive from the seed KB (the cogito and kin) → then **inject curated fuel** (kotekino's
  first-person personality axioms + selected clean definitions) via `scripts/ingest.py` → watch a
  *clean* cascade + the net holding. This is where the machinery shines (clean fuel over a clean local
  taxonomy = no errors to amplify) and where tokeniko starts to *take shape* as the twin. Driven by the
  author; the engine is ready.

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

### 🔭 Consolidation checkpoint — process maps (AFTER the enriched soak)

- **BPMN-style process maps (Mermaid).** Isolate + diagram every information journey across the
  components — the API compilation pipeline, the brain coordinator + phases + wondering/materialize
  seam, senses inbound/outbound, the DB tiers, the evaluator/chainer — as **swim-lane** diagrams
  (stakeholders as lanes: users / brain / evaluator / DB / senses / …; start + end; cross-lane messages;
  forks). Mermaid (subgraph lanes + sequence diagrams for cross-lane messages), self-contained HTML
  visualizer(s), homed in **`doc/ref/processes/`**. Deliberately a **post-soak beat** — the system is
  then both stable and freshly-observed — and it carries **forward "as-will-be" projections** (senses
  going-live) as *projectual* reference, to force forward-consistency. NOT strict BPMN2 XML
  (over-formal + token-draining for an internal map).

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

# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next* — the REAL pipeline, nothing else. **History
> → `landed.md`** · **icebox → `parked.md`** · **design detail → `doc/ref/notes.md`**. The **why** is
> `VISION.md`; the **how** lives in `CLAUDE.md`, `brain/README.md`, `doc/ref/notes.md`, and the code. When
> status and any other doc disagree, **this file (+ `landed.md`) wins** — check/update it after **every
> commit**. Keep entries **terse** (one line of what + the key term/file).

Legend: 🔄 in progress · 🔭 next · ✅ done  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress — BPMN-style process maps (the consolidation checkpoint)

The **definitions-as-rules arc (steps 1–5) is complete** — see `landed.md`. The author's live
**curated-fuel test** validated the machinery AND surfaced the next round of refinements (→ **Brain
v1.1**, below). We deliberately pause building to draw the system's process maps first — the checkpoint
we agreed to run *after* the enriched-soak machinery landed, now active. It keeps the direction crystal:
each Brain-v1.1 fix will show exactly which lane it lives in.

- 🔄 **BPMN-style process maps (Mermaid).** Isolate + diagram every information journey across the
  components — the API compilation pipeline, the brain coordinator + phases + wondering/materialize seam,
  senses inbound/outbound, the DB tiers, the evaluator/chainer, the definitions-as-rules ingestion — as
  **swim-lane** diagrams (stakeholders as lanes: users / brain / evaluator / DB / senses / …; start +
  end; cross-lane messages; forks). Mermaid (subgraph lanes + sequence diagrams for cross-lane
  messages), self-contained HTML visualizer, homed in **`doc/ref/processes/`**. Carries forward
  **"as-will-be" projections** (senses going-live) as *projectual* reference, to force
  forward-consistency. NOT strict BPMN2 XML (over-formal + token-draining for an internal map).

## 🔭 Next (ordered)

- **Brain v1.1 — grounding/chaining refinements → `doc/ref/brain-v1.1.md`.** The gaps the curated-fuel
  test surfaced (detail + brainstorming in the ref doc): **#1** generic "a X is a Y" taxonomy must chain
  (extract is_a from copular axioms, high-trust tier — the natural-taxonomy gap); **#3** definitional
  *sufficiency* (the sufficient direction of a definition — "has merit → valuable"; the generative unlock
  that sidesteps the is_a-amplification trap); **#4** revocation durability + subject-WSD (the
  chat-zombie). **#2** predicate-complement capture is parked (parser-level; workaround exists). Priority
  when it resumes: #1 → #3 → #4.

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
- **`doc/ref/brain-v1.1.md`** — the Brain v1.1 backlog + brainstorming (grounding/chaining refinements from the curated-fuel test).
- **`doc/ref/notes.md`** — design notes & findings (phased plan + reasoning-engine brainstorm + parser/compiler review).
- **`doc/ref/test-feedback.md`** — the living empirical fragility log (observed → diagnosis → action).
- **`doc/ref/kb-growing-outward.md`** — the "synthetic learning" design (analytic/synthetic cut).
- **`doc/ref/paper_outline.md`** — the paper (external artifact).

**Root:**
- **`VISION.md`** — the why (north star).
- **`brain/README.md`** — the brain's orchestration + meta-language spec.
- **`CLAUDE.md`** — architecture / code layout + ground rules (not status).

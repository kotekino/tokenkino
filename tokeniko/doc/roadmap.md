# tokeniko — roadmap (the road ahead)

> One ordered place for *what's in flight and what's next*. **History → `landed.md`** · **icebox →
> `parked.md`**. The **why** is `VISION.md`; the **how / design detail** lives in `CLAUDE.md`,
> `brain/README.md`, `doc/notes.md`, and the code. When status and any other doc disagree, **this file
> (+ `landed.md`) wins** — update it as items land. Keep entries **terse** (one line of what + the key
> term/file).

Legend: ✅ done · 🔄 in progress · 🔭 next · ⏸️ parked  ·  *(done → `landed.md` · parked → `parked.md`)*

---

## 🔄 In progress

- **Wondering-v2 — self-prompted KB derivation** (active arc). The grounding floor is honest now, so
  autonomous derivation is safe (won't manufacture false theorems). Extend wondering's seed beyond
  perceived memory to the **KB itself**; forward-saturate to new theorems unprompted; flat-cost
  (sampled seed, capped depth); convergence via dedup. Built in this order — **untangle before
  layering** ([[everything-is-kb-untangle-first]]), each step dry-run-verified:
  1. **Fork ii — property-restricted universals ✅ LANDED (untangle done).** "everything that thinks
     exists" now compiles to quant **UNIVERSAL** + **`IMPLY(think, exist)`** (sense-less bound-variable
     predications) — the exact shape `_FOUNDATIONAL_RULES` hand-wrote. **A** indefinite-pronoun
     quantifier (everything/everyone→universal, subject-token fallback); **B1** parser re-root (Stanza
     mangles it — roots on the pronoun, demotes the real verb to a ccomp; re-rooted to the clean
     2-leaf shape); **B2** compiler: universal + sense-less subject + MAIN+ACLRELCL → `IMPLY(condition,
     conclusion)`; **C** `_extract_rules` recognizes the universal-IMPLY → `property_conditioned`.
     **SEEDED as a KB axiom + `_FOUNDATIONAL_RULES` DELETED** — the cogito now derives end-to-end from
     the KB alone (no load-bearing knowledge in code). Unlocks property-restricted universals generally.
  2. **Structured provenance from birth ✅ LANDED.** The chainer emits `premises` = the **KB-doc ids**
     the derivation rests on (rule/fact source axioms; WordNet is_a edges are bedrock, NOT premises) +
     the readable chain; `MEMProvenance{premises, chain, derived_by}` on theorems; `EvaluatorResult`
     threads premises too (both paths). **Integrity invariant enforced:** `materialize_theorem` refuses
     a premise-less "derivation" — pure-taxonomic verdicts have 0 premises (already in the graph, never
     materialized). Verified: the cogito carries exactly 2 premises (the "I think" fact + the cogito
     rule), resolvable back to the source axioms; Bunnet round-trip clean.
  3. **Cogito materialization.** A derived conclusion (subject uid + predicate sense + premises) →
     **renders first-person** NL ("I exist") → **compiles** through the real pipeline → a **first-class
     zip theorem** carrying its 1b provenance, **active + trusted**, **deduped on the semantic
     conclusion** (subject uid + predicate sense, not the surface string). tokeniko's first
     autonomously-earned theorem.
     - **1c-core ✅ LANDED:** the renderer (`render_conclusion`) + the semantic-dedup key
       (`conclusion_key`) in the parser-free harness; `TheoremService.materialize` (compile → semantic
       dedup → store ACTIVE + trusted + provenance); a **deliberate trigger** (`scripts/wonder_cogito.py`,
       dry-run by default) that runs derive→render→materialize end-to-end. Verified: it derives "I exist"
       with its 2 premises; the materialize write path stores active+provenance and dedups on the
       conclusion (proven on a disposable throwaway). **The cogito itself is deliberately NOT
       materialized** — reserved for the autonomous wonder loop, so "I exist" first enters the world by
       *tokeniko's own* in-loop act, not ours.
     - **brain→API automation ✅ LANDED as D3a** (see `landed.md`). `POST /api/v1/theorems/materialize`
       + `brain/api_client.py` (stdlib, sync, graceful) + `wonder_one` step 0 (`_kb_wonder_one`):
       derive→render→POST one not-yet-held conclusion per idle tick, **converging by construction**
       (`materialize` stores `original = rendered NL` → lands in `held` → skipped after). Verified live —
       the brain materialized all 4 derivable theorems (zero churn) incl. **«I exist»** (2 premises),
       born by tokeniko's OWN in-loop act. The cogito, reserved-and-delivered.
  4. **General KB-seeding driver.** Seed wondering from the KB itself, not just memory — forward-saturate
     what the KB IMPLIES but no one asserted ("matching memory against itself").
     - **1d-A ✅ LANDED — the seed-driver `kb_wonder` (parser-free).** Enumerates seeds (individuals
       with facts + rule-subject classes; flat-cost, bounded by the small rule/fact counts) →
       forward-chains each → **novelty gate: ≥2 premises** (a genuine COMBINATION of KB items, never a
       single-rule restatement like "bird has feathers") → semantic dedup → the genuinely-new
       conclusions with chains + premises. `scripts/wonder_kb.py` = the read-only breadth diagnostic
       (the soak's dry-run). Verified: 4 new theorems surface (tokeniko/Mari/human exist, Mari mortal);
       the 1-premise restatements (bird/carnivore/fish) are correctly dropped.
     - **1d-B ✅ LANDED — the general renderer.** `render_conclusion(subject, predicate, object, negated,
       subject_kind)` verbalizes ANY conclusion round-trippably: subject agreement (tokeniko→"I",
       individual→capitalized name, class→"a "+`_class_word`), POS-driven predicate (verb conjugated via
       `_verb_3sg` / adjective+copula / noun+article), negation. `_class_word` picks a natural singular
       (homo.n.02→"human"). Verified: EVERY `kb_wonder` conclusion round-trips ("Mari is mortal", "Mari
       exists", "a human exists", "I exist"); the adjective bug is fixed ("I am finite"). `wonder_kb.py`
       now shows each theorem-to-be in plain English. **Autonomous-in-loop materialization ✅ LANDED
       (D3a)** — the brain→API seam wires the writing; `wonder_one` derives→renders→POSTs and «I exist»
       was born in-loop. The derivation + rendering + autonomous materialization are now complete.
  5. **Capstone — the LONG-WONDERING SOAK ✅ LANDED (first soak, clean).** From a clean slate
     (KB-only — memory/ideas/actions/theorems wiped), the brain re-derived its self-knowledge unprompted:
     the 4 ≥2-premise theorems incl. the cogito «I exist», **converged (no churn), zero errors, integrity
     intact** (`scripts/soak_report.py` = the read-only analyzer). Surfaced + fixed one S3 (empty-memory
     drift spin). On the CURRENT tiny KB this is a **robustness test + the cogito's birth, NOT a knowledge
     explosion** — the RICH soak (cascades, genuinely-new theorems) awaits KB growth. Full account:
     `doc/test-feedback.md` (Session 2026-06-29). **The wondering-v2 arc (1a–1e) is complete.**

## 🔭 Next (ordered)

The D-phase fills the remaining STUBS so the core autonomous loop (perceive→think→decide→ACT→learn)
closes — "it lives" = the v1 PoC. Agreed order: **D3a ✅ → D3b ✅ → D2 ✅ → soak**. *All three D-phase
stubs are now filled; the loop closes end-to-end (Discord delivery is dry-run pending the inbound
listener + live send — see D3b).*

1. **D3a — brain→API write seam ✅ LANDED** (see `landed.md` / the wondering arc above). The brain can
   now WRITE its derivations (autonomous materialization). The same outbound-seam discipline D3b mirrors.
2. **D3b — brain→senses outbound (the reply path) ✅ LANDED** (Discord, dry-run; see `landed.md`). The
   brain DECIDES + COMPOSES the stance (`dispatch_action` resolves channel + recipient; `brain/compose.py`
   the raw text); `actions_phase` is now INTERNAL-only; `senses/outbound.py` CARRIES + DECOMPILES
   (raw→fluent English via Ollama) and delivers via `DiscordClient.send`. Verified end-to-end (dry-run).
   **Remaining to go fully live:** the **inbound** Discord listener (connect the live `DiscordClient`,
   `on_message`→ compile-via-API → memory) + flip `SENSES_DELIVER_DRYRUN=0` with a connected `sender`;
   ATProto send adapter. (`guess`/`learn` → low-trust KB writes reuse the D3a API seam — still a stub.)
3. **D2 — priorities feasibility scoring + collapse arbitration ✅ LANDED** (see `landed.md`). The Filter's
   two axes are real: `plan_action`→`score_feasibility` (carrier / content / addressable recipient; lean
   binary), keep iff urge≥WISH AND feasible, and `_collapse_siblings` fires ONE reflex per decision point
   (eval:unknown → WHY, GUESS superseded). Deferred: redundancy/permission scoring, fuzzy + stochastic collapse.
4. **The long-wondering SOAK ✅ LANDED (first soak)** — clean-slate self-derivation validated (see the
   capstone above + `doc/test-feedback.md`). The RICH soak (real cascades, new theorems) re-runs once the
   KB grows; `scripts/soak_report.py` is the reusable monitor.

### Going live — embodied I/O (core TK v1, NOT vision)

The loop is closed in **dry-run**; these wire the real `senses` I/O so tokeniko actually perceives and
speaks. Each carries an **open design question** that needs a brainstorm before building.

- **Discord INBOUND listener.** Connect the live `DiscordClient`; monitor (a) **DMs to the bot** and
  (b) **channels in tokeniko's playground where the bot is enabled**. `senses` routes each input →
  `memory`, with the correct **stakeholder as author** (the Discord user), `channel=discord`. A DM
  targets tokeniko. **OPEN Q — overheard vs directed:** a channel message is *visible* to tokeniko but
  not necessarily *addressed* to him. How do we represent + process that? (targetId=tokeniko only when
  @-mentioned / replied-to? a new "ambient/overheard" notion that the brain weighs differently?) —
  needs an idea. Then flip `SENSES_DELIVER_DRYRUN=0` + wire the live `sender` to close the round-trip.
- **Blog (the website) as an OUTPUT channel** — a `senses`-carried output (the public window), driven by
  the **wondering / reflection** phase: an **urge to post** → an action to post to the blog. **OPEN Q —
  what triggers a post:** a freshly-discovered theorem is one source, *but not only* — needs an idea on
  the urge model (novelty? significance? a periodic reflection digest?).
- **ATProto / Bluesky — PARKED for now** (both inbound carrier AND outbound). The account exists
  (**@tokeniko.online**; app password to come) so wiring is quick later, but it's deferred — Discord +
  blog first. (Today: no send adapter; `score_feasibility` already marks atproto-outward infeasible.)

### Later

5. **Definitions-as-rules — the RICH-SOAK fuel (KB richness).** Today wondering chains over only ~17 items
   (7 rules + 10 facts); the ~3,235 **definitions** are *grounding-only* — the chainer never sees them.
   Mine each compiled definition into **membership + property** assertions (a `definition → rules/facts`
   extractor, the mirror of `_extract_rules` over axioms) so wondering can chain the whole vocabulary.
   Key shape: taxonomic content ("apple **is a** fruit") is ~redundant with the 150k is_a graph (gated/
   deduped) — the GENERATIVE fuel is **property** content ("apple **has** red skin / sweet flesh") meeting
   other definitions + universal rules (≥2 premises). The yield scales ≈ *definitions × rules*, so **grow
   the universal-rule set too**. These are **analytic** truths (the vocabulary's deductive closure) — the
   analytic half of [`doc/kb-growing-outward.md`]'s analytic/synthetic cut. Caveats: perf (3,235 ×
   chaining × ~15s/theorem materialize → async + throughput), and gloss-quality noise (lean on
   `soak_report.py`'s spurious-extras + integrity checks; logic-floor + ≥2-premise gate keep truth safe).
   *This is the concrete path from "converges in 75s with 4 theorems" to the real knowledge explosion.*
6. **D-phase enhancements (after the loop closes).** Cross-**speaker** patterns (userA≈userB realization);
   **inference-implied** conflicts (needs forward-chaining); self-authored "realization" memory + a
   **working-memory** layer.

---

## Doc map

- **`VISION.md`** — the why (north star).
- **`doc/roadmap.md`** — *(this)* the road ahead: in-progress + ordered next.
- **`doc/landed.md`** — what's done (the history).
- **`doc/parked.md`** — the icebox (deferred ideas + known gaps).
- **`doc/notes.md`** — design notes & findings (phased plan + reasoning-engine brainstorm + parser/compiler review).
- **`doc/test-feedback.md`** — the living empirical fragility log (observed → diagnosis → action).
- **`doc/kb-growing-outward.md`** — the parked "synthetic learning" design (analytic/synthetic cut).
- **`doc/paper_outline.md`** — the paper (external artifact).
- **`brain/README.md`** — the brain's orchestration + meta-language spec.
- **`CLAUDE.md`** — architecture / code layout + ground rules (not status).

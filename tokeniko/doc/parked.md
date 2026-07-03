# tokeniko — parked (the icebox)

> Deliberately deferred — good ideas and known gaps that are **not** the current focus. Moved out of
> `roadmap.md` so the road ahead stays clean. Promote an item back to `roadmap.md` Next when its time
> comes. The active road is `roadmap.md`; history is `landed.md`.

---

**ATProto / Bluesky — a `senses` I/O channel (inbound carrier AND outbound)** — the account exists
(**@tokeniko.online**; app password to come) so wiring is quick later, but deferred behind Discord +
blog (the going-live `roadmap.md` Next). Today: no send adapter; `score_feasibility` already marks
atproto-outward infeasible. Promote when Discord + blog are live.

**D-phase enhancements (after the embodied loop is live)** — cross-**speaker** patterns (userA≈userB
realization); **inference-implied** conflicts (needs forward-chaining, not just literal contradiction);
self-authored "realization" memory + a **working-memory** layer.

**Wondering-net structural polish (definitions-as-rules, step-4 residual)** — the ingestion extractor
gate is already conservative (main-clause genus only + redundancy/placeholder/cycle/reliable-tier
disjointness), so these were deferred: reject **circular nominalization** genera ("management→manage"),
and **flag-the-middle** (surface borderline extracted edges for review rather than silently accept).
Promote only if the enriched soak shows them biting.

**Ingestion-time differentia extraction (definitions-as-rules, step-5 follow-on)** — today
`extract_differentia.py` is a BATCH tool over all definitions. To make the author's live-injected
curated definitions cascade automatically, wire the same gated extraction at INGESTION (a definition
create → its clean differentia rule appears in `derived_rules`, scoped to that one def), mirroring how
the genus untangle runs at compile time (write-gated to storing paths, never `/evaluate`). Then feeding
a definition via `ingest.py` makes it wondering-fuel with no manual re-run. (Batch stays for bulk;
NOT auto-run on the noisy WordNet 3,235 — decision A.)

**Predicate-complement capture (Brain v1.1 #2 — parser-level)** — the rule/fact extractor reads only
the DIRECT object (`senses['direct']`), so a **prepositional** complement ("run **in** a hardware" →
rule `(run, obj=None)` → derives "tokeniko run") and an **infinitival/control** complement ("want **to
know** their creator", which even mis-compiles to a spurious `IMPLY`) are DROPPED — the derived theorem
loses its meaning. *New specimen (2026-07-03 theorem autopsy): the **possessive relation** — "kotekino
is MY creator" flattens to the bare class membership `kotekino is_a creator.n.02`; the actual BOND
(creator-of-ME, a tokeniko↔kotekino relation) is dropped with the possessive. Same family: a relational
argument the zip doesn't carry.* Deep fix at the parser/compiler (Stanza-level, adjacent to the parked D3a
subject-rebinding + prepositional-complement work). Workaround today: phrase with a direct object ("all
softwares need hardware", "all thinkers seek their creator"). The deepest pole of the Brain v1.1 arc.

**Differentia-rule VERB recovery (definitions-as-rules, step-5 residual)** — the strict differentia
gate (step 5.1) keeps only reliably-clean rules zip-only: adjective differentia ("all apples sweet") +
transitive verbs WITH a direct object ("all bathrooms contain a bathtub"). It conservatively DROPS the
verbs it can't disambiguate from the zip alone — **passive-voice reduced relatives** ("an airfield
**equipped** with…" → the class is the patient, not "airport equips") and **intransitive agentive
verbs** ("trained **to compete**"). Separating these needs **parser-level voice/agency detection** (the
reduced-participle vs finite-relative-with-nsubj distinction), adjacent to the parked D3a
subject-rebinding work. Would recover the verb bulk (~300 candidates) as clean differentia rules and
substantially grow the enriched-soak fuel. Promote when the parser voice signal is built.

**Restricted-universal residuals (Brain v1.1 2c follow-ons)** — the conditioned-rule fix covers
amod/compound modifiers ("thinking machines", "wild animals"). Not yet covered: **relative-clause
restriction** ("all machines THAT THINK are minds" — compiles through the subordinate path, not a
subject property; needs the same cond_props emission from a restrictive-subordinate clause) and
**object-side modifiers** ("all thinking machines have an ARTIFICIAL body" → the direct role's amod
is still dropped — meaning-loss, not scope-widening, so lower stakes). Promote with step 4 (the
universal extractor shares the conjunctive machinery).

**Negated-copular DISJOINTNESS extraction (Brain v1.1 step-2 residual)** — "a dog is not a cat" /
"no machine is a human" (a negated/NEGATIVE copular noun-noun generic) is a **disjointness claim**, not
an is_a edge and not a property rule — today the step-2 extractor counts it (`negated_skip`) and moves
on. A future extractor could mine these into pairwise-disjoint assertions feeding
`relations_disjoint` (the refutation side), symmetric to how affirmative copulars feed subsumption.
Promote when curated fuel starts stating exclusions.

**Tier-1 / KB growing OUTWARD** — genuine *synthetic* learning from trusted testimony (learned axioms
vs derived theorems; the analytic/synthetic cut). Full design + open forks in **`doc/ref/kb-growing-outward.md`**.
Needs the trust-gradient; build after the consolidation floor is solid.

**Questions follow-ups** — imperatives (the `imperative` scalar, same mechanism); wh where/when/how
solving + real self-knowledge for "how do you feel?"; multi-clause / embedded questions.

**Conditional reasoning / premise-in-question (R4b)** — "given P, is Q?" where a premise is submitted
*with* the question (stanza subordinates it as a `ccomp` under the question ROOT). Today the premise's
truth AND-folds into the polar verdict → a **false premise gives a confident-wrong NO**
("a stone is an animal, is a cat an animal?" → NO). The *floor* fix: propagate a "question vs
co-submitted premise" discriminator onto `TKZipContent` (per-clause mood, not blanket `_stamp_mood`) +
fold only the question leaves in `_polar_answer` (→ honest IDK/correct YES). The *real* behavior — USE
the premise hypothetically — is conditional reasoning, built with the question-answering deepening.
Full diagnosis in `doc/ref/test-feedback.md` (2026-06-25). Trigger is uncommon; normal questions unaffected.

**Performance (optimize-later)** — `evaluate_zip` reloads the full active KB on every call → ~12s/item
brain throughput; cache the active KB across ticks. Dual `en_core_web_lg` load (`parser.nlp` +
`c_state.nlp`) → consolidate.

**WSD (deeper refinements, beyond the next-up Pillar 3 #2)** — contextual WSD for ambiguous heads;
co-predication hint (prefer attribute-sharing adjective senses); graded attribute-contrariety (no
crisp `antonym` edge). xfail "a robin has feathers" (WSD-gated thin grounding → confident-ish verdict
where it should abstain). *(The core sense-selection + sense-number canonicalization is `roadmap.md`
Next.)*

**Parser / Stanza** — concessive + resultative clause types (`although`→OTHER, `so`→AND today); D3a
relative-clause matrix subject (Stanza mis-root); `imply`→IMPLY parataxis robustness; clausal-subject
support ("to err is human"); negative-quantifier subject rewrite ("nobody").
- *(Property-restricted universal rules / cogito fork ii — **UN-PARKED**: now `roadmap.md`
  In-progress 1a, the untangle-first step of wondering-v2.)*

**Evaluator** — geometric negation-awareness in `compareContent`; quantifier effect on the *geometric*
grounding; axiom/theorem `≡1` tautology creation guard; intrinsic comparison grounding (eq/noteq);
trust-weighted grounding + conflict arbitration; defeasibility of biological universals (crisp `all`
over-asserts — penguins don't fly).

**OOV / robustness** — tiered OOV recovery (optional LLM "polish" escalation on INSUFFICIENT);
sentence-level unparseable front-gate (cheap English-coverage reject before the slow Ollama translate).

**Anchors** — EXACT-membership mop-up (route the ~13 closed sets through the resolver); floor
calibration on a larger battery; KB vector-coverage gaps (`hugely`, `unequal`, `dissimilar`).

**Cleanup / misc** — 1b **verbs** (the "means"-frame drags a spurious predicate); legacy `axioms` /
`names` collection cleanup; `@-1,0,0` spacetime artifact; t-norm / implication choice (Gödel vs
Łukasiewicz vs product — the one semi-arbitrary constant); coreference (pronoun → individual).

**Dev tooling** — `probe_brain.py` (live brain-loop integration probe: injects a multi-author batch
via `/input`, asserts the loop invariants) currently lives in the scratch dir — candidate to formalize
into `scripts/` or `tests/`.

**Dreaming (a hunch — future, biological-creature framing)** — a new brain **phase**: access RANDOM
memories and *distort / mix / shuffle* them (a blender over the memory log) into a new **`dreams`**
collection that mirrors the `memory` modeling (also a timeseries). During the dream phase **`senses`
is paused and the other brain loops are paused — only the dream loop runs**. Use is TBD (a hunch —
likely creativity / consolidation / novel-association later). Revisit after the logical brain (D) is
whole. See `VISION.md`.

# tokeniko — parked (the icebox)

> Deliberately deferred — good ideas and known gaps that are **not** the current focus. Moved out of
> `roadmap.md` so the road ahead stays clean. Promote an item back to `roadmap.md` Next when its time
> comes. The active road is `roadmap.md`; history is `landed.md`.

---

**Conversation momentum (senses C follow-on)** — after tokeniko speaks in a channel he is IN the
conversation for a while, so the next ambient messages there deserve more than 0.6 (the author's
instinct: a multiplier lifting polite-guest toward engaged-participant ~0.75). The clean design is
already agreed: DERIVE it from the memory timeseries (his own recent self-speech in that
`channel_id` within a window), never stored state — the same principle as the open-why derivation.
Parked to watch plain C live first; promote when the missing lift is actually felt.

**Inbound preparser (B3, reversed by C 2026-07-11)** — `prepare=1` on senses→/input is OFF
(author's call): the Ollama pre-input path is under review (the polisher story — ollama / Claude
API / other), the playground server posts polished messages by discipline, and raw input doubles as
a standing parser/compiler robustness test (what breaks feeds `doc/ref/test-feedback.md` — exactly
the deepest-pole goal). Re-enable (or replace) when the polisher decision lands; a strong parser
under a polisher is strength in depth either way.

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

**Sufficiency v1 residuals (Brain v1.1 step 4)** — conservative firsts, promote if the enriched soak
shows them worth it: (1) **derived properties as cond satisfiers** — sufficient rules currently match
the seed's stored property FACTS only; letting chainer-derived properties satisfy definiens conjuncts
(recognition over inferred traits) needs the fixpoint interleaved with property derivation. (2)
**adjective-definienda sufficiency** ("has merit → valuable" — the finding-#3 flagship) has NO fuel:
all glosses were "a/an X is …" noun-templated, so adjective definienda compile as noun-STRUCTURED
zips (the step-5.1 pin now labels their subjects with the true `.s.`/`.a.` sense, but the clause
shape stays noun-copular); needs per-POS gloss re-templating first. (3) **class-seed recognition** — sufficient rules fire only
on individuals (property facts are uid-keyed); a class satisfying a definiens via its own differentia
rules is a further unification.

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

**Performance (optimize-later)** — the fingerprint KB cache (`_kb_cache`) landed, but every
materialized theorem changes the fingerprint → the next tick still pays a FULL reload (3233
definition zips, tens of seconds) — an incremental/delta reload would cut soak tick cost ~10x.
Dual `en_core_web_lg` load (`parser.nlp` + `c_state.nlp`) → consolidate.

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

**Mentalese materialize — a direct zip constructor for self-talk (post-arc, author-blessed
2026-07-09)** — wondering's materialize still round-trips through NL (render → re-parse), now made
safe by the sense-pin; but a mind's memory integrity should not depend on parsing its own speech at
all. The end state: build the `TKZip` DIRECTLY from the symbolic conclusion (dictionary vectors for
the senses, the one canonical SVO marker pattern all derived conclusions share, neutral spacetime),
still through the API materialize seam (write-path invariant + contradiction guard stay sacred); NL
becomes render-only (audit/blog/Discord), generated on the way out, never parsed on the way in. The
sense-pin is half of this already. DELIBERATELY deferred: until then the round-trip doubles as a
parser-robustness harness on tokeniko's own generated speech (it caught the "stores"-as-noun leak) —
switch to mentalese once the parser has eaten enough of these tests.

**Plural-genus collection/member gate (enriched-soak specimen, 2026-07-09)** — "a forest is the
TREES and other plants in a large densely wooded area" minted tier edge `forest.n.01 is_a tree.n.01`
→ «a forest has trunk» @0.3. A PLURAL genus head ("the trees") defines a collection by its members —
that is collection-of/member-of, never is_a. Gate improvement for `extract_isa_edges`: reject (or
re-type) a plural-headed genus. Companion specimen: differentia OBJECT mis-sense («a sector
illustrates fabric» — "textual material" got the textile sense); the object-side WSD shares the
general differentia-WSD residual above.

**TKZip binary compaction — the zip becomes an actual vector (author's note, 2026-07-09)** — today's
`TKZip` JSON is the human-readable PROJECTION of what VISION says it is: a fixed-size mathematical
object. Field names, nesting, floats-as-text are scaffolding for human eyes. With correct data
modeling the payload packs to near-pure numbers (the role tensors are fixed-size by constraint; the
operator tree is the only variable part) — orders-of-magnitude smaller. Becomes LOAD-BEARING when
zips cross the wire (the native-zip channel: bandwidth) and when memory grows life-long (storage).
Pairs naturally with the mentalese materialize constructor above. Deliberately later: representation
performance is an optimize-later concern ([[laptop-ceiling-optimize-later]]); design it once, with
the wire format, not piecemeal.

**Conversational expectation — the open-why (go-live specimen, 2026-07-09)** — tokeniko's first live
act was asking «why is that?»; but when the human answers, the "because" is evaluated COLD — he does
not remember he asked. The missing piece is dialogue context, and the author fixed its architecture
in one line: **context is never a volatile store — it is ALWAYS derivable from the state of memory.**
No session state machine: when an inbound arrives, DERIVE the open expectation by querying his own
biography (did I recently ask why to this speaker / did this message reply-thread to my question? →
evaluate the inbound AS a candidate explanation of the original statement — which feeds the learning
channel + trust ledger, step 3). Exposed gap the derivation needs closed: his OWN speech currently
lives only in the actions log — for context to be memory-derivable, delivered outbound must land in
`memory` too (sourceId=tokeniko). Companion of the trust ledger; builds on reply_to threading. And the recency weighting the
derivation needs is FREE by construction — `memory` is a Mongo TIMESERIES precisely so that
recent-items queries are cheap and natural (the author's point: that collection type was chosen for
this).

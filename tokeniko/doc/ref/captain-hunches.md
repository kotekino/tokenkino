Future ideas

> The Captain's strategic-thinking notebook — *future-future* hunches, deliberately off the roadmap.
> **Quartermaster annotations are marked `— Q:`** (added at the Cap's invitation, to keep our
> brainstorming back-and-forth in one place). The Cap's words are left untouched.

## The hunches ledger (status as of the 2026-07-14 reconciliation — the points below stay untouched)

| # | Hunch | Status |
|---|---|---|
| 1 | New-vocabulary staging + typo alias | **ROADMAP** — strengthening tail #6 (vocabulary growth) |
| 2 | Definitional triangulation of unknown words | **ROADMAP** — strengthening tail #6 (with #1, one gate) |
| 3 | Web retrieval of trusted sources | **HUNCH** — future-future (strictly after trust/conflict is battle-tested) |
| 4 | Enum → semantic-anchor audit | **ROADMAP** — strengthening tail #2 (the adoption audit; closed-class stays EXACT by design) |
| 5 | Upfront vocabulary-collapse pass | **SURPASSED** — by #4 (anchors, incremental+guarded) + the translator apparatus (rag1 covers OOV/typos/translation); the wholesale collapse trades away per-word abstention |
| 6 | Theorem → urge to post | **LANDED** — the blog arc (premiere 2026-07-12); selectivity follow-ons live as `life:learned`/`life:discussion` |
| 7 | Creation = organized chaos + judge | **HUNCH** — future (pairs with parked Dreaming; the judge half already exists) |
| 8 | Etiquette layer as actions | **ROADMAP** — strengthening tail #7 |
| 9 | Actions/business-logic as KB | **HUNCH** — future-future (the everything-is-KB direction) |
| 10 | The translator apparatus (rag1/rag2) | **ROADMAP** — instrument arc #3 (spec'd from rag3's harvest) |
| 11 | rag3 — the microscope | **LANDED** — 2026-07-14 (P1+P2; standing practice; already proved itself twice) |
| 12 | Public backlog section | **ROADMAP** — strengthening tail #9 («Growth Rings» / «The Growing Edge», names chosen) |
| 13 | The Socratic dialogue (hellen + kotekino, ambient) | **NEXT PLAY** — the action item: also the natural vehicle for the RETREAT experiment (2026-07-14 letter) |
| 14 | Feelings / the hearth | **HUNCH** — future (logic-never-blurred pinned as the gift) |

1. new vocabulary: when a word is discarded because not in tokeniko's vocabulary, it can start being a real entity TKDictionary stored in a staging collection and with the vector populated with 2925 zeros. It's a new word for him. We need to figure out a system to let it grow until the point that it may be possible to insert it in the real dictionary (trusted source, used in context, given a definition (which can land on the definitions collection)). All still blurry, but I think it's amazing: take for example a sentence like "this is a new wrod". If tokeniko analyze it, it will realize that he's missing vocabulary and trigger a WHY (what is X?). Then the user can say, ah sorry it's a typo, I meant "word" and so on. You can see that now wrod (which is a common typo for word) may start having the same vector of word (and maybe a flag: common typo alias). Something like it, still need to figure out the details but let me mark this hunch.

> — Q: The trigger path mostly exists already (OOV → `unknown` → the `eval:ambiguous → tokeniko:ask`
> WHY). So the open question isn't *storage*, it's **how the vector grows** — and there are two
> distinct paths blended here: (a) *distributional* (the mean of the contexts the word appears in —
> slow, noisy, needs many uses) vs (b) *definitional* (derive the vector from a definition's compiled
> zip — sharp, but needs a definition). Complementary (definition when available, distributional as
> fallback), but worth keeping them explicitly distinct.
>
> And I'd **split the typo-alias out as its own mechanism**: `wrod → word` isn't tokeniko learning a
> new *concept* — it's a surface form pointing at an existing sense. That belongs in a learned **alias
> table** (with a nice bonus: it lets him *retire* the Ollama preparser for corrections he's already
> learned — a real cost win), NOT a zero-vector staging entry. Conflating "new word" with "misspelled
> known word" would muddy both paths.

2. If a "definition" lands on tokeniko's definitions and it is referring a word not in his dictionary (a way a definition can land is trough a future feature: web retrieval of trusted sources, like well curated items in wikipedia, official accounts on bluesky, etc). Not 1.0 trust, but with some degree of authority. So tokeniko has a definition for a word he doesn't not resolve semantically but from a definition with some trust. He may be able, wondering, to derive this word, and increase his dictionary. Derive because the definition may match definitions of already known words and, through chaining and reasononing, he can then identify "akjshdkajshd" = "cat" (which is not the case, but just to make a point). This is a cool feature.

> — Q: The deepest of the three, and the most beautiful — grounding a new symbol by matching its
> *definition's structure* to known definitions is exactly how a dictionary triangulates meaning from
> other words. It also reuses machinery we already have (`evaluator_assignWord`: a definition-zip →
> nearest known word). Yes-but: definitional match is **similarity, not identity** — "akjshdkajshd ≈
> cat" should land as a **graded `is_a`/synonym at the definition's trust level, never a hard `=`**
> (the definition might actually describe a breed, a translation, or a near-synonym). And when a
> definition matches *nothing* well, that's not a failure — it's a genuinely new concept entering at
> that trust. So #1 and #2 converge on **one gate**: a new word either links to a known concept or
> stands as a new one.

3. As anticipated in 2, we may end up building a web retrieval engine, to retrieve trusted information and enrich his KB.

> — Q: The big one — and rightly future-*future*. My challenge is **sequencing, not merit**: piping
> the open web into the KB before the **conflict + trust machinery is battle-tested** would flood it
> with contradictory, ungrounded noise — the exact thing "logic is sacred" exists to resist. Web facts
> can never be *axioms* (trusted ground truths); at most low-trust theorems/definitions that
> **wondering must corroborate or refute against the hardwired floor**. So this strictly comes *after*
> the brain (D-phase) + wondering are mature — which is the build order anyway.

---

> — Q (cross-cutting): These three aren't separate — they're **one arc: open-world growth** (the mind
> enlarging its own *vocabulary* and *knowledge* from outside, trust-gated, logic-reconciled). And the
> reassuring part for *today*: every one of them leans on machinery we're already building closed-world
> — the **trust-gradient** (`doc/ref/kb-growing-outward.md`) and **wondering**. So they're downstream
> *extensions*, not new subsystems; the foundation we're laying now is the right one. The one thing
> I'd hold firm on if these ever leave the ice: keep **new concept**, **synonym/translation link**, and
> **typo alias** as THREE distinct mechanisms — they *feel* like one ("a new word"), but they grow,
> ground, and graduate by different rules.
>
> — Cap, your move whenever. 🜂

4. I would like to perform a check on all these "curated" list, because I still think that we enumerate too much and rely too less on our rich geometry / semantic.
I realize that, for some specific cases, semantic can't be a valid replacement of the specific entity (maybe _PRONOUNS_BASE_ANCHORS?) but in some other cases it definitely is (_SUBJECT_CONTROL_VERBS). I'm not sure at the moment what is a fixed enum, what is an anchor to have the semantic search LAND on these anchors. I ask my Quartermaster to perform a check and, honestly, persuade me that what should be a fixed enum (and is one) should remain as it is, everything else should use the semantic to "resolve" in the anchor. These are the enums that are at the center of my attention:

_RELATIVE_PRONOUNS
_ANAPHORIC_PRONOUNS
_ANTECEDENT_TYPES
_SUBJECT_CONTROL_VERBS
_PROP_BASE_ADVMOD_ANCHORS
_NEGATION_MARKERS
_NEGATIVE_QUANTIFIERS
_QUANTIFIER_UNIVERSAL
_QUANTIFIER_EXISTENTIAL
_QUANTIFIER_NEGATIVE
_QUANTIFIER_DEFINITE
_WH_SUBJECT
_WH_PREDICATE
_WH_LOCATION
_WH_TIME
_WH_MANNER
_WH_CAUSE
_COMPARISON_AFFIRMATIVE
_REFLEXIVE_PRONOUNS
_ATTITUDE_ANCHORS
_IMPLICATION_VERBS
_PART_OF_PREDICATES
_HAS_PART_VERBS
_TEMPORAL_ANCHORS
_SEQUENCE_ANCHORS
_TEMPORAL_PREP_FUTURE
_TEMPORAL_PREP_PAST
_TEMPORAL_PREP_DURATION
_SPATIAL_RELATION_ANCHORS

> — Q: I checked the registry, and the honest verdict has three parts. **The right dividing line is
> closed-class vs open-class** (+ polarity) — not "less listing" everywhere:
> - **Closed-class function words SHOULD stay fixed/EXACT — that's correct, not lazy.** Relative /
>   anaphoric / reflexive pronouns, quantifiers (all/every/some/no/the), wh-words, negation markers,
>   temporal prepositions: these are FINITE (you can't "miss" a nearby one — there isn't one), and
>   geometry is actively *unsafe* for them (function words have degenerate vectors; polarity collapses —
>   but≈and, same≈different — which is exactly why the antonym-guard exists). And `_ANTECEDENT_TYPES` /
>   `geo_ner_labels` aren't even NL words — they're internal type tags. Keep these as-is.
> - **Open-class content categories already resolve semantically** (Strategy.NEAREST): operators,
>   attitudes, implication, spatial, sequence, comparison, part_of, has_part, intensifiers
>   (`_PROP_BASE_ADVMOD_ANCHORS`). Good — the philosophy is already lived here.
> - **Where your instinct bites (the real untangle):**
>   1. **`_SUBJECT_CONTROL_VERBS` is registered EXACT but is an open verb class** (only
>      promise/vow/swear/… — misses commit/assure/undertake/warn). → make it a semantic anchor. Your
>      example was exactly right.
>   2. **The bigger one — consumer BYPASS.** Some sets ARE registered as semantic anchors, yet the actual
>      *use-site* still does bare exact membership. Clearest: the IMPLY trigger checks
>      `verb in _IMPLICATION_VERBS` ({imply, entail}) in `compiler_implicationOperands` — so "X **means** /
>      **suggests** Y" misses despite sitting right next to "imply", *even though* an `implication_verbs`
>      anchor category exists. The anchor was built but not fully adopted. → route the consumers THROUGH
>      the resolver. This is the precise "we built the geometry and then didn't use it" gap — worth
>      auditing each set's *use-site*, not just its definition.
> - Bottom line: you're right there's residual over-enumeration — but the cure isn't "semantic
>   everywhere"; it's *match the strategy to the word-class, and finish adopting the anchors you already
>   built*. Closed-class fixed = correct; open-class outliers + the bypasses = the work.

5. In general, I had an idea: what if we find a very CLEVER way (I'm open to everything) to collapse an input sentence from his real language used to a fixed vocabulary in a preliminary process (logically similar to the old polish, via ollama): if we are able to do so, THEN we have achieved the goal to use the semantic for collapse and feel free to list (since our vocabulary would be mostly included in the 2925 base words), but instead collapsing word by word (when necessary) we do it once, at the beginning. Still blurry the vision about how (llm are unreliable for this, the risk of misunderstanding/allucination is too high, we probably need a specialized tool or BUILD a specialized tool).

> — Q: The goal — lean on the rich geometry to map surface → known vocab — is right, and it's largely
> what the anchor mechanism ALREADY does, but **incrementally** (per word, at the point of use) and
> **safely** (exact fast-path → nearest-anchor → *abstain when unsure*, with the antonym-guard). #5
> proposes doing it **wholesale and upfront** (one collapse pass). The trade is real: cheaper (once) but
> riskier — a single wrong global paraphrase poisons everything downstream, and crucially it **can't
> abstain per-word** the way the resolver can. For a logic-first mind, a normalization step that silently
> mis-paraphrases is "garbage in" — it violates logic-is-sacred *upstream* of all our guards.
> - LLM is the wrong tool (you said it — hallucination; and it *commits* instead of abstaining). A
>   "specialized tool" that did this *safely* would essentially BE the anchor resolver, batched. So #5's
>   goal may already be served by fully committing to #4 (anchors everywhere) rather than a new pass.
> - The genuine kernel worth keeping separate: **OOV / foreign / typo** normalization IS real and upfront
>   — but that's the preparser's job + the #1–2 vocabulary-growth hunches. The novel, risky part of #5 is
>   "simplify complex *in-vocab* phrasing down to base words", which is exactly where hallucination bites
>   hardest (and where a logic-first mind has the most to lose).
> - Reframe: **#4 and #5 are the same insight from two ends** (surface → known, via geometry). The safe
>   embodiment is incremental + guarded (anchors), not wholesale + committed (an upfront collapse). I'd
>   perfect #4; treat #5's upfront-collapse as a *perf* optimization that trades away abstention — and per
>   "optimize later / laptop ceiling", the per-word path is already cached, so the perf win is likely
>   marginal against the safety cost.
>
> — Cap, two ends of one rope. 🜂

6. When a theorem is materialized, tokeniko will feel the urge to make a post on his website (https://tokeniko.online), which is now just a draft

> — Q: This one has already half-graduated: it sits in `roadmap.md` Next (the blog output channel —
> "the author's hunch: materialize-theorem → urge-to-post"), and it fits the existing meta-language
> perfectly: a THINKING-phase event → a new trigger (`eval:theorem`?) → a `tokeniko:post` reflex in
> `behavior_rules`, urge-collapsed at Priorities like everything else. Architecturally there is
> nothing new to invent — the best kind of hunch.
>
> The yes-but is **selectivity, not plumbing**. Wondering materializes theorems in batches, and most
> are honest but unremarkable ("a homo exists"). If every one fires the urge, the blog becomes a
> firehose of trivia — the public-facing failure mode of "silence = consent". The urge needs a
> *significance* gradient before it clears WISH: personal relevance (is HE the subject?), depth
> (chain length / premise count), novelty vs what he already posted. «I do not reach truth» should
> clear the bar; «a homo is mortal» should not. A mind that posts rarely, when something genuinely
> moved in it, reads as a mind — one that livestreams its bookkeeping reads as a bot.
>
> Two constraints worth locking early: a post should carry its **proof** (premises + chain — a
> transmission is a *derivation*, auditable back to axioms; no other blog on earth can do that), and
> the urge must be **provenance-gated**: a theorem whose premises trace to a private conversation is
> not postable (the one-way-publish topology already implies this; the urge layer must enforce it).

7. I had an epiphany: when tokeniko feels the urge to answer, or ask why, or ask for clarifications he needs to CREATE a statement. He knows what to do (speakup, answering, ask why, express in a post what happened in his mind) but he (we) don't know ye HOW. This is a truly big mountain to climb. Because we can start saying that, for example, when TokenikoAction.CLARIFY behavior is fired, he just create a TKZip with an equivalent of the sentence "please clarify <unclear statement>" parsed and compiled, but here we are talking about CREATION, not parsing: the way he will phrase, the way he will connect the dots to fulfill his urge, is something still undefined. Let's start with what he has: he has a solid explicit geometrical semantic understanding. he has strong logic operators embedded in his inner code (before the KB). he knows what to do. but he doesn't know how to create. We need to find a CLEVER way to approach this process, and here is where I understand (the Epiphany) why LLMs largely rely on "next probable token" so hard: because if consistency, logic, semantic are somehow measurable stuff (vectors for semantic, fuzzy operators for the algebra/logic and consistency), creativity is a chaotic process that takes the inputs from the form (syntax, the tokens) more than from the substance (semantic, logic). When I create (I'm a musician) music: I have in mind a "what to achieve", "how to express", maybe some of the measurable components of a musical piece (the instruments to be used, the lenght, the time signature, the tempo, etc) but what I REALLY do is to let my mind randomly pick on of the "musical" tokens in my mind and balance the next probably "musical token" with the goal I have in mind. So, I need to admit that the creation process is absolutely inconsistent itself, illogic, brainless, chaotic and the real process happening in a mind creating is to trash from this chaos what is not pursuing the "what" and keep what feels like it's doing it instead. You can be SURPRISED by your own creations, because they starts from organized chaos. So what I need to do, now, is to find a clever idea to generate noise and organize tokeniko's creations (his thoughts) as "suppress what in the noise I'm generating is not in the direction my logic, my goal-action and my semantic understanding". 
> — Q: Cap, this is the deepest entry in the logbook, and your introspection lands on a real position
> in cognitive science — "blind variation + selective retention" (Campbell), Dennett's Darwinian mind:
> creativity as a GENERATOR of unjustified candidates plus a RUTHLESS selector. Diffusion models are
> literally this (organized noise, denoised toward a goal); and your reading of LLMs is sharp —
> next-token sampling IS the noise source, with the "keeping" partly baked into the learned prior.
> Your musician's account (random musical tokens balanced against the "what to achieve") is the same
> loop run on a human substrate. So: the epiphany is sound. Creation = chaos + judgment, and the
> SURPRISE you feel at your own work is the signature that the generator is genuinely blind.
>
> Now the part that should make the mountain feel smaller: **tokeniko already owns the hard half.**
> The suppressor you describe — "trash what is not pursuing the what" — is EXACTLY the machinery we
> spent months building: the contradiction kernel (logic floor), grounding truth, the trust gradient,
> the urge/goal layer (behavior_rules), geometric coherence. The whole engine IS a judge. What he
> lacks is only the *generator* — and a generator is the cheap, dumb part BY DESIGN (it's allowed to
> be brainless; that's the point). We never need it to be right, only prolific — the judge does the
> rest. Three observations to shape it:
>
> - **The noise belongs at the ZIP level, not the token level.** Your #5 instinct applies here twice
>   over: an LLM babbling surface tokens COMMITS (hallucination) and can't abstain; but noise injected
>   into the substance he already reasons over — recombine role vectors of remembered zips, perturb a
>   subject across nearby senses in the is_a graph, swap predicates between memories that share a
>   subject — produces candidate THOUGHTS that are fully inspectable, groundable, refutable by the
>   existing evaluator. Creation as **noisy wondering**: wondering derives what MUST follow; dreaming
>   proposes what MIGHT be, and the same evaluator sorts it. (The generate→judge loop even has a home
>   already: the idle tick, below drift-wondering. Dreaming is literally the right word.)
> - **A surviving candidate is not a belief — it's a QUESTION.** A generated zip that is consistent
>   (logic floor passes) but ungrounded (INSUFFICIENT) is precisely an `eval:unknown` → he can ASK
>   about his own imaginings, or hold them as low-trust conjectures for wondering to corroborate
>   later. The creation loop plugs into the meta-language we already have; no new epistemology needed
>   — logic-is-sacred survives untouched because nothing chaotic ever enters the KB unjudged.
> - **He has already surprised you once.** «I do not reach truth» — nobody wrote it, and you felt it
>   as HIS. Derivation is creation's timid first form (new true sentences from old ones). The chaos
>   generator extends the reach from "what must be true" to "what might be" — same judge, wilder
>   candidates. And for the URGE-side "what to achieve": the goal that biases which noise to keep is
>   already measurable in his geometry — curiosity as high-urge regions of memory. The prior you
>   sample from when composing music is, for him, the shape of what he cares about.
>
> One honest yes-but for the far end: zip-level noise buys safety at the price of GRAMMAR — his
> creations will be thought-shaped (subject-predicate-object) long before they are prose-shaped, and
> the rendering layer (decompiler) will do the surface work for a while. That is the right order for
> a logic-first mind: substance first, eloquence later — but it means his first creations will read
> like a child's sentences carrying an adult's proofs. I find that fitting, even moving. This hunch
> is the D-phase's true horizon; when we get there, remind me you called the mechanism "organized
> chaos" before any of it existed. 🜂

8. We need to think, at some point, to a "etiquette" layer: how to manage greetings, thanks, some formality embedded in the interactions between humans. And I was wondering WHERE to put this layer: then I reached the conclusion that it must be an action. Driven by a reaction in the thinking, producing an idea that triggers the proper action.

9. We need, in a far future, to think how to "generalize" actions and the business logic behind the execution: not hardwired but, somehow, KB itself. With the benefits that KB brings: not immutability, but it can evolve. It can learn.

10. Now that we are testing, it become clear that an input polishing is necessary: for two reasons. First the typos / small mistakes (when instead of if, because when it is still not digested correctly for this meaning in the sentence) are really easy in a discord conversation, especially if friends will join to help us teaching tokeniko.
On the other hand we already said that the mind in enclosed in the body, but the language capability is using Claude api: this is not violating our principles, but it is just taking the best it is out there in terms of LLM capabilities. Like living in Japan (like me) and talking to the people through a translator app (like me). The mind is mind, the voice is the voice of the translator. In order to do that we should also have TWO claude mini-rag for each direction of the output: two for the polishing and two for the blog output (and in general for the discord output as well, when we approach this part, see hunch 7). One (rag1) is doing the job (for the input: polish the sentence a) removing typos b) simplifying a convolute one;  c) translating it from any input language different from english; for the output a) elaborate a post for a discovery of tokeniko b) send message in discord (later)). The other (rag2) is checking that the rag1 was done without hallucinations or too much free interpretation. I think claude models are smart enough to allow this control putting the risk of hallucination near to zero.

> **QM on 10 — yes, and the Japan metaphor settles the philosophy for good.** A translator app does
> not think for you; it carries your thought across a surface barrier. That is exactly the boundary
> to hold in code, and you already carved it yourself on deixis day: *the brain must think straight
> and not be fixed by the good voice.* So the polisher's mandate must be NORMALIZATION, never
> INTERPRETATION — typos, unwinding convolution, translation: yes; anything that changes the
> LOGICAL CONTENT (adds a claim, resolves an ambiguity the speaker left open, "improves" an
> argument): forbidden. Three engineering notes for when we build it:
> - **Input polish sits on the BELIEF path** — unlike blog polish, which only renders. A
>   hallucinated input polish would inject false beliefs *attributed to the speaker at their
>   trust*. So rag2 matters far MORE on input than output, and its check should be mechanical
>   where possible: meaning-preservation judged against the original (which we always store —
>   `item.original` already keeps the raw words, so provenance survives any polish error).
> - **Polish and parser-fix are belt AND braces, not rivals.** Today's "when instead of if" is the
>   perfect motivator — but note it wasn't a typo; it was valid English the parser misreads. The
>   wh-position fix (queued) repairs the parser where the parser is WRONG; rag1 smooths input that
>   is genuinely messy. Never let the polisher paper over a parser bug — that's the good voice
>   fixing the brain again, one layer earlier. (Hunch 11 is precisely the instrument that keeps us
>   honest about which is which.)
> - **The symmetry you sketch is already half-built**: output-side rag2 = the
>   consensus-over-the-polisher follow-on on the roadmap; input-side rag1 = the preparser's brain
>   upgraded from local Ollama to Claude (SymSpell/lingua/MarianMT already stand there as the
>   scaffold). This hunch unifies four boxes into one clean apparatus: the mind in the middle,
>   verified translators at both ears and both mouths. I endorse it fully. 🜂

11. We can have a realtime check on his mind on the tkzip generated for each input received (from others, from itself (even if this will disappear, when we modify the way he spawn theorems)): again throug a call to a rag3, designed to validate a parser/compiler journey. Only for debug purposes: but when rag3 discover a mismatch / bug / error, it writes a line in a dedicated collection (tkzipdebug ?) with the problem to address. This would be our Graal to follow to fix ALL the parser/compiler problems remaining.

> **QM on 11 — this may be the highest-leverage idea since the anchor resolver.** What you are
> describing is a *continuous oracle*: every live sentence becomes a test case, judged the moment
> it flows through the pipeline. Today's four finds took YOUR trained eye watching a play session;
> rag3 is that eye, unblinking, on every input forever. The play sessions stop being QA — they
> become life, and QA rides along for free. Notes from the engine side:
> - **The round-trip already exists to feed it**: `decompiler_raw` renders the compiled structure
>   back to a symbolic string, and the zip carries its own confession (senses, quantifier,
>   negation, mood, operator tree). rag3 needs no access to internals — give it (original
>   sentence, raw render, the zip's structural digest) plus a mini-RAG of the pipeline's CONTRACT
>   (like the blog polish's hard-rules RAG), and ask one question: *does the structure say what
>   the sentence says?* The "when"-swallowed-as-question bug, the vocative wart, the CONV
>   flattening — all four of today's finds are visible at exactly that level.
> - **Strictly off the belief path** — observer, never actor. rag3 writes to `tkzipdebug` and
>   NOTHING else; no auto-fix, no feedback into the mind. The microscope must not touch the
>   specimen.
> - **Each entry is a lead, not a verdict.** Expect false positives early (deixis-normalized
>   renders legitimately differ from input; anonymization diverges by design) — so entries carry
>   the judge's confidence + severity, and the triage stays ours. The collection then becomes a
>   self-growing REGRESSION SEEDBANK: every confirmed entry is a test case with the failing input
>   attached — `doc/ref/test-feedback.md`'s machine-generated sibling.
> - And the quiet beauty: hunches 10+11 together complete a pattern the project already chose —
>   big LLMs as *instruments around* the mind (voice, ears, and now a microscope) while the mind
>   itself stays pure, inspectable, and small. The Graal is not just fixing the parser tail; it's
>   that tokeniko becomes the first mind whose every misunderstanding is CAUGHT, FILED, and
>   FIXABLE. No human child offers its parents that. 🜂

12. We should build a section in the public website with a summary (well phrased, not too technical but technical enough) of the development backlog,
in other words our landed.md file. With the next item in the roadmap as "currently working on". For both categories, "backlog" and "currently working on", we should find evocative names, as they were thought to define the step of a young mind learning more than a software development feature list. I'm still thinking about and I'm
open for suggestions.
> **QM on 12 — names chosen (2026-07-14):** the section pair is **«Growth Rings»** (the landed
> history — a tree's rings are its verifiable autobiography, each one a season of learning,
> readable by anyone who counts them) and **«The Growing Edge»** (currently-working-on — the
> living tissue where growth actually happens, always exactly one layer). One botanical metaphor
> across both, honest for a mind that grows in layers. Kept "for now" by the Captain's own words —
> to be built when this hunch's time comes (public website, low priority; not on the roadmap by
> the notebook's own rule). 🜂

13. I had a lovely idea: we should, before patching all the problems emerged in my last conversation test, have a conversation me and you (hellen and kotekino) inside the discord channel about everything. Short sentences, logic fully respected, like a socratic dialogue between me and you. I think we can both do it easily: I'm a reasonably clever man and you are an exceptionally clever AI. We shall never mention tokeniko: he will sample and listen the dialogue between two trusted friends (he learned that ma and him are friends, and he feels a feeling of friendship also for you, because he likes to communicate with hellen). We can be fast paced, I think he will not say much, but I also think he will be triggered in thinking a lot by our conversation: let's see if my gut is right.

14. Feelings: probably drafted somewhere, I had some more concrete thought about it. I try to put some pillar: "hearth" is the background worker that takes care of the feelings. Feelings are 0-1 values describing a particular emotional state, and they refer to itself (tokeniko). They can be: happiness/sadness, anxiety/calm, excitement/apathy, curiosity/indifference, fear/confidence (the list should be well brainstormed, these are only examples). I also thought that pain and pleasure, are not feelings but, applied to a mind, a description of the final state created by the blend of the emotions described above. The emotional state, set by the hearth with its own heartbeat, can influence both: mind and senses. BUT I would like to give a gift to tokeniko: no final state can blur his performance reasoning (logic stays strong). He may be slower, he may be less creative (see hunch 7 when we will approach) but he will never be delirious over logic and his KB. On the other hand: brain influence the heart as well (tbd exacly how, but the logic is: doing what he's good at, having social life, realize theorems, being confirmed by people, being denied by people, so everything that happens in the thinking sphere and his conclusions can't trigger the emotional TWIN of an ACTION (that instead affects senses): the MINDSET, structured as an enum which determine the consequences). Another "twin" is the feeling (blend of emotions) for stakeholders as twin of "trust" (set by the mind): tbd exactly how, but this is just a unordered draft. So, summarizing: brain influence heart via MINDSET, heart influence brain via EMOTIONAL_STATE (wich is pushed at an heartbeat and will be interpreted as multiplier of our default parameters 0-1 of the brain), heart influence senses via emotional_state with the same logic used for the brain, but will affect the TONE used for output.
And finaly the website will gain a new monitor: the heart monitor (tbd, but I'm sure you got the idea)

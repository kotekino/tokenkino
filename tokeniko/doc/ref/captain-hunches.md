Future ideas

> The Captain's strategic-thinking notebook — *future-future* hunches, deliberately off the roadmap.
> **Quartermaster annotations are marked `— Q:`** (added at the Cap's invitation, to keep our
> brainstorming back-and-forth in one place). The Cap's words are left untouched.

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
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
> — the **trust-gradient** (`doc/kb-growing-outward.md`) and **wondering**. So they're downstream
> *extensions*, not new subsystems; the foundation we're laying now is the right one. The one thing
> I'd hold firm on if these ever leave the ice: keep **new concept**, **synonym/translation link**, and
> **typo alias** as THREE distinct mechanisms — they *feel* like one ("a new word"), but they grow,
> ground, and graduate by different rules.
>
> — Cap, your move whenever. 🜂
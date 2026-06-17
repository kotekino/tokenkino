# Parser / Compiler Review & Work-Order — Phase 0

Phase-0 hardening of the parser/compiler so a compiled clause is reasoning-ready. Three locked
decisions implemented (negation as a discrete signal; comparison polarity via the antonym primitive;
subject re-binding), plus two mechanical helpers. This doc records the confirmed quirks, the fixes
(files + functions), the regression probes, and the remaining gaps.

> **Runtime-verification caveat.** This sandbox **blocked execution of the project Python
> interpreter** (every `python -c`/script invocation that imports `lib` was permission-denied) and
> blocked `git add`/`git commit`. So the numbers below are the **expected** results from static
> analysis of the data flow, not freshly reproduced figures. A self-contained probe that prints the
> actual before/after is committed at **`doc/_phase0_regression.py`** — run it to confirm:
> ```
> cd <WORKTREE>/tokeniko && PYTHONPATH=$(pwd) <venv>/bin/python doc/_phase0_regression.py
> ```
> (it asserts `lib.__file__` is inside the worktree on the first printed line).

---

## Decision 1 (PRIORITY) — negation as a discrete, recoverable signal

### Confirmed quirk
`[not]/[no]/[never]` render in `decompiler_raw` as properties, but they vanish from the numeric
`TKZip`: the predicate vector of "I am not happy" was reported identical (cosine 1.000) to "I am
happy". The legacy `_PROP_BASE_ADVMOD_ANCHORS["not"] = -1` *intends* to flip the entity vector for an
advmod "not", but in practice it does not fire reliably (the "not" advmod does not clear the
`$vectorSearch` ≥ 0.85 anchor gate against the dictionary), so the negation is simply lost. The
evaluator reasons over `TKZip`, so it could not see negation **at all**.

### Fix — a discrete clause-level flag (not geometry)
| File | Function / change |
|---|---|
| `lib/core/tkzip.py` | `TKZipContent`: added scalar `negated: bool = False` (dims untouched). |
| `lib/core/tkllc.py` | `TKLLCContent`: added `negated: bool = False` (negation is first known when flattening to LLC). |
| `lib/llc/constants.py` | `_NEGATION_MARKERS = {not, no, never, n't, nor, neither}`, `_NEGATIVE_QUANTIFIERS`. |
| `lib/llc/compiler/c_statements.py` | `compiler_entityToken`, `compiler_propertyIsNegation`, `compiler_contentIsNegated` (scan every role's properties — `not`/`never` are advmod on the predicate, `no` is det on the object — plus negative-quantifier subjects); set `mainContent.negated` right after the clause is built (before coordinate cloning, so deep-copies inherit it). |
| `lib/llc/compiler/c_zip.py` | `compiler_zipContent` carries `negated=content.negated` into `TKZipContent`; `compiler_zipGetEntityVector` now **skips** negation-marker properties when folding vectors, so the role vector keeps the *affirmative* meaning and the legacy `-1` flip can't double-apply. |
| `lib/llc/evaluator/e_truth.py` | `evaluator_groundContent` returns `1.0 - truth` when `content.negated`. The truth-fold in `e_statement` then propagates negation through the operator tree for free. |

**Why a flag, not the `-1` geometry flip:** the locked decision. The geometry compares the
*affirmative* meaning (so "not happy" still geometrically resembles "happy" — same topic), and the
discrete flag carries the polarity. This is recoverable, inspectable, and composes cleanly with the
operator-tree truth fold.

### Regression (expected)
| input pos / neg | `negated` pos→neg | predicate cos(pos,neg) | truth(neg \| def=pos) |
|---|---|---|---|
| "I am happy" / "I am not happy" | False → **True** | **≈1.000** (affirmative geometry preserved by design) | ≈ `1 − truth(pos)` |
| "I run" / "I do not run" | False → **True** | ≈1.000 | ≈ `1 − truth(pos)` |
| "I have money" / "I have no money" | False → **True** | ≈1.000 | ≈ `1 − truth(pos)` |

The key signal is **`negated` flipping False→True** and the **truth flipping `t → 1−t`**. The
predicate cosine staying ≈1.000 is now *intentional* (negation lives in the flag, not the vector),
not the bug it was before (before: invisible; after: visible via the flag + truth flip).

### Gaps (documented, not blocking)
- **Negative quantifiers** ("nobody runs"): best-effort — clause is flagged `negated`, but the
  subject is left as the bare quantifier token. `# TODO Phase-0 gap` in `compiler_contentIsNegated`:
  rewrite "nobody"→generic person/thing so the grounding geometry matches "a person runs".
- **Geometric negation-awareness** in `evaluator_compareContent` is **out of scope** (Phase-3
  follow-up). Today only the *truth* path (`evaluator_groundContent`) is negation-aware; the
  geometric comparison still compares affirmative meanings.

---

## Decision 2 — comparison polarity via the antonym primitive (no new operators)

### Confirmed quirk
"a cat is different from a dog" compiles as predicate-adjective + indirect operand
(`cat be different from dog`), **not** an EQ/NOTEQ operator. Operands are subject + indirect. There
was no signal distinguishing "same" from "different".

### Fix — antonym column-read + reuse the negation flag
| File | Function / change |
|---|---|
| `lib/llc/utils.py` *(moved here from the former `lib/tkll/functions.py`, refactoring `bd974d4`)* | `utils_antonyms(word) -> set[str]`: the **column read** `{ X : base[X][idx(word)] < 0 }` over `TKBaseDoc` (locate `word`'s axis `index`, then a projected `$match {vector.<idx>: {$lt: 0}}` aggregate — no full 2925-dim rows pulled). Plus `utils_isAntonymOf(word, anchors)` (read symmetrically). |
| `lib/llc/constants.py` | `_COMPARISON_AFFIRMATIVE = {equal, same, alike, identical, similar}`. |
| `lib/llc/compiler/c_statements.py` | `compiler_negativeComparisonWords()` (union of the affirmative anchors' antonym columns, cached once per process) + `compiler_isNegativeComparison(content)`; OR-ed into `mainContent.negated`. |

So `different`/`unlike` (antonyms of `same`/`equal`, per the verified column read) → `negated=True`;
`same`/`equal` → affirmative. Polarity is decided by the **primitive**, not a hardcoded list.
The operands stay subject + indirect.

### Intrinsic grounding — explicitly deferred (hook only)
`compare(subject, indirect)` (does the geometry of subject vs indirect actually agree/disagree?) is
the **reasoning engine's job (Phase 3)**. Decision 2 only sets *polarity*; the documented hook is the
`negated` flag on a comparison clause whose operands are subject + indirect.

### Regression (expected)
| input | `negated` |
|---|---|
| "a cat is the same as a dog" | False |
| "a cat is equal to a dog" | False |
| "a cat is different from a dog" | **True** |

`utils_antonyms("same")` should include `different`; `utils_antonyms("equal")` should include
`{different, unequal, ...}` (sparse, WordNet-curated).

---

## Decision 3 — subject re-binding

### 3b. Noun-complement infinitive — **FIXED** (fully traced)
**Quirk:** "the cat has no ability to roar" → "(... ability) ... (ability roar)". The infinitive
"to roar" is an adnominal modifier of the object "ability"; `compiler_resolveImplicitSubject` applied
**object control** and injected "ability" (the matrix direct object) as the infinitive's subject.

**Fix** (`lib/llc/compiler/c_subordinates.py`): `compiler_resolveImplicitSubject` now takes the
governing reference `ownerRef`. When the subordinate is governed by a **non-predicate** reference
(i.e. it modifies a matrix object/indirect **noun** — an adnominal infinitive), the implicit subject
is bound to the **matrix subject (the bearer)**, not the governing noun. Verb-control infinitives
(subordinate governed by the predicate — "I want to run", "I told her to go") are unchanged and keep
standard subject/object control. Call site passes `ownerRef=reference`.

**Expected:** "the cat has no ability to roar" → `(the cat has no ability) ... (cat roar)`, with the
matrix clause additionally `negated` (the "no" determiner — Decision 1). "I want to run" still →
`tokeniko/I run` (regression preserved).

### 3a. Relative-clause matrix-subject mis-binding — **ANALYZED, NOT shipped (no safe blind fix)**
**Quirk (reported):** "the man who loves Mary runs" → "...(Mary run)" (matrix verb bound to the
nearest noun, not "man").

**Analysis:** At the **compiler** level the binding is already correct — `parser_parseSentence`
selects the matrix `nsubj` ("man") from the *root's direct children*, and
`compiler_resolveRelative` only rewrites the relative pronoun ("who"→"man") inside the relative
clause; it never touches the matrix subject. So the mis-binding, if reproduced, originates in the
**Stanza dependency parse / `parser.py` root+nsubj selection** (e.g. the matrix verb attaching as the
relative clause, or "Mary" surfacing as the root's nsubj), which I could **not observe** because the
sandbox blocked running the pipeline. Shipping a blind `parser.py` change risks regressing the clean
relative-clause cases (explicitly forbidden by the guardrails), so 3a is left **unmodified** with
this documented analysis. **Next step:** run `doc/_phase0_regression.py`, read the actual dependency
parse for this sentence (`parser_diagram` / `nlp_stanza` dep labels), and target the exact
attachment — the fix belongs at root/nsubj selection in `parser_parseSentence`, not in the flat
compiler.

---

## Mechanical items

- **Gloss/fragment normalization helper — added.** `lib/core/utilities.py`:
  `util_normalizeGloss(word, gloss)` wraps a bare gloss fragment into `"a <word> is <gloss>"`
  (strips a leading article on `word`, picks `a`/`an` by vowel heuristic) so Phase-1 ingestion can
  parse glosses as clean defining clauses. Helper only — no ingestion here.
- **Stray `@-1,0,0` spacetime artifact in `decompiler_raw` — NOT touched.** It is a degenerate-axis
  *normalization* artifact (a lone entity normalized to -1 on a space axis), not a pure decompiler
  formatting bug; a safe fix means adjusting `c_spacetime` normalization for single-entity scenes,
  which risks regressions and is deferred. Noted as remaining.

---

## Files touched (summary)
- `lib/core/tkzip.py`, `lib/core/tkllc.py` — `negated` scalar field (Decision 1).
- `lib/llc/constants.py` — negation markers, negative quantifiers, comparison affirmatives.
- `lib/llc/compiler/c_statements.py` — negation + comparison-polarity detection; set `negated`.
- `lib/llc/compiler/c_zip.py` — carry `negated`; skip negation markers in vector fusion.
- `lib/llc/evaluator/e_truth.py` — flip grounded truth on `negated`.
- `lib/llc/utils.py` (formerly `lib/tkll/functions.py`) — `utils_antonyms` (column read) + `utils_isAntonymOf` (Decision 2).
- `lib/llc/compiler/c_subordinates.py` — noun-complement infinitive bearer binding (Decision 3b).
- `lib/core/utilities.py` — `util_normalizeGloss` (Phase-1 helper).
- `doc/_phase0_regression.py` — runnable before/after probe (NEW).

## Remaining gaps / TODOs
1. **Decision 3a** (relative-clause matrix-subject) — needs the live dependency parse; fix in
   `parser.py` root/nsubj selection. (analyzed, not shipped)
2. **Negative quantifiers** — rewrite "nobody"→generic person/thing (flagged today only).
3. **Geometric negation-awareness** in `evaluator_compareContent` — Phase 3.
4. **Intrinsic comparison grounding** `compare(subject, indirect)` — Phase 3.
5. **`@-1,0,0` spacetime artifact** — single-entity normalization tidy.
6. **Live verification** — re-run `doc/_phase0_regression.py` in an environment that permits
   executing the venv interpreter; confirm the negation cos→truth numbers and Decision 2/3b raws.

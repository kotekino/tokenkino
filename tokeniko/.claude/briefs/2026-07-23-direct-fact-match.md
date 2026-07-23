# BRIEF: the direct fact-match — §2's two grounding leads closed by one primitive

> Work order for the 1st Officier. Design approved by the author 2026-07-23 (all four forks
> ruled — see "The rulings"). `CLAUDE.md` is law. DO NOT commit.

## The two live specimens (the leads, roadmap §2)

1. **Negated property vs stored affirmative fact**: «tokeniko you do not learn» grounded
   UNKNOWN, not FALSE — the self-axiom «I learn» never refuted the negated claim, so the
   belief-grounded speakup never got its live cue.
2. **Polar question misses a direct theorem**: «is gold beautiful?» → IDK despite the ACTIVE
   theorem «gold is beautiful» (the geometric `relationMatch` sees it; the polar verdict never
   consults it).

Shared root: the evaluator has NO direct fact-consultation — a claim is never compared
key-for-key against stored single-clause knowledge. `role_key` (landed 2026-07-23, `e_keys.py`)
makes the key identity-aware, so the cure is now buildable.

## The rulings (closed — do not reopen)

1. **Exact conclusion-key match, not geometry.** The claim's key = role_key(subject) +
   role_key(predicate) + role_key(direct) + the NEGATED flag; look it up among active
   axiom/theorem zips whose (single-clause) leaf carries the same role keys. Same polarity ⇒
   CONFIRMS; opposite polarity ⇒ REFUTES, citing the fact. The geometric `_best_match` stays
   byte-identical, untouched.
2. **Confidence = the matched fact's trust. NO new threshold/knob.** A refutation resting on a
   low-trust row speaks softly by construction (verdict-confidence scaling downstream is
   already in place). Derivation cites the fact (its original + kind + trust).
3. **v1 = single-clause claims only** (same scope discipline as the reductio prover's v1). A
   multi-clause claim skips the direct match — the existing machinery handles it as today.
4. **Home: the evaluator package** (DB-agnostic — works over the INJECTED axiom/theorem zips;
   suggested: a small `e_facts.py` beside `e_keys.py`, or extend `e_statement` — your
   latitude). The harness threads nothing new: it already passes the zips.

## The two consumers

- **Assertion grounding** (`evaluator_evaluateStatement`, `e_statement.py`): when the normal
  grounding leaves a single-clause claim unresolved/insufficient, consult the direct match —
  an opposite-polarity fact grounds it RESOLVED with truth ≈ (1 − extremity) i.e. a refutation
  (truth low, confidence = fact trust), a same-polarity fact corroborates (truth high). The
  derivation carries the cited fact so the speakup has its evidence. Mind the existing
  abstention post-passes: the direct match must run where it doesn't get washed back to
  insufficient.
- **The polar path** (`evaluation_harness.answer_zip` / `_polar_answer`): order becomes
  grounded-RESOLVED first (unchanged) → **direct match** (YES/NO, confidence = fact trust) →
  the reductio prover (unchanged, still the last resort) → honest IDK.

## Scope fence

- IN: the primitive + the two consumers + tests.
- OUT: `_best_match`/geometry (untouched) · the reductio prover (untouched; only its ORDER
  relative to the new step in answer_zip as above) · wh-solving (already cured) ·
  multi-clause direct matching · any API/service/parser/compiler change.
- Negation symmetry IS in scope: a stored NEGATED fact must also refute an affirmative claim
  (and confirm a negated one) — the key comparison is polarity-aware both ways.
- Attitude-wrapped clauses (THAT / "I believe…") are NOT direct-matchable — the wrapped content
  is not an assertion; skip them (guard on the leaf's operator context if needed).

## Where to look

- `lib/llc/evaluator/e_keys.py` — `role_key` (this week's primitive; your foundation).
- `lib/core/evaluation_harness.py` — `conclusion_key` (the existing dedup key discipline —
  study it; your key should agree with its identity-first spirit), `answer_zip`,
  `_polar_answer`, `_try_reductio_answer` (the ordering).
- `lib/llc/evaluator/e_statement.py` — `evaluator_evaluateStatement`, `_best_match`, the
  grounding-floor post-passes (where abstention is enforced — place the direct match correctly
  relative to them).
- `tests/test_identity_blindness.py` (this week's file — fixture style for evaluator tests),
  `tests/test_reductio_loop.py` (the polar-answer test patterns).

## Acceptance

- New tests (`tests/test_direct_fact_match.py`, sibling style): the two live specimens as
  regression — «tokeniko does not learn» grounds FALSE against a stored «I learn» (identity
  subject!) with the fact cited in the derivation · «is gold beautiful?» → YES (confidence =
  the theorem's trust) · negation symmetry both ways · low-trust fact ⇒ low-confidence verdict
  (no threshold) · multi-clause claim skips (regression: behavior unchanged) · no-match stays
  honest IDK · reductio still reachable when no direct match exists.
- Full gate green (`PYTHONPATH=. ../.venv/bin/python -m pytest tests/ -q`, FOREGROUND,
  `pgrep -f pytest` first): all passed, 1 xfailed is the norm.
- Working tree left dirty (NO commit); daemons stay OFF; docs untouched (QM reconciles).
- Standing report: outcome / files+whys / gate verbatim / deviations / findings.

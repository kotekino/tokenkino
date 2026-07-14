"""Known limitations — tracked as xfail (not red builds).

These encode genuine current gaps so a future fix turns them green (xpass) and surfaces the win,
rather than silently passing. strict=False: an xpass is reported, not a failure.
"""
import pytest

from tests.asserts import assert_resolved_true


# PROMOTED from xfail 2026-07-14 (the WSD selection fixes): the Lesk self-mention exclusion +
# recompiled fixtures put the "birds have feathers" rule on the sense robin disambiguates under —
# the rule fires, the syllogism resolves TRUE. Stays here as the healed gap's regression guard.
def test_robin_has_feathers(evaluate):
    assert_resolved_true(evaluate("a robin has feathers"))


@pytest.mark.xfail(
    reason="stanza does not tag a bare-copular wh-word as PronType=Int without the '?' ('who is "
           "happy' -> who has EMPTY morph; the aux-inverted 'when do you sleep' IS tagged). The "
           "interrogative detector keys on PronType=Int, so the '?'-less bare-copular question "
           "reads as a statement. Surfaced 2026-07-13 while fixing the wh-position bug (R5 — the "
           "fix itself is sound: root-attachment gating, tests/test_wh_position.py). A fix means "
           "a second detection signal (e.g. sentence-initial wh-lemma at the root + copular "
           "inversion) — design it deliberately, not as a patch.",
    strict=False,
)
def test_bare_copular_wh_question_without_mark(compile_zip, leaves):
    zp = compile_zip("who is happy")
    lvs = leaves(zp)
    assert all(l.dubitative == 1.0 for l in lvs)

"""Known limitations — tracked as xfail (not red builds).

These encode genuine current gaps so a future fix turns them green (xpass) and surfaces the win,
rather than silently passing. strict=False: an xpass is reported, not a failure.
"""
import pytest

from tests.asserts import assert_resolved_true


@pytest.mark.xfail(
    reason="WSD-gated: the 'birds have feathers' universal rule keys on a bird-class sense that "
           "the specific 'robin' is NOT disambiguated under, so the rule does not fire for robin. "
           "OBSERVED actual behavior (2026-06): the evaluator does NOT return "
           "insufficient_knowledge — it returns status='resolved' with truth~0.12 (a near-FALSE "
           "verdict, empty derivation), i.e. a confidently-wrong answer rather than an honest "
           "abstention. Either fix (rule fires -> resolved/true, OR no rule -> insufficient) turns "
           "this xpass and surfaces the win.",
    strict=False,
)
def test_robin_has_feathers(evaluate):
    assert_resolved_true(evaluate("a robin has feathers"))

# ------------------------------------------------------------------------------------------------
# M2 — FACTIVE CAUSALITY: "because"/"so" = AND + the `cause` carrier (2026-07-16).
#
# «A because B» asserts THREE things: A, B, and the link — CONV betrayed the factivity twice
# (imply(0,1)=1 shrugged at a FALSE reason; the reason clause was gate-invisible, unlearnable).
# The author's approved design: full-sentence because/since → AND + cause="reason";
# so/therefore/hence conjuncts → AND + cause="result" (the new CONSECUTIVE clause type — stanza
# tags them advmod, the anchor-gated advmod-marker admits them). The link itself is carried
# UN-JUDGED (explanatory adequacy is the conditional-rule extractor arc's territory).
# Unchanged by design: root-mark FRAGMENTS stay CONV (L2 — a relation half, never a standalone
# assertion); "if" (non-factive) and "when" (a generic rule, L1a) stay CONV.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core.tk import TKOperator
from lib.core.kb_extract import _zip_leaf_items, _zip_is_asserted


def _leaves(zp):
    return [(it.op, it.content) for it in _zip_leaf_items(zp.items)]


# ---- because → AND + reason -------------------------------------------------------------------------

def test_because_coasserts_with_reason(compile_zip):
    leaves = _leaves(compile_zip("a cat runs because it is hungry"))
    assert all(op == TKOperator.AND for op, _ in leaves)
    assert any(c.cause == "reason" for _, c in leaves)
    head = leaves[0][1]
    assert head.cause is None, "only the reason half carries the link"


def test_because_negation_survives(compile_zip):
    # the reason clause keeps its own polarity under the co-assertion
    leaves = _leaves(compile_zip("a cat runs because it is not tired"))
    reason = next(c for _, c in leaves if c.cause == "reason")
    assert reason.negated is True


def test_coordinated_reason_all_leaves_marked(compile_zip):
    # «because B1 or B2» — the whole subordinate is the reason (the harvest's contradict shape)
    leaves = _leaves(compile_zip(
        "it does not contradict because a mind can be an animal or a mind can be a software"
    ))
    reasons = [c for _, c in leaves if c.cause == "reason"]
    assert len(reasons) == 2
    assert all(c.modal == "possibility" for c in reasons), "the ◇ carrier rides along"


# ---- so / therefore → AND + result ------------------------------------------------------------------

def test_so_conjunct_carries_result(compile_zip):
    leaves = _leaves(compile_zip("a cat is an animal so a cat is a creature"))
    assert all(op == TKOperator.AND for op, _ in leaves)
    assert any(c.cause == "result" for _, c in leaves)


def test_therefore_the_cogito_phrasing(compile_zip):
    # «I think, therefore I exist» — the classic phrasing now carries its consequence link
    leaves = _leaves(compile_zip("I think, therefore I exist"))
    assert all(op == TKOperator.AND for op, _ in leaves)
    assert any(c.cause == "result" for _, c in leaves)


# ---- unchanged by design ----------------------------------------------------------------------------

def test_fragment_stays_conv_no_cause(compile_zip):
    # L2 stands: a bare because-fragment is a relation HALF — non-asserted, no carrier
    zp = compile_zip("because you think")
    assert not _zip_is_asserted(zp.items)
    ops = [op for op, _ in _leaves(zp)]
    assert TKOperator.CONV in ops
    assert all(c.cause is None for _, c in _leaves(zp))


def test_if_stays_conv(compile_zip):
    # non-factive: «if B, A» asserts neither half
    ops = [op for op, _ in _leaves(compile_zip("if a cat is hungry the cat eats"))]
    assert TKOperator.CONV in ops


def test_when_stays_conv(compile_zip):
    # L1a stands: temporal "when" is a generic rule, gate-visible
    ops = [op for op, _ in _leaves(compile_zip("when a person says false he is being wrong"))]
    assert TKOperator.CONV in ops


def test_plain_and_no_cause(compile_zip):
    leaves = _leaves(compile_zip("a cat is a mammal and a dog is an animal"))
    assert all(c.cause is None for _, c in leaves)


# ---- the truth consequence (the design's point) -----------------------------------------------------

def test_false_reason_drags_the_fold(compile_zip):
    # operator-level: with AND joins, a false reason refutes the whole statement where CONV's
    # imply(0, 1) = 1 shrugged — the factive speaker committed to the reason.
    from lib.llc.evaluator.operators import operator_truth
    leaves = _leaves(compile_zip("a cat runs because it is hungry"))
    assert all(op == TKOperator.AND for op, _ in leaves)
    truth = 1.0  # main clause true
    for op, _ in leaves[1:]:
        truth = operator_truth(op, truth, 0.0)  # the reason grounds FALSE
    assert truth == 0.0

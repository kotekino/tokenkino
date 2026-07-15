# ------------------------------------------------------------------------------------------------
# M1 — ADVERSATIVE COORDINATION: "but" = AND + the `contrast` flag (2026-07-16).
#
# The third harvest's headline: contrastive "X but Y" compiled the second clause with op=NOT IMPLY,
# and the Gödel fold 1-imply(a,b) sent every TRUE "X but Y" to 0. The author's ruling: the asserted
# content is exactly X∧Y (his NOT(X→¬Y) reading reduces classically to the conjunction); the
# adversative nuance is IMPLICATURE — a carrier flag like `modal`, never an operator. These tests
# pin the fix on REAL compiled zips: the M1 six-pack's shapes + the no-regression set.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core.tk import TKOperator
from lib.core.kb_extract import _zip_leaf_items


def _leaf_items(zip_):
    """(op, content) per leaf clause, via the canonical wrapper traversal (kb_extract)."""
    return [(it.op, it.content) for it in _zip_leaf_items(zip_.items)]


# ---- the M1 signature: "but" joins as AND, contrast flagged, negation intact ----------------------

def test_but_compiles_and_with_contrast(compile_zip):
    # the harvest's own specimen: «a calculator is a software but a calculator is not a mind»
    leaves = _leaf_items(compile_zip("a cat is a mammal but a cat is not a dog"))
    assert len(leaves) == 2
    ops = [op for op, _ in leaves]
    assert TKOperator.NOTIMPLY not in ops, "the adversative must never be an implication"
    assert all(op == TKOperator.AND for op in ops)
    head, conj = leaves[0][1], leaves[1][1]
    assert head.contrast is False and head.negated is False
    assert conj.contrast is True, "the adversative nuance must ride the contrast flag"
    assert conj.negated is True, "the conjunct's own negation must survive the join"


def test_true_but_sentence_no_longer_folds_false(compile_zip):
    # the author's sentence: «I am tired but I continue working» — both clauses true must fold
    # HIGH (the old NOTIMPLY(1,1)=0 sent every true "but" statement to 0). We assert the operator
    # shape (the fold is op-determined): all joins AND, so the fold of true leaves is true.
    from lib.llc.evaluator.operators import operator_truth
    leaves = _leaf_items(compile_zip("a whale is heavy but a whale is fast"))
    assert all(op == TKOperator.AND for op, _ in leaves)
    truth = 1.0
    for op, _ in leaves[1:]:
        truth = operator_truth(op, truth, 1.0)
    assert truth == 1.0


def test_but_with_modal_and_quantifier_flags_intact(compile_zip):
    # «humans are not softwares but some software can be a mind» (harvest, 07-15 10:24) —
    # the conjunct keeps its OWN quantifier + modality alongside the contrast flag
    leaves = _leaf_items(
        compile_zip("humans are not machines but some machine can be a mind")
    )
    assert all(op == TKOperator.AND for op, _ in leaves)
    conj = leaves[-1][1]
    assert conj.contrast is True
    assert conj.modal == "possibility", "the ◇ carrier must survive the adversative join"
    assert leaves[0][1].negated is True, "the head clause's negation is its own"


# ---- no-regression: the other joins are untouched --------------------------------------------------

def test_plain_and_never_contrast(compile_zip):
    leaves = _leaf_items(compile_zip("a cat is a mammal and a dog is an animal"))
    assert all(op == TKOperator.AND for op, _ in leaves)
    assert all(c.contrast is False for _, c in leaves)


def test_or_join_untouched(compile_zip):
    leaves = _leaf_items(compile_zip("a cat is a mammal or a cat is a reptile"))
    assert any(op == TKOperator.OR for op, _ in leaves)
    assert all(c.contrast is False for _, c in leaves)


# ---- the anchor layer: exact hits + the operators table --------------------------------------------

def test_contrast_anchor_membership():
    from lib.llc.anchors import anchor_resolve
    for w in ("but", "however", "yet", "nevertheless", "though", "whereas"):
        assert anchor_resolve(w, "contrast") is True, w
    for w in ("and", "or", "also", "moreover", "therefore"):
        assert bool(anchor_resolve(w, "contrast")) is False, w


def test_but_resolves_to_and_operator():
    from lib.llc.anchors import anchor_resolve
    assert anchor_resolve("but", "operators") == TKOperator.AND
    assert anchor_resolve("however", "operators") == TKOperator.AND
    assert anchor_resolve("so", "operators") == TKOperator.IMPLY  # conclusives untouched
    assert anchor_resolve("or", "operators") == TKOperator.OR

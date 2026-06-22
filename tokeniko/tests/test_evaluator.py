"""Evaluator layer contract — VERDICT BANDS against the seeded KB.

Asserts status + truth band (and, where stated, the presence of a derivation chain) — never an
exact float. Depends on the seeded definitions/axioms/relations being present.
"""
import pytest

from tests.asserts import (
    assert_resolved_true,
    assert_resolved_false,
    assert_insufficient,
    assert_inconsistent,
)


def test_cat_is_a_mammal(evaluate):
    assert_resolved_true(evaluate("a cat is a mammal"))


def test_cat_eats_meat_has_derivation(evaluate):
    r = evaluate("a cat eats meat")
    assert_resolved_true(r)
    assert len(r.derivation) > 0, r.derivation


def test_cat_does_not_eat_meat(evaluate):
    assert_resolved_false(evaluate("a cat does not eat meat"))


def test_mari_is_mortal_syllogism(evaluate):
    # Mari-is-a-human fact + all-humans-mortal rule => Mari is mortal.
    assert_resolved_true(evaluate("Mari is mortal"))


def test_mari_exists_two_hop(evaluate):
    assert_resolved_true(evaluate("Mari exists"))


def test_alive_and_dead_inconsistent(evaluate):
    assert_inconsistent(evaluate("the cat is alive and the cat is dead"))


def test_non_self_identity_inconsistent(evaluate):
    assert_inconsistent(evaluate("a thing is not equal to itself"))


def test_gibberish_insufficient(evaluate):
    # the #16 fix: gibberish subject -> insufficient (neutral), never a confident verdict.
    assert_insufficient(evaluate("Sgriodnsktj exists"))


def test_novel_words_insufficient(evaluate):
    assert_insufficient(evaluate("a wug is a blicket"))


# --- questions (P2): a question is ANSWERED, not asserted -------------------------------------

def test_polar_inconsistent_is_loud_no(answer):
    # a self-contradictory polar question -> a confident NO (logic-is-sacred), conf 1.0.
    a = answer("the cat is alive and the cat is not alive?")
    assert a.kind.value == "polar" and a.verdict.value == "no"
    assert a.confidence == 1.0


def test_polar_true_is_yes(answer):
    a = answer("is a cat a mammal?")
    assert a.kind.value == "polar" and a.verdict.value == "yes"


def test_polar_false_is_no(answer):
    a = answer("is a cat a fish?")
    assert a.kind.value == "polar" and a.verdict.value == "no"


def test_wh_what_solves_a_value(answer):
    # "what is a cat?" -> a wh VALUE (the is_a hypernym). band: a non-empty value, not the exact word.
    a = answer("what is a cat?")
    assert a.kind.value == "wh" and a.verdict.value == "value"
    assert a.value


def test_wh_unsupported_is_unknown(answer):
    # an answerable-later wh-type abstains honestly rather than fabricating.
    a = answer("how do you feel?")
    assert a.kind.value == "wh" and a.verdict.value == "unknown"


def test_declarative_is_not_answered(answer):
    # a statement is not a question: answer_zip returns None (the brain uses the assertion path).
    assert answer("a cat is a mammal") is None

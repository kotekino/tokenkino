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

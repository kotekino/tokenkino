"""Compiler layer contract — COMPILE-ONLY, evaluator-independent.

Asserts the structural facts the compiler is responsible for (flags, key presence, quantifier enum,
leaf count, identity uid prefix) — NOT the exact sense strings (WSD drifts) and NOT any truth value.
"""
import pytest


def _first_leaf(compile_zip, leaves, sentence):
    return leaves(compile_zip(sentence))[0]


def test_known_clause_is_known_with_senses(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "a cat is a mammal")
    assert leaf.unknown is False
    assert "subject" in leaf.senses
    assert "predicate" in leaf.senses


def test_gibberish_subject_is_unknown(compile_zip, leaves):
    # the #16 fix: an OOV gibberish token must mark the clause unknown (no silent grounding).
    leaf = _first_leaf(compile_zip, leaves, "Sgriodnsktj exists")
    assert leaf.unknown is True


def test_novel_words_are_unknown(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "a wug is a blicket")
    assert leaf.unknown is True


def test_named_individual_mints_identity(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "Mari is happy")
    assert leaf.unknown is False
    assert leaf.identities.get("subject", "").startswith("mari@")


def test_universal_quantifier(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "all carnivores eat meat")
    assert leaf.quantifier.value == "universal"
    assert "subject" in leaf.senses
    assert "predicate" in leaf.senses


def test_conjunction_yields_two_leaves(compile_zip, leaves):
    zp = compile_zip("the cat is alive and the cat is dead")
    assert len(leaves(zp)) == 2


def test_reflexive_identity_flag(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "a thing is equal to itself")
    assert leaf.reflexive is True


def test_negation_flag(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "the cat is not alive")
    assert leaf.negated is True

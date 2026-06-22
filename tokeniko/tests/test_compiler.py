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


def test_declarative_is_not_a_question(compile_zip, leaves):
    # a statement must NOT be flagged interrogative: dubitative stays at its non-question default,
    # wh_role None. (the assertion path must be untouched by the questions work.)
    leaf = _first_leaf(compile_zip, leaves, "a cat is a mammal")
    assert leaf.dubitative != 1.0
    assert leaf.wh_role is None


def test_polar_question_flags_all_leaves(compile_zip, leaves):
    # a polar question: dubitative=1 on EVERY leaf (mood is a whole-utterance property), wh_role None.
    lvs = leaves(compile_zip("the cat is dead and alive?"))
    assert len(lvs) >= 2
    assert all(l.dubitative == 1.0 for l in lvs)
    assert all(l.wh_role is None for l in lvs)


def test_wh_question_gap_role(compile_zip, leaves):
    # a wh-question: dubitative=1 and the wh-word's gap role is captured (what -> predicate).
    leaf = _first_leaf(compile_zip, leaves, "what is a cat?")
    assert leaf.dubitative == 1.0
    assert leaf.wh_role is not None and leaf.wh_role.value == "predicate"


def test_wh_question_subject_gap(compile_zip, leaves):
    leaf = _first_leaf(compile_zip, leaves, "who is happy?")
    assert leaf.wh_role is not None and leaf.wh_role.value == "subject"


def test_aux_resolving_to_generic_does_not_crash(compile_zip, leaves):
    # regression: an aux in a malformed embedded clause ("...know how are you") resolves to a
    # TKGeneric (no .vector) — the parser used to read .vector unguarded and crash /input with
    # AttributeError. It must now compile cleanly (empty aux vector). Structure-only; no float/sense.
    zp = compile_zip("I would like to know how are you")
    assert len(leaves(zp)) >= 1

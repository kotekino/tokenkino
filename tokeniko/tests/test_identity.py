"""Identity layer contract — geometric compareContent + demonstrable entity-linking.

compareContent: a fuzzy similarity in [0,1]. Two clauses about DIFFERENT individuals must score
lower than two identical clauses. sameIndividual: same uid -> True, different -> False.
"""
import pytest

from lib.llc.evaluator.e_compare import evaluator_compareContent
from lib.llc.evaluator import evaluator_sameIndividual


@pytest.fixture(scope="session")
def leaf(compile_zip, leaves):
    def _leaf(sentence):
        return leaves(compile_zip(sentence))[0]
    return _leaf


def test_different_individuals_compare_lower(leaf):
    score = evaluator_compareContent(leaf("Mari is happy"), leaf("Luca is happy"))
    assert score < 0.75, score


def test_identical_clause_compares_high(leaf):
    score = evaluator_compareContent(leaf("Mari is happy"), leaf("Mari is happy"))
    assert score > 0.95, score


def test_same_individual_true(leaf):
    assert evaluator_sameIndividual(leaf("Mari is happy"), leaf("Mari is sad")) is True


def test_different_individual_false(leaf):
    assert evaluator_sameIndividual(leaf("Mari is happy"), leaf("Luca is happy")) is False

"""Creation guard contract — the REJECT path (logic-is-sacred).

A statement whose logical FORM is a contradiction must be rejected at create() BEFORE any insert,
so the KB is never mutated. We only test the reject path: testing the SUCCESS path would write a
real row into the seeded KB.
"""
import pytest

from api.services import AxiomService
from api.services.validation import InconsistentStatementError


@pytest.fixture(scope="session")
def axiom_service(_io):
    tok, ai = _io
    return AxiomService(tok, ai)


def test_reject_self_inequality(axiom_service):
    with pytest.raises(InconsistentStatementError):
        axiom_service.create("a thing is not equal to itself")


def test_reject_contrary_predicates(axiom_service):
    with pytest.raises(InconsistentStatementError):
        axiom_service.create("the cat is alive and the cat is dead")

# --------------------------------------------------------------
# services: shared validation — the CONTRADICTION CREATION GUARD.
# A trusted statement (axiom / definition / theorem) whose logical FORM is a contradiction (folds to 0
# under every crisp assignment — X∧¬X, a≠a, antonym-predicate "alive and dead") can never be trusted
# knowledge (logic-is-sacred), so it is rejected at create/patch/replace — NOT inside compile_fields
# (so the recompile utility never chokes on a pre-existing bad row).
# Tautologies ("a thing is equal to itself") and contingent statements (the normal case) are allowed.
# --------------------------------------------------------------
from typing import Callable

from lib.llc.evaluator import evaluator_classifyForm
from lib.core.models import TKRelationDoc
from lib.core.tkzip import TKZip


# --- domain error (mapped by the API layer onto HTTP 422) ---
class InconsistentStatementError(Exception):
    """The statement's logical form is a contradiction (false under every assignment)."""

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail

    def __str__(self) -> str:
        return self.detail


# the antonym reader: antonyms(sense) -> senses directly antonym-linked to `sense`. mirrors
# evaluation_service._make_antonym_reader; cached so repeated lookups during one classify hit memory.
def make_antonym_reader() -> Callable[[str], list[str]]:
    cache: dict[str, list[str]] = {}

    def antonyms(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "antonym"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return antonyms


# the guard: raise if the zip's logical FORM is a contradiction; allow tautologies + contingent forms.
def assert_no_contradiction(zip_obj: TKZip) -> None:
    reader = make_antonym_reader()
    form = evaluator_classifyForm(zip_obj, antonyms=reader)
    if form.contradiction:
        raise InconsistentStatementError(form.detail or "statement is a logical contradiction")

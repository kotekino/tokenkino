"""Sense-pinned materialize (the NL round-trip fix, 2026-07-09 soak).

The wondering derives a conclusion SYMBOLICALLY (exact senses, from the proof), renders it to NL,
and materialize re-parses that NL — a lossy round-trip: «a budget stores information» parses
"stores" as the plural NOUN (shop), losing the subject; every "X stores information" then collapses
onto one degenerate dedup key and the wondering spins forever re-deriving into the void. The fix:
the brain sends the conclusion's senses; the service pins them into the compiled zip (sense + 2925
vector) BEFORE dedup/store — the derivation's senses are the truth, the NL is only its surface.

Runs against the sandbox memory DB (conftest) through the REAL compile pipeline.
"""
import pytest

from lib.core.memory import MEMProvenance


@pytest.fixture()
def theorem_service(_io):
    from api.services import TheoremService
    tok, ai = _io
    return TheoremService(tok, ai)


@pytest.fixture()
def cleanup(_io):
    made = []
    yield made
    from lib.core.models import TKTheoremDoc
    for t in made:
        fresh = TKTheoremDoc.get(t.id).run()
        if fresh is not None:
            fresh.delete()


def _prov():
    return MEMProvenance(premises=["p|is_a|q"], chain="chain: synthetic", derived_by="wondering")


def test_degenerate_renders_no_longer_collide(theorem_service, cleanup):
    # both render with 3sg "stores" (parses as the noun 'shop'); without the pin they collapse
    # onto one degenerate key and the second dedups onto the first. With the pin: two theorems.
    t1 = theorem_service.materialize(
        "a budget stores information", _prov(), trusted=0.3,
        senses={"subject": "budget.n.01", "predicate": "store.v.01", "object": "information.n.01"})
    cleanup.append(t1)
    t2 = theorem_service.materialize(
        "a cash stores information", _prov(), trusted=0.3,
        senses={"subject": "cash.n.01", "predicate": "store.v.01", "object": "information.n.01"})
    cleanup.append(t2)
    assert t1.id != t2.id, "distinct conclusions must store as distinct theorems"


def test_pinned_senses_land_in_the_zip(theorem_service, cleanup):
    from lib.core.evaluation_harness import _zip_leaves
    t = theorem_service.materialize(
        "a coin stores information", _prov(), trusted=0.3,
        senses={"subject": "coin.n.01", "predicate": "store.v.01", "object": "information.n.01"})
    cleanup.append(t)
    leaves = _zip_leaves(t.zip.items)
    assert any((lf.senses or {}).get("subject") == "coin.n.01" for lf in leaves)
    assert any((lf.senses or {}).get("predicate") == "store.v.01" for lf in leaves)


def test_true_dedup_still_converges(theorem_service, cleanup):
    senses = {"subject": "fund.n.01", "predicate": "store.v.01", "object": "information.n.01"}
    t1 = theorem_service.materialize("a fund stores information", _prov(), trusted=0.3, senses=senses)
    cleanup.append(t1)
    t2 = theorem_service.materialize("a fund stores information", _prov(), trusted=0.3, senses=senses)
    assert t1.id == t2.id, "the same conclusion must dedup onto the held theorem"

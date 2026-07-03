"""Transitive cascade revocation (Brain v1.1 step 3) — the provenance net.

Synthetic three-generation descent in the SANDBOX memory DB (conftest points Bunnet at
<memory>_test): AX (a fake axiom id) -> T1 -> T2 -> T3, where each child's provenance cites its
parent. Revoking AX must take the whole line down — dry-run reports without writing, real run
archives all three. Docs are zip-less (the cascade reads only provenance) and cleaned up per test.
"""
import pytest

from lib.core.memory import MEMChannels, MEMProvenance


_FAKE_AXIOM = "5f00000000000000000000aa"  # never a real doc — just a premise key


@pytest.fixture()
def descent(_io):
    from lib.core.models import TKTheoremDoc

    def _mk(original, premises):
        return TKTheoremDoc(
            original=original,
            sourceId="prov-test",
            channel=MEMChannels.INTERNAL,
            archived=False,
            provenance=MEMProvenance(premises=premises, chain="chain: synthetic"),
        ).insert()

    t1 = _mk("__prov_t1", [_FAKE_AXIOM])
    t2 = _mk("__prov_t2", [str(t1.id), "extra|is_a|key"])
    t3 = _mk("__prov_t3", [str(t2.id)])
    yield t1, t2, t3
    for t in (t1, t2, t3):
        fresh = TKTheoremDoc.get(t.id).run()
        if fresh is not None:
            fresh.delete()


def test_cascade_dry_run_reports_without_writing(descent):
    from lib.core.evaluation_harness import revoke_dependents
    from lib.core.models import TKTheoremDoc

    found = revoke_dependents([_FAKE_AXIOM], dry_run=True)
    assert {t.original for t in found} == {"__prov_t1", "__prov_t2", "__prov_t3"}
    # dry-run wrote nothing: all three still active in the DB
    for t in descent:
        assert TKTheoremDoc.get(t.id).run().archived is False


def test_cascade_archives_the_whole_descent(descent):
    from lib.core.evaluation_harness import revoke_dependents
    from lib.core.models import TKTheoremDoc

    archived = revoke_dependents([_FAKE_AXIOM], dry_run=False)
    assert {t.original for t in archived} == {"__prov_t1", "__prov_t2", "__prov_t3"}
    for t in descent:
        fresh = TKTheoremDoc.get(t.id).run()
        assert fresh.archived is True
        assert fresh.archivedAt is not None


def test_cascade_from_mid_generation_spares_the_ancestor(descent):
    from lib.core.evaluation_harness import revoke_dependents
    from lib.core.models import TKTheoremDoc

    t1, t2, t3 = descent
    archived = revoke_dependents([str(t2.id)], dry_run=False)
    assert {t.original for t in archived} == {"__prov_t3"}
    assert TKTheoremDoc.get(t1.id).run().archived is False
    assert TKTheoremDoc.get(t2.id).run().archived is False  # the premise itself is the caller's to archive

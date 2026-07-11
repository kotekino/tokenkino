"""Trust ledger P3 — the teaching channel (tier-1) + the doc-id resolution fix. Sandbox memory DB.

A trusted soul's novel (eval:unknown) assertion materializes as a TAUGHT theorem at
min(teacher_trust, 0.9) with the "taught:<uid>" revocation premise; below the bar it stays
remembered-not-believed; unknown vocabulary never becomes knowledge. resolve_canonical accepts
BOTH currencies (uid and stakeholder doc id — memory items carry the doc id in sourceId).
"""
import pytest

from lib.core.memory import MEMChannels, TrustEpisodeKind
from lib.core.tkzip import TKZip, TKZipItem, TKZipContent


_TEACHER = "p3-hellen@discord:7"


def _zip(unknown=False):
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
        subject=None, predicate=None, direct=None, unknown=unknown)))


def _mk_teacher(_io, trust=0.95, imprint=False):
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc(uid=_TEACHER, name="p3-hellen", isMe=False,
                                   channel=MEMChannels.DISCORD, trust=trust,
                                   imprint=imprint).save()


def _mk_item(_io, original, source_doc_id, zip_obj=None):
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(original=original, sourceId=source_doc_id,
                           channel=MEMChannels.DISCORD, zip=zip_obj or _zip())
    item.insert()
    return item


@pytest.fixture()
def clean_p3(_io):
    from lib.core.models import (
        TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKTheoremDoc, TKTrustEpisodeDoc,
    )
    def _wipe():
        TKMemoryItemDoc.get_motor_collection().delete_many({})
        TKMemoryStakeholdersDoc.find({"uid": _TEACHER}).delete().run()
        TKTrustEpisodeDoc.find({"stakeholder_uid": _TEACHER}).delete().run()
        TKTheoremDoc.find({"original": {"$regex": "^p3:"}}).delete().run()
    _wipe()
    yield
    _wipe()


def test_trusted_teacher_materializes_a_taught_theorem(_io, clean_p3):
    from brain.thinking import materialize_taught
    from lib.core.models import TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "p3: wisdom begins in wonder", str(teacher.id))
    assert materialize_taught(item) is True
    thm = TKTheoremDoc.find_one({"original": "p3: wisdom begins in wonder"}).run()
    assert thm is not None and thm.archived is False
    assert thm.trusted == pytest.approx(0.9)              # min(0.95, 0.9) — capped below axioms
    assert thm.sourceId == str(teacher.id)                # tier-1: speaker-RELEVANT
    assert thm.provenance.premises == [f"taught:{_TEACHER}"]   # the revocation key
    assert thm.provenance.derived_by == "teaching"


def test_imprinted_teacher_teaches_at_the_cap(_io, clean_p3):
    from brain.thinking import materialize_taught
    from lib.core.models import TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.5, imprint=True)   # imprint overrides the stale cache
    item = _mk_item(_io, "p3: the unexamined life is not worth living", str(teacher.id))
    assert materialize_taught(item) is True
    thm = TKTheoremDoc.find_one({"original": {"$regex": "^p3: the unexamined"}}).run()
    assert thm.trusted == pytest.approx(0.9)


def test_stranger_is_remembered_not_believed(_io, clean_p3):
    from brain.thinking import materialize_taught
    from lib.core.models import TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.5)                 # a neutral stranger
    item = _mk_item(_io, "p3: stranger wisdom", str(teacher.id))
    assert materialize_taught(item) is False
    assert TKTheoremDoc.find_one({"original": "p3: stranger wisdom"}).run() is None
    # the episodic record (the memory item) exists regardless — remembered, not believed
    from lib.core.models import TKMemoryItemDoc
    assert TKMemoryItemDoc.find_one({"original": "p3: stranger wisdom"}).run() is not None


def test_unknown_vocabulary_never_becomes_knowledge(_io, clean_p3):
    from brain.thinking import materialize_taught
    teacher = _mk_teacher(_io, trust=1.0)
    item = _mk_item(_io, "p3: a wug is a blicket", str(teacher.id), zip_obj=_zip(unknown=True))
    assert materialize_taught(item) is False


def test_taught_dedups_by_original(_io, clean_p3):
    from brain.thinking import materialize_taught
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "p3: wisdom begins in wonder", str(teacher.id))
    assert materialize_taught(item) is True
    again = _mk_item(_io, "p3: wisdom begins in wonder", str(teacher.id))
    assert materialize_taught(again) is False


# ---- the P2 live-currency fix: resolution by stakeholder DOC id --------------------------------------

def test_resolve_canonical_accepts_a_doc_id(_io, clean_p3):
    from lib.core.trust import record_episode, resolve_canonical, trust_of
    teacher = _mk_teacher(_io, trust=0.5)
    doc_id = str(teacher.id)
    assert resolve_canonical(doc_id).uid == _TEACHER      # the live currency (memory sourceId)
    soul = record_episode(doc_id, TrustEpisodeKind.KICKER, source_id="m9")
    assert soul is not None
    assert trust_of(doc_id) == trust_of(_TEACHER) == pytest.approx(0.6)

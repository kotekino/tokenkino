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
    # a minimal VALID lesson leaf: the headless-teaching belt (the mammal incident, 2026-07-18)
    # refuses a leaf with no subject at all — a stand-in zip must now carry one, like any real
    # taught assertion does (the trust mechanics under test here are unaffected).
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
        subject=None, predicate=None, direct=None, unknown=unknown,
        senses={"subject": "wisdom.n.01", "predicate": "begin.v.01"})))


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
    assert materialize_taught(item) is not None
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
    assert materialize_taught(item) is not None
    thm = TKTheoremDoc.find_one({"original": {"$regex": "^p3: the unexamined"}}).run()
    assert thm.trusted == pytest.approx(0.9)


def test_stranger_is_remembered_not_believed(_io, clean_p3):
    from brain.thinking import materialize_taught
    from lib.core.models import TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.5)                 # a neutral stranger
    item = _mk_item(_io, "p3: stranger wisdom", str(teacher.id))
    assert materialize_taught(item) is None
    assert TKTheoremDoc.find_one({"original": "p3: stranger wisdom"}).run() is None
    # the episodic record (the memory item) exists regardless — remembered, not believed
    from lib.core.models import TKMemoryItemDoc
    assert TKMemoryItemDoc.find_one({"original": "p3: stranger wisdom"}).run() is not None


def test_unknown_vocabulary_never_becomes_knowledge(_io, clean_p3):
    from brain.thinking import materialize_taught
    teacher = _mk_teacher(_io, trust=1.0)
    item = _mk_item(_io, "p3: a wug is a blicket", str(teacher.id), zip_obj=_zip(unknown=True))
    assert materialize_taught(item) is None


def test_taught_dedups_by_original(_io, clean_p3):
    from brain.thinking import materialize_taught
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "p3: wisdom begins in wonder", str(teacher.id))
    assert materialize_taught(item) is not None
    again = _mk_item(_io, "p3: wisdom begins in wonder", str(teacher.id))
    assert materialize_taught(again) is None


# ---- the P2 live-currency fix: resolution by stakeholder DOC id --------------------------------------

def test_resolve_canonical_accepts_a_doc_id(_io, clean_p3):
    from lib.core.trust import record_episode, resolve_canonical, trust_of
    teacher = _mk_teacher(_io, trust=0.5)
    doc_id = str(teacher.id)
    assert resolve_canonical(doc_id).uid == _TEACHER      # the live currency (memory sourceId)
    soul = record_episode(doc_id, TrustEpisodeKind.KICKER, source_id="m9")
    assert soul is not None
    assert trust_of(doc_id) == trust_of(_TEACHER) == pytest.approx(0.6)


# ---- survey slice 3: the B-wire (teachability as personality) + the curiosity ask ----------------

@pytest.fixture()
def bwire_world(_io, clean_p3):
    """The two slice-3 rules + the topic ask scaffold (the sandbox store is empty by default —
    the fallback ask_more carries no {topic} slot) + a trusted teacher. Swept on both edges."""
    from lib.core.memory import EvalToken, TokenikoAction
    from lib.core.models import TKActionDoc, TKBehaviorRuleDoc, TKIdeaDoc, TKScaffoldDoc
    rules = [
        TKBehaviorRuleDoc(trigger=EvalToken.NOVEL.value,
                          action=TokenikoAction.LEARN.value, urge=0.75),
        TKBehaviorRuleDoc(trigger=EvalToken.LEARNED.value,
                          action=TokenikoAction.ASK.value, urge=0.6),
    ]
    for r in rules:
        r.insert()
    scaffold = TKScaffoldDoc(category="ask_more", template="why is it that «{topic}»?",
                             slots=["topic"], weight=100.0)
    scaffold.insert()
    teacher = _mk_teacher(_io, trust=0.95)
    yield {"teacher": teacher}
    scaffold.delete()
    TKBehaviorRuleDoc.get_motor_collection().delete_many(
        {"trigger": {"$in": [EvalToken.NOVEL.value, EvalToken.LEARNED.value]}})
    TKIdeaDoc.get_motor_collection().delete_many(
        {"trigger": {"$in": [EvalToken.NOVEL.value, EvalToken.LEARNED.value]}})
    TKActionDoc.get_motor_collection().delete_many(
        {"payload.action_token": {"$in": [TokenikoAction.LEARN.value, TokenikoAction.ASK.value]}})


def test_the_bwire_circle(bwire_world):
    """The whole wire through the REAL components: candidate -> eval:novel idea -> plan/dispatch
    (learn, INTERNAL) -> the executor mints -> eval:learned (topic) -> the ask plan carries the
    topic-slotted question, threaded at the teacher."""
    from brain import behavior
    from brain import main as brain_main
    from brain.thinking import _taught_candidate
    from lib.core.memory import EvalToken, TokenikoAction
    from lib.core.models import TKIdeaDoc, TKTheoremDoc
    import json

    teacher = bwire_world["teacher"]
    # metadata must ride the INSERT (memory is a timeseries — .save() is a findAndModify, forbidden)
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(original="p3: every dolphin dreams", sourceId=str(teacher.id),
                           channel=MEMChannels.DISCORD, zip=_zip(),
                           metadata=json.dumps({"channel_id": "777", "message_id": "msg-1"}))
    item.insert()

    # 1. the decision site: teachable -> eval:novel (the mint does NOT happen here — the B-wire)
    assert _taught_candidate(item) is not None
    ideas = behavior.spawn_ideas_for(EvalToken.NOVEL.value, payload=item.zip,
                                     source=str(item.id), target=item.sourceId)
    assert len(ideas) == 1 and ideas[0].action_token == TokenikoAction.LEARN.value
    assert TKTheoremDoc.find_one({"original": "p3: every dolphin dreams"}).run() is None

    # 2. plan + dispatch: INTERNAL, self-targeted, the lesson's memory id in the payload
    plan = behavior.plan_action(ideas[0], "tokeniko-uid")
    assert plan is not None and plan["channel"].value == "internal"
    assert plan["payload"]["source"] == str(item.id)
    action = behavior.dispatch_action(ideas[0], "tokeniko-uid", plan)

    # 3. the executor: the mint happens HERE + the curiosity spawns with the topic
    brain_main._execute_learn(action)
    thm = TKTheoremDoc.find_one({"original": "p3: every dolphin dreams"}).run()
    assert thm is not None and thm.provenance.derived_by == "teaching"
    learned = TKIdeaDoc.find_one({"trigger": EvalToken.LEARNED.value}).run()
    assert learned is not None and learned.action_token == TokenikoAction.ASK.value
    assert learned.answer == {"topic": "p3: every dolphin dreams"}

    # 4. the curiosity ask: topic-slotted raw, threaded under the lesson at the teacher
    ask_plan = behavior.plan_action(learned, "tokeniko-uid")
    assert ask_plan is not None
    assert "p3: every dolphin dreams" in ask_plan["payload"]["raw"]
    assert ask_plan["payload"]["destination"]["channel_id"] == "777"

    # 5. re-execution is race-safe: the dedup makes the second mint an honest no-op
    brain_main._execute_learn(action)
    from lib.core.models import TKTheoremDoc as T
    assert len(T.find({"original": "p3: every dolphin dreams"}).to_list()) == 1


def test_no_learn_rule_no_learning(_io, clean_p3):
    """The personality switch: without the eval:novel rule the candidate is heard but NOTHING
    is spawned and nothing is minted — a mind that doesn't accept teaching."""
    from brain import behavior
    from brain.thinking import _taught_candidate
    from lib.core.memory import EvalToken
    from lib.core.models import TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "p3: unheard lesson", str(teacher.id))
    assert _taught_candidate(item) is not None            # teachable...
    ideas = behavior.spawn_ideas_for(EvalToken.NOVEL.value, payload=item.zip,
                                     source=str(item.id), target=item.sourceId)
    assert ideas == []                                    # ...but no rule -> no idea
    assert TKTheoremDoc.find_one({"original": "p3: unheard lesson"}).run() is None


def test_ask_throttle_one_question_per_teacher(bwire_world):
    from types import SimpleNamespace
    from brain import behavior
    from lib.core.memory import EvalToken, TokenikoAction
    from lib.core.models import TKActionDoc

    def _ask_idea():
        return SimpleNamespace(
            action_token=TokenikoAction.ASK.value, trigger=EvalToken.LEARNED.value,
            urge=0.6, source=None, answer={"topic": "p3: every dolphin dreams"},
            material=None, target="p3-hellen@discord:7", confidence=None,
        )

    plan = behavior.plan_action(_ask_idea(), "tokeniko-uid")
    assert plan is not None
    TKActionDoc(action_type=plan["action_type"], sourceId="tokeniko-uid",
                targetId=plan["target"], channel=plan["channel"],
                payload=plan["payload"]).insert()
    assert behavior.plan_action(_ask_idea(), "tokeniko-uid") is None   # the window holds

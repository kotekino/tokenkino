"""Trust ledger P2 — the meta-language wiring (senses D). Sandbox memory DB.

The trust:* trigger family spawns beside the eval reflex (own namespace, no collapse-collision);
plan_action routes trust tokens INTERNAL + speaker-targeted; Priorities exempts INTERNAL actions
from the directedness multiplication (an overheard lie still costs trust); actions_phase executes
update_trust for real (episode + refold); the verdict→episode echo mapping incl. the strong
kicker (the closed why-loop).
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from lib.core.memory import (
    ActionStatus, ActionType, EvalToken, MEMChannels, TokenikoAction, TrustEpisodeKind,
)


_SPEAKER = "p2-john@discord:9"


def _mem_insert(_io, original, source, target, minutes_ago, meta=None, directedness=1.0):
    from lib.core.models import TKMemoryItemDoc
    from lib.core.tkzip import TKZip, TKZipItem, TKZipContent
    item = TKMemoryItemDoc(
        original=original, sourceId=source, targetId=target, channel=MEMChannels.DISCORD,
        metadata=json.dumps(meta) if meta else None, directedness=directedness,
        zip=TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
            subject=None, predicate=None, direct=None))),
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    item.insert()
    return item


@pytest.fixture()
def clean_p2(_io):
    from lib.core.models import (
        TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKTrustEpisodeDoc, TKIdeaDoc,
        TKActionDoc, TKBehaviorRuleDoc,
    )
    def _wipe():
        TKMemoryItemDoc.get_motor_collection().delete_many({})
        TKMemoryStakeholdersDoc.find({"uid": _SPEAKER}).delete().run()
        TKTrustEpisodeDoc.find({"stakeholder_uid": _SPEAKER}).delete().run()
        TKIdeaDoc.find({"trigger": {"$regex": "^trust:"}}).delete().run()
        TKActionDoc.find({"action_type": ActionType.UPDATE_TRUST.value}).delete().run()
        TKBehaviorRuleDoc.find({"trigger": {"$regex": "^trust:"}}).delete().run()
    _wipe()
    yield
    _wipe()


def _seed_trust_rules():
    from lib.core.models import TKBehaviorRuleDoc
    TKBehaviorRuleDoc(trigger=TrustEpisodeKind.KICKER.value,
                      action=TokenikoAction.MORE_TRUST.value, urge=0.65).insert()
    TKBehaviorRuleDoc(trigger=TrustEpisodeKind.LOGIC_VIOLATION.value,
                      action=TokenikoAction.LESS_TRUST.value, urge=0.65).insert()


def _mk_speaker():
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc(uid=_SPEAKER, name="p2-john", isMe=False,
                                   channel=MEMChannels.DISCORD).save()


# ---- plan_action routes trust tokens INTERNAL + speaker-targeted ------------------------------------

def test_plan_action_trust_is_internal_and_speaker_targeted(_io, clean_p2):
    from brain import behavior
    from lib.core.models import TKIdeaDoc
    item = _mem_insert(_io, "the cat is dead and alive", _SPEAKER, "me", 1,
                       meta={"channel_id": "333", "message_id": "m1"})
    idea = TKIdeaDoc(trigger=TrustEpisodeKind.LOGIC_VIOLATION.value,
                     action_token=TokenikoAction.LESS_TRUST.value, urge=0.65,
                     source=str(item.id), target=_SPEAKER,
                     answer={"note": "a logic violation"})
    idea.insert()
    plan = behavior.plan_action(idea, "tokeniko-uid")
    assert plan["action_type"] == ActionType.UPDATE_TRUST
    assert plan["channel"] == MEMChannels.INTERNAL       # brain-executed, never a senses carrier
    assert plan["target"] == _SPEAKER                     # the ledger that moves is the speaker's
    assert plan["payload"]["source"] == str(item.id)      # provenance
    assert "destination" not in plan["payload"]           # nothing on the wire


# ---- Priorities: INTERNAL exempt from directedness ---------------------------------------------------

def test_priorities_internal_exempt_from_directedness(_io, clean_p2):
    import brain.main as brain_main
    from brain import behavior
    from lib.core.models import TKIdeaDoc, TKActionDoc
    _mk_speaker()
    _seed_trust_rules()
    # an OVERHEARD (0.15) logic violation: outward speakup would die (0.7 x 0.15), but the
    # trust update keeps its raw urge and must survive.
    item = _mem_insert(_io, "the cat is dead and alive", _SPEAKER, None, 1, directedness=0.15)
    ideas = behavior.spawn_ideas_for(TrustEpisodeKind.LOGIC_VIOLATION.value,
                                     payload=item.zip, source=str(item.id),
                                     answer={"note": "x"}, target=_SPEAKER)
    assert len(ideas) == 1
    brain_main._tokeniko_uid = "tokeniko-uid"
    # drain the queue (other sandbox leftovers may be pending) until OUR idea is parsed
    from bson import ObjectId
    for _ in range(20):
        kept = TKIdeaDoc.get(ObjectId(str(ideas[0].id))).run()
        if kept.parsed_by_prio:
            break
        assert brain_main.priorities_phase() is True
    assert kept.status == "done", f"discarded: urge={kept.urge} feas={kept.feasibility}"
    action = TKActionDoc.find_one({"action_type": ActionType.UPDATE_TRUST.value}).run()
    assert action is not None and action.targetId == _SPEAKER


# ---- actions_phase executes update_trust for real ----------------------------------------------------

def test_actions_phase_records_the_episode(_io, clean_p2):
    import brain.main as brain_main
    from lib.core.models import TKActionDoc, TKTrustEpisodeDoc
    from lib.core.trust import trust_of
    _mk_speaker()
    TKActionDoc(action_type=ActionType.UPDATE_TRUST, sourceId="tok", targetId=_SPEAKER,
                channel=MEMChannels.INTERNAL,
                payload={"action_token": TokenikoAction.LESS_TRUST.value,
                         "trigger": TrustEpisodeKind.LOGIC_VIOLATION.value,
                         "source": "m-src", "answer": {"note": "a logic violation"}}).insert()
    assert brain_main.actions_phase() is True
    eps = TKTrustEpisodeDoc.find({"stakeholder_uid": _SPEAKER}).to_list()
    assert len(eps) == 1 and eps[0].kind == TrustEpisodeKind.LOGIC_VIOLATION
    assert eps[0].source_id == "m-src"
    assert trust_of(_SPEAKER) == pytest.approx(0.35)      # 0.5 - 0.15, folded


# ---- the verdict -> episode echo ---------------------------------------------------------------------

def test_trust_echo_mapping(_io, clean_p2, monkeypatch):
    import brain.thinking as thinking
    monkeypatch.setattr(thinking, "_self_id", lambda: "me-id")
    item = SimpleNamespace(sourceId=_SPEAKER, timestamp=datetime.now(timezone.utc),
                           metadata=None, original="x")
    # TRUE without an open question -> agreement
    monkeypatch.setattr(thinking, "_derive_reply_context", lambda i: None)
    trig, ans = thinking._trust_echo(EvalToken.TRUE.value, item, SimpleNamespace(premises=[]))
    assert trig == TrustEpisodeKind.AGREEMENT.value
    # TRUE closing my open question -> THE KICKER
    monkeypatch.setattr(thinking, "_derive_reply_context",
                        lambda i: SimpleNamespace(original="why is that?"))
    trig, ans = thinking._trust_echo(EvalToken.TRUE.value, item, SimpleNamespace(premises=[]))
    assert trig == TrustEpisodeKind.KICKER.value
    assert "why is that?" in ans["note"]
    # FALSE -> disagreement carrying the refuted belief's trust
    monkeypatch.setattr(thinking.evaluation_harness, "_conclusion_trust", lambda p: 0.3)
    trig, ans = thinking._trust_echo(EvalToken.FALSE.value, item, SimpleNamespace(premises=["ax1"]))
    assert trig == TrustEpisodeKind.DISAGREEMENT.value and ans["belief_trust"] == 0.3
    # INCONSISTENT -> logic violation; UNKNOWN -> nothing; self-speech -> nothing
    trig, _ = thinking._trust_echo(EvalToken.INCONSISTENT.value, item, SimpleNamespace(premises=[]))
    assert trig == TrustEpisodeKind.LOGIC_VIOLATION.value
    assert thinking._trust_echo(EvalToken.UNKNOWN.value, item, SimpleNamespace(premises=[])) == (None, None)
    me_item = SimpleNamespace(sourceId="me-id", timestamp=item.timestamp, metadata=None, original="y")
    assert thinking._trust_echo(EvalToken.TRUE.value, me_item, SimpleNamespace(premises=[])) == (None, None)

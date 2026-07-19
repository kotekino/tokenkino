# ------------------------------------------------------------------------------------------------
# THE ETIQUETTE FAMILY — survey slice 4 (2026-07-19, hunch 8). A social act is RECOGNIZED, never
# evaluated: the detector at the compile seam (lib/llc/social — anchor-catch over the "social"
# category), the MEMItem carrier, the early think_one branch (_social_react: react to the room or
# to himself, stay quiet for an act naming another), fork A (content wins — the prefix strips,
# no reflex), the directedness floor, and the per-speaker throttle.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core.memory import EvalToken, MEMChannels, TokenikoAction
from lib.llc.social import SocialDetection, social_detect


# ---- the detector (exact-hit paths — no vectors needed) -----------------------------------------

@pytest.mark.parametrize("text,kind,at,remainder", [
    ("hello",                       "greeting", None,       ""),
    ("Hello!",                      "greeting", None,       ""),
    ("hello everyone",              "greeting", None,       ""),
    ("hello tokeniko",              "greeting", "tokeniko", ""),
    ("hello John",                  "greeting", "john",     ""),   # at-OTHER: recognized, quiet
    ("tokeniko, hello!",            "greeting", "tokeniko", ""),
    ("good morning",                "greeting", None,       ""),
    ("good morning everyone!",      "greeting", None,       ""),
    ("thanks",                      "thanks",   None,       ""),
    ("thank you tokeniko",          "thanks",   "tokeniko", ""),
    ("bye bye",                     "farewell", None,       ""),
    ("goodnight all",               "farewell", None,       ""),
    ("see you",                     "farewell", None,       ""),
])
def test_detector_pure_acts(text, kind, at, remainder):
    det = social_detect(text, "tokeniko")
    assert det == SocialDetection(kind, at, remainder)


def test_detector_fork_a_strips_the_prefix():
    # MIXED: content wins — the prefix strips (separator-delimited), the content compiles clean
    det = social_detect("hello tokeniko, is gold beautiful?", "tokeniko")
    assert det.kind == "greeting" and det.at == "tokeniko"
    assert det.remainder == "is gold beautiful?"
    det = social_detect("hello everyone! I just woke up", "tokeniko")
    assert det.kind == "greeting" and det.remainder == "I just woke up"


def test_detector_metalinguistic_guard():
    # NO separator after the head -> not a social prefix: the utterance flows whole
    assert social_detect("hello is a word", "tokeniko") is None


@pytest.mark.parametrize("text", [
    "gold is beautiful",
    "the cat sleeps",
    "why is the sky blue?",
    "ok",           # the 2026-07-19 measurement: «ok»->hey 0.719 — a semantic fallback would
    "yes",          # greet acknowledgments, so the category is EXACT (see _SOCIAL_BASE_ANCHORS)
    "no",
    "sure",
    "indeed!",
])
def test_detector_non_social_passthrough(text):
    assert social_detect(text, "tokeniko") is None


def test_detector_widened_table_catches_the_synonyms():
    # the anchor-catch principle yields to measurement here: EXACT with a generous table
    assert social_detect("howdy", "tokeniko").kind == "greeting"
    assert social_detect("ciao!", "tokeniko").kind == "greeting"
    assert social_detect("see ya", "tokeniko").kind == "farewell"


# ---- the reactor + the plumbing -------------------------------------------------------------------

@pytest.fixture()
def social_world(_io):
    from lib.core.models import (TKActionDoc, TKBehaviorRuleDoc, TKIdeaDoc,
                                 TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKScaffoldDoc)
    rules = [
        TKBehaviorRuleDoc(trigger=EvalToken.GREETING.value,
                          action=TokenikoAction.GREET.value, urge=0.7),
        TKBehaviorRuleDoc(trigger=EvalToken.THANKS.value,
                          action=TokenikoAction.WELCOME.value, urge=0.6),
        TKBehaviorRuleDoc(trigger=EvalToken.FAREWELL.value,
                          action=TokenikoAction.FAREWELL_BACK.value, urge=0.6),
    ]
    for r in rules:
        r.insert()
    scaffold = TKScaffoldDoc(category="greet", template="hello {name}!",
                             slots=["name"], weight=100.0)
    scaffold.insert()
    speaker = TKMemoryStakeholdersDoc(uid="waver@stest:4", name="waver", isMe=False,
                                      channel=MEMChannels.DISCORD, trust=0.5).save()
    yield {"speaker": speaker}
    scaffold.delete()
    triggers = [EvalToken.GREETING.value, EvalToken.THANKS.value, EvalToken.FAREWELL.value]
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": {"$in": triggers}})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": {"$in": triggers}})
    TKActionDoc.get_motor_collection().delete_many(
        {"payload.action_token": {"$in": [TokenikoAction.GREET.value,
                                          TokenikoAction.WELCOME.value,
                                          TokenikoAction.FAREWELL_BACK.value]}})
    TKMemoryItemDoc.get_motor_collection().delete_many({"sourceId": str(speaker.id)})
    TKMemoryStakeholdersDoc.get_motor_collection().delete_many({"uid": "waver@stest:4"})


def _social_item(speaker_id, kind, at=None, meta=True):
    import json
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(
        original="hello", zip=None, sourceId=speaker_id, channel=MEMChannels.DISCORD,
        directedness=0.6, social=kind, social_at=at,
        metadata=json.dumps({"channel_id": "555", "message_id": "m-1"}) if meta else None,
    )
    item.insert()
    return item


def test_social_react_greets_the_room(social_world):
    from brain import behavior
    from brain.thinking import _social_react
    from lib.core.models import TKIdeaDoc
    item = _social_item(str(social_world["speaker"].id), "greeting")
    assert _social_react(item) is True
    idea = TKIdeaDoc.find_one({"trigger": EvalToken.GREETING.value}).run()
    assert idea is not None and idea.action_token == TokenikoAction.GREET.value
    assert idea.answer == {"name": "waver"}
    # the plan: the warm register speaks, threaded into the room
    plan = behavior.plan_action(idea, "tokeniko-uid")
    assert plan is not None
    assert plan["payload"]["raw"] == "hello waver!"
    assert plan["payload"]["destination"]["channel_id"] == "555"
    # the floor (author's guard ruling): ambient 0.6 floored to addressed -> 0.7 x 0.9
    assert plan["payload"]["intensity"]["arousal"] == pytest.approx(0.63)


def test_social_react_stays_quiet_for_another(social_world):
    from brain.thinking import _social_react
    from lib.core.models import TKIdeaDoc
    item = _social_item(str(social_world["speaker"].id), "greeting", at="john")
    assert _social_react(item) is False
    assert TKIdeaDoc.find_one({"trigger": EvalToken.GREETING.value}).run() is None


def test_social_throttle_one_nod_per_speaker(social_world):
    from types import SimpleNamespace
    from brain import behavior
    from lib.core.models import TKActionDoc

    def _idea():
        return SimpleNamespace(
            action_token=TokenikoAction.GREET.value, trigger=EvalToken.GREETING.value,
            urge=0.7, source=None, answer=None, material=None,
            target="waver@stest:4", confidence=None,
        )

    plan = behavior.plan_action(_idea(), "tokeniko-uid")
    assert plan is not None
    TKActionDoc(action_type=plan["action_type"], sourceId="tokeniko-uid",
                targetId=plan["target"], channel=plan["channel"],
                payload=plan["payload"]).insert()
    assert behavior.plan_action(_idea(), "tokeniko-uid") is None   # the window holds


def test_social_item_is_never_evaluated(social_world):
    # the junk-path cure: think_one's early branch — a social item spawns NO why/guess/unknown
    # ideas whatever its content would have graded. Proven at the reactor level: the ONLY ideas
    # a social item can produce are its social trigger's.
    from brain.thinking import _social_react
    from lib.core.models import TKIdeaDoc
    item = _social_item(str(social_world["speaker"].id), "farewell")
    _social_react(item)
    assert TKIdeaDoc.find_one({"trigger": EvalToken.UNKNOWN.value,
                               "source": str(item.id)}).run() is None
    idea = TKIdeaDoc.find_one({"trigger": EvalToken.FAREWELL.value}).run()
    assert idea is not None and idea.action_token == TokenikoAction.FAREWELL_BACK.value

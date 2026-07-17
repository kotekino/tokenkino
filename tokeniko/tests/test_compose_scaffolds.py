# ------------------------------------------------------------------------------------------------
# Compose 2.0 slice 1 (2026-07-17 — hunch 19's first brick): the voice moves from hardwired
# strings to the scaffold store. Two layers, tested on their fault line: the ROUTER is
# deterministic (decision -> category + data — legacy parity asserted on an EMPTY store, so an
# unseeded brain speaks byte-identically to yesterday); the SHELF pick is stochastic
# (weighted-random, injectable rng) and the data binds VERBATIM (the creativity fence).
# ------------------------------------------------------------------------------------------------
import random

import pytest

from lib.core.evaluation import AnswerKind, AnswerVerdict
from lib.core.memory import EvalToken, TokenikoAction
from brain.compose import compose_raw, creative_compose, _route, _FALLBACK


# ---- the router: legacy parity on an empty store -----------------------------------------------------
# (the sandbox db has no scaffolds unless a test inserts them — these run against the fallback)

def _polar(verdict, reason=""):
    return {"kind": AnswerKind.POLAR.value, "verdict": verdict, "reason": reason}


@pytest.mark.parametrize("token,trigger,answer,expected", [
    (TokenikoAction.ANSWER.value, None, _polar(AnswerVerdict.YES.value), "yes"),
    (TokenikoAction.ANSWER.value, None, _polar(AnswerVerdict.NO.value), "no"),
    (TokenikoAction.ANSWER.value, None, _polar(AnswerVerdict.NO.value, "inconsistent question"),
     "no, that is contradictory"),
    (TokenikoAction.ANSWER.value, None, {"verdict": AnswerVerdict.UNKNOWN.value}, "I do not know"),
    (TokenikoAction.ANSWER.value, None,
     {"kind": AnswerKind.WH.value, "verdict": AnswerVerdict.VALUE.value, "value": "feline"}, "feline"),
    (TokenikoAction.ANSWER.value, None, {}, "I do not know"),        # unrecognized -> honest
    (TokenikoAction.SPEAKUP.value, EvalToken.INCONSISTENT.value, None, "no, that is contradictory"),
    (TokenikoAction.SPEAKUP.value, EvalToken.FALSE.value, None, "no, that is not true"),
    (TokenikoAction.SPEAKUP.value, None, None, "I do not agree"),
    (TokenikoAction.CLARIFY.value, None, None, "that contradicts what you said before — which holds?"),
    (TokenikoAction.ASK.value, None, None, "can you tell me more about that?"),
    (TokenikoAction.WHY.value, None, None, "why is that?"),
    (TokenikoAction.CONCEDE.value, None, {}, "you are right"),
    (TokenikoAction.CONCEDE.value, None, {"retracted": ["all software are minds"]},
     "you are right — I no longer hold that all software are minds"),
    (TokenikoAction.CONCEDE.value, None, {"weakened": "some software are minds"},
     "you are right — what remains true is that some software are minds"),
    (TokenikoAction.CONCEDE.value, None,
     {"retracted": ["all software are minds"], "weakened": "some software are minds"},
     "you are right — I no longer hold that all software are minds — "
     "what remains true is that some software are minds"),
    (TokenikoAction.POST.value, None, None, ""),                     # post: no reply text here
])
def test_router_legacy_parity(_io, token, trigger, answer, expected):
    assert compose_raw(token, trigger, answer) == expected


def test_every_routed_category_has_a_fallback():
    # the router must never name a category the fallback dict cannot speak
    routable = ["answer_yes", "answer_no", "answer_no_contradictory", "answer_idk", "answer_value",
                "speakup_inconsistent", "speakup_false", "speakup_disagree", "clarify_conflict",
                "ask_more", "why", "concede_plain", "concede_retract", "concede_weakened",
                "concede_retract_weakened"]
    assert set(routable) <= set(_FALLBACK)


# ---- the shelf: stochastic pick + the verbatim fence -------------------------------------------------

@pytest.fixture()
def why_shelf(_io):
    from lib.core.models import TKScaffoldDoc
    rows = [
        TKScaffoldDoc(category="why", template="why is that?", weight=1.0),
        TKScaffoldDoc(category="why", template="why?", weight=0.5),
        TKScaffoldDoc(category="why", template="I don't see the connection, why?", weight=0.5),
        TKScaffoldDoc(category="why", template="never spoken", weight=0.5, enabled=False),
    ]
    for r in rows:
        r.insert()
    yield [r.template for r in rows[:3]]
    for r in rows:
        r.delete()


def test_shelf_pick_is_weighted_random_and_enabled_only(why_shelf):
    rng = random.Random(42)
    seen = {creative_compose("why", rng=rng) for _ in range(60)}
    assert seen == set(why_shelf)                     # superposition: all enabled variants appear
    assert "never spoken" not in seen                 # disabled rows never speak


def test_data_binds_verbatim(_io):
    from lib.core.models import TKScaffoldDoc
    row = TKScaffoldDoc(category="concede_retract",
                        template="I retreat: {retracted}", slots=["retracted"])
    row.insert()
    try:
        text = creative_compose("concede_retract",
                                {"retracted": "ALL softwares ARE minds (sic)"},
                                rng=random.Random(1))
        # the fence: the payload lands character-for-character, never paraphrased
        assert "ALL softwares ARE minds (sic)" in text
    finally:
        row.delete()


def test_slot_gate_excludes_unsatisfiable_scaffolds(_io):
    from lib.core.models import TKScaffoldDoc
    row = TKScaffoldDoc(category="why", template="I don't understand why {topic}",
                        slots=["topic"], weight=100.0)
    row.insert()
    try:
        # the why-path carries no topic data — the slotted row is unreachable, the fallback speaks
        assert creative_compose("why", {}, rng=random.Random(1)) == "why is that?"
    finally:
        row.delete()


def test_empty_category_falls_back(_io):
    assert creative_compose("why", {}) == "why is that?"
    assert creative_compose("no_such_category", {}) == ""


# ---- the route table itself --------------------------------------------------------------------------

def test_internal_tokens_route_to_none():
    for token in (TokenikoAction.IGNORE.value, TokenikoAction.GUESS.value,
                  TokenikoAction.POST.value, TokenikoAction.RETREAT.value):
        assert _route(token, None, None) is None


# ---- slice 2: the intensity tuple (2026-07-17 — confidence gates the shelf, arousal the register) ----

def test_hedge_table_reversed_anchors():
    from brain.compose import hedge_for
    assert hedge_for(0.3) == "slightly"       # the 0.3 anchor, inverted
    assert hedge_for(0.55) == "passably"      # the 0.5 anchor, inverted
    assert hedge_for(0.9) is None             # sure enough to speak plain
    assert hedge_for(1.0) is None
    assert hedge_for(None) is None            # no signal -> no hedge


def test_verdict_confidence_formulas():
    from types import SimpleNamespace
    from brain.thinking import verdict_confidence
    # logic never hedges: INCONSISTENT is always 1.0, whatever the premises
    r = SimpleNamespace(truth=0.5, premises=["p1"])
    assert verdict_confidence(EvalToken.INCONSISTENT.value, r) == 1.0
    # FALSE: extremity × premise trust (premise-less -> trust 1.0)
    r = SimpleNamespace(truth=0.05, premises=[])
    assert verdict_confidence(EvalToken.FALSE.value, r) == pytest.approx(0.95)
    # TRUE mirrors
    r = SimpleNamespace(truth=0.9, premises=[])
    assert verdict_confidence(EvalToken.TRUE.value, r) == pytest.approx(0.9)
    # question-like reflexes carry no hedgeable content
    r = SimpleNamespace(truth=0.5, premises=[])
    assert verdict_confidence(EvalToken.UNKNOWN.value, r) is None
    assert verdict_confidence(None, r) is None


@pytest.fixture()
def banded_shelf(_io):
    from lib.core.models import TKScaffoldDoc
    rows = [
        TKScaffoldDoc(category="speakup_false", template="no, that is not true",
                      intensity_band=[0.6, 1.0]),
        TKScaffoldDoc(category="speakup_false", template="hmm, that does not seem right to me",
                      intensity_band=[0.0, 0.6]),
    ]
    for r in rows:
        r.insert()
    yield
    for r in rows:
        r.delete()


def test_confidence_band_gates_the_shelf(banded_shelf):
    rng = random.Random(7)
    high = {creative_compose("speakup_false", intensity={"confidence": 0.95}, rng=rng)
            for _ in range(20)}
    assert high == {"no, that is not true"}                       # the plain register only
    low = {creative_compose("speakup_false", intensity={"confidence": 0.3}, rng=rng)
           for _ in range(20)}
    assert low == {"hmm, that does not seem right to me"}          # the soft register only


def test_over_narrow_banding_never_mutes(banded_shelf, _io):
    from lib.core.models import TKScaffoldDoc
    # arousal band nothing satisfies -> the band-shelf empties -> the FULL shelf speaks anyway
    row = TKScaffoldDoc(category="ask_more", template="tell me everything",
                        arousal_band=[0.99, 1.0])
    row.insert()
    try:
        text = creative_compose("ask_more", intensity={"confidence": 0.5, "arousal": 0.1},
                                rng=random.Random(3))
        assert text == "tell me everything"    # never-mute: fallback to the whole shelf
    finally:
        row.delete()


def test_hedge_slot_binds_the_adverb(_io):
    from lib.core.models import TKScaffoldDoc
    row = TKScaffoldDoc(category="speakup_disagree", template="I {hedge} disagree",
                        slots=["hedge"], intensity_band=[0.0, 0.7], weight=50.0)
    row.insert()
    try:
        text = creative_compose("speakup_disagree", intensity={"confidence": 0.3},
                                rng=random.Random(5))
        assert text == "I slightly disagree"   # the Zadeh slot: table word, template grammar
        # at high confidence the hedge key is absent -> the slotted row is unreachable
        plain = creative_compose("speakup_disagree", intensity={"confidence": 0.95},
                                 rng=random.Random(5))
        assert plain == "I do not agree"
    finally:
        row.delete()


def test_plan_action_carries_the_tuple(_io):
    from types import SimpleNamespace
    from brain.behavior import plan_action
    idea = SimpleNamespace(
        action_token=TokenikoAction.WHY.value, trigger=EvalToken.UNKNOWN.value,
        urge=0.6, source=None, answer=None, material=None, target=None, confidence=0.42,
    )
    plan = plan_action(idea, "tokeniko-uid")
    intensity = plan["payload"]["intensity"]
    assert intensity["confidence"] == 0.42
    assert intensity["arousal"] == pytest.approx(0.6)   # no source -> arousal = raw urge


def test_answer_confidence_covers_the_question_path(_io):
    from types import SimpleNamespace
    from brain.behavior import plan_action
    idea = SimpleNamespace(
        action_token=TokenikoAction.ANSWER.value, trigger=EvalToken.QUESTION.value,
        urge=0.9, source=None, material=None, target="asker", confidence=None,
        answer={"kind": AnswerKind.POLAR.value, "verdict": AnswerVerdict.YES.value,
                "confidence": 0.87, "reason": ""},
    )
    plan = plan_action(idea, "tokeniko-uid")
    assert plan["payload"]["intensity"]["confidence"] == 0.87   # the answer dict fills the gap

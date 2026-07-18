# ------------------------------------------------------------------------------------------------
# THE REDUCTIO ACTION — slice 1 (roadmap §0, 2026-07-18). The derivation mirror recognizes an
# absurd (a∧¬a in one chain); this arc turns recognition into the other half of the r.a.a.: a
# QUESTION to the premise-givers — «one of these must be false: {premises}. If all were true, I
# would have to conclude that {absurd}. Which is the false assumption?» (clarify's derivational
# cousin). Covered here:
#   - kb_wonder SURFACES conflicts to the caller (collect_conflicts) instead of only swallowing
#   - the compose route (tokeniko:reduct -> "reduct" category, premises joined at the router)
#   - the reductio_ledger reconcile: spawn-once, resolve-on-cure, re-open on poison's return
#   - Fork B targeting (the most trusted premise-giver) + the plan (teacher's channel, SEND_MESSAGE)
# The synthetic vocabulary is the mammal incident distilled (same shapes as test_coreference_gate).
# ------------------------------------------------------------------------------------------------
import random
from types import SimpleNamespace

import pytest

from lib.core import evaluation_harness
from lib.core.memory import EvalToken, TokenikoAction, ActionType, MEMChannels, ReductioStatus
from brain import compose

# ---- the incident, distilled (the chainer's real vocabulary — membership rules + the negation) --

_PARENTS = lambda s: {"human.n.01": ["animal.n.01"], "animal.n.01": []}.get(s, [])
_RULES = [
    {"subject": "animal.n.01", "predicate": "mind.n.01", "object": None, "negated": False,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-animals-minds"},
    {"subject": "mind.n.01", "predicate": "software.n.01", "object": None, "negated": False,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-mind-software"},
    {"subject": "software.n.01", "predicate": "animal.n.01", "object": None, "negated": True,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-software-not-animal"},
]
_MEMBER = {"subject_uid": "kotekino@test", "klass_sense": "human.n.01",
           "predicate": "human.n.01", "negated": False, "source_id": "fact-k-human"}

_SYNTH_KB = {"rules": _RULES, "facts": [_MEMBER], "relations": _PARENTS, "tier_subjects": []}


# ---- kb_wonder surfaces the conflict (pure — injected KB, no DB) --------------------------------

def test_kb_wonder_surfaces_conflicts():
    conflicts: list = []
    conclusions = evaluation_harness.kb_wonder(kb=_SYNTH_KB, collect_conflicts=conflicts)
    assert any(c["predicate"] == "animal.n.01" for c in conflicts), \
        "the incident's conflict must be surfaced to the caller"
    c = next(c for c in conflicts if c["predicate"] == "animal.n.01")
    assert c["subject"] == "kotekino@test" and c["subject_kind"] == "individual"
    assert c["premises"], "a surfaced conflict carries its premise set"
    # and the materialization contract is unchanged: the CONFLICTED subject's contradicted
    # conclusion never appears in the output (mind.n.01's own clean «not an animal» may — its
    # closure never holds the opposite; per-subject is the mirror's whole point)
    assert all(not (o["subject"] == "kotekino@test" and o["predicate"] == "animal.n.01")
               for o in conclusions)


def test_kb_wonder_without_collector_is_unchanged():
    # the default path (no collector) keeps the exact pre-slice behavior
    conclusions = evaluation_harness.kb_wonder(kb=_SYNTH_KB)
    assert all(not (o["subject"] == "kotekino@test" and o["predicate"] == "animal.n.01")
               for o in conclusions)


# ---- the compose route (pure) -------------------------------------------------------------------

def test_route_reduct_binds_premises_and_absurd():
    answer = {"premises": ["a mind is a software", "software are not animals"],
              "absurd": "Kotekino is an animal and Kotekino is not an animal"}
    routed = compose._route(TokenikoAction.REDUCT.value, EvalToken.ABSURDITY.value, answer)
    assert routed is not None
    category, data = routed
    assert category == "reduct"
    assert data["premises"] == "«a mind is a software» or «software are not animals»"
    assert data["absurd"] == answer["absurd"]


def test_route_reduct_without_data_is_silent():
    # never fabricate a premise: nothing nameable -> nothing to ask
    assert compose._route(TokenikoAction.REDUCT.value, EvalToken.ABSURDITY.value, None) is None
    assert compose._route(TokenikoAction.REDUCT.value, EvalToken.ABSURDITY.value,
                          {"premises": [], "absurd": "x and not x"}) is None
    assert compose._route(TokenikoAction.REDUCT.value, EvalToken.ABSURDITY.value,
                          {"premises": ["a"], "absurd": None}) is None


def test_compose_raw_speaks_the_question():
    answer = {"premises": ["a mind is a software"], "absurd": "X is Y and X is not Y"}
    raw = compose.compose_raw(TokenikoAction.REDUCT.value, EvalToken.ABSURDITY.value, answer,
                              rng=random.Random(7),
                              intensity={"confidence": 1.0, "arousal": 0.95})
    assert raw, "the reduct must always have something to say"
    assert "a mind is a software" in raw       # the premise rides verbatim (the fence)
    assert "X is Y and X is not Y" in raw      # the absurd is named
    assert "false" in raw.lower()              # the question asks for the false assumption


# ---- the absurd render (pure) -------------------------------------------------------------------

def test_conflict_absurd_renders_both_polarities():
    from brain import thinking
    c = {"subject": "kotekino@test", "subject_kind": "individual",
         "predicate": "animal.n.01", "object": None}
    absurd = thinking._conflict_absurd(c)
    assert absurd is not None
    assert "Kotekino" in absurd and "animal" in absurd
    assert " and " in absurd and "not" in absurd   # the pair, both polarities


# ---- the ledger reconcile + targeting + the plan (pipeline — the Mongo sandbox) -----------------

@pytest.fixture()
def reductio_sandbox(_io):
    """Two teacher souls (unequal trust), two ARCHIVED premise axioms (resolvable by id, invisible
    to every KB loader — no leakage into other tests), the eval:absurdity rule. Cleaned up after."""
    from lib.core.models import (TKAxiomDoc, TKBehaviorRuleDoc, TKIdeaDoc,
                                 TKMemoryStakeholdersDoc, TKReductioDoc)
    from lib.core.memory import MEMChannels as _MC

    low = TKMemoryStakeholdersDoc(name="lowsoul", uid="lowsoul@test:1", trust=0.55,
                                  channel=_MC.DISCORD, contextKey="chan-1:111")
    high = TKMemoryStakeholdersDoc(name="highsoul", uid="highsoul@test:2", trust=0.9,
                                   channel=_MC.DISCORD, contextKey="chan-1:222")
    low.insert(); high.insert()
    ax1 = TKAxiomDoc(original="a mind is a software", sourceId=low.uid,
                     archived=True, readonly=False)
    ax2 = TKAxiomDoc(original="software are not animals", sourceId=high.uid,
                     archived=True, readonly=False)
    ax1.insert(); ax2.insert()
    rule = TKBehaviorRuleDoc(trigger=EvalToken.ABSURDITY.value,
                             action=TokenikoAction.REDUCT.value, urge=0.95)
    rule.insert()
    yield {"low": low, "high": high, "ax1": ax1, "ax2": ax2}
    # cleanup — raw pymongo (Bunnet .find().delete() without .run() is a silent no-op)
    TKReductioDoc.get_motor_collection().delete_many({"signature": {"$regex": "^kotekino@test"}})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": EvalToken.ABSURDITY.value})
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": EvalToken.ABSURDITY.value})
    TKAxiomDoc.get_motor_collection().delete_many({"_id": {"$in": [ax1.id, ax2.id]}})
    TKMemoryStakeholdersDoc.get_motor_collection().delete_many(
        {"uid": {"$in": [low.uid, high.uid]}})


def _incident_conflicts(ax1, ax2):
    # the surfaced-conflict shape (kb_wonder's contract), premises = real doc ids + graph keys
    premises = [str(ax1.id), str(ax2.id), "human.n.01|is_a|animal.n.01"]
    return [{"subject": "kotekino@test", "subject_kind": "individual",
             "predicate": "animal.n.01", "object": None, "negated": True,
             "chain": "synthetic [CONFLICT]", "premises": premises}]


def test_reductio_lifecycle(reductio_sandbox):
    from brain import thinking
    from lib.core.models import TKIdeaDoc, TKReductioDoc
    sb = reductio_sandbox
    conflicts = _incident_conflicts(sb["ax1"], sb["ax2"])

    # 1. the question is born: one open ledger row + one idea, aimed at the MOST TRUSTED giver
    thinking._reductio_reconcile(conflicts)
    row = TKReductioDoc.find_one({"signature": "kotekino@test|animal.n.01|"}).run()
    assert row is not None and row.status == ReductioStatus.OPEN and row.generation == 0
    assert "Kotekino" in row.absurd and "not" in row.absurd
    ideas = TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()
    assert len(ideas) == 1
    idea = ideas[0]
    assert idea.action_token == TokenikoAction.REDUCT.value
    assert idea.target == sb["high"].uid          # Fork B: the most trusted premise-giver
    assert idea.confidence == 1.0                 # the r.a.a. is logic — logic never hedges
    assert set(idea.answer["premises"]) == {"a mind is a software", "software are not animals"}

    # 2. asked-once: the same conflict next pass spawns NOTHING new
    thinking._reductio_reconcile(conflicts)
    assert len(TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()) == 1

    # 3. the cure: the conflict vanishes from the saturation -> the row resolves
    thinking._reductio_reconcile([])
    row = TKReductioDoc.find_one({"signature": "kotekino@test|animal.n.01|"}).run()
    assert row.status == ReductioStatus.RESOLVED and row.resolvedAt is not None

    # 4. the poison returns -> re-opened one generation up, honestly re-asked
    thinking._reductio_reconcile(conflicts)
    row = TKReductioDoc.find_one({"signature": "kotekino@test|animal.n.01|"}).run()
    assert row.status == ReductioStatus.OPEN and row.generation == 1
    assert len(TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()) == 2


def test_reduct_plan_reaches_the_teacher(reductio_sandbox):
    from brain import behavior
    from lib.core.models import TKIdeaDoc
    sb = reductio_sandbox
    idea = TKIdeaDoc(
        trigger=EvalToken.ABSURDITY.value, action_token=TokenikoAction.REDUCT.value,
        urge=0.95, source="reductio:x:0", target=sb["high"].uid, confidence=1.0,
        answer={"premises": ["a mind is a software", "software are not animals"],
                "absurd": "Kotekino is an animal and Kotekino is not an animal"},
    )
    plan = behavior.plan_action(idea, "tokeniko")
    assert plan is not None
    assert plan["action_type"] == ActionType.SEND_MESSAGE
    assert plan["channel"] == MEMChannels.DISCORD      # the teacher's channel, no source memory
    assert plan["target"] == sb["high"].uid
    assert plan["payload"]["intensity"]["confidence"] == 1.0
    raw = plan["payload"]["raw"]
    assert raw and "a mind is a software" in raw and "false" in raw.lower()
    assert behavior.score_feasibility(plan) == 1.0     # addressable via the contextKey DM route


def test_reductio_without_rule_stays_unledgered(_io):
    # no enabled eval:absurdity rule -> the conflict keeps logging loudly, no ledger row (so the
    # question is honestly asked the first pass AFTER the personality learns the reflex)
    from brain import thinking
    from lib.core.models import TKReductioDoc
    conflicts = [{"subject": "nobody@test", "subject_kind": "individual",
                  "predicate": "animal.n.01", "object": None, "negated": True,
                  "chain": "synthetic", "premises": ["r-x"]}]
    thinking._reductio_reconcile(conflicts)
    assert TKReductioDoc.find_one({"signature": "nobody@test|animal.n.01|"}).run() is None

# ------------------------------------------------------------------------------------------------
# THE HYPOTHESIS ENGINE — survey slice 5 (2026-07-19, the author-approved design). A guess is
# CHARITABLE BELIEF WITH EVIDENCE: still-UNKNOWN at execution + geometric resemblance to something
# held -> a theorem row at HYPOTHESIS_TRUST (derived_by="hypothesis"), silently. Covered here:
# the formation bar (resemblance floor / verdict re-check / dedup), the wire (idea -> plan ->
# dispatch -> _execute_guess), the PROMOTION (a trusted teacher corroborates -> taught in place),
# the untangler's first-suspect preference (his own guesses die before a taught belief is
# questioned — silently), and the dream that tells it (the author's fork ruling).
#
# The evaluate seam is INJECTED (monkeypatched) in the formation tests: the full-gate sandbox KB
# is shared across suites, so a live relationMatch would be nondeterministic — the bar's logic is
# what's under test, not the geometry (which has its own suites).
# ------------------------------------------------------------------------------------------------
import datetime

import pytest
from bson import ObjectId

from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.memory import EvalToken, MEMChannels, MEMProvenance, TokenikoAction

_TEACHER = "guesser@htest:1"


def _zip(subject="gold.n.01", predicate="beautiful.a.01"):
    from lib.core.tkzip import TKZip, TKZipItem, TKZipContent
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
        subject=None, predicate=None, direct=None,
        senses={"subject": subject, "predicate": predicate})))


def _mk_speaker(_io, trust=0.5, uid=_TEACHER):
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc(uid=uid, name="guesser", isMe=False,
                                   channel=MEMChannels.DISCORD, trust=trust).save()


def _mk_item(speaker_id, original="htest: gold is beautiful", directedness=0.6):
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(original=original, sourceId=speaker_id,
                           channel=MEMChannels.DISCORD, zip=_zip(),
                           directedness=directedness)
    item.insert()
    return item


def _unknown_eval(match=0.72, matched_id=None, matched_original="htest: gold is precious"):
    result = EvaluatorResult(truth=0.5, status=EvaluatorStatus.INSUFFICIENT,
                             relationMatch=match)
    return {"result": result, "matchedId": matched_id or str(ObjectId()),
            "matchedOriginal": matched_original, "relationMatch": match}


@pytest.fixture()
def hyp_world(_io):
    from lib.core.models import (TKActionDoc, TKIdeaDoc, TKMemoryItemDoc,
                                 TKMemoryStakeholdersDoc, TKTheoremDoc)
    speaker = _mk_speaker(_io)
    yield {"speaker": speaker}
    TKTheoremDoc.get_motor_collection().delete_many({"original": {"$regex": "^htest:"}})
    TKMemoryItemDoc.get_motor_collection().delete_many({"original": {"$regex": "^htest:"}})
    TKMemoryStakeholdersDoc.get_motor_collection().delete_many({"uid": _TEACHER})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": EvalToken.UNKNOWN.value})
    TKActionDoc.get_motor_collection().delete_many(
        {"payload.action_token": TokenikoAction.GUESS.value})


# ---- the formation bar --------------------------------------------------------------------------

def test_hypothesis_minted_with_evidence(hyp_world, monkeypatch):
    from brain import thinking
    from lib.core.models import TKTheoremDoc
    item = _mk_item(str(hyp_world["speaker"].id))
    monkeypatch.setattr(thinking, "evaluate_zip", lambda z: _unknown_eval())
    norm = thinking.materialize_hypothesis(item)
    assert norm == "htest: gold is beautiful"
    row = TKTheoremDoc.find_one({"original": norm}).run()
    assert row is not None and row.archived is False
    assert row.trusted == pytest.approx(0.3)                    # min(speaker 0.5, cap 0.3)
    assert row.provenance.derived_by == "hypothesis"
    assert "resembles «htest: gold is precious» at 0.72" in row.provenance.chain
    assert f"hypothesis:{_TEACHER}" in row.provenance.premises
    assert row.postable is True                                  # public-born: may be dreamed


def test_no_resemblance_no_guess(hyp_world, monkeypatch):
    from brain import thinking
    from lib.core.models import TKTheoremDoc
    item = _mk_item(str(hyp_world["speaker"].id))
    monkeypatch.setattr(thinking, "evaluate_zip", lambda z: _unknown_eval(match=0.4))
    assert thinking.materialize_hypothesis(item) is None
    assert TKTheoremDoc.find_one({"original": "htest: gold is beautiful"}).run() is None


def test_refuted_or_derivable_is_not_guessed(hyp_world, monkeypatch):
    from brain import thinking
    item = _mk_item(str(hyp_world["speaker"].id))
    for truth, status in ((0.05, EvaluatorStatus.RESOLVED), (0.95, EvaluatorStatus.RESOLVED)):
        out = _unknown_eval()
        out["result"] = EvaluatorResult(truth=truth, status=status, relationMatch=0.9)
        monkeypatch.setattr(thinking, "evaluate_zip", lambda z, o=out: o)
        assert thinking.materialize_hypothesis(item) is None


def test_hypothesis_dedups_by_original(hyp_world, monkeypatch):
    from brain import thinking
    item = _mk_item(str(hyp_world["speaker"].id))
    monkeypatch.setattr(thinking, "evaluate_zip", lambda z: _unknown_eval())
    assert thinking.materialize_hypothesis(item) is not None
    again = _mk_item(str(hyp_world["speaker"].id))
    assert thinking.materialize_hypothesis(again) is None


def test_dm_born_guess_is_never_postable(hyp_world, monkeypatch):
    from brain import thinking
    from lib.core.models import TKTheoremDoc
    item = _mk_item(str(hyp_world["speaker"].id), directedness=1.0)   # a DM (>= 0.95)
    monkeypatch.setattr(thinking, "evaluate_zip", lambda z: _unknown_eval())
    norm = thinking.materialize_hypothesis(item)
    assert TKTheoremDoc.find_one({"original": norm}).run().postable is False


# ---- the wire -----------------------------------------------------------------------------------

def test_the_guess_wire(hyp_world, monkeypatch):
    from types import SimpleNamespace
    from brain import behavior, thinking
    from brain import main as brain_main
    from lib.core.models import TKTheoremDoc
    item = _mk_item(str(hyp_world["speaker"].id))
    monkeypatch.setattr(thinking, "evaluate_zip", lambda z: _unknown_eval())
    idea = SimpleNamespace(
        action_token=TokenikoAction.GUESS.value, trigger=EvalToken.UNKNOWN.value,
        urge=0.55, source=str(item.id), answer=None, material=None, target=None,
        confidence=None, id=ObjectId(),
    )
    plan = behavior.plan_action(idea, "tokeniko-uid")
    assert plan is not None and plan["channel"] == MEMChannels.INTERNAL
    assert plan["payload"]["source"] == str(item.id)      # the lesson's memory id rides the wire
    action = behavior.dispatch_action(idea, "tokeniko-uid", plan)
    brain_main._execute_guess(action)
    assert TKTheoremDoc.find_one({"original": "htest: gold is beautiful"}).run() is not None


# ---- the promotion (the analytic/synthetic seam) --------------------------------------------------

def test_teacher_corroboration_promotes_the_guess(hyp_world, monkeypatch):
    from brain import thinking
    from lib.core.models import TKMemoryStakeholdersDoc, TKTheoremDoc
    item = _mk_item(str(hyp_world["speaker"].id))
    monkeypatch.setattr(thinking, "evaluate_zip", lambda z: _unknown_eval())
    norm = thinking.materialize_hypothesis(item)
    assert TKTheoremDoc.find_one({"original": norm}).run().trusted == pytest.approx(0.3)

    teacher = TKMemoryStakeholdersDoc(uid="prof@htest:2", name="prof", isMe=False,
                                      channel=MEMChannels.DISCORD, trust=0.95).save()
    try:
        lesson = _mk_item(str(teacher.id))
        assert thinking.materialize_taught(lesson) == norm     # the candidate saw a PROMOTABLE row
        row = TKTheoremDoc.find_one({"original": norm}).run()
        assert row.trusted == pytest.approx(0.9)               # promoted to the teacher's level
        assert row.provenance.derived_by == "teaching"
        assert "promoted from hypothesis" in row.provenance.chain
        assert len(TKTheoremDoc.find({"original": norm}).to_list()) == 1   # in PLACE, no twin
    finally:
        TKMemoryStakeholdersDoc.get_motor_collection().delete_many({"uid": "prof@htest:2"})


# ---- the untangler's first-suspect preference + the dream -----------------------------------------

def test_untangler_drops_the_guess_first_and_the_dream_tells_it(_io, monkeypatch):
    from brain import thinking
    from lib.core import untangle
    from lib.core.models import (TKAxiomDoc, TKBehaviorRuleDoc, TKIdeaDoc, TKTheoremDoc)
    from lib.core.memory import LifeEventKind

    axiom = TKAxiomDoc(original="htest2: no software is an animal", zip=_zip(),
                       sourceId="seed", archived=False, readonly=True)
    axiom.insert()
    taught = TKTheoremDoc(
        original="htest2: all minds are software", zip=_zip(), sourceId="prof@htest:2",
        channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=["taught:prof@htest:2"], chain="t",
                                 derived_by="teaching")).insert()
    guess = TKTheoremDoc(
        original="htest2: all animals are minds", zip=_zip(), sourceId="x",
        channel=MEMChannels.INTERNAL, archived=False, trusted=0.3, postable=True,
        provenance=MEMProvenance(premises=["hypothesis:someone@htest"], chain="h",
                                 derived_by="hypothesis")).insert()
    rule = TKBehaviorRuleDoc(trigger=LifeEventKind.DREAM.value,
                             action=TokenikoAction.POST.value, urge=0.7)
    rule.insert()
    # a synthetic saturation: ONE conflict resting on all three docs — normally UNDECIDABLE
    # (two revisables: the taught belief + the guess); the first-suspect rule decides it.
    groups = {"animal.n.01|animal.n.01|": {
        "c": {"subject": "animal.n.01", "predicate": "animal.n.01", "object": None,
              "subject_kind": "class", "premises": []},
        "premises": {str(axiom.id), str(taught.id), str(guess.id)},
    }}
    monkeypatch.setattr(untangle, "_saturate", lambda: groups)
    try:
        report = untangle.untangle_pass(apply=True)
        assert len(report["convicted"]) == 1
        entry = report["convicted"][0]
        assert entry["guess"] is True
        assert entry["original"] == "htest2: all animals are minds"
        assert report["asked"] == []                                     # decidable after all
        assert TKTheoremDoc.get(guess.id).run().archived is True         # the guess fell
        assert TKTheoremDoc.get(taught.id).run().archived is False       # the taught belief stands
        # ... and the DREAM tells it (the author's fork ruling)
        assert thinking.spawn_dream(report) is True
        idea = TKIdeaDoc.find_one({"trigger": LifeEventKind.DREAM.value}).run()
        assert idea.material["retracted"][0]["guess"] is True
    finally:
        TKAxiomDoc.get_motor_collection().delete_many({"original": {"$regex": "^htest2:"}})
        TKTheoremDoc.get_motor_collection().delete_many({"original": {"$regex": "^htest2:"}})
        TKBehaviorRuleDoc.get_motor_collection().delete_many(
            {"trigger": LifeEventKind.DREAM.value})
        TKIdeaDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.DREAM.value})


def test_dream_composer_speaks_the_guess_register():
    import senses.blog as blog
    d = blog.compose_draft(
        {"kind": "dream",
         "retracted": [{"original": "all animals are minds", "absurd": "a and not a",
                        "guess": True}],
         "asked": 0, "significance": 0.9},
        soul_reader=lambda uid: None, souls_reader=lambda: [],
        premise_reader=lambda pid: None)
    joined = " ".join(d.facts)
    assert "I let a guess of mine go" in joined
    assert "«all animals are minds»" in joined

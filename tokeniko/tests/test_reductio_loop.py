# ------------------------------------------------------------------------------------------------
# THE REDUCTIO ACTION — slice 2: the loop closes (roadmap §0, 2026-07-18). The claim under test:
# the resolution consumer needs ZERO new machinery — the natural answer to the reduct question
# («not all minds are software») rides the EXISTING correction/retreat path, the premise archives,
# the conflict vanishes from the next saturation, and the ledger row RESOLVES. The whole r.a.a.
# circle, end-to-end, through the REAL components at every step:
#
#   poisoned taught theorems -> _load_active_kb -> kb_wonder (the conflict surfaces)
#   -> _reductio_reconcile (row OPEN + the reduct question aimed at the most trusted teacher)
#   -> the teacher's denial -> thinking._try_correction (Popper trust gate)
#   -> plan/dispatch -> brain_main._execute_retreat (archive + cascade + subaltern)
#   -> fresh saturation (no conflict) -> _reductio_reconcile (row RESOLVED)
#   -> the concede idea (the conversation's honest ending: «you are right — I no longer hold…»)
#
# The poison is the mammal incident distilled to class seeds (probe-verified sense-consistent):
# «all animals are minds» + «all minds are software» + «no software is an animal» -> the chainer
# derives animal ∧ ¬animal in one closure.
# ------------------------------------------------------------------------------------------------
import datetime
from types import SimpleNamespace

import pytest
from bson import ObjectId

from lib.core import evaluation_harness
from lib.core.memory import (ActionType, EvalToken, MEMChannels, MEMProvenance,
                             ReductioStatus, TokenikoAction, TrustEpisodeKind)

_SIG = "animal.n.01|animal.n.01|"          # the contradicted conclusion key the poison produces
_PREMISE_B = "all minds are software"      # the premise the teacher will deny

_POISON = [
    ("all animals are minds",  "novice@rtest:2"),
    (_PREMISE_B,               "prof@rtest:1"),   # the most trusted teacher's premise
    ("no software is an animal", "novice@rtest:2"),
]


@pytest.fixture()
def poisoned_world(_io, compile_zip):
    """The mammal shape as ACTIVE taught theorems + two teachers of unequal trust + the four
    behavior rules the circle needs. FUNCTION-scoped: every test gets a fresh poisoned world
    (the circle tests consume it — they archive the premise). Everything cleaned; the KB cache
    reset on both edges."""
    from lib.core.models import (TKBehaviorRuleDoc, TKIdeaDoc, TKMemoryStakeholdersDoc,
                                 TKReductioDoc, TKTheoremDoc)
    prof = TKMemoryStakeholdersDoc(name="prof", uid="prof@rtest:1", trust=0.95,
                                   channel=MEMChannels.DISCORD, contextKey="rchan:11").insert()
    novice = TKMemoryStakeholdersDoc(name="novice", uid="novice@rtest:2", trust=0.6,
                                     channel=MEMChannels.DISCORD, contextKey="rchan:22").insert()
    theorems = []
    for sentence, teacher in _POISON:
        theorems.append(TKTheoremDoc(
            original=sentence, zip=compile_zip(sentence), sourceId=teacher,
            channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
            provenance=MEMProvenance(premises=[f"taught:{teacher}"],
                                     chain="taught (reductio-loop fixture)",
                                     derived_by="teaching"),
        ).insert())
    rules = [
        TKBehaviorRuleDoc(trigger=EvalToken.ABSURDITY.value, action=TokenikoAction.REDUCT.value, urge=0.95),
        TKBehaviorRuleDoc(trigger=EvalToken.CORRECTION.value, action=TokenikoAction.RETREAT.value, urge=0.95),
        TKBehaviorRuleDoc(trigger=EvalToken.CORRECTION_DONE.value, action=TokenikoAction.CONCEDE.value, urge=0.85),
        TKBehaviorRuleDoc(trigger=TrustEpisodeKind.CORRECTION.value, action=TokenikoAction.MORE_TRUST.value, urge=0.6),
    ]
    for r in rules:
        if TKBehaviorRuleDoc.find_one({"trigger": r.trigger, "action": r.action}).run() is None:
            r.insert()
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    yield {"prof": prof, "novice": novice, "theorems": theorems}
    # teardown — raw pymongo where Bunnet queries would silently no-op without .run()
    from lib.core.models import TKActionDoc
    # the circles dispatch REAL actions (dispatch_action persists PENDING rows) and execute them
    # directly — sweep them, or the next actions_phase test drains OUR leftover instead of its own
    TKActionDoc.get_motor_collection().delete_many(
        {"action_type": ActionType.REVISE_BELIEF.value})
    TKTheoremDoc.get_motor_collection().delete_many(
        {"original": {"$in": [s for s, _ in _POISON] + ["some mind is a software"]}})
    TKReductioDoc.get_motor_collection().delete_many({})   # sandbox ledger — module-scoped truth
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": {"$in": [
        EvalToken.ABSURDITY.value, EvalToken.CORRECTION.value,
        EvalToken.CORRECTION_DONE.value, TrustEpisodeKind.CORRECTION.value]}})
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": {"$in": [
        EvalToken.ABSURDITY.value, EvalToken.CORRECTION.value,
        EvalToken.CORRECTION_DONE.value, TrustEpisodeKind.CORRECTION.value]}})
    TKMemoryStakeholdersDoc.get_motor_collection().delete_many(
        {"uid": {"$in": ["prof@rtest:1", "novice@rtest:2"]}})
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None


def _saturate():
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    conflicts: list = []
    evaluation_harness.kb_wonder(collect_conflicts=conflicts)
    return conflicts


# the ANSWER-FORM BOUNDARY (slice 2 finding, pinned honestly — runs FIRST, reads only): the
# correction detector consumes O/E CORNERS («not all minds are software» / «no mind is a
# software»); a GENERIC denial («a mind is not a software») is not a corner, so correction v1
# does not consume it — the belief stands and the normal eval:false path pushes back, even
# though tokeniko himself asked the question. The fork (charity by reductio-context vs coaching
# the question's form) is the author's — see roadmap §0.
def test_generic_denial_is_not_yet_a_correction(poisoned_world, compile_zip):
    assert evaluation_harness.correction_target(
        compile_zip("a mind is not a software")) is None


def test_the_circle_closes(poisoned_world, compile_zip, monkeypatch):
    from brain import behavior, thinking
    from brain import main as brain_main
    from lib.core.models import TKIdeaDoc, TKMemoryItemDoc, TKReductioDoc

    # ---- 1. the poison saturates: the REAL loader + chainer surface the conflict --------------
    conflicts = _saturate()
    ours = [c for c in conflicts
            if c["subject"] == "animal.n.01" and c["predicate"] == "animal.n.01"]
    assert ours, "the poisoned world must produce the animal ∧ ¬animal conflict"

    # ---- 2. the question is born, aimed at the MOST TRUSTED teacher ---------------------------
    thinking._reductio_reconcile(conflicts)
    row = TKReductioDoc.find_one({"signature": _SIG}).run()
    assert row is not None and row.status == ReductioStatus.OPEN
    idea = TKIdeaDoc.find_one({"trigger": EvalToken.ABSURDITY.value,
                               "source": f"reductio:{row.id}:0"}).run()
    assert idea is not None and idea.target == "prof@rtest:1"
    assert set(idea.answer["premises"]) == {s for s, _ in _POISON}

    # ---- 3. the teacher answers the question — the EXISTING correction path consumes it -------
    item = TKMemoryItemDoc(
        id=ObjectId(), original="not all minds are software",
        zip=compile_zip("not all minds are software"),
        sourceId="prof@rtest:1", channel="discord", directedness=1.0,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    assert thinking._try_correction(item) is True, \
        "the natural answer must ride the correction path — no new binding machinery"
    retreat_idea = TKIdeaDoc.find_one(
        {"trigger": EvalToken.CORRECTION.value, "source": str(item.id)}).run()
    assert retreat_idea is not None

    # ---- 4. the retreat executes (the real plan/dispatch/executor chain) ----------------------
    mints = []
    monkeypatch.setattr("brain.api_client.materialize_theorem",
                        lambda **kw: mints.append(kw) or {"status": "complete"})
    plan = behavior.plan_action(retreat_idea, "tokeniko")
    assert plan is not None and plan["action_type"] == ActionType.REVISE_BELIEF
    action = behavior.dispatch_action(retreat_idea, "tokeniko", plan)
    brain_main._execute_retreat(action)
    from lib.core.models import TKTheoremDoc
    premise_doc = TKTheoremDoc.find_one({"original": _PREMISE_B}).run()
    assert premise_doc.archived is True, "the denied premise is retreated (archived, never deleted)"
    assert len(mints) == 1 and mints[0]["tokens"].startswith("some ")  # the subaltern survives

    # ---- 5. the cure propagates: fresh saturation, no conflict, the ledger RESOLVES -----------
    conflicts2 = _saturate()
    assert not any(c["subject"] == "animal.n.01" and c["predicate"] == "animal.n.01"
                   for c in conflicts2), "the retreated premise no longer fuels the contradiction"
    thinking._reductio_reconcile(conflicts2)
    row = TKReductioDoc.find_one({"signature": _SIG}).run()
    assert row.status == ReductioStatus.RESOLVED and row.resolvedAt is not None

    # ---- 6. the conversation's honest ending: the concede names what was retracted ------------
    concede = TKIdeaDoc.find_one(
        {"trigger": EvalToken.CORRECTION_DONE.value, "target": "prof@rtest:1"}).run()
    assert concede is not None and concede.action_token == TokenikoAction.CONCEDE.value
    assert concede.answer["retracted"] == [_PREMISE_B]


# ---- fork A: the reduct-answer binding (the answer-form gap's cure) -----------------------------

def _denial_item(compile_zip, sentence, source_uid):
    from lib.core.models import TKMemoryItemDoc
    return TKMemoryItemDoc(
        id=ObjectId(), original=sentence, zip=compile_zip(sentence),
        sourceId=source_uid, channel="discord", directedness=1.0,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )


def test_generic_denial_closes_the_circle_in_context(poisoned_world, compile_zip, monkeypatch):
    # the SECOND circle: the same loop, answered in the natural conversational form — the
    # generic denial the correction detector cannot see, bound by the reductio context.
    from brain import behavior, thinking
    from brain import main as brain_main
    from lib.core.models import TKIdeaDoc, TKReductioDoc, TKTheoremDoc

    thinking._reductio_reconcile(_saturate())
    row = TKReductioDoc.find_one({"signature": _SIG}).run()
    assert row is not None and row.target == "prof@rtest:1"
    # the poison may spread further than the distilled shape (in the sandbox it reaches Mari
    # through her humanity — her own animal ∧ ¬animal row, also aimed at prof): collect EVERY
    # open row aimed at the teacher; the shared premise threads through them all.
    open_sigs = {r.signature for r in TKReductioDoc.find(
        {"status": ReductioStatus.OPEN.value, "target": "prof@rtest:1"}).to_list()}
    assert _SIG in open_sigs

    item = _denial_item(compile_zip, "a mind is not a software", "prof@rtest:1")
    assert thinking._try_correction(item) is False          # the boundary stands (no corner)
    assert thinking._try_reduct_answer(item) is True        # the context binds it
    retreat_idea = TKIdeaDoc.find_one(
        {"trigger": EvalToken.CORRECTION.value, "source": str(item.id)}).run()
    assert retreat_idea is not None
    assert retreat_idea.answer["corner"] == "R"
    assert retreat_idea.answer["signature"] in open_sigs    # bound through one of the asked rows
    assert retreat_idea.answer["sources"][0]["original"] == _PREMISE_B
    assert retreat_idea.answer["weakened"] is None          # a flat denial mints no subaltern

    mints = []
    monkeypatch.setattr("brain.api_client.materialize_theorem",
                        lambda **kw: mints.append(kw) or {"status": "complete"})
    plan = behavior.plan_action(retreat_idea, "tokeniko")
    brain_main._execute_retreat(behavior.dispatch_action(retreat_idea, "tokeniko", plan))
    assert TKTheoremDoc.find_one({"original": _PREMISE_B}).run().archived is True
    assert mints == []                                      # nothing minted — epistemic caution

    thinking._reductio_reconcile(_saturate())
    # ONE answer cures EVERY absurdity resting on the retired premise — all the asked rows close
    for sig in open_sigs:
        assert TKReductioDoc.find_one(
            {"signature": sig}).run().status == ReductioStatus.RESOLVED
    concede = TKIdeaDoc.find_one(
        {"trigger": EvalToken.CORRECTION_DONE.value, "target": "prof@rtest:1"}).run()
    assert concede is not None and concede.answer["retracted"] == [_PREMISE_B]


def test_reduct_binding_scoped_to_the_asked_teacher(poisoned_world, compile_zip):
    # the scope: only the ASKED teacher's denial binds — a premise-giver who was not asked, or a
    # stranger, rides the normal paths (their denial is a claim like any other)
    from brain import thinking
    thinking._reductio_reconcile(_saturate())
    assert thinking._try_reduct_answer(
        _denial_item(compile_zip, "a mind is not a software", "novice@rtest:2")) is False
    assert thinking._try_reduct_answer(
        _denial_item(compile_zip, "a mind is not a software", "nobody@rtest:9")) is False


def test_reduct_binding_reaches_individual_subject_premises(poisoned_world, compile_zip, _io):
    # the live miss (2026-07-19): an INDIVIDUAL-subject premise («so I am a mammal» — subject
    # tokeniko, an identity uid, never a sense) was unmatchable by the sense-only key, so the
    # teacher's denial bounced to clarify and the row stayed open. The key now falls back to the
    # identity-bridge: the addressed «you are not a mammal» carries the same uid and binds.
    from brain import thinking
    from lib.core.memory import MEMProvenance
    from lib.core.models import TKIdeaDoc, TKReductioDoc, TKTheoremDoc
    ghost = TKTheoremDoc(
        original="so I am a mammal", zip=compile_zip("so I am a mammal"),
        sourceId="prof@rtest:1", channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=["taught:prof@rtest:1"],
                                 chain="taught (reductio-loop fixture)", derived_by="teaching"),
    ).insert()
    row = TKReductioDoc(
        signature="tokeniko|mammal.n.01|", premises=[str(ghost.id)],
        absurd="I am a mammal and I am not a mammal",
        status=ReductioStatus.OPEN, target="prof@rtest:1", generation=0,
    ).insert()
    try:
        item = _denial_item(compile_zip, "you are not a mammal", "prof@rtest:1")
        assert thinking._try_reduct_answer(item) is True
        retreat_idea = TKIdeaDoc.find_one(
            {"trigger": EvalToken.CORRECTION.value, "source": str(item.id)}).run()
        assert retreat_idea is not None
        assert retreat_idea.answer["corner"] == "R"
        assert retreat_idea.answer["signature"] == row.signature
        assert retreat_idea.answer["sources"][0]["original"] == "so I am a mammal"
    finally:
        TKTheoremDoc.get_motor_collection().delete_many({"original": "so I am a mammal"})


def test_unaddressed_denial_still_does_not_bind(poisoned_world, compile_zip, _io):
    # the coreference gate's caution survives the identity fallback: an AMBIENT «you are not a
    # mammal» (addressed=False — the room, not the DM) resolves «you» to no identity, keys to
    # None, and binds nothing. The cure never reopens the mammal-era hole.
    import copy as _copy
    import datetime as _dt
    from brain import thinking
    from lib.core.memory import MEMProvenance
    from lib.core.models import TKMemoryItemDoc, TKReductioDoc, TKTheoremDoc
    from lib.llc.compiler import compiler_compile
    from lib.llc.parser import parser
    tok, ai = _io
    ghost = TKTheoremDoc(
        original="so I am a mammal", zip=compile_zip("so I am a mammal"),
        sourceId="prof@rtest:1", channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=["taught:prof@rtest:1"],
                                 chain="taught (reductio-loop fixture)", derived_by="teaching"),
    ).insert()
    TKReductioDoc(
        signature="tokeniko|mammal.n.01|", premises=[str(ghost.id)],
        absurd="I am a mammal and I am not a mammal",
        status=ReductioStatus.OPEN, target="prof@rtest:1", generation=0,
    ).insert()
    try:
        ambient_zip = compiler_compile(_copy.deepcopy(
            parser("you are not a mammal", tok, tok, ai, addressed=False)))[1]
        item = TKMemoryItemDoc(
            id=ObjectId(), original="you are not a mammal", zip=ambient_zip,
            sourceId="prof@rtest:1", channel="discord", directedness=0.6,
            timestamp=_dt.datetime.now(_dt.timezone.utc),
        )
        assert thinking._try_reduct_answer(item) is False
    finally:
        TKTheoremDoc.get_motor_collection().delete_many({"original": "so I am a mammal"})


def test_reduct_binding_gate_holds_for_low_trust(poisoned_world, compile_zip):
    # the same Popper gate as every correction: the answerer's trust must reach the belief's —
    # the reductio context disambiguates the MEANING, it never lowers the bar
    from brain import thinking
    thinking._reductio_reconcile(_saturate())
    prof = poisoned_world["prof"]
    prof.trust = 0.5            # below the taught belief's 0.7
    prof.save()
    assert thinking._try_reduct_answer(
        _denial_item(compile_zip, "a mind is not a software", "prof@rtest:1")) is False

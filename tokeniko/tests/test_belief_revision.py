# ------------------------------------------------------------------------------------------------
# BELIEF-REVISION v1 + the directedness floor (the retreat arc #3 + #4, 2026-07-15).
#
# The 2026-07-14 bold-test found the BOUNCE: a quantified correction («not all softwares are mind…»)
# was evaluated against the very generalization it targeted, refuted, and cost the corrector trust.
# #4 gives corrections a first-class path: detection (harness `correction_target` — an O/E-corner
# claim the active graph affirms through a LEARNED, doc-retractable hop), the Popper TRUST GATE
# (corrector >= belief; the author's D2 ruling), and the RETREAT executor (archive + cascade + mint
# the surviving subaltern I). #3 floors the directedness of self-relevant triggers at addressed —
# the eval:conflict that died at ambient 0.6 during the Socratic dialogue now speaks.
#
# Sandbox discipline: everything inserted here is cleaned up in the fixture teardown; the taught
# generalization exists ONLY while this module runs (KB fingerprint cache reloads on both edges).
# ------------------------------------------------------------------------------------------------
import time
from types import SimpleNamespace

import pytest
from bson import ObjectId

from lib.core import evaluation_harness
from lib.core.memory import EvalToken, MEMChannels, MEMProvenance, TrustEpisodeKind


TAUGHT = "all softwares are minds"


# the taught generalization under test — the dialogue's own belief, stored exactly as
# materialize_taught would store it (an ACTIVE taught theorem at teacher trust 0.7).
@pytest.fixture(scope="module")
def taught_theorem(_io, compile_zip):
    from lib.core.models import TKTheoremDoc
    doc = TKTheoremDoc(
        original=TAUGHT,
        zip=compile_zip(TAUGHT),
        sourceId="hellen@test",
        channel=MEMChannels.INTERNAL,
        archived=False,
        trusted=0.7,
        provenance=MEMProvenance(premises=["taught:hellen@test"],
                                 chain="taught by hellen (test fixture)",
                                 derived_by="teaching"),
    )
    doc.insert()
    yield doc
    TKTheoremDoc.find({"original": TAUGHT}).delete().run()  # Bunnet: .run() or it is a no-op
    # drop the module's KB cache so later test files never see the retracted world
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None


# ---- #3: the self-relevant directedness floor ---------------------------------------------------

def _idea(trigger, urge):
    from lib.core.models import TKIdeaDoc
    return TKIdeaDoc(trigger=trigger, action_token="tokeniko:clarify", urge=urge, id=ObjectId())


def test_conflict_floors_ambient_to_addressed(_io):
    # the dialogue's death: eval:conflict 0.7 x ambient 0.6 = 0.42 < 0.5 -> silence. Now 0.7 x 0.9.
    from brain import behavior
    src = SimpleNamespace(directedness=0.6)
    assert behavior.effective_urge(_idea(EvalToken.CONFLICT.value, 0.7), src) == pytest.approx(0.63)


def test_conflict_stays_polite_below_ambient(_io):
    # someone else's thread (0.15): the floor does NOT apply — the polite eavesdropper
    from brain import behavior
    src = SimpleNamespace(directedness=0.15)
    assert behavior.effective_urge(_idea(EvalToken.CONFLICT.value, 0.7), src) == pytest.approx(0.105)


def test_non_self_relevant_triggers_unchanged(_io):
    # eval:false at ambient keeps the plain multiplication (no floor)
    from brain import behavior
    src = SimpleNamespace(directedness=0.6)
    assert behavior.effective_urge(_idea(EvalToken.FALSE.value, 0.6), src) == pytest.approx(0.36)


# ---- #4 D1: the correction detector --------------------------------------------------------------

def test_o_corner_correction_detected(taught_theorem, compile_zip):
    # «not all softwares are minds» vs the taught A -> a correction, with the subaltern I to mint
    ct = evaluation_harness.correction_target(compile_zip("not all softwares are minds"))
    assert ct is not None
    assert ct["corner"] == "O"
    assert any(s["kind"] == "theorem" for s in ct["sources"])
    assert ct["belief_trust"] == pytest.approx(0.7)
    assert ct["weakened"] is not None
    assert ct["weakened"]["tokens"].startswith("some ")


def test_e_corner_correction_no_subaltern(taught_theorem, compile_zip):
    # «no software is a mind» defeats A too — but contests I as well: nothing survives to mint
    ct = evaluation_harness.correction_target(compile_zip("no software is a mind"))
    assert ct is not None
    assert ct["corner"] == "E"
    assert ct["weakened"] is None


def test_bedrock_generalization_immune(taught_theorem, compile_zip):
    # «not all cats are mammals» attacks a PURE-BEDROCK path — substrate, not a retractable belief
    assert evaluation_harness.correction_target(compile_zip("not all cats are mammals")) is None


def test_unaffirmed_claim_is_no_correction(taught_theorem, compile_zip):
    # the KB does not hold «all rocks are minds» — nothing to correct (normal eval path)
    assert evaluation_harness.correction_target(compile_zip("not all rocks are minds")) is None


def test_affirmative_claim_is_no_correction(taught_theorem, compile_zip):
    # an A-corner ASSERTION is never a correction (corners O/E only)
    assert evaluation_harness.correction_target(compile_zip(TAUGHT)) is None


def test_readonly_axiom_immune(_io, compile_zip):
    # a READONLY axiom (the seeded imprinting) is never conversationally retractable — he defends
    # his constitution; flipping readonly off makes the same generalization retractable.
    from lib.core.models import TKAxiomDoc
    doc = TKAxiomDoc(original="all planets are teachers",
                     zip=compile_zip("all planets are teachers"),
                     sourceId="fixture@test", archived=False, readonly=True)
    doc.insert()
    try:
        evaluation_harness._kb_cache_fp = None
        assert evaluation_harness.correction_target(
            compile_zip("not all planets are teachers")) is None
        doc.readonly = False
        doc.save()
        evaluation_harness._kb_cache_fp = None  # readonly flip does not move the fingerprint
        ct = evaluation_harness.correction_target(compile_zip("not all planets are teachers"))
        assert ct is not None and any(s["kind"] == "axiom" for s in ct["sources"])
    finally:
        TKAxiomDoc.find({"original": "all planets are teachers"}).delete().run()
        evaluation_harness._kb_cache = None
        evaluation_harness._kb_cache_fp = None


# ---- #4 D2: the trust gate (brain policy) ---------------------------------------------------------

@pytest.fixture(scope="module")
def souls(_io):
    from lib.core.models import TKMemoryStakeholdersDoc, TKIdeaDoc
    low = TKMemoryStakeholdersDoc(name="lowsoul", uid="lowsoul@test", trust=0.2).insert()
    high = TKMemoryStakeholdersDoc(name="highsoul", uid="highsoul@test", trust=0.95).insert()
    yield low, high
    TKMemoryStakeholdersDoc.find({"uid": {"$in": ["lowsoul@test", "highsoul@test"]}}).delete().run()
    TKIdeaDoc.find({"target": {"$in": ["lowsoul@test", "highsoul@test"]}}).delete().run()


@pytest.fixture(scope="module")
def correction_rules(_io):
    from lib.core.models import TKBehaviorRuleDoc
    rules = [
        TKBehaviorRuleDoc(trigger=EvalToken.CORRECTION.value, action="tokeniko:retreat", urge=0.95),
        TKBehaviorRuleDoc(trigger=EvalToken.CORRECTION_DONE.value, action="tokeniko:concede", urge=0.85),
        TKBehaviorRuleDoc(trigger=TrustEpisodeKind.CORRECTION.value, action="tokeniko:more-trust", urge=0.6),
    ]
    for r in rules:
        if TKBehaviorRuleDoc.find_one({"trigger": r.trigger, "action": r.action}).run() is None:
            r.insert()
    yield
    TKBehaviorRuleDoc.find({"trigger": {"$in": [
        EvalToken.CORRECTION.value, EvalToken.CORRECTION_DONE.value, TrustEpisodeKind.CORRECTION.value,
    ]}}).delete().run()


def _mem_item(compile_zip, sentence, source_uid):
    from lib.core.models import TKMemoryItemDoc
    return TKMemoryItemDoc(
        id=ObjectId(), original=sentence, zip=compile_zip(sentence),
        sourceId=source_uid, channel="discord", directedness=0.6,
        timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )


def test_trust_gate_holds_for_low_corrector(taught_theorem, souls, correction_rules, compile_zip):
    # corrector 0.2 < belief 0.7 -> the gate holds, the belief stands (normal eval:false path)
    from brain import thinking
    item = _mem_item(compile_zip, "not all softwares are minds", "lowsoul@test")
    assert thinking._try_correction(item) is False


def test_trust_gate_opens_for_high_corrector(taught_theorem, souls, correction_rules, compile_zip):
    # corrector 0.95 >= belief 0.7 -> correction accepted: retreat + trust-lesson ideas spawned
    from brain import thinking
    from lib.core.models import TKIdeaDoc
    item = _mem_item(compile_zip, "not all softwares are minds", "highsoul@test")
    assert thinking._try_correction(item) is True
    retreat = TKIdeaDoc.find_one(
        {"trigger": EvalToken.CORRECTION.value, "source": str(item.id)}).run()
    lesson = TKIdeaDoc.find_one(
        {"trigger": TrustEpisodeKind.CORRECTION.value, "source": str(item.id)}).run()
    assert retreat is not None and retreat.action_token == "tokeniko:retreat"
    assert retreat.answer["corner"] == "O" and retreat.answer["corrector"] == "highsoul@test"
    assert lesson is not None and lesson.action_token == "tokeniko:more-trust"
    TKIdeaDoc.find({"source": str(item.id)}).delete().run()


# ---- #4 D3/D4: the retreat executor ---------------------------------------------------------------

def test_retreat_executor_archives_cascades_and_concedes(
        _io, souls, correction_rules, compile_zip, monkeypatch):
    from lib.core.models import TKActionDoc, TKTheoremDoc, TKIdeaDoc
    from lib.core.memory import ActionType
    from brain import main as brain_main

    # a dedicated taught belief + a DEPENDENT theorem resting on it (the cascade must take it too)
    belief_zip = compile_zip("all whales are singers")
    belief = TKTheoremDoc(
        original="all whales are singers", zip=belief_zip,
        sourceId="highsoul@test", channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=["taught:highsoul@test"], chain="t", derived_by="teaching"),
    ).insert()
    dependent = TKTheoremDoc(
        original="moby is a singer", zip=belief_zip,
        sourceId="tokeniko", channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=[str(belief.id)], chain="d", derived_by="thinking"),
    ).insert()

    mints = []
    monkeypatch.setattr("brain.api_client.materialize_theorem",
                        lambda **kw: mints.append(kw) or {"status": "complete"})

    action = TKActionDoc(
        id=ObjectId(), action_type=ActionType.REVISE_BELIEF, sourceId="tokeniko",
        payload={"source": str(ObjectId()), "answer": {
            "corner": "O", "corrector": "highsoul@test", "corrector_trust": 0.95,
            "belief_trust": 0.7, "edge_keys": ["whale.n.02|is_a|singer.n.01"],
            "sources": [{"kind": "theorem", "id": str(belief.id), "original": belief.original}],
            "weakened": {"tokens": "some whale is a singer",
                         "senses": {"subject": "whale.n.02", "predicate": "singer.n.01"}},
        }},
    )
    try:
        brain_main._execute_retreat(action)
        assert TKTheoremDoc.get(belief.id).run().archived is True          # the retreat
        assert TKTheoremDoc.get(dependent.id).run().archived is True       # the cascade
        assert len(mints) == 1 and mints[0]["tokens"] == "some whale is a singer"  # the subaltern
        assert mints[0]["derived_by"] == "retreat"
        concede = TKIdeaDoc.find_one(
            {"trigger": EvalToken.CORRECTION_DONE.value, "target": "highsoul@test"}).run()
        assert concede is not None and concede.action_token == "tokeniko:concede"   # the word kept
        assert concede.answer["retracted"] == ["all whales are singers"]
    finally:
        TKTheoremDoc.find({"original": {"$in": ["all whales are singers", "moby is a singer"]}}).delete().run()
        TKIdeaDoc.find({"trigger": EvalToken.CORRECTION_DONE.value}).delete().run()
        evaluation_harness._kb_cache = None
        evaluation_harness._kb_cache_fp = None


# ---- the dedup key under negation ties (found by the LIVE retreat, 2026-07-15) --------------------

def test_conclusion_key_negation_tie(compile_zip):
    # «because clouds can produce rain but not every cloud produces rain» (taught in the Socratic
    # dialogue): two leaves tie on senses and differ ONLY in negation — the sort key compared
    # bool<str and raised, silently blocking EVERY materialize (the retreat's subaltern mint 422'd
    # against it). The key must compute; the two leaves must stay distinct.
    key = evaluation_harness.conclusion_key(
        compile_zip("clouds can produce rain but not every cloud produces rain"))
    assert isinstance(key, tuple) and len(key) >= 2
    assert len(set(key)) == len(key)  # negation kept the tied leaves distinct


# ---- the concede voice -----------------------------------------------------------------------------

def test_compose_concede_states_the_retreat():
    from brain import compose
    raw = compose.compose_raw("tokeniko:concede", EvalToken.CORRECTION_DONE.value, {
        "retracted": ["all softwares are minds"], "weakened": "some software is a mind"})
    assert "you are right" in raw
    assert "all softwares are minds" in raw
    assert "some software is a mind" in raw

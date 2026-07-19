# ------------------------------------------------------------------------------------------------
# THE UNTANGLER + THE DREAM — §0 slice 3 (2026-07-18). KB-wide reductio as sleep-phase belief
# hygiene: saturate everything through the mirror, convict by the fork-D bar (exactly ONE
# revisable premise among constitution/substrate — the r.a.a. itself convicts; logic never
# guesses), retreat through the belief-revision machinery, and tell the blog it was a DREAM.
# The tiered world mirrors the real incident: the two flanking premises are READONLY AXIOMS
# (the constitution), the stale «all minds are software» a taught THEOREM — the true poison was
# the taught row, and the bar convicts exactly it.
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

import pytest

from lib.core import evaluation_harness, untangle
from lib.core.memory import LifeEventKind, MEMChannels, MEMProvenance, TokenikoAction

_SIG_PART = "animal.n.01|animal.n.01"
_POISON_A = "all animals are minds"
_POISON_B = "all minds are software"      # the stale premise — the taught, revisable row
_POISON_C = "no software is an animal"


# ---- the conviction bar (pure) ------------------------------------------------------------------

def test_partition_premises_tiers():
    ro_axiom = SimpleNamespace(readonly=True, original="constitution")
    rw_axiom = SimpleNamespace(readonly=False, original="learned axiom")
    theorem = SimpleNamespace(original="taught theorem")   # theorems carry no readonly field
    revisable, protected = untangle.partition_premises([ro_axiom, rw_axiom, theorem])
    assert protected == [ro_axiom]
    assert revisable == [rw_axiom, theorem]


# ---- the dream composer (pure — fallback voice, injected empty souls) ---------------------------

def _dream_material(asked=0, retracted=None):
    return {"kind": "dream", "asked": asked, "significance": 0.9,
            "retracted": retracted if retracted is not None else [
                {"original": _POISON_B,
                 "absurd": "a mind is an animal and a mind is not an animal"}]}


def test_compose_dream_draft():
    from senses.blog import compose_draft
    draft = compose_draft(_dream_material(asked=2), souls_reader=lambda: [])
    assert draft.kind == "log"                       # the ship's-log of the sleeping mind
    assert any(_POISON_B in f for f in draft.facts)  # the retraction is named
    assert any("2" in f for f in draft.facts)        # the open tangles are counted
    assert draft.proof and any("impossib" in p for p in draft.proof)  # the absurd IS the proof


def test_compose_dream_requires_a_retraction():
    from senses.blog import compose_draft
    with pytest.raises(ValueError):
        compose_draft(_dream_material(retracted=[]), souls_reader=lambda: [])


# ---- the tiered world (pipeline) ----------------------------------------------------------------

@pytest.fixture()
def tiered_world(_io, compile_zip):
    """The incident's true shape: constitution flanks, taught poison in the middle, one dependent
    theorem resting on the poison (the cascade's witness). Function-scoped, fully swept."""
    from lib.core.models import TKAxiomDoc, TKBehaviorRuleDoc, TKIdeaDoc, TKTheoremDoc
    created = {"axioms": [], "theorems": []}
    for s in (_POISON_A, _POISON_C):
        doc = TKAxiomDoc(original=s, zip=compile_zip(s), sourceId="seed@rtest",
                         archived=False, readonly=True)
        doc.insert()
        created["axioms"].append(doc)
    belief = TKTheoremDoc(
        original=_POISON_B, zip=compile_zip(_POISON_B), sourceId="prof@rtest:1",
        channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=["taught:prof@rtest:1"], chain="t", derived_by="teaching"),
    )
    belief.insert()
    created["theorems"].append(belief)
    dependent = TKTheoremDoc(
        original="my code is a software", zip=compile_zip(_POISON_B), sourceId="tokeniko",
        channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=[str(belief.id)], chain="d", derived_by="thinking"),
    )
    dependent.insert()
    created["theorems"].append(dependent)
    rule = TKBehaviorRuleDoc(trigger=LifeEventKind.DREAM.value,
                             action=TokenikoAction.POST.value, urge=0.7)
    rule.insert()
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    yield {"belief": belief, "dependent": dependent}
    TKAxiomDoc.get_motor_collection().delete_many(
        {"original": {"$in": [_POISON_A, _POISON_C]}})
    TKTheoremDoc.get_motor_collection().delete_many(
        {"original": {"$in": [_POISON_B, "my code is a software"]}})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.DREAM.value})
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.DREAM.value})
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None


def _our(entries):
    return [e for e in entries if _SIG_PART in e["signature"]]


def test_dry_run_convicts_without_touching(tiered_world):
    from lib.core.models import TKTheoremDoc
    report = untangle.untangle_pass(apply=False)
    ours = _our(report["convicted"])
    assert ours, "the tiered conflict must be decidable: exactly one revisable premise"
    entry = ours[0]
    assert entry["original"] == _POISON_B and entry["kind"] == "theorem"
    assert entry["doc_id"] == str(tiered_world["belief"].id)
    assert "my code is a software" in entry["dependents"]      # the cascade previewed
    assert not _our(report["asked"]) and not _our(report["constitution"])
    # dry-run touched NOTHING
    assert TKTheoremDoc.get(tiered_world["belief"].id).run().archived is False
    assert report["residual"] == report["conflicts"]


def test_apply_retreats_cascades_and_cures(tiered_world):
    from lib.core.models import TKTheoremDoc
    report = untangle.untangle_pass(apply=True)
    assert _our(report["convicted"])
    assert TKTheoremDoc.get(tiered_world["belief"].id).run().archived is True     # the retreat
    assert TKTheoremDoc.get(tiered_world["dependent"].id).run().archived is True  # the cascade
    # the re-saturation is honest: our absurdity is gone from the residual world
    residual = untangle._saturate()
    assert not any(_SIG_PART in sig for sig in residual)


def test_two_revisable_premises_are_asked_not_guessed(tiered_world, _io):
    # flip one flanking axiom to revisable -> TWO candidates: the bar refuses to guess
    from lib.core.models import TKAxiomDoc, TKTheoremDoc
    ax = TKAxiomDoc.find_one({"original": _POISON_A}).run()
    ax.readonly = False
    ax.save()
    report = untangle.untangle_pass(apply=True)
    ours = _our(report["asked"])
    assert ours and set(ours[0]["candidates"]) == {_POISON_A, _POISON_B}
    assert not _our(report["convicted"])
    assert TKTheoremDoc.find_one({"original": _POISON_B}).run().archived is False  # untouched


def test_all_constitution_is_flagged_not_touched(_io, compile_zip):
    # the poison entirely in readonly axioms -> only the author's hand may move
    from lib.core.models import TKAxiomDoc
    docs = []
    try:
        for s in (_POISON_A, _POISON_B, _POISON_C):
            d = TKAxiomDoc(original=s, zip=compile_zip(s), sourceId="seed@rtest",
                           archived=False, readonly=True)
            d.insert()
            docs.append(d)
        report = untangle.untangle_pass(apply=True)
        assert _our(report["constitution"])
        assert not _our(report["convicted"]) and not _our(report["asked"])
        for d in docs:
            assert TKAxiomDoc.get(d.id).run().archived is False
    finally:
        TKAxiomDoc.get_motor_collection().delete_many(
            {"original": {"$in": [_POISON_A, _POISON_B, _POISON_C]}})
        evaluation_harness._kb_cache = None
        evaluation_harness._kb_cache_fp = None


# ---- the dream spawn (pipeline) -----------------------------------------------------------------

def test_spawn_dream_gates_on_postability(tiered_world):
    from brain import thinking
    from lib.core.models import TKIdeaDoc
    # a night whose only retraction is DM-tainted -> no public dream at all
    private = {"convicted": [{"original": _POISON_B, "absurd": "x and not x", "postable": False}],
               "asked": []}
    assert thinking.spawn_dream(private) is False
    assert TKIdeaDoc.find_one({"trigger": LifeEventKind.DREAM.value}).run() is None
    # a postable night dreams once — and the same night never dreams twice (source dedup)
    public = {"convicted": [{"original": _POISON_B, "absurd": "x and not x", "postable": True}],
              "asked": [{"signature": "s", "absurd": "y and not y"}]}
    assert thinking.spawn_dream(public) is True
    assert thinking.spawn_dream(public) is False
    ideas = TKIdeaDoc.find({"trigger": LifeEventKind.DREAM.value}).to_list()
    assert len(ideas) == 1
    material = ideas[0].material
    assert material["kind"] == "dream" and material["asked"] == 1
    # slice 5: every retraction carries the guess flag (False for an ordinary belief; a dropped
    # hypothesis dreams in its own register)
    assert material["retracted"] == [{"original": _POISON_B, "absurd": "x and not x",
                                      "guess": False}]

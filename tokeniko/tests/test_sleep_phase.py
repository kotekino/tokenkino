# ------------------------------------------------------------------------------------------------
# THE SLEEP PHASE — §0 slice 3.5 (2026-07-18, the author's design: "he falls asleep wondering").
# Sleep is a MODE, never a blocker: the phase routing keeps running (the reactive probe IS the
# wake sensor), so any event that would have exited wondering exits sleep by construction. Covered
# here: the night's duty (one KB-change-gated untangle pass, apply — safe unsupervised by the
# fork-D bar), the dream stash-and-tell-on-waking discipline, the wake helper, and the reboot-is-
# a-wake recovery. The loop's clock arithmetic is deliberately thin — the helpers carry the logic.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core import evaluation_harness
from lib.core.memory import LifeEventKind, MEMChannels, MEMProvenance, TokenikoAction

_POISON_A = "all animals are minds"
_POISON_B = "all minds are software"
_POISON_C = "no software is an animal"


@pytest.fixture()
def night_world(_io, compile_zip):
    """The tiered poison (constitution flanks + one taught revisable premise) + the life:dream
    rule + a fresh brain_state row dedicated to the test. Fully swept."""
    from lib.core.models import (TKAxiomDoc, TKBehaviorRuleDoc, TKBrainStateDoc,
                                 TKIdeaDoc, TKTheoremDoc)
    axioms = []
    for s in (_POISON_A, _POISON_C):
        d = TKAxiomDoc(original=s, zip=compile_zip(s), sourceId="seed@stest",
                       archived=False, readonly=True)
        d.insert()
        axioms.append(d)
    belief = TKTheoremDoc(
        original=_POISON_B, zip=compile_zip(_POISON_B), sourceId="prof@stest:1",
        channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
        provenance=MEMProvenance(premises=["taught:prof@stest:1"], chain="t", derived_by="teaching"),
    )
    belief.insert()
    rule = TKBehaviorRuleDoc(trigger=LifeEventKind.DREAM.value,
                             action=TokenikoAction.POST.value, urge=0.7)
    rule.insert()
    bs = TKBrainStateDoc(key="sleep-test")
    bs.insert()
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    yield {"bs": bs, "belief": belief}
    TKAxiomDoc.get_motor_collection().delete_many({"original": {"$in": [_POISON_A, _POISON_C]}})
    TKTheoremDoc.get_motor_collection().delete_many({"original": _POISON_B})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.DREAM.value})
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.DREAM.value})
    TKBrainStateDoc.get_motor_collection().delete_many({"key": "sleep-test"})
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None


def test_sleep_duty_untangles_and_stashes_the_dream(night_world):
    from brain import main as brain_main
    from lib.core.models import TKIdeaDoc, TKTheoremDoc
    bs = night_world["bs"]
    brain_main._sleep_duty(bs)
    # the retreat happened in his sleep (the fork-D bar convicted the taught premise)
    assert TKTheoremDoc.get(night_world["belief"].id).run().archived is True
    # the dream is STASHED, not yet told — the telling never disturbs the sleep
    assert bs.pending_dream is not None
    assert any(c["original"] == _POISON_B for c in bs.pending_dream["convicted"])
    assert TKIdeaDoc.find_one({"trigger": LifeEventKind.DREAM.value}).run() is None
    # the watermark advanced: the same night never re-saturates (deep rest)
    assert bs.last_untangled_kb_at > 0
    stash = bs.pending_dream
    brain_main._sleep_duty(bs)
    assert bs.pending_dream == stash  # unchanged — the second call was a no-op


def test_wake_tells_the_dream_once(night_world):
    from brain import main as brain_main
    from lib.core.models import TKIdeaDoc
    bs = night_world["bs"]
    brain_main._sleep_duty(bs)
    bs.asleep_since = 1
    bs.save()
    assert brain_main._wake(bs, 100.0, "test") is None
    assert bs.asleep_since is None
    assert bs.pending_dream is None                    # the stash is consumed
    ideas = TKIdeaDoc.find({"trigger": LifeEventKind.DREAM.value}).to_list()
    assert len(ideas) == 1                             # ☀️ the dream is told
    assert ideas[0].material["kind"] == "dream"
    assert any(r["original"] == _POISON_B for r in ideas[0].material["retracted"])
    # waking again with nothing stashed is a quiet no-op
    assert brain_main._wake(bs, 100.0, "test") is None
    assert len(TKIdeaDoc.find({"trigger": LifeEventKind.DREAM.value}).to_list()) == 1


def test_wake_when_awake_is_identity(night_world):
    from brain import main as brain_main
    bs = night_world["bs"]
    assert brain_main._wake(bs, None, "test") is None  # not asleep — nothing happens
    assert bs.pending_dream is None


def test_reboot_wake_recovers_the_dream(night_world):
    # a mid-night crash: asleep_since set, dream stashed — the coordinator's startup recovery
    # (reboot is a wake) is _spawn_pending_dream + the flag clear; prove the pieces compose.
    from brain import main as brain_main
    from lib.core.models import TKIdeaDoc
    bs = night_world["bs"]
    brain_main._sleep_duty(bs)
    bs.asleep_since = 1
    bs.save()
    # ... the process dies here; the next life starts:
    bs.asleep_since = None
    bs.save()
    brain_main._spawn_pending_dream(bs)
    assert bs.pending_dream is None
    assert TKIdeaDoc.find_one({"trigger": LifeEventKind.DREAM.value}).run() is not None


# ---- the morning questions (the obsession guard, author's ruling 2026-07-18) --------------------

@pytest.fixture()
def undecidable_night(_io, compile_zip):
    """TWO revisable premises (both taught theorems) -> the night cannot convict; the tangle is
    stashed and re-asked on waking. Includes the reduct rule + a reachable teacher + an OPEN
    ledger row (the awake-time reconcile already asked once)."""
    from lib.core import evaluation_harness
    from lib.core.memory import EvalToken, ReductioStatus
    from lib.core.models import (TKBehaviorRuleDoc, TKBrainStateDoc, TKIdeaDoc,
                                 TKMemoryStakeholdersDoc, TKReductioDoc, TKTheoremDoc)
    prof = TKMemoryStakeholdersDoc(name="prof", uid="prof@mtest:1", trust=0.95,
                                   channel=MEMChannels.DISCORD, contextKey="mchan:11").insert()
    theorems = []
    for s in (_POISON_A, _POISON_B, _POISON_C):
        theorems.append(TKTheoremDoc(
            original=s, zip=compile_zip(s), sourceId="prof@mtest:1",
            channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
            provenance=MEMProvenance(premises=["taught:prof@mtest:1"], chain="t",
                                     derived_by="teaching"),
        ).insert())
    rule = TKBehaviorRuleDoc(trigger=EvalToken.ABSURDITY.value,
                             action=TokenikoAction.REDUCT.value, urge=0.95)
    rule.insert()
    bs = TKBrainStateDoc(key="morning-test")
    bs.insert()
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    yield {"bs": bs, "prof": prof}
    TKTheoremDoc.get_motor_collection().delete_many(
        {"original": {"$in": [_POISON_A, _POISON_B, _POISON_C]}})
    TKReductioDoc.get_motor_collection().delete_many({})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": EvalToken.ABSURDITY.value})
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": EvalToken.ABSURDITY.value})
    TKMemoryStakeholdersDoc.get_motor_collection().delete_many({"uid": "prof@mtest:1"})
    TKBrainStateDoc.get_motor_collection().delete_many({"key": "morning-test"})
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None


def test_morning_question_reasks_the_open_tangle(undecidable_night):
    from brain import main as brain_main
    from brain import thinking
    from lib.core import evaluation_harness
    from lib.core.memory import EvalToken
    from lib.core.models import TKIdeaDoc, TKReductioDoc
    bs = undecidable_night["bs"]

    # the awake-time reconcile asks ONCE (the ledger opens; the first question goes out)
    conflicts = []
    evaluation_harness.kb_wonder(collect_conflicts=conflicts)
    thinking._reductio_reconcile(conflicts)
    first = TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()
    assert first, "the awake reconcile must have asked"
    # a second reconcile pass does NOT re-ask (asked-once within the waking day)
    thinking._reductio_reconcile(conflicts)
    assert len(TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()) == len(first)

    # the night runs: nothing convicted (two revisable premises), the tangle is STASHED
    brain_main._sleep_duty(bs)
    assert bs.pending_dream is None                     # no conviction -> no dream
    assert bs.pending_questions is not None
    assert bs.pending_questions["signatures"]

    # ☀️ waking re-asks the still-open tangle — a FRESH idea despite the same open row
    brain_main._wake(bs, 100.0, "test")
    after_wake = TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()
    assert len(after_wake) > len(first), "waking still-tangled must ask again"
    assert bs.pending_questions is None                 # the stash is consumed
    # and the ledger row itself is untouched (still OPEN, same generation)
    rows = TKReductioDoc.find({"status": "open"}).to_list()
    assert rows and all(r.generation == 0 for r in rows)


def test_morning_question_skips_a_resolved_row(undecidable_night):
    # the tangle was answered while he slept -> the row resolved -> the morning stays quiet
    from brain import main as brain_main
    from brain import thinking
    from lib.core import evaluation_harness
    from lib.core.memory import EvalToken, ReductioStatus
    from lib.core.models import TKIdeaDoc, TKReductioDoc
    bs = undecidable_night["bs"]
    conflicts = []
    evaluation_harness.kb_wonder(collect_conflicts=conflicts)
    thinking._reductio_reconcile(conflicts)
    n_before = len(TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list())
    brain_main._sleep_duty(bs)
    assert bs.pending_questions is not None
    TKReductioDoc.get_motor_collection().update_many(
        {}, {"$set": {"status": ReductioStatus.RESOLVED.value}})
    brain_main._wake(bs, 100.0, "test")
    assert bs.pending_questions is None
    assert len(TKIdeaDoc.find({"trigger": EvalToken.ABSURDITY.value}).to_list()) == n_before


def test_sleep_duty_deep_rest_on_unchanged_kb(_io):
    # no poison inserted, watermark pinned at "now"-ish: the duty must not re-saturate at all
    from brain import main as brain_main
    from brain import thinking
    from lib.core.models import TKBrainStateDoc
    bs = TKBrainStateDoc(key="sleep-test-2")
    bs.insert()
    try:
        bs.last_untangled_kb_at = thinking._kb_max_createdat() + 1
        called = []
        import lib.core.untangle as untangle_mod
        orig = untangle_mod.untangle_pass
        untangle_mod.untangle_pass = lambda **kw: called.append(1) or {}
        try:
            brain_main._sleep_duty(bs)
        finally:
            untangle_mod.untangle_pass = orig
        assert called == []                            # deep rest — no saturation ran
        assert bs.pending_dream is None
    finally:
        TKBrainStateDoc.get_motor_collection().delete_many({"key": "sleep-test-2"})

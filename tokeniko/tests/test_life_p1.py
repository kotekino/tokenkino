"""Blog output channel P1 — the life:* trigger namespace. Sandbox memory DB.

A genuinely-new POSTABLE theorem spawns life:theorem (significance-modulated urge); a trust fold
that ACTUALLY MOVES spawns life:encounter; "DM never public" gates postability at every
materialization site (and the wondering premise-AND cascades the taint); tokeniko:post plans on
the PUBLIC channel, broadcast (target None), feasible iff it carries its material.

Calibration under test (rule urges from scripts/seed_behavior_rules.py, act threshold 0.5):
  life:theorem @ 0.65 — plain sig 0.7 -> 0.455 silent; taught/multi-hop sig 0.8 -> 0.52 posts.
  life:encounter @ 0.7 — flat sig 0.9 -> 0.63 posts.
"""
import pytest
from bson import ObjectId

from lib.core.memory import (
    ActionStatus, ActionType, LifeEventKind, MEMChannels, TokenikoAction, TrustEpisodeKind,
)
from lib.core.tkzip import TKZip, TKZipItem, TKZipContent


_TEACHER = "life-p1-hellen@discord:11"
_SPEAKER = "life-p1-john@discord:12"

# the seeded personality rows (mirror scripts/seed_behavior_rules.py — the calibration under test)
_THEOREM_RULE_URGE = 0.65
_ENCOUNTER_RULE_URGE = 0.7


def _zip():
    # minimal VALID lesson leaf (the headless-teaching belt, 2026-07-18: a subject-less stand-in
    # is no longer teachable — like any real taught assertion, the fixture carries a subject).
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
        subject=None, predicate=None, direct=None,
        senses={"subject": "wisdom.n.01", "predicate": "begin.v.01"})))


def _mk_soul(uid, name, trust=0.95, imprint=False):
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc(uid=uid, name=name, isMe=False,
                                   channel=MEMChannels.DISCORD, trust=trust,
                                   imprint=imprint).save()


def _mk_item(original, source_doc_id, directedness=0.9, channel=MEMChannels.DISCORD):
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(original=original, sourceId=source_doc_id, channel=channel,
                           directedness=directedness, zip=_zip())
    item.insert()
    return item


def _seed_life_rules():
    from lib.core.models import TKBehaviorRuleDoc
    TKBehaviorRuleDoc(trigger=LifeEventKind.THEOREM.value,
                      action=TokenikoAction.POST.value, urge=_THEOREM_RULE_URGE).insert()
    TKBehaviorRuleDoc(trigger=LifeEventKind.ENCOUNTER.value,
                      action=TokenikoAction.POST.value, urge=_ENCOUNTER_RULE_URGE).insert()


@pytest.fixture()
def clean_life(_io):
    from lib.core.models import (
        TKActionDoc, TKBehaviorRuleDoc, TKIdeaDoc, TKMemoryItemDoc,
        TKMemoryStakeholdersDoc, TKTheoremDoc, TKTrustEpisodeDoc,
    )
    def _wipe():
        # Bunnet gotcha: .find().delete() is a silent no-op without .run(); the memory timeseries
        # additionally needs the raw pymongo delete_many.
        TKMemoryItemDoc.get_motor_collection().delete_many({})
        TKMemoryStakeholdersDoc.find({"uid": {"$regex": "^life-p1-"}}).delete().run()
        TKTrustEpisodeDoc.find({"stakeholder_uid": {"$regex": "^life-p1-"}}).delete().run()
        TKTheoremDoc.find({"original": {"$regex": "^life-p1:"}}).delete().run()
        TKIdeaDoc.find({"trigger": {"$regex": "^life:"}}).delete().run()
        TKActionDoc.find({"action_type": ActionType.UPDATE_TRUST.value}).delete().run()
        TKBehaviorRuleDoc.find({"trigger": {"$regex": "^life:"}}).delete().run()
    _wipe()
    _seed_life_rules()
    yield
    _wipe()


def _life_theorem_ideas():
    from lib.core.models import TKIdeaDoc
    return TKIdeaDoc.find({"trigger": LifeEventKind.THEOREM.value}).to_list()


# ---- 1+2. the provenance gate at materialize_taught (+ the life:theorem spawn) -----------------------

def test_taught_channel_graded_is_postable_and_spawns_life_theorem(_io, clean_life):
    from brain.thinking import materialize_taught
    from lib.core.models import TKTheoremDoc
    teacher = _mk_soul(_TEACHER, "life-p1-hellen", trust=0.95)
    item = _mk_item("life-p1: wisdom begins in wonder", str(teacher.id), directedness=0.9)
    assert materialize_taught(item) is not None
    thm = TKTheoremDoc.find_one({"original": "life-p1: wisdom begins in wonder"}).run()
    assert thm is not None and thm.postable is True        # channel talk (0.9) is NOT a DM
    ideas = _life_theorem_ideas()
    assert len(ideas) == 1
    idea = ideas[0]
    assert idea.source == str(thm.id)                      # theorem-sourced, not memory-sourced
    assert idea.material["kind"] == "theorem"
    assert idea.material["theorem_id"] == str(thm.id)
    assert idea.material["derived_by"] == "teaching"
    # significance: base 0.7 + taught 0.1 (single-hop, non-personal) = 0.8; urge = 0.65 x 0.8
    assert idea.material["significance"] == pytest.approx(0.8)
    assert idea.urge == pytest.approx(_THEOREM_RULE_URGE * 0.8)


def test_taught_in_a_dm_is_not_postable_and_stays_silent(_io, clean_life):
    from brain.thinking import materialize_taught
    from lib.core.models import TKTheoremDoc
    teacher = _mk_soul(_TEACHER, "life-p1-hellen", trust=0.95)
    item = _mk_item("life-p1: a private lesson", str(teacher.id), directedness=1.0)  # a Discord DM
    assert materialize_taught(item) is not None                # learned all the same (knowledge is knowledge)
    thm = TKTheoremDoc.find_one({"original": "life-p1: a private lesson"}).run()
    assert thm is not None and thm.postable is False       # DM never public
    assert _life_theorem_ideas() == []                     # ...and never an urge to post it


# ---- 3. the significance helper: ordering + the calibration bands ------------------------------------

def test_significance_ordering_and_calibration_bands(_io):
    from brain.thinking import life_theorem_significance
    from brain.main import URGE_THRESHOLD
    plain = life_theorem_significance(
        "wondering", "chain: all bird have feathers -> bird has feathers", personal=False)
    multi = life_theorem_significance(
        "wondering", "chain: cat —is_a→ carnivore -> all carnivore eat meat -> cat eat meat",
        personal=False)
    taught = life_theorem_significance("teaching", "taught by hellen", personal=False)
    personal_taught = life_theorem_significance("teaching", "taught by hellen", personal=True)
    assert plain == pytest.approx(0.7)
    assert multi == pytest.approx(0.8) == taught
    assert personal_taught == pytest.approx(1.0)           # 0.7 + 0.2 + 0.1, clamp holds it at 1.0
    assert plain < multi < personal_taught
    # the calibration bands: plain x rule urge stays BELOW the act threshold; taught clears it.
    assert plain * _THEOREM_RULE_URGE < URGE_THRESHOLD <= taught * _THEOREM_RULE_URGE
    # encounter: flat significance clears the threshold at its rule urge
    from brain.thinking import ENCOUNTER_SIGNIFICANCE
    assert ENCOUNTER_SIGNIFICANCE * _ENCOUNTER_RULE_URGE >= URGE_THRESHOLD


# ---- 4. plan_action + score_feasibility for tokeniko:post --------------------------------------------

def test_plan_action_post_is_public_broadcast_with_material(_io, clean_life):
    from brain import behavior
    from lib.core.models import TKIdeaDoc
    material = {"kind": "theorem", "theorem_id": str(ObjectId()), "original": "life-p1: x",
                "derived_by": "wondering", "premises": [], "chain": [], "significance": 0.8}
    idea = TKIdeaDoc(trigger=LifeEventKind.THEOREM.value,
                     action_token=TokenikoAction.POST.value, urge=0.52,
                     source=material["theorem_id"], material=material)
    idea.insert()
    plan = behavior.plan_action(idea, "tokeniko-uid")
    assert plan["action_type"] == ActionType.POST_CONTENT
    assert plan["channel"] == MEMChannels.PUBLIC           # never the source channel
    assert plan["target"] is None                          # broadcast self-expression, not directed
    assert plan["payload"]["material"] == material
    assert "destination" not in plan["payload"]            # no thread-back on a broadcast
    assert behavior.score_feasibility(plan) == 1.0
    # without its material a post has nothing to compose from -> honestly infeasible
    bare = TKIdeaDoc(trigger=LifeEventKind.THEOREM.value,
                     action_token=TokenikoAction.POST.value, urge=0.52)
    bare.insert()
    bare_plan = behavior.plan_action(bare, "tokeniko-uid")
    assert behavior.score_feasibility(bare_plan) == 0.0


# ---- 5. life:encounter — spawned iff the fold ACTUALLY MOVED ------------------------------------------

def _drain_update_trust(action_id):
    import brain.main as brain_main
    from lib.core.models import TKActionDoc
    for _ in range(20):
        act = TKActionDoc.get(ObjectId(str(action_id))).run()  # Bunnet: .run() executes
        if act.status == ActionStatus.DONE:
            return
        assert brain_main.actions_phase() is True
    raise AssertionError("update_trust action never drained")


def _mk_trust_action(target_uid, source_item_id):
    from lib.core.models import TKActionDoc
    action = TKActionDoc(
        action_type=ActionType.UPDATE_TRUST, sourceId="tok", targetId=target_uid,
        channel=MEMChannels.INTERNAL,
        payload={"action_token": TokenikoAction.MORE_TRUST.value,
                 "trigger": TrustEpisodeKind.AGREEMENT.value,
                 "source": source_item_id, "answer": {"note": "corroborated by my KB"}})
    action.insert()
    return action


def test_fold_move_spawns_life_encounter(_io, clean_life):
    from lib.core.models import TKIdeaDoc
    soul = _mk_soul(_SPEAKER, "life-p1-john", trust=0.5)   # neutral, NOT imprinted -> fold moves
    item = _mk_item("life-p1: the sun is a star", str(soul.id))
    action = _mk_trust_action(_SPEAKER, str(item.id))
    _drain_update_trust(action.id)
    ideas = TKIdeaDoc.find({"trigger": LifeEventKind.ENCOUNTER.value}).to_list()
    assert len(ideas) == 1
    idea = ideas[0]
    assert idea.source == str(item.id)                     # the memory item behind the episode
    assert idea.material["kind"] == "encounter"
    assert idea.material["soul_uid"] == _SPEAKER
    assert idea.material["episode"] == TrustEpisodeKind.AGREEMENT.value
    assert idea.material["trust_after"] == pytest.approx(0.52)  # 0.5 + 0.02, folded
    assert idea.urge == pytest.approx(_ENCOUNTER_RULE_URGE * 0.9)  # flat significance 0.9


def test_imprinted_soul_records_episode_but_no_encounter(_io, clean_life):
    from lib.core.models import TKIdeaDoc, TKTrustEpisodeDoc
    soul = _mk_soul(_SPEAKER, "life-p1-john", trust=0.5, imprint=True)  # pinned: fold NEVER moves
    item = _mk_item("life-p1: the moon is a rock", str(soul.id))
    action = _mk_trust_action(_SPEAKER, str(item.id))
    _drain_update_trust(action.id)
    eps = TKTrustEpisodeDoc.find({"stakeholder_uid": _SPEAKER}).to_list()
    assert len(eps) == 1                                   # the trail stays honest where the scalar is pinned
    assert TKIdeaDoc.find({"trigger": LifeEventKind.ENCOUNTER.value}).to_list() == []


# ---- 6. the wondering premise-AND -----------------------------------------------------------------------

def test_premises_postable_poisons_on_a_dm_tainted_premise(_io, clean_life):
    from brain.thinking import _premises_postable
    from lib.core.models import TKTheoremDoc
    poison = TKTheoremDoc(original="life-p1: poison premise", sourceId="tok",
                          channel=MEMChannels.INTERNAL, archived=False, postable=False)
    poison.save()
    clean = TKTheoremDoc(original="life-p1: clean premise", sourceId="tok",
                         channel=MEMChannels.INTERNAL, archived=False, postable=True)
    clean.save()
    # matched by Mongo id (the edge_trust currency) AND by original (the fallback) — both poison
    assert _premises_postable([str(poison.id)]) is False
    assert _premises_postable(["life-p1: poison premise"]) is False
    # a postable premise, an unmatched axiom id and a graph-edge key all pass
    assert _premises_postable([str(clean.id)]) is True
    assert _premises_postable([str(ObjectId()), "cat.n.01|is_a|carnivore.n.01"]) is True
    assert _premises_postable([]) is True
    # one poisoned premise among clean ones poisons the conclusion (the AND)
    assert _premises_postable([str(clean.id), str(poison.id)]) is False

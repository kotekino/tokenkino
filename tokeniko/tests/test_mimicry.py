# ------------------------------------------------------------------------------------------------
# LEARNED SCAFFOLDS FROM THE AUDIENCE (roadmap §1, 2026-07-24) — two-stage linguistic accommodation.
# Stage one (brain/mimicry.mimic_observe): while talking with a decently-trusted person, a phrasing
# of theirs that re-expresses an act he already performs joins his shelf SCOPED to that person (a
# MIMIC row) — his voice with everyone else is untouched. Stage two (brain/main._consolidate_mimicry):
# the night promotes the deserving picked-up phrasings to a durable global voice and retires the rest
# (never deletes — biography). Under test: the gate ladder (self / momentum / trust / Lane A / Lane B
# / the quality fence), the compose scope gate + the `used` adoption tick, and the sleep promote-or-
# retire criteria. Parser-free by construction — Mongo + the context ring + geometry only.
# ------------------------------------------------------------------------------------------------
import json
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from brain import context, mimicry


_ALICE = "mimic-alice@discord:1"
_BOB = "mimic-bob@discord:1"
_ROOM = "mimic-room-1"


def _wipe():
    from lib.core.models import (TKScaffoldDoc, TKMemoryStakeholdersDoc, TKTrustEpisodeDoc)
    # every row this suite makes carries the MIMICX marker in its template (minted rows inherit it
    # from the item's original) — one regex sweep clears the shelf; souls/episodes by uid prefix.
    TKScaffoldDoc.get_motor_collection().delete_many({"template": {"$regex": "MIMICX"}})
    TKMemoryStakeholdersDoc.get_motor_collection().delete_many({"uid": {"$regex": "^mimic-"}})
    TKTrustEpisodeDoc.get_motor_collection().delete_many({"stakeholder_uid": {"$regex": "^mimic-"}})


@pytest.fixture(autouse=True)
def _fresh(_io):
    context.reset()
    _wipe()
    yield
    _wipe()
    context.reset()


def _soul(uid, trust=0.7, imprint=False):
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc(uid=uid, name=uid.split("@")[0], isMe=False,
                                   trust=trust, imprint=imprint).save()


def _item(original="MIMICX a plain turn", source=_ALICE, zp=None, social=None,
          channel_id=_ROOM, item_id="mimic-item"):
    return SimpleNamespace(
        original=original, zip=zp, sourceId=source, channel="discord",
        metadata=json.dumps({"channel_id": channel_id}),
        timestamp=datetime.now(timezone.utc), social=social, social_at=None, id=item_id,
    )


# feed `n` prior turns from `source` into the room's ring (momentum-building), warm skipped.
def _prime(source, n, channel_id=_ROOM):
    context._warmed.add(channel_id)
    for i in range(n):
        context.context_add(_item(source=source, channel_id=channel_id, item_id=f"prime-{i}"))


# the production sequence: thinking runs context_add(item) THEN mimic_observe(item).
def _observe(item):
    context.context_add(item)
    return mimicry.mimic_observe(item)


def _scoped_rows(scope):
    from lib.core.models import TKScaffoldDoc
    return TKScaffoldDoc.find({"scope": scope}).to_list()


# ---- gate: momentum («after a while») ----------------------------------------------------------

def test_momentum_two_priors_no_mint_three_priors_mints(_io):
    _soul(_ALICE, trust=0.7)
    trigger = _item(original="MIMICX heyyy", social="greeting")
    _prime(_ALICE, 2)                                   # 2 prior turns + the trigger = depth 3
    assert _observe(trigger) is False                  # prior=2 < 3 -> below momentum
    assert _scoped_rows(_ALICE) == []
    context.reset()
    _prime(_ALICE, 3)                                   # 3 prior turns + the trigger = depth 4
    assert _observe(trigger) is True                   # prior=3 >= 3 -> converges
    assert len(_scoped_rows(_ALICE)) == 1


# ---- gate: trust («decent») --------------------------------------------------------------------

def test_trust_below_bar_never_mints(_io):
    _soul(_ALICE, trust=0.5)                            # < 0.6, a near-stranger
    _prime(_ALICE, 3)
    assert _observe(_item(original="MIMICX heyyy", social="greeting")) is False
    assert _scoped_rows(_ALICE) == []


# ---- gate 1: never self ------------------------------------------------------------------------

def test_self_speech_never_mints(_io):
    from lib.core.io import get_tokeniko
    me = get_tokeniko()
    _prime(me.uid, 3)                                   # even with momentum + full self-trust...
    got = _observe(_item(original="MIMICX heyyy", source=me.uid, social="greeting"))
    assert got is False                                # ...his own words are never picked up
    assert _scoped_rows(me.uid) == []


# ---- Lane A: a social act, verbatim, scoped, zip-less ------------------------------------------

def test_lane_a_greeting_mints_verbatim_scoped_zipless(_io):
    soul = _soul(_ALICE, trust=0.8)
    _prime(_ALICE, 3)
    assert _observe(_item(original="MIMICX yo yo what's good", social="greeting")) is True
    rows = _scoped_rows(_ALICE)
    assert len(rows) == 1
    row = rows[0]
    assert row.category == "greet"                     # greeting -> the greet act
    assert row.template == "MIMICX yo yo what's good"  # his raw words, verbatim
    assert row.zip is None                             # a greeting is not a claim
    assert row.scope == soul.uid and row.enabled is True
    assert row.provenance == f"mimic:{soul.uid}"
    assert row.trusted == pytest.approx(0.8)


def test_lane_a_thanks_is_skipped(_io):
    _soul(_ALICE, trust=0.8)
    _prime(_ALICE, 3)
    # `thanks` has no speakable category yet (the reciprocal-thanks is parked) — recognized, skipped
    assert _observe(_item(original="MIMICX many thanks friend", social="thanks")) is False
    assert _scoped_rows(_ALICE) == []


# ---- Lane B: a slot-less whole-zip match -------------------------------------------------------

def _global_learnable(category, zp, template="MIMICX i concur"):
    from lib.core.models import TKScaffoldDoc
    return TKScaffoldDoc(category=category, template=template, slots=[], zip=zp,
                         scope=None, enabled=True, provenance="seed").insert()


def test_lane_b_match_mints_matched_category_and_item_zip(_io, compile_zip):
    zp = compile_zip("water is a liquid")
    _global_learnable("agree", zp)                     # a global, slot-less, zip-bearing learnable row
    soul = _soul(_ALICE, trust=0.8)
    _prime(_ALICE, 3)
    trigger = _item(original="MIMICX water's a liquid, for sure", zp=compile_zip("water is a liquid"))
    assert _observe(trigger) is True                   # identical zip -> match >= floor
    rows = _scoped_rows(_ALICE)
    assert len(rows) == 1
    assert rows[0].category == "agree"                 # the matched act being re-phrased
    assert rows[0].zip is not None                     # Lane B rows carry the item's OWN zip
    assert rows[0].template == "MIMICX water's a liquid, for sure"
    assert rows[0].scope == soul.uid


def test_lane_b_below_floor_does_not_mint(_io, compile_zip, monkeypatch):
    zp = compile_zip("water is a liquid")
    _global_learnable("agree", zp)
    _soul(_ALICE, trust=0.8)
    _prime(_ALICE, 3)
    monkeypatch.setattr(mimicry, "evaluator_compareZip", lambda a, b: 0.5)  # deterministically far
    trigger = _item(original="MIMICX something unrelated", zp=compile_zip("water is a liquid"))
    assert _observe(trigger) is False
    assert _scoped_rows(_ALICE) == []


# ---- the quality fence -------------------------------------------------------------------------

def test_dedup_same_template_one_row(_io):
    _soul(_ALICE, trust=0.8)
    _prime(_ALICE, 3)
    trigger = _item(original="MIMICX heyyy", social="greeting")
    assert _observe(trigger) is True
    assert _observe(trigger) is False                  # the exact phrasing already sits in greet
    assert len(_scoped_rows(_ALICE)) == 1


def test_braces_and_length_fences(_io):
    _soul(_ALICE, trust=0.8)
    _prime(_ALICE, 3)
    # a brace would collide with str.format at bind time
    assert _observe(_item(original="MIMICX hi {there}", social="greeting")) is False
    # a mannerism is short, not a monologue
    long = "MIMICX " + "a" * 130
    assert _observe(_item(original=long, social="greeting")) is False
    assert _scoped_rows(_ALICE) == []


def test_cap_fence_bounds_per_talker_growth(_io):
    from lib.core.models import TKScaffoldDoc
    soul = _soul(_ALICE, trust=0.8)
    for i in range(8):                                 # the talker already lent MIMIC_CAP rows
        TKScaffoldDoc(category="greet", template=f"MIMICX cap {i}", slots=[], zip=None,
                      scope=soul.uid, enabled=True, provenance=f"mimic:{soul.uid}").insert()
    _prime(_ALICE, 3)
    assert _observe(_item(original="MIMICX one more please", social="greeting")) is False
    assert len(_scoped_rows(_ALICE)) == 8              # growth bound held


# ---- the compose scope gate + the `used` adoption tick -----------------------------------------

def test_scoped_row_visible_only_to_its_target(_io):
    from lib.core.models import TKScaffoldDoc
    import random
    from lib.core.voice import creative_compose
    TKScaffoldDoc(category="greet", template="MIMICX heyyy", slots=[], scope=_ALICE,
                  enabled=True, provenance=f"mimic:{_ALICE}").insert()
    rng = random.Random(1)
    # speaking BACK to Alice: her picked-up phrasing is on the shelf
    assert creative_compose("greet", target=_ALICE, rng=rng) == "MIMICX heyyy"
    # to anyone else (or no target): the scoped row is invisible -> the curated fallback speaks
    assert creative_compose("greet", target=_BOB, rng=rng) == "hello!"
    assert creative_compose("greet", target=None, rng=rng) == "hello!"


def test_used_ticks_on_a_scoped_pick_not_on_a_seed(_io):
    from lib.core.models import TKScaffoldDoc
    import random
    from lib.core.voice import creative_compose
    scoped = TKScaffoldDoc(category="greet", template="MIMICX heyyy", slots=[], scope=_ALICE,
                           enabled=True, provenance=f"mimic:{_ALICE}", used=0).insert()
    seed = TKScaffoldDoc(category="farewell", template="MIMICX bye now", slots=[], scope=None,
                         enabled=True, provenance="seed", used=0).insert()
    creative_compose("greet", target=_ALICE, rng=random.Random(1))
    creative_compose("farewell", target=_ALICE, rng=random.Random(1))
    assert TKScaffoldDoc.get(scoped.id).run().used == 1   # the mimic pick counts (adoption signal)
    assert TKScaffoldDoc.get(seed.id).run().used == 0     # a global seed never ticks


def test_no_matching_scope_falls_back_never_mutes(_io):
    import random
    from lib.core.voice import creative_compose
    # no scoped rows at all for this target -> the never-mute fallback is untouched
    assert creative_compose("greet", target=_ALICE, rng=random.Random(1)) == "hello!"


# ---- the sleep consolidation: promote-or-retire ------------------------------------------------

def _mimic_row(scope, used=0, category="greet", template="MIMICX heyyy", created=None):
    from lib.core.models import TKScaffoldDoc
    row = TKScaffoldDoc(category=category, template=template, slots=[], zip=None, scope=scope,
                        enabled=True, provenance=f"mimic:{scope}", trusted=0.7, weight=1.0, used=used)
    if created is not None:
        row.createdAt = created
    return row.insert()


def _reload(row_id):
    from lib.core.models import TKScaffoldDoc
    return TKScaffoldDoc.get(row_id).run()


def test_consolidation_promotes_by_use(_io):
    from brain import main as brain_main
    _soul(_ALICE, trust=0.95)                          # highly trusted NOW
    row = _mimic_row(_ALICE, used=1)                   # he actually reached for it — affinity
    brain_main._consolidate_mimicry(None)
    got = _reload(row.id)
    assert got.enabled is True and got.scope is None   # promoted to a durable global voice
    assert got.provenance == f"taught:{_ALICE}"
    assert got.weight == pytest.approx(0.5)            # seasons the voice; curated stays dominant
    assert got.trusted == pytest.approx(0.9)           # min(teacher_trust, 0.9)
    assert got.used == 1                               # biography kept


def test_consolidation_promotes_by_episode_proximity(_io):
    from brain import main as brain_main
    from lib.core.models import TKTrustEpisodeDoc
    from lib.core.memory import TrustEpisodeKind
    _soul(_ALICE, trust=0.95)
    now = int(time.time())
    row = _mimic_row(_ALICE, used=0, created=now)      # never used...
    TKTrustEpisodeDoc(stakeholder_uid=_ALICE, kind=TrustEpisodeKind.KICKER, delta=+0.1,
                      timestamp=now).insert()          # ...but a positive episode sits close in time
    brain_main._consolidate_mimicry(None)
    got = _reload(row.id)
    assert got.scope is None and got.enabled is True   # promoted on the affinity episode
    assert got.provenance == f"taught:{_ALICE}"


def test_consolidation_retires_on_low_trust(_io):
    from brain import main as brain_main
    _soul(_ALICE, trust=0.7)                           # decent enough to mimic, below the teaching bar
    row = _mimic_row(_ALICE, used=1)                   # affinity present, but trust < 0.9
    brain_main._consolidate_mimicry(None)
    got = _reload(row.id)
    assert got.enabled is False                        # retired — never deleted
    assert got.scope == _ALICE                         # everything else untouched
    assert got.provenance == f"mimic:{_ALICE}"


def test_consolidation_retires_on_no_affinity(_io):
    from brain import main as brain_main
    _soul(_ALICE, trust=0.95)                          # highly trusted...
    row = _mimic_row(_ALICE, used=0, created=int(time.time()))  # ...but never used, no episode near
    brain_main._consolidate_mimicry(None)
    got = _reload(row.id)
    assert got.enabled is False                        # no affinity -> retired
    assert got.scope == _ALICE

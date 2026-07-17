# ------------------------------------------------------------------------------------------------
# The context ring + the anecdote (compose 2.0 slice 5, 2026-07-17 — case 3, the first UNPROMPTED
# speech; the working-memory SEED, hunch 20's social column). Under test: the ring as a DERIVABLE
# cache (feed/evict/warm-from-timeseries — a reset IS a restart), the topic centroid (others' talk
# only), the association scan's social gates (conservative floor / cooldown / novelty), the
# thinking trigger's ambient-band + quiet-verdict discipline, and the mouth (router + side-note
# register + the verbatim fence). Synthetic centroids via monkeypatch — no live KB dependency.
# ------------------------------------------------------------------------------------------------
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest

from brain import context


@pytest.fixture(autouse=True)
def _fresh_ring(_io):
    context.reset()
    yield
    context.reset()


def _item(original="water is a liquid", zp=None, source="john@test", channel="discord",
          channel_id="room-1", ts=None, directedness=0.6, item_id="ctx-item"):
    import json
    return SimpleNamespace(
        original=original, zip=zp, sourceId=source, channel=channel,
        metadata=json.dumps({"channel_id": channel_id}),
        timestamp=ts or datetime.now(timezone.utc), directedness=directedness, id=item_id,
    )


# ---- the ring: a derivable cache ----------------------------------------------------------------------

def test_ring_feeds_and_caps(compile_zip):
    zp = compile_zip("water is a liquid")
    context._warmed.add("room-1")            # cold start for this unit (warm tested separately)
    for i in range(40):
        context.context_add(_item(zp=zp, item_id=f"i{i}"))
    ring = context._rings["room-1"]
    assert len(ring) == context._RING_MAX    # capped, oldest evicted


def test_ring_warms_from_the_timeseries(compile_zip):
    # the cache is DERIVABLE: rows already in memory appear in the ring on first touch
    import json
    from lib.core.models import TKMemoryItemDoc
    from lib.core.memory import MEMChannels
    zp = compile_zip("gold is a metal")
    stored = TKMemoryItemDoc(
        original="gold is a metal", zip=zp, sourceId="hellen@test", targetId="t",
        channel=MEMChannels.DISCORD, metadata=json.dumps({"channel_id": "warm-room"}),
        timestamp=datetime.now(timezone.utc),
    )
    stored.insert()
    try:
        context.context_add(_item(zp=None, channel_id="warm-room", item_id="live-1"))
        originals = [r.original for r in context._rings["warm-room"]]
        assert "gold is a metal" in originals       # warmed from the tail
        assert originals[-1] == "water is a liquid"  # the live feed lands after
    finally:
        # timeseries delete needs raw pymongo (the bunnet no-op gotcha)
        TKMemoryItemDoc.get_motor_collection().delete_many({"original": "gold is a metal"})


def test_topic_centroid_reads_others_only(compile_zip):
    zp = compile_zip("water is a liquid")
    context._warmed.add("room-1")
    me = context._self_uid()
    context.context_add(_item(zp=zp, source=me or "self", item_id="mine-1"))
    if me is not None:
        assert context.topic_centroid("room-1") is None   # his own speech defines no topic
    context.context_add(_item(zp=zp, source="john@test", item_id="other-1"))
    assert context.topic_centroid("room-1") is not None


# ---- the association scan: the social gates ------------------------------------------------------------

def _fake_kb(monkeypatch, notions):
    monkeypatch.setattr(context, "_load_kb_centroids", lambda: notions)


def test_floor_rejects_far_notions(compile_zip, monkeypatch):
    zp = compile_zip("water is a liquid")
    context._warmed.add("room-1")
    context.context_add(_item(zp=zp))
    topic = context.topic_centroid("room-1")
    near = topic / (np.linalg.norm(topic) or 1.0)
    _fake_kb(monkeypatch, [("kb-far", "far notion", -near)])   # cosine -1: maximally far
    assert context.find_association("room-1") is None
    _fake_kb(monkeypatch, [("kb-near", "water boils at one hundred degrees", near)])
    assoc = context.find_association("room-1")
    assert assoc is not None and assoc["proximity"] > 0.99
    assert assoc["notion"] == "water boils at one hundred degrees"


def test_cooldown_and_novelty(compile_zip, monkeypatch):
    zp = compile_zip("water is a liquid")
    context._warmed.add("room-1")
    context.context_add(_item(zp=zp))
    topic = context.topic_centroid("room-1")
    _fake_kb(monkeypatch, [("kb-1", "a notion", topic)])
    assert context.find_association("room-1") is not None
    context.record_anecdote("room-1", "kb-1")
    assert context.find_association("room-1") is None          # the cooldown holds
    context._last_anecdote["room-1"] = time.time() - context._ANECDOTE_COOLDOWN_S - 1
    assert context.find_association("room-1") is None          # novelty: kb-1 was told here
    _fake_kb(monkeypatch, [("kb-1", "a notion", topic), ("kb-2", "another notion", topic)])
    assoc = context.find_association("room-1")
    assert assoc is not None and assoc["notion_id"] == "kb-2"  # the fresh notion speaks


# ---- the thinking trigger: ambient band + spawn discipline ---------------------------------------------

def test_anecdote_fires_only_in_the_ambient_band(monkeypatch, _io):
    from brain import thinking, behavior
    calls, spawns = [], []
    monkeypatch.setattr(context, "channel_key", lambda item: "room-x")
    monkeypatch.setattr(context, "find_association",
                        lambda key: calls.append(key) or {"notion": "n", "notion_id": "id",
                                                          "proximity": 0.8})
    monkeypatch.setattr(context, "record_anecdote", lambda key, nid: None)
    monkeypatch.setattr(behavior, "spawn_ideas_for",
                        lambda *a, **kw: spawns.append(kw) or [object()])
    thinking._try_anecdote(_item(directedness=1.0))    # a DM — never a side-note
    thinking._try_anecdote(_item(directedness=0.15))   # someone else's thread — polite silence
    assert calls == []
    thinking._try_anecdote(_item(directedness=0.6))    # ambient — the opening
    assert calls == ["room-x"] and len(spawns) == 1
    assert spawns[0]["urge_scale"] == pytest.approx((1 + 0.8) / 2)   # proximity IS the itch


def test_record_only_when_the_idea_spawned(monkeypatch, _io):
    from brain import thinking, behavior
    recorded = []
    monkeypatch.setattr(context, "channel_key", lambda item: "room-y")
    monkeypatch.setattr(context, "find_association",
                        lambda key: {"notion": "n", "notion_id": "id", "proximity": 0.9})
    monkeypatch.setattr(context, "record_anecdote", lambda key, nid: recorded.append(nid))
    monkeypatch.setattr(behavior, "spawn_ideas_for", lambda *a, **kw: [])   # dedup swallowed it
    thinking._try_anecdote(_item(directedness=0.6))
    assert recorded == []                     # no idea -> the cooldown is NOT armed


# ---- the mouth: router + the side-note register --------------------------------------------------------

def test_mention_routes_the_notion_verbatim(_io):
    import random
    from lib.core.memory import TokenikoAction
    from brain.compose import compose_raw, _route
    cat, data = _route(TokenikoAction.MENTION.value, None, {"notion": "a coin stores value"})
    assert cat == "anecdote" and data == {"notion": "a coin stores value"}
    assert _route(TokenikoAction.MENTION.value, None, None) is None   # no notion, no words
    text = compose_raw(TokenikoAction.MENTION.value, None,
                       {"notion": "a coin stores value"}, rng=random.Random(1))
    assert text == "that reminds me — a coin stores value"            # fallback register + fence


def test_mention_is_dispatchable(_io):
    from lib.core.memory import TokenikoAction
    from brain.behavior import _DISPATCH, _SELF_RELEVANT_TRIGGERS
    from lib.core.memory import EvalToken
    assert TokenikoAction.MENTION.value in _DISPATCH
    assert EvalToken.ASSOCIATION.value in _SELF_RELEVANT_TRIGGERS

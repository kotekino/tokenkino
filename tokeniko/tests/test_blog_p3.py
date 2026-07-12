"""Blog output channel P3 — the PUBLIC-channel carrier + the stats heartbeat. Sandbox memory DB.

deliver_one_public composes payload["material"] via compose_post and ships the transmission
contract (WITHOUT the internal `polished` flag) to /transmissions; a payload["snapshot"] ships
VERBATIM to /mind; neither key, an uncomposable material, a raised push or a non-2xx status all
land FAILED (no auto-retry, no raise); dry-run (flag OR missing INGEST_API_KEY) marks DONE
without touching the push function. brain/heartbeat.build_snapshot returns the six KPI metric
keys + the sparkline series as finite counts (souls excludes isMe); _should_beat is the pure
tick-modulo x min-seconds cadence guard. NO network: the push function is always injected.
"""
import asyncio
from datetime import datetime

import pytest

from lib.core.memory import ActionStatus, ActionType, MEMChannels


_TRANSMISSION_KEYS = {"slug", "date", "kind", "title", "excerpt", "body", "readMin"}

# a fixed compose_post result (the P2 contract, `polished` included — P3 must strip it)
_POST = {
    "slug": "theorem-blog-p3-fixed",
    "date": "2026-07-12T00:00:00+00:00",
    "kind": "argument",
    "title": "I derived something",
    "excerpt": "I derived something new today.",
    "body": ["I derived something new today.", "How I know: a -> b."],
    "readMin": 1,
    "polished": True,
}

_MATERIAL = {"kind": "theorem", "original": "blog-p3: x", "derived_by": "wondering",
             "premises": [], "chain": [], "significance": 0.8}


@pytest.fixture()
def clean_public(_io):
    from lib.core.models import TKActionDoc
    def _wipe():
        # Bunnet gotcha: .find().delete() is a silent no-op without .run()
        TKActionDoc.find({"channel": MEMChannels.PUBLIC.value}).delete().run()
    _wipe()
    yield
    _wipe()


def _mk_action(payload):
    from lib.core.models import TKActionDoc
    action = TKActionDoc(action_type=ActionType.POST_CONTENT, sourceId="tok",
                         channel=MEMChannels.PUBLIC, payload=payload)
    action.insert()
    return action


def _status_of(action):
    from lib.core.models import TKActionDoc
    return TKActionDoc.get(action.id).run().status  # Bunnet: .run() executes


def _capture(status=201, exc=None):
    """An injected push stub: records (url, body) calls, returns `status` or raises `exc`."""
    calls = []

    async def post_fn(url, body):
        if exc is not None:
            raise exc
        calls.append((url, body))
        return status

    return post_fn, calls


def _patch_compose(monkeypatch, result=_POST):
    import senses.blog_outbound as bo
    seen = []

    async def fake_compose(material):
        seen.append(material)
        return result

    monkeypatch.setattr(bo, "compose_post", fake_compose)
    return seen


def _live_env(monkeypatch):
    # flags are read lazily (the go-live lesson); the key value is a test dummy, never a secret
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "0")
    monkeypatch.setenv("INGEST_API_KEY", "test-key-not-real")


# ---- 1. material -> compose -> /transmissions, `polished` stripped, DONE -----------------------------

def test_material_composes_and_ships_transmission(_io, clean_public, monkeypatch):
    import senses.blog_outbound as bo
    _live_env(monkeypatch)
    seen = _patch_compose(monkeypatch)
    post_fn, calls = _capture(status=201)
    action = _mk_action({"material": _MATERIAL})

    assert asyncio.run(bo.deliver_one_public(post_fn)) is True
    assert seen == [_MATERIAL]                        # compose_post got the material verbatim
    (url, body), = calls
    assert url.endswith("/transmissions")
    assert set(body) == _TRANSMISSION_KEYS            # the exact contract...
    assert "polished" not in body                     # ...with the internal flag stripped
    assert body["slug"] == _POST["slug"]
    assert _status_of(action) == ActionStatus.DONE


# ---- 2. snapshot -> /mind verbatim, DONE ---------------------------------------------------------------

def test_snapshot_ships_verbatim_to_mind(_io, clean_public, monkeypatch):
    import senses.blog_outbound as bo
    _live_env(monkeypatch)
    snapshot = {"state": "thinking", "doing": "x", "uptimeSec": 5,
                "metrics": {"definitions": 1, "inferencesPerCycle": 0},
                "activity": [{"at": "2026-07-12T00:00:00+00:00", "text": "post_content [done]"}]}
    post_fn, calls = _capture(status=201)
    action = _mk_action({"snapshot": snapshot})

    assert asyncio.run(bo.deliver_one_public(post_fn)) is True
    (url, body), = calls
    assert url.endswith("/mind")
    assert body == snapshot                           # verbatim — the brain built the contract body
    assert _status_of(action) == ActionStatus.DONE


# ---- 3. neither material nor snapshot -> FAILED --------------------------------------------------------

def test_payload_with_neither_key_fails(_io, clean_public, monkeypatch):
    import senses.blog_outbound as bo
    _live_env(monkeypatch)
    post_fn, calls = _capture()
    action = _mk_action({"something": "else"})

    assert asyncio.run(bo.deliver_one_public(post_fn)) is True
    assert calls == []
    assert _status_of(action) == ActionStatus.FAILED


def test_uncomposable_material_fails(_io, clean_public, monkeypatch):
    import senses.blog_outbound as bo
    _live_env(monkeypatch)
    _patch_compose(monkeypatch, result=None)          # compose_post rejected the material
    post_fn, calls = _capture()
    action = _mk_action({"material": {"kind": "weird"}})

    assert asyncio.run(bo.deliver_one_public(post_fn)) is True
    assert calls == []
    assert _status_of(action) == ActionStatus.FAILED


# ---- 4. push failure (exception / non-2xx) -> FAILED, never raises -------------------------------------

def test_push_exception_and_non_2xx_fail_without_raising(_io, clean_public, monkeypatch):
    import senses.blog_outbound as bo
    _live_env(monkeypatch)
    _patch_compose(monkeypatch)

    raising_fn, _ = _capture(exc=RuntimeError("network down"))
    action1 = _mk_action({"material": _MATERIAL})
    assert asyncio.run(bo.deliver_one_public(raising_fn)) is True  # handled, no raise
    assert _status_of(action1) == ActionStatus.FAILED

    rejected_fn, calls = _capture(status=401)
    action2 = _mk_action({"snapshot": {"state": "idle", "metrics": {}}})
    assert asyncio.run(bo.deliver_one_public(rejected_fn)) is True
    assert len(calls) == 1                            # pushed, rejected -> FAILED
    assert _status_of(action2) == ActionStatus.FAILED


# ---- 5. dry-run (flag OR missing key) -> DONE without touching the push function -----------------------

def test_dryrun_marks_done_without_pushing(_io, clean_public, monkeypatch):
    import senses.blog_outbound as bo
    _patch_compose(monkeypatch)
    post_fn, calls = _capture()

    # the SENSES_DELIVER_DRYRUN flag itself (the outbound.py semantics, default-on)
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "1")
    monkeypatch.setenv("INGEST_API_KEY", "test-key-not-real")
    action1 = _mk_action({"material": _MATERIAL})
    assert asyncio.run(bo.deliver_one_public(post_fn)) is True
    assert _status_of(action1) == ActionStatus.DONE

    # live flag but NO key -> nothing could authenticate: dry-run too
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "0")
    monkeypatch.delenv("INGEST_API_KEY", raising=False)
    action2 = _mk_action({"snapshot": {"state": "idle", "metrics": {}}})
    assert asyncio.run(bo.deliver_one_public(post_fn)) is True
    assert _status_of(action2) == ActionStatus.DONE

    assert calls == []                                # the push function was never touched


# ---- 6. build_snapshot — honest counts, contract shape, souls excludes isMe ----------------------------

def test_build_snapshot_shape_and_souls_exclude_me(_io, clean_public):
    from brain.heartbeat import build_snapshot
    from lib.core.models import TKMemoryStakeholdersDoc

    snap = build_snapshot("wondering")
    assert snap["state"] == "wondering"
    assert isinstance(snap["doing"], str) and snap["doing"]
    assert isinstance(snap["uptimeSec"], int) and snap["uptimeSec"] >= 0

    expected = {"definitions", "axiomsRules", "theorems", "dictionary",
                "souls", "trustEpisodes", "inferencesPerCycle"}
    assert set(snap["metrics"]) == expected
    for key, value in snap["metrics"].items():
        assert isinstance(value, int) and value >= 0, key  # finite numbers per the contract

    for entry in snap["activity"]:
        assert set(entry) == {"at", "text"}
        datetime.fromisoformat(entry["at"])           # parseable ISO
        assert isinstance(entry["text"], str) and entry["text"]
    assert len(snap["activity"]) <= 5

    # souls = every known mind EXCEPT himself (tokeniko exists in the sandbox via get_tokeniko)
    total = TKMemoryStakeholdersDoc.find_all().count()
    me = TKMemoryStakeholdersDoc.find({"isMe": True}).count()
    assert me >= 1
    assert snap["metrics"]["souls"] == total - me


# ---- 7. the pure heartbeat cadence guard ----------------------------------------------------------------

def test_should_beat_wall_clock_only():
    # WALL-CLOCK cadence (the never-beat lesson, 2026-07-12): tick duration varies 0.05s-30s+
    # (a wondering tick renders via Ollama), so a tick-modulo gate delayed the first live beat
    # indefinitely. min_seconds is the ONLY cadence gate; tick>0 is just the boot guard.
    from brain.heartbeat import _should_beat
    kw = {"min_seconds": 300.0}
    assert _should_beat(1, 0.0, 1000.0, **kw) is True       # first tick after boot beats at once
    assert _should_beat(0, 0.0, 1000.0, **kw) is False      # tick 0 never beats (boot guard)
    assert _should_beat(7, 900.0, 1000.0, **kw) is False    # only 100s elapsed
    assert _should_beat(7, 650.0, 1000.0, **kw) is True     # 350s >= 300s — any tick number
    assert _should_beat(9999, 999.9, 1000.0, **kw) is False # sub-threshold gap never beats


def test_delivered_requires_the_api_envelope():
    # the false-200 lesson: a frontend catch-all's 200+HTML must never read as delivered.
    from senses.blog_outbound import _delivered
    assert _delivered(201, '{"success": true, "data": {"slug": "x"}}') is True
    assert _delivered(200, '{"success": true}') is True
    assert _delivered(200, "<!DOCTYPE html><html>...") is False       # the actual incident shape
    assert _delivered(200, '{"success": false, "message": "no"}') is False
    assert _delivered(401, '{"success": true}') is False              # status still gates

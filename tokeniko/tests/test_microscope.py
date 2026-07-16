"""rag3 P1 — the microscope (the instrument arc, 2026-07-14 summit).

Covers the three organs: the DIGEST (pure — a deterministic structural rendering of a zip), the
JUDGE (schema/validation behavior over a fake client — same discipline as the blog polish tests:
any failure returns None, never raises), and the PASS (sandbox: inputs-only filtering, dedup by
item_id, an entry written with the verdict). The memory collection is a TIMESERIES — cleanup uses
raw pymongo delete_many (the bunnet delete no-op).
"""
import asyncio
import json

import pytest

from lib.core.memory import MEMChannels
from lib.core.tk import TKOperator, TKQuantifier, TKWhRole
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from senses import microscope


# ---- the digest (pure) -----------------------------------------------------------------------

def _leaf(op=TKOperator.AND, **over):
    fields = dict(senses={"subject": "coin.n.01", "predicate": "have.v.01", "direct": "value.n.01"},
                  quantifier=TKQuantifier.INDEFINITE)
    fields.update(over)
    return TKZipItem(op=op, content=TKZipContent(subject=None, predicate=None, direct=None, **fields))


def test_digest_renders_roles_operators_and_flags():
    zp = TKZip(map=[0.0] * 8, items=TKZipItem(content=[
        _leaf(),
        _leaf(op=TKOperator.CONV, senses={"subject": "person.n.01", "predicate": "state.v.01"},
              quantifier=TKQuantifier.GENERIC, negated=True),
    ]))
    d = microscope.digest_zip(zp)
    assert "subject: coin.n.01" in d and "direct: value.n.01" in d
    assert "op=CONV" in d                      # the operator survives — the storm's tell
    assert "negated=True" in d
    assert "quantifier=indefinite" in d


def test_digest_carries_mood_and_identity():
    zp = TKZip(map=[0.0] * 8, items=TKZipItem(content=[
        _leaf(dubitative=1.0, wh_role=TKWhRole.TIME,
              identities={"subject": "kotekino@discord:1"}),
    ]))
    d = microscope.digest_zip(zp)
    assert "mood=question" in d and "wh_role=time" in d
    assert "kotekino@discord:1" in d


def test_digest_is_deterministic():
    zp = TKZip(map=[0.0] * 8, items=TKZipItem(content=[_leaf()]))
    assert microscope.digest_zip(zp) == microscope.digest_zip(zp)


# ---- the judge (fake client) ------------------------------------------------------------------

class _FakeMessages:
    def __init__(self, text=None, exc=None):
        self._text, self._exc = text, exc

    async def create(self, **kwargs):
        if self._exc:
            raise self._exc
        block = type("B", (), {"type": "text", "text": self._text})()
        return type("R", (), {"content": [block]})()


class _FakeClient:
    def __init__(self, text=None, exc=None):
        self.messages = _FakeMessages(text=text, exc=exc)


_GOOD = {"verdict": "mismatch", "confidence": 0.9, "severity": "high",
         "category": "operator-flattening", "note": "the IF clause reads as a bare assertion"}


def test_judge_returns_the_validated_verdict():
    out = asyncio.run(microscope.judge("s", "d", client=_FakeClient(text=json.dumps(_GOOD))))
    assert out["verdict"] == "mismatch" and out["category"] == "operator-flattening"
    from lib.rag import RAG3_JUDGE
    assert out["model"] == RAG3_JUDGE.model


def test_judge_clamps_confidence():
    payload = dict(_GOOD, confidence=7.5)
    out = asyncio.run(microscope.judge("s", "d", client=_FakeClient(text=json.dumps(payload))))
    assert out["confidence"] == 1.0


@pytest.mark.parametrize("bad", [
    dict(exc=RuntimeError("api down")),
    dict(text="not json {"),
    dict(text=json.dumps({"verdict": "maybe", "confidence": 0.5,
                          "severity": None, "category": None, "note": None})),
])
def test_judge_failure_returns_none_never_raises(bad):
    assert asyncio.run(microscope.judge("s", "d", client=_FakeClient(**bad))) is None


# ---- the pass (sandbox) -----------------------------------------------------------------------

@pytest.fixture()
def clean_microscope(_io):
    from lib.core.io import init_io  # noqa: F401 (the _io fixture already ran it)
    from lib.core.models import TKMemoryItemDoc, TKZipDebugDoc

    def _wipe():
        TKZipDebugDoc.find({"original": {"$regex": "^rag3-test"}}).delete().run()
        # the memory collection is a TIMESERIES: bunnet delete is a silent no-op — raw pymongo
        col = TKMemoryItemDoc.get_motor_collection()
        col.delete_many({"original": {"$regex": "^rag3-test"}})

    _wipe()
    yield
    _wipe()


def _mk_item(original, source_id):
    from lib.core.models import TKMemoryItemDoc
    zp = TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
        subject=None, predicate=None, direct=None,
        senses={"subject": "coin.n.01", "predicate": "have.v.01"})))
    item = TKMemoryItemDoc(original=original, sourceId=source_id,
                           channel=MEMChannels.DISCORD, zip=zp)
    item.insert()
    return item


def test_pass_judges_only_others_inputs_and_dedups(_io, clean_microscope):
    from lib.core.io import get_tokeniko
    from lib.core.models import TKZipDebugDoc
    me = str(get_tokeniko().id)
    _mk_item("rag3-test self talk", me)                       # self: never judged (inputs-only)
    other = _mk_item("rag3-test a coin has value", "someone-else")

    fake = _FakeClient(text=json.dumps(dict(_GOOD, verdict="ok", severity=None, category=None)))
    n = asyncio.run(microscope.microscope_pass(client=fake, batch=10))
    assert n == 1
    entries = TKZipDebugDoc.find({"original": {"$regex": "^rag3-test"}}).to_list()
    assert len(entries) == 1
    assert entries[0].item_id == str(other.id) and entries[0].verdict == "ok"
    assert "coin.n.01" in entries[0].digest

    # second pass: everything already judged -> nothing written (dedup by item_id)
    assert asyncio.run(microscope.microscope_pass(client=fake, batch=10)) == 0


def test_judge_maps_sentinels_to_none():
    # the schema carries no null unions (the API rejects enum-vs-type-array) — "none"/"" come back
    # as sentinels and must land as real Nones in the entry
    payload = {"verdict": "ok", "confidence": 0.95, "severity": "none", "category": "none", "note": ""}
    out = asyncio.run(microscope.judge("s", "d", client=_FakeClient(text=json.dumps(payload))))
    assert out["verdict"] == "ok"
    assert out["severity"] is None and out["category"] is None and out["note"] is None

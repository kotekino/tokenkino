"""Senses B — deepen the 1:1: (B1) delivered speech becomes zip-less biography; (B2) the open-why
derivation (context DERIVED from the memory timeseries — structural reply-threading first, recency
fallback); (B3) the live inbound runs the preparser and forwards reply_to. Sandbox memory DB."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from lib.core.memory import ActionStatus, ActionType, MEMChannels


def _mem_insert(_io, original, source, target, minutes_ago, meta=None, with_zip=False):
    from lib.core.models import TKMemoryItemDoc
    from lib.core.tkzip import TKZip, TKZipItem, TKZipContent
    item = TKMemoryItemDoc(
        original=original, sourceId=source, targetId=target, channel=MEMChannels.DISCORD,
        metadata=json.dumps(meta) if meta else None,
        zip=TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
            subject=None, predicate=None, direct=None))) if with_zip else None,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    item.insert()
    return item


@pytest.fixture()
def clean_mem(_io):
    yield
    from lib.core.models import TKMemoryItemDoc
    TKMemoryItemDoc.get_motor_collection().delete_many({})  # sandbox only


@pytest.fixture()
def me_id(_io):
    from lib.core.models import TKMemoryStakeholdersDoc
    me = TKMemoryStakeholdersDoc.find_one({"isMe": True}).run()
    import brain.thinking as thinking
    thinking._self_source_id = None  # reset the lazy cache per test session state
    return str(me.id)


# ---- B1: delivered speech -> memory ----------------------------------------------------------------

def test_live_send_records_self_speech(_io, clean_mem, monkeypatch):
    import senses.outbound as outbound
    from lib.core.models import TKActionDoc, TKMemoryItemDoc
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "0")
    outbound._self_id = None
    action = TKActionDoc(
        action_type=ActionType.SEND_MESSAGE, sourceId="tok", targetId="asker-id",
        channel=MEMChannels.DISCORD,
        payload={"raw": "why is that?", "destination": {"channel_id": "333", "reply_to": "111"}})
    action.insert()

    async def sender(dest, content):
        return "sent-777"

    try:
        assert asyncio.run(outbound.deliver_one(sender)) is True
        rec = TKMemoryItemDoc.find_one({"original": "why is that?"}).run()
        assert rec is not None and rec.zip is None          # biography, invisible to the reaction loop
        assert rec.targetId == "asker-id"
        assert json.loads(rec.metadata)["message_id"] == "sent-777"  # the structural hook
    finally:
        fresh = TKActionDoc.get(action.id).run()
        if fresh is not None:
            fresh.delete()


def test_dryrun_records_nothing(_io, clean_mem, monkeypatch):
    import senses.outbound as outbound
    from lib.core.models import TKActionDoc, TKMemoryItemDoc
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "1")
    action = TKActionDoc(
        action_type=ActionType.SEND_MESSAGE, sourceId="tok", targetId="asker-id",
        channel=MEMChannels.DISCORD,
        payload={"raw": "hello", "destination": {"channel_id": "333"}})
    action.insert()
    try:
        assert asyncio.run(outbound.deliver_one(None)) is True
        assert TKMemoryItemDoc.find_one({"original": "hello"}).run() is None
    finally:
        fresh = TKActionDoc.get(action.id).run()
        if fresh is not None:
            fresh.delete()


# ---- B2: the open-why derivation --------------------------------------------------------------------

def test_structural_reply_derivation(_io, clean_mem, me_id):
    from brain.thinking import _derive_reply_context
    q = _mem_insert(_io, "why is that?", me_id, "speaker-1", 5, meta={"message_id": "sent-1"})
    ans = _mem_insert(_io, "because you think", "speaker-1", me_id, 1,
                      meta={"reply_to": "sent-1"}, with_zip=True)
    hit = _derive_reply_context(ans)
    assert hit is not None and str(hit.id) == str(q.id)


def test_recency_derivation_without_threading(_io, clean_mem, me_id):
    from brain.thinking import _derive_reply_context
    q = _mem_insert(_io, "why is that?", me_id, "speaker-1", 5, meta={"message_id": "sent-1"})
    ans = _mem_insert(_io, "because you think", "speaker-1", me_id, 1, with_zip=True)  # no reply_to
    hit = _derive_reply_context(ans)
    assert hit is not None and str(hit.id) == str(q.id)


def test_interleaved_speech_closes_the_window(_io, clean_mem, me_id):
    from brain.thinking import _derive_reply_context
    _mem_insert(_io, "why is that?", me_id, "speaker-1", 10, meta={"message_id": "sent-1"})
    _mem_insert(_io, "the sky is blue", "speaker-1", me_id, 5, with_zip=True)  # spoke since -> closed
    ans = _mem_insert(_io, "because you think", "speaker-1", me_id, 1, with_zip=True)
    assert _derive_reply_context(ans) is None


def test_non_question_self_speech_opens_nothing(_io, clean_mem, me_id):
    from brain.thinking import _derive_reply_context
    _mem_insert(_io, "yes", me_id, "speaker-1", 5, meta={"message_id": "sent-1"})  # an answer, not a question
    ans = _mem_insert(_io, "because you think", "speaker-1", me_id, 1, with_zip=True)
    assert _derive_reply_context(ans) is None


# ---- B3: inbound params ------------------------------------------------------------------------------

def test_inbound_params_carry_prepare_and_reply_to():
    from senses.inbound import dm_input_params
    from lib.discord.models import DiscordMessage
    msg = DiscordMessage(message_id="111", author_id="222", author_name="renzo",
                         channel_id="333", content="beause you think", reply_to="999",
                         is_dm=True, is_self=False)
    p = dm_input_params(msg)
    assert p["prepare"] == 1
    assert json.loads(p["metadata"])["reply_to"] == "999"

"""P3 — the speaking half: deliver_one ships the action's RAW symbolic text (no Ollama polish —
author's call 2026-07-09, the creation/nuance layer is a later chapter) to the Destination forwarded
by P2, threaded via reply_to. Sandbox memory DB; the sender is a capture stub (no socket, no Ollama).
"""
import asyncio

import pytest

from lib.core.memory import ActionStatus, ActionType, MEMChannels


@pytest.fixture()
def discord_action(_io):
    from lib.core.models import TKActionDoc
    action = TKActionDoc(
        action_type=ActionType.SEND_MESSAGE,
        sourceId="tokeniko-uid",
        targetId="asker-stakeholder-id",
        channel=MEMChannels.DISCORD,
        payload={"action_token": "tokeniko:answer", "raw": "yes",
                 "destination": {"channel_id": "333", "reply_to": "111"}},
    )
    action.insert()
    yield action
    from lib.core.models import TKActionDoc as T
    fresh = T.get(action.id).run()
    if fresh is not None:
        fresh.delete()


def test_deliver_ships_raw_to_forwarded_destination(_io, discord_action, monkeypatch):
    import senses.outbound as outbound
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "0")   # flags are read lazily (the go-live lesson)
    # (SENSES_OUTBOUND_POLISH retired 2026-07-16 — composed text ships verbatim, no polish path)
    sent = []

    async def sender(dest, content):
        sent.append((dest, content))
        return "msg-999"

    assert asyncio.run(outbound.deliver_one(sender)) is True
    (dest, content), = sent
    assert content == "yes"                      # RAW, unpolished — no Ollama in the loop
    assert dest.channel_id == "333"
    assert dest.reply_to == "111"                # threads under the asker's exact message

    from lib.core.models import TKActionDoc
    fresh = TKActionDoc.get(discord_action.id).run()
    assert fresh.status == ActionStatus.DONE


def test_dryrun_never_touches_the_sender(_io, discord_action, monkeypatch):
    import senses.outbound as outbound
    monkeypatch.setenv("SENSES_DELIVER_DRYRUN", "1")
    sent = []

    async def sender(dest, content):
        sent.append(content)
        return "x"

    assert asyncio.run(outbound.deliver_one(sender)) is True
    assert sent == []                             # dry-run: logged, marked DONE, no socket

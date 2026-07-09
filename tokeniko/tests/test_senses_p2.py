"""P2 — the reply thread-back: plan_action forwards the source memory item's reply coordinates
(P1 stamped them as metadata) into payload["destination"], so the outbound executor threads the
answer under the exact message that caused it. Sandbox memory DB (conftest); docs cleaned per test.
"""
import json

import pytest

from lib.core.memory import MEMChannels


@pytest.fixture()
def discord_question(_io):
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(
        original="are you a software?",
        sourceId="asker-stakeholder-id",
        targetId="tokeniko-id",
        channel=MEMChannels.DISCORD,
        metadata=json.dumps({"channel_id": "333", "message_id": "111"}),
        directedness=1.0,
    )
    item.insert()
    yield item
    # memory is a timeseries -> raw pymongo delete (Bunnet .delete() is a no-op there)
    TKMemoryItemDoc.get_motor_collection().delete_many({"_id": item.id})


def _idea(source_id, token="tokeniko:answer", target="asker-stakeholder-id"):
    from lib.core.models import TKIdeaDoc
    return TKIdeaDoc(trigger="eval:question", action_token=token,
                     source=str(source_id), target=target,
                     answer={"kind": "polar", "verdict": "yes", "confidence": 1.0})


def test_destination_forwarded_and_feasible(_io, discord_question):
    from brain.behavior import plan_action, score_feasibility
    plan = plan_action(_idea(discord_question.id), "tokeniko-uid")
    assert plan["channel"] == MEMChannels.DISCORD
    assert plan["payload"]["destination"] == {"channel_id": "333", "reply_to": "111"}
    assert score_feasibility(plan) == 1.0  # explicit coords are always addressable


def test_internal_reflex_gets_no_destination(_io, discord_question):
    from brain.behavior import plan_action
    plan = plan_action(_idea(discord_question.id, token="tokeniko:guess", target=None), "tokeniko-uid")
    assert plan["channel"] == MEMChannels.INTERNAL
    assert "destination" not in plan["payload"]


def test_malformed_metadata_is_ignored(_io):
    from lib.core.models import TKMemoryItemDoc
    from brain.behavior import plan_action
    item = TKMemoryItemDoc(original="hello", sourceId="s", channel=MEMChannels.DISCORD,
                           metadata="{not json")
    item.insert()
    try:
        plan = plan_action(_idea(item.id), "tokeniko-uid")
        assert "destination" not in plan["payload"]  # degrade to stakeholder-route, never crash
    finally:
        TKMemoryItemDoc.get_motor_collection().delete_many({"_id": item.id})

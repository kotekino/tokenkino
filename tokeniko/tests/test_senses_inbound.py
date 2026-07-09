"""Senses inbound (go-live P1, DMs first) — the perception seam, socket-free.

The handler's routing (self/non-DM/empty dropped, zip-lane stubbed, language ingested via /input),
the structural modality sniffer (a TKZip validates; everything else is language), and the fuzzy
`directedness` carrier on memory items. The HTTP call is monkeypatched — no API, no Discord.
"""
import asyncio
import json

import senses.inbound as inbound
from senses.inbound import dm_input_params, handle_discord_message, sniff_modality
from lib.core.memory import MEMItem
from lib.core.tkzip import TKZip, TKZipItem, TKZipContent
from lib.discord.models import DiscordMessage


def _dm(content="are you a software?", **over):
    fields = dict(message_id="111", author_id="222", author_name="renzo",
                  channel_id="333", guild_id=None, content=content,
                  is_dm=True, is_self=False)
    fields.update(over)
    return DiscordMessage(**fields)


def _zip_wire():
    # a minimal ROUND-TRIPPABLE zip (one leaf; a content-less TKZipItem doesn't re-validate)
    z = TKZip(map=[0.0] * 8,
              items=TKZipItem(content=TKZipContent(subject=None, predicate=None, direct=None)))
    return z.model_dump_json()


# ---- modality sniffer ----------------------------------------------------------------------------

def test_sniffer_english_is_language():
    assert sniff_modality("are you a software?") == "language"


def test_sniffer_json_but_not_zip_is_language():
    assert sniff_modality('{"hello": "world"}') == "language"
    assert sniff_modality('{"map": [], "items": "garbage"}') == "language"


def test_sniffer_malformed_json_is_language():
    assert sniff_modality("{not json at all") == "language"
    assert sniff_modality("") == "language"


def test_sniffer_valid_zip_is_tkzip():
    assert sniff_modality(_zip_wire()) == "tkzip"


# ---- handler routing -----------------------------------------------------------------------------

def test_handler_drops_self_nondm_empty():
    assert asyncio.run(handle_discord_message(_dm(is_self=True))) == "self"
    assert asyncio.run(handle_discord_message(_dm(is_dm=False, guild_id="9"))) == "not_dm"
    assert asyncio.run(handle_discord_message(_dm(content="  "))) == "empty"


def test_handler_stubs_the_zip_lane(monkeypatch):
    called = []
    monkeypatch.setattr(inbound, "_call_input", lambda p: called.append(p) or {"status": "complete"})
    assert asyncio.run(handle_discord_message(_dm(content=_zip_wire()))) == "tkzip_stub"
    assert called == []  # the zip lane must NOT reach /input (trust-gated activation, step 3)


def test_handler_ingests_language_dm(monkeypatch):
    called = []
    monkeypatch.setattr(inbound, "_call_input", lambda p: called.append(p) or {"status": "complete"})
    assert asyncio.run(handle_discord_message(_dm())) == "ingested"
    assert len(called) == 1


def test_handler_reports_api_failure(monkeypatch):
    monkeypatch.setattr(inbound, "_call_input", lambda p: None)
    assert asyncio.run(handle_discord_message(_dm())) == "failed"


# ---- the /input params seam ----------------------------------------------------------------------

def test_dm_params_carry_identity_channel_coords_directedness():
    p = dm_input_params(_dm())
    assert p["talker"] == "renzo@discord:222"        # channel-scoped uid (contextKey after the @)
    assert p["talker_name"] == "renzo"
    assert p["channel"] == "discord"
    assert p["directedness"] == 1.0                   # a DM is unambiguously directed
    coords = json.loads(p["metadata"])
    assert coords == {"channel_id": "333", "message_id": "111"}  # the P2 reply thread-back


# ---- the directedness carrier ---------------------------------------------------------------------

def test_memory_item_directedness_defaults_to_full():
    item = MEMItem(original="x", sourceId="s")
    assert item.directedness == 1.0

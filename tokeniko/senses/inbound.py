# --------------------------------------------------------------
# senses/inbound.py — the INBOUND perception path (senses go-live P1, DMs first). The perceiving half
# of the membrane: a normalized DiscordMessage arrives from the adapter, and senses turns it into a
# `memory` item by calling the API's /input (the ONE compile seam — senses stays parser-free exactly
# like the brain; the API owns spaCy/Stanza).
#
# P1 SCOPE (author's call, 2026-07-09): PRIVATE MESSAGES ONLY — a DM is unambiguously directed
# (directedness=1.0), so the reasoning core meets the world with zero addressing ambiguity. Guild
# channels (directedness grading, ambient listening) are step 2: the handler drops non-DMs for now.
#
# MODALITY SNIFFER (the per-channel language scaffold): a channel speaks English OR TKZip (the native
# peer language — senses/README.md "Per-channel language"). Detection is STRUCTURAL, not statistical:
# a TKZip is JSON with a rigid, validatable schema, its own watermark. The zip lane is RECOGNIZED BUT
# STUBBED — validate + log, do NOT ingest/reason: an inbound pre-compiled thought bypasses every
# interpretive defense, so the lane activates only trust-gated (with the trust ledger, step 3).
# --------------------------------------------------------------
import asyncio
import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Optional

from pydantic import ValidationError

from lib.core.tkzip import TKZip
from lib.discord.models import DiscordMessage

logger = logging.getLogger("tokeniko-brain")

_API_BASE = os.getenv("BRAIN_API_BASE", "http://localhost:8000")   # same seam as brain/api_client
_TIMEOUT = float(os.getenv("SENSES_INBOUND_TIMEOUT", "120"))       # /input compiles (~seconds); patient


# ---- modality sniffer -----------------------------------------------------------------------------

# "tkzip" iff the content is a JSON document that VALIDATES as a TKZip; anything else is "language"
# (the preparser downstream handles human-language detection/translation). Structural — no ambiguity.
def sniff_modality(content: str) -> str:
    s = (content or "").strip()
    if not (s.startswith("{") and s.endswith("}")):
        return "language"
    try:
        data = json.loads(s)
    except (ValueError, TypeError):
        return "language"
    if not isinstance(data, dict) or "map" not in data or "items" not in data:
        return "language"
    try:
        TKZip.model_validate(data)
        return "tkzip"
    except ValidationError:
        return "language"


# ---- the /input call (sync urllib, run via asyncio.to_thread) -------------------------------------

def _call_input(params: dict) -> Optional[dict]:
    url = f"{_API_BASE.rstrip('/')}/api/v1/input?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as error:
        logger.warning("[inbound] /input failed (%s) — message dropped this pass", error)
        return None


# ---- the message handler ---------------------------------------------------------------------------

# build the /input params for a DM — split out so the seam is unit-testable without a socket.
def dm_input_params(msg: DiscordMessage) -> dict:
    return {
        "tokens": msg.content,
        "talker": f"{msg.author_name}@discord:{msg.author_id}",   # channel-scoped uid (contextKey after @)
        "talker_name": msg.author_name,
        "channel": "discord",
        # the reply coordinates: plan_action forwards them into the action payload so the answer
        # threads back to the asker's actual message (P2).
        "metadata": json.dumps({"channel_id": msg.channel_id, "message_id": msg.message_id}),
        "directedness": 1.0,                                       # a DM is unambiguously directed
    }


# the on_message handler senses registers with the DiscordClient. Returns what it did (for tests/logs):
# "self" | "not_dm" | "empty" | "tkzip_stub" | "ingested" | "failed".
async def handle_discord_message(msg: DiscordMessage) -> str:
    if msg.is_self:
        return "self"                       # never perceive your own speech as input
    if not msg.is_dm:
        return "not_dm"                     # P1: DMs only (channel listening = step 2)
    if not (msg.content or "").strip():
        return "empty"                      # attachment-only / empty — nothing to compile
    if sniff_modality(msg.content) == "tkzip":
        # the native-zip lane: recognized, validated, NOT ingested (trust-gated activation, step 3).
        logger.info("[inbound] TKZip-lane message from %s — lane stubbed, not ingested", msg.author_name)
        return "tkzip_stub"

    params = dm_input_params(msg)
    result = await asyncio.to_thread(_call_input, params)
    if result is None or result.get("status") != "complete":
        logger.warning("[inbound] DM from %s not ingested (status=%s)",
                       msg.author_name, result.get("status") if result else "unreachable")
        return "failed"
    logger.info("[inbound] DM from %s -> memory: %r", msg.author_name, msg.content[:80])
    return "ingested"

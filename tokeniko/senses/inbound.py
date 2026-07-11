# --------------------------------------------------------------
# senses/inbound.py — the INBOUND perception path (go-live P1 + C channel listening). The perceiving half
# of the membrane: a normalized DiscordMessage arrives from the adapter, and senses turns it into a
# `memory` item by calling the API's /input (the ONE compile seam — senses stays parser-free exactly
# like the brain; the API owns spaCy/Stanza).
#
# C SCOPE (author's call, 2026-07-11): CHANNEL LISTENING — every message is perceived, and the
# DIRECTEDNESS GRADING turns addressing into one scalar (DM 1.0 · @-mention/name/reply-to-him 0.9 ·
# ambient 0.6 "the polite guest" · someone else's thread 0.15). Perception and reasoning always run
# at full strength; the scalar gates ONLY the urge to act (Priorities: urge x directedness vs the
# threshold) — discretion-to-silence emerges from the multiplication, no special cases. The ambient
# grade is the personality dial: at 0.6 he answers a question asked to the room (0.9x0.6 clears 0.5)
# but stays quiet otherwise. (Conversation momentum — he just spoke, so the room is "his"
# conversation for a while — is parked: derive it from the memory timeseries, see doc/parked.md.)
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


# ---- the directedness grading (C) ------------------------------------------------------------------

# the addressing ladder — how much this message is FOR tokeniko, as one fuzzy scalar. The signals
# (mentions_me / reply_to_me) are computed by the adapter, the only layer that sees discord.py.
_DIR_DM = 1.0            # a DM is unambiguously directed
_DIR_ADDRESSED = 0.9     # @-mention, his name in the text, or a reply to one of HIS messages
_DIR_AMBIENT = 0.6       # a plain channel message — "the polite guest" (author's call, 2026-07-11)
_DIR_OTHERS_THREAD = 0.15  # a reply into someone ELSE's thread — barely his business


def grade_directedness(msg: DiscordMessage) -> float:
    if msg.is_dm:
        return _DIR_DM
    if msg.mentions_me or msg.reply_to_me:
        return _DIR_ADDRESSED
    if msg.reply_to is not None:
        return _DIR_OTHERS_THREAD
    return _DIR_AMBIENT


# ---- the message handler ---------------------------------------------------------------------------

# build the /input params for a message (DM or channel) — split out so the seam is unit-testable
# without a socket.
def input_params(msg: DiscordMessage) -> dict:
    return {
        "tokens": msg.content,
        "talker": f"{msg.author_name}@discord:{msg.author_id}",   # channel-scoped uid (contextKey after @)
        "talker_name": msg.author_name,
        "channel": "discord",
        # the reply coordinates: plan_action forwards them into the action payload so the answer
        # threads back to the asker's actual message (P2). reply_to = what THIS message replies to —
        # the structural hook of the open-why derivation (B2: is this a reply to MY question?).
        "metadata": json.dumps({"channel_id": msg.channel_id, "message_id": msg.message_id,
                                "reply_to": msg.reply_to}),
        "directedness": grade_directedness(msg),
        # the preparser is OFF (author's call, 2026-07-11): the Ollama path is under review, the
        # playground server posts polished messages, and raw input is a standing parser/compiler
        # robustness test — what breaks feeds doc/ref/test-feedback.md. (B3 reversed; see parked.md.)
    }


# the on_message handler senses registers with the DiscordClient. Returns what it did (for tests/logs):
# "self" | "empty" | "tkzip_stub" | "ingested" | "failed".
async def handle_discord_message(msg: DiscordMessage) -> str:
    if msg.is_self:
        return "self"                       # never perceive your own speech as input
    if not (msg.content or "").strip():
        return "empty"                      # attachment-only / empty — nothing to compile
    if sniff_modality(msg.content) == "tkzip":
        # the native-zip lane: recognized, validated, NOT ingested (trust-gated activation, step 3).
        logger.info("[inbound] TKZip-lane message from %s — lane stubbed, not ingested", msg.author_name)
        return "tkzip_stub"

    params = input_params(msg)
    result = await asyncio.to_thread(_call_input, params)
    if result is None or result.get("status") != "complete":
        logger.warning("[inbound] message from %s not ingested (status=%s)",
                       msg.author_name, result.get("status") if result else "unreachable")
        return "failed"
    logger.info("[inbound] %s from %s (directedness=%.2f) -> memory: %r",
                "DM" if msg.is_dm else "channel msg", msg.author_name,
                params["directedness"], msg.content[:80])
    return "ingested"

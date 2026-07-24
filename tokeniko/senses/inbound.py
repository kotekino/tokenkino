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
# but stays quiet otherwise. CONVERSATION MOMENTUM (B, 2026-07-24): an ambient message inside an OPEN
# exchange — he just addressed / was addressed in this channel — lifts to 0.85, so the room stays "his"
# conversation for a while (derived from the memory timeseries, never stored state — the open-why).
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
from datetime import datetime, timedelta, timezone
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
_DIR_MOMENTUM = 0.85     # an ambient message inside an OPEN exchange — the room is still "his" (B)
_DIR_AMBIENT = 0.6       # a plain channel message — "the polite guest" (author's call, 2026-07-11)
_DIR_OTHERS_THREAD = 0.15  # a reply into someone ELSE's thread — barely his business


def grade_directedness(msg: DiscordMessage) -> float:
    if msg.is_dm:
        return _DIR_DM
    if msg.mentions_me or msg.reply_to_me:
        return _DIR_ADDRESSED
    if msg.reply_to is not None:
        return _DIR_OTHERS_THREAD    # an explicit signal (someone else's thread) beats momentum
    if _in_open_exchange(msg):
        return _DIR_MOMENTUM         # ambient, but the conversation is open — lift toward addressed
    return _DIR_AMBIENT


# ---- conversation momentum (B, 2026-07-24) — the parked "the room is his" item, promoted ----------

# the window in which the room stays "his" conversation after the last directed turn. Read LAZILY at
# call time (senses/main imports this module BEFORE load_dotenv — the outbound.py flag lesson), so a
# .env override actually takes effect.
def _momentum_window_s() -> float:
    return float(os.getenv("MOMENTUM_WINDOW_S", "600"))


# the channel_id an inbound/outbound memory item was stamped with (metadata is a JSON string, not a
# nested doc — the timeseries meta_field — so channel matching happens in Python).
def _item_channel_id(item) -> Optional[str]:
    try:
        return json.loads(item.metadata).get("channel_id") if item.metadata else None
    except (ValueError, TypeError, AttributeError):
        return None


# is this ambient message part of an OPEN exchange? — DERIVED from the memory timeseries, never stored
# state (the open-why principle: senses has Mongo; the brain's RAM ring is unreachable and must stay
# so). Within the window, in the SAME channel, EITHER (a) this author just addressed tokeniko
# (directedness >= 0.9) OR (b) tokeniko just spoke TO this author (an outbound targeted at him). A
# derivation failure must NEVER break perception — best-effort, momentum absent -> plain ambient.
def _in_open_exchange(msg: DiscordMessage) -> bool:
    try:
        from lib.core.io import get_tokeniko
        from lib.core.memory import MEMChannels
        from lib.core.models import TKMemoryItemDoc, TKMemoryStakeholdersDoc

        author_uid = f"{msg.author_name}@discord:{msg.author_id}"
        author = TKMemoryStakeholdersDoc.find_one({"uid": author_uid}).run()  # Bunnet: .run() executes
        if author is None:
            return False                     # never spoke here before -> nothing open
        author_id, me_id = str(author.id), str(get_tokeniko().id)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=_momentum_window_s())
        rows = TKMemoryItemDoc.find(
            {"channel": MEMChannels.DISCORD.value,
             "timestamp": {"$gte": cutoff},
             "$or": [
                 {"sourceId": author_id, "directedness": {"$gte": _DIR_ADDRESSED}},  # (a) he addressed tokeniko
                 {"sourceId": me_id, "targetId": author_id},                          # (b) tokeniko spoke to him
             ]},
        ).to_list()
        return any(_item_channel_id(row) == msg.channel_id for row in rows)
    except Exception as error:
        logger.debug("[inbound] open-exchange derivation skipped (%s) — ambient stands", error)
        return False


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

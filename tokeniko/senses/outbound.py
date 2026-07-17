# --------------------------------------------------------------
# senses/outbound.py — the OUTBOUND actions executor (#4 D3b). The carrier half of the brain→senses
# reply seam: the brain DECIDES (mints an Action with channel=discord, a target, and the composed
# text in the payload); senses CARRIES it to the socket — through the rag2-out voice gate (compose
# 2.0 slice 3): a long-enough composed reply gets ONE Haiku fluency pass, shipped ONLY if the
# API's zip-verifier proves the polish still compiles to the raw's meaning (consensus-with-the-
# compiler on the way out, mirroring rag1-in). ANY failure anywhere ships the raw verbatim.
#
# OWNERSHIP (no cross-process race, no new status): the brain's `actions_phase` consumes only
# channel=INTERNAL; this executor consumes only channel=discord. Disjoint filters over the SAME queue.
#
# DRY-RUN by default (`SENSES_DELIVER_DRYRUN`!=0): resolve + decompile + LOG the would-send, mark DONE,
# touch no socket — so the whole seam is verifiable without Discord credentials / risking live spam.
# Flip to live (and pass a real `sender`) once the inbound listener + a connected DiscordClient land.
# pipeline-light: never imports the parser (the verify consensus runs at the API — the one-compile
# seam); the ONLY cloud call is the rag2-out polish, gated + graceful (RAG2_OUT_DISABLED kills it).
# --------------------------------------------------------------
import asyncio
import json
import logging
import os
import urllib.request
from typing import Awaitable, Callable, Optional

from lib.core.models import TKActionDoc, TKMemoryItemDoc, TKMemoryStakeholdersDoc
from lib.core.memory import ActionStatus, MEMChannels, TokenikoAction
from lib.discord.models import Destination
from lib.rag import RAG2_OUT, rag_call, rag_enabled

logger = logging.getLogger("tokeniko-brain")

_API_BASE = os.getenv("BRAIN_API_BASE", "http://localhost:8000")  # same seam as inbound
_VERIFY_TIMEOUT = float(os.getenv("SENSES_VOICE_VERIFY_TIMEOUT", "120"))  # two compiles; patient
# below this length a reply is template-curated and fragment-shaped ("yes", "why is that?") —
# unpolishable by the verifier's own gate, so the Haiku call is never spent on it.
_POLISH_MIN_CHARS = int(os.getenv("SENSES_VOICE_POLISH_MIN_CHARS", "25"))


# ---- the rag2-out voice gate (compose 2.0 slice 3) ---------------------------------------------------
# ask the API whether the polish still compiles to the raw's meaning. Graceful None on any trouble
# (API down / malformed reply) — the caller ships the raw.
def _verify_voice(raw: str, polished: str) -> Optional[dict]:
    body = json.dumps({"raw": raw, "polished": polished}).encode("utf-8")
    req = urllib.request.Request(
        f"{_API_BASE.rstrip('/')}/api/v1/voice/verify", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_VERIFY_TIMEOUT) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return out.get("data") if out.get("status") == "complete" else None
    except Exception as error:
        logger.warning("[outbound] voice verify unreachable (%s) — raw ships", error)
        return None


# polish + verify one composed reply; returns the text to ship (the polish ONLY when the compiler
# consensus holds — every other path is the raw, verbatim). Never raises.
async def _voice_out(raw: str) -> str:
    if not rag_enabled("RAG2_OUT_DISABLED") or len(raw) < _POLISH_MIN_CHARS:
        return raw
    polished = await rag_call(RAG2_OUT, raw)
    polished = (polished or "").strip()
    if not polished or polished == raw:
        return raw
    verdict = await asyncio.to_thread(_verify_voice, raw, polished)
    if verdict and verdict.get("ok"):
        logger.info("[outbound] rag2-out verified: %r -> %r", raw, polished)
        return polished
    logger.info("[outbound] rag2-out REJECTED (%s) — raw ships: %r",
                (verdict or {}).get("note", "unverifiable"), raw)
    return raw

# tokeniko's own stakeholder id (the sourceId of his recorded speech), resolved lazily once.
_self_id: Optional[str] = None


def _tokeniko_id() -> Optional[str]:
    global _self_id
    if _self_id is None:
        me = TKMemoryStakeholdersDoc.find_one({"isMe": True}).run()  # Bunnet: .run() executes
        _self_id = str(me.id) if me is not None else None
    return _self_id


# SELF-SPEECH → MEMORY (senses B1, 2026-07-09): a DELIVERED outbound message is a biographical event —
# record it as a zip-less memory item (sourceId=tokeniko, targetId=the recipient). zip=None keeps it
# INVISIBLE to the reaction loop (think/wonder filter zip!=None) while making conversational context
# DERIVABLE from the timeseries (the open-why: "did I recently ask this speaker something?"). metadata
# carries the SENT message id (the structural hook an inbound reply threads back to) + what it replied
# to. Live sends only — a dry-run says nothing, so it records nothing.
def _record_self_speech(action, dest: Destination, text: str, sent_message_id: str) -> None:
    try:
        me = _tokeniko_id()
        if me is None:
            return
        TKMemoryItemDoc(
            original=text,
            zip=None,
            sourceId=me,
            targetId=action.targetId,
            channel=MEMChannels.DISCORD,
            metadata=json.dumps({
                "channel_id": dest.channel_id or "",
                "message_id": sent_message_id,
                "reply_to": dest.reply_to,
            }),
        ).insert()
    except Exception as error:
        logger.warning("[outbound] self-speech record failed (%s) — delivery unaffected", error)

POLL_INTERVAL = float(os.getenv("SENSES_OUTBOUND_POLL", "2"))   # seconds between idle polls


# the delivery flags are read LAZILY (call time, not import time): senses/main.py imports this module
# BEFORE load_dotenv() runs, so a module-level read sees a bare environment and silently stays in
# dry-run whatever .env says (bit us at go-live, 2026-07-09). Lazy also means the flag is honored
# without touching code.
def _dryrun() -> bool:
    return os.getenv("SENSES_DELIVER_DRYRUN", "1") != "0"        # default: dry-run (no live send)


# the senders the executor can be handed (None in dry-run). channel adapter -> (Destination, text) -> id.
Sender = Callable[[Destination, str], Awaitable[str]]


# resolve the action's recipient to a Discord Destination, or None if unaddressable.
#   1. explicit per-message coords in payload["destination"] — the FORWARD path: the (deferred) inbound
#      listener stamps the origin channel_id / reply_to message_id here for an in-channel threaded reply.
#   2. fallback: DM the participant via the discord id carried in the stakeholder's contextKey
#      ("channel:talker_uid") — enough to prove the seam before inbound exists.
def _resolve_destination(target_uid: Optional[str], payload: dict) -> Optional[Destination]:
    dest = payload.get("destination")
    if isinstance(dest, dict):
        try:
            return Destination(**dest)
        except Exception:
            return None
    if not target_uid:
        return None
    sh = TKMemoryStakeholdersDoc.find_one({"uid": target_uid}).run()  # Bunnet: .run() executes
    if sh is None or not sh.contextKey or ":" not in sh.contextKey:
        return None
    platform_id = sh.contextKey.split(":", 1)[1]
    if not platform_id:
        return None
    try:
        return Destination(user_id=platform_id)
    except Exception:
        return None


# deliver ONE pending discord action (oldest-first). grab (PENDING->PROCESSING) before any await so a
# crash mid-delivery doesn't leave it re-grabbable as PENDING. Returns True iff it handled one.
async def deliver_one(sender: Optional[Sender] = None) -> bool:
    pending = (
        TKActionDoc.find(
            {"status": ActionStatus.PENDING.value, "channel": MEMChannels.DISCORD.value}
        )
        .sort("createdAt")
        .limit(1)
        .to_list()
    )
    if not pending:
        return False
    action = pending[0]
    action.status = ActionStatus.PROCESSING
    action.save()

    payload = action.payload or {}
    raw = (payload.get("raw") or "").strip()
    # the rag2-out voice gate (compose 2.0 slice 3): one verified fluency pass, or the raw
    # verbatim — the voice can gain fluency, never lose meaning. The ANECDOTE skips the polish
    # (premiere find, 2026-07-17): its side-note register («by the way, …») is discourse framing
    # the zip cannot see — Haiku stripped it and the verifier CORRECTLY passed the result
    # («Gold is beautiful.»): meaning preserved, charm lost. For a side-note the register IS the
    # point, and the scaffold text is already curated English — ship it verbatim.
    polishable = raw and payload.get("action_token") != TokenikoAction.MENTION.value
    english = await _voice_out(raw) if polishable else raw
    dest = _resolve_destination(action.targetId, payload)

    if dest is None or not english:
        logger.warning(
            "[outbound] action %s undeliverable (dest=%s, english=%r) -> FAILED",
            str(action.id), dest, english,
        )
        action.status = ActionStatus.FAILED
        action.save()
        return True

    if _dryrun() or sender is None:
        logger.info("[outbound] DRY-RUN would send to %s: %r  (raw=%r)",
                    dest, english, payload.get("raw", ""))
        action.status = ActionStatus.DONE
        action.save()
        return True

    try:
        msg_id = await sender(dest, english)
        logger.info("[outbound] sent to %s (msg=%s): %r", dest, msg_id, english)
        _record_self_speech(action, dest, english, msg_id)  # B1: spoken words are biography
        action.status = ActionStatus.DONE
    except Exception as error:
        logger.warning("[outbound] send failed for action %s (%s) -> FAILED", str(action.id), error)
        action.status = ActionStatus.FAILED
    action.save()
    return True


# the executor loop (a cancellable while-loop, mirroring the other senses tasks). Drains back-to-back
# while there is work, then idles at POLL_INTERVAL.
async def outbound_executor_task(sender: Optional[Sender] = None) -> None:
    logger.info("📤 Outbound executor started (dry-run=%s)", _dryrun())
    try:
        while True:
            try:
                did = await deliver_one(sender)
            except Exception as error:
                logger.error("[outbound] executor error: %s", error)
                did = False
            await asyncio.sleep(0 if did else POLL_INTERVAL)
    except asyncio.CancelledError:
        logger.info("📤 Outbound executor interrupted...")

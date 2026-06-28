# --------------------------------------------------------------
# senses/outbound.py — the OUTBOUND actions executor (#4 D3b). The carrier half of the brain→senses
# reply seam: the brain DECIDES (mints an Action with channel=discord, a target, and a raw decision
# text in the payload); senses CARRIES + DECOMPILES (turns the raw text into fluent English via
# `decompiler_decompile` — the channel-appropriate NLG — and delivers it to the socket).
#
# OWNERSHIP (no cross-process race, no new status): the brain's `actions_phase` consumes only
# channel=INTERNAL; this executor consumes only channel=discord. Disjoint filters over the SAME queue.
#
# DRY-RUN by default (`SENSES_DELIVER_DRYRUN`!=0): resolve + decompile + LOG the would-send, mark DONE,
# touch no socket — so the whole seam is verifiable without Discord credentials / risking live spam.
# Flip to live (and pass a real `sender`) once the inbound listener + a connected DiscordClient land.
# pipeline-light: imports the decompiler (Ollama only, no spaCy) + the Destination model — never the parser.
# --------------------------------------------------------------
import asyncio
import logging
import os
from typing import Awaitable, Callable, Optional

from lib.core.models import TKActionDoc, TKMemoryStakeholdersDoc
from lib.core.memory import ActionStatus, MEMChannels
from lib.llc.decompiler import decompiler_decompile
from lib.discord.models import Destination

logger = logging.getLogger("tokeniko-brain")

POLL_INTERVAL = float(os.getenv("SENSES_OUTBOUND_POLL", "2"))   # seconds between idle polls
DRYRUN = os.getenv("SENSES_DELIVER_DRYRUN", "1") != "0"          # default: dry-run (no live send)

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


# raw decision text -> fluent English (the decompile step that lives in senses, per-channel NLG). Ollama;
# falls back to the raw text on failure so the polish step never blocks delivery. NOTE: decompiler_decompile
# returns a {model: translation} dict (it runs two models) — take the first non-empty translation.
async def _to_english(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        result = await decompiler_decompile(raw)
        if isinstance(result, dict):
            english = next((v.strip() for v in result.values() if isinstance(v, str) and v.strip()), "")
        else:
            english = (result or "").strip()
        return english or raw
    except Exception as error:
        logger.warning("[outbound] decompile failed (%s) — sending raw", error)
        return raw


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
    english = await _to_english(payload.get("raw", ""))
    dest = _resolve_destination(action.targetId, payload)

    if dest is None or not english:
        logger.warning(
            "[outbound] action %s undeliverable (dest=%s, english=%r) -> FAILED",
            str(action.id), dest, english,
        )
        action.status = ActionStatus.FAILED
        action.save()
        return True

    if DRYRUN or sender is None:
        logger.info("[outbound] DRY-RUN would send to %s: %r  (raw=%r)",
                    dest, english, payload.get("raw", ""))
        action.status = ActionStatus.DONE
        action.save()
        return True

    try:
        msg_id = await sender(dest, english)
        logger.info("[outbound] sent to %s (msg=%s): %r", dest, msg_id, english)
        action.status = ActionStatus.DONE
    except Exception as error:
        logger.warning("[outbound] send failed for action %s (%s) -> FAILED", str(action.id), error)
        action.status = ActionStatus.FAILED
    action.save()
    return True


# the executor loop (a cancellable while-loop, mirroring the other senses tasks). Drains back-to-back
# while there is work, then idles at POLL_INTERVAL.
async def outbound_executor_task(sender: Optional[Sender] = None) -> None:
    logger.info("📤 Outbound executor started (dry-run=%s)", DRYRUN)
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

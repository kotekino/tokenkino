# --------------------------------------------------------------
# senses/blog_outbound.py — the PUBLIC-channel actions executor (blog P3): the carrier half of
# the brain→website seam. The brain DECIDES (mints POST_CONTENT actions on MEMChannels.PUBLIC:
# payload["material"] = a life event to publish, or payload["snapshot"] = a ready-built mind
# snapshot — brain/heartbeat.py); this executor COMPOSES + SHIPS — material goes through
# senses/blog.compose_post (draft → polish → transmission contract) and lands on
# POST {BLOG_API_BASE}/transmissions (idempotent upsert by slug); a snapshot ships VERBATIM to
# POST {BLOG_API_BASE}/mind. Contract: tokeniko-public/doc/ingestion-api.md.
#
# OWNERSHIP (no cross-process race, no new status): disjoint channel filters over the SAME
# TKActionDoc queue — the brain's actions_phase consumes INTERNAL, senses/outbound.py consumes
# discord, this executor consumes PUBLIC only.
#
# DRY-RUN by default (`SENSES_DELIVER_DRYRUN`!=0, mirroring outbound.py) — and a MISSING
# INGEST_API_KEY forces it too (no key = nothing could authenticate; log the would-send, mark
# DONE, touch no socket). NO AUTO-RETRY on a failed push: the action stays FAILED — a failed
# post can be re-minted by a future life event; the failure is logged loudly instead.
#
# pipeline-light BY CONSTRUCTION: no spaCy/Ollama/discord; aiohttp (discord.py's transitive dep,
# already in the venv — no new dependency) is imported lazily inside the live push only, so the
# module imports clean and tests inject their own post function.
# --------------------------------------------------------------
import asyncio
import json
import logging
import os
from typing import Awaitable, Callable, Optional

from lib.core.models import TKActionDoc
from lib.core.memory import ActionStatus, MEMChannels
from senses.blog import compose_post

logger = logging.getLogger("tokeniko-brain")

# the injectable push signature: (full URL, JSON body) -> HTTP status code. Tests hand in a
# capture stub; live runs default to the aiohttp-backed _http_post below.
PostFn = Callable[[str, dict], Awaitable[int]]

# the transmission body per the ingestion contract — compose_post's extra `polished` flag is
# internal telemetry (raw-vs-polished render) and is stripped before shipping.
_TRANSMISSION_KEYS = ("slug", "date", "kind", "title", "excerpt", "body", "readMin")


# env is read LAZILY (call time, not import time) — the go-live lesson from outbound.py:
# senses/main.py imports this module BEFORE load_dotenv() runs, so a module-level read would see
# a bare environment and silently misconfigure whatever .env says.
def _api_base() -> str:
    # the API lives on its OWN host (api.tokeniko.online → the backend App Service); the apex
    # serves the SPA, whose catch-all would swallow a POST with a false 200 (the 2026-07-12
    # incident). Never default to the frontend host.
    return os.getenv("BLOG_API_BASE", "https://api.tokeniko.online/api").rstrip("/")


def _poll_interval() -> float:
    return float(os.getenv("SENSES_BLOG_POLL", "10"))  # seconds between idle polls


def _dryrun() -> bool:
    if os.getenv("SENSES_DELIVER_DRYRUN", "1") != "0":  # default: dry-run (no live push)
        return True
    return not os.getenv("INGEST_API_KEY")  # no key -> nothing could authenticate: dry-run too


# PROOF OF DELIVERY, not just a status code (the false-200 lesson, 2026-07-12): a static
# frontend's catch-all answers ANY request — including a POST — with 200 + an HTML shell, so a
# misrouted BLOG_API_BASE would read as "delivered" while writing nothing. The ingestion API's
# contract is a JSON envelope {"success": true, ...}; a 2xx whose body is not that envelope is a
# delivery FAILURE. Pure so it's unit-testable without a socket.
def _delivered(status: int, body_text: str) -> bool:
    if not (200 <= status < 300):
        return False
    try:
        parsed = json.loads(body_text)
    except Exception:
        return False
    return isinstance(parsed, dict) and parsed.get("success") is True


# the live push: one aiohttp session per call — at this cadence (posts are rare, heartbeats every
# ~5 min) a persistent session isn't worth its lifecycle management. Returns the HTTP status —
# but a 2xx WITHOUT the API's JSON envelope raises (misrouted endpoint = not delivered); the
# caller maps any raise to FAILED.
async def _http_post(url: str, body: dict) -> int:
    import aiohttp  # lazy: never touched in dry-run or under an injected post_fn (tests)
    headers = {"Authorization": f"Bearer {os.getenv('INGEST_API_KEY', '')}"}
    timeout = aiohttp.ClientTimeout(total=float(os.getenv("BLOG_API_TIMEOUT", "30")))
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=body, headers=headers) as resp:
            text = await resp.text()
            if 200 <= resp.status < 300 and not _delivered(resp.status, text):
                raise RuntimeError(
                    f"2xx without the API envelope (HTTP {resp.status}, body starts "
                    f"{text[:60]!r}) — BLOG_API_BASE likely points at the frontend, not the API")
            return resp.status


# ship a material action: compose (draft -> polish -> contract) then POST /transmissions.
# Returns True iff the action should be DONE.
async def _deliver_material(action: TKActionDoc, material, post_fn: Optional[PostFn]) -> bool:
    post = await compose_post(material)
    if post is None:  # malformed material — compose_post already logged the why
        logger.warning("[blog-outbound] action %s: material did not compose -> FAILED",
                       str(action.id))
        return False
    body = {k: post[k] for k in _TRANSMISSION_KEYS}
    url = _api_base() + "/transmissions"
    if _dryrun():
        logger.info("[blog-outbound] DRY-RUN would POST %s: slug=%s title=%r polished=%s",
                    url, post["slug"], post["title"], post["polished"])
        return True
    try:
        status = await (post_fn or _http_post)(url, body)
    except Exception as error:
        logger.warning("[blog-outbound] transmission slug=%s push failed (%s) -> FAILED "
                       "(no auto-retry — a future life event may re-mint the post)",
                       post["slug"], error)
        return False
    if 200 <= status < 300:  # 201 = new, 200 = idempotent update by slug
        logger.info("[blog-outbound] published transmission slug=%s (polished=%s, HTTP %s)",
                    post["slug"], post["polished"], status)
        return True
    logger.warning("[blog-outbound] transmission slug=%s rejected (HTTP %s) -> FAILED "
                   "(no auto-retry — a future life event may re-mint the post)",
                   post["slug"], status)
    return False


# ship a snapshot action: the brain built the exact POST /api/mind body — pushed VERBATIM.
async def _deliver_snapshot(action: TKActionDoc, snapshot, post_fn: Optional[PostFn]) -> bool:
    url = _api_base() + "/mind"
    if _dryrun():
        logger.info("[blog-outbound] DRY-RUN would POST %s: state=%s metrics=%s", url,
                    snapshot.get("state") if isinstance(snapshot, dict) else None,
                    snapshot.get("metrics") if isinstance(snapshot, dict) else None)
        return True
    try:
        status = await (post_fn or _http_post)(url, snapshot)
    except Exception as error:
        logger.warning("[blog-outbound] mind snapshot push failed (%s) -> FAILED "
                       "(the next heartbeat carries fresh counts anyway)", error)
        return False
    if 200 <= status < 300:
        logger.info("[blog-outbound] mind snapshot pushed (HTTP %s)", status)
        return True
    logger.warning("[blog-outbound] mind snapshot rejected (HTTP %s) -> FAILED", status)
    return False


# deliver ONE pending PUBLIC action (oldest-first). grab (PENDING->PROCESSING) before any await
# so a crash mid-delivery doesn't leave it re-grabbable as PENDING (the outbound.py idiom).
# Returns True iff it handled one (whatever the outcome).
async def deliver_one_public(post_fn: Optional[PostFn] = None) -> bool:
    pending = (
        TKActionDoc.find(
            {"status": ActionStatus.PENDING.value, "channel": MEMChannels.PUBLIC.value}
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
    if "material" in payload:
        ok = await _deliver_material(action, payload["material"], post_fn)
    elif "snapshot" in payload:
        ok = await _deliver_snapshot(action, payload["snapshot"], post_fn)
    else:
        logger.warning("[blog-outbound] action %s carries neither material nor snapshot -> FAILED",
                       str(action.id))
        ok = False

    action.status = ActionStatus.DONE if ok else ActionStatus.FAILED
    action.save()
    return True


# the executor loop (a cancellable while-loop, mirroring outbound_executor_task): drains
# back-to-back while there is work, then idles at SENSES_BLOG_POLL.
async def blog_outbound_task(post_fn: Optional[PostFn] = None) -> None:
    logger.info("📡 Blog outbound executor started (dry-run=%s)", _dryrun())
    try:
        while True:
            try:
                did = await deliver_one_public(post_fn)
            except Exception as error:
                logger.error("[blog-outbound] executor error: %s", error)
                did = False
            await asyncio.sleep(0 if did else _poll_interval())
    except asyncio.CancelledError:
        logger.info("📡 Blog outbound executor interrupted...")

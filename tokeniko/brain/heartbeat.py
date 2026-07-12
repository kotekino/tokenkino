# --------------------------------------------------------------
# brain/heartbeat.py — the public MIND MONITOR stats heartbeat (blog P3, brain side). Every so
# often the coordinator asks this module to enqueue ONE POST_CONTENT action on MEMChannels.PUBLIC
# whose payload["snapshot"] is the ready-to-ship POST /api/mind body (the ingestion contract,
# tokeniko-public/doc/ingestion-api.md): the brain reports RAW numeric facts; the website backend
# derives the display (KPI tiles, trends, the sparkline). Same split as everywhere else in the
# blog arc: the brain DECIDES + BUILDS, the senses PUBLIC executor (senses/blog_outbound.py)
# CARRIES it over HTTP — this module never touches the network.
#
# CADENCE (the rate-limit math): a beat fires when at least BRAIN_HEARTBEAT_MIN_S (default 300s)
# has passed since the last one — wall-clock only (see _should_beat for why tick-counting lied).
# 300s ⇒ at most 3 heartbeats per 15-minute window, plus the occasional transmission post —
# comfortably under the public API's 100 req / 15 min per-IP limit. Counting DB documents each
# beat is fine at a 5-minute cadence (a handful of indexed count queries).
#
# GRACEFUL BY CONTRACT: maybe_beat is wrapped whole — a heartbeat failure (Mongo hiccup, model
# drift) must NEVER break the coordinator loop; it logs and retries at the next tick multiple.
# brain stays parser-free: only lib.core models here, no spaCy/Stanza/compiler.
# --------------------------------------------------------------
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from lib.core.models import (
    TKActionDoc,
    TKAxiomDoc,
    TKBrainStateDoc,
    TKDefinitionDoc,
    TKDictionaryDoc,
    TKMemoryStakeholdersDoc,
    TKTheoremDoc,
    TKTrustEpisodeDoc,
)
from lib.core.memory import ActionType, MEMChannels

logger = logging.getLogger("tokeniko-brain")

# the honest one-line "what it's doing now" per reported state (the contract's `doing` field).
# Only the states the coordinator can cheaply and truthfully observe are used (see maybe_beat's
# caller in brain/main.py): "ingesting"/"refuting" would claim introspection the loop doesn't have.
_DOING: dict[str, str] = {
    "thinking": "evaluating fresh memory against what I know",
    "wondering": "re-examining an old memory — my knowledge has grown since",
    "idle": "waiting — nothing new to think about",
}


# the pure cadence guard (unit-testable without a clock or a DB): beat iff at least `min_seconds`
# have passed since the last beat — WALL-CLOCK ONLY. The original design also gated on a tick
# multiple, but tick duration is wildly variable (a busy yield is 0.05s, an idle tick 5s, a
# WONDERING tick 30s+ — Ollama renders, API materializes), so 100 ticks meant anything from
# seconds to nearly an hour: the first live brain never beat (2026-07-12). Time-since-last is
# equally O(1) and honest at every loop speed; the first beat fires on the first tick after boot
# (last_beat_at=0 — fresh stats on wake is a feature). `tick` stays a parameter for the boot
# guard only (tick <= 0 never beats).
def _should_beat(tick: int, last_beat_at: float, now: float,
                 min_seconds: Optional[float] = None) -> bool:
    if min_seconds is None:
        min_seconds = float(os.getenv("BRAIN_HEARTBEAT_MIN_S", "300"))
    if tick <= 0:
        return False
    return (now - last_beat_at) >= min_seconds


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()


# build the POST /api/mind body from honest Mongo counts. Metric keys are the backend's KPI tiles
# (definitions / axiomsRules / theorems / dictionary / souls / trustEpisodes) + the sparkline
# series (inferencesPerCycle). All values must be finite numbers per the contract.
def build_snapshot(state: str) -> dict:
    now = int(time.time())
    metrics = {
        "definitions": TKDefinitionDoc.find_all().count(),
        # active knowledge only — archived axioms/theorems don't reason, so they don't count.
        "axiomsRules": TKAxiomDoc.find({"archived": False}).count(),
        "theorems": TKTheoremDoc.find({"archived": False}).count(),
        "dictionary": TKDictionaryDoc.find_all().count(),
        # souls = the minds he knows, HIMSELF EXCLUDED ($ne True also catches legacy docs that
        # predate the isMe field). Participants and named individuals both count — each is a
        # known mind/entity in his world.
        "souls": TKMemoryStakeholdersDoc.find({"isMe": {"$ne": True}}).count(),
        "trustEpisodes": TKTrustEpisodeDoc.find_all().count(),
        # inferencesPerCycle: theorems derived in the last 24h (createdAt >= now-86400). Chosen
        # over the ideas-per-hour proxy because a theorem IS an inference — the count measures
        # actual reasoning output, not urges; and it's one indexed-range count, cheap at this
        # cadence. (A true per-cycle delta would need snapshot memory — not worth the state.)
        "inferencesPerCycle": TKTheoremDoc.find({"createdAt": {"$gte": now - 86400}}).count(),
    }
    # activity: the last 5 actions (ANY channel) as type+status only — NEVER raw payload content
    # (an action payload may quote a private conversation; the public log stays metadata-honest).
    recent = TKActionDoc.find_all().sort("-createdAt").limit(5).to_list()
    activity = [
        {"at": _iso(a.createdAt),
         "text": f"{getattr(a.action_type, 'value', a.action_type)} "
                 f"[{getattr(a.status, 'value', a.status)}]"}
        for a in recent
    ]
    # uptime = seconds since the wake boundary (brain_state.wake_at — set once on first run).
    bs = TKBrainStateDoc.find_one({"key": "singleton"}).run()  # Bunnet: .run() executes
    uptime = int(now - bs.wake_at) if bs is not None and bs.wake_at else 0
    return {
        "state": state,
        "doing": _DOING.get(state, _DOING["thinking"]),
        "uptimeSec": max(0, uptime),
        "metrics": metrics,
        "activity": activity,
    }


# wall-clock timestamp of the last SUCCESSFUL beat (module-level: the coordinator is one process,
# one loop). A failed beat leaves it untouched, so the retry comes at the next tick multiple.
_last_beat_at: float = 0.0


# the coordinator hook: called EVERY tick, cheap no-op unless the cadence guard fires. Returns
# True iff a snapshot action was enqueued. Never raises — the whole body is guarded so a
# heartbeat failure cannot break the coordinator loop.
def maybe_beat(tick: int, state: str, tokeniko_uid: str) -> bool:
    global _last_beat_at
    try:
        now = time.time()
        if not _should_beat(tick, _last_beat_at, now):
            return False
        TKActionDoc(
            action_type=ActionType.POST_CONTENT,
            channel=MEMChannels.PUBLIC,
            sourceId=tokeniko_uid or "tokeniko",
            payload={"snapshot": build_snapshot(state)},
        ).insert()
        _last_beat_at = now
        logger.info("[heartbeat] mind snapshot enqueued (tick=%d, state=%s)", tick, state)
        return True
    except Exception as error:
        logger.warning("[heartbeat] snapshot enqueue failed (%s) — coordinator unaffected", error)
        return False

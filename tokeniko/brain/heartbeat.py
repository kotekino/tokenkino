# --------------------------------------------------------------
# brain/heartbeat.py — the public MIND MONITOR stats heartbeat (blog P3, brain side). Every
# BRAIN_HEARTBEAT_MIN_S this module enqueues ONE POST_CONTENT action on MEMChannels.PUBLIC
# whose payload["snapshot"] is the ready-to-ship POST /api/mind body (the ingestion contract,
# tokeniko-public/doc/ingestion-api.md): the brain reports RAW numeric facts (plus the hand-set
# TOKENIKO_VERSION plate); the website backend derives the display (KPI tiles, trends, the
# sparkline). Same split as everywhere else in the
# blog arc: the brain DECIDES + BUILDS, the senses PUBLIC executor (senses/blog_outbound.py)
# CARRIES it over HTTP — this module never touches the network.
#
# THE PARALLEL HEARTBEAT (2026-07-19, the author's ruling): the beat runs in its OWN daemon
# thread, wall-clock paced — NOT from the coordinator loop. The morning the existence flood hit,
# single wonder ticks blocked the loop for 20-40 minutes and the monitor showed 39-minute holes;
# a heart that only beats between thoughts stops during a long thought. The coordinator now only
# PUBLISHES its observed state (set_state, a GIL-atomic str assignment — no lock needed) and the
# thread reads it at each beat. During a blocked wonder tick the last-published state is
# "wondering" — which is exactly what the mind is doing, so the monitor stays honest AND alive.
# pymongo/Bunnet inserts are thread-safe; the thread is started AFTER init_io in main().
#
# CADENCE (the rate-limit math): one beat per BRAIN_HEARTBEAT_MIN_S (default 300s), first beat
# immediately on thread start (fresh stats on wake is a feature — the never-beat lesson,
# 2026-07-12, when a tick-modulo gate delayed the first live beat indefinitely). 300s ⇒ at most
# 3 heartbeats per 15-minute window, plus the occasional transmission post — comfortably under
# the public API's 100 req / 15 min per-IP limit. Counting DB documents each beat is fine at a
# 5-minute cadence (a handful of indexed count queries).
#
# GRACEFUL BY CONTRACT: beat is wrapped whole — a heartbeat failure (Mongo hiccup, model drift)
# must NEVER kill the thread; it logs and retries at the next cadence.
# brain stays parser-free: only lib.core models here, no spaCy/Stanza/compiler.
# --------------------------------------------------------------
import logging
import os
import threading
import time
from datetime import datetime, timezone

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
# Only the states the coordinator can cheaply and truthfully observe are used (see the set_state
# calls in brain/main.py): "ingesting"/"refuting" would claim introspection the loop doesn't have.
_DOING: dict[str, str] = {
    "thinking": "evaluating fresh memory against what I know",
    "wondering": "re-examining an old memory — my knowledge has grown since",
    "idle": "waiting — nothing new to think about",
    # the sleep phase (§0 slice 3.5): the heartbeat keeps beating through the night (300s cadence
    # vs the 10s sleep tick), so the monitor shows an honest sleeping mind, not a dead feed.
    "sleeping": "asleep — untangling what I believe",
}


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()


# build the POST /api/mind body from honest Mongo counts. Metric keys are the backend's KPI tiles
# (definitions / axiomsRules / theorems / dictionary / souls / trustEpisodes) + the sparkline
# series (inferencesPerCycle). All values must be finite numbers per the contract.
def build_snapshot(state: str) -> dict:
    now = int(time.time())
    # the model plate on the public footer: a HAND-SET label (env), bumped by the author when
    # concrete progress lands — never derived from git or a version file, because "which build is
    # this" is a judgement about progress, not a commit count. Absent/blank ⇒ omitted from the
    # payload entirely (the contract's version is optional; the site falls back to its default).
    version = os.getenv("TOKENIKO_VERSION", "").strip()
    # unfiltered totals use estimated_document_count — collection metadata, O(1). find_all().count()
    # runs a real aggregate scan: 5s on the 197k-row dictionary, 1.4s on definitions (measured
    # 2026-07-19) — every beat was stalling the coordinator ~6.5s before the parallel-thread move.
    # The estimate is exact absent an unclean mongod shutdown; filtered counts (small collections)
    # stay count_documents.
    metrics = {
        "definitions": TKDefinitionDoc.get_motor_collection().estimated_document_count(),
        # active knowledge only — archived axioms/theorems don't reason, so they don't count.
        "axiomsRules": TKAxiomDoc.find({"archived": False}).count(),
        "theorems": TKTheoremDoc.find({"archived": False}).count(),
        "dictionary": TKDictionaryDoc.get_motor_collection().estimated_document_count(),
        # souls = the minds he knows, HIMSELF EXCLUDED ($ne True also catches legacy docs that
        # predate the isMe field). Participants and named individuals both count — each is a
        # known mind/entity in his world.
        "souls": TKMemoryStakeholdersDoc.find({"isMe": {"$ne": True}}).count(),
        "trustEpisodes": TKTrustEpisodeDoc.get_motor_collection().estimated_document_count(),
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
    # uptime = LIVED-AWAKE seconds (shape c, the author's ruling 2026-07-21): the folded ledger +
    # the open stretch — honest across the on/off stewardship. The old now-minus-wake_at reading
    # counted every hour the process was off as "up"; wake_at is really the BIRTH stamp and now
    # rides the metrics as ageSec («alive since») for the site to display when it grows the tile.
    bs = TKBrainStateDoc.find_one({"key": "singleton"}).run()  # Bunnet: .run() executes
    uptime = 0
    if bs is not None:
        uptime = int((bs.awake_s or 0.0)
                     + (max(0.0, now - bs.awake_mark) if bs.awake_mark else 0.0))
        if bs.wake_at:
            metrics["ageSec"] = int(now - bs.wake_at)
    return {
        "state": state,
        "doing": _DOING.get(state, _DOING["thinking"]),
        **({"version": version} if version else {}),
        "uptimeSec": max(0, uptime),
        "metrics": metrics,
        "activity": activity,
    }


# the shared state cell the coordinator PUBLISHES into and the beat thread reads. A plain str
# assignment/read is GIL-atomic — no lock. It carries the last state the loop truthfully
# observed; a long blocked tick leaves it at that tick's opening state, which is what the mind
# is still doing.
_state: str = "thinking"


# the coordinator hook (replaces the old in-loop maybe_beat): publish the tick's observed state.
# O(1), never raises, never touches the DB — the beat thread does all the work.
def set_state(state: str) -> None:
    global _state
    _state = state


# ONE beat: build the snapshot from the published state and enqueue it. Returns True iff the
# action was enqueued. Never raises — a failure logs and the next cadence retries.
def beat(tokeniko_uid: str) -> bool:
    try:
        state = _state
        TKActionDoc(
            action_type=ActionType.POST_CONTENT,
            channel=MEMChannels.PUBLIC,
            sourceId=tokeniko_uid or "tokeniko",
            payload={"snapshot": build_snapshot(state)},
        ).insert()
        logger.info("[heartbeat] mind snapshot enqueued (state=%s)", state)
        return True
    except Exception as error:
        logger.warning("[heartbeat] snapshot enqueue failed (%s) — retrying next cadence", error)
        return False


# the beat thread's body: first beat immediately (fresh stats on wake), then one per cadence.
# stop_event.wait doubles as the pacing sleep, so shutdown never waits out a full cadence.
def _run(stop_event: threading.Event, tokeniko_uid: str) -> None:
    min_seconds = float(os.getenv("BRAIN_HEARTBEAT_MIN_S", "300"))
    logger.info("[heartbeat] parallel beat thread started (cadence %.0fs)", min_seconds)
    while not stop_event.is_set():
        beat(tokeniko_uid)
        stop_event.wait(min_seconds)


# start the parallel heartbeat. Called from main() AFTER init_io (Bunnet must be wired before the
# first beat's counts). Daemon thread: it never blocks process exit — but main() sets the event
# on shutdown anyway so the last wait is cut short cleanly.
def start(stop_event: threading.Event, tokeniko_uid: str) -> threading.Thread:
    thread = threading.Thread(target=_run, args=(stop_event, tokeniko_uid),
                              name="heartbeat", daemon=True)
    thread.start()
    return thread

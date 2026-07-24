# --------------------------------------------------------------
# brain/context.py — the SHORT-TERM CONTEXT RING (compose 2.0 slice 5; the working-memory SEED —
# hunch 20's social column, deliberately its first brick).
#
# A per-channel RAM ring of the recent conversation: (speaker_uid, zip, original, ts, mine). A
# CACHE, never a source of truth — fully derivable from the memory timeseries (fed live by
# thinking as items are processed; lazily WARMED from the timeseries tail on first touch per
# channel), so a restart rebuilds it and a crash costs nothing biographical. Consumers:
#   - others' rows -> the TOPIC CENTROID (the mean 2925-semantic of the recent channel talk) —
#     the seed the anecdote's KB association scan matches against;
#   - own rows / RAM state -> the NOVELTY check + the per-channel anecdote COOLDOWN (the social
#     throttles: a wrong or repeated association costs more than silence).
#
# THE ASSOCIATION SCAN: the active KB (axioms + theorems, archived=False) is tens-to-hundreds of
# rows — an in-memory cosine scan over cached per-doc centroids is cheaper and index-free at this
# scale (the laptop-ceiling ruling: honest big-O now; Mongo $vectorSearch becomes right when the
# KB grows). The floor is CONSERVATIVE and env-tunable (ANECDOTE_FLOOR) — an explicit calibration
# point. PARSER-FREE: Mongo reads + numpy only.
# --------------------------------------------------------------
import json
import logging
import os
import time
from datetime import timezone
from collections import deque
from dataclasses import dataclass
from typing import Optional

import numpy as np

from lib.core.kb_extract import _zip_leaves
from lib.core.models import TKAxiomDoc, TKMemoryItemDoc, TKTheoremDoc

logger = logging.getLogger("tokeniko-brain")

_RING_MAX = int(os.getenv("BRAIN_CONTEXT_RING_MAX", "30"))
_RING_WINDOW_S = float(os.getenv("BRAIN_CONTEXT_WINDOW_S", "1800"))     # 30 min of talk
_ANECDOTE_FLOOR = float(os.getenv("ANECDOTE_FLOOR", "0.6"))             # conservative; calibrate live
_ANECDOTE_COOLDOWN_S = float(os.getenv("ANECDOTE_COOLDOWN_S", "1800"))  # one side-note per half hour
_KB_CACHE_TTL_S = float(os.getenv("BRAIN_CONTEXT_KB_TTL_S", "600"))

_MARKER_DIMS, _SEMANTIC_DIMS = 300, 2925


@dataclass
class ContextRow:
    speaker_uid: str
    zip: object                # TKZip or None (self-speech rows are zip-less)
    original: str
    ts: float                  # epoch seconds
    mine: bool


# module state — RAM only, derivable, rebuilt on restart
_rings: dict[str, deque] = {}
_warmed: set[str] = set()
_last_anecdote: dict[str, float] = {}                  # channel key -> epoch of the last side-note
_mentioned: dict[str, dict[str, float]] = {}           # channel key -> {notion_id: epoch}
_kb_centroids: Optional[list[tuple[str, str, np.ndarray]]] = None  # (doc_id, original, centroid)
_kb_loaded_at: float = 0.0


def _epoch(ts) -> float:
    # Mongo returns NAIVE datetimes that ARE UTC — .timestamp() on a naive value reads it as
    # LOCAL time (the +9h JST trap thinking._epoch_utc already guards): pin UTC first.
    try:
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc).timestamp()
        return ts.timestamp()
    except AttributeError:
        return float(ts)


# the channel key of a memory item: the Discord channel id when the metadata carries one (one ring
# per room), else the channel enum value (api / internal talk shares one ring per channel kind).
def channel_key(item) -> str:
    try:
        meta = json.loads(getattr(item, "metadata", None) or "{}")
        if isinstance(meta, dict) and meta.get("channel_id"):
            return str(meta["channel_id"])
    except (ValueError, TypeError):
        pass
    channel = getattr(item, "channel", None)
    return str(getattr(channel, "value", channel) or "unknown")


# the mean 2925-semantic of a zip's content-bearing role tensors (subject/predicate/direct per
# leaf; zero blocks skipped — an absent role says nothing about the topic). None for no signal.
def zip_semantic(zp) -> Optional[np.ndarray]:
    if zp is None:
        return None
    vecs = []
    for leaf in _zip_leaves(zp.items):
        for role in (getattr(leaf, "subject", None), getattr(leaf, "predicate", None),
                     getattr(leaf, "direct", None)):
            if role:
                sem = np.asarray(role[_MARKER_DIMS:_MARKER_DIMS + _SEMANTIC_DIMS], dtype=np.float32)
                if np.any(sem):
                    vecs.append(sem)
    if not vecs:
        return None
    return np.mean(vecs, axis=0)


def _evict(ring: deque) -> None:
    horizon = time.time() - _RING_WINDOW_S
    while ring and ring[0].ts < horizon:
        ring.popleft()


# lazily warm a channel's ring from the memory tail — the cache is DERIVABLE by construction.
# The metadata channel filter is applied in Python (metadata is a JSON string, not queryable);
# the scan is bounded (the newest 100 rows of the item's channel kind).
def _warm(key: str, sample_item) -> None:
    if key in _warmed:
        return
    _warmed.add(key)
    try:
        channel = getattr(sample_item, "channel", None)
        tail = (TKMemoryItemDoc.find({"channel": getattr(channel, "value", channel)})
                .sort("-timestamp").limit(100).to_list())
    except Exception as error:
        logger.warning("[context] warm failed for %s (%s) — ring starts cold", key, error)
        return
    ring = _rings.setdefault(key, deque())
    me = _self_uid()
    for it in reversed(tail):
        if channel_key(it) != key:
            continue
        ring.append(ContextRow(
            speaker_uid=str(it.sourceId), zip=it.zip, original=it.original or "",
            ts=_epoch(it.timestamp), mine=(me is not None and str(it.sourceId) == me)))
    while len(ring) > _RING_MAX:
        ring.popleft()
    _evict(ring)


_self_uid_cache: Optional[str] = None


def _self_uid() -> Optional[str]:
    global _self_uid_cache
    if _self_uid_cache is None:
        try:
            from lib.core.io import get_tokeniko
            _self_uid_cache = str(get_tokeniko().id)
        except Exception:
            return None
    return _self_uid_cache


# feed one processed memory item into its channel's ring (thinking calls this for every item it
# looks at — questions and assertions alike: it is all channel talk).
def context_add(item) -> None:
    key = channel_key(item)
    _warm(key, item)
    ring = _rings.setdefault(key, deque())
    me = _self_uid()
    ring.append(ContextRow(
        speaker_uid=str(item.sourceId), zip=item.zip, original=item.original or "",
        ts=_epoch(item.timestamp), mine=(me is not None and str(item.sourceId) == me)))
    while len(ring) > _RING_MAX:
        ring.popleft()
    _evict(ring)


# how many of `uid`'s rows the channel's ring currently holds (the mimicry MOMENTUM read, §1
# learned scaffolds): a DERIVED count over the live ring, never stored state — «after a while» of
# talking with someone is just their depth in the working memory. `uid` is the ring's speaker key
# (str(sourceId), the channel body), matching how context_add stamps rows.
def talker_depth(key: str, uid: str) -> int:
    ring = _rings.get(key)
    if not ring:
        return 0
    _evict(ring)
    return sum(1 for row in ring if row.speaker_uid == uid)


# the channel's TOPIC CENTROID: the mean semantic of OTHERS' recent zips (his own speech follows
# the topic, it does not define it). None = no signal (empty/cold ring).
def topic_centroid(key: str) -> Optional[np.ndarray]:
    ring = _rings.get(key)
    if not ring:
        return None
    _evict(ring)
    vecs = [v for row in ring if not row.mine and row.zip is not None
            for v in (zip_semantic(row.zip),) if v is not None]
    if not vecs:
        return None
    return np.mean(vecs, axis=0)


# ---- the KB association scan --------------------------------------------------------------------------

def _load_kb_centroids() -> list[tuple[str, str, np.ndarray]]:
    global _kb_centroids, _kb_loaded_at
    now = time.time()
    if _kb_centroids is not None and now - _kb_loaded_at < _KB_CACHE_TTL_S:
        return _kb_centroids
    out: list[tuple[str, str, np.ndarray]] = []
    try:
        for doc_cls in (TKAxiomDoc, TKTheoremDoc):
            for doc in doc_cls.find({"archived": False}).to_list():
                if doc.zip is None or not (doc.original or "").strip():
                    continue
                sem = zip_semantic(doc.zip)
                if sem is not None:
                    out.append((str(doc.id), doc.original.strip(), sem))
    except Exception as error:
        logger.warning("[context] KB centroid load failed (%s) — no associations this pass", error)
        return _kb_centroids or []
    _kb_centroids, _kb_loaded_at = out, now
    logger.debug("[context] KB centroids cached: %d notions", len(out))
    return out


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# find the nearest KB notion to the channel's current topic — the ideas-association. Returns
# {"notion", "notion_id", "proximity"} or None. Gates, each a social cost: the CONSERVATIVE
# proximity floor (a wrong association costs more than silence), the per-channel COOLDOWN (no
# trivia machine), and NOVELTY (a notion mentioned here recently never repeats).
def find_association(key: str) -> Optional[dict]:
    now = time.time()
    if now - _last_anecdote.get(key, 0.0) < _ANECDOTE_COOLDOWN_S:
        return None
    centroid = topic_centroid(key)
    if centroid is None:
        return None
    seen = _mentioned.get(key, {})
    best: Optional[tuple[float, str, str]] = None
    for doc_id, original, sem in _load_kb_centroids():
        if doc_id in seen and now - seen[doc_id] < _RING_WINDOW_S * 4:
            continue  # novelty: told here recently
        p = _cosine(centroid, sem)
        if best is None or p > best[0]:
            best = (p, doc_id, original)
    if best is None or best[0] < _ANECDOTE_FLOOR:
        return None
    return {"proximity": best[0], "notion_id": best[1], "notion": best[2]}


# record that the side-note actually SPAWNED (called only then): arms the cooldown + novelty.
def record_anecdote(key: str, notion_id: str) -> None:
    now = time.time()
    _last_anecdote[key] = now
    _mentioned.setdefault(key, {})[notion_id] = now


# test seam: drop all RAM state (the cache is derivable — this is exactly a restart).
def reset() -> None:
    global _kb_centroids, _kb_loaded_at, _self_uid_cache
    _rings.clear()
    _warmed.clear()
    _last_anecdote.clear()
    _mentioned.clear()
    _kb_centroids, _kb_loaded_at, _self_uid_cache = None, 0.0, None

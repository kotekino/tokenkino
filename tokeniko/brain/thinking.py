# --------------------------------------------------------------
# brain/thinking.py — the Thinking cognition (#4 D1a). Closes perceive -> evaluate -> ideas:
# it reads stored `memory` TKZips, evaluates each against the current KB via the PARSER-FREE
# evaluate_zip harness, maps the outcome to a reserved eval:* token, and fans it into ideas through
# the behavior layer (which Priorities then arbitrates into actions).
#
# PARSER-FREE by construction: imports only the harness + lib.core.* + brain.behavior — never the
# parser/compiler — so the brain process never loads spaCy/Stanza. One bounded memory item per tick
# (think_one) keeps Thinking cooperative with the coordinator's Actions/Priorities phases.
#
# D1b (still next): wondering (self-prompted derivation over the wondering window), theorem
# derivation (necessary truths -> KB), and the eval:true novelty split (redundant -> ignore vs a
# novel KB-bridging truth taught externally -> learn).
# --------------------------------------------------------------
import logging
from datetime import datetime, timezone
from typing import Optional

import lib.core.evaluation_harness as evaluation_harness
from lib.core.evaluation_harness import evaluate_zip
from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.memory import EvalToken
from lib.core.models import TKMemoryItemDoc, TKBrainStateDoc
from brain import behavior

logger = logging.getLogger("tokeniko-brain")

# strong-conclusion bands on a RESOLVED fuzzy truth: only the confident corners spawn an idea.
# the mid band (between FALSE_CEIL and TRUE_FLOOR) is "resolved-mid" — no strong conclusion, no idea.
TRUE_FLOOR = 0.85
FALSE_CEIL = 0.15


# memory `timestamp` is stored tz-aware UTC, but the timeseries collection reads it back NAIVE
# (tzinfo=None). .timestamp() on a naive datetime is interpreted in LOCAL time — a tz-skewed epoch.
# normalize: a naive ts is UTC, so the cursor is consistent regardless of the host tz.
# KEEP SUB-SECOND precision (float, NOT int): the stored ts has ms precision, so truncating the cursor
# to whole seconds leaves the just-processed item still `> cursor` (X.7 > X.0) → it is re-found and
# re-thought every tick (the obsessive loop). A sub-second cursor excludes it (strict `>` at ms).
def _epoch_utc(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()


# map an evaluation result to its reserved eval:* trigger token (the meta-language trigger side).
# INCONSISTENT -> eval:inconsistent (logic violation); INSUFFICIENT -> eval:unknown (missing KB);
# RESOLVED splits by truth confidence: > TRUE_FLOOR -> eval:true, < FALSE_CEIL -> eval:false,
# else None (resolved but no strong conclusion -> no idea spawned).
def status_to_token(result: EvaluatorResult) -> Optional[str]:
    if result.status == EvaluatorStatus.INCONSISTENT:
        return EvalToken.INCONSISTENT.value
    if result.status == EvaluatorStatus.INSUFFICIENT:
        return EvalToken.UNKNOWN.value
    if result.status == EvaluatorStatus.RESOLVED:
        if result.truth > TRUE_FLOOR:
            return EvalToken.TRUE.value
        if result.truth < FALSE_CEIL:
            return EvalToken.FALSE.value
    return None


# process ONE memory item (a bounded work-unit for the coordinator). PER-USER-GROUPED scan (#1):
# rather than one global oldest-first stream, it focuses on the LIVELIEST conversation — the speaker
# who owns the single newest unprocessed message — and drains THAT speaker's window oldest-first
# (advancing only that speaker's cursor) before the focus moves on. So tokeniko reads as present in
# the live chat: a fresh message makes its speaker the focus and an action spawns within a tick or
# two; quiet backlogs are served once the lively conversation is drained (and, eventually, by the
# wondering state). Per-speaker cursors are what let the focus jump between speakers without a single
# global cursor leaping past — and dropping — another conversation's unprocessed backlog.
#
# It evaluates the chosen item, maps the outcome to an eval:* token, and (if a strong conclusion)
# fans it into ideas; then cross-checks the same speaker's priors for a context conflict. Advances +
# persists that speaker's cursor so the item is never reprocessed. Returns True iff it processed one.
#
# First-run guard: if wake_at is None, initialize it to the latest memory ts and return False —
# tokeniko only reacts to memory that ARRIVES AFTER it first wakes, never re-thinks all of history.
def think_one(brain_state: TKBrainStateDoc) -> bool:
    wake = brain_state.wake_at
    if wake is None:
        latest = (
            TKMemoryItemDoc.find({})
            .sort("-timestamp")
            .limit(1)
            .to_list()
        )
        if latest:
            brain_state.wake_at = _epoch_utc(latest[0].timestamp)
        else:
            brain_state.wake_at = datetime.now(timezone.utc).timestamp()
        brain_state.save()
        return False

    wake_dt = datetime.fromtimestamp(wake, timezone.utc)
    # every memory item past the wake boundary, with a zip, NEWEST-first (so the first eligible item
    # we hit is the single newest unprocessed message across all speakers → its speaker is the focus).
    candidates = (
        TKMemoryItemDoc.find({"timestamp": {"$gt": wake_dt}})
        .sort("-timestamp")
        .to_list()
    )
    cursors = dict(brain_state.source_cursors or {})
    # eligible = unprocessed per its OWN speaker's cursor (default floor = the wake boundary).
    eligible = [
        c
        for c in candidates
        if c.zip is not None and _epoch_utc(c.timestamp) > cursors.get(c.sourceId, wake)
    ]
    if not eligible:
        return False

    # FOCUS = the speaker who owns the newest eligible message (candidates are newest-first, so it is
    # eligible[0]'s speaker). Within that speaker, process the OLDEST eligible item — draining their
    # window chronologically (priors before posteriors, which the cross-item check below relies on).
    focus_source = eligible[0].sourceId
    item = min(
        (c for c in eligible if c.sourceId == focus_source),
        key=lambda c: c.timestamp,
    )

    out = evaluate_zip(item.zip)
    result: EvaluatorResult = out["result"]
    token = status_to_token(result)

    if token:
        ideas = behavior.spawn_ideas_for(token, payload=item.zip, source=str(item.id))
        logger.info(
            "[thinking] evaluated memory=%s status=%s truth=%.3f -> %s (%d idea(s))",
            str(item.id),
            result.status.value,
            result.truth,
            token,
            len(ideas),
        )
    else:
        logger.info(
            "[thinking] evaluated memory=%s status=%s truth=%.3f -> no strong conclusion",
            str(item.id),
            result.status.value,
            result.truth,
        )

    # --------------------------------------------------------------
    # CROSS-ITEM CONSISTENCY (#4 D): besides the single-item eval above, cross-check this item
    # against the SAME speaker's recent prior items for a contradiction. A cross-item contradiction
    # is a REVISABLE CONTEXT conflict ("you said the cat is alive, now you say it's dead — which
    # holds?") — NOT the hardwired logic INCONSISTENT (that is reserved for X∧¬X within ONE
    # statement). On a conflict, emit eval:conflict (the seeded personality maps it to
    # tokeniko:clarify). Parser-free: classifyForm over a synthetic union of the two items' clauses.
    #
    # DEFERRED: (1) cross-SPEAKER patterns — this is SAME-SPEAKER only; (2) inference-implied
    # conflicts (e.g. "eating" vs "dead") that need forward-chaining — this catches DIRECT contraries
    # (X∧¬X / antonym-predicate) only.
    n_clauses = evaluation_harness._zip_leaves(item.zip.items)
    priors = (
        TKMemoryItemDoc.find(
            {"sourceId": item.sourceId, "timestamp": {"$lt": item.timestamp}}
        )
        .sort("-timestamp")
        .limit(25)
        .to_list()
    )
    for m in priors:
        if m.zip is None:
            continue
        detail = evaluation_harness.cross_item_conflict(
            n_clauses + evaluation_harness._zip_leaves(m.zip.items)
        )
        if detail:
            behavior.spawn_ideas_for(
                EvalToken.CONFLICT.value, payload=item.zip, source=str(item.id)
            )
            logger.info(
                "[thinking] cross-item conflict: memory=%s vs %s -> eval:conflict (%s)",
                str(item.id),
                str(m.id),
                detail,
            )
            break  # one conflict idea per N (idempotent dedups re-ticks anyway)

    # advance ONLY the focus speaker's cursor past this item (sub-second, so the just-processed item
    # is strictly excluded next tick — the obsessive-loop guard). Other speakers' cursors are untouched,
    # so their backlogs survive the focus jump. Reassign the dict so the doc-save persists the mutation.
    cursors[focus_source] = _epoch_utc(item.timestamp)
    brain_state.source_cursors = cursors
    brain_state.save()
    return True

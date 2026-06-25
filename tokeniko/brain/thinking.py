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
# D1b (landing here): theorem derivation + the eval:true novelty split — a RESOLVED-true input whose
# derivation carries a FORWARD-CHAINED materialization ("chain: ...") is genuine derived knowledge and
# is silently materialized as an active theorem (tier-2, speaker-irrelevant). See materialize_theorem.
# STILL next: wondering (self-prompted derivation over the wondering window), and the tier-1 split (an
# eval:true that is NOT KB-derivable but taught by a trusted speaker -> learn at teacher trust).
# --------------------------------------------------------------
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

import lib.core.evaluation_harness as evaluation_harness
from lib.core.evaluation_harness import evaluate_zip
from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.io import get_tokeniko
from lib.core.memory import EvalToken, MEMChannels
from lib.core.models import (
    TKAxiomDoc,
    TKBrainStateDoc,
    TKDefinitionDoc,
    TKMemoryItemDoc,
    TKTheoremDoc,
)
from brain import behavior

logger = logging.getLogger("tokeniko-brain")

# strong-conclusion bands on a RESOLVED fuzzy truth: only the confident corners spawn an idea.
# the mid band (between FALSE_CEIL and TRUE_FLOOR) is "resolved-mid" — no strong conclusion, no idea.
TRUE_FLOOR = 0.85
FALSE_CEIL = 0.15

# WONDERING tunables (see wonder_one).
WONDER_QUEUE_CAP = 256     # max pending re-examinations (lifespan-bounded work, not history-bounded)
DRIFT_INTERVAL = 60        # seconds of wondering-idle before a drift (random) batch is enqueued
DRIFT_BATCH = 4            # how many random memory ids a drift batch enqueues


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


# the D1b novelty split. A RESOLVED-true input's `derivation` may carry several provenance strings;
# only a FORWARD-CHAINED materialization is theorem-worthy:
#   "chain: ..."   — a UNIVERSAL rule fired down the is_a taxonomy to derive a NEW property
#                    ("all carnivores eat meat" + cat is_a* carnivore => "a cat eats meat"). This is
#                    knowledge DEMONSTRATED from axioms + the hardwired operator math => a THEOREM.
#   "subsumed:"/"part_of:" — trivial taxonomy, re-derivable from the graph on demand => NOT a theorem.
#   "refuted:"/"KB-refuted:" — a refutation (truth~0), not a truth at all => never a theorem.
# A derived theorem is TIER-2 = speaker-irrelevant (sourceId=tokeniko, trusted 0.9): it follows from
# the universal KB, not from who said it. TIER-1 (an eval:true that is NOT KB-derivable but taught by
# a trusted speaker) is DEFERRED — it needs a real KB-novelty signal, which this is not.
_CHAIN_PREFIX = "chain: "


def _derived_theorem(result: EvaluatorResult) -> bool:
    return any(d.startswith(_CHAIN_PREFIX) for d in (result.derivation or []))


# materialize a forward-chained truth as an ACTIVE theorem. SILENT learning (no idea/action) — it
# grows the KB, it does not speak. Idempotent by `original` (silence = consent: a re-derived truth
# already known is not re-stored). Caching the demonstrated conclusion lets future evals match it
# geometrically instead of re-deriving it every time. Returns True iff a NEW theorem was written.
def materialize_theorem(result: EvaluatorResult, item: TKMemoryItemDoc) -> bool:
    if item.zip is None or not _derived_theorem(result):
        return False
    if TKTheoremDoc.find_one({"original": item.original}).run() is not None:
        return False  # already a theorem — dedup by original
    chain = next(d for d in result.derivation if d.startswith(_CHAIN_PREFIX))
    TKTheoremDoc(
        original=item.original,
        zip=item.zip,
        sourceId=str(get_tokeniko().id),  # tier-2: tokeniko derived it — speaker-irrelevant
        channel=MEMChannels.INTERNAL,
        archived=False,                   # ACTIVE (model default is archived=True) -> joins reasoning
        trusted=0.9,
    ).save()
    logger.info("[thinking] derived THEOREM «%s» <- %s", item.original, chain)
    return True


# --------------------------------------------------------------
# WONDERING (#4 D1c) — the lowest-priority REFLECTIVE pass. Where think_one REACTS to fresh memory,
# wonder_one RE-EXAMINES memory tokeniko has ALREADY lived through, *because the KB has grown since*:
# a new definition/axiom/theorem can make an old, once-INSUFFICIENT input now KB-derivable. It is
# SILENT — knowledge only: it spawns NO ideas and NO actions, and it does NOT cross-item-check; a
# re-derived truth is materialized straight into a theorem (materialize_theorem, which dedups by
# `original` — that is what makes wondering converge instead of churning).
#
# Two drivers feed the wonder_queue (work-item ids), drained ONE per idle tick:
#   ASSOCIATIVE (driver 1) — KB-CHANGE-GATED: when active knowledge created AFTER last_wondered_kb_at
#       appears, its senses pick out the memory items that touch it (the deltas to recheck). Targeted.
#   DRIFT (driver 2) — when the queue is empty and a throttle has elapsed, enqueue a small RANDOM
#       batch of past items. Covers items the associative driver missed (e.g. queue overflow) and
#       keeps idle wondering alive even when the KB is static.
#
# Cost is FLAT per tick regardless of history: the queue is capped (WONDER_QUEUE_CAP), the KB load is
# fingerprint-cached (evaluate_zip), and drift is throttled (DRIFT_INTERVAL) + bounded ($sample).
# Coordinator wiring (when wonder_one runs vs think_one) lives in brain/main.py — NOT here.


# the active-knowledge createdAt watermark, computed CHEAPLY (one indexed newest-first row per model,
# never a full .to_list()). mirrors kb_fingerprint's _count_and_max but returns only the max ts.
def _kb_max_createdat() -> int:
    mx = 0
    for model in (TKDefinitionDoc, TKAxiomDoc, TKTheoremDoc):
        newest = model.find({"archived": False}).sort("-createdAt").limit(1).to_list()
        if newest:
            mx = max(mx, newest[0].createdAt)
    return mx


def wonder_one(brain_state: TKBrainStateDoc) -> bool:
    # 1. FIRST-RUN GUARD. Anchor the associative watermark at "now" so the entire seeded KB is not
    #    one giant delta on first wonder (mirrors think_one's wake_at first-run guard). No work yet.
    if brain_state.last_wondered_kb_at == 0:
        brain_state.last_wondered_kb_at = _kb_max_createdat() or int(time.time())
        brain_state.save()
        return False

    queue = list(brain_state.wonder_queue or [])

    # 2. ASSOCIATIVE ENQUEUE — active DELTA knowledge created after the watermark drives a re-check
    #    of the memory items whose senses overlap the delta's senses.
    delta_docs = []
    for model in (TKDefinitionDoc, TKAxiomDoc, TKTheoremDoc):
        delta_docs += model.find(
            {"archived": False, "createdAt": {"$gt": brain_state.last_wondered_kb_at}}
        ).to_list()
    if delta_docs:
        delta_senses: set[str] = set()
        for d in delta_docs:
            if d.zip is not None:
                delta_senses.update(evaluation_harness.zip_senses(d.zip))
        # advance the watermark past every delta doc we just serviced.
        brain_state.last_wondered_kb_at = max(
            brain_state.last_wondered_kb_at, max(d.createdAt for d in delta_docs)
        )
        if delta_senses:
            touched = (
                TKMemoryItemDoc.find({"senses": {"$in": list(delta_senses)}})
                .sort("-timestamp")
                .to_list()
            )
            in_queue = set(queue)
            dropped = 0
            for it in touched:
                sid = str(it.id)
                if sid in in_queue:
                    continue
                if len(queue) >= WONDER_QUEUE_CAP:
                    dropped += 1  # overflow — drift will sweep it up later
                    continue
                queue.append(sid)
                in_queue.add(sid)
            if dropped:
                logger.info("[wondering] associative: dropped %d over cap (queue=%d)", dropped, len(queue))
        brain_state.wonder_queue = queue
        brain_state.save()
        logger.info(
            "[wondering] associative: delta=%d senses=%d -> queued (queue=%d)",
            len(delta_docs), len(delta_senses), len(queue),
        )

    # 3. DRIFT ENQUEUE — only when there is no associative work pending. Throttled, and bounded by a
    #    Mongo $sample aggregation (random regardless of history size, no full scan).
    if not queue:
        now = int(time.time())
        last = brain_state.last_wondering_at
        if last is None or now - last >= DRIFT_INTERVAL:
            sampled = TKMemoryItemDoc.get_motor_collection().aggregate(
                [{"$match": {"zip": {"$ne": None}}},
                 {"$sample": {"size": DRIFT_BATCH}},
                 {"$project": {"_id": 1}}]
            )
            for row in sampled:
                queue.append(str(row["_id"]))
            brain_state.wonder_queue = queue
            brain_state.save()
            logger.info("[wondering] drift: queued %d random", len(queue))
        if not queue:
            return False  # nothing to do (no delta, drift throttled/empty)

    # 4. PROCESS ONE queued item. Pop + persist the cursor FIRST so a crash mid-eval doesn't re-pop it.
    item_id = queue.pop(0)
    brain_state.wonder_queue = queue
    brain_state.last_wondering_at = int(time.time())
    brain_state.save()

    try:
        oid = ObjectId(item_id)
    except Exception:
        return True  # stale/garbage id — consumed
    item = TKMemoryItemDoc.get(oid).run()  # Bunnet: .run() executes the query
    if item is None or item.zip is None:
        return True  # gone / no zip — consumed

    # SKIP questions — answered, not believed (wondering learns only assertions).
    leaves = evaluation_harness._zip_leaves(item.zip.items)
    if any(getattr(leaf, "dubitative", 0.5) >= 0.999 for leaf in leaves):
        return True

    out = evaluate_zip(item.zip)  # fingerprint-cached KB load
    result: EvaluatorResult = out["result"]
    if status_to_token(result) == EvalToken.TRUE.value:
        materialize_theorem(result, item)  # SILENT: knowledge only, no idea/action
    return True


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

    # --------------------------------------------------------------
    # QUESTION vs ASSERTION (#4 D, questions P3): a question is ANSWERED, not believed. answer_zip
    # returns None for a declarative (a cheap mood check BEFORE any KB load), so the assertion path
    # below is unchanged. For a question it computes the AnswerResult (polar yes/no/idk reusing the
    # truth machinery; wh value-solving) and fans an eval:question idea carrying the answer + the
    # asker (item.sourceId) as the reply target. A question is NOT a belief, so it does NOT run the
    # assertion eval (no speakup/etc.) and is NOT cross-item-conflict-checked.
    # --------------------------------------------------------------
    qout = evaluation_harness.answer_zip(item.zip)
    if qout is not None:
        answer = qout["answer"]
        ideas = behavior.spawn_ideas_for(
            EvalToken.QUESTION.value,
            payload=item.zip,
            source=str(item.id),
            answer=answer.model_dump(),
            target=item.sourceId,
        )
        logger.info(
            "[thinking] question memory=%s -> answer %s/%s conf=%.2f (%d idea(s))",
            str(item.id), answer.kind.value, answer.verdict.value, answer.confidence, len(ideas),
        )
    else:
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
            # D1b: a forward-chained eval:true is genuine derived knowledge -> learn it (silently).
            if token == EvalToken.TRUE.value:
                materialize_theorem(result, item)
        else:
            logger.info(
                "[thinking] evaluated memory=%s status=%s truth=%.3f -> no strong conclusion",
                str(item.id),
                result.status.value,
                result.truth,
            )

        # ----------------------------------------------------------
        # CROSS-ITEM CONSISTENCY (#4 D): cross-check this ASSERTION against the SAME speaker's recent
        # priors for a contradiction. A cross-item contradiction is a REVISABLE CONTEXT conflict
        # ("you said the cat is alive, now you say it's dead — which holds?") — NOT the hardwired
        # logic INCONSISTENT (X∧¬X within ONE statement). On a conflict, emit eval:conflict (the
        # seeded personality maps it to tokeniko:clarify). classifyForm over a synthetic union.
        #
        # DEFERRED: (1) cross-SPEAKER patterns — SAME-SPEAKER only; (2) inference-implied conflicts
        # ("eating" vs "dead") needing forward-chaining — DIRECT contraries (X∧¬X / antonym) only.
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
                n_clauses, evaluation_harness._zip_leaves(m.zip.items)
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

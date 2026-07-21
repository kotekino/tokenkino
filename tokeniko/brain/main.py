import asyncio
import logging
import os
import signal
import sys
import threading
import time
from typing import Optional

from dotenv import load_dotenv

from lib.core.io import init_io, get_tokeniko
from lib.core.models import TKIdeaDoc, TKActionDoc, TKBrainStateDoc
from lib.core.memory import (
    IdeaStatus,
    ActionStatus,
    ActionType,
    LifeEventKind,
    MEMChannels,
    TokenikoAction,
    TrustEpisodeKind,
    UrgeLevel,
)
from lib.core import trust
from brain import behavior
from brain import heartbeat
from brain import thinking

load_dotenv()

# Configurazione del logging per vedere cosa succede in console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tokeniko-brain")

# --------------------------------------------------------------
# brain orchestration — the HOW (step A). A SINGLE coordinator that, each tick, picks the
# highest-priority phase WITH WORK — Actions > Priorities > Thinking — runs ONE bounded unit, then
# cooperatively yields. The queue mechanics (grab / transition / drain, idea -> action creation) are
# REAL; the cognition (scoring, trigger -> action mapping, thinking derivation) is STUBBED — those are
# steps C (meta-language) and D (the WHAT / reasoning-engine). Every stub is marked inline.
#
# Concurrency note: a single coordinator process has no intra-process race, so the queue state
# machines use find + save (read, mutate, persist). The PRODUCTION upgrade — once multiple workers /
# overlapping execution frames are introduced — is an atomic MongoDB `find_one_and_update`
# (pending -> processing) so two workers can never grab the same item. See brain/README.md Appendix.
# --------------------------------------------------------------

# how long to sleep when only Thinking ran this tick (CPU throttle / good citizen)
IDLE_INTERVAL = 5.0
# cooperative yield between busy units (lets the loop stay responsive without saturating a core)
BUSY_YIELD = 0.05
# Priorities keep/discard floor: an idea must clear this urge to survive (wish = 0.5)
URGE_THRESHOLD = UrgeLevel.WISH.value
# IDLE CONFIRMATION before wondering (author's ruling 2026-07-16): wondering starts only when the
# quiet is CONFIRMED — no actions/priorities/reactive-thinking work for this many seconds. Between
# two sentences of a live conversation he keeps polling fresh memory (cheap, every IDLE_INTERVAL)
# instead of starting a daydream he'd have to finish first.
WONDER_IDLE_CONFIRM = float(os.getenv("BRAIN_WONDER_IDLE_CONFIRM_S", "60"))
# THE SLEEP PHASE (§0 slice 3.5, the author's design 2026-07-18): he falls asleep WONDERING —
# wondering allowed and FRUITLESS (no new result from any pass) for SLEEP_AFTER seconds. Asleep,
# wondering stops (kb_wonder every tick is not rest); only the reactive probe keeps running — the
# wake sensor. ANY work wakes him (his ruling: every event that exits wondering exits sleep), and
# SLEEP_MAX ends the night regardless (he wakes rested; a still-silent world naps again after a
# fresh SLEEP_AFTER of wakefulness). While asleep the cooperative tick lengthens to SLEEP_TICK —
# the embodied machine literally rests; a few seconds of wake latency reads as a mind stirring.
SLEEP_AFTER = float(os.getenv("BRAIN_SLEEP_AFTER_S", "600"))
SLEEP_MAX = float(os.getenv("BRAIN_SLEEP_MAX_S", "2700"))
SLEEP_TICK = float(os.getenv("BRAIN_SLEEP_TICK_S", "10"))
# TIREDNESS — the wakefulness bound (the author's ruling 2026-07-19, reversing fruitfulness-only
# sleep after the existence flood kept him up 4.5h straight: an inexhaustible wondering frontier
# means "sleep when nothing new comes" never triggers). The body's claim on the mind: awake for
# WAKE_MAX seconds ⇒ he falls asleep NO MATTER how fruitful the wondering is. Fork A (his
# ruling): reactive work (someone actually talking to him) DEFERS the collapse — you don't fall
# asleep mid-dialogue — but never resets the clock: at the first quiet tick past the bound he
# drops off. Staying up late talking doesn't make you less tired. Wondering defers nothing.
# Default 7200s ≈ a 2.5:1 wake-to-nap ratio against the 45-min SLEEP_MAX naps.
WAKE_MAX = float(os.getenv("BRAIN_WAKE_MAX_S", "7200"))
# the GOODNIGHT recency gate (survey slice 2, the author-approved spam trap): the falling-asleep
# edge speaks ONLY into a channel someone used within this window — you say goodnight to people
# who are around; an empty room gets the silent sleep (cycles are frequent: SLEEP_MAX naps would
# otherwise turn the goodnight into a chatterbox tic).
GOODNIGHT_RECENCY = float(os.getenv("GOODNIGHT_RECENCY_S", "3600"))


# --------------------------------------------------------------
# brain_state continuity singleton — persists the working-memory cursor + wondering window across
# process restarts, so tokeniko resumes its cycles (one continuous self).
# --------------------------------------------------------------
def get_or_create_brain_state() -> TKBrainStateDoc:
    bs = TKBrainStateDoc.find_one({"key": "singleton"}).run()
    if bs is None:
        bs = TKBrainStateDoc(key="singleton")
        bs.insert()
    return bs


# --------------------------------------------------------------
# Actions phase (The Executor) — strict FIFO. Pull the oldest pending action and carry it out.
# Returns True if it processed an action this tick, False if the queue was empty.
# --------------------------------------------------------------
def actions_phase(bs: Optional[TKBrainStateDoc] = None) -> bool:
    # INTERNAL channel ONLY (D3b): outward actions (discord/atproto) are carried out by `senses`, which
    # polls its OWN channel — the brain must NOT consume them (disjoint channel filters = no cross-process
    # race, no new status). INTERNAL = the KB-write reflexes (guess/learn) the brain executes itself.
    # PUBLIC post actions (blog P1) queue as PENDING here untouched — the carrier lands in P3.
    pending = (
        TKActionDoc.find(
            {"status": ActionStatus.PENDING.value, "channel": MEMChannels.INTERNAL.value}
        )
        .sort("createdAt")
        .limit(1)
        .to_list()
    )
    if not pending:
        return False

    action = pending[0]

    # grab: pending -> processing
    # (production: atomic find_one_and_update to avoid a multi-worker race — see module note)
    action.status = ActionStatus.PROCESSING
    action.save()

    # execute the INTERNAL action. UPDATE_TRUST (D P2) is REAL: record the episode on the target
    # speaker's ledger (kind = the trust:* trigger) + refold the cached scalar. guess/learn stay
    # stubbed (the D3a low-trust KB-write seam).
    if action.action_type == ActionType.UPDATE_TRUST:
        payload = action.payload or {}
        try:
            kind = TrustEpisodeKind(payload.get("trigger"))
        except ValueError:
            kind = None
        answer = payload.get("answer") or {}
        if kind is not None and action.targetId:
            # life:encounter (blog P1): spawned ONLY when the fold ACTUALLY MOVED — an imprinted
            # soul is pinned (fold never moves, episode still recorded, no idea), and a clamped
            # floor/ceiling fold that absorbs the delta is likewise not an event. Compare the
            # folded scalar before vs after the episode.
            trust_before = trust.trust_of(action.targetId)
            soul = trust.record_episode(
                action.targetId, kind,
                source_id=payload.get("source"),
                belief_trust=answer.get("belief_trust"),
                note=answer.get("note"),
            )
            if soul is not None:
                trust_after = 1.0 if soul.imprint else soul.trust
                if abs(trust_after - trust_before) > 1e-9:
                    behavior.spawn_ideas_for(
                        LifeEventKind.ENCOUNTER.value,
                        source=payload.get("source"),  # the original memory item behind the episode
                        material={
                            "kind": "encounter",
                            "soul_uid": soul.uid,       # the CANONICAL soul whose fold moved
                            "episode": kind.value,      # the trust:* kind
                            "trust_after": trust_after,
                            "note": answer.get("note"),
                        },
                        # flat significance: a fold move is already rare by construction.
                        urge_scale=thinking.ENCOUNTER_SIGNIFICANCE,
                    )
        else:
            logger.warning("[actions] malformed update_trust action %s dropped", str(action.id))
    elif action.action_type == ActionType.REVISE_BELIEF:
        _execute_retreat(action)
    elif (action.payload or {}).get("action_token") == TokenikoAction.LEARN.value:
        _execute_learn(action, bs)
    elif (action.payload or {}).get("action_token") == TokenikoAction.GUESS.value:
        _execute_guess(action)
    else:
        logger.info(
            "[actions] would execute %s on channel=%s target=%s (internal KB-write — TODO)",
            action.action_type,
            action.channel,
            action.targetId,
        )

    # transition: processing -> done
    action.status = ActionStatus.DONE
    action.save()
    return True


# the LEARN executor (survey slice 3, the B-wire — author's ruling): the taught-theorem MINT,
# moved out of think_one and behind the meta-language. The eval:novel -> tokeniko:learn rule is
# the personality switch of teachability; this executor is the hand. materialize_taught re-runs
# the full candidate check (race-safe: a lesson learned meanwhile dedups to an honest no-op).
# On a REAL mint, spawn eval:learned -> the curiosity trigger (target = the teacher; the topic =
# the normalized lesson): a novel lesson earns one deepening «why» — literally the kicker-hunting
# question (the closed why-loop is the twin-soul signal). Throttled at plan time (ASK_COOLDOWN_S).
def _execute_learn(action: TKActionDoc, bs: Optional[TKBrainStateDoc] = None) -> None:
    from bson import ObjectId
    from bson.errors import InvalidId
    from lib.core.models import TKMemoryItemDoc
    from lib.core.memory import EvalToken

    payload = action.payload or {}
    src = payload.get("source")
    item = None
    try:
        item = TKMemoryItemDoc.get(ObjectId(src)).run()  # Bunnet: .run() executes
    except (InvalidId, TypeError):
        item = None
    if item is None:
        logger.warning("[actions] learn action %s: source memory %r unresolvable — dropped",
                       str(action.id), src)
        return
    # bs threaded from the coordinator so a same-teacher run BATCHES into the digest buffer (the
    # post decision happens inside materialize_taught -> _spawn_life_theorem); None -> 1:1, as before.
    norm = thinking.materialize_taught(item, bs=bs)
    if norm is None:
        logger.info("[actions] learn action %s: nothing minted («%s» — raced/no longer teachable)",
                    str(action.id), item.original[:60])
        return
    behavior.spawn_ideas_for(
        EvalToken.LEARNED.value, payload=item.zip, source=str(item.id),
        target=item.sourceId, answer={"topic": norm},
    )


# the GUESS executor (survey slice 5): the hypothesis engine's hand — 138 stub firings become
# real content. materialize_hypothesis does the whole bar (still-UNKNOWN re-check, resemblance
# floor, deixis norm, dedup) and mints the low-trust hypothesis row, or honestly no-ops. SILENT
# by design (wondering's cousin): no follow-on idea, no post — the guess's death gets the dream.
def _execute_guess(action: TKActionDoc) -> None:
    from bson import ObjectId
    from bson.errors import InvalidId
    from lib.core.models import TKMemoryItemDoc

    payload = action.payload or {}
    src = payload.get("source")
    item = None
    try:
        item = TKMemoryItemDoc.get(ObjectId(src)).run()  # Bunnet: .run() executes
    except (InvalidId, TypeError):
        item = None
    if item is None:
        logger.warning("[actions] guess action %s: source memory %r unresolvable — dropped",
                       str(action.id), src)
        return
    norm = thinking.materialize_hypothesis(item)
    if norm is None:
        logger.info("[actions] guess action %s: no hypothesis formed («%s» — the bar held)",
                    str(action.id), item.original[:60])


# --------------------------------------------------------------
# BELIEF-REVISION v1 — the RETREAT executor (retreat arc #4). The payload's `answer` is the
# harness `correction_target` detail (already trust-gated by thinking): retractable source docs,
# defeated edge keys, the weakened subaltern, the corrector. Three moves + the follow-on:
#   1. ARCHIVE each retractable source doc (readonly axioms were excluded at detection) — archiving
#      IS the retreat: the doc stops yielding its edges at the next KB load (revocation durability
#      by construction). Never deleted — "true history be it".
#   2. CASCADE: revoke_dependents over the archived doc ids + the defeated edge keys — every
#      theorem whose proof rests on the retreated belief falls with it (archived, kept as history).
#   3. MINT the weakened subaltern (O-corner only): «all S are P» retreats down the square to
#      «some S are P» via the API materialize seam (sense-pinned, semantically deduped, trusted at
#      the corrector's level capped by the taught ceiling). API down -> logged skip, never a crash
#      (the retreat itself is complete without the mint).
#   4. SPAWN eval:correction-done -> tokeniko:concede (the directed acknowledgment): source = the
#      correction memory item (so the reply threads under it), target = the corrector.
# --------------------------------------------------------------
def _execute_retreat(action: TKActionDoc) -> None:
    from bson import ObjectId
    from bson.errors import InvalidId
    from lib.core import evaluation_harness
    from lib.core.models import TKAxiomDoc, TKTheoremDoc
    from lib.core.memory import EvalToken
    from brain import api_client

    payload = action.payload or {}
    ct = payload.get("answer") or {}
    sources = ct.get("sources") or []
    if not sources:
        logger.warning("[actions] malformed revise_belief action %s dropped", str(action.id))
        return

    now = int(time.time())
    retracted: list[str] = []
    archived_ids: list[str] = []
    archived_docs: list = []
    for s in sources:
        model = {"axiom": TKAxiomDoc, "theorem": TKTheoremDoc}.get(s.get("kind"))
        if model is None:
            continue
        try:
            doc = model.get(ObjectId(s["id"])).run()  # Bunnet: .run() executes
        except (InvalidId, TypeError):
            doc = None
        if doc is None or doc.archived or getattr(doc, "readonly", False):
            continue  # already gone, or hardwired-protected — never force
        doc.archived = True
        doc.archivedAt = now
        doc.save()
        archived_ids.append(str(doc.id))
        archived_docs.append(doc)
        retracted.append(doc.original)
        logger.info("[actions] RETREAT: archived %s «%s» (corrected by %s)",
                    s["kind"], doc.original, ct.get("corrector"))
    if not archived_ids:
        logger.warning("[actions] revise_belief %s: nothing retractable remained — no retreat",
                       str(action.id))
        return

    # 2. the cascade: dependents of the retreated docs AND of the defeated edges fall together.
    dependents = evaluation_harness.revoke_dependents(
        archived_ids + list(ct.get("edge_keys") or []), dry_run=False)

    # 3. retreat down the square: mint the surviving subaltern I (O-corner corrections only).
    weakened = ct.get("weakened")
    minted = None
    if weakened and weakened.get("tokens"):
        trusted = min(float(ct.get("corrector_trust", 0.9)), 0.9)  # taught ceiling
        wsenses = weakened.get("senses") or {}
        # ZIP-NATIVE (instrument arc #2): the subaltern is born as structure — no parser in the mint.
        structure = ({"subject": wsenses.get("subject"), "predicate": wsenses.get("predicate"),
                      "subject_kind": "class"}
                     if wsenses.get("subject") and wsenses.get("predicate") else None)
        minted = api_client.materialize_theorem(
            tokens=weakened["tokens"],
            premises=[f"corrected-by:{ct.get('corrector')}"] + archived_ids,
            chain=(f"retreat down the square: {ct.get('corner')}-corner correction by "
                   f"{ct.get('corrector')} defeats «{retracted[0]}» -> subaltern survives"),
            derived_by="retreat",
            trusted=trusted,
            structure=structure,
            senses=wsenses if structure is None else None,
        )
        if minted is None:
            logger.warning("[actions] retreat mint «%s» skipped (API unreachable) — retreat itself complete",
                           weakened["tokens"])

    # 4. the follow-on acknowledgment (sequential by construction — it states what ACTUALLY fell).
    behavior.spawn_ideas_for(
        EvalToken.CORRECTION_DONE.value,
        source=payload.get("source"),
        answer={
            "retracted": retracted,
            "dependents": len(dependents),
            "weakened": (weakened or {}).get("tokens"),
            "corrector": ct.get("corrector"),
        },
        target=ct.get("corrector"),
        # slice 2: the concession's confidence = the corrector's trust-gated certainty (the
        # retreat only ran because it cleared the belief's own trust — he concedes as surely
        # as he was corrected).
        confidence=ct.get("corrector_trust"),
    )

    # 5. the RETREAT TRANSMISSION (survey slice 2): a WAKING conversational retreat is
    # blog-worthy — «I changed my mind today» (the night's retreats stay dreams; this path only
    # runs awake, so no double post by construction). Provenance-gated: every fallen belief must
    # be postable (the DM taint cascades exactly like min-trust); the corrector is credited by
    # epithet only for a public exchange — «a friend» shields a DM correction.
    from lib.core.models import TKMemoryItemDoc
    postable = (all(getattr(d, "postable", True) for d in archived_docs)
                and all(getattr(t, "postable", True) for t in dependents))
    if postable:
        src_item = None
        try:
            src_item = TKMemoryItemDoc.get(ObjectId(payload.get("source"))).run()
        except (InvalidId, TypeError):
            src_item = None
        private = bool(src_item is not None and thinking._is_dm(src_item))
        behavior.spawn_ideas_for(
            LifeEventKind.RETREAT.value,
            source=payload.get("source"),
            material={
                "kind": "retreat",
                "retracted": retracted,
                "casualties": [t.original for t in dependents],
                "corrector": ct.get("corrector"),
                "private": private,
                "significance": 0.9,
            },
        )
    logger.info(
        "[actions] RETREAT complete: %d doc(s) archived, %d dependent theorem(s) cascaded, "
        "subaltern %s -> concede spawned",
        len(archived_ids), len(dependents),
        f"minted «{(weakened or {}).get('tokens')}»" if minted else "not minted",
    )


# COLLAPSE ARBITRATION (#4 D2): a decision point = the ideas sharing (source, trigger) — the
# superposition of candidate reflexes one evaluation fanned out (e.g. eval:unknown -> {why, guess}).
# When one is acted on, its still-pending siblings are SUPERSEDED (discarded) so tokeniko fires ONE
# reflex per decision, not every candidate. The winner is the highest-urge feasible one (ideas are
# pulled urge-desc, so the first KEPT idea of a group is its winner). Returns how many were superseded.
def _collapse_siblings(winner: TKIdeaDoc) -> int:
    if not winner.source:
        return 0  # no decision-point key (test / source-less spawn) -> nothing to collapse
    siblings = (
        TKIdeaDoc.find(
            {
                "source": winner.source,
                "trigger": winner.trigger,
                "parsed_by_prio": False,
                "status": IdeaStatus.PENDING.value,
            }
        )
        .to_list()
    )
    n = 0
    for s in siblings:
        if s.id == winner.id:
            continue
        s.status = IdeaStatus.DISCARDED
        s.parsed_by_prio = True
        s.save()
        n += 1
    return n


# --------------------------------------------------------------
# Priorities phase (The Filter) — urge x feasibility gatekeeper. Pull the oldest pending UNPARSED
# idea, score it, and either yield an Action (keep) or discard it. One idea per tick.
# Returns True if it processed an idea this tick, False if none awaited evaluation.
# --------------------------------------------------------------
def priorities_phase() -> bool:
    pending = (
        TKIdeaDoc.find(
            {"status": IdeaStatus.PENDING.value, "parsed_by_prio": False}
        )
        .sort("-urge")  # most-urgent candidate first (urge is also the conflict key)
        .limit(1)
        .to_list()
    )
    if not pending:
        return False

    idea = pending[0]

    # grab: pending -> processing
    # (production: atomic find_one_and_update — see module note)
    idea.status = IdeaStatus.PROCESSING
    idea.save()

    # PLAN the action this idea's reflex would yield (C: the reserved-token behavior layer — the
    # meta-language [eval:X] -> [tokeniko:Y], KB-driven personality). None = tokeniko:ignore / no reflex
    # -> a deliberate NO-OP (kept, nothing to execute), not a discard.
    plan = behavior.plan_action(idea, _tokeniko_uid)
    if plan is None:
        idea.feasibility = 0.0
        idea.parsed_by_prio = True
        idea.status = IdeaStatus.DONE
        idea.save()
        logger.info(
            "[priorities] idea trigger=%s action_token=%s -> ignore/no-op",
            idea.trigger, idea.action_token,
        )
        return True

    # D2 — the TWO axes (brain/README "urge vs feasibility"). URGE (how much it wants it) must clear the
    # threshold AND FEASIBILITY (can it actually be done) must be positive. Ties/conflicts -> urge.
    # C: the urge is scaled by the source perception's DIRECTEDNESS before the gate (behavior.
    # effective_urge) — the polite-guest discretion. (The pull above still sorts by RAW urge: within a
    # decision point directedness is constant so the winner is unchanged; across sources it only
    # affects processing order, and every idea is gated independently here.)
    # D P2 refinement: OUTWARD actions only — discretion is about acting on the world, not about
    # what he may conclude. An INTERNAL reflex (KB-write, trust update) keeps its raw urge: an
    # OVERHEARD lie still costs trust (we learn who people are by watching them talk to others).
    # Blog P1: PUBLIC (a broadcast post) is likewise exempt — self-expression is never scaled down
    # by addressing (how directed the STIRRING perception was says nothing about his own window;
    # a life:encounter idea's source IS a memory item, so without the exemption an ambient-sourced
    # fold move would be muted). Significance already shaped the urge at spawn.
    feasibility = behavior.score_feasibility(plan)
    idea.feasibility = feasibility
    idea.parsed_by_prio = True
    if plan["channel"] in (MEMChannels.INTERNAL, MEMChannels.PUBLIC):
        urge = idea.urge
    else:
        urge = behavior.effective_urge(idea, behavior._source_memory(idea))
    keep = urge >= URGE_THRESHOLD and feasibility > 0

    if keep:
        action = behavior.dispatch_action(idea, _tokeniko_uid, plan=plan)
        idea.status = IdeaStatus.DONE
        idea.save()
        # COLLAPSE the superposition: this kept idea WON its decision point (highest-urge feasible,
        # pulled first) -> supersede its still-pending sibling candidates so tokeniko fires ONE reflex,
        # not every candidate (e.g. eval:unknown -> WHY wins, GUESS superseded). Stochastic = future.
        superseded = _collapse_siblings(idea)
        logger.info(
            "[priorities] kept idea trigger=%s action_token=%s urge=%s (effective=%.2f) feas=%s -> action %s (%s); superseded %d sibling(s)",
            idea.trigger, idea.action_token, idea.urge, urge, feasibility,
            str(action.id) if action else None,
            action.action_type.value if action else None,
            superseded,
        )
    else:
        idea.status = IdeaStatus.DISCARDED
        idea.save()
        reason = "below urge threshold" if urge < URGE_THRESHOLD else "infeasible"
        logger.info(
            "[priorities] discarded idea trigger=%s action_token=%s urge=%s (effective=%.2f) feas=%s (%s)",
            idea.trigger, idea.action_token, idea.urge, urge, feasibility, reason,
        )
    return True


# --------------------------------------------------------------
# Thinking phase (The Generator) — the lowest-priority background filler ("thinks always, acts
# maybe"). Runs only when both queues are empty. Two sub-passes, REACTIVE first:
#   think_one  (D1a/D1b) — evaluate ONE FRESH `memory` TKZip vs the KB, fan eval:* into ideas + learn
#                          forward-chained theorems (closing perceive -> evaluate -> ideas -> actions).
#   wonder_one (D1c)     — only when there is nothing fresh: RE-EXAMINE a past item because the KB has
#                          grown (associative + drift), silently materializing any newly-derivable
#                          theorem. The reactive pass wins; wondering fills the idle.
# Returns WHICH sub-pass did a unit of work this tick — "think" | "wonder" | None (truthy iff any
# work, so the coordinator's brief-yield-vs-idle-sleep logic reads it like the old bool; the
# distinction feeds the heartbeat's honest state: reactive think vs idle-time wonder — blog P3).
# --------------------------------------------------------------
# `wonder_allowed` is the coordinator's idle-confirmation gate: the reactive pass (think_one) always
# runs; wondering additionally requires the confirmed quiet (see WONDER_IDLE_CONFIRM).
def thinking_phase(brain_state: TKBrainStateDoc, wonder_allowed: bool = True) -> Optional[str]:
    if thinking.think_one(brain_state):
        sub = "think"
    else:
        # the FRUITFULNESS distinction (sleep phase): wonder_one reports "derived" (new knowledge
        # — resets the sleep clock) vs "checked" (an idle re-examination that found nothing new —
        # the mind running dry; the drift driver's random batches land here, or he could never
        # fall asleep). Both map to the "wondering" heartbeat state — only the clock differs.
        w = thinking.wonder_one(brain_state) if wonder_allowed else False
        sub = "wonder" if w == "derived" else ("wonder-idle" if w else None)
    brain_state.last_thinking_at = int(time.time())
    brain_state.save()
    return sub


# --------------------------------------------------------------
# THE SLEEP PHASE helpers (§0 slice 3.5). Sleep is a MODE, never a blocker: the phase routing runs
# every tick regardless (the existing Actions > Priorities > think probe IS the wake sensor), so
# "every event that would have exited wondering exits sleep" holds by construction.
# --------------------------------------------------------------

# the night's duty: ONE untangle pass per sleep, KB-change-gated (an unchanged KB = deep rest).
# apply=True is safe UNSUPERVISED by the fork-D bar: convictions are logic (exactly-one-revisable),
# never a guess; undecidable tangles only queue ledger questions — he wakes with them on his lips.
# The dream material is STASHED (bs.pending_dream), told on waking — the telling never disturbs
# the sleep. In-process execution is serialized by the coordinator: no concurrency caveat.
def _sleep_duty(bs: TKBrainStateDoc) -> None:
    from lib.core.untangle import untangle_pass
    kb_now = thinking._kb_max_createdat()
    if kb_now <= (bs.last_untangled_kb_at or 0):
        logger.info("[sleep] the KB is unchanged since the last untangling — deep rest")
        return
    report = untangle_pass(apply=True)
    bs.last_untangled_kb_at = thinking._kb_max_createdat() or kb_now
    if report["convicted"]:
        bs.pending_dream = {"convicted": report["convicted"], "asked": report["asked"]}
    if report["asked"]:
        # the morning questions (the obsession guard): the undecidable tangles are stashed and
        # RE-ASKED on waking — waking up still-tangled is itself a reason to ask.
        bs.pending_questions = {"at": int(time.time()),
                                "signatures": [e["signature"] for e in report["asked"]]}
    bs.save()
    logger.info("[sleep] the night's untangling: %d absurdity(ies) — %d retreated, %d for the "
                "morning's questions, %d constitution-flagged",
                report["conflicts"], len(report["convicted"]), len(report["asked"]),
                len(report["constitution"]))


# the GOODNIGHT (survey slice 2): spoken at the falling-asleep edge, SYNCHRONOUSLY — the idea is
# born DONE (parsed_by_prio=True) and planned/dispatched right here, because a pending idea would
# be priorities-work next tick and the goodnight itself would wake him (the wake-catch). The rule
# stays KB personality (life:sleep -> tokeniko:goodnight in behavior_rules — no rule, no
# goodnight); the Discord action row waits for the senses carrier, which the sleeping brain never
# sees as work. The spam trap: only a recently-alive channel hears it (GOODNIGHT_RECENCY).
def _say_goodnight(bs: TKBrainStateDoc) -> None:
    from datetime import datetime, timezone
    from lib.core.models import TKMemoryItemDoc
    from lib.core.memory import TokenikoAction
    try:
        rules = behavior.behavior_for(LifeEventKind.SLEEP.value)
        rule = next((r for r in rules
                     if r.action == TokenikoAction.GOODNIGHT.value), None)
        if rule is None:
            return  # the personality keeps no goodnight — silent sleep
        me = get_tokeniko()
        since = datetime.fromtimestamp(time.time() - GOODNIGHT_RECENCY, tz=timezone.utc)
        recent = (TKMemoryItemDoc.find(
            {"channel": MEMChannels.DISCORD.value, "sourceId": {"$ne": str(me.id)},
             "timestamp": {"$gte": since}, "metadata": {"$ne": None}})
            .sort("-timestamp").limit(1).to_list())
        if not recent:
            return  # nobody around — goodnight is for people, never for empty rooms
        idea = TKIdeaDoc(
            trigger=LifeEventKind.SLEEP.value, action_token=TokenikoAction.GOODNIGHT.value,
            urge=rule.urge, source=str(recent[0].id),
            status=IdeaStatus.DONE, parsed_by_prio=True,  # born consumed — never queue work
        )
        idea.insert()
        plan = behavior.plan_action(idea, _tokeniko_uid)
        if plan is not None and behavior.score_feasibility(plan) > 0.0:
            behavior.dispatch_action(idea, _tokeniko_uid, plan)
            logger.info("[sleep] 🌙 he says goodnight to the room before drifting off")
    except Exception:
        logger.exception("[sleep] the goodnight failed — sleeping silently")


# a stashed dream is told on waking (spawn_dream is content-idempotent, so a re-told night dedups).
def _spawn_pending_dream(bs: TKBrainStateDoc) -> None:
    if not bs.pending_dream:
        return
    try:
        if thinking.spawn_dream(bs.pending_dream):
            logger.info("[sleep] ☀️ he tells his dream")
    except Exception:
        logger.exception("[sleep] the dream could not be told — let go")
    bs.pending_dream = None
    bs.save()


# the stashed MORNING QUESTIONS are asked on waking (author's ruling: waking up still-tangled is
# itself a reason to ask, whether he asked before or not — the obsession guard).
def _spawn_morning_questions(bs: TKBrainStateDoc) -> None:
    if not bs.pending_questions:
        return
    try:
        n = thinking.ask_morning_questions(bs.pending_questions)
        if n:
            logger.info("[sleep] ☀️ he wakes with %d question(s) on his lips", n)
    except Exception:
        logger.exception("[sleep] the morning questions could not be asked — let go")
    bs.pending_questions = None
    bs.save()


# the falling-asleep decision (pure, unit-testable — no clock, no DB): the reason he falls
# asleep this tick, or None. Two doors into the night:
#   "tired"     — the wakefulness bound (WAKE_MAX, the author's ruling 2026-07-19): awake too
#                 long ⇒ sleep NO MATTER how fruitful the wondering is. The existence flood
#                 proved fruitfulness-only sleep never triggers against an inexhaustible
#                 frontier. Fork A: a reactive tick (sub == "think") defers the collapse — you
#                 don't fall asleep mid-dialogue — and only CONFIRMED quiet (WONDER_IDLE_CONFIRM
#                 since the last reactive work) lets it land, so the pause between two sentences
#                 never reads as bedtime. Deferred, never reset: at the first confirmed-quiet
#                 tick past the bound he drops off. Wondering defers nothing.
#   "wondering" — the original edge (§0 slice 3.5): confirmed-quiet wondering FRUITLESS for
#                 SLEEP_AFTER — he falls asleep wondering.
def _sleep_reason(asleep_at: Optional[float], sub: Optional[str], now_m: float,
                  awake_since: float, last_busy: float,
                  last_fruitful: float) -> Optional[str]:
    if asleep_at is not None or sub == "think":
        return None
    if now_m - last_busy < WONDER_IDLE_CONFIRM:
        return None  # unconfirmed quiet — he might be mid-dialogue
    if now_m - awake_since >= WAKE_MAX:
        return "tired"
    if sub is None and now_m - last_fruitful >= SLEEP_AFTER:
        return "wondering"
    return None


# THE WONDERING-STATE DECAY (the author's ruling 2026-07-21): the published state describes the
# SESSION, not the instant. The wonder units are quick — a minting night is mostly empty ticks —
# so the instantaneous verdict spent flood nights saying «idle» while theorems arrived every few
# minutes. The `idle` verdict now decays: quiet since the last wonder unit (`wonder` and
# `wonder-idle` both refresh — checking the notebooks IS wondering) shorter than SLEEP_AFTER still
# reads "wondering". DELIBERATELY the same constant, no new knob: the sleep design already ends a
# fruitless wondering session at exactly SLEEP_AFTER, so the display session hands off to
# "sleeping" with no idle intrusion. Real events always preempt the smoothing (think → "thinking"
# instantly); daytime idle stays honest (no recent wonder unit → "idle"). Pure — table-testable.
def _published_state(sub: Optional[str], asleep_at: Optional[float], now_m: float,
                     last_wonder_at: float) -> str:
    if sub == "think":
        return "thinking"
    if sub in ("wonder", "wonder-idle"):
        return "wondering"
    if asleep_at is not None:
        return "sleeping"
    if now_m - last_wonder_at <= SLEEP_AFTER:
        return "wondering"  # the session is still warm — between thoughts, not idle
    return "idle"


# --------------------------------------------------------------
# THE LIVED-AWAKE LEDGER (shape c, the author's ruling 2026-07-21) — `wake_at` is the BIRTH stamp
# («alive since», never reset); this ledger measures time actually spent AWAKE. Neither sleep-phase
# time nor process-dead time is awake time — the author powers the brain on and off around the work
# sessions, and the old now-minus-wake_at "uptime" counted every one of those dead hours. Fold on
# falling asleep, (re)open on waking and on boot. Pure state mutations (no save — the caller owns
# the write) so the tests can drive them directly; a live reading = awake_s + (now - awake_mark).
# --------------------------------------------------------------
def _fold_awake(bs: TKBrainStateDoc, now_w: float) -> None:
    if bs.awake_mark is not None:
        bs.awake_s += max(0.0, now_w - bs.awake_mark)
        bs.awake_mark = None


def _mark_awake(bs: TKBrainStateDoc, now_w: float) -> None:
    if bs.awake_mark is None:
        bs.awake_mark = now_w


def _boot_awake_ledger(bs: TKBrainStateDoc, now_w: float) -> None:
    # a mark left open by a process death: credit only the WITNESSED tail — the last recorded
    # think/wonder moment. The stretch beyond it is unwitnessed and never credited (conservative:
    # an idle hour before a crash undercounts; the ledger never overcounts).
    if bs.awake_mark is not None:
        witnessed = float(max(bs.last_thinking_at or 0, bs.last_wondering_at or 0))
        bs.awake_s += max(0.0, min(witnessed, now_w) - bs.awake_mark)
        bs.awake_mark = None
    _mark_awake(bs, now_w)


# wake: clear the sleep state, tell the stashed dream + ask the morning questions.
# Returns None (the new asleep_at).
def _wake(bs: TKBrainStateDoc, asleep_at: Optional[float], reason: str) -> Optional[float]:
    if asleep_at is None:
        return None
    slept = time.monotonic() - asleep_at
    logger.info("[sleep] ☀️ he wakes (%s) after %.0fs asleep", reason, slept)
    bs.asleep_since = None
    _mark_awake(bs, time.time())  # the lived-awake stretch reopens with him
    bs.save()
    _spawn_pending_dream(bs)
    _spawn_morning_questions(bs)
    return None


# --------------------------------------------------------------
# The coordinator — dynamic priority routing. Each tick: drain Actions fully before Priorities;
# Priorities before Thinking; Thinking only when both are empty. The cooperative yield between busy
# units + the longer idle sleep is the throttle. Event-driven interruption falls out for free: a new
# idea/action created between ticks is picked up on the next iteration.
# --------------------------------------------------------------
async def coordinator(stop_event: asyncio.Event) -> None:
    logger.info("🧠 Coordinator started")
    bs = get_or_create_brain_state()
    # A REBOOT IS A WAKE (sleep phase): an interrupted night never resumes — but its dream
    # survived in bs.pending_dream and is told on this wake (content-idempotent).
    if bs.asleep_since is not None:
        bs.asleep_since = None
        logger.info("[sleep] ☀️ woken by the reboot — the night ended with the process")
    # the lived-awake ledger: fold any stretch orphaned by the last process death, open this one.
    _boot_awake_ledger(bs, time.time())
    bs.save()
    # the digest buffer: an interrupted night's leftover batches ship on this wake (the boot flush,
    # the digest machinery 2026-07-21) — the goodnight summary a crash never got to send.
    thinking.flush_digests(bs)
    _spawn_pending_dream(bs)
    tick = 0  # monotone loop counter (one increment per iteration) — used by the per-tick guard log
    # the idle-confirmation clock: last moment REACTIVE work (actions/priorities/think) happened.
    # starts at "now" so a fresh wake never opens with a daydream (he looks around first).
    last_busy = time.monotonic()
    # the sleep clock: last moment ANY pass produced a unit of work (reactive OR a fruitful
    # wonder). Quiet past SLEEP_AFTER while wondering is allowed = he falls asleep wondering.
    last_fruitful = time.monotonic()
    # the tiredness clock (WAKE_MAX): when this wakefulness began — boot counts as a wake.
    # Reset ONLY on an actual sleep→wake transition (see wake below); nothing defers-by-reset.
    awake_since = time.monotonic()
    asleep_at: Optional[float] = None  # monotonic mirror of bs.asleep_since (the loop's clock)
    # the display decay clock (_published_state): last wonder unit of any flavor. Starts cold —
    # a fresh boot with no wondering yet reads honestly "idle"/"thinking", never a stale session.
    last_wonder_at = float("-inf")

    # the loop's wake wrapper: _wake + restart the tiredness clock iff he was actually asleep
    # (a reactive tick while already awake is the identity — his wakefulness just continues).
    def wake(reason: str) -> None:
        nonlocal asleep_at, awake_since
        was_asleep = asleep_at is not None
        asleep_at = _wake(bs, asleep_at, reason)
        if was_asleep:
            awake_since = time.monotonic()

    try:
        while not stop_event.is_set():
            tick += 1
            # PER-TICK GUARD: an unhandled phase exception must never kill the coordinator silently —
            # the process would stay alive with a dead loop (indistinguishable from a hang). Log the
            # full traceback, back off one idle interval, keep living.
            try:
                if actions_phase(bs):
                    # Actions/Priorities work reports as "thinking" (blog P3 state mapping): deciding
                    # and acting on urges is still thought — "ingesting"/"refuting" would claim
                    # introspection the coordinator doesn't cheaply have.
                    wake("the world moved")
                    last_busy = last_fruitful = time.monotonic()
                    heartbeat.set_state("thinking")
                    await asyncio.sleep(BUSY_YIELD)
                    continue
                if priorities_phase():
                    wake("the world moved")
                    last_busy = last_fruitful = time.monotonic()
                    heartbeat.set_state("thinking")
                    await asyncio.sleep(BUSY_YIELD)
                    continue
                # Thinking ran: if it actually processed memory (and may have spawned ideas), yield
                # briefly so the next tick promptly routes to Priorities; only true idle gets the long
                # sleep (CPU throttle / good citizen). Wondering is additionally gated on CONFIRMED
                # idle: only after WONDER_IDLE_CONFIRM seconds without reactive work (author's ruling
                # 2026-07-16 — he starts wondering when he's reasonably sure nothing else needs him)
                # — and STOPS while asleep (the sleep phase: re-saturating every tick is not rest;
                # the reactive probe keeps running as the wake sensor).
                wonder_allowed = (asleep_at is None
                                  and time.monotonic() - last_busy >= WONDER_IDLE_CONFIRM)
                sub = thinking_phase(bs, wonder_allowed)
                if sub == "think":
                    wake("someone spoke")
                    last_busy = time.monotonic()
                if sub in ("think", "wonder"):
                    # only FRUITFUL work resets the sleep clock — an idle re-check ("wonder-idle",
                    # the drift driver finding nothing new) lets the drowsiness accumulate.
                    last_fruitful = time.monotonic()
                if sub in ("wonder", "wonder-idle"):
                    last_wonder_at = time.monotonic()  # the display decay clock (both flavors)
                # the SLEEP transitions: tiredness (WAKE_MAX, fruitful or not) or fruitless
                # wondering past SLEEP_AFTER — _sleep_reason decides; SLEEP_MAX ends the night
                # regardless, with a fresh wakeful window before any next nap.
                now_m = time.monotonic()
                reason = _sleep_reason(asleep_at, sub, now_m,
                                       awake_since, last_busy, last_fruitful)
                if reason is not None:
                    asleep_at = now_m
                    bs.asleep_since = int(time.time())
                    _fold_awake(bs, time.time())  # the lived-awake stretch closes with his eyes
                    # the digest buffer's goodnight summary (the digest machinery 2026-07-21): the
                    # night's repeated-reasoning batches ship as one cumulative post per shape at the
                    # falling-asleep edge — beside the goodnight, before the untangling dream.
                    thinking.flush_digests(bs)
                    bs.save()
                    if reason == "tired":
                        logger.info("[sleep] 🌙 tiredness takes him (awake for %.0fs) — "
                                    "fruitful or not, the body claims its sleep",
                                    now_m - awake_since)
                    else:
                        logger.info("[sleep] 🌙 he falls asleep wondering (quiet for %.0fs)",
                                    now_m - last_fruitful)
                    _say_goodnight(bs)  # the farewell edge (recency-gated; never queue work)
                    _sleep_duty(bs)  # the night's untangling — retreats now, the dream on waking
                elif asleep_at is not None and now_m - asleep_at >= SLEEP_MAX:
                    wake("rested")
                    last_fruitful = time.monotonic()
                # the honest state for the heartbeat thread — session-granular via the wondering
                # decay (_published_state): think -> "thinking", wondering (or a still-warm
                # wondering session) -> "wondering", asleep -> "sleeping", else "idle".
                heartbeat.set_state(_published_state(sub, asleep_at, now_m, last_wonder_at))
                await asyncio.sleep(BUSY_YIELD if sub
                                    else SLEEP_TICK if asleep_at is not None else IDLE_INTERVAL)
            except Exception:
                logger.exception("[coordinator] tick %d failed — backing off one idle interval", tick)
                await asyncio.sleep(IDLE_INTERVAL)
    except asyncio.CancelledError:
        logger.info("🧠 Coordinator interrupted...")
        raise


# the tokeniko stakeholder uid, resolved once in main() and used as every action's sourceId.
_tokeniko_uid: str = ""


# main / init
async def main():
    global _tokeniko_uid
    logger.info("🚀 Init tokeniko: brain")

    # 1. Init — brain only needs MongoDB (+ Ollama client); no spaCy/Stanza pipeline.
    db, db_memory, ai_client = init_io()

    # resolve tokeniko's identity once; every action it emits is sourced from it.
    tokeniko = get_tokeniko()
    _tokeniko_uid = tokeniko.uid
    logger.info("🧠 tokeniko identity: uid=%s", _tokeniko_uid)

    # 2. Graceful Shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def shutdown_handler():
        logger.warning("⚠️ SIGTERM. Time to go to deep sleep...")
        stop_event.set()

    # Listen for termination signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    # 3. The parallel heartbeat (2026-07-19): its own daemon thread, started after init_io so
    # Bunnet is wired for the first beat's counts. A blocked coordinator tick (a long wondering
    # pass) can no longer hole the monitor feed — the heart beats through the thought.
    heartbeat_stop = threading.Event()
    heartbeat.start(heartbeat_stop, _tokeniko_uid)

    # 4. Run the single coordinator (replaces the three independent loops).
    coordinator_task = asyncio.create_task(coordinator(stop_event))
    try:
        # Waiting for sigterms
        await stop_event.wait()

        # Gently shutdown
        logger.info("Shutting down coordinator...")
        coordinator_task.cancel()
        try:
            await coordinator_task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        heartbeat_stop.set()  # cut the beat thread's wait short (daemon — never blocks exit)
        logger.info("🛑 tokeniko is deep sleeping. See ya'll")


if __name__ == "__main__":
    # main start
    asyncio.run(main())

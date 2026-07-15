import asyncio
import logging
import signal
import sys
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
def actions_phase() -> bool:
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
def thinking_phase(brain_state: TKBrainStateDoc) -> Optional[str]:
    sub = ("think" if thinking.think_one(brain_state)
           else "wonder" if thinking.wonder_one(brain_state)
           else None)
    brain_state.last_thinking_at = int(time.time())
    brain_state.save()
    return sub


# --------------------------------------------------------------
# The coordinator — dynamic priority routing. Each tick: drain Actions fully before Priorities;
# Priorities before Thinking; Thinking only when both are empty. The cooperative yield between busy
# units + the longer idle sleep is the throttle. Event-driven interruption falls out for free: a new
# idea/action created between ticks is picked up on the next iteration.
# --------------------------------------------------------------
async def coordinator(stop_event: asyncio.Event) -> None:
    logger.info("🧠 Coordinator started")
    bs = get_or_create_brain_state()
    tick = 0  # heartbeat cadence counter (blog P3) — monotone, one increment per loop iteration
    try:
        while not stop_event.is_set():
            tick += 1
            if actions_phase():
                # Actions/Priorities work reports as "thinking" (blog P3 state mapping): deciding
                # and acting on urges is still thought — "ingesting"/"refuting" would claim
                # introspection the coordinator doesn't cheaply have.
                heartbeat.maybe_beat(tick, "thinking", _tokeniko_uid)
                await asyncio.sleep(BUSY_YIELD)
                continue
            if priorities_phase():
                heartbeat.maybe_beat(tick, "thinking", _tokeniko_uid)
                await asyncio.sleep(BUSY_YIELD)
                continue
            # Thinking ran: if it actually processed memory (and may have spawned ideas), yield
            # briefly so the next tick promptly routes to Priorities; only true idle gets the long
            # sleep (CPU throttle / good citizen).
            sub = thinking_phase(bs)
            # the honest state for the heartbeat: reactive think -> "thinking", idle-time
            # re-examination -> "wondering", no work at all -> "idle".
            state = "thinking" if sub == "think" else "wondering" if sub == "wonder" else "idle"
            heartbeat.maybe_beat(tick, state, _tokeniko_uid)
            await asyncio.sleep(BUSY_YIELD if sub else IDLE_INTERVAL)
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

    # 3. Run the single coordinator (replaces the three independent loops).
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
        logger.info("🛑 tokeniko is deep sleeping. See ya'll")


if __name__ == "__main__":
    # main start
    asyncio.run(main())

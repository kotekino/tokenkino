import asyncio
import logging
import signal
import sys
import time

from dotenv import load_dotenv

from lib.core.io import init_io, get_tokeniko
from lib.core.models import TKIdeaDoc, TKActionDoc, TKBrainStateDoc
from lib.core.memory import (
    IdeaStatus,
    ActionStatus,
    MEMChannels,
    UrgeLevel,
)
from brain import behavior
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

    # STUB (D): execute the INTERNAL action (guess/learn -> low-trust KB writes via the D3a API seam).
    # Outward I/O is senses' job; this branch only ever sees INTERNAL actions now.
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

    # STUB (D): score feasibility. The real scorer (resources / allowlist / reachable channel /
    # derivable proof) lands with the reasoning engine. Placeholder = always feasible.
    feasibility = 1.0

    # decision: keep iff urge clears the threshold AND it is feasible; else discard.
    keep = idea.urge >= URGE_THRESHOLD and feasibility > 0

    if keep:
        # C (IMPLEMENTED): idea -> action mapping via the reserved-token behavior layer (the
        # meta-language: [eval:X] -> [tokeniko:Y], KB-driven personality — see brain/behavior.py).
        # The idea already carries its baked-in tokeniko:Y reflex (action_token); dispatch maps it to
        # a concrete Action (or None for tokeniko:ignore / no reflex). The feasibility SCORING +
        # collapse-arbitration over multiple kept candidates remain D / parked.
        action = behavior.dispatch_action(idea, _tokeniko_uid)

        idea.feasibility = feasibility
        idea.parsed_by_prio = True
        idea.status = IdeaStatus.DONE
        if action is None:
            logger.info(
                "[priorities] kept idea trigger=%s action_token=%s -> ignore/no-op",
                idea.trigger,
                idea.action_token,
            )
        else:
            logger.info(
                "[priorities] kept idea trigger=%s action_token=%s -> action %s (%s)",
                idea.trigger,
                idea.action_token,
                str(action.id),
                action.action_type.value,
            )
    else:
        idea.feasibility = feasibility
        idea.parsed_by_prio = True
        idea.status = IdeaStatus.DISCARDED
        logger.info(
            "[priorities] discarded idea trigger=%s urge=%s (below threshold %s)",
            idea.trigger,
            idea.urge,
            URGE_THRESHOLD,
        )

    idea.save()
    return True


# --------------------------------------------------------------
# Thinking phase (The Generator) — the lowest-priority background filler ("thinks always, acts
# maybe"). Runs only when both queues are empty. Two sub-passes, REACTIVE first:
#   think_one  (D1a/D1b) — evaluate ONE FRESH `memory` TKZip vs the KB, fan eval:* into ideas + learn
#                          forward-chained theorems (closing perceive -> evaluate -> ideas -> actions).
#   wonder_one (D1c)     — only when there is nothing fresh: RE-EXAMINE a past item because the KB has
#                          grown (associative + drift), silently materializing any newly-derivable
#                          theorem. The reactive pass wins; wondering fills the idle.
# Returns True iff EITHER sub-pass did a unit of work this tick (so the coordinator yields briefly
# rather than taking the long idle sleep).
# --------------------------------------------------------------
def thinking_phase(brain_state: TKBrainStateDoc) -> bool:
    did = thinking.think_one(brain_state) or thinking.wonder_one(brain_state)
    brain_state.last_thinking_at = int(time.time())
    brain_state.save()
    return did


# --------------------------------------------------------------
# The coordinator — dynamic priority routing. Each tick: drain Actions fully before Priorities;
# Priorities before Thinking; Thinking only when both are empty. The cooperative yield between busy
# units + the longer idle sleep is the throttle. Event-driven interruption falls out for free: a new
# idea/action created between ticks is picked up on the next iteration.
# --------------------------------------------------------------
async def coordinator(stop_event: asyncio.Event) -> None:
    logger.info("🧠 Coordinator started")
    bs = get_or_create_brain_state()
    try:
        while not stop_event.is_set():
            if actions_phase():
                await asyncio.sleep(BUSY_YIELD)
                continue
            if priorities_phase():
                await asyncio.sleep(BUSY_YIELD)
                continue
            # Thinking ran: if it actually processed memory (and may have spawned ideas), yield
            # briefly so the next tick promptly routes to Priorities; only true idle gets the long
            # sleep (CPU throttle / good citizen).
            did = thinking_phase(bs)
            await asyncio.sleep(BUSY_YIELD if did else IDLE_INTERVAL)
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

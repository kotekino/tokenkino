# --------------------------------------------------------------
# brain/behavior.py — the meta-language engine (step C). The reserved-token behavior layer:
# [eval:X] -> [tokeniko:Y] @ urge. The SYNTAX is hardwired (the EvalToken / TokenikoAction enums +
# the _DISPATCH registry below); the POLICY is MEMORY (the `behavior_rules` table = tokeniko's
# personality). See brain/README.md "## The meta-language (behavior rules)".
#
# Three primitives:
#   - behavior_for(trigger)      -> the candidate rule set (the superposition) for a trigger.
#   - spawn_ideas_for(trigger)   -> fan the candidates out into ideas (one per rule; Thinking/D calls).
#   - dispatch_action(idea, uid) -> map an idea's baked-in tokeniko:Y reflex to a concrete Action.
# --------------------------------------------------------------
import json
import os
import time
from typing import Optional

from bson import ObjectId

from lib.core.models import (
    TKBehaviorRuleDoc,
    TKIdeaDoc,
    TKActionDoc,
    TKMemoryItemDoc,
    TKMemoryStakeholdersDoc,
)
from lib.core.memory import EvalToken, TokenikoAction, ActionType, MEMChannels
from brain import compose

# the channels tokeniko can currently ACT on (deliver an outward action). HARDWIRED for v1 (a small
# set isn't worth a table yet) — externalize to a channel-capability KB record later (everything-is-KB):
# INTERNAL = self KB-writes; DISCORD has a senses carrier; ATPROTO has NO send adapter yet -> infeasible.
# PUBLIC (blog P1): the carrier lands in P3 — planned posts queue as PENDING actions on this channel
# (the handoff): nothing consumes them yet (actions_phase drains INTERNAL only; senses polls discord).
_ACTABLE_CHANNELS = {MEMChannels.INTERNAL, MEMChannels.DISCORD, MEMChannels.PUBLIC}


# the HARDWIRED dispatch registry: tokeniko:Y reflex -> concrete ActionType. Code today, but a plain
# dict REGISTRY so it can be externalized to DATA later (the "actions-as-data" future, parked).
# guess/learn are INTERNAL KB-writes (targetId = tokeniko, no senses I/O); speakup/ask/why are outward
# messages (senses carries them out); post publishes; ignore -> no action (absent from the registry).
_DISPATCH = {
    TokenikoAction.SPEAKUP.value: ActionType.SEND_MESSAGE,
    TokenikoAction.ASK.value:     ActionType.SEND_MESSAGE,
    TokenikoAction.WHY.value:     ActionType.SEND_MESSAGE,
    TokenikoAction.POST.value:    ActionType.POST_CONTENT,
    TokenikoAction.GUESS.value:   ActionType.SEND_MESSAGE,   # internal (targetId=self) — see below
    TokenikoAction.LEARN.value:   ActionType.SEND_MESSAGE,   # internal (targetId=self)
    # clarify: outward, recipient = the conflicting speaker (resolved in dispatch_action from the
    # source memory item's sourceId, since clarify is not _INTERNAL and carries no idea.target).
    TokenikoAction.CLARIFY.value: ActionType.SEND_MESSAGE,
    # answer: outward + DIRECTED — the recipient is the asker (idea.target), set on the action below.
    TokenikoAction.ANSWER.value:  ActionType.SEND_MESSAGE,
    # trust (D P2): INTERNAL ledger updates — the brain executes them itself (actions_phase);
    # target = the SPEAKER whose ledger moves (idea.target), never a message on the wire.
    TokenikoAction.MORE_TRUST.value: ActionType.UPDATE_TRUST,
    TokenikoAction.LESS_TRUST.value: ActionType.UPDATE_TRUST,
    # belief-revision v1 (retreat arc #4): retreat = INTERNAL KB revision (brain-executed:
    # archive + cascade + weaken); concede = the directed acknowledgment to the corrector
    # (idea.target), spawned by the retreat HANDLER so it can state what was actually retracted.
    TokenikoAction.RETREAT.value: ActionType.REVISE_BELIEF,
    TokenikoAction.CONCEDE.value: ActionType.SEND_MESSAGE,
    # the anecdote (compose 2.0 slice 5): an on-topic KB notion offered as a side-note into the
    # channel — outward, threads under the message that stirred the association.
    TokenikoAction.MENTION.value: ActionType.SEND_MESSAGE,
    # the reductio (roadmap §0): outward + DIRECTED at the chosen premise-giver (idea.target).
    # No source memory item exists (the trigger is a derivation, not a perception) — the channel
    # is read off the target stakeholder (see plan_action), and the carrier's destination
    # fallback DMs via the contextKey (provenance-safe: a DM never leaks a premise to a room).
    TokenikoAction.REDUCT.value: ActionType.SEND_MESSAGE,
    # the agreement voice (survey 2026-07-19): outward, recipient = the corroborated speaker
    # (source-memory sourceId, the clarify pattern). Rare by THROTTLE, not by urge — see
    # plan_action's cooldown gate (the rule outranks ignore's urge, so it would otherwise fire
    # on every corroboration; the author's over-engagement guard, cap-feedback 2026-07-05).
    TokenikoAction.AGREE.value: ActionType.SEND_MESSAGE,
    # the goodnight (survey slice 2): outward into the recently-alive room — the source memory
    # is the room's LAST inbound item (recency-gated at the transition site, brain/main.py), so
    # channel + destination resolve through the normal seams; reply_to is dropped below (a
    # goodnight is to the room, never a thread under someone's old message).
    TokenikoAction.GOODNIGHT.value: ActionType.SEND_MESSAGE,
    # the etiquette family (survey slice 4): the reactive social reflexes — outward, recipient =
    # the greeter/thanker/leaver (idea.target), threaded under their message via the source
    # memory's coords. Throttled per speaker below (SOCIAL_COOLDOWN_S — no hello-loops).
    TokenikoAction.GREET.value: ActionType.SEND_MESSAGE,
    TokenikoAction.WELCOME.value: ActionType.SEND_MESSAGE,
    TokenikoAction.FAREWELL_BACK.value: ActionType.SEND_MESSAGE,
    # IGNORE -> no action
}

# the internal-reflex set: these reflexes are KB-writes addressed to tokeniko itself (the actual KB
# write is step D), so their action targetId is tokeniko's own uid (an internal reflection loop).
_INTERNAL = {TokenikoAction.GUESS.value, TokenikoAction.LEARN.value, TokenikoAction.RETREAT.value}

# the trust-reflex set: INTERNAL channel (brain-executed, never a senses carrier) but SPEAKER-targeted
# (the ledger that moves is the speaker's, not tokeniko's).
_TRUST = {TokenikoAction.MORE_TRUST.value, TokenikoAction.LESS_TRUST.value}

# the AGREE cooldown (seconds, per channel): the agreement voice's RARITY dial. Urge cannot make
# agree rare (the collapse is a max — an agree rule above ignore always wins), so rarity lives
# here: one nod per window, then silence-is-consent resumes. Stochastic collapse (parked) may
# replace this someday.
_AGREE_COOLDOWN_S = int(os.getenv("AGREE_COOLDOWN_S", "1800"))

# the ASK cooldown (seconds, per TEACHER — survey slice 3): a teaching burst that mints five
# theorems earns ONE curiosity question, not five (the over-engagement guard again; keyed by
# target where agree keys by channel — curiosity is about the person, not the room).
_ASK_COOLDOWN_S = int(os.getenv("ASK_COOLDOWN_S", "600"))

# the SOCIAL cooldown (seconds, per SPEAKER — survey slice 4): one greeting/welcome/farewell per
# person per window — etiquette without hello-loops (a bot greeting on a timer must not be
# answered forever). The etiquette triggers are directedness-FLOORED (the author's guard ruling:
# etiquette wins over over-engagement in public), so the throttle is the only rarity dial.
_SOCIAL_COOLDOWN_S = int(os.getenv("SOCIAL_COOLDOWN_S", "3600"))
_SOCIAL_TOKENS = {TokenikoAction.GREET.value, TokenikoAction.WELCOME.value,
                  TokenikoAction.FAREWELL_BACK.value}


# the candidate set / superposition: every ENABLED rule for a trigger, most-urgent first (order as
# the tiebreak). Multiple rules may match one trigger — Priorities arbitrates.
def behavior_for(trigger: str) -> list[TKBehaviorRuleDoc]:
    rules = (
        TKBehaviorRuleDoc.find({"trigger": trigger, "enabled": True}).to_list()
    )
    return sorted(rules, key=lambda r: (-r.urge, r.order))


# the fan-out: for each candidate rule, create+insert an idea carrying that rule's reflex (action_token)
# and urge. The superposition made concrete — Thinking/D will call this. Returns the created ideas.
# `material` (life:*) rides the life-event context to the post composer (mirrors `answer`/`target`);
# `urge_scale` is the SIGNIFICANCE modulation (blog P1): idea.urge = rule.urge x significance, so how
# noteworthy the event is shapes the urge AT SPAWN and the act threshold does the rest in Priorities.
def spawn_ideas_for(trigger: str, payload=None, source: Optional[str] = None,
                    answer: Optional[dict] = None, target: Optional[str] = None,
                    material: Optional[dict] = None, urge_scale: float = 1.0,
                    confidence: Optional[float] = None) -> list[TKIdeaDoc]:
    ideas: list[TKIdeaDoc] = []
    for rule in behavior_for(trigger):
        # IDEMPOTENCY (the obsessive-thinking guard): never two ideas for the same
        # (source, trigger, action_token). The same memory item re-reached (a re-eval tick, or later
        # wondering) must NOT re-emit the SAME conclusion+reflex — that is obsessive looping. A DIFFERENT
        # outcome (a new trigger because the KB grew = growing wiser) is a different key, so it is allowed.
        # (No source → can't key it → no dedup; that path is for tests / source-less spawns.)
        if source is not None and TKIdeaDoc.find_one(
            {"source": source, "trigger": trigger, "action_token": rule.action}
        ).run() is not None:
            continue
        idea = TKIdeaDoc(
            trigger=trigger,
            action_token=rule.action,
            urge=rule.urge * urge_scale,
            payload=payload,
            source=source,
            answer=answer,
            material=material,
            target=target,
            confidence=confidence,  # slice 2: the content's epistemic confidence (decision-site computed)
        )
        idea.insert()
        ideas.append(idea)
    return ideas


# EFFECTIVE URGE (senses C) — the ONE place addressing acts: the rule's urge scaled by how much the
# source perception was FOR tokeniko (MEMItem.directedness — DM 1.0 · addressed 0.9 · ambient 0.6 ·
# someone else's thread 0.15). Perception and reasoning always run at full strength; only the urge to
# ACT is scaled, so discretion-to-silence emerges from the multiplication against the keep threshold
# (e.g. answer 0.9 x ambient 0.6 = 0.54 speaks; why 0.6 x 0.6 = 0.36 stays quiet). No source, or a
# source without the field (internal/self items), means fully directed — behave exactly as before.
#
# SELF-RELEVANT floor (retreat arc #3): a conflict with tokeniko's own worldview is inherently
# addressed to HIM — the perception's directedness says nothing about how much the conflict matters
# to him. Floored at ADDRESSED (0.9) when the perception was at least ambient; BELOW ambient (someone
# else's thread) the scale stands — he stays the polite eavesdropper (the INTERNAL trust ledger is
# already unscaled, so an overheard conflict still moves it). The correction family (#4) is
# self-relevant for the same reason: a revision of his own beliefs — and its acknowledgment — is
# about HIM, whoever the correction was nominally addressed to.
_SELF_RELEVANT_TRIGGERS = {
    EvalToken.CONFLICT.value,
    EvalToken.CORRECTION.value,
    EvalToken.CORRECTION_DONE.value,
    # the anecdote (slice 5): the association's push comes from WITHIN — his own thought itching
    # to be shared, not the speaker's address. Without the floor, ambient talk (0.6) could never
    # clear the act threshold and case 3 would be stillborn; below ambient the scale stands (the
    # polite eavesdropper does not interject into someone else's thread).
    EvalToken.ASSOCIATION.value,
    # the reductio (§0): the absurd lives in HIS OWN derivations — self-relevant par excellence.
    # (In practice its ideas carry no source memory item, so the urge rides unscaled anyway;
    # listed for the honesty of the set.)
    EvalToken.ABSURDITY.value,
    # the etiquette family (survey slice 4 — the author's guard ruling MECHANIZED): etiquette
    # WINS over over-engagement in public — a room-wide «hello everyone» (ambient 0.6) must
    # clear the act threshold, so the social triggers floor to addressed. Discretion lives in
    # the at-other suppression (thinking) + the per-speaker throttle instead.
    EvalToken.GREETING.value,
    EvalToken.THANKS.value,
    EvalToken.FAREWELL.value,
}
_ADDRESSED_FLOOR = 0.9   # senses/inbound.grade_directedness: addressed
_AMBIENT_GRADE = 0.6     # senses/inbound.grade_directedness: ambient


def effective_urge(idea: TKIdeaDoc, src: Optional[TKMemoryItemDoc]) -> float:
    directedness = getattr(src, "directedness", None) if src is not None else None
    if directedness is None:
        return idea.urge
    if getattr(idea, "trigger", None) in _SELF_RELEVANT_TRIGGERS and directedness >= _AMBIENT_GRADE:
        directedness = max(directedness, _ADDRESSED_FLOOR)
    return idea.urge * directedness


# the memory item that spawned the idea (idea.source), or None. The reply path reads its CHANNEL (where
# to answer — a Discord question is answered on Discord) and its sourceId (who to answer = the speaker).
def _source_memory(idea: TKIdeaDoc) -> Optional[TKMemoryItemDoc]:
    if not idea.source:
        return None
    try:
        return TKMemoryItemDoc.get(ObjectId(idea.source)).run()  # Bunnet: .run() executes the query
    except Exception:
        return None


# PLAN the concrete action an idea's reflex would yield — WITHOUT persisting it — so Priorities can
# score its feasibility BEFORE committing (D2). tokeniko:ignore (or a missing/unknown action_token) ->
# None (no reflex). The plan carries the OUTBOUND addressing the carrier (`senses`) needs, the brain
# NAMING channel + target (it never touches the socket):
#   - CHANNEL: the source memory's channel (a Discord question -> a Discord reply); INTERNAL for a
#     KB-write reflex (guess/learn) and as the fallback when there is no source. `actions_phase`
#     executes INTERNAL itself; `senses` polls its own channel (discord/atproto).
#   - TARGET: self for an internal KB-write; idea.target (the asker) for a DIRECTED reply (answer);
#     else the speaker (the source memory's sourceId) for an outward reflex (speakup/clarify/ask/why).
#   - payload["raw"]: the terse decision text (compose) -> senses decompiles it to fluent English.
def plan_action(idea: TKIdeaDoc, tokeniko_uid: str) -> Optional[dict]:
    token = idea.action_token
    if token == TokenikoAction.IGNORE.value or token not in _DISPATCH:
        return None

    src = _source_memory(idea)

    # channel: PUBLIC for a post (blog P1 — NEVER the source channel: a post is broadcast
    # self-expression on tokeniko's own window, not a reply into the stirring conversation);
    # INTERNAL for a KB-write or trust reflex; else the source memory's channel (carrier = senses).
    if token == TokenikoAction.POST.value:
        channel = MEMChannels.PUBLIC
    elif token in _INTERNAL or token in _TRUST:
        channel = MEMChannels.INTERNAL
    else:
        channel = MEMChannels.INTERNAL
        if src is not None and src.channel:
            try:
                channel = MEMChannels(src.channel)
            except ValueError:
                channel = MEMChannels.INTERNAL
        elif token == TokenikoAction.REDUCT.value and idea.target:
            # the reductio (§0): no source memory item (the trigger is a derivation) — the
            # channel is where the chosen premise-giver LIVES (their stakeholder doc).
            sh = TKMemoryStakeholdersDoc.find_one({"uid": idea.target}).run()  # Bunnet: .run()
            if sh is not None and sh.channel:
                channel = sh.channel

    # the AGREE throttle (survey 2026-07-19): one nod per channel per cooldown window — the
    # over-engagement guard (cap-feedback 2026-07-05). Within the window the plan dissolves and
    # silence-is-consent resumes, exactly as if ignore had won the collapse.
    if token == TokenikoAction.AGREE.value:
        last = (TKActionDoc.find({"payload.action_token": token, "channel": channel.value})
                .sort("-createdAt").limit(1).to_list())
        if last and (int(time.time()) - last[0].createdAt) < _AGREE_COOLDOWN_S:
            return None

    # target: None for a post (broadcast, not directed) / self (internal KB-write) / the asker
    # (directed answer) / the speaker whose ledger moves (trust) / the speaker (outward reply).
    if token == TokenikoAction.POST.value:
        target = None
    elif token in _INTERNAL:
        target = tokeniko_uid
    elif idea.target:
        target = idea.target
    elif src is not None:
        target = src.sourceId
    else:
        target = None

    # the ASK throttle (survey slice 3): one curiosity question per teacher per window — within
    # it the plan dissolves (the lesson is still learned; only the question is skipped).
    if token == TokenikoAction.ASK.value and target:
        last = (TKActionDoc.find({"payload.action_token": token, "targetId": target})
                .sort("-createdAt").limit(1).to_list())
        if last and (int(time.time()) - last[0].createdAt) < _ASK_COOLDOWN_S:
            return None

    # the SOCIAL throttle (survey slice 4): one nod of each etiquette kind per speaker per
    # window — the hello-loop guard (the reflex dissolves; the act stays remembered).
    if token in _SOCIAL_TOKENS and target:
        last = (TKActionDoc.find({"payload.action_token": token, "targetId": target})
                .sort("-createdAt").limit(1).to_list())
        if last and (int(time.time()) - last[0].createdAt) < _SOCIAL_COOLDOWN_S:
            return None

    payload = {"action_token": token, "trigger": idea.trigger}
    if token in _TRUST or token in (TokenikoAction.RETREAT.value, TokenikoAction.LEARN.value):
        payload["source"] = idea.source  # provenance: the memory item behind the episode/correction/lesson
    if idea.answer is not None:
        payload["answer"] = idea.answer  # the verdict/value (auditable; a native-zip channel reads it raw)
    if idea.material is not None:
        payload["material"] = idea.material  # life:* — the post composer's fuel (theorem / encounter context)
    # the INTENSITY tuple (compose 2.0 slice 2): confidence = the content's epistemic certainty
    # (decision-site computed on the idea; the answer dict's own confidence covers the question
    # path); arousal = the effective urge (urge × directedness — how much this matters to him
    # NOW). Gates the scaffold shelf + feeds the hedge; auditable on the stored Action.
    confidence = idea.confidence
    if confidence is None and idea.answer is not None:
        confidence = idea.answer.get("confidence")
    intensity = {"confidence": confidence, "arousal": effective_urge(idea, src)}
    payload["intensity"] = intensity
    raw = compose.compose_raw(token, idea.trigger, idea.answer, intensity=intensity)
    if raw:
        payload["raw"] = raw             # the decision text -> senses decompiles -> fluent English
        # (compose_raw returns "" for post — that's fine: raw is OPTIONAL here, the post composer
        # runs at the carrier over payload["material"] in P2/P3.)

    # the reply THREAD-BACK (senses go-live P2): the perceiving channel stamped its reply coordinates
    # on the source memory item (P1: metadata = {"channel_id","message_id"}); forward them as the
    # outbound Destination so a directed reply threads under the exact message that caused it.
    # Outward DIRECTED only — an internal KB-write / trust update / broadcast post has no destination.
    if (token not in _INTERNAL and token not in _TRUST and token != TokenikoAction.POST.value
            and src is not None and getattr(src, "metadata", None)):
        try:
            coords = json.loads(src.metadata)
        except (ValueError, TypeError):
            coords = None
        if isinstance(coords, dict) and coords.get("channel_id"):
            payload["destination"] = {"channel_id": str(coords["channel_id"]),
                                      "reply_to": coords.get("message_id")}
            if token == TokenikoAction.GOODNIGHT.value:
                # a goodnight addresses the ROOM — never threaded under the last speaker's
                # (possibly long-scrolled-past) message.
                payload["destination"].pop("reply_to", None)

    return {
        "action_token": token,
        "action_type": _DISPATCH[token],
        "channel": channel,
        "target": target,
        "payload": payload,
    }


# is the planned outward action's recipient ADDRESSABLE? explicit per-message coords always are; else
# the target stakeholder must resolve to a route on the channel (discord: a platform id in contextKey).
def _addressable(target: Optional[str], payload: dict, channel: MEMChannels) -> bool:
    if isinstance(payload.get("destination"), dict):
        return True
    if not target:
        return False
    sh = TKMemoryStakeholdersDoc.find_one({"uid": target}).run()  # Bunnet: .run() executes the query
    if sh is None:
        return False
    if channel == MEMChannels.DISCORD:
        return bool(sh.contextKey and ":" in sh.contextKey)  # "channel:talker_uid" carries the discord id
    return True


# FEASIBILITY (#4 D2) — *can the planned action actually be done* (the second axis, distinct from urge).
# v1 is lean + honest, binary {0.0, 1.0}: every check is a REAL capability gap, never a speculative score.
#   - internal KB-write reflex (guess/learn) -> always feasible (the write itself is a separate D-stub).
#   - outward: needs a carrier for its channel (atproto has none yet), something to say (a raw text),
#     and an addressable recipient. Any missing -> infeasible.
# (redundancy/no-op + permission-allowlist scoring deferred; fuzzy degrees are future.)
def score_feasibility(plan: dict) -> float:
    token = plan["action_token"]
    if token in _INTERNAL:
        return 1.0
    if token in _TRUST:
        # a ledger update needs no text and no wire — only a known speaker to record against.
        return 1.0 if plan["target"] else 0.0
    if token == TokenikoAction.POST.value:
        # a post needs its MATERIAL (the composer's fuel, blog P1) — it needs no recipient and no
        # raw text (the composer runs at the carrier, P2/P3). BEFORE the generic outward checks:
        # those gate on raw + an addressable recipient, which a broadcast post honestly lacks.
        return 1.0 if plan["payload"].get("material") else 0.0
    channel = plan["channel"]
    if channel not in _ACTABLE_CHANNELS:
        return 0.0  # no carrier for this channel (e.g. ATProto) -> honestly infeasible
    if not plan["payload"].get("raw"):
        return 0.0  # nothing to say
    if not _addressable(plan["target"], plan["payload"], channel):
        return 0.0  # unreachable recipient
    return 1.0


# map an idea's reflex to a concrete Action and PERSIST it. Pass a precomputed `plan` (from plan_action)
# to avoid re-resolving; otherwise it plans here. Returns None for a no-reflex idea (ignore/unknown).
def dispatch_action(idea: TKIdeaDoc, tokeniko_uid: str, plan: Optional[dict] = None) -> Optional[TKActionDoc]:
    if plan is None:
        plan = plan_action(idea, tokeniko_uid)
    if plan is None:
        return None
    action = TKActionDoc(
        action_type=plan["action_type"],
        sourceId=tokeniko_uid,
        targetId=plan["target"],
        channel=plan["channel"],
        payload=plan["payload"],
        ideaId=str(idea.id),
    )
    action.insert()
    return action

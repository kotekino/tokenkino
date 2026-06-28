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
from typing import Optional

from bson import ObjectId

from lib.core.models import TKBehaviorRuleDoc, TKIdeaDoc, TKActionDoc, TKMemoryItemDoc
from lib.core.memory import TokenikoAction, ActionType, MEMChannels
from brain import compose


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
    # IGNORE -> no action
}

# the internal-reflex set: these reflexes are KB-writes addressed to tokeniko itself (the actual KB
# write is step D), so their action targetId is tokeniko's own uid (an internal reflection loop).
_INTERNAL = {TokenikoAction.GUESS.value, TokenikoAction.LEARN.value}


# the candidate set / superposition: every ENABLED rule for a trigger, most-urgent first (order as
# the tiebreak). Multiple rules may match one trigger — Priorities arbitrates.
def behavior_for(trigger: str) -> list[TKBehaviorRuleDoc]:
    rules = (
        TKBehaviorRuleDoc.find({"trigger": trigger, "enabled": True}).to_list()
    )
    return sorted(rules, key=lambda r: (-r.urge, r.order))


# the fan-out: for each candidate rule, create+insert an idea carrying that rule's reflex (action_token)
# and urge. The superposition made concrete — Thinking/D will call this. Returns the created ideas.
def spawn_ideas_for(trigger: str, payload=None, source: Optional[str] = None,
                    answer: Optional[dict] = None, target: Optional[str] = None) -> list[TKIdeaDoc]:
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
            urge=rule.urge,
            payload=payload,
            source=source,
            answer=answer,
            target=target,
        )
        idea.insert()
        ideas.append(idea)
    return ideas


# the memory item that spawned the idea (idea.source), or None. The reply path reads its CHANNEL (where
# to answer — a Discord question is answered on Discord) and its sourceId (who to answer = the speaker).
def _source_memory(idea: TKIdeaDoc) -> Optional[TKMemoryItemDoc]:
    if not idea.source:
        return None
    try:
        return TKMemoryItemDoc.get(ObjectId(idea.source)).run()  # Bunnet: .run() executes the query
    except Exception:
        return None


# map an idea's baked-in tokeniko:Y reflex to a concrete Action. tokeniko:ignore (or a missing /
# unknown action_token) -> no action (None). The action carries the OUTBOUND addressing the carrier
# (`senses`) needs — resolved here, the brain NAMING channel + target (it never touches the socket):
#   - CHANNEL: the source memory's channel (a Discord question -> a Discord reply); INTERNAL for a
#     KB-write reflex (guess/learn) and as the fallback when there is no source. `actions_phase`
#     executes INTERNAL itself; `senses` polls its own channel (discord/atproto).
#   - TARGET: self for an internal KB-write; idea.target (the asker) for a DIRECTED reply (answer);
#     else the speaker (the source memory's sourceId) for an outward reflex (speakup/clarify/ask/why).
#   - payload["raw"]: the terse decision text (compose) -> senses decompiles it to fluent English.
def dispatch_action(idea: TKIdeaDoc, tokeniko_uid: str) -> Optional[TKActionDoc]:
    token = idea.action_token
    if token == TokenikoAction.IGNORE.value or token not in _DISPATCH:
        return None

    src = _source_memory(idea)

    # channel: INTERNAL for a KB-write reflex; else the source memory's channel (carrier = senses).
    if token in _INTERNAL:
        channel = MEMChannels.INTERNAL
    else:
        channel = MEMChannels.INTERNAL
        if src is not None and src.channel:
            try:
                channel = MEMChannels(src.channel)
            except ValueError:
                channel = MEMChannels.INTERNAL

    # target: self (internal KB-write) / the asker (directed answer) / the speaker (outward reply).
    if token in _INTERNAL:
        target = tokeniko_uid
    elif idea.target:
        target = idea.target
    elif src is not None:
        target = src.sourceId
    else:
        target = None

    payload = {"action_token": token, "trigger": idea.trigger}
    if idea.answer is not None:
        payload["answer"] = idea.answer  # the verdict/value (auditable; a native-zip channel reads it raw)
    raw = compose.compose_raw(token, idea.trigger, idea.answer)
    if raw:
        payload["raw"] = raw             # the decision text -> senses decompiles -> fluent English

    action = TKActionDoc(
        action_type=_DISPATCH[token],
        sourceId=tokeniko_uid,
        targetId=target,
        channel=channel,
        payload=payload,
        ideaId=str(idea.id),
    )
    action.insert()
    return action

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

from lib.core.models import TKBehaviorRuleDoc, TKIdeaDoc, TKActionDoc
from lib.core.memory import TokenikoAction, ActionType, MEMChannels


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
    # clarify: outward (NOT in _INTERNAL, so targetId=None for now). The actual recipient — the
    # conflicting speaker — is resolved later in D3 / `senses` (from the conflict's source memory item).
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


# map an idea's baked-in tokeniko:Y reflex to a concrete Action. tokeniko:ignore (or a missing /
# unknown action_token) -> no action (None). guess/learn -> internal (targetId = self = a KB-write
# intent; the write itself is D); a DIRECTED reflex (answer) -> targetId = idea.target (the asker);
# speakup/ask/why/clarify/post -> outward (targetId None; `senses` resolves + carries out).
def dispatch_action(idea: TKIdeaDoc, tokeniko_uid: str) -> Optional[TKActionDoc]:
    token = idea.action_token
    if token == TokenikoAction.IGNORE.value or token not in _DISPATCH:
        return None

    # targetId: self for an internal KB-write reflex; the asker for a directed reply; else None (senses).
    if token in _INTERNAL:
        target = tokeniko_uid
    elif idea.target:
        target = idea.target
    else:
        target = None

    payload = {"action_token": token, "trigger": idea.trigger}
    if idea.answer is not None:
        payload["answer"] = idea.answer  # the verdict/value for an answer reflex (senses renders it)

    action = TKActionDoc(
        action_type=_DISPATCH[token],
        sourceId=tokeniko_uid,
        targetId=target,
        channel=MEMChannels.INTERNAL,
        payload=payload,
        ideaId=str(idea.id),
    )
    action.insert()
    return action

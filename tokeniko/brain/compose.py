# --------------------------------------------------------------
# brain/compose.py — the OUTBOUND message ROUTER (compose 2.0; was #4 D3b). The brain DECIDES
# *what to say*; this is where that decision becomes a communicative-act CATEGORY + the bound
# data. The stochastic half (the scaffold shelf, the hedge, the fallback strings) lives in the
# SHARED voice reader — lib/core/voice.creative_compose — since slice 4, when the blog (a
# `senses` consumer) needed it too: routing is the brain's decision; HOW a category speaks is
# shared voice.
#
# The router is DETERMINISTIC and total: one category per distinct communicative decision (the
# concede if-chain became four total-template categories), so every template's slots are always
# satisfiable by construction. B1 (slice 4): a FALSE verdict may carry the refuting BELIEF's
# original in the answer dict — the speakup route binds it as {belief}, so the KB notion that
# grounded the disagreement can show itself in the reply («no, that is not true — I hold that a
# calculator never thinks»). The raw string rides in the Action payload; `senses` carries it
# through the rag2-out gate.
# --------------------------------------------------------------
import random
from typing import Optional

from lib.core.evaluation import AnswerKind, AnswerVerdict
from lib.core.memory import EvalToken, TokenikoAction
# re-exported for the existing consumers/tests: the shelf reader moved to lib at slice 4
from lib.core.voice import _FALLBACK, creative_compose, hedge_for  # noqa: F401


# ---- the ROUTER: decision -> (category, data) --------------------------------------------------------

# route the ANSWER decision (the AnswerResult dict). POLAR reuses the truth verdict (a
# logic-certain NO is named as such); WH surfaces the solved value; UNKNOWN is an honest non-answer.
def _route_answer(answer: dict) -> tuple[str, dict]:
    kind = answer.get("kind")
    verdict = answer.get("verdict")
    reason = (answer.get("reason") or "").lower()
    if verdict == AnswerVerdict.UNKNOWN.value:
        return "answer_idk", {}
    if kind == AnswerKind.POLAR.value:
        if verdict == AnswerVerdict.YES.value:
            return "answer_yes", {}
        if verdict == AnswerVerdict.NO.value:
            if "inconsist" in reason or "contradict" in reason:
                return "answer_no_contradictory", {}
            return "answer_no", {}
    if kind == AnswerKind.WH.value and verdict == AnswerVerdict.VALUE.value:
        value = answer.get("value")
        if value:
            return "answer_value", {"value": value}
    return "answer_idk", {}  # unrecognized shape -> honest fallback (never fabricate an answer)


# route the CONCEDE decision (belief-revision v1): the category is picked by what the retreat
# actually left behind — retracted belief(s), the surviving subaltern, both, or neither.
def _route_concede(answer: dict) -> tuple[str, dict]:
    retracted = answer.get("retracted") or []
    weakened = answer.get("weakened")
    if retracted and weakened:
        return "concede_retract_weakened", {"retracted": retracted[0], "weakened": weakened}
    if retracted:
        return "concede_retract", {"retracted": retracted[0]}
    if weakened:
        return "concede_weakened", {"weakened": weakened}
    return "concede_plain", {}


# the decision's category + data, or None for tokens with no reply text here (post / internal).
def _route(action_token: str, trigger: Optional[str], answer: Optional[dict]) -> Optional[tuple[str, dict]]:
    if action_token == TokenikoAction.ANSWER.value:
        return _route_answer(answer or {})
    if action_token == TokenikoAction.SPEAKUP.value:
        # speakup fires on a flawed assertion — name the flaw from the trigger.
        if trigger == EvalToken.INCONSISTENT.value:
            return "speakup_inconsistent", {}
        if trigger == EvalToken.FALSE.value:
            # B1: the refuting belief (resolved at the decision site from the refutation's
            # premises) rides the answer dict — belief-naming scaffolds become reachable.
            belief = (answer or {}).get("belief")
            return "speakup_false", ({"belief": belief} if belief else {})
        return "speakup_disagree", {}
    if action_token == TokenikoAction.CLARIFY.value:
        return "clarify_conflict", {}
    if action_token == TokenikoAction.ASK.value:
        return "ask_more", {}
    if action_token == TokenikoAction.WHY.value:
        return "why", {}
    if action_token == TokenikoAction.CONCEDE.value:
        return _route_concede(answer or {})
    return None  # post / internal reflexes have no Discord-reply text here


# compose the RAW decision text for an outward action — the seam plan_action calls. `answer` is
# the AnswerResult dict (tokeniko:answer / tokeniko:concede) or the belief carrier (speakup);
# `trigger` is the eval:* token that fired the reflex; `intensity` is the (confidence, arousal)
# tuple assembled by the plan (slice 2 — gates the shelf + feeds the hedge). Returns the composed
# string, or "" when there is nothing to say.
def compose_raw(action_token: str, trigger: Optional[str] = None, answer: Optional[dict] = None,
                rng: Optional[random.Random] = None, intensity: Optional[dict] = None) -> str:
    routed = _route(action_token, trigger, answer)
    if routed is None:
        return ""
    category, data = routed
    return creative_compose(category, data, rng=rng, intensity=intensity)

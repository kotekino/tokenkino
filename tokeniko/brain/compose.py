# --------------------------------------------------------------
# brain/compose.py — the OUTBOUND message composer (compose 2.0 slice 1, 2026-07-17; was #4 D3b).
# The brain DECIDES *what to say*; this is where that decision becomes a raw message string.
#
# TWO layers, split on the design's fault line (hunch 19, the QM-on-19 record):
#   - the ROUTER (compose_raw): DETERMINISTIC — maps the decision (action token + trigger +
#     answer) to a communicative-act CATEGORY and the data payload. One category per distinct
#     decision, so every template is total (the concede if-chain became four categories).
#   - the SHELF (creative_compose): STOCHASTIC — the enabled scaffolds of that category
#     (TKScaffoldDoc, memory not code: the behavior_rules move applied to the voice), picked
#     weighted-random (the fuzzy-personality superposition collapse), data bound into the slots
#     VERBATIM (the creativity fence: variation lives in scaffold choice — later + hedges +
#     polish — never in paraphrasing the data).
#
# GRACEFUL BY FALLBACK: an empty shelf / unreachable store falls through to the legacy hardwired
# string (_FALLBACK), so the brain never goes mute because a seed hasn't run. PARSER-FREE: pure
# composition over the structured AnswerResult / trigger — Mongo reads only. The raw string rides
# in the Action payload; `senses` ships it verbatim (rag2-out — slice 3 — will own the polish).
# --------------------------------------------------------------
import logging
import random
from typing import Optional

from lib.core.evaluation import AnswerKind, AnswerVerdict
from lib.core.memory import EvalToken, TokenikoAction

logger = logging.getLogger("tokeniko-brain")


# the legacy voice (pre-scaffold hardwired strings) — now the FALLBACK per category. Kept exact:
# with an unseeded store, today's behavior is byte-identical to yesterday's.
_FALLBACK: dict[str, str] = {
    "answer_yes": "yes",
    "answer_no": "no",
    "answer_no_contradictory": "no, that is contradictory",
    "answer_idk": "I do not know",
    "answer_value": "{value}",
    "speakup_inconsistent": "no, that is contradictory",
    "speakup_false": "no, that is not true",
    "speakup_disagree": "I do not agree",
    "clarify_conflict": "that contradicts what you said before — which holds?",
    "ask_more": "can you tell me more about that?",
    "why": "why is that?",
    "concede_plain": "you are right",
    "concede_retract": "you are right — I no longer hold that {retracted}",
    "concede_weakened": "you are right — what remains true is that {weakened}",
    "concede_retract_weakened": ("you are right — I no longer hold that {retracted} — "
                                 "what remains true is that {weakened}"),
}


# the Zadeh hedge (slice 2): the advmod fuzzy anchors read BACKWARDS — inbound the compiler maps
# "slightly"→0.3 / "passably"→0.5 as degree scalars; outbound a mid/low confidence maps back to
# the anchor word. Only templates DESIGNED for it consume the hedge (the {hedge} slot: «I {hedge}
# disagree») — the table supplies the word, the template owns the grammar, so a hedge can never
# produce broken English. High confidence -> None: the hedge key is absent from the data and
# hedge-slotted scaffolds become unreachable (plain speech). Logic-certain content (1.0) is
# upstream's business: logic never hedges.
def hedge_for(confidence: Optional[float]) -> Optional[str]:
    if confidence is None:
        return None
    if confidence < 0.45:
        return "slightly"    # the 0.3 anchor, inverted
    if confidence < 0.7:
        return "passably"    # the 0.5 anchor, inverted
    return None              # sure enough to speak plain


def _in_band(band, value: Optional[float]) -> bool:
    if value is None or not band:
        return True          # no signal / no band -> the gate stays open
    lo, hi = band[0], band[1]
    return lo <= value <= hi


# pick one scaffold from the category's shelf and bind the data. The shelf = enabled rows of the
# category whose slots the data can satisfy (subset gate — a scaffold demanding {retracted} is
# unreachable without it) AND whose intensity/arousal bands contain the tuple (slice 2: intensity
# joins category as the retrieval double key). An emptied band-shelf falls back to the slot-shelf
# — banding SHADES the voice, never mutes it. The pick is weighted-random (`rng` injectable); the
# bind is str.format on named keys — VERBATIM, the fence. Any store trouble -> the fallback.
def creative_compose(category: str, data: Optional[dict] = None,
                     rng: Optional[random.Random] = None,
                     intensity: Optional[dict] = None) -> str:
    data = {k: str(v) for k, v in (data or {}).items()}
    confidence = (intensity or {}).get("confidence")
    arousal = (intensity or {}).get("arousal")
    hedge = hedge_for(confidence)
    if hedge is not None:
        data.setdefault("hedge", hedge)  # available to {hedge}-designed templates only
    template = _FALLBACK.get(category, "")
    try:
        from lib.core.models import TKScaffoldDoc
        shelf = [s for s in TKScaffoldDoc.find({"category": category, "enabled": True}).to_list()
                 if set(s.slots or []) <= set(data)]
        banded = [s for s in shelf
                  if _in_band(getattr(s, "intensity_band", None), confidence)
                  and _in_band(getattr(s, "arousal_band", None), arousal)]
        pool = banded or shelf  # never-mute: an over-narrow banding falls back to the whole shelf
        if pool:
            picker = rng if rng is not None else random
            chosen = picker.choices(pool, weights=[max(s.weight, 0.0) or 0.0 for s in pool])[0]
            template = chosen.template
            logger.debug("[compose] %s (c=%s a=%s) -> scaffold %s «%s»",
                         category, confidence, arousal, str(chosen.id), template)
    except Exception as error:  # the voice must never crash the brain — fall back, log, speak
        logger.warning("[compose] scaffold store unavailable for %s (%s) — fallback", category, error)
    try:
        return template.format(**data)
    except (KeyError, IndexError, ValueError):
        logger.warning("[compose] template/data mismatch for %s — fallback", category)
        return _FALLBACK.get(category, "").format(**data) if _FALLBACK.get(category) else ""


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
            return "speakup_false", {}
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
# the AnswerResult dict (tokeniko:answer / tokeniko:concede); `trigger` is the eval:* token that
# fired the reflex; `intensity` is the (confidence, arousal) tuple assembled by the plan (slice 2
# — gates the shelf + feeds the hedge). Returns the composed string, or "" when there is nothing
# to say.
def compose_raw(action_token: str, trigger: Optional[str] = None, answer: Optional[dict] = None,
                rng: Optional[random.Random] = None, intensity: Optional[dict] = None) -> str:
    routed = _route(action_token, trigger, answer)
    if routed is None:
        return ""
    category, data = routed
    return creative_compose(category, data, rng=rng, intensity=intensity)

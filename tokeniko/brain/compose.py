# --------------------------------------------------------------
# brain/compose.py — the OUTBOUND message composer (#4 D3b). The brain DECIDES *what to say*; this is
# where that decision becomes a terse **raw** message string. It is the cognition/personality side of
# rendering — the *stance* (yes / no / "that is contradictory" / the solved value) — NOT the fluent
# surface form. The raw string rides in the Action payload; `senses` applies the channel-appropriate
# polish (`decompiler_decompile`, raw → fluent English via Ollama) and carries it to the socket. A
# future native-zip channel skips that polish entirely — which is exactly why the LLM finish lives in
# senses (per-channel) and only the decision lives here.
#
# PARSER-FREE: pure string composition over the structured AnswerResult / trigger — no pipeline import.
# Deterministic + terse on purpose (the LLM polish is senses' job; keep the decision auditable here).
# --------------------------------------------------------------
from typing import Optional

from lib.core.evaluation import AnswerKind, AnswerVerdict
from lib.core.memory import EvalToken, TokenikoAction


# compose the RAW decision text for an outward action. `answer` is the AnswerResult dict (for
# tokeniko:answer); `trigger` is the eval:* token that fired the reflex (for the non-answer reflexes).
# Returns a terse raw string (senses decompiles → fluent English), or "" when there is nothing to say.
def compose_raw(action_token: str, trigger: Optional[str] = None, answer: Optional[dict] = None) -> str:
    if action_token == TokenikoAction.ANSWER.value:
        return _compose_answer(answer or {})
    if action_token == TokenikoAction.SPEAKUP.value:
        # speakup fires on a flawed assertion — name the flaw from the trigger.
        if trigger == EvalToken.INCONSISTENT.value:
            return "no, that is contradictory"
        if trigger == EvalToken.FALSE.value:
            return "no, that is not true"
        return "I do not agree"
    if action_token == TokenikoAction.CLARIFY.value:
        return "that contradicts what you said before — which holds?"
    if action_token == TokenikoAction.ASK.value:
        return "can you tell me more about that?"
    if action_token == TokenikoAction.WHY.value:
        return "why is that?"
    return ""  # post / internal reflexes have no Discord-reply text here


# render the raw answer text from an AnswerResult dict. POLAR reuses the truth verdict (a logic-certain
# NO is loud); WH surfaces the solved value; UNKNOWN is an honest non-answer.
def _compose_answer(answer: dict) -> str:
    kind = answer.get("kind")
    verdict = answer.get("verdict")
    reason = (answer.get("reason") or "").lower()

    if verdict == AnswerVerdict.UNKNOWN.value:
        return "I do not know"

    if kind == AnswerKind.POLAR.value:
        if verdict == AnswerVerdict.YES.value:
            return "yes"
        if verdict == AnswerVerdict.NO.value:
            # a logic-certain NO (inconsistent question) is named as such; else a plain no.
            if "inconsist" in reason or "contradict" in reason:
                return "no, that is contradictory"
            return "no"

    if kind == AnswerKind.WH.value and verdict == AnswerVerdict.VALUE.value:
        value = answer.get("value")
        if value:
            return str(value)

    return "I do not know"  # unrecognized shape -> honest fallback (never fabricate an answer)

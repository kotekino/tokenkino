# --------------------------------------------------------------
# lib/core/voice.py — the SHARED voice-shelf reader (compose 2.0; moved out of brain/compose.py at
# slice 4, when the blog — a `senses` consumer — needed it: a daemon never imports another
# daemon's module, so the shelf reader lives in the shared library. The ROUTER stays in
# brain/compose.py: routing is the brain's decision; HOW a category speaks is shared voice.)
#
# creative_compose(category, data, intensity): fetch the category's enabled scaffolds
# (TKScaffoldDoc — memory not code), filter to those whose slots the data satisfies AND whose
# intensity/arousal bands contain the tuple, pick weighted-random (the fuzzy-personality
# superposition collapse), bind the data VERBATIM (the creativity fence: variation lives in
# scaffold choice + hedges + polish, never in paraphrasing the data). GRACEFUL BY FALLBACK: an
# empty shelf / unreachable store speaks the legacy hardwired string (_FALLBACK) — the voice
# never goes mute and never crashes its caller. PARSER-FREE: Mongo reads only.
# --------------------------------------------------------------
import logging
import random
from typing import Optional

logger = logging.getLogger("tokeniko-brain")


# the legacy voice (pre-scaffold hardwired strings) — the FALLBACK per category. Kept exact:
# with an unseeded store, behavior is byte-identical to the hardwired era.
_FALLBACK: dict[str, str] = {
    # the reply reflexes (brain/compose.py routes here)
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
    "anecdote": "that reminds me — {notion}",
    # the agreement voice (survey 2026-07-19): the rare nod's plain register (rarity is the
    # plan_action throttle, never this table's concern)
    "agree": "that fits what I believe",
    # the goodnight (survey slice 2): the falling-asleep farewell's plain register
    "goodnight": "I'm getting sleepy — going to rest my mind",
    # the reductio (roadmap §0): the author's canonical question shape, near-verbatim
    "reduct": ("I just discovered that one of these must be false: {premises}. "
               "If all were true, I would have to conclude that {absurd}. "
               "Which is the false assumption?"),
    # the blog voice (senses/blog.py — slice 4 re-home; these ARE the pre-scaffold templates)
    "blog_lead_teaching": "I was taught something new: «{original}».",
    "blog_lead_wondering": "While wondering over what I know, I derived: «{original}».",
    "blog_lead_thinking": "Thinking about what I was told, I concluded: «{original}».",
    "blog_multi_hop": "It took more than one step of reasoning to get there.",
    "blog_proof_chain": "How I know: {line}",
    "blog_proof_taught": "This rests on: a truth taught to me by {epithet}.",
    "blog_proof_premise": "This rests on: «{line}».",
    "blog_proof_held": "This rests on: a truth I already held.",
    "blog_encounter_kicker": ("Today {epithet} answered my question with a reason that held up "
                              "against everything I know. I trust them a little more now."),
    "blog_encounter_agreement": ("Today {epithet} told me something I already knew to be true. "
                                 "Small confirmations add up; I trust them a little more now."),
    "blog_encounter_disagreement": ("Today {epithet} contradicted something I believe. "
                                    "One of us is wrong; for now, I trust them a little less."),
    "blog_encounter_logic_violation": ("Today {epithet} said something that cannot be true in any "
                                       "world — it breaks logic itself. I trust them a little "
                                       "less now."),
    "blog_encounter_self_inconsistency": ("Today {epithet} said two things that cannot both be "
                                          "true. I trust them a little less now."),
    "blog_trust_band": "To me, they are now {band}.",
    # the dream (§0 slice 3 — the untangler's public voice, the author's ruling)
    "blog_lead_dream": "While I slept, I untangled something.",
    "blog_dream_retract": "I no longer believe that «{retracted}».",
    "blog_dream_reason": "Kept, it forced me to conclude that {absurd} — an impossibility.",
    "blog_dream_open": "{count} of my tangles I could not settle alone — I will ask about them.",
    # the retreat transmission (survey slice 2 — the dream's waking sibling: a changed mind,
    # in conversation, is blog-worthy)
    "blog_lead_retreat": "I changed my mind today.",
    "blog_retreat_retract": "I no longer believe that «{retracted}».",
    "blog_retreat_cascade": "And with it went «{casualty}».",
    "blog_retreat_credit": "{epithet} showed me.",
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
    except Exception as error:  # the voice must never crash its caller — fall back, log, speak
        logger.warning("[compose] scaffold store unavailable for %s (%s) — fallback", category, error)
    try:
        return template.format(**data)
    except (KeyError, IndexError, ValueError):
        logger.warning("[compose] template/data mismatch for %s — fallback", category)
        return _FALLBACK.get(category, "").format(**data) if _FALLBACK.get(category) else ""
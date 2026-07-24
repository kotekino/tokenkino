# --------------------------------------------------------------
# brain/mimicry.py — LEARNED SCAFFOLDS FROM THE AUDIENCE (roadmap §1, stage one: ephemeral mimicry).
#
# Humans in an intense 1:1 dialogue converge on each other's phrasing (linguistic accommodation).
# tokeniko gets the same: while talking with a decently-trusted person, a phrasing of theirs that
# re-expresses a communicative act he ALREADY performs joins his shelf SCOPED to that person — he
# drifts toward their register mid-conversation, and his voice with everyone else stays untouched.
# The quarantine IS the conversation: the scoped row is a MIMIC (provenance "mimic:<uid>"), and the
# durable shelf only ever grows in SLEEP (brain/main._sleep_duty promotes-or-retires — stage two).
#
# PARSER-FREE (the brain's law): Mongo reads + the context ring + numpy geometry only. No compile
# happens here — Lane A social rows carry no zip (a greeting is not a claim), Lane B rows reuse the
# item's OWN already-compiled zip. v1 scope (ruled): Lane A (social acts) + Lane B SLOT-LESS only
# (whole-zip match); slotted-template extraction is v2.
# --------------------------------------------------------------
import logging
import os
from typing import Optional

from lib.core.models import TKScaffoldDoc
from lib.core.trust import resolve_canonical
from lib.llc.evaluator import evaluator_compareZip
from brain import context

logger = logging.getLogger("tokeniko-brain")

# the gate ladder — all env-tunable, defaults as ruled (2026-07-24).
_MOMENTUM = int(os.getenv("MIMIC_MOMENTUM", "3"))    # «after a while»: prior turns from this talker
_BAR = float(os.getenv("MIMIC_BAR", "0.6"))          # «decent» trust to start converging
_FLOOR = float(os.getenv("MIMIC_FLOOR", "0.85"))     # Lane B whole-zip match to name the act re-phrased
_CAP = int(os.getenv("MIMIC_CAP", "8"))              # per-talker growth bound (un-retired mimic rows)
_MAXLEN = int(os.getenv("MIMIC_MAXLEN", "120"))      # a mannerism is SHORT

# Lane A: a recognized social act maps to the speakable compose category it re-phrases. `thanks`
# has no speakable category yet (the reciprocal-thanks is parked) — it is skipped, never mimicked.
_LANE_A = {"greeting": "greet", "farewell": "farewell"}

# Lane B: the communicative acts a whole-zip match may name — the compose categories a heard
# assertion/answer could be re-phrasing. blog_*/concede_*/reduct are NOT learnable (his private
# registers, never picked up from the audience).
_LEARNABLE = {"greet", "farewell", "agree", "answer_yes", "answer_no",
              "answer_idk", "why", "goodnight", "ask_more"}


# the Lane B classifier: the enabled, GLOBAL, SLOT-LESS, zip-bearing learnable row nearest the
# item's zip, if it clears the floor — that row's category is the act being re-phrased. None when
# nothing is close enough (conservative: an unmatched phrasing is not learned).
def _lane_b_category(item_zip) -> Optional[str]:
    best_cat, best_sim = None, _FLOOR
    rows = TKScaffoldDoc.find(
        {"category": {"$in": list(_LEARNABLE)}, "enabled": True, "scope": None}
    ).to_list()
    for row in rows:
        if row.slots or row.zip is None:
            continue
        try:
            sim = evaluator_compareZip(item_zip, row.zip)
        except Exception as error:  # a malformed stored zip must never sink the pass
            logger.debug("[mimicry] compare skipped for scaffold %s (%s)", str(row.id), error)
            continue
        if sim >= best_sim:
            best_cat, best_sim = row.category, sim
    return best_cat


# observe one just-processed memory item; mint an ephemeral mimic row when every gate passes.
# Returns True iff a row was minted. The caller wraps this like the ring feed (an error logs +
# continues, never blocks thinking) — but the gates themselves are cheap and conservative.
def mimic_observe(item) -> bool:
    # 1. NEVER SELF — his own speech is not something he picks up from the audience.
    soul = resolve_canonical(getattr(item, "sourceId", "") or "")
    if soul is None or getattr(soul, "isMe", False):
        return False
    scope_uid = soul.uid                                    # the CANONICAL soul: the scope + provenance key
    talker_trust = 1.0 if soul.imprint else soul.trust

    # 2. MOMENTUM («after a while») — enough prior turns from this talker in the channel's ring.
    # context_add already appended THIS item (thinking runs it first), so subtract it to count PRIORS.
    key = context.channel_key(item)
    prior = context.talker_depth(key, str(item.sourceId)) - 1
    if prior < _MOMENTUM:
        return False

    # 3. TRUST («decent») — only converge toward someone he already half-trusts.
    if talker_trust < _BAR:
        return False

    # 4/5. the ACT being re-phrased — Lane A (a pure social act) or Lane B (a whole-zip match).
    if getattr(item, "social", None):
        category = _LANE_A.get(item.social)                 # greeting->greet, farewell->farewell; thanks skipped
        if category is None:
            return False
        row_zip = None                                      # a greeting is not a claim — no zip (honest, like a seed)
    elif getattr(item, "zip", None) is not None:
        category = _lane_b_category(item.zip)
        if category is None:
            return False
        row_zip = item.zip                                  # the mimic carries the item's OWN compiled zip
    else:
        return False

    # 6. QUALITY FENCE — his raw words are the mannerism, kept VERBATIM.
    template = (item.original or "").strip()
    if not template:
        return False
    if "{" in template or "}" in template:                  # str.format collision — the bind would choke
        return False
    if len(template) > _MAXLEN:                             # a mannerism is short, not a monologue
        return False
    # dedup: this exact phrasing already sits in that category (any provenance/scope) — never twice.
    if TKScaffoldDoc.find_one({"category": category, "template": template}).run() is not None:
        return False
    # growth bound: one talker may only lend so many un-retired mimic rows at a time.
    if TKScaffoldDoc.find({"scope": scope_uid, "enabled": True}).count() >= _CAP:
        return False

    TKScaffoldDoc(
        category=category, template=template, slots=[], zip=row_zip,
        provenance=f"mimic:{scope_uid}", trusted=talker_trust, weight=1.0,
        enabled=True, scope=scope_uid, used=0,
    ).insert()
    logger.info("[mimicry] 🪞 a way of speaking picked up from %s (%s)", soul.name, category)
    return True

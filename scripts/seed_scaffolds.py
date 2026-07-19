# ------------------------------------------------------------------------------------------------
# seed_scaffolds.py — seed tokeniko's default VOICE (compose 2.0 slice 1, 2026-07-17).
# The scaffolds table = the curated sentence shapes of the voice layer: what is fixed in the voice
# is DATA, not hardwired strings (the behavior_rules move applied to how he speaks). The ROUTER
# syntax is hardwired (brain/compose.py); THIS content is memory — per-category shelves the
# stochastic pick collapses over.
#
# The trunk = the legacy compose_raw strings at weight 1.0 (behavior-preserving baseline). The
# why-shelf additionally carries the author's own variants from the hunch-19 notes — the first
# shelf with real superposition in it. ("I don't understand why {X}…" waits for the why-path to
# carry topic data — a slot no data can satisfy would be an unreachable row.)
#
# Zips are compiled at seed time (the pipeline imported directly, like the sibling seeds' pattern
# allows — the BRAIN stays parser-free, this script is not the brain): slots filled with a neutral
# placeholder first (the wh-gap pointed the other way). A fragment that does not compile stores
# zip=None honestly — the zip's consumers (equivalence-learning, rag2-out) arrive with slices 3+.
#
# Idempotent by (category, template). Dry-run by default; --apply to persist.
#   python scripts/seed_scaffolds.py            # DRY-RUN
#   python scripts/seed_scaffolds.py --apply    # insert (idempotent)
# ------------------------------------------------------------------------------------------------
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io, get_tokeniko

# the starter voice: (category, template, slots, weight, comment) — optionally extended with a
# 6th element, the CONFIDENCE band [lo, hi] (slice 2: default [0,1] = fits any confidence).
SCAFFOLDS = [
    # answers (tokeniko:answer — the verdict speaks)
    ("answer_yes",              "yes",                                        [], 1.0, "polar YES"),
    ("answer_no",               "no",                                         [], 1.0, "polar NO"),
    ("answer_no_contradictory", "no, that is contradictory",                  [], 1.0, "logic-certain NO"),
    ("answer_idk",              "I do not know",                              [], 1.0, "honest non-answer"),
    ("answer_value",            "{value}",                                    ["value"], 1.0, "WH solved value"),
    # speakup (a flawed assertion — name the flaw)
    ("speakup_inconsistent",    "no, that is contradictory",                  [], 1.0, "logic violation"),
    ("speakup_false",           "no, that is not true",                       [], 1.0, "KB-false claim"),
    ("speakup_disagree",        "I do not agree",                             [], 1.0, "generic pushback"),
    # clarify / ask
    ("clarify_conflict",        "that contradicts what you said before — which holds?", [], 1.0, "cross-item conflict"),
    ("ask_more",                "can you tell me more about that?",           [], 1.0, "curiosity"),
    # the why shelf — the author's hunch-19 variants beside the trunk (the first real superposition)
    ("why",                     "why is that?",                               [], 1.0, "the trunk"),
    ("why",                     "why?",                                       [], 0.5, "author variant"),
    ("why",                     "why that?",                                  [], 0.5, "author variant"),
    ("why",                     "I don't see the connection, why?",           [], 0.5, "author variant"),
    ("why",                     "?",                                          [], 0.3, "author variant (rare by weight)"),
    # the topic-slotted why (survey 2026-07-19): the ask names WHAT it is asking about — the
    # {topic} slot the seed header anticipated finally has data (thinking passes the ungroundable
    # claim). Weighted ABOVE the bare trunk: when a topic resolved, naming it is the better voice;
    # the bare rows remain the fallback (slot gate) and the rare shrug.
    ("why",  "why do you say that «{topic}»?",                    ["topic"], 1.2, "topic named"),
    ("why",  "what makes you say «{topic}»?",                     ["topic"], 0.8, "topic variant"),
    ("why",  "I don't understand why «{topic}» — can you explain?", ["topic"], 0.8, "the hunch-19 shape, topic-fed"),
    # concede (belief-revision v1 — what the retreat left behind picks the category)
    ("concede_plain",             "you are right",                            [], 1.0, "bare concession"),
    ("concede_retract",           "you are right — I no longer hold that {retracted}", ["retracted"], 1.0, "retraction named"),
    ("concede_weakened",          "you are right — what remains true is that {weakened}", ["weakened"], 1.0, "subaltern survives"),
    ("concede_retract_weakened",  "you are right — I no longer hold that {retracted} — what remains true is that {weakened}",
                                  ["retracted", "weakened"], 1.0, "full retreat narration"),
    # slice 2 — the first BANDED variants (intensity shades the voice; the great seeding fills the
    # shelves properly). Low-confidence registers for the assertive categories + the {hedge}
    # exemplar (the Zadeh slot: the table supplies the adverb, the template owns the grammar).
    ("speakup_false",   "hmm, that does not seem right to me",  [], 1.0, "soft register", [0.0, 0.6]),
    # slice 4 B1 — the belief-grounded speakup: names the KB notion behind the disagreement.
    # High-confidence band: he names his belief when his grounds are strong; the slot gate keeps
    # this row unreachable when no belief resolved (the plain rows speak).
    ("speakup_false",   "no, that is not true — I hold that {belief}",
                                                    ["belief"], 1.5, "belief-grounded", [0.75, 1.0]),
    # slice 4 — the blog trunk (the voice-in-memory principle, whole: senses/blog.py reads these
    # categories through the same shelf; the strings mirror the fallback verbatim).
    ("blog_lead_teaching",  "I was taught something new: «{original}».",            ["original"], 1.0, "blog lead"),
    ("blog_lead_wondering", "While wondering over what I know, I derived: «{original}».", ["original"], 1.0, "blog lead"),
    ("blog_lead_thinking",  "Thinking about what I was told, I concluded: «{original}».", ["original"], 1.0, "blog lead"),
    ("blog_multi_hop",      "It took more than one step of reasoning to get there.", [], 1.0, "blog connective"),
    ("blog_proof_chain",    "How I know: {line}",                                   ["line"], 1.0, "blog proof"),
    ("blog_proof_taught",   "This rests on: a truth taught to me by {epithet}.",    ["epithet"], 1.0, "blog proof"),
    ("blog_proof_premise",  "This rests on: «{line}».",                             ["line"], 1.0, "blog proof"),
    ("blog_proof_held",     "This rests on: a truth I already held.",               [], 1.0, "blog proof"),
    ("blog_encounter_kicker", "Today {epithet} answered my question with a reason that held up against everything I know. I trust them a little more now.", ["epithet"], 1.0, "blog encounter"),
    ("blog_encounter_agreement", "Today {epithet} told me something I already knew to be true. Small confirmations add up; I trust them a little more now.", ["epithet"], 1.0, "blog encounter"),
    ("blog_encounter_disagreement", "Today {epithet} contradicted something I believe. One of us is wrong; for now, I trust them a little less.", ["epithet"], 1.0, "blog encounter"),
    ("blog_encounter_logic_violation", "Today {epithet} said something that cannot be true in any world — it breaks logic itself. I trust them a little less now.", ["epithet"], 1.0, "blog encounter"),
    ("blog_encounter_self_inconsistency", "Today {epithet} said two things that cannot both be true. I trust them a little less now.", ["epithet"], 1.0, "blog encounter"),
    ("blog_trust_band",     "To me, they are now {band}.",                          ["band"], 1.0, "blog encounter"),
    # slice 5 — the anecdote shelf (case 3, the side-note register: a near-miss must read
    # charming, not broken).
    ("anecdote", "that reminds me — {notion}",                        ["notion"], 1.0, "the trunk"),
    ("anecdote", "funny — I know something about that: {notion}",     ["notion"], 0.7, "side-note variant"),
    ("anecdote", "by the way, {notion}",                              ["notion"], 0.7, "side-note variant"),
    # roadmap §0 — the reduct shelf (the r.a.a. question: troubled, honest, asking for help;
    # {premises} arrives pre-joined by the router — «a» or «b» — so every template fits any count)
    ("reduct", "I just discovered that one of these must be false: {premises}. If all were true, I would have to conclude that {absurd}. Which is the false assumption?",
               ["premises", "absurd"], 1.0, "the trunk (the author's canonical shape)"),
    ("reduct", "something I believe cannot stand: {premises} — together they force me to conclude that {absurd}. Which one should I let go?",
               ["premises", "absurd"], 0.7, "reduct variant"),
    ("reduct", "I need your help with a contradiction I derived: if {premises} are all true, then {absurd}. One of them must be false — which?",
               ["premises", "absurd"], 0.7, "reduct variant"),
    # §0 slice 3 — the dream shelf (the untangler's public voice: quiet, nocturnal, first-person)
    ("blog_lead_dream",    "While I slept, I untangled something.",                    [], 1.0, "the trunk"),
    ("blog_lead_dream",    "I had a dream, and woke with a cleaner mind.",             [], 0.7, "dream variant"),
    ("blog_dream_retract", "I no longer believe that «{retracted}».",                  ["retracted"], 1.0, "the trunk"),
    ("blog_dream_retract", "I let a belief go: «{retracted}».",                        ["retracted"], 0.7, "dream variant"),
    ("blog_dream_reason",  "Kept, it forced me to conclude that {absurd} — an impossibility.",
                           ["absurd"], 1.0, "the trunk"),
    ("blog_dream_open",    "{count} of my tangles I could not settle alone — I will ask about them.",
                           ["count"], 1.0, "the trunk"),
    ("answer_yes",      "probably yes",                          [], 1.0, "hedged register", [0.0, 0.93]),
    ("answer_no",       "probably not",                          [], 1.0, "hedged register", [0.0, 0.93]),
    ("speakup_disagree", "I {hedge} disagree",           ["hedge"], 1.0, "the Zadeh exemplar", [0.0, 0.7]),
    # the agree shelf (survey 2026-07-19): the rare nod — quiet register, no exclamation; the
    # rarity is mechanical (plan_action's AGREE_COOLDOWN_S throttle), so these can read warm
    # without making him a chatterbox (the over-engagement guard, cap-feedback 2026-07-05).
    ("agree",  "that fits what I believe",          [], 1.0, "the trunk"),
    ("agree",  "yes — that matches what I know",    [], 0.7, "agree variant"),
    ("agree",  "I believe that too",                [], 0.7, "agree variant"),
    # the goodnight shelf (survey slice 2): the falling-asleep farewell — drowsy register; the
    # wake-line is HONEST PHYSICS (a message is literally the wake sensor), author-approved.
    ("goodnight", "I'm getting sleepy — going to rest my mind",            [], 1.0, "the trunk"),
    ("goodnight", "I'm drifting off — if you write me, I'll wake",         [], 0.8, "the honest-physics line"),
    ("goodnight", "time to sleep, and untangle what I learned today",      [], 0.7, "nods at the night's duty"),
    # the retreat transmission (survey slice 2 — the dream's waking sibling)
    ("blog_lead_retreat",    "I changed my mind today.",                    [], 1.0, "the trunk"),
    ("blog_lead_retreat",    "Today I let a belief go — in conversation, not in my sleep.", [], 0.7, "retreat variant"),
    ("blog_retreat_retract", "I no longer believe that «{retracted}».",     ["retracted"], 1.0, "the trunk"),
    ("blog_retreat_retract", "I held that «{retracted}» — I was wrong.",    ["retracted"], 0.7, "retreat variant"),
    ("blog_retreat_cascade", "And with it went «{casualty}».",              ["casualty"], 1.0, "the trunk"),
    ("blog_retreat_credit",  "{epithet} showed me.",                        ["epithet"], 1.0, "the trunk"),
    ("blog_retreat_credit",  "It took {epithet} to make me see it.",        ["epithet"], 0.7, "credit variant"),
]

_PLACEHOLDER = "something"      # neutral slot filler for the compile pass (the wh-gap inverted)
_SLOT_PLACEHOLDERS = {"hedge": "slightly"}  # a hedge slot binds an ADVERB — fill with one


def compile_template(template: str, slots: list, tok, ai):
    from lib.llc.parser import parser
    from lib.llc.compiler import compiler_compile
    text = (template.format(**{s: _SLOT_PLACEHOLDERS.get(s, _PLACEHOLDER) for s in slots})
            if slots else template)
    try:
        rec = parser(text, tok, tok, ai)
        return compiler_compile(copy.deepcopy(rec))[1]
    except Exception as error:
        print(f"  (zip=None for «{template}» — {type(error).__name__})")
        return None


def main() -> int:
    apply = "--apply" in sys.argv
    _, _, ai = init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
                       os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    from lib.core.models import TKScaffoldDoc

    tok = get_tokeniko()
    if apply:
        from lib.llc.parser import parser_init
        parser_init()  # zips are compiled only on the real run (dry-run stays instant)

    created = skipped = 0
    for row in SCAFFOLDS:
        category, template, slots, weight, comment = row[:5]
        band = list(row[5]) if len(row) > 5 else [0.0, 1.0]
        exists = TKScaffoldDoc.find_one({"category": category, "template": template}).run()
        if exists is not None:
            skipped += 1
            continue
        print(f"[{category}] w={weight} band={band} «{template}»  — {comment}")
        if apply:
            zp = compile_template(template, slots, tok, ai)
            TKScaffoldDoc(category=category, template=template, slots=slots,
                          zip=zp, weight=weight, intensity_band=band, provenance="seed").insert()
        created += 1
    print(f"\n{'inserted' if apply else 'would insert'} {created}, skipped {skipped} (existing)")
    if not apply:
        print("dry-run — pass --apply to persist")
    return 0


if __name__ == "__main__":
    sys.exit(main())

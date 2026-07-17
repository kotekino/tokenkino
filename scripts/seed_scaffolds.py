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

# the starter voice: (category, template, slots, weight, comment).
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
    # concede (belief-revision v1 — what the retreat left behind picks the category)
    ("concede_plain",             "you are right",                            [], 1.0, "bare concession"),
    ("concede_retract",           "you are right — I no longer hold that {retracted}", ["retracted"], 1.0, "retraction named"),
    ("concede_weakened",          "you are right — what remains true is that {weakened}", ["weakened"], 1.0, "subaltern survives"),
    ("concede_retract_weakened",  "you are right — I no longer hold that {retracted} — what remains true is that {weakened}",
                                  ["retracted", "weakened"], 1.0, "full retreat narration"),
]

_PLACEHOLDER = "something"  # neutral slot filler for the compile pass (the wh-gap inverted)


def compile_template(template: str, slots: list, tok, ai):
    from lib.llc.parser import parser
    from lib.llc.compiler import compiler_compile
    text = template.format(**{s: _PLACEHOLDER for s in slots}) if slots else template
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
    for category, template, slots, weight, comment in SCAFFOLDS:
        exists = TKScaffoldDoc.find_one({"category": category, "template": template}).run()
        if exists is not None:
            skipped += 1
            continue
        print(f"[{category}] w={weight} «{template}»  — {comment}")
        if apply:
            zp = compile_template(template, slots, tok, ai)
            TKScaffoldDoc(category=category, template=template, slots=slots,
                          zip=zp, weight=weight, provenance="seed").insert()
        created += 1
    print(f"\n{'inserted' if apply else 'would insert'} {created}, skipped {skipped} (existing)")
    if not apply:
        print("dry-run — pass --apply to persist")
    return 0


if __name__ == "__main__":
    sys.exit(main())

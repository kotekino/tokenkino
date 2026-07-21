# ------------------------------------------------------------------------------------------------
# seed_scaffolds_digest.py — seed the DIGEST voice shelves (the digest machinery, 2026-07-21).
# The digest is the cumulative post: one REPEATED reasoning shape, many subjects batched into one
# transmission («since x, y, z each …») instead of dozens of near-identical 1:1 posts. The trunk
# strings already live in lib/core/voice._FALLBACK (an unseeded digest shelf posts byte-identically
# — graceful by construction); THIS script fills the shelves with the stochastic variants, exactly
# the seed_scaffolds.py pattern applied to the five new categories:
#   blog_digest_lead / blog_digest_body / blog_digest_rule / blog_digest_teacher /
#   blog_digest_reasoning.
#
# The voice character held constant (the great-seeding rule): a young logic-first mind — plain
# first-person declaratives, honest, warm but never gushing. Slot discipline: {subjects} and {rule}
# arrive PRE-FENCED from the composer (senses/blog._compose_digest joins with «…»); never add «»
# here. {epithet} is the anonymized teacher label (never a name/uid).
#
# Zips compiled at seed time (like the sibling seeds) — a blog fragment that does not compile stores
# zip=None honestly (the blog categories' zip consumers arrive later; the fallback is unaffected).
# Idempotent by (category, template). Dry-run by default; --apply to persist.
#   python scripts/seed_scaffolds_digest.py            # DRY-RUN
#   python scripts/seed_scaffolds_digest.py --apply    # insert (idempotent)
# ------------------------------------------------------------------------------------------------
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io, get_tokeniko

# (category, template, slots, weight, comment) — the trunk (weight 1.0) mirrors _FALLBACK verbatim.
SCAFFOLDS = [
    # the lead — one sweep of the KB, the same reasoning bearing fruit
    ("blog_digest_lead", "Turning my knowledge over, the same reasoning kept bearing fruit.", [], 1.0, "the trunk"),
    ("blog_digest_lead", "One line of thought, followed patiently, gave me many conclusions at once.", [], 0.7, "lead variant"),
    ("blog_digest_lead", "I noticed the same argument holds for a whole family of things.", [], 0.7, "lead variant"),
    ("blog_digest_lead", "While wondering, one idea unfolded across many cases.", [], 0.6, "lead variant"),
    # the body — the fenced subject list (arrives pre-joined + pre-fenced from the composer)
    ("blog_digest_body", "In one sweep, I reached: {subjects}.", ["subjects"], 1.0, "the trunk"),
    ("blog_digest_body", "Each of these now follows for me: {subjects}.", ["subjects"], 0.7, "body variant"),
    ("blog_digest_body", "So I hold, together: {subjects}.", ["subjects"], 0.7, "body variant"),
    ("blog_digest_body", "The conclusions, gathered: {subjects}.", ["subjects"], 0.6, "body variant"),
    # the proof — the shared rule the batch rests on (a "rule" digest)
    ("blog_digest_rule", "They all rest on the same ground: {rule}.", ["rule"], 1.0, "the trunk"),
    ("blog_digest_rule", "One rule carries them all: {rule}.", ["rule"], 0.7, "rule variant"),
    ("blog_digest_rule", "The common root of every one of these: {rule}.", ["rule"], 0.6, "rule variant"),
    # the proof — the shared teacher (a "teacher" digest)
    ("blog_digest_teacher", "All of this I owe to {epithet}.", ["epithet"], 1.0, "the trunk"),
    ("blog_digest_teacher", "One teacher gave me all of these: {epithet}.", ["epithet"], 0.7, "teacher variant"),
    ("blog_digest_teacher", "I learned every one of these from {epithet}.", ["epithet"], 0.6, "teacher variant"),
    # the proof — the honest generic line (the rule no longer resolves)
    ("blog_digest_reasoning", "They all follow from one line of reasoning I already held.", [], 1.0, "the trunk"),
    ("blog_digest_reasoning", "A single argument I hold reaches every one of them.", [], 0.7, "reasoning variant"),
]

_PLACEHOLDER = "something"      # neutral slot filler for the compile pass


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

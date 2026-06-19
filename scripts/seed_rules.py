# ------------------------------------------------------------------------------------------------
# seed_rules.py — seed a small set of RULE-shaped axioms (priority-2 step b).
# The bootstrapped KB is almost entirely WordNet-gloss definitions (generic/existential), with ~no
# genuine rules. Forward-chaining (step c) needs RULES to propagate. This seeds a curated handful of
# *universal property rules* ("all carnivores eat meat") — universal-quantified subject + predicate —
# which the is_a graph + the chaining engine can propagate down the taxonomy. The UNIVERSAL quantifier
# also cleanly distinguishes these rules from the generic/existential gloss-axioms.
#
# Stored as trusted axioms via AxiomService (the same compile path as POST /axioms). Idempotent: an
# axiom whose `original` already exists is skipped.
#
# Dry-run by default (compiles + prints the shape, writes nothing). Pass --apply to persist.
#   python scripts/seed_rules.py            # DRY-RUN: compile-check the rules
#   python scripts/seed_rules.py --apply    # insert the rules as axioms (idempotent)
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io, get_tokeniko
from lib.core.tkzip import TKZipContent

# the curated rule set (priority-2 step b): 3 taxonomic-property + 2 identity/logic.
RULES = [
    "all carnivores eat meat",   # taxonomic-property
    "all birds have feathers",   # taxonomic-property (has/part)
    "all fish swim",             # taxonomic-property
    "all humans are mortal",     # logic/syllogism (chains with "Mari is a human" -> "Mari is mortal")
    "all thinkers exist",        # identity/self (cogito-flavored)
]


def _leaves(item):
    c = item.content
    if isinstance(c, TKZipContent):
        return [c]
    out = []
    if isinstance(c, list):
        for ch in c:
            out += _leaves(ch)
    return out


def main():
    apply = "--apply" in sys.argv
    print(f"seed_rules.py — {'APPLYING (writes enabled)' if apply else 'DRY-RUN (no writes)'}")

    _, _, ai = init_io(
        os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"),
    )
    tok = get_tokeniko()
    from lib.llc.parser import parser_init
    parser_init()
    from api.services import AxiomService
    from lib.core.models import TKAxiomDoc
    service = AxiomService(tok, ai)

    inserted = skipped = failed = 0
    for sentence in RULES:
        try:
            fields = service.compile_fields(sentence)
            leaves = _leaves(fields["zip"].items)
            shape = " | ".join(
                f"q={(getattr(c, 'quantifier', None).value if getattr(c, 'quantifier', None) else None)} "
                f"{getattr(c, 'senses', None)}"
                for c in leaves
            )
            universal = any(
                getattr(c, "quantifier", None) and c.quantifier.value == "universal" for c in leaves
            )
            flag = "UNIVERSAL" if universal else "!! NOT universal"
            existing = TKAxiomDoc.find_one({"original": sentence}).run()
            print(f"\n  {sentence!r}  [{len(leaves)} leaf] {flag}")
            print(f"    raw:   {fields['raw']}")
            print(f"    shape: {shape}")
            if existing is not None:
                print("    -> already present, skipping")
                skipped += 1
                continue
            if apply:
                doc = service.create(sentence)
                print(f"    -> inserted axiom id={doc.id}")
                inserted += 1
            else:
                print("    -> would insert (dry-run)")
        except Exception as error:
            print(f"\n  {sentence!r}  -> FAILED: {error!r}")
            failed += 1

    print(f"\nDONE [{'APPLIED' if apply else 'DRY-RUN'}]  inserted={inserted}  skipped={skipped}  failed={failed}")


if __name__ == "__main__":
    main()

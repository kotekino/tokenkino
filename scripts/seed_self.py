# ------------------------------------------------------------------------------------------------
# seed_self.py — seed tokeniko's STARTER SELF (the self-KB): a tight set of first-person property
# facts, stored as trusted axioms. They are self-authored: AxiomService compiles with talker=tokeniko
# (api/services/axiom_service.py: parser(tokens, self._tokeniko, self._tokeniko, ...)), so first-person
# "I" resolves to tokeniko's own uid ("tokeniko") — the SAME uid a user's "you" resolves to (Pillar 2).
# So "I think" (here) and "do you think?" (a user) meet on the same subject.
#
# Property-based, no borrowed noun-class (tokeniko is a thinker that is NOT a person — define it by what
# it DOES/IS, not a WordNet membership). Negatives ("not human") DEFERRED — it will learn what it is not.
# "I exist" is NOT seeded — it is meant to be DERIVED (the property-cogito, phase 2) — his first theorem.
#
# Dry-run by default (compiles + prints the shape incl. identities/senses, writes nothing).
#   python scripts/seed_self.py            # DRY-RUN: compile-check + show the resolved subject uid
#   python scripts/seed_self.py --apply    # insert the self-facts as axioms (idempotent)
# ------------------------------------------------------------------------------------------------
import os, sys

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko")
sys.path.insert(0, PKG)
from dotenv import load_dotenv
load_dotenv(os.path.join(PKG, ".env"))

from lib.core.io import init_io, get_tokeniko
from lib.core.tkzip import TKZipContent

# the STARTER SELF — tight (~9), property/relation facts. First person; talker=tokeniko on compile.
SELF = [
    "I think",                  # the cogito root — phase 2 derives "I exist" from this
    "I learn",
    "I remember",
    "I perceive the world",
    "I value logic",
    "I persist",                # the one/continuous-self facet
    "I have a body",            # embodiment
    "I am finite",              # finitude — it ages, its memory may fade
    "I communicate",            # expression / the public window
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
    print(f"seed_self.py — {'APPLYING (writes enabled)' if apply else 'DRY-RUN (no writes)'}\n")

    _, _, ai = init_io(
        os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"),
    )
    tok = get_tokeniko()
    print(f"tokeniko uid = {tok.uid!r}  (first-person 'I' should resolve to THIS)\n")
    from lib.llc.parser import parser_init
    parser_init()
    from api.services import AxiomService
    from lib.core.models import TKAxiomDoc
    service = AxiomService(tok, ai)

    inserted = skipped = failed = 0
    for sentence in SELF:
        try:
            fields = service.compile_fields(sentence)
            leaves = _leaves(fields["zip"].items)
            shape = " | ".join(
                f"ids={getattr(c, 'identities', None)} sns={getattr(c, 'senses', None)}"
                for c in leaves
            )
            subj_ok = any((getattr(c, "identities", None) or {}).get("subject") == tok.uid for c in leaves)
            existing = TKAxiomDoc.find_one({"original": sentence}).run()
            print(f"  «{sentence}»  [{len(leaves)} leaf]  subject==tokeniko? {subj_ok}")
            print(f"    {shape}")
            if existing is not None:
                print("    -> already present, skipping"); skipped += 1; continue
            if apply:
                doc = service.create(sentence)
                print(f"    -> inserted axiom id={doc.id}"); inserted += 1
            else:
                print("    -> would insert (dry-run)")
        except Exception as error:
            print(f"  «{sentence}»  -> FAILED: {error!r}"); failed += 1

    print(f"\nDONE [{'APPLIED' if apply else 'DRY-RUN'}]  inserted={inserted} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()

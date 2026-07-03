# ------------------------------------------------------------------------------------------------
# revoke_edge.py — STEP 4: retract a LOW-TRUST tier is_a edge and everything that rests on it.
#
# The revocability half of the wondering net: because a definition-derived edge is low-trust and
# fallible, it must be RETRACTABLE — and retracting it must also archive every theorem whose proof
# walked it (else an orphaned conclusion would outlive its premise). The chainer records a tier edge as
# the stable premise key "subject|is_a|object" (evaluation_harness), so this is a direct lookup —
# theorem premises never reference other theorems, so no transitive cascade is needed.
#
# DRY-RUN by default (prints the blast radius); --apply archives the theorems + deletes the edge.
#
#   python scripts/revoke_edge.py air.n.01 mixture.n.01            # dry-run
#   python scripts/revoke_edge.py air.n.01 mixture.n.01 --apply     # retract
# ------------------------------------------------------------------------------------------------
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDerivedRelationDoc, TKTheoremDoc


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 2:
        print("usage: python scripts/revoke_edge.py <subject_sense> <object_sense> [--apply]")
        return
    subject, object = args
    key = f"{subject}|is_a|{object}"

    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    edge = TKDerivedRelationDoc.find_one({"subject": subject, "object": object, "relation": "is_a"}).run()
    # TRANSITIVE dependents (step 3): theorems resting on this edge, then THEIR dependents, recursively
    # (revoke_dependents walks the provenance net; dry_run here only reports).
    from lib.core.evaluation_harness import revoke_dependents
    dependents = revoke_dependents([key], dry_run=True)

    bar = "=" * 80
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n{bar}\nREVOKE tier edge  [{mode}]  {key}\n{bar}")
    if edge is None:
        print(f"  no such tier edge in derived_relations — nothing to revoke.")
    else:
        print(f"  edge: {edge.subject} is_a {edge.object}  (trust {edge.trust}, method {edge.method})")
        print(f"        source: «{edge.source_original}»")
    print(f"\n  theorems resting on it ({len(dependents)}):")
    for t in dependents:
        print(f"    [{'archived' if t.archived else 'ACTIVE'}] «{t.original}»  (trusted {t.trusted})")

    if not apply:
        print(f"\n  DRY-RUN — nothing changed. Re-run with --apply to retract.\n{bar}")
        return

    archived = len(revoke_dependents([key], dry_run=False))  # the transitive cascade, for real
    if edge is not None:
        edge.delete()
    print(f"\n  archived {archived} dependent theorem(s); deleted the edge."
          f"\n  (archived theorems are kept as history, out of active reasoning.)\n{bar}")


if __name__ == "__main__":
    main()

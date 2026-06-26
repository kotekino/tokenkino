# ------------------------------------------------------------------------------------------------
# wonder_kb.py — the KB-WONDERING breadth diagnostic (wondering-v2, step 1d-A).
# Forward-SATURATES tokeniko's whole KB: seeds the chainer from every entity it knows (individuals
# with facts + rule-subject classes) and shows the genuinely-NEW conclusions the KB IMPLIES but no
# one asserted — novelty-gated (>=2 premises = a real combination, not a single-rule restatement) and
# deduped. This is the DRY-RUN of the long-wondering soak (1e): it reveals, read-only, exactly what
# tokeniko would derive on its own.
#
# READ-ONLY — derives + prints; writes NOTHING (rendering + materialization is 1d-B + the API seam).
#   python scripts/wonder_kb.py
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core import evaluation_harness as H
from lib.core.models import TKAxiomDoc


def main():
    init_io(
        os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"),
    )

    conclusions = H.kb_wonder()
    print(f"\nKB-wondering — {len(conclusions)} genuinely-new conclusion(s) the KB implies "
          f"(>=2 premises, deduped):\n")

    for c in sorted(conclusions, key=lambda x: (x["subject_kind"], x["subject"])):
        obj = f" {c['object']}" if c["object"] else ""
        neg = "NOT " if c["negated"] else ""
        print(f"  [{c['subject_kind']:10}] {c['subject']}  =>  {neg}{c['predicate']}{obj}"
              f"   ({len(c['premises'])} premises)")
        print(f"               chain: {c['chain']}")
        for pid in c["premises"]:
            doc = TKAxiomDoc.get(pid).run()
            label = doc.original if doc else "<not an active axiom>"
            print(f"                 premise {pid} = {label!r}")
        print()

    if not conclusions:
        print("  (nothing newly derivable — the KB's rules/facts imply no >=2-premise conclusions yet.)")


if __name__ == "__main__":
    main()

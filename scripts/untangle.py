#!/usr/bin/env python
# ------------------------------------------------------------------------------------------------
# untangle.py — THE UNTANGLER (roadmap §0 slice 3): KB-wide reductio as sleep-phase belief
# hygiene. Saturates the whole KB through the derivation mirror, collects every absurdity + its
# premise set, and retreats the premises CONVICTED by reductio (the fork-D bar: exactly ONE
# revisable premise among constitution/substrate — the r.a.a. itself convicts it; logic never
# guesses). Undecidable conflicts are left for the wake-time reduct reflex (the brain asks the
# teachers); constitution-level tensions are flagged for the author's hand alone.
#
# Run WHILE THE DAEMONS SLEEP (like recompile.py) — the pass archives docs the running brain
# would be reasoning over. On --apply with convictions it spawns ONE life:dream idea: when he
# wakes, he tells the blog he had a DREAM («while I slept, I untangled something…»).
#
# Dry-run by default (full report, zero writes); --apply to retreat + dream.
#   python scripts/untangle.py            # DRY-RUN
#   python scripts/untangle.py --apply
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io


def main() -> int:
    apply = "--apply" in sys.argv
    print(f"untangle.py — {'APPLYING (retreats enabled)' if apply else 'DRY-RUN (no writes)'}\n")
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    from lib.core.untangle import untangle_pass

    report = untangle_pass(apply=apply)
    print(f"saturation: {report['conflicts']} distinct absurdit{'y' if report['conflicts'] == 1 else 'ies'}\n")

    for e in report["convicted"]:
        verb = "RETREATED" if apply else "would retreat"
        print(f"  ⚖ CONVICTED — {verb} «{e['original']}» ({e['kind']})")
        print(f"      the absurd it forced: {e['absurd']}")
        for dep in e["dependents"]:
            print(f"      cascade: «{dep}» falls with it")
        if not e["postable"]:
            print("      (not postable — this retraction will not be dreamed publicly)")
    for e in report["asked"]:
        print(f"  ？ UNDECIDABLE — {e['absurd']}")
        print(f"      candidates: {'; '.join('«' + c + '»' for c in e['candidates'])}")
        print("      (left for the wake-time reduct reflex — he will ask the teachers)")
    for e in report["constitution"]:
        print(f"  ⚠ CONSTITUTION tension — {e['absurd']}")
        print(f"      rests only on readonly axioms: {'; '.join('«' + p + '»' for p in e['premises'])}")
    for e in report["unresolvable"]:
        print(f"  ∅ UNRESOLVABLE — {e['absurd']} (no doc-backed premise)")

    if apply and report["convicted"]:
        print(f"\nresidual after retreats: {report['residual']} absurdity(ies)")
        from brain import thinking
        if thinking.spawn_dream(report):
            print("the DREAM idea is spawned — he will tell it when he wakes 🌙")
        else:
            print("no publicly-dreamable retraction (provenance gate) — he keeps this night to himself")
    elif not apply:
        print("\ndry-run — pass --apply to retreat the convicted premises and spawn the dream")
    else:
        print("\nnothing convicted — the KB is untangled (or every tangle needs a teacher/the author)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ------------------------------------------------------------------------------------------------
# probe_enriched_soak.py — STEP 5 SCOPING (read-only): where is the enriched-soak fuel, and how big is
# the cascade? Measures the TWO fuel paths so the "grow the rules" decision is data-driven, not abstract.
# Writes NOTHING (reads the recompiled definition zips + the applied is_a tier).
#
#   PATH A — is_a-edge cascade (needs ONLY rules + broadened seeding, no chainer changes):
#     one universal rule about a tier GENUS fires on every tier subject that points to it. The
#     "rule leverage" = genus -> #tier-subjects: writing N rules about the top genera yields ~sum
#     theorems, each with >=2 premises (tier edge + rule). Cheap, bounded, uses the machinery we have.
#   PATH B — property-content fuel (the differentia: "an ability is the quality of being ABLE to
#     PERFORM" -> ability→able, ability→perform). The generative source the roadmap named — but each
#     property fact has a CLASS subject (not a uid), which the chainer does not yet consume, so PATH B
#     needs a property-extractor + a chainer extension (a bigger build). This sizes that fuel.
#
#   python scripts/probe_enriched_soak.py
# ------------------------------------------------------------------------------------------------
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc, TKDerivedRelationDoc
import lib.core.evaluation_harness as H


def _pos(sense):
    for tag in (".n.", ".v.", ".a.", ".s.", ".r."):
        if sense and tag in sense:
            return tag.strip(".")
    return "?"


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    docs = TKDefinitionDoc.find({"archived": False}).to_list()

    bar = "=" * 88
    print(f"\n{bar}\nENRICHED-SOAK SCOPING — where is the fuel?  ({len(docs)} definitions)\n{bar}")

    # ---- PATH A: is_a-edge cascade — rule leverage (genus -> #tier subjects) ----
    tier = TKDerivedRelationDoc.find({"relation": "is_a"}).to_list()
    genus_subjects: dict[str, set] = {}
    for e in tier:
        genus_subjects.setdefault(e.object, set()).add(e.subject)
    leverage = sorted(((g, len(s)) for g, s in genus_subjects.items()), key=lambda x: -x[1])
    total_edges = len(tier)
    print(f"\n— PATH A  is_a-edge cascade (one rule per genus fires on all its tier subjects) —")
    print(f"  tier: {total_edges} edges over {len(genus_subjects)} distinct genera")
    print(f"  rule leverage — top 15 genera by #tier-subjects (each = theorems from ONE rule):")
    for g, n in leverage[:15]:
        print(f"      {g:24} {n:3} subjects")
    for topn in (10, 25, 50, 100):
        yield_ = sum(n for _, n in leverage[:topn])
        print(f"  -> {topn:3} rules (top genera) => ~{yield_} cascade theorems (>=2 premises each)")

    # ---- PATH B: property-content fuel (the differentia) ----
    # every NON-genus leaf carrying a predicate sense is property content about the definition subject.
    # the genus leaf = the first noun->noun copular leaf (already mined as an is_a edge in step 3).
    prop_pos = Counter()
    defs_with_prop = 0
    total_prop = 0
    samples = []
    for d in docs:
        leaves = H._zip_leaves(d.zip.items) if d.zip else []
        genus_seen = False
        props = []
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, pred = s.get("subject"), s.get("predicate")
            if not pred:
                continue
            if not genus_seen and subj and ".n." in (subj or "") and ".n." in pred and subj != pred:
                genus_seen = True   # the genus leaf (step-3 fuel) — skip
                continue
            props.append((subj, pred, s.get("direct")))
            prop_pos[_pos(pred)] += 1
            total_prop += 1
        if props:
            defs_with_prop += 1
            if len(samples) < 10:
                samples.append((d.original, props))

    print(f"\n— PATH B  property-content fuel (the differentia — non-genus predicates) —")
    print(f"  definitions carrying >=1 property leaf: {defs_with_prop}  ({100*defs_with_prop/len(docs):.0f}%)")
    print(f"  total property facts: {total_prop}   predicate POS: {dict(prop_pos)}")
    print(f"  (each is a CLASS-subject property fact — chainer consumes uid-facts + rules today, so PATH B")
    print(f"   needs a property-extractor + a chainer extension to fire; bigger build than PATH A.)")
    print(f"  samples:")
    for orig, props in samples:
        ps = ", ".join(f"{p}" + (f"→{o}" if o else "") for _, p, o in props[:3])
        print(f"    «{orig}»")
        print(f"        props: {ps}")
    print(f"\n{bar}")
    print("READ-ONLY scoping. PATH A = cheap cascade with the machinery we have (rules + broadened seeds);")
    print("PATH B = the deeper generative fuel (property-extractor + chainer extension).")
    print(bar)


if __name__ == "__main__":
    main()

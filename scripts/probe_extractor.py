# ------------------------------------------------------------------------------------------------
# probe_extractor.py — STEP 3 DRY-RUN: the definition→is_a EXTRACTOR + low-trust tier (the FUEL).
# READ-ONLY — measures the tier the extractor would write and the fuel it unlocks, writing NOTHING.
# The GATE + accepted edges come from the SINGLE SOURCE OF TRUTH (lib.core.kb_extract) that the writer
# (scripts/extract_definitions.py) also uses, so the probe (the ruler) can never drift from the writer.
# Reads the STORED (recompiled, sense-faithful) definition zips — no parser, full population in seconds.
#
#   Q1  TIER SIZE — how many clean, deduped is_a edges does the gate accept?
#   Q2  ENRICHMENT — of those, how many are genuinely NEW vs already graph-connected?
#   Q3  SAFETY — the rejection breakdown (redundant / placeholder / cycle / disjoint) + samples.
#   Q4  FUEL — union the tier into the evaluator's is_a reader and re-run wondering: (A) TODAY's
#       autonomous seeds, (B) a breadth PREVIEW seeding from every tier subject.
#
#   python scripts/probe_extractor.py
# ------------------------------------------------------------------------------------------------
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc
import lib.core.evaluation_harness as H
from lib.core.kb_extract import extract_isa_edges, gate_edge, _candidate_edges, _genus_lemma
from lib.llc.evaluator import evaluator_forwardChain
from lib.llc.evaluator.e_relations import relations_disjoint


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    kb = H._load_active_kb()
    bedrock = H._make_relations_reader()  # gate + measure against the TRUSTED graph only
    docs = TKDefinitionDoc.find({"archived": False}).to_list()

    bar = "=" * 88
    print(f"\n{bar}\nDEFINITION -> is_a EXTRACTOR — STEP 3 DRY-RUN  ({len(docs)} active definitions)\n{bar}")

    # ---- Q1/Q2/Q3: the authoritative gate result (shared with the writer) ----
    edges, stats = extract_isa_edges(docs, bedrock)   # deduped, gated accepted edges
    tier: dict[str, list[str]] = {}
    for e in edges:
        tier.setdefault(e["subject"], []).append(e["object"])
    accepted = len(edges)
    tier_subjects = len(tier)

    # enrichment split + genus distribution + tier-3 recoveries, over the ACCEPTED edges
    genus_freq = Counter()
    new_edges, offgraph, recovered_tier3 = 0, 0, 0
    for e in edges:
        genus_freq[_genus_lemma(e["object"])] += 1
        if bedrock(e["subject"]) or bedrock(e["object"]):
            new_edges += 1
        else:
            offgraph += 1
        if relations_disjoint(e["subject"], e["object"], bedrock) is not None:
            recovered_tier3 += 1  # accepted despite a tier-3 (physical/abstract) disjointness

    print(f"\n— Q1/Q2/Q3  EXTRACTION + GATING  (one main-clause is_a edge per definition, deduped) —")
    print(f"  candidate noun->noun genus edges .... {stats['candidate']}")
    print(f"  REDUNDANT (bedrock already derives) .. {stats['redundant']:5}  ({_pct(stats['redundant'], stats['candidate'])})  dropped")
    print(f"  reject: PLACEHOLDER genus ............ {stats['placeholder']:5}  ({_pct(stats['placeholder'], stats['candidate'])})  structural (gloss artifact)")
    print(f"  reject: CYCLE ........................ {stats['cycle']:5}  ({_pct(stats['cycle'], stats['candidate'])})  gated out")
    print(f"  reject: DISJOINT (reliable tiers 1/2)  {stats['disjoint']:5}  ({_pct(stats['disjoint'], stats['candidate'])})  gated out")
    print(f"  ACCEPT -> tier (deduped) ............. {accepted:5}  over {tier_subjects} subjects")
    print(f"      (incl. {recovered_tier3} tier-3 edges the OLD strict gate would have wrongly dropped)")
    print(f"      NEW / graph-connected {new_edges}   off-graph {offgraph}")
    print(f"  genus lemma distribution (top 12 — sanity-check for placeholders that slipped through):")
    print(f"      {', '.join(f'{g}:{n}' for g, n in genus_freq.most_common(12))}")

    # rejection SAMPLES — a light second pass over candidates for a few examples per verdict (diagnostic)
    buckets: dict[str, list] = {"placeholder": [], "cycle": [], "disjoint": []}
    for subj, genus, doc in _candidate_edges(docs):
        v = gate_edge(subj, genus, bedrock)
        if v in buckets and len(buckets[v]) < 8:
            buckets[v].append((subj, genus, doc.original))
    print(f"\n— NEW is_a edges the bedrock graph LACKS (sample of the fuel) —")
    for e in edges[:12]:
        print(f"    {e['subject']:24} is_a {e['object']:24}  «{e['source_original']}»")
    for label, rows in (("PLACEHOLDER (gloss artifacts)", buckets["placeholder"]),
                        ("CYCLE (subject already an ancestor of genus)", buckets["cycle"]),
                        ("DISJOINT (reliable tiers 1/2)", buckets["disjoint"])):
        if rows:
            print(f"\n— rejected {label} —")
            for subj, genus, orig in rows:
                print(f"    {subj:24} is_a {genus:24}  «{orig}»")

    # ---- Q4  FUEL: union the tier into the reader, re-run wondering ----
    def extended(sense):
        base = bedrock(sense)
        extra = tier.get(sense, [])
        return base + [g for g in extra if g not in base]

    print(f"\n{bar}\n— Q4  FUEL — does the tier let wondering derive theorems it couldn't before? —\n{bar}")
    base_theorems = H.kb_wonder({**kb, "relations": bedrock})
    ext_theorems = H.kb_wonder({**kb, "relations": extended})
    base_sigs = {_sig(t) for t in base_theorems}
    new_from_ext = [t for t in ext_theorems if _sig(t) not in base_sigs]
    print(f"\n(A) current autonomous seeds:  bedrock -> {len(base_theorems)} theorems   "
          f"tier-extended -> {len(ext_theorems)}   (+{len(new_from_ext)} new)")
    for t in new_from_ext[:15]:
        print(f"      + {_render(t)}   [{len(t['premises'])} premises]")
    if not new_from_ext:
        print(f"      (none — expected on the tiny 7-rule KB: today's seeds don't reach the new edges.")
        print(f"       the tier's value scales with the rule set + seeding breadth — see (B) + step 5.)")

    rules, facts = kb["rules"], kb["facts"]
    b_sigs, e_sigs = set(), set()
    for reader, sink in ((bedrock, b_sigs), (extended, e_sigs)):
        for subj in tier:
            derived, _ = evaluator_forwardChain(subj, None, rules, reader, facts)
            for d in derived:
                if len(d.get("premises", [])) >= 2:
                    sink.add((subj, d["predicate"], d.get("object"), bool(d.get("negated", False))))
    unlocked = e_sigs - b_sigs
    print(f"\n(B) breadth preview — seed from all {tier_subjects} tier subjects (>=2-premise theorems):")
    print(f"      bedrock -> {len(b_sigs)}   tier-extended -> {len(e_sigs)}   (+{len(unlocked)} unlocked by the tier)")
    for subj, pred, obj, neg in list(unlocked)[:15]:
        print(f"      + {subj} {'NOT ' if neg else ''}{pred}" + (f" {obj}" if obj else ""))
    print(f"\n  NB: fuel yield scales ~ (edges x rules). {accepted} edges meet a {len(rules)}-rule KB today;")
    print(f"      growing the universal-rule set is the multiplier (roadmap step 5, the enriched soak).")
    print(bar)


def _pct(n, d):
    return f"{100*n/d:.1f}%" if d else "0.0%"


def _sig(t):
    return (t["subject"], t["predicate"], t.get("object"), bool(t.get("negated", False)))


def _render(t):
    neg = "NOT " if t.get("negated") else ""
    obj = f" {t['object']}" if t.get("object") else ""
    return f"{t['subject']} {neg}{t['predicate']}{obj}"


if __name__ == "__main__":
    main()

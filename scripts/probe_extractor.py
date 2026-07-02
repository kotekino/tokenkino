# ------------------------------------------------------------------------------------------------
# probe_extractor.py — STEP 3 DRY-RUN: the definition→is_a EXTRACTOR + low-trust tier (the FUEL).
# READ-ONLY — mines the now-clean genus of every definition into candidate is_a edges, GATES them
# against tokeniko's own is_a graph, and MEASURES both the tier and the fuel it unlocks, writing
# NOTHING. Reads the STORED (already-recompiled, sense-faithful) definition zips — no parser, so it
# runs over the FULL population in seconds.
#
# It answers the step-3 questions with numbers:
#   Q1  TIER SIZE — how many is_a edges does the extractor mine from the main copular clause?
#   Q2  ENRICHMENT — of those, how many are genuinely NEW (not already derivable from the bedrock
#       150k-edge is_a graph)? redundant edges add nothing; NEW edges are the enrichment.
#   Q3  SAFETY — the graph-consistency gate (reject-on-doubt): reject any candidate that would create
#       a CYCLE (subject already an is_a ancestor of the genus) or cross a DISJOINT ontological
#       boundary (the poison an is_a edge must never assert). Are the rejections correct?
#   Q4  FUEL — union the clean tier into the is_a reader and re-run wondering: (A) the effect on
#       TODAY's autonomous seeds (individuals + rule-subject classes), and (B) a breadth PREVIEW —
#       seeding the chainer from every tier subject — the "definitions × rules" cascade potential.
#
# Governing principle (locked in the brainstorm): asymmetric risk -> reject-on-doubt. A false is_a
# edge poisons ALL downstream reasoning, so prefer dropping a good edge to admitting a bad one. The
# tier is SEPARATE from the bedrock WordNet graph (a reader UNION), never polluting it.
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
from lib.llc.evaluator.e_relations import relations_subsumes, relations_disjoint


def _is_noun(sense):
    return bool(sense) and ".n." in sense


# reliable disjointness tiers for ADMISSION (see the step-3 dry-run finding): tier 1 (biological
# kingdoms) + tier 2 (organism/artifact/substance) are trustworthy; tier 3 (physical⊥abstract) is
# NOT — WordNet arbitrarily files polysemous nouns on either side, so it false-rejects true
# cross-abstraction edges (agent→cause, breathing→process). We reject a candidate ONLY when the
# disjointness fires at tier 1 or 2 (the finest tier relations_disjoint reports).
_T1 = {"animal.n.01", "plant.n.02", "fungus.n.01", "fungus.n.02", "bacteria.n.01", "microorganism.n.01"}
_T2 = {"organism.n.01", "artifact.n.01", "natural_object.n.01", "substance.n.01"}
_T3 = {"physical_entity.n.01", "abstraction.n.06"}


def _disjoint_tier(note: str) -> int:
    for tok in note.replace(" ⊥", " ").split():
        if tok in _T1:
            return 1
        if tok in _T2:
            return 2
        if tok in _T3:
            return 3
    return 0


# STRUCTURAL "definitional-genus" filter: metalinguistic placeholder heads that are NEVER a real is_a
# hypernym — they signal a gloss ARTIFACT ("a beer is a general NAME for…", "a bitter is English TERM
# for…"), not a taxonomic parent. Conservative by design: only the unambiguously-metalinguistic words,
# so no legitimate abstract genus (process/state/group/part…) is ever dropped.
_PLACEHOLDER_GENERA = {"name", "term", "word", "designation"}


def _genus_lemma(sense: str) -> str:
    return (sense or "").split(".", 1)[0]


# THE EXTRACTOR (pure, over stored senses). For each definition, mine the MAIN copular clause's
# genus as a candidate is_a edge (subject_sense -> genus_sense). Structural gate: noun->noun only
# (the taxonomic spine), main clause only (the FIRST qualifying leaf — no subordinate/relcl genus),
# no self-edge. Returns [(subject_sense, genus_sense, original), ...] — one edge per definition at most.
def extract_edges(docs):
    edges = []
    for d in docs:
        leaves = H._zip_leaves(d.zip.items) if d.zip else []
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, genus = s.get("subject"), s.get("predicate")
            if _is_noun(subj) and _is_noun(genus) and subj != genus:
                edges.append((subj, genus, d.original))
                break  # main clause only
    return edges


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    kb = H._load_active_kb()
    bedrock = kb["relations"]  # cached is_a reader over the 150k-edge WordNet graph
    docs = TKDefinitionDoc.find({"archived": False}).to_list()

    bar = "=" * 88
    print(f"\n{bar}\nDEFINITION -> is_a EXTRACTOR — STEP 3 DRY-RUN  ({len(docs)} active definitions)\n{bar}")

    # ---- extract + gate ----
    raw_edges = extract_edges(docs)
    stats = Counter()
    tier: dict[str, list[str]] = {}          # ACCEPTED edges: subject -> [genus, ...]
    new_samples, offgraph_samples = [], []
    cycle_rej, disjoint_rej, placeholder_rej = [], [], []
    genus_freq = Counter()                   # genus lemma distribution among accepted edges

    for subj, genus, orig in raw_edges:
        stats["candidate"] += 1
        # REDUNDANT: the bedrock graph already derives subject is_a genus -> adds nothing.
        if relations_subsumes(genus, subj, bedrock) is not None:
            stats["redundant"] += 1
            continue
        # STRUCTURAL: a metalinguistic placeholder genus ("…is a general NAME for…") is a gloss
        # artifact, never a real hypernym -> drop for the RIGHT reason (not via coarse disjointness).
        if _genus_lemma(genus) in _PLACEHOLDER_GENERA:
            stats["reject_placeholder"] += 1
            if len(placeholder_rej) < 10:
                placeholder_rej.append((subj, genus, orig))
            continue
        # SAFETY GATE (reject-on-doubt) --------------------------------------------------------
        # CYCLE: subject is already an is_a ancestor of the genus -> subject->genus closes a loop.
        if relations_subsumes(subj, genus, bedrock) is not None:
            stats["reject_cycle"] += 1
            if len(cycle_rej) < 10:
                cycle_rej.append((subj, genus, orig))
            continue
        # DISJOINT: reject only when the disjointness fires at a RELIABLE tier (1 biological kingdoms
        # / 2 organism-artifact-substance). tier 3 (physical⊥abstract) is dropped for admission — it
        # false-rejects true cross-abstraction edges (see the dry-run finding); the trust tier +
        # revocability are the safety net for those, not a coarse ontological boundary.
        witness = relations_disjoint(subj, genus, bedrock)
        if witness is not None and _disjoint_tier(witness[-1]) in (1, 2):
            stats["reject_disjoint"] += 1
            if len(disjoint_rej) < 10:
                disjoint_rej.append((subj, genus, orig))
            continue
        if witness is not None:
            stats["recovered_tier3"] += 1    # would've been rejected under the old strict gate
        # ACCEPT into the low-trust tier ------------------------------------------------------
        tier.setdefault(subj, [])
        if genus not in tier[subj]:
            tier[subj].append(genus)
        genus_freq[_genus_lemma(genus)] += 1
        # sub-classify: NEW (both senses live in the bedrock graph, edge merely absent) vs OFF-GRAPH
        # (subject and/or genus has no is_a edges at all -> unconnected; the edge can't be graph-checked).
        if bedrock(subj) or bedrock(genus):
            stats["accept_new"] += 1
            if len(new_samples) < 15:
                new_samples.append((subj, genus, orig))
        else:
            stats["accept_offgraph"] += 1
            if len(offgraph_samples) < 10:
                offgraph_samples.append((subj, genus, orig))

    accepted = stats["accept_new"] + stats["accept_offgraph"]
    tier_subjects = len(tier)

    print(f"\n— Q1/Q2/Q3  EXTRACTION + GATING  (one main-clause is_a edge per definition) —")
    print(f"  candidate noun->noun genus edges .... {stats['candidate']}")
    print(f"  REDUNDANT (bedrock already derives) .. {stats['redundant']:5}  ({_pct(stats['redundant'], stats['candidate'])})  dropped")
    print(f"  reject: PLACEHOLDER genus ............ {stats['reject_placeholder']:5}  ({_pct(stats['reject_placeholder'], stats['candidate'])})  structural (gloss artifact)")
    print(f"  reject: CYCLE ........................ {stats['reject_cycle']:5}  ({_pct(stats['reject_cycle'], stats['candidate'])})  gated out")
    print(f"  reject: DISJOINT (reliable tiers 1/2)  {stats['reject_disjoint']:5}  ({_pct(stats['reject_disjoint'], stats['candidate'])})  gated out")
    print(f"  ACCEPT -> tier ....................... {accepted:5}  ({_pct(accepted, stats['candidate'])})")
    print(f"      (incl. {stats['recovered_tier3']} tier-3 edges the OLD strict gate would have wrongly dropped)")
    print(f"      of which NEW (graph-connected) ... {stats['accept_new']:5}  <- the enrichment")
    print(f"      of which OFF-GRAPH (unconnected) . {stats['accept_offgraph']:5}  <- can't graph-check; low-confidence")
    print(f"  => low-trust tier: {accepted} edges over {tier_subjects} subjects.")
    print(f"  genus lemma distribution (top 12 — sanity-check for placeholders that slipped through):")
    print(f"      {', '.join(f'{g}:{n}' for g, n in genus_freq.most_common(12))}")

    print(f"\n— NEW is_a edges the bedrock graph LACKS (the fuel; both senses graph-connected) —")
    for subj, genus, orig in new_samples:
        print(f"    {subj:24} is_a {genus:24}  «{orig}»")
    if offgraph_samples:
        print(f"\n— OFF-GRAPH accepted edges (unconnected senses — flag for the trust tier) —")
        for subj, genus, orig in offgraph_samples:
            print(f"    {subj:24} is_a {genus:24}  «{orig}»")
    if placeholder_rej:
        print(f"\n— rejected PLACEHOLDER-genus edges (metalinguistic gloss artifacts — 'a general name for…') —")
        for subj, genus, orig in placeholder_rej:
            print(f"    {subj:24} is_a {genus:24}  «{orig}»")
    if cycle_rej:
        print(f"\n— rejected CYCLE edges (subject already an ancestor of genus — should be correct) —")
        for subj, genus, orig in cycle_rej:
            print(f"    {subj:24} is_a {genus:24}  «{orig}»")
    if disjoint_rej:
        print(f"\n— rejected DISJOINT edges (reliable tiers 1/2 — animal⊥plant, organism⊥artifact) —")
        for subj, genus, orig in disjoint_rej:
            print(f"    {subj:24} is_a {genus:24}  «{orig}»")

    # ---- Q4  FUEL: union the tier into the reader, re-run wondering ----
    def extended(sense):
        base = bedrock(sense)
        extra = tier.get(sense, [])
        return base + [g for g in extra if g not in base]

    print(f"\n{bar}\n— Q4  FUEL — does the tier let wondering derive theorems it couldn't before? —\n{bar}")

    # (A) the effect on TODAY's autonomous seeds (individuals-with-facts + rule-subject classes).
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

    # (B) breadth PREVIEW (a step-5 look-ahead): seed the chainer from EVERY tier subject with the
    # extended graph, count the genuinely-new (>=2-premise) theorems the definitions+rules now imply.
    from lib.llc.evaluator import evaluator_forwardChain
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

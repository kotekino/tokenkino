# ------------------------------------------------------------------------------------------------
# probe_definitions.py — DRY-RUN investigation: what can the ~3,235 definitions actually feed the
# reasoner? (the "definitions-as-rules / rich-soak fuel" question). READ-ONLY — decodes + quantifies,
# writes nothing.
#
# It answers, with numbers, the three questions the brainstorm raised:
#   1. Does the CURRENT extractor mine anything from definitions? (they're existential/generic, not
#      universal, so _extract_rules/_extract_facts should yield ~0 — confirm the gap.)
#   2. How much of the definitions' TAXONOMIC content (subject is_a predicate) is REDUNDANT with the
#      150k-edge is_a graph the chainer already walks? (redundant => mining it as membership rules adds
#      nothing new.)
#   3. How much GENERATIVE content exists (the predicate_nmod differentia) — and how noisy is it?
#
#   python scripts/probe_definitions.py
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
from lib.llc.evaluator.e_relations import relations_subsumes


def _pos(sense):
    for tag in (".n.", ".v.", ".a.", ".s.", ".r."):
        if sense and tag in sense:
            return tag.strip(".")
    return "?"


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    parents = H._make_relations_reader()
    bar = "=" * 80
    print(f"\n{bar}\nDEFINITIONS-AS-RULES — DRY-RUN PROBE  ({len(docs)} active definitions)\n{bar}")

    # --- Q1: does the CURRENT chainer-extractor mine anything from definitions? ---
    rules = H._extract_rules(docs)
    facts = H._extract_facts(docs)
    print(f"\n— Q1  CURRENT extractor yield on definitions —")
    print(f"  _extract_rules -> {len(rules)} rules   _extract_facts -> {len(facts)} facts")
    print(f"  (expected ~0: definitions are existential/generic, not universal or entity-linked → the")
    print(f"   chainer never uses them today. A definition-aware extractor is required.)")

    # --- decode structure ---
    quant = Counter(); nleaves = Counter(); pred_pos = Counter()
    has_genus = 0; has_diff = 0; both_nouns = 0
    redundant = 0; novel_edge = 0; offgraph = 0
    diff_samples, novel_samples, noise_candidates = [], [], []

    for d in docs:
        leaves = H._zip_leaves(d.zip.items) if d.zip else []
        nleaves[len(leaves)] += 1
        for lf in leaves:
            q = getattr(lf, "quantifier", None)
            quant[getattr(q, "value", str(q))] += 1
            s = getattr(lf, "senses", None) or {}
            subj, pred, nmod = s.get("subject"), s.get("predicate"), s.get("predicate_nmod")
            if pred:
                has_genus += 1
                pred_pos[_pos(pred)] += 1
            if nmod:
                has_diff += 1
                if len(diff_samples) < 12:
                    diff_samples.append((d.original, subj, nmod))
            # taxonomic redundancy: is "subject is_a predicate" already derivable from the is_a graph?
            if subj and pred and ".n." in subj and ".n." in pred:
                both_nouns += 1
                if subj == pred:
                    continue
                chain = relations_subsumes(pred, subj, parents)
                if chain is not None:
                    redundant += 1
                elif parents(subj) or parents(pred):
                    novel_edge += 1
                    if len(novel_samples) < 12:
                        novel_samples.append((d.original, subj, pred))
                else:
                    offgraph += 1
                    if len(noise_candidates) < 12:
                        noise_candidates.append((d.original, subj, pred))

    # --- Q2/Q3 report ---
    print(f"\n— STRUCTURE —")
    print(f"  leaves/definition: {dict(nleaves)}")
    print(f"  quantifier distribution: {dict(quant)}")
    print(f"  genus (predicate) present: {has_genus}   differentia (predicate_nmod) present: {has_diff}")
    print(f"  genus POS: {dict(pred_pos)}")

    print(f"\n— Q2  TAXONOMIC REDUNDANCY  (of {both_nouns} noun→noun 'subject is_a predicate' claims) —")
    if both_nouns:
        print(f"  already in is_a graph (REDUNDANT): {redundant}  ({100*redundant/both_nouns:.1f}%)")
        print(f"  NOT in graph but senses known (NEW is_a edge): {novel_edge}  ({100*novel_edge/both_nouns:.1f}%)")
        print(f"  senses off the is_a graph entirely: {offgraph}  ({100*offgraph/both_nouns:.1f}%)")
    print(f"  => membership-from-definitions is mostly REDUNDANT with what the chainer already walks.")

    print(f"\n— Q3  GENERATIVE CONTENT (the differentia — potential NEW fuel, but relational + noisy) —")
    for orig, subj, nmod in diff_samples:
        print(f"    {subj:20} —nmod→ {nmod:20}   «{orig}»")

    if novel_samples:
        print(f"\n— NEW is_a edges the graph LACKS (a definition claims subj is_a pred, graph disagrees) —")
        for orig, subj, pred in novel_samples:
            print(f"    {subj:20} is_a {pred:20}   «{orig}»  [review: real gap or WSD noise?]")
    if noise_candidates:
        print(f"\n— OFF-GRAPH senses (likely WSD noise / rare senses — the gloss-quality risk) —")
        for orig, subj, pred in noise_candidates:
            print(f"    {subj:20} is_a {pred:20}   «{orig}»")
    print(bar)


if __name__ == "__main__":
    main()

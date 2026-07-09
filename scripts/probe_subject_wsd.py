# ------------------------------------------------------------------------------------------------
# probe_subject_wsd.py — STEP 5 SURVEY (READ-ONLY): the subject-WSD error rate + blast radius.
#
# The definitions were framed by glosses.py as "a {word} is {clean_gloss(synset.definition())}" from a
# KNOWN WordNet synset — so inverting the gloss text against the word's synsets recovers the TRUE
# subject sense per definition (exact ground truth, not a sample estimate). This probe:
#
#   A. GROUND TRUTH + ERROR RATE — for every active noun-frame definition, recover the true synset
#      (gloss-inversion) and compare with the compiled zip's subject sense. Also reports whether the
#      truth is even EXPRESSIBLE by WSD (is it among the tokeniko dictionary's senses of the word?).
#   B. LIVE-TIER BLAST RADIUS — how many of the applied derived_relations edges (genus-extract-v1)
#      and derived_rules (sufficiency-v1) rest on a mis-sensed subject (poisoned LIVE fuel).
#   C. DIFFERENTIA DRY-RUN — extract_differentia_rules over the active definitions (never applied):
#      volume + how many accepted rules would carry a mis-sensed subject.
#   D. HARDENING SIMULATION — per error, which strategy would fix it:
#        pin      — gloss-pinning at ingestion (truth recovered -> pin the subject sense; defs only)
#        graph    — a subject-side untangle (a sense of the same word that the compiled genus
#                   subsumes in bedrock — the mirror of c_untangle's genus rule)
#      and whether the current gate ALREADY rejects the poisoned edge (disjoint/redundant/...).
#
# READ-ONLY — writes nothing, mutates nothing.
#   python scripts/probe_subject_wsd.py            # full census
#   VERBOSE=1 python scripts/probe_subject_wsd.py  # + every error listed
# ------------------------------------------------------------------------------------------------
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc, TKDerivedRelationDoc, TKDerivedRuleDoc, TKDictionaryDoc
from lib.core.kb_extract import _zip_leaves, extract_differentia_rules, gate_edge
from lib.core.evaluation_harness import _make_relations_reader
from lib.llc.evaluator.e_relations import relations_subsumes

VERBOSE = os.getenv("VERBOSE") == "1"
BAR = "=" * 100

# the gloss-inversion (clean_gloss / recover_truth) lives in the PIN writer — one source of truth
# for probe + writer, same pattern as the kb_extract gates.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pin_definition_senses import recover_truth  # noqa: E402


def first_subject_leaf(zip_doc):
    """the first leaf carrying a subject sense (mirrors the extractors' main-clause read)."""
    if zip_doc is None:
        return None
    for leaf in _zip_leaves(zip_doc.items):
        s = leaf.senses or {}
        if s.get("subject"):
            return leaf
    return None


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    parents = _make_relations_reader()

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    print(f"\n{BAR}\nSUBJECT-WSD SURVEY  ({len(docs)} active definitions)\n{BAR}")

    # in-memory dictionary word→senses (is the truth even expressible by WSD?)
    dict_senses: dict[str, set] = {}
    for d in TKDictionaryDoc.find({}).to_list():
        dict_senses.setdefault((d.word or "").lower(), set()).add(d.sense)

    # ---------------- A. ground truth + error rate ----------------
    stats = Counter()
    errors = []          # (doc, word, truth, compiled, genus_sense)
    truth_by_id = {}     # def id -> (truth|None, compiled|None, frame)
    for doc in docs:
        word, truth, fr = recover_truth(doc.original)
        leaf = first_subject_leaf(doc.zip)
        compiled = (leaf.senses or {}).get("subject") if leaf else None
        genus = (leaf.senses or {}).get("predicate") if leaf else None
        truth_by_id[str(doc.id)] = (truth, compiled, fr)
        if fr == "other":
            stats["frame_other"] += 1
            continue
        if fr == "adj":
            stats["frame_adj"] += 1
            continue
        stats["frame_noun"] += 1
        if truth is None:
            stats["unrecovered"] += 1
            continue
        if compiled is None:
            stats["no_subject_sense"] += 1
            continue
        if compiled == truth:
            stats["match"] += 1
            continue
        stats["MISMATCH"] += 1
        if truth not in dict_senses.get(word, set()):
            stats["mismatch_truth_not_in_dictionary"] += 1
        errors.append((doc, word, truth, compiled, genus))

    n_noun = stats["frame_noun"]
    n_judged = stats["match"] + stats["MISMATCH"]
    print(f"\nA. GROUND TRUTH (gloss-inversion) + ERROR RATE")
    print(f"  noun-frame definitions ....... {n_noun}   (adj {stats['frame_adj']}, other {stats['frame_other']})")
    print(f"  truth unrecovered ............ {stats['unrecovered']}  (gloss text no longer matches any synset)")
    print(f"  no compiled subject sense .... {stats['no_subject_sense']}")
    print(f"  judged (truth vs compiled) ... {n_judged}")
    print(f"    subject CORRECT ............ {stats['match']}")
    print(f"    subject MIS-SENSED ......... {stats['MISMATCH']}"
          + (f"   ({stats['MISMATCH']/n_judged:.1%} of judged)" if n_judged else ""))
    print(f"      of which truth NOT even in dictionary (WSD could never pick it): {stats['mismatch_truth_not_in_dictionary']}")

    # ---------------- B. live-tier blast radius ----------------
    print(f"\nB. LIVE-TIER BLAST RADIUS")
    tier_edges = TKDerivedRelationDoc.find({}).to_list()
    poisoned_edges = []
    for e in tier_edges:
        truth, compiled, fr = truth_by_id.get(e.source_id, (None, None, None))
        if truth is not None and compiled is not None and truth != compiled and e.subject == compiled:
            poisoned_edges.append(e)
    print(f"  derived_relations edges ...... {len(tier_edges)}   poisoned subject: {len(poisoned_edges)}"
          + (f"  ({len(poisoned_edges)/len(tier_edges):.1%})" if tier_edges else ""))
    for e in poisoned_edges[:15]:
        truth, _, _ = truth_by_id[e.source_id]
        print(f"    {e.subject:26} is_a {e.object:24} TRUE subj: {truth:28} «{e.source_original[:48]}»")

    suff_rules = TKDerivedRuleDoc.find({"method": "sufficiency-v1"}).to_list()
    poisoned_suff = []
    for r in suff_rules:
        truth, compiled, fr = truth_by_id.get(r.source_id, (None, None, None))
        if truth is not None and compiled is not None and truth != compiled and r.subject == compiled:
            poisoned_suff.append((r, truth))
    print(f"  sufficient rules ............. {len(suff_rules)}   poisoned class: {len(poisoned_suff)}"
          + (f"  ({len(poisoned_suff)/len(suff_rules):.1%})" if suff_rules else ""))
    for r, truth in poisoned_suff[:10]:
        print(f"    concludes {r.subject:24} TRUE class: {truth:28} «{(r.source_original or '')[:48]}»")

    # ---------------- C. differentia dry-run (never applied) ----------------
    print(f"\nC. DIFFERENTIA DRY-RUN (the unapplied tier)")
    diff_rules, diff_stats = extract_differentia_rules(docs, parents)
    print(f"  gate stats: {dict(diff_stats)}")
    poisoned_diff = []
    for r in diff_rules:
        truth, compiled, fr = truth_by_id.get(r["source_id"], (None, None, None))
        if truth is not None and compiled is not None and truth != compiled and r["subject"] == compiled:
            poisoned_diff.append((r, truth))
    print(f"  accepted rules ............... {len(diff_rules)}   poisoned subject: {len(poisoned_diff)}"
          + (f"  ({len(poisoned_diff)/len(diff_rules):.1%})" if diff_rules else ""))
    for r, truth in poisoned_diff[:10]:
        print(f"    all {r['subject']:24} {r['predicate']:20} {str(r['object'] or ''):18} TRUE subj: {truth}")

    # ---------------- D. hardening simulation ----------------
    print(f"\nD. HARDENING SIMULATION (per mis-sensed noun definition)")
    fix = Counter()
    rows = []
    for doc, word, truth, compiled, genus in errors:
        # strategy 1: gloss-pin (defs only) — truth recovered, so always fixable
        pin_ok = True
        # strategy 2: graph subject-untangle — a sense of the same word the compiled GENUS subsumes
        graph_ok = False
        if genus and ".n." in (genus or ""):
            for cand in dict_senses.get(word, set()):
                if ".n." in cand and cand != compiled and relations_subsumes(genus, cand, parents):
                    graph_ok = True
                    break
        # does the CURRENT gate already reject the poisoned edge?
        gate_verdict = gate_edge(compiled, genus, parents) if genus and ".n." in (genus or "") else "n/a"
        fix["pin"] += pin_ok
        fix["graph"] += graph_ok
        fix[f"gate:{gate_verdict}"] += 1
        rows.append((word, truth, compiled, genus, graph_ok, gate_verdict))

    n_err = len(errors)
    print(f"  mis-sensed definitions ....... {n_err}")
    print(f"  fixed by gloss-PINNING ....... {fix['pin']}  (ingestion-time; definitions only)")
    print(f"  fixed by graph subject-untangle {fix['graph']}  (general; needs the true edge in bedrock + sense in dictionary)")
    print(f"  current gate verdict on the poisoned edge: "
          + ", ".join(f"{k.split(':',1)[1]}={v}" for k, v in sorted(fix.items()) if k.startswith("gate:")))
    shown = rows if VERBOSE else rows[:20]
    for word, truth, compiled, genus, graph_ok, gate_verdict in shown:
        print(f"    {word:16} true={truth:26} got={compiled:22} genus={str(genus):22}"
              f" graph_fix={'Y' if graph_ok else '-'} gate={gate_verdict}")
    if not VERBOSE and n_err > 20:
        print(f"    ... {n_err - 20} more (VERBOSE=1 to list all)")

    print(f"\n{BAR}\nREAD-ONLY — nothing written.\n{BAR}")


if __name__ == "__main__":
    main()

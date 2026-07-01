# ------------------------------------------------------------------------------------------------
# probe_untangle.py — STEP 1 DRY-RUN: the graph-constrained GENUS untangle (definitions-as-rules).
# READ-ONLY — re-parses a sample of definitions, applies the untangle to each main "X is a ⟨genus⟩"
# clause, and MEASURES the effect before committing to a full recompile:
#   OVERRIDDEN      — the genus sense was wrong (homophony) and is recovered to the graph-consistent
#                     sense (e.g. ear: electric_organ.n.01 -> organ.n.01). the WIN.
#   kept_new_edge   — no sense of the genus word is an ancestor of the subject -> a genuine NEW is_a
#                     edge (air -> mixture); LEFT UNTOUCHED (we must not nuke real enrichment).
#   kept_redundant  — the genus was already a graph-consistent ancestor; LEFT UNTOUCHED.
# Correctness is guaranteed by construction: an override only ever lands on a sense that IS an is_a
# ancestor of the subject (so it can never invent a worse edge).
#
#   python scripts/probe_untangle.py            # N=120 sample
#   N=300 python scripts/probe_untangle.py
# ------------------------------------------------------------------------------------------------
import os
import sys
import copy
import random
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io, get_tokeniko
from lib.core.models import TKDefinitionDoc, TKDictionaryDoc
import lib.core.evaluation_harness as H
from lib.llc.evaluator.e_relations import relations_subsumes
from lib.llc.parser import parser, parser_init
from lib.llc.compiler import compiler_compile


def _sense_num(s):
    try:
        return int(s.rsplit(".", 1)[1])
    except Exception:
        return 99


_dict_cache: dict[str, list] = {}
def senses_of(word):
    w = (word or "").lower()
    if w not in _dict_cache:
        _dict_cache[w] = [d.sense for d in TKDictionaryDoc.find({"word": w}).to_list()]
    return _dict_cache[w]


# THE UNTANGLE (pure). For "an X is a ⟨genus⟩…", disambiguate the genus by tokeniko's OWN taxonomy:
# among the senses the genus WORD can denote, prefer the one that is an is_a ancestor of the subject.
# Only OVERRIDE when the current pick is NOT consistent but a consistent alternative exists — so it
# fixes homophony (ear→electric_organ⇒organ) yet leaves genuine new edges (air→mixture) and
# already-correct edges alone. Noun→noun genus only (the taxonomic spine).
def untangle_genus(subject_sense, genus_token, genus_sense, parents):
    if not subject_sense or not genus_sense:
        return genus_sense
    if ".n." not in subject_sense or ".n." not in genus_sense:
        return genus_sense
    cands = list(senses_of(genus_token))
    if genus_sense not in cands:
        cands.append(genus_sense)
    consistent = [c for c in cands if c != subject_sense and relations_subsumes(c, subject_sense, parents)]
    if not consistent:
        return genus_sense                       # genuine NEW edge / off-graph -> keep parser's choice
    if genus_sense in consistent:
        return genus_sense                       # already consistent -> keep
    return min(consistent, key=_sense_num)       # override -> most-frequent consistent sense


def _llc_leaves(items):
    out = []
    for it in items:
        c = it.content
        if isinstance(c, list):
            out += _llc_leaves(c)
        elif c is not None:
            out.append(c)
    return out


def main():
    _, _, ai = init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
                       os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    parser_init()
    tok = get_tokeniko()
    parents = H._make_relations_reader()

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    random.seed(3)
    random.shuffle(docs)
    N = int(os.getenv("N", "120"))
    sample = docs[:N]
    # make sure the canonical homophony case is in the sample
    ear = TKDefinitionDoc.find_one({"original": {"$regex": "^an ear is"}}).run()
    if ear and all(d.id != ear.id for d in sample):
        sample.append(ear)

    stats = Counter()
    overrides, bad = [], []
    for d in sample:
        try:
            rec = parser(d.original, tok, tok, ai)
            llc, _ = compiler_compile(copy.deepcopy(rec))
        except Exception:
            stats["parse_error"] += 1
            continue
        ents = {e.id: e for e in llc.entities}
        content = next((c for c in _llc_leaves(llc.items) if c.subject and c.predicate), None)
        if content is None:
            stats["no_copula"] += 1
            continue
        subj = ents.get(content.subject.id)
        pred = ents.get(content.predicate.id)
        if not subj or not pred or not subj.sense or not pred.sense:
            stats["missing"] += 1
            continue
        stats["evaluated"] += 1
        new = untangle_genus(subj.sense, pred.token, pred.sense, parents)
        if new == pred.sense:
            if ".n." in subj.sense and ".n." in pred.sense:
                if relations_subsumes(pred.sense, subj.sense, parents):
                    stats["kept_redundant"] += 1
                else:
                    stats["kept_new_edge"] += 1
            else:
                stats["kept_nonnoun"] += 1
        else:
            stats["OVERRIDDEN"] += 1
            recovered = bool(relations_subsumes(new, subj.sense, parents))
            (overrides if recovered else bad).append((d.original, subj.sense, pred.token, pred.sense, new))

    bar = "=" * 84
    print(f"\n{bar}\nGENUS UNTANGLE — DRY-RUN  (sample {len(sample)})\n{bar}")
    print("— counts —")
    for k in ["evaluated", "OVERRIDDEN", "kept_redundant", "kept_new_edge", "kept_nonnoun",
              "no_copula", "missing", "parse_error"]:
        if stats[k]:
            print(f"   {k:16} {stats[k]}")
    print(f"\n— OVERRIDES (homophony fixed → recovered to a graph-consistent genus) —")
    for orig, subj, tok_, old, new in overrides[:25]:
        print(f"   {subj:22} genus '{tok_}': {old:22} -> {new:22}")
        print(f"        «{orig}»")
    if bad:
        print(f"\n— *** OVERRIDES THAT DID NOT LAND ON AN ANCESTOR (should be empty!) *** —")
        for row in bad:
            print(f"   {row}")
    print(f"\n— kept_new_edge = genuine new is_a edges LEFT UNTOUCHED (air→mixture class): {stats['kept_new_edge']}")
    print(bar)


if __name__ == "__main__":
    main()

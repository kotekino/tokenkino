# ------------------------------------------------------------------------------------------------
# probe_differentia.py — STEP 5.1 DRY-RUN: mine the definitions' DIFFERENTIA into candidate universal
# PROPERTY rules ("a carnivore is an animal that eats meat" -> "all carnivores eat meat"), and MEASURE
# the yield + the SPURIOUS rate before building the extractor. READ-ONLY (reads the recompiled zips +
# the is_a graph); writes nothing.
#
# The generative fuel of the enriched soak: a definition "an X is a <genus> that <differentia>" gives a
# universal rule about X (the differentia), which cascades DOWN the is_a hierarchy to X's subclasses
# (>=2 premises: the subclass's is_a edge + this rule). Analytic (true by the vocabulary's own defs).
#
# THE GATE HYPOTHESIS (to validate on real samples, reject-on-doubt): the differentia binds to the
# CLASS X only when the GENUS is CONCRETE (under physical_entity). When the genus is an ABSTRACT
# NOMINALIZATION (under abstraction.n.06: quality/act/state/trait/right...), the differentia describes
# the BEARER, not X ("an ability is the QUALITY of being able to PERFORM" -> "all abilities perform" is
# WRONG — the bearer performs). "concrete vs abstract" is read from the is_a graph, not a word list.
#
#   python scripts/probe_differentia.py
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
from lib.llc.evaluator.e_relations import relations_isa_ancestors


def _pos(sense):
    for tag in (".n.", ".v.", ".a.", ".s.", ".r."):
        if sense and tag in sense:
            return tag.strip(".")
    return "?"


def _lemma(sense):
    return (sense or "").split(".", 1)[0]


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    parents = H._make_relations_reader()   # bedrock is_a graph (abstractness check)
    docs = TKDefinitionDoc.find({"archived": False}).to_list()

    # is the genus ABSTRACT (under abstraction.n.06) vs CONCRETE (under physical_entity.n.01)?
    _abstract_cache: dict[str, bool] = {}
    def is_abstract(sense):
        if sense not in _abstract_cache:
            anc = set(relations_isa_ancestors(sense, parents).keys()) | {sense}
            _abstract_cache[sense] = ("abstraction.n.06" in anc) and ("physical_entity.n.01" not in anc)
        return _abstract_cache[sense]

    stats = Counter()
    clean, abstract_rej, circular_rej, noun_rej, noobj_rej = [], [], [], [], []

    for d in docs:
        leaves = H._zip_leaves(d.zip.items) if d.zip else []
        # the genus leaf = first noun->noun copular; X = its subject, genus = its predicate
        X = genus = None
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, pred = s.get("subject"), s.get("predicate")
            if subj and pred and ".n." in subj and ".n." in pred and subj != pred:
                X, genus = subj, pred
                genus_leaf = lf
                break
        if not X or not genus:
            continue
        # differentia = other leaves whose subject is the CLASS X (its own asserted properties)
        for lf in leaves:
            if lf is genus_leaf:
                continue
            s = getattr(lf, "senses", None) or {}
            if s.get("subject") != X:
                continue
            pred = s.get("predicate")
            if not pred or pred == genus:
                continue
            stats["candidate"] += 1
            direct = s.get("direct")
            pos = _pos(pred)
            row = (X, pred, direct, genus, d.original)
            # GATE 1 — abstract-nominalization genus -> differentia is about the bearer, not X
            if is_abstract(genus):
                stats["abstract_genus"] += 1
                if len(abstract_rej) < 12:
                    abstract_rej.append(row)
                continue
            # GATE 2 — circular differentia (predicate morphologically ~ X): "ability -> able"
            if _lemma(pred)[:4] and _lemma(pred)[:4] == _lemma(X)[:4]:
                stats["circular"] += 1
                if len(circular_rej) < 8:
                    circular_rej.append(row)
                continue
            # GATE 3 — NOUN differentia = a genus-disjunction alt ("a structure OR object") or appositive
            if pos == "n":
                stats["noun"] += 1
                if len(noun_rej) < 10:
                    noun_rej.append(row)
                continue
            # GATE 4 — a VERB without a direct object is a passive reduced-relative ("equipped WITH",
            # "characterized BY") or an intransitive whose agency we can't confirm from the zip -> drop
            # (reject-on-doubt; verb recovery is parked = needs parser voice/agency detection). An
            # AGENTIVE transitive verb carries its direct object ("eat MEAT", "contain LIQUID").
            if pos == "v" and not direct:
                stats["verb_noobj"] += 1
                if len(noobj_rej) < 12:
                    noobj_rej.append(row)
                continue
            # CLEAN: an adjective ("X is sweet") OR a transitive verb WITH its object ("X contains Y")
            stats["clean"] += 1
            stats[f"clean_{pos}"] += 1
            if len(clean) < 25:
                clean.append(row)

    bar = "=" * 90
    print(f"\n{bar}\nDIFFERENTIA → universal PROPERTY RULES — STEP 5.1 DRY-RUN  ({len(docs)} definitions)\n{bar}")
    print(f"\n— candidate differentia (property leaves whose subject is the definiendum class X) —")
    print(f"  candidates ............... {stats['candidate']}")
    print(f"  reject ABSTRACT genus .... {stats['abstract_genus']}  (differentia about the bearer, not X)")
    print(f"  reject NOUN differentia .. {stats['noun']}  (genus-disjunction alt / appositive noise)")
    print(f"  reject VERB w/o object ... {stats['verb_noobj']}  (passive reduced-relative / unconfirmed intransitive — PARKED)")
    print(f"  reject CIRCULAR .......... {stats['circular']}  (predicate ~ X, e.g. ability→able)")
    print(f"  CLEAN rules .............. {stats['clean']}   POS: v(+obj)={stats['clean_v']} a={stats['clean_a']} s={stats['clean_s']}")

    print(f"\n— CLEAN candidate rules ('all X <differentia>') — eyeball for quality —")
    for X, pred, obj, genus, orig in clean:
        rule = f"all {_lemma(X)} {_lemma(pred)}" + (f" {_lemma(obj)}" if obj else "")
        print(f"    {rule:40} [genus {genus}]  «{orig}»")

    print(f"\n— rejected VERB-w/o-object (passive/intransitive — the PARKED recovery set) —")
    for X, pred, obj, genus, orig in noobj_rej:
        print(f"    all {_lemma(X)} {_lemma(pred):16} [genus {genus}]  «{orig}»")

    print(f"\n— rejected NOUN-differentia (genus-disjunction / appositive noise) —")
    for X, pred, obj, genus, orig in noun_rej:
        print(f"    all {_lemma(X)} {_lemma(pred):16} «{orig}»")
    print(bar)


if __name__ == "__main__":
    main()

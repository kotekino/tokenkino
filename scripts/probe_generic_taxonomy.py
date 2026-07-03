# ------------------------------------------------------------------------------------------------
# probe_generic_taxonomy.py — STEP 2 DRY-RUN PROBE (Brain v1.1): generic taxonomy chains.
#
# READ-ONLY. Finding #1: a GENERIC copular noun predication ("a cat is a mammal") reaches neither
# _extract_rules (UNIVERSAL only) nor _extract_facts (identity-linked individuals only) — it is
# silently dropped. Step 2 turns that shape into a SOURCE-TRUSTED is_a edge through the SAME
# gate_edge as the definition tier. This probe measures, before anything is built:
#
#   PART 1 — leaf census of the ACTIVE axioms: today's fate of every leaf (rule / fact / DROPPED).
#   PART 2 — the step-2 extractor under BOTH quantifier policies (GENERIC-only vs +EXISTENTIAL),
#            since "a/an" and "some" both compile to EXISTENTIAL: the generic indefinite and the
#            true existential are indistinguishable in today's zip. Data decides the policy.
#   PART 3 — chain-impact diff: the REAL forward-chainer (kb_wonder-style seeds), baseline bedrock
#            vs bedrock ∪ the accepted new edges. The diff = what would NEWLY chain. No simulation.
#   PART 4 (--compile) — a synthetic battery through the real parser (heavy: spaCy/Stanza), dumping
#            the compiled leaf shape of the generic-vs-existential test sentences.
#
#   python scripts/probe_generic_taxonomy.py             # parts 1–3 (parser-free, fast)
#   python scripts/probe_generic_taxonomy.py --compile   # + part 4 (loads the full pipeline)
# ------------------------------------------------------------------------------------------------
import os
import sys

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko")
sys.path.insert(0, PKG)
from dotenv import load_dotenv
load_dotenv(os.path.join(PKG, ".env"))

from lib.core.io import init_io
from lib.core.models import TKAxiomDoc
from lib.core.tk import TKQuantifier
from lib.core.kb_extract import extract_generic_isa_edges, gate_edge
from lib.core.evaluation_harness import (
    _make_relations_reader, _zip_leaves, _extract_rules, _extract_facts,
)
from lib.llc.evaluator.e_chaining import evaluator_forwardChain

BAR = "=" * 96


def _leaf_line(lf) -> str:
    s = getattr(lf, "senses", None) or {}
    ids = getattr(lf, "identities", None) or {}
    q = getattr(lf, "quantifier", None)
    neg = " NEG" if getattr(lf, "negated", False) else ""
    subj = ids.get("subject") or s.get("subject") or "-"
    return (f"[{getattr(q, 'value', q):11}]{neg} subj={subj} "
            f"pred={s.get('predicate') or '-'} dir={s.get('direct') or '-'}")


def _fate(lf) -> str:
    # mirrors the POST-step-2 extraction reality (_extract_rules widened + the edge extractor)
    s = getattr(lf, "senses", None) or {}
    ids = getattr(lf, "identities", None) or {}
    q = getattr(lf, "quantifier", None)
    subj, pred = s.get("subject"), s.get("predicate")
    if q == TKQuantifier.UNIVERSAL and subj and pred:
        return "RULE (universal)"
    if ids.get("subject") and pred:
        return "FACT (individual)"
    if subj and pred and q in (TKQuantifier.GENERIC, TKQuantifier.INDEFINITE, TKQuantifier.NEGATIVE):
        if ".n." in pred and not s.get("direct"):
            return ("EDGE candidate (generic copular)" if q != TKQuantifier.NEGATIVE
                    else "disjointness candidate (future)")
        return "RULE (generic)" if q != TKQuantifier.NEGATIVE else "RULE (negative)"
    if pred and not subj and not ids.get("subject"):
        return "prop-conditioned operand / senseless-subject"
    return "DROPPED"


def part1_census(axioms):
    print(f"\n{BAR}\nPART 1 — leaf census of the {len(axioms)} active axioms (today's fate)\n{BAR}")
    fates = {}
    for doc in axioms:
        leaves = _zip_leaves(doc.zip.items) if doc.zip else []
        lines = []
        for lf in leaves:
            f = _fate(lf)
            fates[f] = fates.get(f, 0) + 1
            lines.append(f"      {_leaf_line(lf)}  ->  {f}")
        flag = " *" if any("DROPPED" in ln for ln in lines) else ""
        print(f"  «{doc.original}»{flag}")
        for ln in lines:
            print(ln)
    print("\n  totals:")
    for f, n in sorted(fates.items(), key=lambda kv: -kv[1]):
        print(f"    {n:4}  {f}")


def part2_policies(axioms, bedrock):
    # the LIVE policy (GENERIC + INDEFINITE, the extractor default — the "a/an" split landed)
    edges, stats = extract_generic_isa_edges(axioms, bedrock)
    print(f"\n{BAR}\nPART 2 — step-2 extractor, policy = GENERIC+INDEFINITE (live default)\n{BAR}")
    for k in ("shape", "universal_rule", "individual_fact", "quantifier_skip",
              "question_skip", "negated_skip", "candidate",
              "redundant", "placeholder", "cycle", "disjoint"):
        if stats.get(k):
            print(f"  {k:16} {stats[k]}")
    print(f"  ACCEPT -> edges .. {len(edges)}  (in-memory, trust=0.9)")
    for e in edges:
        print(f"    {e['subject']:26} is_a {e['object']:26}  «{e['source_original']}»")
    return edges


def part3_chain_diff(axioms, bedrock, edges):
    print(f"\n{BAR}\nPART 3 — chain-impact diff (real forward-chainer): bedrock vs bedrock ∪ {len(edges)} new edges\n{BAR}")
    if not edges:
        print("  no accepted edges -> nothing to diff.")
        return
    rules = _extract_rules(axioms)
    facts = _extract_facts(axioms)
    new_children = {}
    for e in edges:
        new_children.setdefault(e["subject"], []).append(e["object"])

    def union_parents(sense):
        return list(dict.fromkeys(list(bedrock(sense)) + new_children.get(sense, [])))

    def edge_source(subject, object):
        if object in new_children.get(subject, []):
            return f"{subject}|is_a|{object}"
        return None

    # kb_wonder-style seeds: individuals with facts, rule subjects, + the new edges' subjects
    seeds, seen = [], set()
    for f in facts:
        uid = f.get("subject_uid")
        if uid and uid not in seen:
            seen.add(uid)
            seeds.append((uid, uid, None))
    for r in rules:
        cs = r.get("subject")
        if cs and cs not in seen:
            seen.add(cs)
            seeds.append((cs, None, cs))
    for e in edges:
        if e["subject"] not in seen:
            seen.add(e["subject"])
            seeds.append((e["subject"], None, e["subject"]))

    def run(parents, es):
        out = {}
        for subject, uid, sense in seeds:
            derived, _ = evaluator_forwardChain(sense, uid, rules, parents, facts, edge_source=es)
            for d in derived:
                if len(d.get("premises", [])) < 2:      # kb_wonder's novelty gate
                    continue
                sig = (subject, d["predicate"], d.get("object"), bool(d.get("negated", False)))
                out.setdefault(sig, d)
        return out

    base = run(bedrock, None)
    union = run(union_parents, edge_source)
    new = {sig: d for sig, d in union.items() if sig not in base}
    print(f"  baseline conclusions (>=2 premises): {len(base)}   with new edges: {len(union)}   NEW: {len(new)}")
    for (subject, pred, obj, neg), d in sorted(new.items()):
        o = f" {obj}" if obj else ""
        print(f"    NEW  {subject}  {'NOT ' if neg else ''}{pred}{o}")
        print(f"         chain: {d['chain']}")


_BATTERY = [
    ("a cat is a mammal", "finding-#1 shape; indefinite generic (expect redundant vs bedrock)"),
    ("a thinker is a mind", "indefinite generic, likely non-redundant — the payoff shape"),
    ("cats are mammals", "bare plural — the pure GENERIC quantifier"),
    ("some humans are killers", "TRUE existential — must NOT edge (cycle-gate exhibit?)"),
    ("some birds are pets", "TRUE existential the gate cannot catch — the policy risk, honestly"),
    ("a whale is a fish", "FALSE generic the gate cannot catch — known limit, low-trust+revocable"),
    ("the cat is a mammal", "DEFINITE subject — excluded by policy"),
    ("a dog is not a cat", "negated generic — excluded (future disjointness candidate)"),
    ("humans create their gods", "generic but non-copular (verb) — excluded by shape"),
]


def part4_compile(bedrock):
    print(f"\n{BAR}\nPART 4 — synthetic battery through the real parser (in-memory, no writes)\n{BAR}")
    from lib.llc.parser import parser_init
    parser_init()
    from lib.core.io import get_tokeniko
    from api.services import AxiomService
    service = AxiomService(get_tokeniko(), None)
    for sentence, why in _BATTERY:
        print(f"\n  «{sentence}»   ({why})")
        try:
            fields = service.compile_fields(sentence)
        except Exception as error:
            print(f"      FAILED to compile: {error!r}")
            continue
        for lf in _zip_leaves(fields["zip"].items):
            s = getattr(lf, "senses", None) or {}
            subj, pred = s.get("subject"), s.get("predicate")
            verdict = "-"
            if subj and pred and ".n." in subj and ".n." in pred and subj != pred and not s.get("direct"):
                verdict = gate_edge(subj, pred, bedrock)
            print(f"      {_leaf_line(lf)}  gate={verdict}")


def main():
    do_compile = "--compile" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    axioms = TKAxiomDoc.find({"archived": False}).to_list()
    bedrock = _make_relations_reader()   # gate + diff baseline judge against the TRUSTED graph only

    part1_census(axioms)
    edges = part2_policies(axioms, bedrock)
    part3_chain_diff(axioms, bedrock, edges)
    if do_compile:
        part4_compile(bedrock)
    print(f"\n{BAR}\nDRY-RUN complete — nothing written.\n{BAR}")


if __name__ == "__main__":
    main()

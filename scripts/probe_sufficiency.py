# ------------------------------------------------------------------------------------------------
# probe_sufficiency.py — Brain v1.1 STEP 4 DRY-RUN: what would definitional SUFFICIENCY extract?
#
# READ-ONLY census over the live definitions. The mining + gate live in
# lib.core.kb_extract.extract_sufficient_rules (the single source of truth — this probe and the
# writer scripts/extract_sufficiency.py call the SAME function, so ruler and writer can never
# drift). The rationale — the drop-disjuncts-never-conjuncts soundness rule, the genus-as-conjunct
# trap defusal — is documented on the extractor itself.
#
# What this adds over the writer's dry-run: the structural census (definiendum POS / clause shape)
# and the RECOGNITION TEASER (which rules could fire on the known individuals, as a loose
# property-lemma upper bound — the real chainer additionally requires the genus in the closure and
# strict object match, so the true count is far lower; recognition pays off as experience grows).
#
#   python scripts/probe_sufficiency.py            # full census + samples + the teaser
# ------------------------------------------------------------------------------------------------
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKAxiomDoc, TKDefinitionDoc
from lib.core.evaluation_harness import _make_relations_reader
from lib.core.kb_extract import _pos, _zip_leaves, extract_facts, extract_sufficient_rules


def _lemma(s):
    return (s or "").split(".", 1)[0]


def main():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    bedrock = _make_relations_reader()

    bar = "=" * 96
    print(f"\n{bar}\nSTEP-4 SUFFICIENCY PROBE  [read-only]  ({len(docs)} active definitions)\n{bar}")

    # ---- census A: structure -------------------------------------------------------------------
    pos_of_main = Counter()
    struct = Counter()
    for d in docs:
        leaves = _zip_leaves(d.zip.items) if d.zip else []
        if not leaves:
            struct["empty"] += 1
            continue
        main_subj = next((s for s in ((lf.senses or {}).get("subject") for lf in leaves) if s), None)
        pos_of_main[_pos(main_subj) if main_subj else "none"] += 1
        struct["multi_clause" if len(leaves) > 1 else "single_clause"] += 1

    print("\n-- census: definiendum POS (main-leaf subject) --")
    for k, v in pos_of_main.most_common():
        print(f"   {k:6} {v}")
    print("-- census: clause structure --")
    for k, v in struct.most_common():
        print(f"   {k:14} {v}")

    # ---- the extractor (the shared gate) ---------------------------------------------------------
    rules, stats = extract_sufficient_rules(docs, bedrock)
    cond_count = Counter(len(r["conds"]) for r in rules)

    print(f"\n-- sufficiency mining (kb_extract.extract_sufficient_rules) --")
    print(f"   definitions with a genus spine .... {stats['candidate_def']}"
          f"   (no_genus {stats['no_genus']}, genus_only {stats['genus_only']},"
          f" abstract_genus {stats['abstract_genus']})")
    print(f"   DNF branches examined ............. {stats['candidate_branch']}")
    for k in ("taint", "no_pred", "foreign_subj", "negated_cond", "noun_cond", "verb_noobj",
              "circular", "bare"):
        print(f"     rejected {k:13} {stats[f'br_{k}']}")
    print(f"     ACCEPTED ............ {stats['accept']}  (from"
          f" {len({r['klass'] for r in rules})} distinct classes)")
    print(f"   conds-per-rule: " + "  ".join(f"{n} cond -> {c} rules" for n, c in sorted(cond_count.items())))

    print(f"\n-- sample accepted sufficient rules (first 25) --")
    for r in rules[:25]:
        conds = " ∧ ".join(f"{_lemma(c['predicate'])}({_lemma(c['object']) if c['object'] else '∅'})"
                           for c in r["conds"])
        print(f"   is_a {_lemma(r['genus'])} ∧ {conds}  →  is_a {_lemma(r['klass'])}"
              f"      «{r['source_original'][:70]}»")

    # ---- the teaser: which sufficient rules could fire on the known individuals ------------------
    # property-lemma match only, genus + objects ignored — a deliberately LOOSE upper bound.
    axioms = TKAxiomDoc.find({"archived": False}).to_list()
    facts = extract_facts(axioms)
    uids: dict[str, list] = {}
    for f in facts:
        uids.setdefault(f["subject_uid"], []).append(f)
    print(f"\n-- teaser: recognition candidates per known individual (LOOSE upper bound) --")
    for uid, ufacts in uids.items():
        have = {_lemma(f["predicate"]) for f in ufacts
                if f.get("kind") == "property" and not f.get("negated", False)}
        hits = [r for r in rules
                if all(any(_lemma(c["predicate"])[:4] == h[:4] and len(h) >= 4
                           or _lemma(c["predicate"]) == h for h in have)
                       for c in r["conds"])]
        print(f"   {uid}: {len(hits)} candidate recognitions"
              + (f" — e.g. " + ", ".join(sorted({_lemma(r['klass']) for r in hits})[:8]) if hits else ""))

    print(f"\n{bar}\nREAD-ONLY probe — nothing written.\n{bar}")


if __name__ == "__main__":
    main()

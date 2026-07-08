# ------------------------------------------------------------------------------------------------
# extract_sufficiency.py — Brain v1.1 STEP 4 WRITER: mine the definitions' SUFFICIENT direction into
# the LOW-TRUST rule tier (`derived_rules`, kind="sufficient") — the recognition/classification fuel.
#
# A definition is a biconditional (X ⟺ genus ∧ definiens); this persists the direction the
# differentia writer doesn't: whatever satisfies the WHOLE definiens IS an X —
#     (is_a genus ∧ cond₁ ∧ … ∧ condₙ) → is_a X
# Uses the SAME gate as the dry-run probe (lib.core.kb_extract.extract_sufficient_rules — one source
# of truth), judged against the bedrock is_a graph. Each accepted rule lands with full provenance
# (source definition + trust + method), revocable + low-trust like every definition-derived item.
#
# IDEMPOTENT full rebuild: --apply DELETES this method's rules then inserts the fresh set. DRY-RUN by
# default (prints the plan, writes nothing).
#
#   python scripts/extract_sufficiency.py            # dry-run
#   python scripts/extract_sufficiency.py --apply     # write the tier (operator-gated)
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc, TKDerivedRuleDoc
from lib.core.kb_extract import extract_sufficient_rules
from lib.core.evaluation_harness import _make_relations_reader

_METHOD = "sufficiency-v1"
_TRUST = 0.3


def _lemma(s):
    return (s or "").split(".", 1)[0]


def main():
    apply = "--apply" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    bedrock = _make_relations_reader()  # gate against the TRUSTED graph only
    rules, stats = extract_sufficient_rules(docs, bedrock)

    bar = "=" * 84
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n{bar}\nSUFFICIENCY → RULE tier  [{mode}]  ({len(docs)} definitions)\n{bar}")
    print(f"  definitions with a genus spine .. {stats['candidate_def']}"
          f"  (no_genus {stats['no_genus']}, genus_only {stats['genus_only']},"
          f" abstract_genus {stats['abstract_genus']})")
    print(f"  DNF branches examined ........... {stats['candidate_branch']}")
    for k in ("taint", "no_pred", "foreign_subj", "negated_cond", "noun_cond", "verb_noobj",
              "circular", "bare"):
        print(f"    rejected {k:13} {stats[f'br_{k}']}")
    print(f"    ACCEPTED ............ {stats['accept']}")

    print(f"\n  sample (first 15):")
    for r in rules[:15]:
        conds = " ∧ ".join(f"{_lemma(c['predicate'])}({_lemma(c['object']) if c['object'] else '∅'})"
                           for c in r["conds"])
        print(f"    is_a {_lemma(r['genus'])} ∧ {conds}  →  is_a {_lemma(r['klass'])}"
              f"    «{r['source_original'][:60]}»")

    if not apply:
        print(f"\n  DRY-RUN — nothing written. Re-run with --apply to rebuild the tier.\n{bar}")
        return

    n_old = TKDerivedRuleDoc.find({"method": _METHOD}).count()
    TKDerivedRuleDoc.find({"method": _METHOD}).delete().run()  # Bunnet: .run() or it's a silent no-op
    docs_out = [
        TKDerivedRuleDoc(
            subject=r["klass"], predicate="", object=None, negated=False,
            kind="sufficient", genus=r["genus"], conds=r["conds"],
            source_id=r["source_id"], source_original=r["source_original"],
            trust=_TRUST, method=_METHOD,
        )
        for r in rules
    ]
    if docs_out:
        TKDerivedRuleDoc.insert_many(docs_out)
    print(f"\n  replaced {n_old} old '{_METHOD}' rules with {len(docs_out)} fresh ones.\n{bar}")


if __name__ == "__main__":
    main()

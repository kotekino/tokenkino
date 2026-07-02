# ------------------------------------------------------------------------------------------------
# extract_differentia.py — STEP 5.2 WRITER: mine the definitions' DIFFERENTIA into the LOW-TRUST
# universal PROPERTY-RULE tier (`derived_rules`), the generative fuel of the enriched soak.
#
# Uses the SAME strict gate as the dry-run probe (lib.core.kb_extract.extract_differentia_rules — one
# source of truth), judged against the bedrock is_a graph. Each accepted rule "all X <differentia>"
# lands in a physically SEPARATE collection with full provenance (source definition + trust + method),
# carrying the differentia's negation, so it — and any theorem it mints — stays revocable + low-trust.
#
# IDEMPOTENT full rebuild: --apply DELETES this method's rules then inserts the fresh set. DRY-RUN by
# default (prints the plan, writes nothing).
#
#   python scripts/extract_differentia.py            # dry-run
#   python scripts/extract_differentia.py --apply     # write the tier (operator-gated)
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc, TKDerivedRuleDoc
from lib.core.kb_extract import extract_differentia_rules
from lib.core.evaluation_harness import _make_relations_reader

_METHOD = "differentia-v1"
_TRUST = 0.3


def _lemma(s):
    return (s or "").split(".", 1)[0]


def main():
    apply = "--apply" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    bedrock = _make_relations_reader()  # gate against the TRUSTED graph only
    rules, stats = extract_differentia_rules(docs, bedrock)

    bar = "=" * 84
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n{bar}\nDIFFERENTIA → PROPERTY-RULE tier  [{mode}]  ({len(docs)} definitions)\n{bar}")
    print(f"  candidate differentia .. {stats['candidate']}")
    for k in ("abstract", "noun", "verb_noobj", "circular"):
        print(f"  rejected {k:12} {stats[k]}")
    print(f"  ACCEPT -> tier ......... {len(rules)}  (method={_METHOD}, trust={_TRUST})")
    print(f"\n  sample rules:")
    for r in rules[:15]:
        neg = "NOT " if r["negated"] else ""
        obj = f" {_lemma(r['object'])}" if r["object"] else ""
        print(f"    all {_lemma(r['subject'])} {neg}{_lemma(r['predicate'])}{obj}   «{r['source_original']}»")

    existing = TKDerivedRuleDoc.find({"method": _METHOD}).count()
    print(f"\n  existing {_METHOD} rules in DB: {existing}")

    if not apply:
        print(f"\n  DRY-RUN — nothing written. Re-run with --apply to rebuild the tier.\n{bar}")
        return

    if existing:
        TKDerivedRuleDoc.find({"method": _METHOD}).delete()
        print(f"  deleted {existing} stale {_METHOD} rules.")
    inserted = 0
    for r in rules:
        TKDerivedRuleDoc(
            subject=r["subject"], predicate=r["predicate"], object=r["object"],
            negated=r["negated"], kind="property",
            source_id=r["source_id"], source_original=r["source_original"],
            trust=_TRUST, method=_METHOD,
        ).insert()
        inserted += 1
    total = TKDerivedRuleDoc.find({"method": _METHOD}).count()
    print(f"  inserted {inserted} rules.  tier now holds {total} {_METHOD} rules.\n{bar}")


if __name__ == "__main__":
    main()

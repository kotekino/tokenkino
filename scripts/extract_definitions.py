# ------------------------------------------------------------------------------------------------
# extract_definitions.py — STEP 3 WRITER: mine the definitions' clean genus into the LOW-TRUST is_a
# tier (`derived_relations`), so definitions finally FUEL the reasoner (grounding + chaining).
#
# Uses the SAME gate as the dry-run probe (lib.core.kb_extract.extract_isa_edges — the single source of
# truth), judged against the BEDROCK is_a graph only. Writes each accepted edge into a physically
# SEPARATE collection (never polluting the ~150k WordNet bedrock) with full provenance (source
# definition + trust + method), so any edge — and any theorem resting on it — stays revocable (step 4).
#
# IDEMPOTENT full rebuild: --apply first DELETES this method's existing edges, then inserts the fresh
# set (deterministic, mirrors recompile.py). DRY-RUN by default — prints the plan, writes nothing.
#
#   python scripts/extract_definitions.py            # dry-run (default) — plan only
#   python scripts/extract_definitions.py --apply     # write the tier (operator-gated)
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc, TKDerivedRelationDoc
from lib.core.kb_extract import extract_isa_edges
from lib.core.evaluation_harness import _make_relations_reader

_METHOD = "genus-extract-v1"
_TRUST = 0.3


def main():
    apply = "--apply" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    bedrock = _make_relations_reader()  # gate against the TRUSTED graph only (never the union)
    edges, stats = extract_isa_edges(docs, bedrock)

    bar = "=" * 84
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n{bar}\nDEFINITION → is_a TIER extractor  [{mode}]  ({len(docs)} active definitions)\n{bar}")
    print(f"  candidate genus edges .. {stats['candidate']}")
    for k in ("redundant", "placeholder", "cycle", "disjoint"):
        print(f"  rejected {k:12} {stats[k]}")
    print(f"  ACCEPT -> tier ......... {len(edges)}  (method={_METHOD}, trust={_TRUST})")
    print(f"\n  sample edges:")
    for e in edges[:12]:
        print(f"    {e['subject']:24} is_a {e['object']:24}  «{e['source_original']}»")

    existing = TKDerivedRelationDoc.find({"method": _METHOD}).count()
    print(f"\n  existing {_METHOD} tier edges in DB: {existing}")

    if not apply:
        print(f"\n  DRY-RUN — nothing written. Re-run with --apply to rebuild the tier.\n{bar}")
        return

    # idempotent full rebuild: drop this method's edges, insert the fresh set.
    if existing:
        TKDerivedRelationDoc.find({"method": _METHOD}).delete()
        print(f"  deleted {existing} stale {_METHOD} edges.")
    inserted = 0
    for e in edges:
        TKDerivedRelationDoc(
            subject=e["subject"], relation="is_a", object=e["object"], pos="n",
            source_id=e["source_id"], source_original=e["source_original"],
            trust=_TRUST, method=_METHOD,
        ).insert()
        inserted += 1
    total = TKDerivedRelationDoc.find({"method": _METHOD}).count()
    print(f"  inserted {inserted} edges.  tier now holds {total} {_METHOD} edges.\n{bar}")


if __name__ == "__main__":
    main()

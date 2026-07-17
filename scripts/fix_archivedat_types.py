#!/usr/bin/env python
# ------------------------------------------------------------------------------------------------
# fix_archivedat_types.py — one-shot metadata TYPE repair (2026-07-17): some archived rows (the
# 2026-07-13 storm containment) carry `archivedAt` as a BSON datetime while the model declares
# epoch-seconds int — every full-collection parse (e.g. recompile.py) chokes on them. This
# converts the TYPE only (datetime -> int(epoch), same instant, UTC): no value, no content, no
# other field is touched — the biography stays byte-identical in meaning.
#
# Raw pymongo on purpose (Bunnet can't parse the rows it's here to fix). Idempotent.
# Dry-run by default; --apply to persist.
#   python scripts/fix_archivedat_types.py            # DRY-RUN (counts per collection)
#   python scripts/fix_archivedat_types.py --apply
# ------------------------------------------------------------------------------------------------
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tokeniko"))
load_dotenv(Path(__file__).resolve().parents[1] / "tokeniko" / ".env")

from lib.core.io import init_io  # noqa: E402


def main() -> int:
    apply = "--apply" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    from lib.core.models import TKAxiomDoc, TKDefinitionDoc, TKTheoremDoc

    total = 0
    for doc_cls in (TKAxiomDoc, TKTheoremDoc, TKDefinitionDoc):
        col = doc_cls.get_motor_collection()
        bad = list(col.find({"archivedAt": {"$type": "date"}}, {"archivedAt": 1}))
        print(f"{col.name}: {len(bad)} row(s) with datetime archivedAt")
        for row in bad:
            ts = row["archivedAt"]
            if ts.tzinfo is None:  # Mongo returns naive UTC — pin it (the JST trap)
                ts = ts.replace(tzinfo=timezone.utc)
            epoch = int(ts.timestamp())
            print(f"  {row['_id']}: {row['archivedAt']} -> {epoch}")
            if apply:
                col.update_one({"_id": row["_id"]}, {"$set": {"archivedAt": epoch}})
            total += 1
    print(f"\n{'converted' if apply else 'would convert'} {total} row(s)")
    if not apply:
        print("dry-run — pass --apply to persist")
    return 0


if __name__ == "__main__":
    sys.exit(main())

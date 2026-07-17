#!/usr/bin/env python
# --------------------------------------------------------------
# scripts/microscope_mark_addressed.py — microscope triage bookkeeping (2026-07-17, author's ask).
#
# Stamps every EXISTING lead in `tkzipdebug` addressed=True, so the NEXT feedback analysis
# (doc/ref/test-feedback.md) samples only the fresh, never-analyzed corpus (addressed=False —
# the model default every new judged lead is born with). Run AFTER an analysis pass has consumed
# its generation of leads. Idempotent; --apply gated like the sibling curation scripts.
#
# Usage (from the repo root):
#   python scripts/microscope_mark_addressed.py           # dry-run: counts only
#   python scripts/microscope_mark_addressed.py --apply
# --------------------------------------------------------------
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tokeniko"))
load_dotenv(Path(__file__).resolve().parents[1] / "tokeniko" / ".env")

from lib.core.io import init_io  # noqa: E402


def main() -> int:
    apply = "--apply" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    from lib.core.models import TKZipDebugDoc

    col = TKZipDebugDoc.get_motor_collection()  # raw pymongo: update_many needs no Bunnet .run() dance
    total = col.count_documents({})
    pending = col.count_documents({"addressed": {"$ne": True}})
    print(f"leads: {total} total, {pending} not yet addressed")
    if not apply:
        print("dry-run — pass --apply to stamp them")
        return 0
    res = col.update_many({"addressed": {"$ne": True}}, {"$set": {"addressed": True}})
    print(f"stamped addressed=True on {res.modified_count} lead(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# --------------------------------------------------------------
# scripts/seed_trust_imprint.py — trust-ledger constitution (senses D P1, run once).
#
# 1. IMPRINT kotekino (the internal stakeholder): trust pinned 1.0 by constitution — the fold
#    never moves it (episodes still recorded; the trail stays honest).
# 2. UNIFY the author's Discord body (fork 3 option A, author's call 2026-07-11 — "I accept A;
#    at a more advanced stage I would have answered B"): kotekino@discord:… -> canonical_uid
#    "kotekino". One soul, one ledger, two channel bodies.
#
# DRY-RUN by default; --apply writes. Idempotent.
# --------------------------------------------------------------
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "tokeniko" / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tokeniko"))

from lib.core.io import init_io  # noqa: E402
from lib.core.models import TKMemoryStakeholdersDoc  # noqa: E402

_ANCHOR_UID = "kotekino"
_BODY_PREFIX = "kotekino@discord:"


def main() -> int:
    apply = "--apply" in sys.argv
    print(f"seed_trust_imprint.py — {'APPLYING (writes enabled)' if apply else 'DRY-RUN (no writes)'}")

    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    anchor = TKMemoryStakeholdersDoc.find_one({"uid": _ANCHOR_UID}).run()
    if anchor is None:
        print(f"  ANCHOR {_ANCHOR_UID!r} not found — nothing to imprint"); return 1
    print(f"  anchor {_ANCHOR_UID!r}: imprint {getattr(anchor, 'imprint', False)} -> True, trust -> 1.0")
    if apply:
        anchor.imprint = True
        anchor.trust = 1.0
        anchor.save()

    bodies = [s for s in TKMemoryStakeholdersDoc.find({}).to_list()
              if s.uid.startswith(_BODY_PREFIX) and s.kind == "participant"]
    if not bodies:
        print(f"  no {_BODY_PREFIX}* participant body found (will unify when it first speaks)")
    for body in bodies:
        print(f"  body {body.uid!r}: canonical_uid {getattr(body, 'canonical_uid', None)!r} -> {_ANCHOR_UID!r}")
        if apply:
            body.canonical_uid = _ANCHOR_UID
            body.save()

    print("done" if apply else "dry-run complete — rerun with --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

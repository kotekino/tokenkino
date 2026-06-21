# ------------------------------------------------------------------------------------------------
# migrate_glosses.py — "full re-home" of WordNet-gloss axioms into multi-clause definitions.
#
# Two coordinated data moves (run AFTER the MEMDefinition model change: content -> zip):
#   (1) RE-DERIVE existing definitions to the new `zip` shape. The stored rows are the OLD
#       `content`-shaped docs (a single TKZipContent), which can NO LONGER load via TKDefinitionDoc
#       after the model change -> we read them with raw pymongo (only `original` is needed), recompile
#       via DefinitionService.compile_fields, and (on --apply) rewrite each row in place:
#       $set {zip, raw}, $unset {content}. ALL metadata is preserved.
#   (2) MOVE the gloss-axioms into definitions. An axiom is a gloss-to-move iff its createdAt day is
#       NOT in the keep-set {2026-06-14, 2026-06-19} (the genuine relational axioms + seeded rules).
#       The createdAt keep-set is AUTHORITATIVE. We ALSO classify by the gloss-frame regex
#       (^(a|an|the|something)\b.*\bis\b) and REPORT any disagreement between the two signals.
#       For each gloss-axiom: compile via DefinitionService.compile_fields; dedup by `original`
#       (skip if a definition with that original already exists); else (on --apply) create a new
#       TKDefinitionDoc and then DELETE the axiom from `axioms`.
#   (3) KEEP the keep-set axioms untouched (reported, with their originals).
#
# Idempotent: re-running --apply is safe. A re-derived definition (already zip-shaped, no content)
# recomputes the same geometry; a moved axiom is gone (deleted); a dedup-existing definition is
# skipped.
#
# Dry-run by default (writes NOTHING). Pass --apply to persist.
#   /Users/renzosala/Develop/personal/tokeniko/.venv/bin/python scripts/migrate_glosses.py
#   /Users/renzosala/Develop/personal/tokeniko/.venv/bin/python scripts/migrate_glosses.py --apply
# ------------------------------------------------------------------------------------------------
import os
import re
import sys
import argparse
import datetime

# make the package importable when run from the repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.join(_HERE, "..", "tokeniko")
sys.path.insert(0, _PKG)

from dotenv import load_dotenv
load_dotenv(os.path.join(_PKG, ".env"))

from pymongo import MongoClient

from lib.core.io import init_io, get_tokeniko
from lib.core.models import TKDefinitionDoc
from lib.core.memory import MEMChannels
from lib.llc.parser import parser_init

from api.services import DefinitionService


# the createdAt days whose axioms are GENUINE (relational axioms + seeded rules/facts) -> KEEP.
# everything else is a WordNet gloss batch -> MOVE to definitions.
_KEEP_DAYS = {"2026-06-14", "2026-06-19"}

# the WordNet-gloss surface frame ("a X is …", "an X is …", "the X is …", "something X is …").
_GLOSS_FRAME = re.compile(r"^(a|an|the|something)\b.*\bis\b", re.IGNORECASE)


def _day_of(created_at) -> str:
    if isinstance(created_at, (int, float)):
        return datetime.datetime.fromtimestamp(created_at, datetime.UTC).strftime("%Y-%m-%d")
    return str(created_at)


def _is_gloss_frame(original: str) -> bool:
    return bool(_GLOSS_FRAME.match((original or "").strip()))


def _serialize_zip(tkzip):
    # bunnet/pydantic serialization for a raw pymongo $set (mode="json" -> bson-safe primitives)
    return None if tkzip is None else tkzip.model_dump(mode="json")


# ------------------------------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.defs_rederived = 0
        self.defs_rederive_failed = 0
        self.gloss_moved = 0
        self.gloss_dedup_skipped = 0
        self.gloss_move_failed = 0
        self.kept = []                 # list of (original) for the keep-set axioms
        self.failures = []             # (phase, id, original, error)
        self.signal_disagreements = [] # (id, original, day, keep_by_day, gloss_by_frame)


def main():
    ap = argparse.ArgumentParser(
        description="Re-home WordNet-gloss axioms into multi-clause definitions (definitions: content -> zip)."
    )
    ap.add_argument("--apply", action="store_true", help="persist the migration (default: dry-run)")
    args = ap.parse_args()

    mode = "APPLYING (writes enabled)" if args.apply else "DRY-RUN (no writes)"
    print("=" * 80)
    print(f"  migrate_glosses.py — {mode}")
    print(f"  keep-days={sorted(_KEEP_DAYS)}")
    print("=" * 80)

    # bootstrap IO + pipeline (loads spaCy/Stanza); registers bunnet docs against the memory DB.
    init_io(
        os.getenv("MONGO_URI"),
        os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"),
        os.getenv("OLLAMA_HOST"),
    )
    tok = get_tokeniko()
    print("loading pipeline (spaCy/Stanza) …")
    parser_init()

    definition_service = DefinitionService(tok, None)

    # raw pymongo handles for reads + the in-place rewrites (existing definitions can NOT load via
    # the new TKDefinitionDoc model — they are still `content`-shaped).
    client = MongoClient(os.getenv("MONGO_URI"))
    mem_db = client[os.getenv("MONGO_DB_NAME_MEMORY")]
    defs_col = mem_db["definitions"]
    axioms_col = mem_db["axioms"]

    report = Report()

    defs_before = defs_col.count_documents({})
    axioms_before = axioms_col.count_documents({})

    # ------------------------------------------------------------------------------------------
    # PHASE 1 — re-derive existing definitions to the new `zip` shape
    # ------------------------------------------------------------------------------------------
    print()
    print(f"[phase 1] re-deriving {defs_before} existing definitions (content -> zip) …")
    existing_defs = list(defs_col.find({}, {"_id": 1, "original": 1}))
    for i, row in enumerate(existing_defs, start=1):
        if i % 200 == 0:
            print(f"  defs: {i}/{len(existing_defs)} …")
        original = row.get("original")
        try:
            fields = definition_service.compile_fields(original)
        except Exception as error:
            report.defs_rederive_failed += 1
            report.failures.append(("rederive", str(row["_id"]), original, repr(error)))
            continue
        report.defs_rederived += 1
        if args.apply:
            defs_col.update_one(
                {"_id": row["_id"]},
                {"$set": {"zip": _serialize_zip(fields["zip"]), "raw": fields["raw"]},
                 "$unset": {"content": ""}},
            )

    # ------------------------------------------------------------------------------------------
    # PHASE 2 — move gloss-axioms -> definitions, keep the rest
    # ------------------------------------------------------------------------------------------
    print()
    print(f"[phase 2] classifying {axioms_before} axioms (keep vs move) …")
    axiom_rows = list(axioms_col.find({}, {"_id": 1, "original": 1, "createdAt": 1}))

    # set of existing definition originals (post-phase-1 the rows still carry `original`), used for
    # dedup. read fresh so a phase-1 apply (which keeps `original`) is reflected.
    existing_originals = {r.get("original") for r in defs_col.find({}, {"original": 1})}

    moved_this_run = set()  # guard against intra-run duplicates among the gloss batch

    for i, row in enumerate(axiom_rows, start=1):
        if i % 200 == 0:
            print(f"  axioms: {i}/{len(axiom_rows)} …")
        original = row.get("original")
        day = _day_of(row.get("createdAt"))
        keep_by_day = day in _KEEP_DAYS
        gloss_by_frame = _is_gloss_frame(original)

        # signal-agreement audit: keep-by-day should mean NOT-gloss-frame, and vice-versa.
        if keep_by_day == gloss_by_frame:
            report.signal_disagreements.append(
                (str(row["_id"]), original, day, keep_by_day, gloss_by_frame)
            )

        if keep_by_day:
            report.kept.append(original)
            continue

        # this is a gloss-to-move (createdAt is authoritative)
        if original in existing_originals or original in moved_this_run:
            report.gloss_dedup_skipped += 1
            continue

        try:
            fields = definition_service.compile_fields(original)
        except Exception as error:
            report.gloss_move_failed += 1
            report.failures.append(("move", str(row["_id"]), original, repr(error)))
            continue

        report.gloss_moved += 1
        moved_this_run.add(original)
        if args.apply:
            definition = TKDefinitionDoc(
                original=fields["original"],
                zip=fields["zip"],
                raw=fields["raw"],
                sourceId=str(tok.id),
                targetId=str(tok.id),
                channel=MEMChannels.INTERNAL,
            )
            definition.insert()
            axioms_col.delete_one({"_id": row["_id"]})

    defs_after = defs_col.count_documents({})
    axioms_after = axioms_col.count_documents({})

    # ------------------------------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 80)
    print(f"  REPORT  [{mode}]")
    print("=" * 80)
    print(f"  phase 1 — definitions re-derived:   {report.defs_rederived}")
    print(f"            re-derive failures:       {report.defs_rederive_failed}")
    print(f"  phase 2 — gloss-axioms moved:       {report.gloss_moved}")
    print(f"            dedup skips (existing):   {report.gloss_dedup_skipped}")
    print(f"            move failures:            {report.gloss_move_failed}")
    print(f"            axioms KEPT (keep-days):  {len(report.kept)}")
    print()
    print("  KEPT axioms (originals):")
    for original in report.kept:
        print(f"    - {original!r}")
    print()
    print(f"  signal disagreements (frame-regex vs createdAt): {len(report.signal_disagreements)}")
    if report.signal_disagreements:
        print("    (id, original, day, keep_by_day, gloss_by_frame):")
        for oid, original, day, keep, gloss in report.signal_disagreements[:30]:
            snippet = (original or "")[:70].replace("\n", " ")
            print(f"    - {oid}  day={day}  keep_by_day={keep}  gloss_by_frame={gloss}  {snippet!r}")
    else:
        print("    none — frame-regex and createdAt AGREE on the whole keep/move split.")
    print()
    if report.failures:
        n = min(15, len(report.failures))
        print(f"  first {n} failures (phase, id, original -> error):")
        for phase, oid, original, error in report.failures[:15]:
            snippet = (original or "")[:60].replace("\n", " ")
            print(f"    - [{phase}] {oid}  {snippet!r}  -> {error}")
    print()
    print("-" * 80)
    print(f"  definitions: before={defs_before}  after={defs_after}")
    print(f"  axioms:      before={axioms_before}  after={axioms_after}")
    if not args.apply:
        unchanged = (defs_before == defs_after) and (axioms_before == axioms_after)
        print(f"  DRY-RUN wrote nothing -> counts unchanged: {unchanged}")
    print("-" * 80)


if __name__ == "__main__":
    main()

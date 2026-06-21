# ------------------------------------------------------------------------------------------------
# recompile.py — re-derive each KB doc's geometry from its stored `original` text by re-running the
# CURRENT compilation pipeline (sense-bridge + identity-bridge), so the stored knowledge base picks
# up `senses` + `identities` it never had (it was saved BEFORE those bridges existed). Needed for the
# upcoming forward-chaining work.
#
# It rewrites ONLY the derived fields — axioms/theorems: `zip` + `raw`; definitions: `zip` + `raw`
# — and NEVER touches metadata (trusted/archived/readonly/createdAt/archivedAt/sourceId/targetId/
# channel/original). It REUSES the exact `*Service.compile_fields(original)` the create/update API
# paths use, so the derived geometry is bit-for-bit the same as a fresh POST.
#
# Dry-run by default (computes a diff summary, writes nothing). Pass --apply to persist.
#   python scripts/recompile.py --collection axioms --limit 8            # DRY-RUN sample
#   python scripts/recompile.py                                          # DRY-RUN all collections
#   python scripts/recompile.py --apply --collection definitions         # APPLY to definitions
#
# Run with the project venv from the repo root:
#   /Users/renzosala/Develop/personal/tokeniko/.venv/bin/python scripts/recompile.py [args]
# ------------------------------------------------------------------------------------------------
import os
import sys
import argparse

# make the package importable when run from the repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.join(_HERE, "..", "tokeniko")
sys.path.insert(0, _PKG)

from dotenv import load_dotenv
load_dotenv(os.path.join(_PKG, ".env"))

from lib.core.io import init_io, get_tokeniko
from lib.core.models import TKAxiomDoc, TKTheoremDoc, TKDefinitionDoc
from lib.core.tkzip import TKZipContent
from lib.llc.parser import parser_init

from api.services import AxiomService, DefinitionService, TheoremService


# ------------------------------------------------------------------------------------------------
# diff helpers
# ------------------------------------------------------------------------------------------------
# COMPARISON CHOICE (`changed`):
#   We compare the Pydantic `model_dump()` of the derived field against the stored one. This is a
#   structural value-equality over the full model (vectors included). It is intentionally exact: any
#   real change in the geometry, the new `senses`/`identities` dicts, negation/quantifier flags, etc.
#   flips `changed=True`. Because every doc here was stored WITHOUT the bridges, we expect nearly all
#   to be `changed` (at minimum they gain a non-empty `senses` dict). model_dump() equality won't
#   false-positive on float identity: the floats are the SAME deterministic pipeline output for the
#   same input text, so equal inputs produce equal float lists (no re-randomization in the compiler).

# walk every leaf TKZipContent of a TKZip's recursive item tree
def _zip_leaves(tkzip):
    if tkzip is None:
        return
    stack = [tkzip.items]
    while stack:
        item = stack.pop()
        if item is None:
            continue
        payload = item.content
        if isinstance(payload, TKZipContent):
            yield payload
        elif isinstance(payload, list):
            stack.extend(payload)


# total number of (role->value) entries across all leaves for a given attribute ("senses"/"identities")
def _zip_attr_count(tkzip, attr):
    total = 0
    for leaf in _zip_leaves(tkzip):
        total += len(getattr(leaf, attr) or {})
    return total


def _content_attr_count(content, attr):
    if content is None:
        return 0
    return len(getattr(content, attr) or {})


def _dump(model):
    return None if model is None else model.model_dump()


# ------------------------------------------------------------------------------------------------
# per-collection processing
# ------------------------------------------------------------------------------------------------
class Stats:
    def __init__(self, name):
        self.name = name
        self.total = 0
        self.recompiled_ok = 0
        self.changed = 0
        self.gained_senses = 0
        self.gained_identities = 0
        self.failed = 0
        self.failures = []  # (id, original, error)


def _process(name, doc_cls, service, derived_keys, count_fn, apply, limit):
    """Generic recompile loop.

    derived_keys: which fields compile_fields returns + how they map onto the doc, e.g.
        for axioms/theorems -> ("zip", "raw"); for definitions -> ("content", "raw").
    count_fn(value, attr) -> int : counts senses/identities entries on the derived/stored value.
    The FIRST derived key is the geometry field (zip / content) used for the diff + gain check.
    """
    stats = Stats(name)
    geom_key = derived_keys[0]

    cursor = doc_cls.find()
    docs = cursor.to_list()
    if limit is not None:
        docs = docs[:limit]
    stats.total = len(docs)

    for i, doc in enumerate(docs, start=1):
        if i % 100 == 0:
            print(f"  {name}: {i}/{stats.total} …")
        try:
            fields = service.compile_fields(doc.original)
        except Exception as error:  # compile failure, NotASingleClauseError, etc. — never abort
            stats.failed += 1
            stats.failures.append((str(doc.id), doc.original, repr(error)))
            continue

        stats.recompiled_ok += 1

        new_geom = fields[geom_key]
        old_geom = getattr(doc, geom_key)

        # changed: structural value inequality of the derived geometry vs stored
        if _dump(new_geom) != _dump(old_geom):
            stats.changed += 1

        # gained_senses / gained_identities: new geometry carries entries the stored one lacked
        new_senses = count_fn(new_geom, "senses")
        old_senses = count_fn(old_geom, "senses")
        if new_senses > 0 and old_senses == 0:
            stats.gained_senses += 1

        new_ids = count_fn(new_geom, "identities")
        old_ids = count_fn(old_geom, "identities")
        if new_ids > 0 and old_ids == 0:
            stats.gained_identities += 1

        if apply:
            for key in derived_keys:
                setattr(doc, key, fields[key])
            doc.save()

    return stats


def _print_report(stats):
    print()
    print(f"=== {stats.name} ===")
    print(f"  total:            {stats.total}")
    print(f"  recompiled_ok:    {stats.recompiled_ok}")
    print(f"  changed:          {stats.changed}")
    print(f"  gained_senses:    {stats.gained_senses}")
    print(f"  gained_identities:{stats.gained_identities}")
    print(f"  failed:           {stats.failed}")
    if stats.failures:
        print(f"  first {min(15, len(stats.failures))} failures:")
        for oid, original, error in stats.failures[:15]:
            snippet = (original or "")[:60].replace("\n", " ")
            print(f"    - {oid}  {snippet!r}  -> {error}")


# ------------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Re-derive KB geometry (zip/content + raw) from stored originals via the current pipeline."
    )
    ap.add_argument("--apply", action="store_true", help="persist the recompiled fields (default: dry-run)")
    ap.add_argument("--collection", choices=["axioms", "definitions", "theorems", "all"], default="all")
    ap.add_argument("--limit", type=int, default=None, help="process at most N docs per collection")
    args = ap.parse_args()

    mode = "APPLYING (writes enabled)" if args.apply else "DRY-RUN (no writes)"
    print("=" * 80)
    print(f"  recompile.py — {mode}")
    print(f"  collection={args.collection}  limit={args.limit if args.limit is not None else 'none'}")
    print("=" * 80)

    # bootstrap the IO layer + pipeline (loads spaCy/Stanza)
    init_io(
        os.getenv("MONGO_URI"),
        os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"),
        os.getenv("OLLAMA_HOST"),
    )
    tok = get_tokeniko()
    print("loading pipeline (spaCy/Stanza) …")
    parser_init()

    axiom_service = AxiomService(tok, None)
    theorem_service = TheoremService(tok, None)
    definition_service = DefinitionService(tok, None)

    want = {"axioms", "definitions", "theorems"} if args.collection == "all" else {args.collection}
    all_stats = []

    if "axioms" in want:
        all_stats.append(_process(
            "axioms", TKAxiomDoc, axiom_service, ("zip", "raw"),
            _zip_attr_count, args.apply, args.limit,
        ))
    if "theorems" in want:
        all_stats.append(_process(
            "theorems", TKTheoremDoc, theorem_service, ("zip", "raw"),
            _zip_attr_count, args.apply, args.limit,
        ))
    if "definitions" in want:
        all_stats.append(_process(
            "definitions", TKDefinitionDoc, definition_service, ("zip", "raw"),
            _zip_attr_count, args.apply, args.limit,
        ))

    for stats in all_stats:
        _print_report(stats)

    # combined summary line
    t = sum(s.total for s in all_stats)
    ok = sum(s.recompiled_ok for s in all_stats)
    ch = sum(s.changed for s in all_stats)
    gs = sum(s.gained_senses for s in all_stats)
    gi = sum(s.gained_identities for s in all_stats)
    fa = sum(s.failed for s in all_stats)
    print()
    print("-" * 80)
    print(f"COMBINED [{mode}]  total={t}  recompiled_ok={ok}  changed={ch}  "
          f"gained_senses={gs}  gained_identities={gi}  failed={fa}")
    print("-" * 80)


if __name__ == "__main__":
    main()

# ------------------------------------------------------------------------------------------------
# soak_report.py — the LONG-WONDERING SOAK analyzer (wondering-v2 capstone #5). READ-ONLY: parses a
# captured brain log + reads the current DB, and prints a STRUCTURED account of what the soak did, so
# we can "understand everything" — performance, results, inconsistencies, successes, and where a bug is
# evident (and at which LAYER: chaining / renderer / compiler-parser via the API / convergence).
#
# It judges what it CAN automatically (churn, errors, convergence, integrity, expected-set coverage) and
# SURFACES the rest (every derivation + chain) for human review — it never silently declares success.
#
#   python scripts/soak_report.py <brain_soak_log_path>
# ------------------------------------------------------------------------------------------------
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKTheoremDoc, TKAxiomDoc, TKMemoryItemDoc, TKIdeaDoc, TKActionDoc

# the theorems a clean-slate soak over the current tiny KB is expected to RE-DERIVE (the 4 ≥2-premise
# conclusions). extras are interesting (new capability or a chaining bug); misses are a regression.
EXPECTED = {"I exist", "Mari exists", "Mari is mortal", "a human exists"}

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})")
_MAT = re.compile(r"KB-derived THEOREM «(.+?)» <- (.+?) \(premises=\[(.*?)\]\)")
_MATFAIL = re.compile(r"KB-derive «(.+?)» — API")
_DRIFT = re.compile(r"\[wondering\] drift: queued (\d+)")


def _ts(line):
    m = _TS.match(line)
    if not m:
        return None
    base = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    return base.timestamp() + int(m.group(2)) / 1000.0


def _fmt_dur(secs):
    return f"{secs:.1f}s" if secs < 120 else f"{secs/60:.1f}min"


def analyze_log(path):
    lines = open(path, encoding="utf-8", errors="replace").readlines()
    times = [t for t in (_ts(l) for l in lines) if t is not None]
    span = (max(times) - min(times)) if len(times) >= 2 else 0.0

    counts = Counter()
    materializations = []   # (ts, conclusion, chain, premises_list)
    fails, errors, warnings = [], [], []
    drift_batches = 0

    for l in lines:
        t = _ts(l)
        if "[wondering]" in l: counts["wondering"] += 1
        if "[thinking]" in l: counts["thinking"] += 1
        if "[priorities]" in l: counts["priorities"] += 1
        if "[actions]" in l: counts["actions"] += 1
        if "[outbound]" in l: counts["outbound"] += 1

        m = _MAT.search(l)
        if m:
            prem = [p.strip().strip("'\"") for p in m.group(3).split(",") if p.strip()]
            materializations.append((t, m.group(1), m.group(2), prem))
        if _MATFAIL.search(l):
            fails.append(l.strip())
        d = _DRIFT.search(l)
        if d:
            drift_batches += 1
        if re.search(r"Traceback|CRITICAL|\bERROR\b|Exception", l):
            errors.append(l.strip())
        elif re.search(r"\bWARNING\b", l) and "[outbound]" not in l:
            warnings.append(l.strip())

    return {
        "lines": len(lines), "span": span,
        "counts": counts, "materializations": materializations,
        "fails": fails, "errors": errors, "warnings": warnings, "drift_batches": drift_batches,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/soak_report.py <brain_soak_log_path>")
        sys.exit(1)
    log_path = sys.argv[1]

    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    a = analyze_log(log_path)
    mats = a["materializations"]
    bar = "=" * 78

    print(f"\n{bar}\nLONG-WONDERING SOAK REPORT\n{bar}")
    print(f"log: {log_path}\n  {a['lines']} lines over {_fmt_dur(a['span'])} wall-clock")

    # ---- PERFORMANCE ----
    print(f"\n— PERFORMANCE —")
    print(f"  phase log-events: " + ", ".join(f"{k}={v}" for k, v in sorted(a["counts"].items())) or "  (none)")
    print(f"  drift batches enqueued: {a['drift_batches']}")
    if len(mats) >= 2:
        gaps = [mats[i][0] - mats[i-1][0] for i in range(1, len(mats)) if mats[i][0] and mats[i-1][0]]
        if gaps:
            print(f"  materialize latency (compile+POST+derive per theorem): "
                  f"min={min(gaps):.1f}s avg={sum(gaps)/len(gaps):.1f}s max={max(gaps):.1f}s")
    if mats and mats[0][0] and mats[-1][0]:
        print(f"  cascade window (first→last materialize): {_fmt_dur(mats[-1][0]-mats[0][0])} "
              f"→ then quiet = CONVERGED" )

    # ---- RESULTS (what it derived) ----
    print(f"\n— RESULTS: {len(mats)} materialization event(s) —")
    for t, concl, chain, prem in mats:
        print(f"  «{concl}»  ({len(prem)} premises)")
        print(f"       {chain}")

    # ---- CONVERGENCE / CHURN (a re-materialized conclusion = non-convergence bug) ----
    concl_counts = Counter(c for _, c, _, _ in mats)
    churn = {c: n for c, n in concl_counts.items() if n > 1}
    print(f"\n— CONVERGENCE / CHURN —")
    if churn:
        print(f"  *** CHURN DETECTED (re-materialized — dedup/convergence BUG): {churn}")
    else:
        print(f"  OK: every conclusion materialized exactly once (converges, no churn).")

    # ---- ERRORS / INCONSISTENCIES, bucketed by suspected LAYER ----
    print(f"\n— ERRORS / FAILURES (by suspected layer) —")
    if a["fails"]:
        print(f"  API materialize failures ({len(a['fails'])}) — compiler/parser (compile of rendered NL) "
              f"or contradiction-guard (renderer derived a contradictory form):")
        for f in a["fails"][:10]:
            print(f"    {f}")
    if a["errors"]:
        print(f"  hard errors / tracebacks ({len(a['errors'])}) — brain/chaining/IO:")
        for e in a["errors"][:10]:
            print(f"    {e}")
    if a["warnings"]:
        print(f"  warnings ({len(a['warnings'])}):")
        for w in a["warnings"][:10]:
            print(f"    {w}")
    if not (a["fails"] or a["errors"] or a["warnings"]):
        print(f"  OK: no failures, errors, or warnings logged.")

    # ---- DB AFTER-STATE + INTEGRITY ----
    active = TKTheoremDoc.find({"archived": False}).to_list()
    derived = [t for t in active if t.provenance and t.provenance.derived_by == "wondering"]
    print(f"\n— DB AFTER-STATE —")
    print(f"  active theorems: {len(active)}  (wondering-derived: {len(derived)})")
    print(f"  queues now — memory={TKMemoryItemDoc.find({}).count()} "
          f"ideas={TKIdeaDoc.find({}).count()} actions={TKActionDoc.find({}).count()}")

    print(f"\n— INTEGRITY (every derived theorem rests on resolvable premises) —")
    bad = 0
    for t in derived:
        prem = (t.provenance.premises if t.provenance else []) or []
        if not prem:
            print(f"  *** «{t.original}» has NO premises (invariant breach)"); bad += 1; continue
        unresolved = [p for p in prem if TKAxiomDoc.get(p).run() is None]
        if unresolved:
            print(f"  *** «{t.original}» premises unresolved: {unresolved}"); bad += 1
    if not bad:
        print(f"  OK: all {len(derived)} derived theorems carry resolvable premises.")

    # ---- EXPECTED-SET COVERAGE + SUCCESSES ----
    got = {t.original for t in derived}
    missing, extra = EXPECTED - got, got - EXPECTED
    print(f"\n— COVERAGE vs EXPECTED ({len(EXPECTED)}) —")
    print(f"  re-derived: {sorted(got & EXPECTED)}")
    if missing:
        print(f"  *** MISSING (regression — chaining/renderer): {sorted(missing)}")
    if extra:
        print(f"  ?? EXTRA (new capability OR a spurious-conclusion bug — REVIEW): {sorted(extra)}")
    cogito = "I exist" in got
    print(f"\n— VERDICT —")
    print(f"  cogito re-born in-loop: {'YES «I exist»' if cogito else 'NO'}")
    clean = not churn and not a["errors"] and not missing
    print(f"  robustness: {'CLEAN (no churn, no errors, full coverage)' if clean else 'SEE FLAGS ABOVE'}")
    print(bar)


if __name__ == "__main__":
    main()

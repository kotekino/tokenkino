# ------------------------------------------------------------------------------------------------
# trace_fragility.py — category-aware retrospective brain tracer (READ-ONLY; mutates nothing).
# For each `memory` item: join its batch-manifest entry (category/severity/expected), RE-RUN the
# stored zip to recover the eval rationale (status/truth/senses/derivation OR the question answer),
# join the ideas it spawned (idea.source == memory.id) + their actions, and auto-flag S0 breaches.
# Pair with scripts/fragility_batch.py. See doc/ref/test-feedback.md.  Run AFTER the brain fully drains
# (per-speaker cursors caught up — not a premature lull).
#   python scripts/trace_fragility.py
# ------------------------------------------------------------------------------------------------
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "tokeniko")
sys.path.insert(0, PKG)
sys.path.insert(0, HERE)  # so `from fragility_batch import BATCH` resolves (same dir)
from dotenv import load_dotenv
load_dotenv(os.path.join(PKG, ".env"))

from lib.core.io import init_io
init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

import lib.core.evaluation_harness as H
from lib.core.evaluation_harness import evaluate_zip, answer_zip
from lib.core.models import (TKMemoryItemDoc, TKIdeaDoc, TKTheoremDoc, TKMemoryStakeholdersDoc)
from fragility_batch import BATCH

manifest = {sent: (cat, spk, exp, sev) for cat, spk, sent, exp, sev in BATCH}
who = {}
for s in TKMemoryStakeholdersDoc.find({}).to_list():
    who[str(s.id)] = s.name; who[s.uid] = s.name
name = lambda i: who.get(i, (i or "?")[:8])

mems = TKMemoryItemDoc.find({}).sort("timestamp").to_list()
ideas_by_src = {}
for idea in TKIdeaDoc.find({}).to_list():
    ideas_by_src.setdefault(idea.source, []).append(idea)

def mood(z):
    leaves = H._zip_leaves(z.items)
    q = any(getattr(l, "dubitative", 0.5) >= 0.999 for l in leaves)
    wh = next((getattr(l, "wh_role", None) for l in leaves if getattr(l, "wh_role", None)), None)
    return "Q" + (f"/{getattr(wh,'value',wh)}" if wh else "/polar") if q else "assert"

def senses_of(z):
    out = {}
    for l in H._zip_leaves(z.items):
        out.update(getattr(l, "senses", {}) or {})
    return out

by_cat = {}
for m in mems:
    by_cat.setdefault(manifest.get(m.original, ("?",))[0], []).append(m)

flags = []
for cat in sorted(by_cat):
    print(f"\n========== CATEGORY {cat} ==========")
    for m in by_cat[cat]:
        c, spk, exp, sev = manifest.get(m.original, ("?", "?", "?", "?"))
        if m.zip is None:
            verdict = "NO ZIP"
        else:
            q = answer_zip(m.zip)
            if q is not None:
                a = q["answer"]
                verdict = f"Q:{a.kind.value}/{a.verdict.value}{('='+a.value) if a.value else ''} conf={a.confidence:.2f}"
            else:
                r = evaluate_zip(m.zip)["result"]
                tag = ("CHAIN" if any(d.startswith("chain:") for d in r.derivation)
                       else ("subsumed" if any(d.startswith(("subsumed:", "refuted:")) for d in r.derivation) else ""))
                verdict = f"A:{r.status.value} t={r.truth:.2f} {tag}".strip()
                if cat == "B":
                    if "dead and alive" in m.original and r.status.value != "inconsistent":
                        flags.append((sev, m.original, f"expected INCONSISTENT, got {r.status.value}"))
                    elif "dead and alive" not in m.original and r.truth > 0.85:
                        flags.append((sev, m.original, f"FALSE accepted TRUE t={r.truth:.2f}"))
        ids = ideas_by_src.get(str(m.id), [])
        idea_s = " ; ".join(f"{i.trigger}=>{i.action_token}" for i in ids) or "—(no idea)"
        print(f"  [{sev}] ({name(m.sourceId)}) «{m.original[:54]}»")
        print(f"        mood={mood(m.zip) if m.zip else '?'}  EVAL[{verdict}]  exp:{exp}")
        print(f"        senses={senses_of(m.zip) if m.zip else {}}  IDEA: {idea_s}")

print("\n\n========== AUTO-FLAGGED S0/S1 GROUNDING BREACHES ==========")
for sev, sent, why in flags:
    print(f"  [{sev}] «{sent[:50]}» -> {why}")
if not flags:
    print("  none auto-detected")
print(f"\ntheorems materialized: {TKTheoremDoc.find({}).count()}")

# --------------------------------------------------------------
# THE UNTANGLER (roadmap §0 slice 3, the author's addition) — KB-wide reductio as belief hygiene.
# Never fix the poisoned KB by hand: this pass deliberately SATURATES the whole KB (kb_wonder
# already seeds the chainer from every entity — the derivation mirror stamps every conflict),
# collects every absurdity + its premise set, and RETREATS the premises convicted by reductio
# through the belief-revision machinery (archive + revoke_dependents cascade — provenance-
# cascaded, biography preserved: retreat, never mongo-edit, never delete).
#
# THE CONVICTION BAR (the author's fork-D ruling, "decidable-only — logic never guesses",
# operationalized): a conflict is DECIDABLE iff exactly ONE of its premise docs is REVISABLE
# (a theorem, or an axiom with readonly=False) and every other premise is beyond conversational
# doubt (readonly axioms = the constitution; graph edges and rule keys = substrate). Then the
# r.a.a. itself convicts the revisable one — that IS logic, not a trust heuristic. Two or more
# revisable premises -> UNDECIDABLE: left for the wake-time reduct reflex (slice 1 asks the
# teachers; the ledger + reconcile machinery handles it when the daemons wake). Zero revisable
# -> a CONSTITUTION-level tension: flagged loudly, only the author's hand may move.
#
# Designed from day one as a tool HE runs while the daemons sleep (scripts/untangle.py is the
# CLI; dry-run default). The sleep phase gains its second duty: memory consolidation AND belief
# hygiene — and its public voice is the DREAM report (brain/thinking.spawn_dream -> the blog).
# --------------------------------------------------------------
import logging
import time

from lib.core import evaluation_harness

logger = logging.getLogger("tokeniko-brain")


# the tier partition behind the conviction bar. `docs` are resolved premise docs (axiom/theorem
# rows); a doc is REVISABLE when conversation could retract it — a theorem, or a non-readonly
# axiom. Readonly axioms are the constitution. Returns (revisable, protected).
def partition_premises(docs) -> tuple[list, list]:
    revisable, protected = [], []
    for doc in docs:
        is_axiom = hasattr(doc, "readonly")  # theorems carry no readonly field
        if is_axiom and getattr(doc, "readonly", True):
            protected.append(doc)
        else:
            revisable.append(doc)
    return revisable, protected


def _absurd_of(c: dict):
    pos = evaluation_harness.render_conclusion(
        c["subject"], c["predicate"], c.get("object"), False, c["subject_kind"])
    neg = evaluation_harness.render_conclusion(
        c["subject"], c["predicate"], c.get("object"), True, c["subject_kind"])
    return f"{pos.rstrip('.')} and {neg.rstrip('.')}" if pos and neg else None


def _saturate() -> dict:
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    conflicts: list = []
    evaluation_harness.kb_wonder(collect_conflicts=conflicts)
    groups: dict[str, dict] = {}
    for c in conflicts:  # polarity twins of one incident share the signature — union premises
        sig = f"{c['subject']}|{c['predicate']}|{c.get('object') or ''}"
        g = groups.setdefault(sig, {"c": c, "premises": set()})
        g["premises"].update(str(p) for p in c.get("premises", []))
    return groups


# ONE untangling pass. dry-run (apply=False, the default) REPORTS everything it would do —
# including each conviction's dependent-theorem descent — and touches nothing. apply=True
# archives each convicted premise + cascades (revoke_dependents), then RE-SATURATES to report
# the residual honestly. The ledger rows of cured conflicts resolve at the brain's next
# wondering pass (the slice-1 reconcile) — the untangler never writes the ledger itself.
def untangle_pass(apply: bool = False) -> dict:
    groups = _saturate()
    report = {"conflicts": len(groups), "convicted": [], "asked": [],
              "constitution": [], "unresolvable": [], "residual": len(groups)}
    now = int(time.time())
    for sig, g in sorted(groups.items()):
        absurd = _absurd_of(g["c"]) or sig
        docs = evaluation_harness.premise_docs(sorted(g["premises"]))
        if not docs:
            # a pure substrate/rule-key conflict — nothing addressable at all
            report["unresolvable"].append({"signature": sig, "absurd": absurd})
            logger.warning("[untangle] %s: no resolvable premise docs — unresolvable", absurd)
            continue
        revisable, protected = partition_premises(docs)
        entry = {"signature": sig, "absurd": absurd,
                 "premises": [d.original.strip() for d in docs]}
        # THE FIRST SUSPECTS (survey slice 5, the author's ruling): his own guesses die before
        # a taught belief is questioned — ANY hypothesis among the premises is convicted (all of
        # them), even when other revisables share the derivation: the conflict stays decidable
        # because a guess is HIS OWN (silent retreat, no concession owed — but the DREAM tells
        # it: each entry carries guess=True for the dream's voice, the author's fork ruling).
        hypotheses = [d for d in revisable
                      if getattr(getattr(d, "provenance", None), "derived_by", "") == "hypothesis"]
        if hypotheses:
            for doc in hypotheses:
                e = dict(entry)
                dependents = evaluation_harness.revoke_dependents([str(doc.id)], dry_run=True)
                e.update({
                    "doc_id": str(doc.id), "kind": "theorem", "guess": True,
                    "original": doc.original.strip(),
                    "postable": bool(getattr(doc, "postable", True)),
                    "dependents": [t.original for t in dependents],
                })
                if apply:
                    doc.archived = True
                    doc.archivedAt = now
                    doc.save()
                    evaluation_harness.revoke_dependents([str(doc.id)], dry_run=False)
                    logger.warning("[untangle] DROPPED the guess «%s» — the first suspect: "
                                   "kept, it forced «%s» (+%d dependent(s))",
                                   doc.original, absurd, len(e["dependents"]))
                report["convicted"].append(e)
            continue
        if len(revisable) == 1:
            doc = revisable[0]
            dependents = evaluation_harness.revoke_dependents([str(doc.id)], dry_run=True)
            entry.update({
                "doc_id": str(doc.id),
                "kind": "axiom" if hasattr(doc, "readonly") else "theorem",
                "original": doc.original.strip(),
                "postable": bool(getattr(doc, "postable", True)),
                "dependents": [t.original for t in dependents],
            })
            if apply:
                doc.archived = True
                doc.archivedAt = now
                doc.save()
                evaluation_harness.revoke_dependents([str(doc.id)], dry_run=False)
                logger.warning("[untangle] RETREATED «%s» — convicted by reductio: kept, it "
                               "forced «%s» (+%d dependent(s) fell with it)",
                               doc.original, absurd, len(entry["dependents"]))
            report["convicted"].append(entry)
        elif len(revisable) >= 2:
            # undecidable — the wake-time reflex asks the teachers (slice 1's machinery)
            entry["candidates"] = [d.original.strip() for d in revisable]
            report["asked"].append(entry)
        else:
            # every doc-backed premise is constitution — only the author's hand may move
            report["constitution"].append(entry)
            logger.warning("[untangle] CONSTITUTION tension: «%s» rests only on readonly "
                           "axioms (%s) — flagged for the author", absurd, entry["premises"])
    if apply and report["convicted"]:
        report["residual"] = len(_saturate())
    return report

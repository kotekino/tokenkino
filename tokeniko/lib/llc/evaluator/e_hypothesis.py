# --------------------------------------------------------------
# e_hypothesis.py — PROOF BY CONTRADICTION (§0 slice 4, the author's "take the momentum" ruling).
# The constructive direction of the r.a.a.: ASSUME a hypothesis, forward-saturate, and if the
# derivation mirror fires on a conflict that (a) was NOT in the unassumed baseline and (b) RESTS
# ON the assumption, the hypothesis is REFUTED — its opposite is proven (h ⊢ ⊥ ⇒ ¬h).
#
# What this adds that forward chaining cannot do: CONTRAPOSITION. The chainer only walks rules
# forward (subject → predicate); it can never reason «all mammals are animals + no software is an
# animal + I am a software ⇒ I am NOT a mammal» — mammal is unreachable forward from software.
# Assuming «I am a mammal» makes the absurd derivable, and the mirror does the rest. (This is
# the ACTUAL question of the mammal incident — answered with a proven NO instead of an IDK.)
#
# Both polarities of the claim are attempted symmetrically (assume c → conflict ⇒ c FALSE;
# assume ¬c → conflict ⇒ c TRUE); whichever the chainer can make generative fires. A negated
# membership FACT is inert in the chainer (negated facts never extend the closure) — that arm
# skips honestly for individual subjects rather than pretending to test it.
#
# DB-agnostic like the whole evaluator package: the caller injects rules/parents/facts. The
# firing site is the polar-question IDK path (evaluation_harness.answer_zip) — he tries to PROVE
# the answer before conceding «I do not know». v1 scope: bare copular MEMBERSHIP claims (a noun
# predicate, no direct object) — the taxonomic question shape the incident lived in.
# --------------------------------------------------------------
from typing import Optional

from lib.core.tk import TKQuantifier
from lib.core.tkzip import TKZipContent

from .e_chaining import evaluator_forwardChain, _TAXO_TRUE, _TAXO_FALSE

# the assumption's premise marker: never a real doc id, so it can be required in (and then
# stripped from) the convicting conflict's premise set.
_HYP_ID = "hypothesis"

# question shapes the prover declines (v1): a NEGATIVE/¬∀-quantified polar question is not a
# bare membership claim to assume.
_SKIP_QUANTIFIERS = {TKQuantifier.NEGATIVE, TKQuantifier.NEGATED_UNIVERSAL}


def _conflicts(subject_sense, subject_uid, rules, parents, facts, edge_source):
    derived, _ = evaluator_forwardChain(subject_sense, subject_uid, rules, parents, facts,
                                        edge_source=edge_source)
    return {
        (d["predicate"], d.get("object"), bool(d.get("negated", False))): d
        for d in derived if d.get("conflict")
    }


# try to decide a membership claim by reductio ad absurdum. Returns (truth, chain, premises)
# when a proof lands — truth 1.0 (claim proven) or 0.0 (claim refuted), the chain narrating the
# assumption and the absurd it forced, premises = the KB docs the proof rests on (the assumption
# marker stripped) — or None (no proof either way; the honest IDK stands).
def evaluator_reductio(
    content: TKZipContent,
    rules: list,
    parents,
    facts: list,
    edge_source=None,
) -> Optional[tuple[float, str, list]]:
    senses = getattr(content, "senses", None) or {}
    identities = getattr(content, "identities", None) or {}
    subject_uid = identities.get("subject")
    subject_sense = senses.get("subject")
    pred = senses.get("predicate")
    if not pred or ".n." not in pred:
        return None  # membership claims only (v1) — the taxonomic question shape
    if senses.get("direct"):
        return None  # a transitive claim is not a bare copular membership
    if not subject_uid and not subject_sense:
        return None
    if getattr(content, "quantifier", None) in _SKIP_QUANTIFIERS:
        return None
    claim_negated = bool(getattr(content, "negated", False))
    subject_name = subject_uid or subject_sense

    baseline = _conflicts(subject_sense, subject_uid, rules, parents, facts, edge_source)

    for hyp_negated in (claim_negated, not claim_negated):
        if subject_uid:
            # an INDIVIDUAL claim assumes a membership FACT (the uid is the seed)
            if hyp_negated:
                continue  # a negated membership fact never extends the closure — inert, skip honestly
            extra_rules: list = []
            extra_facts = [{"subject_uid": subject_uid, "klass_sense": pred, "predicate": pred,
                            "negated": False, "source_id": _HYP_ID}]
        else:
            extra_rules = [{"subject": subject_sense, "predicate": pred, "object": None,
                            "negated": hyp_negated, "kind": "membership", "cond_props": [],
                            "strength": "universal", "source_id": _HYP_ID}]
            extra_facts = []

        found = _conflicts(subject_sense, subject_uid, rules + extra_rules, parents,
                           facts + extra_facts, edge_source)
        for sig, d in found.items():
            if sig in baseline:
                continue  # the ground was already poisoned there — an old absurd proves nothing new
            premises = [str(p) for p in d.get("premises", [])]
            if _HYP_ID not in premises:
                continue  # the absurd must REST ON the assumption, or it convicts nothing
            hyp_text = f"{subject_name} is {'not ' if hyp_negated else ''}{pred}"
            chain = (f"reductio: assume {hyp_text} -> {d['chain']}"
                     f" -> the assumption is false")
            proof_premises = sorted(p for p in premises if p != _HYP_ID)
            # the assumption refuted: if we assumed the claim itself, the claim is FALSE;
            # if we assumed its negation, the claim is PROVEN.
            truth = _TAXO_FALSE if hyp_negated == claim_negated else _TAXO_TRUE
            return (truth, chain, proof_premises)
    return None

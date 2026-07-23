# ------------------------------------------------------------------------------------------------
# THE DIRECT FACT-MATCH (2026-07-23) — the evaluator's key-for-key consultation of stored knowledge.
#
# Geometry (`_best_match`) surfaces the CLOSEST known statement; it never asks "do I already hold
# exactly THIS?". Two §2 grounding leads share that gap: «tokeniko you do not learn» grounded UNKNOWN
# though «I learn» was stored, and «is gold beautiful?» answered IDK though «gold is beautiful» was an
# active theorem. The cure is one primitive: build a claim's CONCLUSION KEY (subject/predicate/direct
# role keys + the negated flag) and look it up among stored SINGLE-CLAUSE facts whose leaf carries the
# same role keys. Same polarity ⇒ CONFIRMS; opposite polarity ⇒ REFUTES — an EXACT match, never a
# vector distance.
#
# IDENTITY-AWARE by construction: the key is read through `role_key` (identity uid FIRST, else WSD
# sense — the identity-blindness cure), so «I learn» (subject = tokeniko's uid) matches «you do not
# learn» (same uid, addressed) though their surface subjects differ. This agrees with
# `conclusion_key`'s dedup discipline: "I exist" and "tokeniko exists" share a key.
#
# DB-AGNOSTIC: the primitive works over the INJECTED axiom/theorem TKZips — no Mongo, no ids. The
# caller that owns the docs (the harness) maps the returned (kind, index) back to a document to price
# the verdict by that fact's trust (ruling 2: confidence = the matched fact's trust, no new knob).
#
# v1 SCOPE (the reductio prover's discipline): SINGLE-CLAUSE claims and SINGLE-CLAUSE, ASSERTED facts
# only. A multi-clause claim keeps the existing machinery; an attitude-wrapped clause (THAT / "I
# believe…") is not an assertion and is filtered by the assertedness gate.
# ------------------------------------------------------------------------------------------------
from collections import namedtuple
from typing import Optional

from lib.core.kb_extract import _zip_leaves, _zip_is_asserted, _leaf_is_crisp
from .e_keys import role_key

# the match verdict: which stored fact (kind + index into that kind's injected list) matched, whether
# it CONFIRMS (same polarity) or refutes (opposite), and the fact's leaf (so the caller can render the
# cited evidence). `confirms=False` is a refutation.
DirectMatch = namedtuple("DirectMatch", ["kind", "index", "confirms", "fact_leaf"])


# the polarity-free conclusion key of a leaf: (subject, predicate, direct) read identity-FIRST. two
# leaves assert the SAME proposition (modulo polarity) when their keys are equal.
def claim_key(leaf) -> tuple:
    return (role_key(leaf, "subject"), role_key(leaf, "predicate"), role_key(leaf, "direct"))


# a leaf names a proposition we can match only when it has an anchored subject AND predicate (an
# unbound ambient "you" keys to None and stays honestly unmatchable — the coreference gate's caution).
def _matchable(leaf) -> bool:
    subj, pred, _ = claim_key(leaf)
    return bool(subj) and bool(pred)


# the ONE crisp asserted leaf of a stored single-clause fact zip, else None. A compound (multi-leaf)
# zip, an attitude/IMPLY-wrapped one (not `_zip_is_asserted`), or a ◇-modal leaf is not a directly
# matchable fact (v1 scope).
def _single_fact_leaf(zip_obj):
    if zip_obj is None or not _zip_is_asserted(zip_obj.items):
        return None
    leaves = _zip_leaves(zip_obj.items)
    if len(leaves) != 1:
        return None
    leaf = leaves[0]
    return leaf if _leaf_is_crisp(leaf) else None


# consult the stored single-clause facts for the claim's exact conclusion key. axioms are tried before
# theorems (ground truth before derived knowledge); the FIRST key match wins. Returns a DirectMatch or
# None. Polarity is compared BOTH ways (the negated flag): a stored NEGATED fact refutes an affirmative
# claim and confirms a negated one, symmetrically.
def direct_fact_match(claim_leaf, axioms, theorems) -> Optional[DirectMatch]:
    if not _matchable(claim_leaf):
        return None
    key = claim_key(claim_leaf)
    claim_negated = bool(getattr(claim_leaf, "negated", False))
    for kind, zips in (("axiom", axioms or []), ("theorem", theorems or [])):
        for i, z in enumerate(zips):
            fleaf = _single_fact_leaf(z)
            if fleaf is None or claim_key(fleaf) != key:
                continue
            confirms = bool(getattr(fleaf, "negated", False)) == claim_negated
            return DirectMatch(kind, i, confirms, fleaf)
    return None


# a compact symbolic rendering of a matched fact leaf ("gold.n.01 beautiful.a.01", "tokeniko@… NOT
# learn.v.01"), read off its role keys — the cited evidence in an evaluator derivation string (the
# evaluator has no doc originals; the harness enriches with the real sentence where it does).
def render_fact(leaf) -> str:
    subj, pred, direct = claim_key(leaf)
    neg = "NOT " if getattr(leaf, "negated", False) else ""
    parts = [p for p in (subj, (neg + pred) if pred else None, direct) if p]
    return " ".join(parts).strip()

# ------------------------------------------------------------------------------------------------
# EVALUATOR — geometric comparison
# compares compiled meaning: two TKZipContent (a clause) or two TKZipItem trees, returning a fuzzy
# similarity in [0, 1] (cosine rescaled: opposite -> 0, orthogonal -> 0.5, identical -> 1).
# ------------------------------------------------------------------------------------------------
import numpy as np

from lib.core.tk import TKOperator
from lib.core.tkllc import TKLLAttitude
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from .operators import operator_similarity

# the marker (complement-type) segment of a role/indirect vector is the first 300 dims;
# the rest (300:3237) is semantic + spacetime (the "who/what/where" content).
_MARKER_SEGMENT = 300

# directional operators: the implication family, where operand ORDER encodes the relation
# ("A IMPLY B" != "B IMPLY A"). The operator sits on the consequent item, so its position in the
# sibling list carries direction. Symmetric connectives (AND/OR/EQ/XOR/XNOR/NOTEQ, THAT) are
# order-independent and stay bag-matched. Used to switch sibling-list comparison to order-aware.
_DIRECTIONAL_OPERATORS = {
    TKOperator.IMPLY,
    TKOperator.CONV,
    TKOperator.NOTIMPLY,
    TKOperator.NOTCONV,
}

# how the per-role similarities combine into the content score. tunable: the relation (predicate)
# and the agent (subject) carry the most meaning; sentiment/modality are minor. set a weight to 0
# to ignore that component (e.g. modality=0 for a pure role comparison).
_CONTENT_WEIGHTS = {
    "predicate": 0.30,
    "subject": 0.25,
    "direct": 0.20,
    "indirects": 0.15,
    "sentiment": 0.05,
    "modality": 0.05,
}

# is a role vector all-zero? a missing role (no subject/direct/...) is zero-padded by the compiler,
# so an all-zero vector means "this role is absent".
def _is_zero(vector: list[float]) -> bool:
    return not np.any(np.asarray(vector, dtype=np.float32))

# cosine similarity rescaled to [0, 1]: opposite (-1) -> 0, orthogonal (0) -> 0.5, identical (1) -> 1.
# both-zero -> 1.0 (two neutral/absent vectors match); exactly one zero -> 0.0 (no basis to match).
def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 1.0 if na == 0.0 and nb == 0.0 else 0.0
    cos = float(np.dot(va, vb) / (na * nb))
    return (cos + 1.0) / 2.0

# similarity of a fixed role slot (subject/predicate/direct). returns None when the role is absent
# in BOTH contents (skip it, neither reward nor penalize), 0.0 when present in only one (structural
# mismatch), else the rescaled cosine.
def _role_similarity(a: list[float], b: list[float]) -> float | None:
    aZero, bZero = _is_zero(a), _is_zero(b)
    if aZero and bZero:
        return None
    if aZero != bZero:
        return 0.0
    return _cosine(a, b)

# marker gate: clamped RAW cosine of two marker (complement-type) segments. 1.0 for the same
# preposition, lower for different types; used to route indirect matches by type. raw (not the
# (cos+1)/2 rescale) so different types actually suppress; both markerless -> 1.0, one markerless -> 0.
def _marker_gate(a_marker: list[float], b_marker: list[float]) -> float:
    va, vb = np.asarray(a_marker, dtype=np.float32), np.asarray(b_marker, dtype=np.float32)
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 1.0 if na == 0.0 and nb == 0.0 else 0.0
    return max(0.0, float(np.dot(va, vb) / (na * nb)))

# similarity of the two (variable-length) indirect sets, ROUTED BY COMPLEMENT TYPE. each indirect
# vector splits into a marker (type, [0:300]) and content (semantic+spacetime, [300:]); a pair is
# scored as markerGate(type) * cosine(content), so "for you" matches "for Luca" (same marker, compare
# the who/what), never "in the kitchen" (different marker -> suppressed), and a complement with no
# same-type partner gets a low best-match = compared to its absence.
# matched by soft bipartite F1 (BERTScore-style): handles differing counts, no fixed alignment.
def _indirects_similarity(a_list: list[list[float]], b_list: list[list[float]]) -> float | None:
    if not a_list and not b_list:
        return None
    if not a_list or not b_list:
        return 0.0

    def pair(ai: list[float], bj: list[float]) -> float:
        markerGate = _marker_gate(ai[:_MARKER_SEGMENT], bj[:_MARKER_SEGMENT])
        contentSim = _cosine(ai[_MARKER_SEGMENT:], bj[_MARKER_SEGMENT:])
        return markerGate * contentSim

    matrix = np.array([[pair(ai, bj) for bj in b_list] for ai in a_list], dtype=np.float32)
    recall = float(matrix.max(axis=1).mean())     # each A indirect's best (same-type) partner in B
    precision = float(matrix.max(axis=0).mean())  # each B indirect's best (same-type) partner in A
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)

# similarity of the statement-level modality scalars (each already in [0, 1]): 1 - mean abs diff.
def _modality_similarity(a: TKZipContent, b: TKZipContent) -> float:
    diffs = [abs(a.ironic - b.ironic), abs(a.dubitative - b.dubitative), abs(a.imperative - b.imperative)]
    return 1.0 - sum(diffs) / len(diffs)

# compare two TKZipContent (one flat clause each) -> fuzzy similarity in [0, 1].
# per-role geometric (cosine) similarity, combined by _CONTENT_WEIGHTS over the components that
# actually apply (roles absent in both contents are skipped and their weight redistributed).
def evaluator_compareContent(a: TKZipContent, b: TKZipContent) -> float:
    similarities: dict[str, float | None] = {
        "predicate": _role_similarity(a.predicate, b.predicate),
        "subject": _role_similarity(a.subject, b.subject),
        "direct": _role_similarity(a.direct, b.direct),
        "indirects": _indirects_similarity(a.indirects, b.indirects),
        "sentiment": _cosine(a.sentiment, b.sentiment),
        "modality": _modality_similarity(a, b),
    }

    # weighted mean over the applicable components (skip the None / not-applicable ones)
    totalWeight = sum(_CONTENT_WEIGHTS[k] for k, v in similarities.items() if v is not None)
    if totalWeight == 0.0:
        return 0.0
    return sum(_CONTENT_WEIGHTS[k] * v for k, v in similarities.items() if v is not None) / totalWeight

# ------------------------------------------------------------------------------------------------
# ITEM-LEVEL COMPARISON (the TKZipItem tree)
# a TKZipItem is either a leaf (content is a TKZipContent clause) or an internal node (content is a
# list of TKZipItem - the "brackets"), annotated with an operator and an optional THAT attitude.
# comparing two trees folds in, at each node: the content, the operator, and the attitude.
# ------------------------------------------------------------------------------------------------

# how an item's components combine. content dominates; the operator (how this clause relates to its
# siblings) is modest; the attitude (only on THAT items) is minor. tunable.
_ITEM_WEIGHTS = {"content": 0.70, "operator": 0.20, "attitude": 0.10}

# similarity of two operators, derived behaviorally from the fuzzy operator math (operators.py):
# operators that transform the same operands similarly are similar (AND~OR moderate, IMPLY~NOTIMPLY
# far, THAT isolated). just a thin alias so the item logic reads consistently.
def _operator_similarity(opA, opB) -> float:
    return operator_similarity(opA, opB)

# similarity of two THAT attitudes. None when neither item carries one (skip, do not penalize);
# 0.5 when only one does (structural mismatch); else blends class match with confidence closeness.
def _attitude_similarity(attA: TKLLAttitude | None, attB: TKLLAttitude | None) -> float | None:
    if attA is None and attB is None:
        return None
    if attA is None or attB is None:
        return 0.5
    klassSim = 1.0 if attA.klass == attB.klass else 0.5
    confSim = 1.0 - abs(attA.confidence - attB.confidence)
    return (klassSim + confSim) / 2.0

# similarity of two item payloads (the recursive part): leaf vs leaf -> content comparison;
# list vs list -> sibling-set comparison; leaf vs list (shape mismatch, e.g. a single clause vs a
# coordinated one) -> F1 of the singleton {leaf} against the list, so extra items in the list are
# penalized (taking just the best match would ignore the unmatched clauses).
def _compare_payload(ca, cb) -> float:
    aLeaf, bLeaf = isinstance(ca, TKZipContent), isinstance(cb, TKZipContent)
    if aLeaf and bLeaf:
        return evaluator_compareContent(ca, cb)
    if not aLeaf and not bLeaf:
        return _compare_item_list(ca, cb)

    leaf, items = (ca, cb) if aLeaf else (cb, ca)
    if not items:
        return 0.0
    sims = [_compare_payload(leaf, it.content) for it in items]
    recall = max(sims)                 # the leaf's best partner in the list
    precision = sum(sims) / len(sims)  # each list item's match to the (only) leaf
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)

# does any item in a sibling list carry a directional operator (implication family)? if so the
# list's operand ORDER is meaningful (the operator sits on the consequent) and the two lists must
# be compared positionally, not as a bag.
def _has_directional(items: list[TKZipItem]) -> bool:
    return any(it.op in _DIRECTIONAL_OPERATORS for it in items)

# ORDER-AWARE comparison of two sibling lists: align item i of A with item i of B (positional),
# so "A IMPLY B" no longer matches "B IMPLY A" (the operator-bearing consequent lands in a
# different slot). Extra items on either side are unmatched (scored 0), penalizing length
# mismatch the same way the bag F1 does. Used only when a directional operator is present.
def _compare_item_list_ordered(la: list[TKZipItem], lb: list[TKZipItem]) -> float:
    n = max(len(la), len(lb))
    if n == 0:
        return 1.0
    sims = [evaluator_compareItem(la[i], lb[i]) if i < len(la) and i < len(lb) else 0.0 for i in range(n)]
    return sum(sims) / n

# similarity of two (variable-length) sibling lists. When EITHER list carries a directional
# operator (IMPLY/CONV/NOTIMPLY/NOTCONV), operand order encodes direction, so they are compared
# positionally (_compare_item_list_ordered) — "A IMPLY B" then scores below "B IMPLY A".
# Otherwise (purely symmetric connectives: AND/OR/EQ/...) order is irrelevant, so the lists are
# bag-matched by soft bipartite F1 (BERTScore-style) over full item similarities, aligning items
# by combined operator + attitude + content regardless of position.
def _compare_item_list(la: list[TKZipItem], lb: list[TKZipItem]) -> float:
    if not la and not lb:
        return 1.0
    if not la or not lb:
        return 0.0

    if _has_directional(la) or _has_directional(lb):
        return _compare_item_list_ordered(la, lb)

    matrix = np.array([[evaluator_compareItem(ai, bj) for bj in lb] for ai in la], dtype=np.float32)
    recall = float(matrix.max(axis=1).mean())
    precision = float(matrix.max(axis=0).mean())
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)

# compare two TKZipItem trees -> fuzzy similarity in [0, 1]: content (recursive) + operator +
# attitude, combined by _ITEM_WEIGHTS over the components that apply.
def evaluator_compareItem(a: TKZipItem, b: TKZipItem) -> float:
    components: dict[str, float | None] = {
        "content": _compare_payload(a.content, b.content),
        "operator": _operator_similarity(a.op, b.op),
        "attitude": _attitude_similarity(a.attitude, b.attitude),
    }

    totalWeight = sum(_ITEM_WEIGHTS[k] for k, v in components.items() if v is not None)
    if totalWeight == 0.0:
        return 0.0
    return sum(_ITEM_WEIGHTS[k] * v for k, v in components.items() if v is not None) / totalWeight

# compare two whole zips (convenience wrapper over their root items)
def evaluator_compareZip(a: TKZip, b: TKZip) -> float:
    return evaluator_compareItem(a.items, b.items)

# ------------------------------------------------------------------------------------------------
# ENTITY-LINKING (Slice 3a)
# the demonstrable same-individual primitive: identity lives in the symbolic uid (out of band of the
# 2925 geometry). returns True if both clauses name the SAME individual in `role`, False if they name
# DIFFERENT individuals, None when either side is unknown (no uid for that role — can't decide).
# ------------------------------------------------------------------------------------------------
def evaluator_sameIndividual(a: TKZipContent, b: TKZipContent, role: str = "subject") -> bool | None:
    ua, ub = a.identities.get(role), b.identities.get(role)
    if ua is None or ub is None:
        return None
    return ua == ub

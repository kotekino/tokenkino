# ------------------------------------------------------------------------------------------------
# EVALUATOR
# geometric comparison of compiled meaning. the first building block compares two TKZipContent
# (one flat clause each) and returns a fuzzy similarity in [0, 1].
# ------------------------------------------------------------------------------------------------
import numpy as np

from lib.core.tkzip import TKZipContent

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

# similarity of the two (variable-length) indirect sets. best practice for comparing two bags of
# embeddings of different cardinality: soft bipartite matching, BERTScore-style.
#   recall    = mean over A of its best match in B   (does B cover each A indirect?)
#   precision = mean over B of its best match in A   (does A cover each B indirect?)
#   score     = F1 (harmonic mean)
# this needs no fixed alignment or equal counts: extra/unmatched indirects on either side drag down
# precision or recall, and F1 balances the two. (An optimal 1-1 assignment via the Hungarian
# algorithm is the stricter alternative, but it needs scipy and forbids many-to-one matches; the
# greedy best-match F1 is the lighter, standard choice and is symmetric.)
def _indirects_similarity(a_list: list[list[float]], b_list: list[list[float]]) -> float | None:
    if not a_list and not b_list:
        return None
    if not a_list or not b_list:
        return 0.0

    matrix = np.array([[_cosine(ai, bj) for bj in b_list] for ai in a_list], dtype=np.float32)
    recall = float(matrix.max(axis=1).mean())     # each A indirect's best partner in B
    precision = float(matrix.max(axis=0).mean())  # each B indirect's best partner in A
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

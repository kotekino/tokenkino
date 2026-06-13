# ------------------------------------------------------------------------------------------------
# FUZZY OPERATORS
# the logical operators as fuzzy truth functions f(a, b) -> [-1, 1] (value = truth degree:
# -1 false, 0 unknown, +1 true), plus a behavioral similarity between operators derived from how
# differently they transform the same operands. foundational math, reusable by the fusion engine.
# NB: the [-1,1] formulas below (esp. IMPLY/EQ, and NOT = -x) are the working definitions per the
# README (min/max/negation/Gödel) — confirm/adjust against the intended operator math.
# ------------------------------------------------------------------------------------------------
import numpy as np

from lib.core.tk import TKOperator

# --- truth functions (binary; the unary NOT ignores b) ---
def _not(a: float, b: float = 0.0) -> float:
    return -a

def _and(a: float, b: float) -> float:
    return min(a, b)

def _or(a: float, b: float) -> float:
    return max(a, b)

def _andnot(a: float, b: float) -> float:
    return min(a, -b)

def _ornot(a: float, b: float) -> float:
    return max(a, -b)

# Gödel implication, mapped through [0,1]: a->b = 1 if a<=b else b
def _imply(a: float, b: float) -> float:
    A, B = (a + 1.0) / 2.0, (b + 1.0) / 2.0
    g = 1.0 if A <= B else B
    return 2.0 * g - 1.0

def _conv(a: float, b: float) -> float:        # converse implication
    return _imply(b, a)

def _notimply(a: float, b: float) -> float:
    return -_imply(a, b)

def _notconv(a: float, b: float) -> float:
    return -_conv(a, b)

def _eq(a: float, b: float) -> float:           # Gödel biconditional
    return min(_imply(a, b), _imply(b, a))

def _noteq(a: float, b: float) -> float:
    return -_eq(a, b)

# truth-functional operators (THAT is excluded: it reifies a proposition, it is not truth-functional)
_OPERATOR_FUNCTIONS = {
    TKOperator.NOT: _not,
    TKOperator.AND: _and,
    TKOperator.OR: _or,
    TKOperator.ANDNOT: _andnot,
    TKOperator.ORNOT: _ornot,
    TKOperator.IMPLY: _imply,
    TKOperator.CONV: _conv,
    TKOperator.NOTIMPLY: _notimply,
    TKOperator.NOTCONV: _notconv,
    TKOperator.EQ: _eq,
    TKOperator.XNOR: _eq,    # logical equivalence == biconditional
    TKOperator.NOTEQ: _noteq,
    TKOperator.XOR: _noteq,  # exclusive-or == negated equivalence
}

# --- behavioral similarity matrix (precomputed once at import) ---
# sample (a, b) on a grid in [-1,1]^2, run every operator, then
#   distance(opA, opB) = mean |fA(a,b) - fB(a,b)|   (range is 2)
#   similarity         = 1 - distance / 2           (identical -> 1, maximally opposite -> 0)
_OP_GRID_STEPS = 21

def _build_similarity_matrix() -> dict[tuple[TKOperator, TKOperator], float]:
    axis = [(-1.0 + 2.0 * i / (_OP_GRID_STEPS - 1)) for i in range(_OP_GRID_STEPS)]
    grid = [(a, b) for a in axis for b in axis]

    outputs = {op: np.array([fn(a, b) for a, b in grid], dtype=np.float64) for op, fn in _OPERATOR_FUNCTIONS.items()}

    matrix: dict[tuple[TKOperator, TKOperator], float] = {}
    for opA, outA in outputs.items():
        for opB, outB in outputs.items():
            distance = float(np.mean(np.abs(outA - outB)))
            matrix[(opA, opB)] = 1.0 - distance / 2.0
    return matrix

_OPERATOR_SIMILARITY = _build_similarity_matrix()

# similarity of two operators in [0, 1], derived from their fuzzy behavior. THAT is not
# truth-functional, so it is isolated: identical to itself, 0 to every connective (a THAT clause's
# real comparison is its attitude, handled separately by the evaluator).
def operator_similarity(opA: TKOperator, opB: TKOperator) -> float:
    if opA == opB:
        return 1.0
    if opA == TKOperator.THAT or opB == TKOperator.THAT:
        return 0.0
    return _OPERATOR_SIMILARITY.get((opA, opB), 0.0)

# ------------------------------------------------------------------------------------------------
# FUZZY OPERATORS
# the logical operators as fuzzy truth functions f(a, b) -> [0, 1] (value = truth degree:
# 0 false, 0.5 unknown, 1 true), plus a behavioral similarity between operators derived from how
# differently they transform the same operands. foundational math, reusable by the reasoning engine.
# NB: the operators combine the TRUTH values of clauses (each a grounded TKZipContent in [0,1]), NOT
# the vectors: comparing flat content needs no operators, only the relations between contents do.
# ------------------------------------------------------------------------------------------------
import numpy as np

from lib.core.tk import TKOperator

# --- truth functions on [0, 1] (binary; the unary NOT ignores b) ---
def _not(a: float, b: float = 0.0) -> float:
    return 1.0 - a

def _and(a: float, b: float) -> float:
    return min(a, b)

def _or(a: float, b: float) -> float:
    return max(a, b)

def _xor(a: float, b: float) -> float:
    return max(min(a, 1.0 - b), min(1.0 - a, b))

def _xnor(a: float, b: float) -> float:
    return 1.0 - _xor(a, b)

# Gödel implication on [0, 1]: a -> b = 1 if a <= b else b
def _imply(a: float, b: float) -> float:
    return 1.0 if a <= b else b

def _conv(a: float, b: float) -> float:        # converse implication: b -> a
    return _imply(b, a)

def _eq(a: float, b: float) -> float:           # Gödel biconditional
    return min(_imply(a, b), _conv(a, b))

def _andnot(a: float, b: float) -> float:
    return min(a, 1.0 - b)

def _ornot(a: float, b: float) -> float:
    return max(a, 1.0 - b)

def _notimply(a: float, b: float) -> float:
    return 1.0 - _imply(a, b)

def _notconv(a: float, b: float) -> float:
    return 1.0 - _conv(a, b)

def _noteq(a: float, b: float) -> float:
    return 1.0 - _eq(a, b)

# truth-functional operators (THAT is excluded: it reifies a proposition, it is not truth-functional).
# XOR/XNOR are their own functions (the standard fuzzy symmetric difference and its complement); they
# are NO LONGER aliased to NOTEQ/EQ — XNOR = 1-XOR differs from EQ = min(imply, conv) in fuzzy logic.
_OPERATOR_FUNCTIONS = {
    TKOperator.NOT: _not,
    TKOperator.AND: _and,
    TKOperator.OR: _or,
    TKOperator.XOR: _xor,
    TKOperator.XNOR: _xnor,
    TKOperator.ANDNOT: _andnot,
    TKOperator.ORNOT: _ornot,
    TKOperator.IMPLY: _imply,
    TKOperator.CONV: _conv,
    TKOperator.NOTIMPLY: _notimply,
    TKOperator.NOTCONV: _notconv,
    TKOperator.EQ: _eq,
    TKOperator.NOTEQ: _noteq,
}

# apply an operator to truth value(s) in [0, 1] -> a truth value in [0, 1]. the reasoning engine
# (e_statement) folds a statement's clause truths through its operator tree with this. NOT is unary
# (b is ignored); THAT is not truth-functional, so it raises (callers handle THAT before this).
def operator_truth(op: TKOperator, a: float, b: float = None) -> float:
    fn = _OPERATOR_FUNCTIONS.get(op)
    if fn is None:
        raise ValueError(f"operator {op} is not truth-functional")
    return fn(a, b if b is not None else 0.0)

# --- behavioral similarity matrix (precomputed once at import) ---
# sample (a, b) on a grid in [0,1]^2, run every operator, then
#   distance(opA, opB) = mean |fA(a,b) - fB(a,b)|   (range is 1)
#   similarity         = 1 - distance               (identical -> 1, maximally opposite -> 0)
_OP_GRID_STEPS = 21

def _build_similarity_matrix() -> dict[tuple[TKOperator, TKOperator], float]:
    axis = [i / (_OP_GRID_STEPS - 1) for i in range(_OP_GRID_STEPS)]
    grid = [(a, b) for a in axis for b in axis]

    outputs = {op: np.array([fn(a, b) for a, b in grid], dtype=np.float64) for op, fn in _OPERATOR_FUNCTIONS.items()}

    matrix: dict[tuple[TKOperator, TKOperator], float] = {}
    for opA, outA in outputs.items():
        for opB, outB in outputs.items():
            distance = float(np.mean(np.abs(outA - outB)))
            matrix[(opA, opB)] = 1.0 - distance
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

# ------------------------------------------------------------------------------------------------
# EVALUATOR — statement evaluation
# evaluate a whole input (TKZip) against tokeniko's knowledge:
#   1. ground each leaf clause (TKZipContent) against the definitions  -> per-clause truth in [0,1]
#      (no operators: the content is flat, the comparison is purely geometric)
#   2. FOLD those clause truths through the input's operator tree (operator_truth, fuzzy [0,1]) to
#      get the statement's overall truth — e.g. A1 IMPLY (A2 AND A3) -> IMPLY(T1, AND(T2, T3))
#   3. if the input relates clauses, require a known axiom/theorem to cover the relation
#   4. combine -> RESOLVED (grounded + relation known, truth = folded) or INSUFFICIENT (something
#      is missing, truth = 0.5)
# The INCONSISTENT outcome (operator-math rule-violation detection + missing-variable tracking) is
# scaffolded by EvaluatorResult but DEFERRED to the reasoning engine.
# The evaluator stays DB-agnostic: the caller loads and injects definitions / axioms / theorems.
#
# Operator/tree convention (pinned empirically by compiling representative sentences):
#   a sibling list[TKZipItem] folds LEFT-TO-RIGHT — item 0 is the seed (its op is AND in practice),
#   and each later item's op combines the running accumulator with that item's truth
#   (acc = op_i(acc, truth_i)). The operator sits on the CONSEQUENT, so "A IMPLY B" (B at index 1,
#   op=IMPLY) folds IMPLY(T_A, T_B) and differs from "B IMPLY A". THAT is not truth-functional: its
#   complement truth is modulated toward 0.5 by the attitude confidence, then conjoined. NOT is a
#   defensive unary case (observed negation is encoded inside the clause vector, not as a NOT op).
# ------------------------------------------------------------------------------------------------
from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.tk import TKOperator
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from .e_compare import evaluator_compareZip
from .e_truth import evaluator_groundContent
from .operators import operator_truth

# a clause is decisively grounded when its truth is far enough from neutral 0.5 (affirmed or denied
# by some definition); within this band it is treated as ungrounded (no definition decides it).
_GROUNDING_MARGIN = 0.15
# an axiom/theorem counts as covering the input's relation when the zip similarity clears this.
_RELATION_MATCH_THRESHOLD = 0.85

# collect every leaf TKZipContent of an item tree, in order
def _collect_contents(item: TKZipItem) -> list[TKZipContent]:
    content = item.content
    if isinstance(content, TKZipContent):
        return [content]
    result: list[TKZipContent] = []
    if isinstance(content, list):
        for child in content:
            result.extend(_collect_contents(child))
    return result

# truth of one item: its leaf grounding (or the fold of its children), then — for a THAT item —
# pulled toward neutral 0.5 by the attitude confidence ("I know X" keeps more of X's truth than
# "I believe X"). non-THAT items carry no attitude, so they are returned unmodulated.
def _self_truth(item: TKZipItem, ground) -> float:
    content = item.content
    if isinstance(content, TKZipContent):
        t = ground(content)
    else:
        t = _fold_list(content, ground)
    if item.attitude is not None:
        t = 0.5 + (t - 0.5) * item.attitude.confidence
    return t

# fold a sibling list into one truth, left-to-right. item 0 seeds the accumulator (a stray NOT on it
# negates the seed); each later item's op combines acc with its truth. NOT -> "and not" (acc AND ¬t);
# THAT -> conjoin its (already attitude-modulated) complement truth; everything else applies its
# fuzzy truth function directly via operator_truth.
def _fold_list(items: list[TKZipItem], ground) -> float:
    if not items:
        return 0.5
    acc = _self_truth(items[0], ground)
    if items[0].op == TKOperator.NOT:
        acc = 1.0 - acc
    for item in items[1:]:
        t = _self_truth(item, ground)
        if item.op == TKOperator.NOT:
            acc = operator_truth(TKOperator.AND, acc, 1.0 - t)
        elif item.op == TKOperator.THAT:
            acc = operator_truth(TKOperator.AND, acc, t)
        else:
            acc = operator_truth(item.op, acc, t)
    return acc

# fold the whole statement tree (root item) into a single truth in [0,1].
def _fold_statement(root: TKZipItem, ground) -> float:
    content = root.content
    if isinstance(content, TKZipContent):
        return _self_truth(root, ground)
    return _fold_list(content, ground) if isinstance(content, list) else 0.5

# best geometric match of the input against the injected knowledge. returns (score, kind, index)
# with kind in {"axiom","theorem"} and index into that kind's list; (None, None, None) if no
# knowledge was provided. the score is kept even when below threshold so the caller can surface the
# closest known statement.
def _best_match(statement: TKZip, axioms: list[TKZip], theorems: list[TKZip]):
    best: float | None = None
    kind: str | None = None
    index: int | None = None
    for i, axiom in enumerate(axioms):
        score = evaluator_compareZip(statement, axiom)
        if best is None or score > best:
            best, kind, index = score, "axiom", i
    for i, theorem in enumerate(theorems):
        score = evaluator_compareZip(statement, theorem)
        if best is None or score > best:
            best, kind, index = score, "theorem", i
    return best, kind, index

# evaluate an input statement. definitions are the grounding set (TKZipContent each); axioms and
# theorems are the relational knowledge (TKZip each). returns a structured EvaluatorResult.
def evaluator_evaluateStatement(
    statement: TKZip,
    definitions: list[TKZipContent],
    axioms: list[TKZip] | None = None,
    theorems: list[TKZip] | None = None,
) -> EvaluatorResult:
    axioms = axioms or []
    theorems = theorems or []

    # 1. ground each leaf clause against the definitions
    contents = _collect_contents(statement.items)
    groundings = [evaluator_groundContent(c, definitions) for c in contents]

    # 2. fold the clause truths through the operator tree -> the statement's overall truth.
    # map each leaf content (by identity) to its grounding; the fold walks the same objects.
    truth_by_id = {id(c): g for c, g in zip(contents, groundings)}
    folded = _fold_statement(statement.items, lambda c: truth_by_id.get(id(c), 0.5))

    missing: list[str] = []
    # clauses whose core arguments are unknown vocabulary (generic, no dictionary sense): a distinct,
    # actionable INSUFFICIENT reason — tokeniko doesn't know the word(s), the seam for an ask-and-learn.
    unknown = sum(1 for c in contents if getattr(c, "unknown", False))
    if unknown:
        missing.append(f"{unknown} clause(s) reference unknown vocabulary")
    # clauses that are known but no definition decides them (truth sits in the neutral band)
    ungrounded = sum(1 for c, g in zip(contents, groundings)
                     if not getattr(c, "unknown", False) and abs(g - 0.5) < _GROUNDING_MARGIN)
    if ungrounded:
        missing.append(f"{ungrounded} clause(s) not grounded by any definition")

    # 3. relational match — always computed (to surface the closest known statement), but only
    # REQUIRED when the input actually relates clauses (more than one clause).
    relationMatch, matchedKind, matchedIndex = _best_match(statement, axioms, theorems)
    if len(contents) > 1 and (relationMatch is None or relationMatch < _RELATION_MATCH_THRESHOLD):
        missing.append("no matching axiom/theorem covers the relation")

    # 4. combine
    if missing:
        return EvaluatorResult(
            truth=0.5, status=EvaluatorStatus.INSUFFICIENT, groundings=groundings, missing=missing,
            relationMatch=relationMatch, matchedKind=matchedKind, matchedIndex=matchedIndex,
        )

    # RESOLVED — clauses grounded and (if relational) a known statement covers the relation.
    # truth = the clause truths folded through the input's operator tree (fuzzy [0,1]).
    return EvaluatorResult(
        truth=folded, status=EvaluatorStatus.RESOLVED, groundings=groundings,
        relationMatch=relationMatch, matchedKind=matchedKind, matchedIndex=matchedIndex,
    )

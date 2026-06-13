# ------------------------------------------------------------------------------------------------
# EVALUATOR — statement evaluation (STAGED)
# evaluate a whole input (TKZip) against tokeniko's knowledge:
#   1. ground each leaf clause (TKZipContent) against the definitions  -> per-clause truth
#   2. if the input has relations (multiple clauses / operators), match it geometrically against
#      the known axioms/theorems
#   3. combine -> RESOLVED (grounded + relation known) or INSUFFICIENT (something is missing)
# The INCONSISTENT outcome (applying the operator math to detect logic-rule violations + tracking
# the missing "variables") is scaffolded by EvaluatorResult but DEFERRED to the reasoning engine.
# The evaluator stays DB-agnostic: the caller loads and injects definitions / axioms / theorems.
# ------------------------------------------------------------------------------------------------
from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from .e_compare import evaluator_compareZip
from .e_truth import evaluator_groundContent

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

    missing: list[str] = []
    ungrounded = sum(1 for g in groundings if abs(g - 0.5) < _GROUNDING_MARGIN)
    if ungrounded:
        missing.append(f"{ungrounded} clause(s) not grounded by any definition")

    # 2. relational match — only needed when the input actually relates clauses
    if len(contents) > 1:
        knowledge = axioms + theorems
        bestMatch = max((evaluator_compareZip(statement, k) for k in knowledge), default=0.0)
        if bestMatch < _RELATION_MATCH_THRESHOLD:
            missing.append("no matching axiom/theorem covers the relation")

    # 3. combine
    if missing:
        return EvaluatorResult(truth=0.5, status=EvaluatorStatus.INSUFFICIENT, groundings=groundings, missing=missing)

    # RESOLVED. provisional truth = the weakest-grounded clause (conservative conjunctive bound);
    # the operator-driven combination of clause truths through the relation is the deferred engine.
    truth = min(groundings) if groundings else 0.5
    return EvaluatorResult(truth=truth, status=EvaluatorStatus.RESOLVED, groundings=groundings)

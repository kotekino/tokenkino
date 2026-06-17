# the evaluator package: geometric comparison of compiled meaning + truth grounding.
# split by section: operators (fuzzy operator math), e_compare (geometric similarity),
# e_truth (grounding a clause vs definitions), e_statement (staged statement evaluation).
from .e_compare import evaluator_compareContent, evaluator_compareItem, evaluator_compareZip
from .e_truth import evaluator_groundContent
from .e_statement import evaluator_evaluateStatement
from .e_label import evaluator_assignWord, TKWordLabel
from .e_consistency import evaluator_classifyForm, FormClass
from .operators import operator_similarity, operator_truth

__all__ = [
    "evaluator_compareContent",
    "evaluator_compareItem",
    "evaluator_compareZip",
    "evaluator_groundContent",
    "evaluator_evaluateStatement",
    "evaluator_assignWord",
    "TKWordLabel",
    "evaluator_classifyForm",
    "FormClass",
    "operator_similarity",
    "operator_truth",
]

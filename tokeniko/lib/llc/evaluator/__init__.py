# the evaluator package: geometric comparison of compiled meaning + truth grounding.
# split by section: operators (fuzzy operator math), e_compare (geometric similarity),
# e_truth (grounding a clause vs definitions), e_statement (staged statement evaluation).
from .e_compare import evaluator_compareContent, evaluator_compareItem, evaluator_compareZip, evaluator_sameIndividual
from .e_truth import evaluator_groundContent
from .e_statement import evaluator_evaluateStatement
from .e_label import evaluator_assignWord, TKWordLabel
from .e_consistency import evaluator_classifyForm, FormClass
from .e_chaining import evaluator_forwardChain, evaluator_chainGround, evaluator_groundIndividualFact
from .e_hypothesis import evaluator_reductio
from .e_wh_solve import evaluator_solveWh
from .e_keys import role_key
from .e_relations import (
    relations_isa_ancestors, relations_subsumes, relations_disjoint,
    relations_part_ancestors, relations_is_part_of,
)
from .operators import operator_similarity, operator_truth

__all__ = [
    "evaluator_compareContent",
    "evaluator_compareItem",
    "evaluator_compareZip",
    "evaluator_sameIndividual",
    "evaluator_groundContent",
    "evaluator_evaluateStatement",
    "evaluator_assignWord",
    "TKWordLabel",
    "evaluator_classifyForm",
    "FormClass",
    "evaluator_forwardChain",
    "evaluator_chainGround",
    "evaluator_groundIndividualFact",
    "evaluator_reductio",
    "evaluator_solveWh",
    "role_key",
    "relations_isa_ancestors",
    "relations_subsumes",
    "relations_disjoint",
    "relations_part_ancestors",
    "relations_is_part_of",
    "operator_similarity",
    "operator_truth",
]

# ------------------------------------------------------------------------------------------------
# EVALUATOR — truth grounding
# ground a clause (TKZipContent) against the definitions: a fuzzy truth in [0, 1] where 1 = the
# clause matches a definition, 0 = it is the perfect opposite of one, 0.5 = neutral (no match nor
# opposite). definitions are tokeniko's purely-semantic ground truths (the vocabulary/playground).
# ------------------------------------------------------------------------------------------------
from lib.core.tkzip import TKZipContent
from .e_compare import evaluator_compareContent

# truth of a single clause vs the definition set. each definition comparison is in [0, 1]
# (1 affirms, 0 contradicts, 0.5 neutral); the clause's truth is the MOST DECISIVE definition,
# i.e. the comparison furthest from 0.5 (a strong match or a strong opposite both decide it).
# no definitions -> 0.5 (nothing to ground against).
# NB: a clause that BOTH strongly matches one definition and strongly opposes another is a grounding
# conflict — that signal is left for the deferred inconsistency reasoning engine.
def evaluator_groundContent(content: TKZipContent, definitions: list[TKZipContent]) -> float:
    if not definitions:
        return 0.5
    # the clause's core arguments are all unknown vocabulary (generic, no semantic anchor): there is
    # nothing to ground, so a contentless clause must stay NEUTRAL rather than spuriously matching any
    # "X is Y" definition ("a wug is a blicket" -> 0.885). 0.5 -> INSUFFICIENT (and the ask reflex).
    if content.unknown:
        return 0.5
    sims = [evaluator_compareContent(content, d) for d in definitions]
    truth = max(sims, key=lambda s: abs(s - 0.5))
    # clause-level negation (Decision 1): the clause asserts ¬P, so its truth is the complement of
    # the positive grounding. negation is a DISCRETE flag (the geometry compares the affirmative
    # meaning); flipping it here lets the truth-fold in e_statement propagate it for free.
    # NB the definitions themselves are affirmative single-clause semantic facts; a negated
    # definition is out of scope. geometric (evaluator_compareContent) negation-awareness is a
    # documented follow-up (Phase 3) and intentionally NOT handled here.
    return 1.0 - truth if content.negated else truth

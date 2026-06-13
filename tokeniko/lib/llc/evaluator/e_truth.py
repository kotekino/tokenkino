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
    sims = [evaluator_compareContent(content, d) for d in definitions]
    return max(sims, key=lambda s: abs(s - 0.5))

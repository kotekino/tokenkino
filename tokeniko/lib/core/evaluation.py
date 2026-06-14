# --------------------------------------------------
# evaluation result
# the structured output of evaluating a statement against tokeniko's knowledge (definitions for
# grounding, axioms/theorems for relations). supports three outcomes; the INCONSISTENT branch
# (operator-math rule checks) is scaffolded here but produced by the future reasoning engine.
# --------------------------------------------------
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class EvaluatorStatus(str, Enum):
    RESOLVED = "resolved"                 # grounded + relations matched: a usable truth value
    INSUFFICIENT = "insufficient_knowledge"  # neutral 0.5: missing definitions/axioms to decide
    INCONSISTENT = "inconsistent"         # truth 0: violates a hardwired logic/math rule

class EvaluatorResult(BaseModel):
    truth: float = Field(default=0.5)              # fuzzy truth in [0, 1]
    status: EvaluatorStatus = Field(default=EvaluatorStatus.INSUFFICIENT)
    groundings: list[float] = Field(default_factory=list)  # per-content truth vs definitions
    missing: list[str] = Field(default_factory=list)       # what knowledge is missing (INSUFFICIENT)
    inconsistency: Optional[str] = None                    # which rule/where (INCONSISTENT; future)
    # the closest known relation (set whenever axioms/theorems were provided, even if INSUFFICIENT);
    # the caller (service) maps matchedKind + matchedIndex back to the concrete document id.
    relationMatch: Optional[float] = None                  # best zip similarity to a known statement
    matchedKind: Optional[str] = None                      # "axiom" | "theorem"
    matchedIndex: Optional[int] = None                     # position within that kind's injected list

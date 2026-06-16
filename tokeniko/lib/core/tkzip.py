# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
from typing import Optional, Union
from pydantic import BaseModel, Field
from lib.core.tk import TKOperator
from lib.core.tkllc import TKLLAttitude

# zip content: can be a content or another llcitem (recursive)
class TKZipContent(BaseModel):
    # statement properties
    ironic: float = Field(default=0.5)
    dubitative: float = Field(default=0.5)
    imperative: float = Field(default=0.5)
    # clause-level negation: the clause asserts ¬P (verbal/copular "not", determiner "no", "never").
    # kept as a DISCRETE recoverable signal because negation otherwise vanishes into the role vectors
    # (cos("I am happy", "I am not happy") == 1.0). the evaluator flips the grounded truth on this.
    negated: bool = Field(default=False)
    # the clause's core arguments are all UNKNOWN vocabulary (generic fallback, no dictionary sense):
    # there is nothing to ground against, so a contentless clause must NOT score a spurious match
    # ("a wug is a blicket" -> 0.885). the evaluator returns neutral 0.5 (-> INSUFFICIENT / ask) on this.
    unknown: bool = Field(default=False)
    sentiment: list[float] = Field(default_factory=lambda: ([0.0] * 2925))
    # statement core elements
    subject: Optional[list[float]] = Field(default_factory=list, min_length=3237, max_length=3237) # 300 (marker) + 2925 (semantic) + spacetime (12)
    predicate: Optional[list[float]] = Field(default_factory=list, min_length=3237, max_length=3237)
    direct: Optional[list[float]] = Field(default_factory=list, min_length=3237, max_length=3237)
    indirects: list[list[float]] = Field(default_factory=list) 

# zip item: can be a statement or an llcitem (recursive)
class TKZipItem(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND)
    attitude: Optional[TKLLAttitude] = None  # carried from the LLC THAT item (propositional X)
    content: TKZipItemPayload = None

# zip 
class TKZip(BaseModel):
    map: list[float] = Field(default_factory=list, min_length=8, max_length=8)
    items: TKZipItem = Field(default_factory=TKZipItem)

# payload for item
TKZipItemPayload = Union[list[TKZipItem], TKZipContent]
TKZipItem.model_rebuild()
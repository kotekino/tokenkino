# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
from typing import Optional, Union
from pydantic import BaseModel, Field
from lib.core.tk import TKOperator, TKQuantifier
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
    # reflexive identity clause: the evaluator PINS it (a=a -> true, a≠a -> false) instead of treating
    # it as a free atom. polarity (which of the two) is carried by `negated`.
    reflexive: bool = Field(default=False)
    # quantifier read off the SUBJECT's determiner (all/some/no/the/bare). the evaluator combines it
    # with the relational (is_a) verdict: NEGATIVE flips the verdict (XOR with `negated`).
    quantifier: TKQuantifier = Field(default=TKQuantifier.GENERIC)
    # WSD-assigned WordNet synset key per populated role ("subject"/"predicate"/"direct"/"indirect0"…).
    # carried (out of band of the geometry) so the evaluator can reach the is_a relations graph for
    # taxonomic grounding/refutation. only roles whose entity has a non-empty sense appear.
    senses: dict[str, str] = Field(default_factory=dict)
    # context-scoped identity uid per entity-linked role ("subject"/"predicate"/"direct"/"indirect0"…).
    # the identity-bridge target (parallel to senses): referential identity carried out of band of the
    # 2925 geometry so the evaluator can recognize the SAME individual across statements. only roles
    # whose entity is an entity-linked named individual appear.
    identities: dict[str, str] = Field(default_factory=dict)
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
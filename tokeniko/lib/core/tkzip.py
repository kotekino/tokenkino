# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
from typing import Optional, Union
from pydantic import BaseModel, Field
from lib.core.tk import TKOperator
from lib.core.tkllc import TKLLSpacetimeMap

# llc content: can be a content or another llcitem (recursive)
class TKZipContent(BaseModel):
    # properties
    ironic: float = Field(default=0.5)
    dubitative: float = Field(default=0.5)
    imperative: float = Field(default=0.5)
    sentiment: list[float] = Field(default_factory=lambda: ([0.0] * 2925))
    # statement core elements
    subject: Optional[list[float]] = Field(default_factory=list, min_length=2925, max_length=2925)
    predicate: Optional[list[float]] = Field(default_factory=list, min_length=2925, max_length=2925)
    direct: Optional[list[float]] = Field(default_factory=list, min_length=2925, max_length=2925)
    indirects: list[list[float]] = Field(default_factory=list, min_length=3225, max_length=3225) # 300 (marker) + 2925
    # spacetime
    size: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the size of the entity in spacetime
    position: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the center of the entity in spacetime
    velocity: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the velocity of the entity in spacetime

# llc item: can be a statement or an llcitem (recursive)
class TKZipItem(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND)
    content: TKZipItemPayload = None 

# llc 
class TKZip(BaseModel):
    map: TKLLSpacetimeMap = Field(default_factory=TKLLSpacetimeMap)
    items: TKZipItem = Field(default_factory=TKZipItem)

# payload for item
TKZipItemPayload = Union[list[TKZipItem], TKZipContent]
TKZipItem.model_rebuild()
# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
from typing import Optional, Union
from pydantic import BaseModel, Field
from lib.core.tk import TKAux, TKClauseType, TKMarker, TKOperator

class TKLLSpacetime(BaseModel):
    size: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the size of the entity in spacetime
    position: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the center of the entity in spacetime
    velocity: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the velocity of the entity in spacetime

# the map of the relative spacetime in the context of the statement
class TKLLSpacetimeMap(BaseModel):
    tbounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # [min, max]
    xbounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # [min, max]
    ybounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # [min, max]
    zbounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # [min, max]

#  property related the sentence by the talker point of view
class TKLLProperties(BaseModel):
    ironic: float = Field(default=0.5) # literal 0 / neutral 0.5 / ironic 1
    dubitative: float = Field(default=0.5) # statement 0 / question 1
    imperative: float = Field(default=0.5) # neutral 0 / order 1
    sentiment: list[float] = Field(default_factory=lambda: ([0.0] * 2925)) # related to one or more base words

# entity: can have different semantic vectors
class TKLLEntity(BaseModel):
    id: int
    referenceId: int
    token: str
    entity_type: str = Field(default='generic')
    semantic_vector: list[float] = Field(default_factory=list)
    spacetime: TKLLSpacetime = Field(default_factory=TKLLSpacetime)

# unique entity in a sentence
class TKLLUniqueEntity(BaseModel):
    id: int
    references: list[int] = Field(default_factory=list())
    token: str

# entity property
class TKLLEntityProperty(BaseModel):
    op: TKOperator
    reference: TKLLEntityReference

# entity reference for the content
class TKLLEntityReference(BaseModel):
    id: int
    op: TKOperator = Field(default=TKOperator.AND)
    aux: Optional[TKAux] = None
    marker: Optional[TKMarker] = None
    properties: list[TKLLEntityProperty] = Field(default_factory=list)

# llc content: can be a content or another llcitem (recursive)
class TKLLCContent(BaseModel):
    clause_type: TKClauseType = Field(default=TKClauseType.MAIN)
    properties: TKLLProperties
    subject: Optional[TKLLEntityReference] = Field(default=None)
    predicate: Optional[TKLLEntityReference] = Field(default=None) 
    direct: Optional[TKLLEntityReference] = Field(default=None) 
    indirects: list[TKLLEntityReference] = Field(default_factory=list)

# llc item: can be a statement or an llcitem (recursive)
class TKLLCItem(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND)
    content: Optional[LLCItemPayload] = None 

# llc 
class TKLLC(BaseModel):
    map: TKLLSpacetimeMap = Field(default_factory=TKLLSpacetimeMap)
    items: list[TKLLCItem] = Field(default_factory=list)
    entities: list[TKLLEntity] = Field(default_factory=list)
    uniqueEntities: list[TKLLUniqueEntity] = Field(default_factory=list())

# payload for item
LLCItemPayload = Union[list[TKLLCItem], TKLLCContent]
TKLLCItem.model_rebuild()
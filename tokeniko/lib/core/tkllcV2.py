# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
from typing import Optional, Union
from pydantic import BaseModel, Field
from lib.core.tk import TKAux, TKClauseType, TKMarker, TKOperator

# entity: can have different semantic vectors
class TKLLEntity(BaseModel):
    id: int
    token: str
    entity_type: str = Field(default='generic')
    semantic_vector: list[float] = Field(default_factory=list)

# map from tkentity and tkllentity
class TKLLEntityMap(BaseModel):
    entity: TKLLEntity
    ref: list[TKLLEntityMapReference]

# map reference for tkentities
class TKLLEntityMapReference(BaseModel):
    inputStatementIdx: int = Field(default=1)
    inputStatementId: int = Field(default=0)
    inputEntityId: int

# entity reference for the content
class TKLLEntityReference(BaseModel):
    id: int
    op: TKOperator = Field(default=TKOperator.AND)
    aux: Optional[TKAux] = None
    marker: Optional[TKMarker] = None
    properties: list[TKLLEntityProperty] = Field(default_factory=list)

# entity property
class TKLLEntityProperty(BaseModel):
    op: TKOperator
    reference: TKLLEntityReference

#  property related the sentence by the talker point of view
class TKLLProperties(BaseModel):
    ironic: float = Field(default=0.5) # literal 0 / neutral 0.5 / ironic 1
    dubitative: float = Field(default=0.5) # statement 0 / question 1
    imperative: float = Field(default=0.5) # neutral 0 / order 1
    sentiment: list[float] = Field(default_factory=lambda: ([0.0] * 2925)) # related to one or more base words

# llc content: can be a content or another llcitem (recursive)
class TKLLCContent(BaseModel):
    clause_type: TKClauseType = Field(default=TKClauseType.MAIN)
    properties: TKLLProperties
    subject: Optional[TKLLEntityReference] = Field(default=None)
    predicate: Optional[TKLLEntityReference] = Field(default=None) 
    direct: Optional[TKLLEntityReference] = Field(default=None) 
    indirects: list[TKLLEntityReference] = Field(default_factory=list)

class TKLLCItem(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND)
    content: Optional[LLCItemPayload] = None 

# llc 
class TKLLC(BaseModel):
    items: list[TKLLCItem] = Field(default_factory=list)
    entities: list[TKLLEntity] = Field(default_factory=list)
    
# payload for item
LLCItemPayload = Union[list[TKLLCItem], TKLLCContent]
TKLLCItem.model_rebuild()
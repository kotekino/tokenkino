from __future__ import annotations
from typing import List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr, RootModel, computed_field

_VECTOR_INDEX = "vector_index"

# --------------------------------------------------
# context
# --------------------------------------------------
class TKMessage(BaseModel):
    source: str
    target: str
    message: str

# alias for list of messages
TKContext = list[TKMessage]

# --------------------------------------------------
# mongo knowledgebase
# --------------------------------------------------

# geo point
class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[float] 

# base word (2925 base words, having semantic vector with 2925 dimensions)
class TKBase(BaseModel):
    entity_type: Literal["base"] = Field(default="base")
    word: str
    vector: list[float] = Field(default_factory=list, min_length=2925, max_length=2925)
    index: int

# dictionary (referring to the 2925 base words, having semantic vector with 2925 dimensions)
class TKDictionary(BaseModel):
    entity_type: Literal["dictionary"] = Field(default="dictionary")
    word: str
    pos: str = Field(pattern="^[avrns]$") 
    sense: str
    definition: str
    vector: list[float] = Field(default_factory=list, min_length=2925, max_length=2925)

# list of proper names
class TKName(BaseModel):
    entity_type: Literal["name"] = Field(default="name")
    name: str

# list of places
class TKPlace(BaseModel):
    entity_type: Literal["place"] = Field(default="place")
    name: str
    type: str
    category: str
    parent_admin: str
    parent_geo: str
    path_admin: list[str] = Field(default_factory=list)
    path_geo: list[str] = Field(default_factory=list)
    physical_features: Optional[list[str]] = None
    location: Optional[GeoPoint] = None

# marker for indirect
class TKMarker(BaseModel):
    entity_type: Literal["marker"] = Field(default="marker")
    type: str
    lemma: str
    vector: list[float] = Field(default_factory=list)

# generic: can be used to get the definition and replace it with a statement, so tokenKino learns :)
class TKGeneric(BaseModel):
    entity_type: Literal["generic"] = Field(default="generic")
    token: str
    upos: str
    pos: Optional[str] = None
    definition: Optional[str] = None
    context: Optional[TKContext] = None

# --------------------------------------------------
# statements related
# --------------------------------------------------
# operator enum
class TKOperator(str, Enum):
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    XNOR = "XNOR"
    IMPLY = "IMPLY"
    CONV = "CONV"
    EQ = "EQ"

# clause type enum
class TKClause(str, Enum):
    MAIN = "main"
    SUBORDINATE = "subordinate"
    COORDINATE = "coordinate"

# LL statement
class TKStatement(BaseModel):
    entity_type: Literal["statement"] = Field(default="statement")

    # clause type
    clause_type: TKClause = Field(default=TKClause.MAIN)

    # public fields
    subject: Optional[TKEntityReference] = Field(default=None) # id of entity, mandatory, has semantic 2925 value
    predicate: Optional[TKEntityReference] = Field(default=None) # id of entity, mandatory, has semantic 2925 value
    direct: Optional[TKEntityReference] = Field(default=None) # optional has semantic 2925 value
    indirects: list[TKEntityReference] = Field(default_factory=list) # optional has semantic 2925 value + semantic definition of marker
    
    # entities
    entities: list[TKEntity] = Field(default_factory=list) # entities in the sentence (generic, no properties)
    
    # private fields
    _id_counter: int = PrivateAttr(default=1)

    # properties
    # @computed_field
    # @property
    # def test(self) -> list[TKEntity]:

    # factory for TKEntity
    def create_entity(self, **kwargs) -> TKEntity:
        entity = TKEntity(id=self._id_counter, **kwargs)
        self.entities.append(entity)
        self._id_counter += 1
        return entity

    # factory for TKEntity
    def create_subject(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        conjunctEntities: list[TKEntityReference] = list()
        
        if kwargs.get("conjuncts", None): 
            conjuncts: list[TKFullEntity] = kwargs["conjuncts"]
            for c in conjuncts:
                conjunct = self.create_entity(payload=c.entity, op=c.op, marker=c.marker, conjuncts=c.conjuncts)
                conjunctEntities.append(TKEntityReference(id=conjunct.id, op=c.op, marker=c.marker, conjuncts=c.conjuncts))
        
        self.subject = TKEntityReference(id=entity.id, op=kwargs["op"], marker=kwargs["marker"], conjuncts=conjunctEntities)
        return entity.id

    # factory for TKEntity
    def create_direct(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        conjunctEntities: list[TKEntityReference] = list()
        
        if kwargs.get("conjuncts", None): 
            conjuncts: list[TKFullEntity] = kwargs["conjuncts"]
            for c in conjuncts:
                conjunct = self.create_entity(payload=c.entity, op=c.op, marker=c.marker, conjuncts=c.conjuncts)
                conjunctEntities.append(TKEntityReference(id=conjunct.id, op=c.op, marker=c.marker, conjuncts=c.conjuncts))
        
        self.direct = TKEntityReference(id=entity.id, op=kwargs["op"], marker=kwargs["marker"], conjuncts=conjunctEntities)
        return entity.id

    # factory for TKEntity
    def add_indirect(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        conjunctEntities: list[TKEntityReference] = list()

        if kwargs.get("conjuncts", None): 
            conjuncts: list[TKFullEntity] = kwargs["conjuncts"]
            for c in conjuncts:
                conjunct = self.create_entity(payload=c.entity, op=c.op, marker=c.marker, conjuncts=c.conjuncts)
                conjunctEntities.append(TKEntityReference(id=conjunct.id, op=c.op, marker=c.marker, conjuncts=c.conjuncts))
                
        self.indirects.append(TKEntityReference(id=entity.id, op=kwargs["op"], marker=kwargs["marker"], conjuncts=conjunctEntities))
        return entity.id

    # factory for TKEntity
    def create_predicate(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        conjunctEntities: list[TKEntityReference] = list()

        if kwargs.get("conjuncts", None):
            conjuncts: list[TKFullEntity] = kwargs["conjuncts"]
            for c in conjuncts:
                conjunct = self.create_entity(payload=c.entity, op=c.op, marker=c.marker, conjuncts=c.conjuncts)
                conjunctEntities.append(TKEntityReference(id=conjunct.id, op=c.op, marker=c.marker, conjuncts=c.conjuncts))
       
        self.predicate = TKEntityReference(id=entity.id, op=kwargs["op"], marker=kwargs["marker"], conjuncts=conjunctEntities)
        return entity.id

    # add property to subject, predicate, object
    def add_properties(self, properties: list[TKFullEntity], target: int): 
        
        # search target
        reference: TKEntityReference = None

        if self.subject and self.subject.id == target:
            reference = self.subject
        elif self.predicate and self.predicate.id == target:
            reference = self.predicate
        elif self.direct and self.direct.id == target:
            reference = self.direct
        elif len(self.indirects) > 0:
            reference: TKEntityReference = next((t for t in self.indirects if t.id == target), None)            
        
         # target found, add properties
        if reference:
            for p in properties:
                entity = self.create_entity(payload=p.entity)
                e = TKEntityReference(op=p.op, id=entity.id)
                reference.properties.append(e)

# entities involved in statements
# payload for entity
EntityPayload = Union[TKName, TKDictionary, TKPlace,TKGeneric, TKStatement]
class TKEntity(BaseModel):
    id: int = 0
    payload: EntityPayload = Field(discriminator='entity_type')

# the full entity
class TKFullEntity(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations

    entity: EntityPayload = Field(discriminator='entity_type')

    # specific semantic value (termine, fine, specificazione, etc)
    marker: Optional[TKMarker] = None

    # conjuect
    conjuncts: list[TKFullEntity] = Field(default_factory=list)

    # properties (list of semantic values)
    properties: list[TKFullEntity] = Field(default_factory=list)    

# a reference to an entity (and its properties)
class TKEntityReference(BaseModel):
    # logical operator
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations
    
    # id
    id: int

    # specific semantic value (termine, fine, specificazione, etc)
    marker: Optional[TKMarker] = None

    # conjuect
    conjuncts: list[TKEntityReference] = Field(default_factory=list)  

    # properties (list of semantic values)
    properties: list[TKEntityReference] = Field(default=[])

# alias for statement
TKStatements = list[TKStatement]

# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
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
#  tone, mode, certainty, hope
class TKLLProperties(BaseModel):
    tone: float = Field(default=0) # literal 0 / neutral 0.5 / ironic 1
    mode: float = Field(default=0) # question 0 / neutral 0.5 / statement 1
    certainty: tuple[int, float] = Field(default=0) # [subject in entities, unknown 0 / neutral 0.5 / fact 1]
    hope: tuple[int,float] = Field(default=0) # [subject in entities, neutral 0 / neutral 0.5 / deep wish 1]
# entity: can have different semantic vectors
class TKLLEntity(BaseModel):
    id: int
    tokens: str
    semantic_vector: list[float] = Field(default_factory=list)
    spacetime: TKLLSpacetime = Field(default_factory=TKLLSpacetime) 
# entity reference for the content
class TKLLEntityReference(BaseModel):
    id: int
    marker: Optional[TKMarker] = None
    properties: list[TKLLEntityReference] = Field(default_factory=list)
# llc item: can be a statement or an llcitem (recursive)
class TKLLCContent(BaseModel):
    properties: TKLLProperties
    subject: Optional[TKLLEntityReference] = Field(default=None)
    predicate: Optional[TKLLEntityReference] = Field(default=None) 
    direct: Optional[TKLLEntityReference] = Field(default=None) 
    indirects: list[TKLLEntityReference] = Field(default_factory=list)
class TKLLCItem(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND)
    content: Optional[LLCItemPayload] = None 
class TKLLC(BaseModel):
    map: TKLLSpacetimeMap = Field(default_factory=TKLLSpacetimeMap)
    items: list[TKLLCItem] = Field(default_factory=list)
    entities: list[TKLLEntity] = Field(default_factory=list)
class TKLLVector(BaseModel):
    vector: list[float] = Field(default_factory=list)

LLCItemPayload = Union[list[TKLLCItem], TKLLCContent]

TKStatement.model_rebuild()
TKEntityReference.model_rebuild()
TKEntity.model_rebuild()
TKFullEntity.model_rebuild()
TKLLCItem.model_rebuild()
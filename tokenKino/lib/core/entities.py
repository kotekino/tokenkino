from __future__ import annotations
import copy
from typing import List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr, RootModel, computed_field

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
    marker_type: str = Field(default="implicit")
    lemma: Optional[str] = None
    vector: list[float] = Field(default_factory=list)
    connect_clause: Optional[str] = None

# auxiliaries
class TKAux(BaseModel):
    entity_type: Literal["aux"] = Field(default="aux")
    lemma: Optional[str] = None
    vector: list[float] = Field(default_factory=list)

# pronoun
class TKPronoun(BaseModel):
    entity_type: Literal["pronoun"] = Field(default="pronoun")
    lemma: Optional[str] = None
    vector: list[float] = Field(default_factory=list)

# generic: can be used to get the definition and replace it with a statement, so tokenKino learns :)
class TKGeneric(BaseModel):
    entity_type: Literal["generic"] = Field(default="generic")
    token: str
    upos: Optional[str] = None
    pos: Optional[str] = None
    definition: Optional[str] = None
    context: Optional[TKContext] = None

# meta entities: possible stakeholders (me, tokenkino or anyone else)
class TKStakeholder(str, Enum):
    ME = "me"
    OTHER = "other"

# a meta entity referencing a stakeholder
class TKMetaEntity(BaseModel):
    entity_type: Literal["meta"] = Field(default="meta")
    who: TKStakeholder = Field(default=TKStakeholder.OTHER)
    name: str = Field(defaul="unknown")
    isTalking: bool = Field(default=True)
    isListening: bool = Field(default=False)

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
    THAT = "THAT",
    ANDNOT = "AND NOT"
    ORNOT = "OR NOT"
    NOTIMPLY = "NOT IMPLY"
    NOTCONV = "NOT CONV"
    NOTEQ = "NOT EQ"

# clause type enum
class TKClause(str, Enum):
    MAIN = "main"
    SUBORDINATE = "subordinate"
    COORDINATE = "coordinate"

# clause subordinate type
class TKClauseType(str, Enum):
    MAIN = "main"
    COORDINATE = "coordinate"
    FINAL = "final"
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    HYPOTETIC = "hypotetic"
    LOCATIVE = "locative"
    CCOMP = "ccomp"
    XCOMP = "xcomp"
    ACL = "acl"
    ACLRELCL = "acl:relcl"
    ADVCL = "advcl"
    PARATAXIS = "parataxis"
    OTHER = "other"

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

    # create subject
    def create_subject(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.subject = TKEntityReference(id=entity.id, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux)
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
                
        return entity.id

    # create direct
    def create_direct(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.direct = TKEntityReference(id=entity.id, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux)
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
                
        return entity.id

    # add indirect
    def add_indirect(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.indirects.append(TKEntityReference(id=entity.id, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux))
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
                
        return entity.id

    # create predicate
    def create_predicate(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.predicate = TKEntityReference(id=entity.id, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux)
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
                
        return entity.id

    # recursively search properties
    def search_childrenEntities(self, ref: TKEntityReference) -> list[TKEntityReference]:
        
        result: list[TKEntityReference] = list()

        # if properties
        if len(ref.properties):
            for p in ref.properties:
                result.append(p)
                result.extend(self.search_childrenEntities(p)) # recursive part (properties and conjuncts)
        
        # if conjuncts
        if len(ref.conjuncts):
            for c in ref.conjuncts:
                result.append(c)
                result.extend(self.search_childrenEntities(c)) # recursive part (properties)

        return result        

    # add property to subject, predicate, object, indirect
    def add_properties(self, properties: list[TKFullEntity], target: int): 
        
        # search target
        reference: TKEntityReference = None
        references: list[TKEntityReference] = list()

        # add object to search into
        if self.subject: references.append(self.subject)
        if self.predicate: references.append(self.predicate)
        if self.direct: references.append(self.direct)
        for i in self.indirects: references.append(i)
        
        # put everything in the possible references (1 level)
        children: list[TKEntityReference] = list()
        for r in references: children.extend(self.search_childrenEntities(r))
        references.extend(children)

        # get reference (fields or properties)
        reference: TKEntityReference = next((t for t in references if t.id == target), None)           

         # target found, add properties
        if reference:
            for p in properties:
                
                # cereate property reference
                entity = self.create_entity(payload=p.entity)
                e = TKEntityReference(op=p.op, id=entity.id, marker=p.marker, aux=p.aux)
                reference.properties.append(e)

                # recurse properties and conjuncts of conjuncts (recursive)
                if len(p.properties) > 0: self.add_properties(p.properties, entity.id)
                if len(p.conjuncts) > 0: self.add_conjuncts(p.conjuncts, entity.id)
        else:
            wrong = True 

    # add conjunct to subject, predicate, object, indirect
    def add_conjuncts(self, conjuncts: list[TKFullEntity], target: int):
        
        # search target
        reference: TKEntityReference = None
        references: list[TKEntityReference] = list()

        # add object to search into
        if self.subject: references.append(self.subject)
        if self.predicate: references.append(self.predicate)
        if self.direct: references.append(self.direct)
        for i in self.indirects: references.append(i)
        
        # put everything in the possible references (1 level)
        children: list[TKEntityReference] = list()
        for r in references: children.extend(self.search_childrenEntities(r))
        references.extend(children)

        # get reference (fields or properties)
        reference: TKEntityReference = next((t for t in references if t.id == target), None)           

         # target found, add properties
        if reference:
            for c in conjuncts:
                
                # cereate property reference
                entity = self.create_entity(payload=c.entity)
                e = TKEntityReference(op=c.op, id=entity.id, marker=c.marker, aux=c.aux)
                reference.conjuncts.append(e)

                # recurse properties and conjuncts of conjuncts (recursive)
                if len(c.properties) > 0: self.add_properties(c.properties, entity.id)
                if len(c.conjuncts) > 0: self.add_conjuncts(c.conjuncts, entity.id)
        else:
            wrong = True

# entities involved in statements
EntityPayload = Union[TKName, TKDictionary, TKPlace, TKGeneric, TKMetaEntity, TKStatement, TKPronoun]
class TKEntity(BaseModel):
    id: int = 0
    payload: EntityPayload = Field(discriminator='entity_type')
    referenceId: int = 0

# the full entity
class TKFullEntity(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations

    token: Optional[str] = None

    entity: EntityPayload = Field(discriminator='entity_type')

    # spacy semantic value
    marker: Optional[TKMarker] = None
    
    # specific semantic value
    aux: Optional[TKAux] = None

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

    # specific semantic value
    marker: Optional[TKMarker] = None

    # specific semantic value
    aux: Optional[TKAux] = None

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

TKStatement.model_rebuild()
TKEntityReference.model_rebuild()
TKEntity.model_rebuild()
TKFullEntity.model_rebuild()
TKLLCItem.model_rebuild()
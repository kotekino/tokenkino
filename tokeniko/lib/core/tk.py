from __future__ import annotations
import copy
import time
from typing import Any, List, Optional, Union, Literal
from enum import Enum
from bson import ObjectId
from pydantic import BaseModel, Field, PrivateAttr

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

# a proper name. a bare name (no NER-type centroid match) carries name only; an entity-linked
# individual additionally carries its NER label, a context-scoped identity uid, and the 2925 type
# centroid as its SEMANTIC vector (meaning=geometry, identity=symbolic uid — kept SEPARATE).
class TKName(BaseModel):
    entity_type: Literal["name"] = Field(default="name")
    name: str
    ner: Optional[str] = None  # the spaCy NER label (PERSON/GPE/ORG/...) when entity-linked
    uid: Optional[str] = None  # context-scoped identity "name@channel:talker_uid", or None for a bare name
    vector: list[float] = Field(default_factory=list)  # 2925 type centroid, or [] for a bare name

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

# marker for indirects
class TKMarker(BaseModel):
    entity_type: Literal["marker"] = Field(default="marker")
    word: Optional[str] = None
    vector: list[float] = Field(default_factory=list)
    definition: Optional[str] = None
    dep: str = Field(default="implicit")
    parent_dep: Optional[str] = Field(default=None)

# property
class TKProperty(BaseModel):
    entity_type: Literal["property"] = Field(default="property", exclude=True)
    word: Optional[str] = None
    vector: list[float] = Field(default_factory=list)

# auxiliaries
class TKAux(BaseModel):
    entity_type: Literal["aux"] = Field(default="aux")
    lemma: Optional[str] = None
    vector: list[float] = Field(default_factory=list)
    tense: Optional[str] = None  # clause tense for the spacetime time axis: past | pres | fut

# pronoun
class TKPronoun(BaseModel):
    entity_type: Literal["pronoun"] = Field(default="pronoun")
    lemma: Optional[str] = None
    vector: list[float] = Field(default_factory=list)

# num
class TKNumber(BaseModel):
    entity_type: Literal["num"] = Field(default="num")
    text: str
    value: float
    num_type: str

# generic: can be used to get the definition and replace it with a statement, so tokeniko learns :)
class TKGeneric(BaseModel):
    entity_type: Literal["generic"] = Field(default="generic")
    token: str
    upos: Optional[str] = None
    pos: Optional[str] = None
    definition: Optional[str] = None

# a meta entity referencing a stakeholder
class TKMetaEntity(BaseModel):
    entity_type: Literal["meta"] = Field(default="meta")
    who: Any
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
    THAT = "THAT"
    ANDNOT = "AND NOT"
    ORNOT = "OR NOT"
    NOTIMPLY = "NOT IMPLY"
    NOTCONV = "NOT CONV"
    NOTEQ = "NOT EQ"

# quantifier read off the subject's determiner. UNIVERSAL (all/every/each), EXISTENTIAL
# (some/any/several), INDEFINITE (a/an — split from EXISTENTIAL in Brain v1.1 step 2: an indefinite
# singular copular "a cat is a mammal" is a GENERIC claim, while "some birds are pets" is a true
# existential that must NEVER become an is_a edge; the split lets the generic-taxonomy extractor
# admit the first without the second), NEGATIVE (no/none/neither), DEFINITE (the/this/that/...),
# GENERIC (bare/no determiner). drives the quantifier-aware truth flip in the relational grounding
# (only NEGATIVE flips; the others are truth-inert there).
class TKQuantifier(str, Enum):
    UNIVERSAL = "universal"
    EXISTENTIAL = "existential"
    INDEFINITE = "indefinite"
    NEGATIVE = "negative"
    DEFINITE = "definite"
    GENERIC = "generic"

# wh-question GAP ROLE — which semantic slot is the variable X a wh-question asks to solve for.
# who/whom/which -> SUBJECT, what -> PREDICATE (copular complement), where -> LOCATION, when -> TIME,
# how -> MANNER, why -> CAUSE. None = polar question or declarative (no gap).
class TKWhRole(str, Enum):
    SUBJECT = "subject"
    PREDICATE = "predicate"
    DIRECT = "direct"
    LOCATION = "location"
    TIME = "time"
    MANNER = "manner"
    CAUSE = "cause"

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

    # interrogative mood — the author-scaffolded `dubitative` carrier: statement 0.5 / question 1.0.
    # set by the parser when the sentence is a question ("?" survives as a PUNCT token; a wh-word
    # carries PronType=Int). a question is ANSWERED, not asserted/believed (see the evaluator/brain).
    dubitative: float = Field(default=0.5)
    # wh-question gap role (the variable X to solve for); None = polar question or declarative.
    wh_role: Optional[TKWhRole] = Field(default=None)

    # the ROOT-level subordinating marker (the storm-sequel fix, 2026-07-14): a FRAGMENT utterance
    # that IS a subordinate clause («because you think» as the whole message) carries its "mark"
    # on the root, which the subordinate-reference path never sees — the causal/temporal relation
    # died unread and the fragment compiled as a bare assertion. The parser now stashes the root
    # mark here; the compiler folds the statement with the marker's subordinate operator (a
    # fragment is a relation HALF, never a standalone assertion — the assertedness gate then sees it).
    marker: Optional[TKMarker] = Field(default=None)

    # public fields
    subject: Optional[TKEntityReference] = Field(default=None) # id of entity, mandatory, has semantic 2925 value
    predicate: Optional[TKEntityReference] = Field(default=None) # id of entity, mandatory, has semantic 2925 value
    direct: Optional[TKEntityReference] = Field(default=None) # optional has semantic 2925 value
    indirects: list[TKEntityReference] = Field(default_factory=list) # optional has semantic 2925 value + semantic definition of marker

    # entities
    entities: list[TKEntity] = Field(default_factory=list) # entities in the sentence (generic, no properties)
    
    # private fields
    _id_counter: int = PrivateAttr(default=1)

    # factory for TKEntity
    def create_entity(self, **kwargs) -> TKEntity:
        entity = TKEntity(id=self._id_counter, **kwargs)
        self.entities.append(entity)
        self._id_counter += 1
        return entity

    # create subject
    def create_subject(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.subject = TKEntityReference(id=entity.id, dep=fullEntity.dep, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux)
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
        if len(fullEntity.subordinates) > 0: self.add_subordinates(fullEntity.subordinates, entity.id)
                
        return entity.id

    # create direct
    def create_direct(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.direct = TKEntityReference(id=entity.id, dep=fullEntity.dep, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux)
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
        if len(fullEntity.subordinates) > 0: self.add_subordinates(fullEntity.subordinates, entity.id)
                
        return entity.id

    # add indirect
    def add_indirect(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.indirects.append(TKEntityReference(id=entity.id, dep=fullEntity.dep, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux))
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
        if len(fullEntity.subordinates) > 0: self.add_subordinates(fullEntity.subordinates, entity.id)
                
        return entity.id

    # create predicate
    def create_predicate(self, fullEntity: TKFullEntity) -> TKEntityReference:
        entity = self.create_entity(payload=fullEntity.entity)
        self.predicate = TKEntityReference(id=entity.id, dep=fullEntity.dep, op=fullEntity.op, marker=fullEntity.marker, aux=fullEntity.aux)
        
        # add properties and conjuncts
        if len(fullEntity.properties) > 0: self.add_properties(fullEntity.properties, entity.id)
        if len(fullEntity.conjuncts) > 0: self.add_conjuncts(fullEntity.conjuncts, entity.id)
        if len(fullEntity.subordinates) > 0: self.add_subordinates(fullEntity.subordinates, entity.id)

        return entity.id

    # recursively search properties
    def search_childrenProperties(self, ref: TKPropertyReference) -> list[TKPropertyReference]:
        
        result: list[TKPropertyReference] = list()

        # if properties
        if len(ref.properties):
            for p in ref.properties:
                result.append(p)
                result.extend(self.search_childrenProperties(p)) # recursive part (properties)

        return result          

    # recursively search children entities
    def search_childrenEntities(self, ref: TKEntityReference) -> list[TKEntityReference]:
        
        result: list[TKEntityReference] = list()

        # if properties
        if len(ref.properties):
            for p in ref.properties:
                result.append(p)
                result.extend(self.search_childrenProperties(p)) # recursive part (properties)
        
        # if conjuncts
        if len(ref.conjuncts):
            for c in ref.conjuncts:
                result.append(c)
                result.extend(self.search_childrenEntities(c)) # recursive part (conjuncts)

        # if subordinates
        if len(ref.subordinates):
            for c in ref.subordinates:
                result.append(c)
                result.extend(self.search_childrenEntities(c)) # recursive part (subordinates)

        return result        

    # add property to subject, predicate, object, indirect
    def add_properties(self, properties: list[TKFullProperty], target: int): 
        
        # search target
        reference: TKPropertyReference = None
        references: list[TKPropertyReference] = list()

        # add object to search into
        if self.subject: references.append(self.subject)
        if self.predicate: references.append(self.predicate)
        if self.direct: references.append(self.direct)
        for i in self.indirects: references.append(i)
        
        # put everything in the possible references (1 level)
        # NB: search_childrenEntities (not search_childrenProperties) so that
        # properties of conjuncts/subordinates (e.g. "other" in "... and other cats")
        # can be located as targets, not just properties hanging off the main fields
        children: list[TKPropertyReference] = list()
        for r in references: children.extend(self.search_childrenEntities(r))
        references.extend(children)

        # get reference (fields or properties)
        reference: TKPropertyReference = next((t for t in references if t.id == target), None)           

         # target found, add properties
        if reference:
            for p in properties:
                
                # cereate property reference
                entity = self.create_entity(payload=p.entity)
                e = TKPropertyReference(id=entity.id, dep=p.dep)
                reference.properties.append(e)

                # recurse properties 
                if len(p.properties) > 0: self.add_properties(p.properties, entity.id)

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
                e = TKEntityReference(op=c.op, id=entity.id, dep=c.dep, marker=c.marker, aux=c.aux)
                reference.conjuncts.append(e)

                # recurse properties and conjuncts of conjuncts (recursive)
                if len(c.properties) > 0: self.add_properties(c.properties, entity.id)
                if len(c.conjuncts) > 0: self.add_conjuncts(c.conjuncts, entity.id)
                if len(c.subordinates) > 0: self.add_subordinates(c.subordinates, entity.id)
        else:
            wrong = True

    # add conjunct to subject, predicate, object, indirect
    def add_subordinates(self, subordinates: list[TKFullEntity], target: int):
        
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
            for c in subordinates:
                
                # cereate property reference
                entity = self.create_entity(payload=c.entity)
                e = TKEntityReference(op=c.op, id=entity.id, dep=c.dep, marker=c.marker, aux=c.aux)
                reference.subordinates.append(e)

                # recurse properties and conjuncts of conjuncts (recursive)
                if len(c.properties) > 0: self.add_properties(c.properties, entity.id)
                if len(c.conjuncts) > 0: self.add_conjuncts(c.conjuncts, entity.id)
                if len(c.subordinates) > 0: self.add_subordinates(c.subordinates, entity.id)
        else:
            wrong = True

# entities involved in statements
EntityPayload = Union[TKName, TKDictionary, TKPlace, TKGeneric, TKMetaEntity, TKStatement, TKPronoun, TKNumber]
class TKEntity(BaseModel):
    id: int = 0
    payload: EntityPayload = Field(discriminator='entity_type')
    referenceId: int = 0

# the full entity
class TKFullEntity(BaseModel):
    # operator
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations

    # original token
    token: Optional[str] = None

    # entity
    entity: EntityPayload = Field(discriminator='entity_type')

    # dep
    dep: str

    # spacy semantic value
    marker: Optional[TKMarker] = None
    
    # specific semantic value
    aux: Optional[TKAux] = None

    # conjuncts
    conjuncts: list[TKFullEntity] = Field(default_factory=list)

    # subordinates
    subordinates: list[TKFullEntity] = Field(default_factory=list)

    # properties (list of semantic values)
    properties: list[TKFullProperty] = Field(default_factory=list)    

# a reference to an entity (and its properties)
class TKEntityReference(BaseModel):
    # logical operator
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations
    
    # id
    id: int

    # dep
    dep: str

    # specific semantic value
    marker: Optional[TKMarker] = None

    # specific semantic value
    aux: Optional[TKAux] = None

    # conjuncts
    conjuncts: list[TKEntityReference] = Field(default_factory=list)  

    # subordinates
    subordinates: list[TKEntityReference] = Field(default_factory=list)

    # properties (list of semantic values)
    properties: list[TKPropertyReference] = Field(default=[])

# the full property
class TKFullProperty(BaseModel):
    token: Optional[str] = None
    entity: EntityPayload = Field(discriminator='entity_type')
    dep: str
    properties: list[TKFullProperty] = Field(default_factory=list)    

# a reference to a property (and its properties)
class TKPropertyReference(BaseModel):
    id: int
    dep: str
    properties: list[TKPropertyReference] = Field(default=[])

# alias for statement
TKStatements = list[TKStatement]

# rebuild models (important to do after editing the models, to update the internal pydantic model)
TKMetaEntity.model_rebuild()
TKStatement.model_rebuild()
TKEntityReference.model_rebuild()
TKEntity.model_rebuild()
TKFullEntity.model_rebuild()
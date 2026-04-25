from __future__ import annotations
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
    coordinates: List[float] 

# base word (2925 base words, having semantic vector with 2925 dimensions)
class TKBase(BaseModel):
    entity_type: Literal["base"] = Field(default="base")
    word: str
    vector: List[float] = Field(default_factory=list, min_length=2925, max_length=2925)
    index: int

# dictionary (referring to the 2925 base words, having semantic vector with 2925 dimensions)
class TKDictionary(BaseModel):
    entity_type: Literal["dictionary"] = Field(default="dictionary")
    word: str
    pos: str = Field(pattern="^[avrns]$") 
    sense: str
    definition: str
    vector: List[float] = Field(default_factory=list)

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
    path_admin: List[str] = Field(default_factory=list)
    path_geo: List[str] = Field(default_factory=list)
    physical_features: Optional[List[str]] = None
    location: Optional[GeoPoint] = None

class TKComplement(BaseModel):
    entity_type: Literal["complement"] = Field(default="complement")
    type: str
    vector: List[float] = Field(default_factory=list)

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

# space map: should manage where and when
class TKSpaceTimeMap(BaseModel):
    entity_type: Literal["spacetime_map"] = Field(default="spacetime_map")
    
    # position in spacetime is relative to the observer (as position and as magnitude)
    spacetime: List[float] = Field(default_factory=list, min_length=4, max_length=4) # [t, x, y, z]
    place: Optional[TKPlace] = None
    dictionary: Optional[TKDictionary] = None

# LL statement
class TKStatement(BaseModel):
    entity_type: Literal["statement"] = Field(default="statement")

    # public fields
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations
    subject: Optional[TKEntityReference] = None # id of entity, mandatory, has semantic 2925 value
    predicate: Optional[TKEntityReference] = None # id of entity, mandatory, has semantic 2925 value
    direct: Optional[TKEntityReference] = None # optional has semantic 2925 vale
    indirect: list[TKEntityReference] = Field(default_factory=list) # optional has semantic 2925 value + semantic definition of complement
    spacetime: Optional[TKSpaceTimeMap] = None # optional, has spacial semantic value (spacetimemap)
    
    # entities
    entities: List[TKEntity] = Field(default_factory=list) # entities in the sentence (generic, no properties)
    
    # private fields
    _id_counter: int = PrivateAttr(default=1)

    # properties
    # @computed_field
    # @property
    # def test(self) -> List[TKEntity]:

    # factory for TKEntity
    def create_entity(self, **kwargs) -> TKEntity:
        entity = TKEntity(id=self._id_counter, **kwargs)
        self.entities.append(entity)
        self._id_counter += 1
        return entity

    # factory for TKEntity
    def create_subject(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        self.subject = TKEntityReference(id=entity.id, complement=kwargs["complement"])
        return entity.id

    # factory for TKEntity
    def create_direct(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        self.direct = TKEntityReference(id=entity.id, complement=kwargs["complement"])
        return entity.id

    # factory for TKEntity
    def create_indirect(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        self.indirect.append(TKEntityReference(id=entity.id, complement=kwargs["complement"]))
        return entity.id

    # factory for TKEntity
    def create_predicate(self, **kwargs) -> TKEntityReference:
        entity = self.create_entity(**kwargs)
        self.predicate = TKEntityReference(id=entity.id, complement=kwargs["complement"])
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
        else:
            reference: TKEntityReference = next((t for t in self.indirect if t.id == target), None)            
        
         # add properties
        if reference:
            for p in properties:
                entity = self.create_entity(payload=p.entity)        
                e = TKEntityReference(id=entity.id)
                reference.properties.append(e.id)

# entities involved in statements
# payload for entity
EntityPayload = Union[TKName, TKDictionary, TKSpaceTimeMap, TKGeneric, TKStatement]
class TKEntity(BaseModel):
    id: int = 0
    payload: EntityPayload = Field(discriminator='entity_type')

# the full entity
class TKFullEntity(BaseModel):
    entity: EntityPayload = Field(discriminator='entity_type')

    # specific semantic value (termine, fine, specificazione, etc)
    complement: Optional[TKComplement] = None

    # properties (list of semantic values)
    properties: list[TKFullEntity] = Field(default=[])    

# a reference to an entity (and its properties)
class TKEntityReference(BaseModel):
    id: int

    # specific semantic value (termine, fine, specificazione, etc)
    complement: Optional[TKComplement] = None

    # properties (list of semantic values)
    properties: list[int] = Field(default=[])

TKStatement.model_rebuild()
TKEntityReference.model_rebuild()
TKEntity.model_rebuild()
TKFullEntity.model_rebuild()

# alias for statement
TKStatements = list[TKStatement]
# --------------------------------------------------
# flat statements related
# --------------------------------------------------
TKFlatMap = tuple[list[float], List[float]] # vector semantic complement, vector semantic dictionary
class TKFlatStatement(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations
    subject: TKFlatMap
    predicate: TKFlatMap
    direct: TKFlatMap
    indirect: list[TKFlatMap] = Field(default_factory=list) # optional has semantic 2925 value + semantic definition of complement
    spacetime: Optional[TKSpaceTimeMap] = None # optional, has spacial semantic value (spacetimemap)    

# alias for list flat statement
TKFlatStatements = list[TKFlatStatement]


# Note per sviluppo delle logiche di valutazione
# - subject, predicate, object e spec si valutano sempre su base semantica
# - when, si valuta su base temporale costruendo una linea temporale degli eventi
# - where, si valuta su base spaziale costruendo una mappa degli eventi
# - la similarity semantica dà valori tra -1 e 1, prima dell'applicazione degli operatori
#   logici, va normalizzata tra 0 e 1, ad esempio con la formula (similarity + 1) / 2 
# - LLC appiattisce le relazioni logiche tra le entità, ad esempio una relazione AND tra due affermazioni diventa una nuova affermazione con un nuovo soggetto che rappresenta la combinazione dei due soggetti originali, e così via per gli altri operatori logici
#   es: io e mari andiamo al mare ->
#       [io, subject] [andare, predicate] [mare, object] [con mari, spec]
#       AND
#       [mari, subject] [andare, predicate] [mare, object] [con io, spec]
#   In questo modo le valutazioni semantiche sono SOLO semantiche (senza mischiare arbitrariamente i valori
#   semantici, mentre quelle logiche (fuzzy) sono solo fuzzy
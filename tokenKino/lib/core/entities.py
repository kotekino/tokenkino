from __future__ import annotations
from typing import List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr, RootModel

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

# es testvar: TKOperator = TKOperator.AND

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

# space operator
class TKSpaceOperator(str, Enum):
    FROM = "FROM"
    TO = "TO"
    AT = "AT"
    IN = "IN"
    INTO = "INTO"
    OUT = "OUT"
    OUTOF = "OUTOF"

# abstract places side
class TKPlaceSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"

# abstract places
class TKAbstractPlace(BaseModel):
    entity_type: Literal["abstract_place"] = Field(default="abstract_place")
    proximity: Optional[int]= Field(default=0) # default here 0, there 10, far 100 very far 1000, very close 0.1
    side: Optional[TKPlaceSide] = None # optional

# space map
SpacePayload = Union[TKPlace, TKAbstractPlace]
class TKSpaceMap(BaseModel):
    entity_type: Literal["space_map"] = Field(default="space_map")
    op: TKSpaceOperator = Field(default=TKSpaceOperator.IN)
    observer: SpacePayload = Field(discriminator='entity_type')
    observed: SpacePayload = Field(discriminator='entity_type')

# entities involved in statements
# payload for entity
EntityPayload = Union[TKName, TKDictionary, TKSpaceMap, TKGeneric]
class TKEntity(BaseModel):
    id: int = 0
    payload: EntityPayload = Field(discriminator='entity_type')

# a reference to an entity (and its properties)
class TKEntityReference(BaseModel):
    id: int
    properties: list[int] = Field(default=[])

# LL statement
class TKStatement(BaseModel):
    entity_type: Literal["statement"] = Field(default="statement")
    op: TKOperator = Field(default=TKOperator.AND) # mandatory, default (AND), allows fuzzy-logic operations
    subject: Optional[TKEntityReference] = None # id of entity, mandatory, has semantic 2925 value
    predicate: Optional[TKEntityReference] = None # id of entity, mandatory, has semantic 2925 value
    object: Optional[TKEntityReference] = None # optional has semantic 2925 vale
    when: Optional[TKEntityReference] = None # optional, has time semantic value
    where: Optional[TKEntityReference] = None # optional, has spacial semantic value
    entities: List[TKEntity] = Field(default_factory=list) # entities in the sentence (generic, no properties)

    # private attr for general counter
    _id_counter: int = PrivateAttr(default=1)

    # factory for TKEntity
    def create_entity(self, **kwargs) -> TKEntityReference:
        entity = TKEntity(id=self._id_counter, **kwargs)
        self.entities.append(entity)
        self._id_counter += 1
        return TKEntityReference(id=entity.id)

    # add property to subject, predicate, object
    def add_properties(self, properties: list[TKDictionary], target: str): 
        attr: TKEntityReference = getattr(self, target)
        for p in properties:
            e = self.create_entity(payload=p)
            attr.properties.append(e.id)
        setattr(self, target, attr)

# alias for statements
TKStatements = list[TKStatement]

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
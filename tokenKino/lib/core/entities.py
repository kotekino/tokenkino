from __future__ import annotations
from typing import List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr

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
    pos: str
    definition: str

# --------------------------------------------------
# statements
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

# LL statement
class TKStatement(BaseModel):
    entity_type: Literal["statement"] = Field(default="statement")
    op: Optional[TKOperator] = None
    subject: Optional[TKEntity] = None
    predicate: Optional[TKEntity] = None
    object: Optional[TKEntity] = None
    when: Optional[TKEntity] = None
    where: Optional[TKEntity] = None
    spec: Optional[TKEntity] = None
    entities: List[TKEntity] = Field(default_factory=list)

    # private attr for general counter
    _id_counter: int = PrivateAttr(default=1)

    # factory for TKEntity
    def create_entity(self, **kwargs) -> TKEntity:
        entity = TKEntity(id=self._id_counter, **kwargs)
        self.entities.append(entity)
        self._id_counter += 1
        return entity

    # register entity in the statement
    def register_entity(self, entity: TKEntity) -> TKEntity:
        if entity.id == 0:
            entity.id = self._id_counter
            self._id_counter += 1
        
        if entity not in self.entities:
            self.entities.append(entity)
        return entity 
    
    # rebuild ids
    def model_post_init(self, __context):
        if self.entities:
            max_id = max(e.id for e in self.entities)
            self._id_counter = max_id + 1    

# payload for entity
EntityPayload = Union[TKName, TKDictionary, TKPlace, TKGeneric, TKStatement]

# entities involved in statements
class TKEntity(BaseModel):
    id: int = 0
    payload: EntityPayload = Field(discriminator='entity_type')

class TKStatements(List[TKStatement]):
    pass

# rebuild models to ensure all fields are properly processed
TKEntity.model_rebuild()
TKStatement.model_rebuild()

# --------------------------------------------------
# context
# --------------------------------------------------
class TKMessage(BaseModel):
    source: str
    target: str
    message: str

class TKContext(List[TKStatement]):
    pass

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
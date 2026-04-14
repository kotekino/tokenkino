from __future__ import annotations
from typing import List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field

# geo point
class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: List[float] 

# base word (2925 base words, having semantic vector with 2925 dimensions)
class TKBase(BaseModel):
    word: str
    vector: List[float] = Field(default_factory=list, min_length=2925, max_length=2925)
    index: int

# dictionary (referring to the 2925 base words, having semantic vector with 2925 dimensions)
class TKDictionary(BaseModel):
    word: str
    pos: str = Field(pattern="^[avrns]$") 
    sense: str
    definition: str
    vector: List[float] = Field(default_factory=list)

# list of proper names
class TKName(BaseModel):
    name: str

# list of places
class TKPlace(BaseModel):
    name: str
    type: str
    category: str
    parent_admin: str
    parent_geo: str
    path_admin: List[str] = Field(default_factory=list)
    path_geo: List[str] = Field(default_factory=list)
    physical_features: Optional[List[str]] = None
    location: Optional[GeoPoint] = None

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

# entities involved in statements
class TKEntity(BaseModel):
    id: int # unique identifier for the entity IN THE CONTEXT OF THE STATEMENT
    type: str
    name: Optional[TKName] = None
    dictionary: Optional[TKDictionary] = None
    place: Optional[TKPlace] = None
    statement: Optional[TKStatement] = None

# LL statement
class TKStatement(BaseModel):
    op: Optional[TKOperator] = None
    subject: TKEntity
    predicate: TKEntity 
    object: Optional[TKEntity] = None
    when: Optional[TKEntity] = None
    where: Optional[TKEntity] = None
    spec: Optional[TKEntity] = None
    entities: List[TKEntity] = Field(default_factory=list)

class TKLLStatement(List[TKStatement]):
    pass

# rebuild models to ensure all fields are properly processed
TKEntity.model_rebuild()
TKStatement.model_rebuild()

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
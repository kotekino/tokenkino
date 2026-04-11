from typing import List, Optional, Union, Literal
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
    path_admin: List[str]
    path_geo: List[str]
    physical_features: Optional[List[str]] = None
    location: Optional[GeoPoint] = None
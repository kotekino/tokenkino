from datetime import datetime, timezone
from typing import Annotated, Optional
from bunnet import Document, Granularity, Indexed, TimeSeriesConfig
from pydantic import Field
from lib.core.tk import TKBase, TKDictionary, TKMarker, TKName, TKPlace
from lib.core.memory import MEMAxiom, MEMTheorem, MEMItem, MEMStakeholder

_VECTOR_INDEX = "vector_index"

# --------------------------------------------------------------
# knowledge base documents
# --------------------------------------------------------------

# document for base words
class TKBaseDoc(TKBase, Document):
    # Diciamo: "Il tipo è str, ed è indicizzato come unico"
    word: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "base"

# document for the dictionary
class TKDictionaryDoc(TKDictionary, Document):
    word: Annotated[str, Indexed()]
    
    class Settings:
        name = "dictionary"

# document for proper names
class TKNameDoc(TKName, Document):
    name: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "names"

# document for places
class TKPlaceDoc(TKPlace, Document):
    name: Annotated[str, Indexed()]

    class Settings:
        name = "places"

# document for markers
class TKMarkerDoc(TKMarker, Document):
    word: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "markers"

# --------------------------------------------------------------
# tokeniko memory
# --------------------------------------------------------------

# axioms: the truths that tokeniko holds about the world, that it will use as basis for reasoning and deriving new knowledge
class TKAxiomDoc(MEMAxiom, Document):
    class Settings:
        name = "axioms"

# theorems: the truths that tokeniko has derived from the axioms, that it will use as basis for reasoning and deriving new knowledge
class TKTheoremDoc(MEMTheorem, Document):
    class Settings:
        name = "theorems"

# items of the conversations
class TKMemoryItemDoc(MEMItem, Document):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[str] = None

    class Settings:
        name = "memory"
        timeseries = TimeSeriesConfig(
            time_field="timestamp",          
            meta_field="metadata",           
            granularity=Granularity.seconds,
            expire_after_seconds=None       
        )

# entities involved in the conversations
class TKMemoryStakeholdersDoc(MEMStakeholder, Document):
    uid: Annotated[str, Indexed(unique=True)]
    class Settings:
        name = "stakeholders"
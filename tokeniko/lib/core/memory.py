# --------------------------------------------------
# memory
# --------------------------------------------------
# channel where a memory is originated
from enum import Enum
import time
from typing import Optional
from pydantic import BaseModel, Field
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip, TKZipContent

class MEMChannels(str, Enum):
    INTERNAL = "internal"
    API = "api"
    DISCORD = "discord"
    ATPROTO = "atproto"

# known talking entities + named individuals.
# kind="participant" (default) is a conversation participant (talker/listener); kind="individual"
# is a named individual referred to in a sentence ("Mari", "Rome", "Google") — entity-linked to a
# context-scoped uid. an individual carries a NER-type-derived SEMANTIC vector (the 2925 type
# centroid; meaning lives in the grounded geometry) separate from its referential uid (identity
# lives symbolically). contextKey scopes the uid to "channel:talker_uid".
class MEMStakeholder(BaseModel):
    name: str
    uid: str
    channel: MEMChannels = Field(default=MEMChannels.INTERNAL)
    isMe: bool = Field(default=False)
    createdAt: int = Field(default_factory=lambda: int(time.time()))
    kind: str = "participant"  # "participant" | "individual"
    ner_type: Optional[str] = None  # the spaCy NER label for an individual (PERSON/GPE/ORG/...)
    vector: Optional[list[float]] = None  # the 2925 type centroid (meaning=geometry); None for participants
    contextKey: Optional[str] = None  # "channel:talker_uid" scope of an individual's uid

# mem item properties
class MEMItemProperties(BaseModel):
    trusted: float = Field(default=0.5) # 0 not trusted, 1 fully trusted

# memory item
class MEMItem(BaseModel):
    original: str
    zip: Optional[TKZip] = None # zipped message (optional, for debugging and learning purposes)
    raw: Optional[str] = None # raw message (optional, for debugging and learning purposes)
    sourceId: str # unique stakeholder objectId of the source (talker)
    targetId: Optional[str] = None # unique stakeholder objectId of the target (listener)
    channel: Optional[str] = None # channel of the message (e.g. "discord", "atproto", "internal")

# alias for list of memory items
MEMContext = list[MEMItem]

# axiom
class MEMAxiom(MEMItem, MEMItemProperties):
    archived: bool = Field(default=False) # if archived, the axiom is not used for reasoning and deriving new knowledge
    readonly: bool = Field(default=True) # if readonly, the axiom cannot be archived and is always used for reasoning and deriving new knowledge
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archivedAt: Optional[int] = None # timestamp of archiving (if archived, the axiom is not used for reasoning and deriving new knowledge)
    trusted: float = Field(default=1)

# theorem
class MEMTheorem(MEMItem, MEMItemProperties):
    archived: bool = Field(default=True) # if archived, the theorem is not used for reasoning and deriving new knowledge
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archivedAt: Optional[int] = None # timestamp of archiving (if archived, the theorem is not used for reasoning and deriving new knowledge)
    trusted: float = Field(default=0.9)

# definition: a semantic statement defining tokeniko's vocabulary/rules ("a thing is equal to
# itself"; "an apple is a fruit with red skin and sweet flesh"). its meaning is the full compiled
# structure (single OR multi clause) -> a TKZip, like axioms/theorems. all WordNet glosses live here.
# like axioms, definitions are trusted ground truths and need no demonstration.
class MEMDefinition(MEMItemProperties):
    original: str
    zip: Optional[TKZip] = None # the compiled semantic structure (single or multi clause)
    raw: Optional[str] = None # raw rendering (optional, for debugging)
    sourceId: str # unique stakeholder objectId of the source (talker)
    targetId: Optional[str] = None # unique stakeholder objectId of the target (listener)
    channel: Optional[str] = None # channel of origin (e.g. "internal")
    archived: bool = Field(default=False) # if archived, the definition is not used for reasoning
    readonly: bool = Field(default=True) # if readonly, the definition cannot be archived
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archivedAt: Optional[int] = None # timestamp of archiving
    trusted: float = Field(default=1)

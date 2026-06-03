# --------------------------------------------------
# memory
# --------------------------------------------------
# channel where a memory is originated
from enum import Enum
import time
from typing import Optional
from pydantic import BaseModel, Field
from lib.core.tkllc import TKLLC

class MEMChannels(str, Enum):
    INTERNAL = "internal"
    API = "api"
    DISCORD = "discord"
    ATPROTO = "atproto"

# known talking entities
class MEMStakeholder(BaseModel):
    name: str
    uid: str
    channel: MEMChannels = Field(default=MEMChannels.INTERNAL)
    isMe: bool = Field(default=False)
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# mem item properties
class MEMItemProperties(BaseModel):
    trusted: float = Field(default=0.5) # 0 not trusted, 1 fully trusted

# memory item
class MEMItem(BaseModel):
    tkllc: TKLLC
    sourceId: str # unique stakeholder objectId of the source (talker)
    targetId: Optional[str] = None # unique stakeholder objectId of the target (listener)
    channel: Optional[str] = None # channel of the message (e.g. "discord", "atproto", "internal")
    raw: Optional[str] = None # raw message (optional, for debugging and learning purposes)

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

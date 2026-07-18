# --------------------------------------------------------------
# events.py — the EVENT layer (author's draft, 2026-07-18): what the atproto senses will
# retrieve from the outside world. DISCONNECTED for now — no doc registration, no consumer;
# the base structure lands ahead of the connector (senses/atproto arc). See .env.template
# (BSKY_APP_PASSWORD) for the credential seat.
# --------------------------------------------------------------
import time
from typing import Optional
from pydantic import BaseModel, Field
from lib.core.memory import MEMStakeholder
from lib.core.tkzip import TKZip

# Events are populated by retrieval on atproto
# the default trust on an event is 0.5
# classification is on multiple trees
# an event is something that happened
#   - iptcTag (static tree)
#   - openTags (centroids best fit, dynamic label)
#   - geoTag (static tree)
class MEMEvent(BaseModel):
    original: str
    zip: Optional[TKZip] = None # the compiled semantic structure (single or multi clause)
    raw: Optional[str] = None # raw rendering (optional, for debugging)
    trusted: float = Field(default=0.5)
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archived: bool = Field(default=False) # if archived, the event is not used
    archivedAt: Optional[int] = None # timestamp of archiving (if archived, the event is not used)
    sourceId: str # unique stakeholder objectId of the source (talker)
    channel: Optional[str] = None # channel of origin (e.g. "bsky")
    # taxonomy
    geoTags: Optional[list[str]] = None # tkplace tags (ref. tkplace.name)
    iptcTags: Optional[list[str]] = None # iptc codes
    openTags: Optional[list[str]] = None #open tags

# the stakeholders referenced by an event
class EVStakeholder(MEMStakeholder):
    kind: str = Field(default="individual") # "individual" | "organization"

# the sources reporting an event
class EVSources(MEMStakeholder):
    kind: str = "atproto" # an event source is always from atproto
    atprotoHandler: str # ex. "@nytimes.com"
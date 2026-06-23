from datetime import datetime, timezone
from typing import Annotated, Optional
from bunnet import Document, Granularity, Indexed, TimeSeriesConfig
from pydantic import Field
from lib.core.tk import TKBase, TKDictionary, TKMarker, TKName, TKPlace, TKProperty
from lib.core.memory import MEMAxiom, MEMDefinition, MEMTheorem, MEMItem, MEMStakeholder, MEMIdea, MEMAction, MEMBehaviorRule, BrainState

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

# document for properties
class TKPropertyDoc(TKProperty, Document):
    word: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "properties"

# synset-keyed semantic relations graph (WordNet-derived): {subject, relation, object, pos}.
# direct edges only — the transitive closure (is_a ancestry) is computed at query time. ~150k triples;
# read lazily through an injected accessor, never loaded wholesale.
class TKRelationDoc(Document):
    # plain fields: the collection already carries indexes on subject/object/relation, so we do not
    # re-declare them here (avoid index-creation churn on a ~150k-doc collection).
    subject: str
    relation: str
    object: str
    pos: Optional[str] = None

    class Settings:
        name = "relations"

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

# definitions: single-sentence semantic statements defining tokeniko's vocabulary/rules
class TKDefinitionDoc(MEMDefinition, Document):
    class Settings:
        name = "definitions"

# items of the conversations
class TKMemoryItemDoc(MEMItem, Document):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[str] = None
    senses: list[str] = Field(default_factory=list)  # flat unique WSD senses across the zip leaves (for associative wondering lookup)

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

# --------------------------------------------------------------
# brain documents (#4 step B): the Idea / Action queues + the brain_state continuity singleton.
# atomic queue transitions use find_one_and_update; brain_state is a singleton keyed by `key`.
# --------------------------------------------------------------
class TKIdeaDoc(MEMIdea, Document):
    class Settings:
        name = "ideas"

class TKActionDoc(MEMAction, Document):
    class Settings:
        name = "actions"

class TKBrainStateDoc(BrainState, Document):
    key: Annotated[str, Indexed(unique=True)] = "singleton"
    class Settings:
        name = "brain_state"

# behavior_rules: the meta-language (C) personality table — [eval:X] -> [tokeniko:Y] @ urge. multiple
# rules may share a trigger (a superposition of candidate reflexes), so the index is NON-unique.
class TKBehaviorRuleDoc(MEMBehaviorRule, Document):
    trigger: Annotated[str, Indexed()] = ""   # non-unique index (multi-rule per trigger)
    class Settings:
        name = "behavior_rules"
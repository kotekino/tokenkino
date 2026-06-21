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

# --------------------------------------------------
# brain — the autonomous mind's data model (#4, step B). See brain/README.md "## Data model".
# the Idea / Action queues (with atomic linear state machines) + the brain_state continuity singleton.
# this is the SHAPE / contract; the urge levels, statuses and deadline are first-cut and to be tuned.
# --------------------------------------------------

# urge level of an idea: the act/don't-act threshold AND the conflict key (highest urge wins).
class UrgeLevel(float, Enum):
    IDEA = 0.1
    WISH = 0.5
    URGE = 0.7
    NEED = 1.0

# linear state machine of a queued idea (atomic transitions via find_one_and_update).
class IdeaStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    DISCARDED = "discarded"

# linear state machine of a queued action.
class ActionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

# the outward act categories — brain decides, senses carries out.
class ActionType(str, Enum):
    SEND_MESSAGE = "send_message"
    CURL = "curl"
    POST_CONTENT = "post_content"

# --------------------------------------------------
# the meta-language (C) — reserved-token behavior layer. The grammar of behavior is HARDWIRED here
# (these two enums = the fixed vocabulary); the POLICY (which trigger maps to which action, at what
# urge) is MEMORY (the `behavior_rules` table = tokeniko's personality). See brain/README.md
# "## The meta-language (behavior rules)".
# --------------------------------------------------

# trigger side — the outcomes of an evaluation (mirrors the evaluator's EvaluatorStatus namespace).
class EvalToken(str, Enum):
    INCONSISTENT = "eval:inconsistent"
    FALSE = "eval:false"
    UNKNOWN = "eval:unknown"
    TRUE = "eval:true"

# action side — the reflexes tokeniko CAN fire (the hardwired repertoire).
class TokenikoAction(str, Enum):
    SPEAKUP = "tokeniko:speakup"
    ASK = "tokeniko:ask"
    WHY = "tokeniko:why"
    GUESS = "tokeniko:guess"
    LEARN = "tokeniko:learn"
    POST = "tokeniko:post"
    IGNORE = "tokeniko:ignore"

# an IDEA — an urge to act (the "maybe"): produced by Thinking, filtered by Priorities, mapped to an
# Action by the meta-language (C). `payload` is what the idea is ABOUT — a single-clause idea wraps as a
# single-leaf TKZip (avoids a TKZip/TKZipContent union). `trigger` is the reserved-token that fired it.
class MEMIdea(BaseModel):
    payload: Optional[TKZip] = None             # what the idea is about
    trigger: str                                # reserved-token (e.g. "eval:inconsistent") — meta-language (C)
    action_token: Optional[str] = None          # the tokeniko:Y reflex baked in from the matched behavior-rule
    urge: float = Field(default=UrgeLevel.IDEA.value)  # act/don't-act threshold + conflict key
    feasibility: Optional[float] = None         # set later by Priorities (can-it-be-done)
    source: Optional[str] = None                # provenance: the memory/theorem/axiom id that spawned it
    status: IdeaStatus = Field(default=IdeaStatus.PENDING)
    parsed_by_prio: bool = Field(default=False)  # awaits the Priorities evaluator
    deadline: Optional[int] = None              # optional epoch-seconds deadline
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# an ACTION — a concrete execution payload (the Actions FIFO queue). brain decides, senses carries out.
class MEMAction(BaseModel):
    action_type: ActionType
    payload: dict = Field(default_factory=dict)  # action-specific (channel, content/message, ...)
    sourceId: str                               # always tokeniko
    targetId: Optional[str] = None
    channel: MEMChannels = Field(default=MEMChannels.INTERNAL)
    status: ActionStatus = Field(default=ActionStatus.PENDING)
    ideaId: Optional[str] = None                # provenance: the idea that yielded this action
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# a behavior rule [eval:X] -> [tokeniko:Y] @ urge — KB-driven PERSONALITY (multiple rules may share a
# trigger: a superposition of candidate reflexes; Priorities arbitrates). syntax is hardwired, this
# CONTENT is memory. enabled lets a rule be toggled; order is a tiebreak hint.
class MEMBehaviorRule(BaseModel):
    trigger: str                      # an EvalToken value, e.g. "eval:unknown"
    action: str                       # a TokenikoAction value, e.g. "tokeniko:why"
    urge: float = Field(default=UrgeLevel.WISH.value)
    enabled: bool = Field(default=True)
    order: int = Field(default=0)
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# the BRAIN_STATE singleton — cognitive continuity across process restarts: the working-memory cursor
# and the wondering window, so tokeniko resumes its cycles without gaps (one continuous self).
class BrainState(BaseModel):
    key: str = "singleton"                      # the singleton key (unique-indexed on the doc)
    working_memory_cursor: Optional[int] = None  # last-processed memory timestamp (epoch seconds)
    wondering_window: Optional[list[int]] = None  # [lo, hi] of the current wondering window
    last_thinking_at: Optional[int] = None
    last_wondering_at: Optional[int] = None

# --------------------------------------------------------------
# API schemas + error mapping.
# The in/out request/response models and the domain-error -> HTTP translation, kept out of
# main.py so it holds only the lifespan and the endpoint handlers.
# --------------------------------------------------------------
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field
from bunnet import PydanticObjectId

from api.services import (
    AxiomNotFoundError, InvalidAxiomIdError,
    DefinitionNotFoundError, InvalidDefinitionIdError,
    TheoremNotFoundError, InvalidTheoremIdError,
    StakeholderNotFoundError, InvalidStakeholderIdError,
    MemoryNotFoundError, InvalidMemoryIdError,
)
from api.services.validation import InconsistentStatementError

# ------------------------------ axioms ------------------------------
class AxiomIn(BaseModel):
    tokens: str  # sentence to compile and store as an axiom

class AxiomPatch(BaseModel):
    tokens: Optional[str] = None       # if present, recompiles original/zip/raw
    trusted: Optional[float] = None
    archived: Optional[bool] = None
    readonly: Optional[bool] = None
    channel: Optional[str] = None

class AxiomReplace(BaseModel):
    tokens: str
    trusted: float = 1.0
    archived: bool = False
    readonly: bool = True

class AxiomSummary(BaseModel):  # listing view (no zip)
    id: PydanticObjectId = Field(alias="_id")
    original: str
    raw: Optional[str] = None
    trusted: float
    archived: bool
    readonly: bool
    channel: Optional[str] = None
    createdAt: int

# ------------------------------ definitions ------------------------------
class DefinitionIn(BaseModel):
    tokens: str  # single-clause sentence to compile and store as a definition

class DefinitionPatch(BaseModel):
    tokens: Optional[str] = None       # if present, recompiles original/zip/raw
    trusted: Optional[float] = None
    archived: Optional[bool] = None
    readonly: Optional[bool] = None
    channel: Optional[str] = None

class DefinitionReplace(BaseModel):
    tokens: str
    trusted: float = 1.0
    archived: bool = False
    readonly: bool = True

class DefinitionSummary(BaseModel):  # listing view (no zip)
    id: PydanticObjectId = Field(alias="_id")
    original: str
    raw: Optional[str] = None
    trusted: float
    archived: bool
    readonly: bool
    channel: Optional[str] = None
    createdAt: int

# ------------------------------ theorems (no readonly) ------------------------------
class TheoremIn(BaseModel):
    tokens: str  # sentence to compile and store as a theorem

class TheoremPatch(BaseModel):
    tokens: Optional[str] = None       # if present, recompiles original/zip/raw
    trusted: Optional[float] = None
    archived: Optional[bool] = None
    channel: Optional[str] = None

class TheoremReplace(BaseModel):
    tokens: str
    trusted: float = 0.9
    archived: bool = True

class TheoremSummary(BaseModel):  # listing view (no zip)
    id: PydanticObjectId = Field(alias="_id")
    original: str
    raw: Optional[str] = None
    trusted: float
    archived: bool
    channel: Optional[str] = None
    createdAt: int

# ------------------------------ stakeholders (read-only) ------------------------------
class StakeholderSummary(BaseModel):  # listing view
    id: PydanticObjectId = Field(alias="_id")
    name: str
    uid: str
    channel: Optional[str] = None
    isMe: bool
    createdAt: int

# ------------------------------ memory (timeseries log; no update) ------------------------------
class MemoryIn(BaseModel):
    original: str                       # the log text
    sourceId: str                       # stakeholder objectId of the source (talker)
    targetId: Optional[str] = None      # stakeholder objectId of the target (listener)
    channel: Optional[str] = None       # channel of origin (e.g. "api", "internal")
    metadata: Optional[str] = None      # timeseries meta field

class MemorySummary(BaseModel):  # listing view (no big zip)
    id: PydanticObjectId = Field(alias="_id")
    original: str
    sourceId: str
    targetId: Optional[str] = None
    channel: Optional[str] = None
    timestamp: datetime

# ------------------------------ evaluate (action; stores nothing) ------------------------------
class EvaluateIn(BaseModel):
    tokens: str  # sentence to compile and evaluate against tokeniko's knowledge

# ------------------------------ domain-error -> HTTP mapping ------------------------------
# run a service action, translating its (invalid-id, not-found) domain errors to 400/404
def _or_http(action, invalid_exc, not_found_exc, name: str):
    try:
        return action()
    except invalid_exc:
        raise HTTPException(status_code=400, detail="invalid object id")
    except not_found_exc:
        raise HTTPException(status_code=404, detail=f"{name} not found")

def axiom_or_http(action):
    return _or_http(action, InvalidAxiomIdError, AxiomNotFoundError, "axiom")

def definition_or_http(action):
    return _or_http(action, InvalidDefinitionIdError, DefinitionNotFoundError, "definition")

def theorem_or_http(action):
    return _or_http(action, InvalidTheoremIdError, TheoremNotFoundError, "theorem")

def stakeholder_or_http(action):
    return _or_http(action, InvalidStakeholderIdError, StakeholderNotFoundError, "stakeholder")

def memory_or_http(action):
    return _or_http(action, InvalidMemoryIdError, MemoryNotFoundError, "memory item")

# run a create/patch/replace action, translating validation failures to HTTP 422:
# a contradictory FORM (logic-is-sacred). Anything else re-raises.
def create_or_http(action):
    try:
        return action()
    except InconsistentStatementError as error:
        raise HTTPException(status_code=422, detail=str(error))

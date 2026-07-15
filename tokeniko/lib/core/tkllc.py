# --------------------------------------------------
# flat llc
# --------------------------------------------------
# spacetime representation for an entity (in the relative space of the context of the statement, not absolute spacetime)
from typing import Optional, Union
from pydantic import BaseModel, Field
from lib.core.tk import TKAux, TKClauseType, TKMarker, TKOperator, TKQuantifier, TKWhRole

# spacetime
class TKLLSpacetime(BaseModel):
    size: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the size of the entity in spacetime
    position: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the center of the entity in spacetime
    velocity: list[float] = Field(default=[0,0,0,0], min_length=4, max_length=4) # [t, x, y, z], represent the velocity of the entity in spacetime

# the absolute scene frame: the RAW [min, max] bounds used to normalize entity coords to [-1,1].
# entity spacetime is normalized within these, so the map is the de-normalization key and
# preserves the absolute anchor (time/space) that normalization would otherwise discard.
# the spatial axes share the isotropic [minSpace, maxSpace] scale (xbounds == ybounds == zbounds).
class TKLLSpacetimeMap(BaseModel):
    tbounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # raw [min, max] time
    xbounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # raw [min, max] space
    ybounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # raw [min, max] space
    zbounds: list[float] = Field(default=[-1,1], min_length=2, max_length=2) # raw [min, max] space

# entity: can have different semantic vectors
class TKLLEntity(BaseModel):
    id: int
    token: str
    entity_type: str = Field(default='generic')
    semantic_vector: list[float] = Field(default_factory=list)
    geo: Optional[list[float]] = None  # [lon, lat(, alt)] for known places, used by the space axis
    # WSD-assigned WordNet synset key (e.g. "cat.n.01") for dictionary entities; the bridge that
    # carries the parse-time sense across the LLC boundary so the evaluator can reach the is_a graph.
    sense: Optional[str] = None
    # context-scoped identity uid for an entity-linked named individual ("mari@api:<uid>"); the
    # identity-bridge that carries referential identity across the LLC boundary (parallel to sense).
    uid: Optional[str] = None

# map from tkentity and tkllentity
class TKLLEntityMap(BaseModel):
    entity: TKLLEntity
    ref: list[TKLLEntityMapReference]

# map reference for tkentities
class TKLLEntityMapReference(BaseModel):
    inputStatementIdx: int = Field(default=1)
    inputStatementId: tuple[int, ...] = Field(default=())
    inputEntityId: int

# entity reference for the content
class TKLLEntityReference(BaseModel):
    id: int
    dep: str
    aux: Optional[TKAux] = None
    marker: Optional[TKMarker] = None
    spacetime: TKLLSpacetime = Field(default_factory=TKLLSpacetime)
    properties: list[TKLLEntityProperty] = Field(default_factory=list)

# entity property: can have properties, reference an entity id
class TKLLEntityProperty(BaseModel):
    id: int
    dep: str
    properties: list[TKLLEntityProperty] = Field(default_factory=list)

#  property related the sentence by the talker point of view
class TKLLProperties(BaseModel):
    ironic: float = Field(default=0.5) # literal 0 / neutral 0.5 / ironic 1
    dubitative: float = Field(default=0.5) # statement 0 / question 1
    imperative: float = Field(default=0.5) # neutral 0 / order 1
    sentiment: list[float] = Field(default_factory=lambda: ([0.0] * 2925)) # related to one or more base words

# llc content: can be a content or another llcitem (recursive)
class TKLLCContent(BaseModel):
    clause_type: TKClauseType = Field(default=TKClauseType.MAIN)
    properties: TKLLProperties
    # clause-level negation: the clause asserts ¬P. set when a role carries a negation marker
    # ("not"/"no"/"never"); a discrete, recoverable signal carried through to the TKZipContent.
    negated: bool = Field(default=False)
    # reflexive identity (a=a / a≠a): operands corefer in an identity comparison. polarity stays in `negated`.
    reflexive: bool = Field(default=False)
    # quantifier read off the SUBJECT's determiner (all/some/no/the/bare). drives the
    # quantifier-aware truth flip in the relational grounding; default GENERIC (bare/no determiner).
    quantifier: TKQuantifier = Field(default=TKQuantifier.GENERIC)
    # wh-question gap role (the variable X to solve for); None = polar question or declarative.
    # mood itself rides `properties.dubitative` (statement 0.5 / question 1.0).
    wh_role: Optional[TKWhRole] = Field(default=None)
    # adversative join ("but"/"however"/…): the clause is co-asserted (its op is AND) with a
    # defied-expectation nuance. A carrier (like `modal`), never an operator — the asserted content
    # of "X but Y" is exactly X∧Y; the contrast is implicature, preserved for a later consumer
    # (default/generic reasoning). M1 2026-07-16.
    contrast: bool = Field(default=False)
    subject: Optional[TKLLEntityReference] = Field(default=None)
    predicate: Optional[TKLLEntityReference] = Field(default=None) 
    direct: Optional[TKLLEntityReference] = Field(default=None) 
    indirects: list[TKLLEntityReference] = Field(default_factory=list)

# attitude of a propositional complement bound by THAT: how the matrix predicate holds X.
# factive (know/realize) presupposes X is true; doxastic (believe/think/assume) is belief held
# at confidence < 1; desiderative (want/hope) is an irrealis goal (X not asserted as true);
# reportative (say/claim) attributes X to a source with truth uncommitted. `confidence` is the
# world-truth projection of X in [0,1] - a tunable default; the fuzzy projection of X into the
# zip math is left to the semantic-calculation layer.
class TKLLAttitude(BaseModel):
    verb: Optional[str] = None  # the embedding predicate lemma ("assume")
    # factive | doxastic | desiderative | reportative — or None: the matrix verb holds NO attitude
    # (below the anchor floor; a ccomp under a non-attitude verb is a suspect parse)
    klass: Optional[str] = "doxastic"
    confidence: float = 0.5

class TKLLCItem(BaseModel):
    op: TKOperator = Field(default=TKOperator.AND)
    attitude: Optional[TKLLAttitude] = None  # set on THAT items: the reified complement X
    content: Optional[LLCItemPayload] = None

# llc 
class TKLLC(BaseModel):
    map: TKLLSpacetimeMap = Field(default_factory=TKLLSpacetimeMap)
    items: list[TKLLCItem] = Field(default_factory=list)
    entities: list[TKLLEntity] = Field(default_factory=list)
    
# payload for item
LLCItemPayload = Union[list[TKLLCItem], TKLLCContent]
TKLLCItem.model_rebuild()
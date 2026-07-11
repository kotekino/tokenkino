from datetime import datetime, timezone
from typing import Annotated, Optional
from bunnet import Document, Granularity, Indexed, TimeSeriesConfig
from pydantic import Field
from lib.core.tk import TKBase, TKDictionary, TKMarker, TKName, TKPlace, TKProperty
from lib.core.memory import MEMAxiom, MEMDefinition, MEMTheorem, MEMItem, MEMStakeholder, MEMIdea, MEMAction, MEMBehaviorRule, MEMTrustEpisode, BrainState

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

# the LOW-TRUST, revocable is_a tier mined from the definitions (definitions-as-rules, step 3). Kept in
# a SEPARATE collection so the pristine ~150k-edge WordNet `relations` bedrock is NEVER polluted:
# revoking the whole tier = dropping this collection, and every edge carries its provenance (the source
# definition + trust + extractor method) so a single edge — and any theorem resting on it — is
# retractable (step 4). The evaluator's is_a reader UNIONS bedrock ∪ this tier; the ingestion untangle
# does NOT (it must disambiguate against the trusted graph only). Same {subject, relation, object, pos}
# shape as bedrock + the provenance fields.
class TKDerivedRelationDoc(Document):
    subject: str
    relation: str
    object: str
    pos: Optional[str] = None
    source_id: str                     # the definition doc id this edge was mined from
    source_original: str               # the definition text (for audit / revocation review)
    trust: float = 0.3                 # low-trust tier (bedrock is implicitly 1.0)
    method: str = "genus-extract-v1"   # extractor version — a full rebuild replaces one method's edges

    class Settings:
        name = "derived_relations"

# the LOW-TRUST, revocable definition-derived RULE tier. Two rule kinds, both mined off the same
# biconditional (a definition is X ⟺ genus ∧ definiens — Brain v1.1 #3):
#   kind="property"   — the NECESSARY direction (differentia, step 5): "a carnivore is an animal that
#                       eats meat" -> "all carnivores eat meat", cascades DOWN the is_a hierarchy.
#                       Uses subject/predicate/object/negated.
#   kind="sufficient" — the SUFFICIENT direction (step 4): whatever satisfies the WHOLE definiens IS
#                       an X — "(is_a animal ∧ eats meat) -> is_a carnivore". Recognition/
#                       classification. Uses subject (the concluded class X), genus (the class
#                       condition) and conds (the property conditions); predicate is unused ("").
# Same separate-collection + provenance discipline as the edge tier (never pollutes the seeded
# axioms; revocable; trust-tiered). The evaluator UNIONS these into the forward-chainer's rule set; a
# theorem derived through one inherits its low trust (min-trust) and names it as a premise.
class TKDerivedRuleDoc(Document):
    subject: str                       # the definiendum class X (a noun sense)
    predicate: str = ""                # property: the differentia predicate | sufficient: unused
    object: Optional[str] = None       # the differentia's direct object, if any
    negated: bool = False              # carried from the differentia leaf ("no ability to roar")
    kind: str = "property"
    genus: Optional[str] = None        # sufficient only: the is_a class condition
    conds: Optional[list[dict]] = None  # sufficient only: [{"predicate", "object"}, ...] — ALL must hold
    source_id: str                     # the definition doc id this rule was mined from
    source_original: str               # the definition text (for audit / revocation review)
    trust: float = 0.3                 # low-trust tier (bedrock axioms are implicitly 1.0)
    method: str = "differentia-v1"     # extractor version — a full rebuild replaces one method's rules

    class Settings:
        name = "derived_rules"

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

# trust_episodes: the trust ledger's permanent trail (senses D) — the SOURCE OF TRUTH the
# stakeholder's folded `trust` scalar is recomputed from (lib/core/trust.fold_trust). Append-only
# biography, never wiped (post-ceremony discipline).
class TKTrustEpisodeDoc(MEMTrustEpisode, Document):
    stakeholder_uid: Annotated[str, Indexed()] = ""   # non-unique (many episodes per stakeholder)
    class Settings:
        name = "trust_episodes"
# ------------------------------------------------------------------------------------------------
# ZIP
# turn the flat LLC into the final fixed-size numeric TKZip: marker + semantic + spacetime vectors,
# with advmod scalar fusion and tanh soft-normalization.
# ------------------------------------------------------------------------------------------------
import numpy as np

from lib.core.tk import TKMarker
from lib.core.tkllc import TKLLCContent, TKLLCItem, TKLLEntityMap, TKLLEntityProperty, TKLLEntityReference
from lib.core.tkzip import TKZipContent, TKZipItem
from lib.core.models import _VECTOR_INDEX, TKMarkerDoc
from lib.llc.constants import _MARKER_SIMILARITY_THRESHOLD, _NEGATION_MARKERS
from lib.llc.anchors import anchor_resolve_vector

from .c_state import _entities, nlp

# get base marker from marker
def compiler_zipGetBaseMarker(token: str) -> TKMarker:
    lemma = str(token).lower()
    exact_match = TKMarkerDoc.find_one(TKMarkerDoc.word == lemma).run()

    if exact_match:
        runtime_marker = TKMarker(**exact_match.model_dump())
        return runtime_marker

    new_doc = nlp(lemma)
    new_vector = new_doc[0].vector.tolist() if len(new_doc) > 0 else []

    pipeline = [
        {
            "$vectorSearch": {
                "index": _VECTOR_INDEX,
                "path": "vector",
                "queryVector": new_vector,
                "numCandidates": 50,
                "limit": 1
            }
        },
        {
            "$project": {
                "_id": 0,
                "word": 1,
                "vector": 1,
                "definition": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]

    search_results = list(TKMarkerDoc.aggregate(pipeline).run())

    if search_results:
        best_match = search_results[0]
        mongo_score = best_match.get("score", 0.0)
        if mongo_score >= _MARKER_SIMILARITY_THRESHOLD:
            best_match.pop("score", None)
            runtime_marker = TKMarker(**best_match)
            return runtime_marker

    new_marker_doc = TKMarkerDoc(
        word=lemma,
        vector=new_vector,
        definition=""
    )
    new_marker_doc.insert()
    runtime_marker = TKMarker(**new_marker_doc.model_dump())

    return runtime_marker

# get advmode
def compiler_zipGetAdvmodeBase(propVec: np.ndarray) -> tuple[float, float]:

    # error gate
    if propVec.min() == propVec.max() == 0.0: return 1,1

    # unified anchor resolver on the in-hand 2925-dim propVec (no Mongo): nearest intensifier anchor
    # >= floor -> its scalar weight; else the category default 1.0. anchors are 0.3/0.5/1.5/2.0, so a
    # returned weight of exactly 1.0 means "no real anchor matched" -> keep the (1.0, 1.0) contract.
    weight = anchor_resolve_vector(propVec, "intensifiers")
    if weight != 1.0:
        return (weight, 0.0)
    return (1.0, 1.0)

# sum property (Ora fa solo algebra lineare pura)
def compiler_zipSumProperty(dep: str, entVec: np.ndarray, propVec: np.ndarray) -> np.ndarray:

    # if property
    weightProp: float = 1.0
    weightEnt: float = 1.0

    # calculate weight
    if dep == "advmod":
        weightEnt, weightProp = compiler_zipGetAdvmodeBase(propVec)
    #elif dep == "nmod":
    # etc

    # combine array using weights
    combined_vec: np.ndarray = (weightEnt * entVec) + (weightProp * propVec)
    return combined_vec

# get vector from an entity
def compiler_zipGetEntityVector(entity: TKLLEntityMap, properties: list[TKLLEntityProperty]) -> np.ndarray:

    # default vector
    entityVec = np.zeros(2925, dtype=np.float32)

    # get semantic for entities
    if entity.entity.entity_type == "dictionary":
        if len(entity.entity.semantic_vector) > 0:
            entityVec = np.array(entity.entity.semantic_vector, dtype=np.float32)

    # merge properties
    for p in properties:
        propEnt = next(e for e in _entities if p.id == e.entity.id)
        # negation markers ("not"/"no"/"never") are captured as the discrete TKZipContent.negated
        # flag (Decision 1), NOT folded into the geometry -- skip them so the role vector stays the
        # affirmative meaning (and the legacy advmod "-1" flip can't double-apply).
        if (propEnt.entity.token or "").lower() in _NEGATION_MARKERS:
            continue
        propVec = compiler_zipGetEntityVector(propEnt, p.properties)
        # blend vectors (linear accumulation)
        entityVec = compiler_zipSumProperty(p.dep, entityVec, propVec)

    # soft normalization
    result = np.tanh(entityVec)
    return result

# get base marker vector
def compiler_zipGetMarker(word: str) -> list[float]:
    baseMarker = compiler_zipGetBaseMarker(word)
    return baseMarker.vector if baseMarker else np.zeros(300).tolist()

# get vector from a reference
def compiler_zipGetVector(ref: TKLLEntityReference) -> list[float]:
    vector: list[float] = []

    # empty reference
    if ref == None:
        return np.zeros(3237).tolist()

    entity = next(e for e in _entities if ref.id == e.entity.id)
    marker: list[float] = compiler_zipGetMarker(ref.marker.word) if ref.marker else np.zeros(300).tolist()
    semantic: list[float] = compiler_zipGetEntityVector(entity, ref.properties).tolist()
    spacetime: list[float] = ref.spacetime.size + ref.spacetime.position + ref.spacetime.velocity
    vector = marker + semantic + spacetime

    return vector

# does a reference resolve to a GENERIC (unknown-word fallback) entity? generic entities carry no
# dictionary sense / semantic vector, so they are not groundable.
def compiler_zipRefIsGeneric(ref: TKLLEntityReference) -> bool:
    if ref is None:
        return False
    entity = next((e for e in _entities if ref.id == e.entity.id), None)
    return entity is not None and entity.entity.entity_type == "generic"

# a clause is UNKNOWN (ungroundable) when it has core arguments but ALL of them are generic/unknown —
# i.e. tokeniko knows none of the "who/what" the clause is about (the copula/predicate alone is not
# enough). a clause with at least one known core argument, or none at all, is left groundable.
def compiler_zipContentUnknown(content: TKLLCContent) -> bool:
    core = [r for r in ([content.subject, content.direct] + content.indirects) if r is not None]
    return bool(core) and all(compiler_zipRefIsGeneric(r) for r in core)

# calculate final vector for the content
def compiler_zipContent(content: TKLLCContent) -> TKZipContent:
    ironic = content.properties.ironic
    dubitative = content.properties.dubitative
    imperative = content.properties.imperative
    sentiment = content.properties.sentiment
    subject = compiler_zipGetVector(content.subject)
    direct = compiler_zipGetVector(content.direct)
    predicate = compiler_zipGetVector(content.predicate)
    indirects: list[list[float]] = []
    for i in content.indirects:
        indirects.append(compiler_zipGetVector(i))

    return TKZipContent(ironic=ironic, dubitative=dubitative, imperative=imperative, negated=content.negated, reflexive=content.reflexive, unknown=compiler_zipContentUnknown(content), sentiment=sentiment, subject=subject, direct=direct, predicate=predicate, indirects=indirects)

# calculate final vectors for the statements
def compiler_zip(items: list[TKLLCItem]) -> list[TKZipItem]:
    result: list[TKZipItem] = []
    for item in items:
        if isinstance(item.content, TKLLCContent):
            result.append(TKZipItem(op=item.op, attitude=item.attitude, content=compiler_zipContent(item.content)))
        else:
            result.append(TKZipItem(op=item.op, attitude=item.attitude, content=compiler_zip(item.content)))
    return result

# ------------------------------------------------------------------------------------------------
# ZIP
# turn the flat LLC into the final fixed-size numeric TKZip: marker + semantic + spacetime vectors,
# with advmod scalar fusion and tanh soft-normalization.
# ------------------------------------------------------------------------------------------------
import numpy as np

from lib.core.tk import TKMarker
from lib.core.tkllc import TKLLCContent, TKLLCItem, TKLLEntityMap, TKLLEntityProperty, TKLLEntityReference
from lib.core.tkzip import TKZipContent, TKZipItem
from lib.core.models import _VECTOR_INDEX, TKDictionaryDoc, TKMarkerDoc
from lib.llc.constants import _MARKER_SIMILARITY_THRESHOLD, _PROP_BASE_ADVMOD_ANCHORS, _PROP_SIMILARITY_THRESHOLD

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

    pipeline = [
        {
            "$vectorSearch": {
                "index": _VECTOR_INDEX,
                "path": "vector",
                "queryVector": propVec.tolist(),
                "numCandidates": 50,
                "limit": 1
            }
        },
        {
            "$project": {
                "_id": 0,
                "word": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]

    search_results = list(TKDictionaryDoc.aggregate(pipeline).run())

    weightEnt = 1.0
    weightProp = 1.0

    if search_results:
        top_result = search_results[0]
        match_word = top_result.get("word", "")
        score = top_result.get("score", 0.0)

        if score >= _PROP_SIMILARITY_THRESHOLD and match_word in _PROP_BASE_ADVMOD_ANCHORS:
            weightEnt = _PROP_BASE_ADVMOD_ANCHORS[match_word]
            weightProp = 0.0

    return weightEnt, weightProp

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

    return TKZipContent(ironic=ironic, dubitative=dubitative, imperative=imperative, sentiment=sentiment, subject=subject, direct=direct, predicate=predicate, indirects=indirects)

# calculate final vectors for the statements
def compiler_zip(items: list[TKLLCItem]) -> list[TKZipItem]:
    result: list[TKZipItem] = []
    for item in items:
        if isinstance(item.content, TKLLCContent):
            result.append(TKZipItem(op=item.op, attitude=item.attitude, content=compiler_zipContent(item.content)))
        else:
            result.append(TKZipItem(op=item.op, attitude=item.attitude, content=compiler_zip(item.content)))
    return result

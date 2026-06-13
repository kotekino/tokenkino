# ------------------------------------------------------------------------------------------------
# EVALUATOR — label / single-word representation
# assigns the single most representative dictionary word to a compiled statement (a TKZip):
# blend the semantic segments of all role vectors into one 2925-dim centroid ("the meaning"),
# then find the nearest dictionary word via a MongoDB $vectorSearch.
#
# NOTE: unlike the rest of the evaluator (pure geometry on in-memory tensors), this module
# queries Mongo directly — the same pattern as lib/llc/compiler/c_zip.py
# (compiler_zipGetBaseMarker / compiler_zipGetAdvmodeBase). That direct DB access is
# acceptable here because the dictionary semantic space lives in Mongo and is indexed there.
# ------------------------------------------------------------------------------------------------
from typing import Optional
import numpy as np
from pydantic import BaseModel

from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from lib.core.models import _VECTOR_INDEX, TKDictionaryDoc

# layout of a role/indirect vector: marker[0:300] + semantic[300:3225] + spacetime[3225:3237].
_SEMANTIC_START = 300
_SEMANTIC_END = 3225  # 300 + 2925

# the result of assigning a word: the nearest dictionary word + its vectorSearch score.
class TKWordLabel(BaseModel):
    word: str
    score: float

# extract the semantic segment [300:3225] of a single role vector, or None if the role is
# absent (empty / all-zero, the compiler zero-pads missing roles).
def _semantic_segment(vector: Optional[list[float]]) -> Optional[np.ndarray]:
    if not vector:
        return None
    seg = np.asarray(vector[_SEMANTIC_START:_SEMANTIC_END], dtype=np.float32)
    if seg.shape[0] != (_SEMANTIC_END - _SEMANTIC_START):
        return None
    if not np.any(seg):
        return None
    return seg

# collect the semantic segments of every present role of one clause (subject/predicate/direct +
# each indirect) into the accumulator.
def _collectContent(content: TKZipContent, acc: list[np.ndarray]) -> None:
    for role in (content.subject, content.predicate, content.direct):
        seg = _semantic_segment(role)
        if seg is not None:
            acc.append(seg)
    for indirect in content.indirects:
        seg = _semantic_segment(indirect)
        if seg is not None:
            acc.append(seg)

# recursively walk the TKZipItem tree, collecting the semantic segments of every leaf clause.
def _collectItem(item: TKZipItem, acc: list[np.ndarray]) -> None:
    content = item.content
    if isinstance(content, TKZipContent):
        _collectContent(content, acc)
    elif isinstance(content, list):
        for child in content:
            _collectItem(child, acc)

# nearest dictionary word to a 2925-dim semantic centroid (mirrors the $vectorSearch in c_zip.py).
def _nearestWord(centroid: np.ndarray) -> Optional[TKWordLabel]:
    pipeline = [
        {
            "$vectorSearch": {
                "index": _VECTOR_INDEX,
                "path": "vector",
                "queryVector": centroid.tolist(),
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
    if not search_results:
        return None

    top_result = search_results[0]
    return TKWordLabel(word=top_result.get("word", ""), score=top_result.get("score", 0.0))

# assign the single most representative dictionary word to a compiled statement.
# blends the SEMANTIC segments [300:3225] of all present role vectors of every leaf clause into one
# 2925-dim centroid (the statement's "meaning"), then returns the nearest dictionary word + score.
# returns None if the statement has no semantic content or no nearest word is found.
def evaluator_assignWord(statement: TKZip) -> Optional[TKWordLabel]:
    segments: list[np.ndarray] = []
    _collectItem(statement.items, segments)

    if not segments:
        return None

    # average the non-zero role segments into one centroid
    centroid = np.mean(np.stack(segments, axis=0), axis=0)
    if not np.any(centroid):
        return None

    return _nearestWord(centroid)

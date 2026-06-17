from lib.core.models import TKDictionaryDoc, TKBaseDoc
from lib.core.models import _VECTOR_INDEX

# ------------------------------------------------------------------------------------------------
# ANTONYM PRIMITIVE (the "column read")
# the 2925 base words form a square-ish co-occurrence/semantic matrix: base[X].vector[idx(W)] is the
# signed relation of base word X to base word W on W's own axis. a NEGATIVE value means X sits on the
# opposite pole of W -> X is an antonym of W. so antonyms(W) is the column read:
#     antonyms(W) = { X : base[X][idx(W)] < 0 }
# it is sense/word-scoped (keyed on the base word W's axis) and returns the SET of opposite base
# words. verified: love->{hate,...}, good->{bad,...}, same->{different,...}. used by the compiler to
# decide comparison-predicate polarity (Decision 2) and reusable wherever opposition is needed.
# NB this is geometric OPPOSITION (a different axis), NOT the dictionary's pairwise cosine
# relatedness -- semantic antonymy is otherwise memory-knowledge (see memory `dictionary-semantics`).
# ------------------------------------------------------------------------------------------------

# antonyms of a single base word via the column read. returns the set of base words on W's opposite
# pole (base[X][idx(W)] < 0), excluding W itself. empty set when W is not a base word.
def utils_antonyms(word: str) -> set[str]:
    word = (word or "").strip().lower()
    if not word:
        return set()

    # locate W's axis (its column index in the 2925-dim base space)
    target = TKBaseDoc.find_one(TKBaseDoc.word == word).run()
    if target is None:
        return set()
    idx = target.index

    # column read: every base word X whose value on W's axis is negative is an antonym of W.
    # project only word + the single axis component (vector.idx) so we don't pull 2925-dim rows.
    result: set[str] = set()
    pipeline = [
        {"$match": {f"vector.{idx}": {"$lt": 0}}},
        {"$project": {"_id": 0, "word": 1}},
    ]
    for res in TKBaseDoc.aggregate(pipeline).run():
        candidate = res.get("word")
        if candidate and candidate != word:
            result.add(candidate)
    return result

# is `word` an antonym of any of the affirmative `anchors`? used to detect negative-comparison
# predicates ("different"/"unlike" are antonyms of "same"/"equal" -> the comparison is negated).
# True iff `word` appears in the antonym column of at least one anchor, OR an anchor appears in the
# antonym column of `word` (the relation is read symmetrically to tolerate sparse columns).
def utils_isAntonymOf(word: str, anchors: set[str]) -> bool:
    word = (word or "").strip().lower()
    if not word:
        return False
    for anchor in anchors:
        if word in utils_antonyms(anchor):
            return True
    # symmetric fallback: anchors found in word's own antonym column
    wordAntonyms = utils_antonyms(word)
    return any(a in wordAntonyms for a in anchors)

# search semantically similar entities
def utils_searchSimilarTokens(token: str, limit: int = 10):
    result = []

    docs = TKDictionaryDoc.find_many(TKDictionaryDoc.word == token).run()
    for doc in docs:
        returnResults = []
        word = ''
        pipeline = [
            {
                "$vectorSearch": {
                    "index": _VECTOR_INDEX,
                    "path": "vector",
                    "queryVector": doc.vector,
                    "numCandidates": limit * 10,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "word": 1,
                    "sense": 1,
                    "definition": 1,
                    "score": { "$meta": "vectorSearchScore" }
                }
            }
        ]

        results = TKDictionaryDoc.aggregate(pipeline)
        for i, res in enumerate(results, 1):
            similar = {
                "word": res.get("word", "unknown"), 
                "score": res.get("score", 0.0), 
                "sense": res.get("sense", "unknown"),
                "definition": res.get("definition", "unknown")
            }
            returnResults.append(similar)

        if len(returnResults) > 0: returnResults.pop(0)

        word = {
            "word": doc.word, 
            "sense": doc.sense,
            "definition": doc.definition
        }
        result.append({
            "word": word,
            "similar": returnResults
        })

    return result

# search semantically opposite entities
def utils_searchDissimilarTokens(token: str, limit: int = 10):
    result = []

    docs = TKDictionaryDoc.find_many(TKDictionaryDoc.word == token).run()
    for doc in docs:
        returnResults = []
        
        # 1. IL TRUCCO MAGICO: Invertiamo il vettore per creare l'"Anti-Concetto"
        # Moltiplichiamo ogni dimensione per -1
        anti_vector = [-v for v in doc.vector]

        pipeline = [
            {
                "$vectorSearch": {
                    "index": _VECTOR_INDEX,
                    "path": "vector",
                    "queryVector": anti_vector, # Usiamo l'anti-vettore qui!
                    "numCandidates": limit * 10,
                    "limit": limit
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "word": 1,
                    "sense": 1,
                    "definition": 1,
                    "score": { "$meta": "vectorSearchScore" }
                }
            }
        ]

        results = TKDictionaryDoc.aggregate(pipeline)
        for i, res in enumerate(results, 1):
            similar = {
                "word": res.get("word", "unknown"), 
                # Nota: Questo score ora rappresenta quanto la parola è "opposta" all'originale
                "score": res.get("score", 0.0), 
                "sense": res.get("sense", "unknown"),
                "definition": res.get("definition", "unknown")
            }
            returnResults.append(similar)

        # 2. Ho rimosso il .pop(0) perché il termine originale 
        # non sarà in questa lista (è dal lato opposto dell'universo)

        word_info = {
            "word": doc.word, 
            "sense": doc.sense,
            "definition": doc.definition
        }
        result.append({
            "word": word_info,
            "dissimilar": returnResults # Rinominato per chiarezza
        })

    return result
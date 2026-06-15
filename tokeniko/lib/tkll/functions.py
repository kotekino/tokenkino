from lib.core.models import TKDictionaryDoc
from lib.core.models import _VECTOR_INDEX

# search semantically similar entities
def tkll_searchSimilarTokens(token: str, limit: int = 10):
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
def tkll_searchDissimilarTokens(token: str, limit: int = 10):
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
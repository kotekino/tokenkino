from lib.core.models import TKDictionaryDoc
from lib.core.models import _VECTOR_INDEX

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
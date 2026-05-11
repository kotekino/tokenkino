# define constants
from lib.core.entities import TKClauseType, TKOperator

_ERRORS_UNABLE_TO_PROCESS: str = "Unable to process the sentence"
_SPACY_MAX_SIMILAR_RESULTS: int = 5
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)
_OPERATORS_BASE_ANCHORS = {
    "and": TKOperator.AND, 
    "or": TKOperator.OR, 
    "not": TKOperator.NOT,
    ",": TKOperator.AND,
    ":": TKOperator.THAT,
    "so": TKOperator.THAT
    }
_OPERATORS_SIMILARITY_THRESHOLD: float = 0.7 
_SUBORDINATE_TYPE_BASE_ANCHORS = {
    "because": TKClauseType.CAUSAL, 
    "if": TKClauseType.HYPOTETIC, 
    "from": TKClauseType.LOCATIVE, 
    "in": TKClauseType.LOCATIVE, 
    "when": TKClauseType.TEMPORAL,
    "to": TKClauseType.XCOMP,
    "that": TKClauseType.CCOMP
    }
_SUBORDINATE_TYPE_SIMILARITY_THRESHOLD: float = 0.6
_OLLAMA_MODEL1 = 'llama3:8b' # general purpose 8b
_OLLAMA_MODEL2 = 'gemma2:9b' # general purpose 3.8b
_OLLAMA_TRANS1 = 'aya:8b' # translation 8b
_OLLAMA_TRANS2 = 'translategemma:4b' # translation 4b
_PRE_SIMILARITY_THRESHOLD = 0.8
_MIN_SIMILARITY = 0.9
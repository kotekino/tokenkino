# define constants
from lib.core.entities import TKOperator

_ERRORS_UNABLE_TO_PROCESS: str = "Unable to process the sentence"
_SPACY_MAX_SIMILAR_RESULTS: int = 5
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)
_OPERATORS_BASE_ANCHORS = {"and": TKOperator.AND, "or": TKOperator.OR, "not": TKOperator.NOT}
_OPERATORS_SIMILARITY_THRESHOLD: float = 0.7 # threshold for fuzzy logic in operator mapping
_OLLAMA_MODEL1 = 'llama3:latest'
_OLLAMA_MODEL2 = 'phi3:latest'
_PRE_SIMILARITY_THRESHOLD = 0.8
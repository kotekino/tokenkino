# define constants
from lib.core.tk import TKClauseType, TKOperator

# errors
_ERRORS_UNABLE_TO_PROCESS: str = "Unable to process the sentence"

# spacy
_SPACY_MAX_SIMILAR_RESULTS: int = 5
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)

# operators
_OPERATORS_BASE_ANCHORS = {
    "and": TKOperator.AND, 
    "or": TKOperator.OR, 
    "not": TKOperator.NOT,
    ",": TKOperator.AND,
    ":": TKOperator.AND,      # elaboration: co-asserted
    "so": TKOperator.IMPLY,   # result: "A so B" => A IMPLY B
    "but": TKOperator.NOTIMPLY
    }
_OPERATORS_SIMILARITY_THRESHOLD: float = 0.7 

# subordinates
_SUBORDINATE_TYPE_BASE_ANCHORS = {
    "because": TKClauseType.CAUSAL, 
    "if": TKClauseType.HYPOTETIC, 
    "from": TKClauseType.LOCATIVE, 
    "in": TKClauseType.LOCATIVE, 
    "when": TKClauseType.TEMPORAL,
    "that": TKClauseType.CCOMP,
    "to": TKClauseType.FINAL,
    }
_SUBORDINATE_TYPE_SIMILARITY_THRESHOLD: float = 0.6

# ollama
_OLLAMA_MODEL1 = 'llama3:8b' # general purpose 8b
_OLLAMA_MODEL2 = 'gemma2:9b' # general purpose 3.8b
_OLLAMA_TRANS1 = 'aya:8b' # translation 8b
_OLLAMA_TRANS2 = 'translategemma:4b' # translation 4b
_PRE_SIMILARITY_THRESHOLD = 0.8
_MIN_SIMILARITY = 0.9

# pronouns
_TALKER_ID = 1
_LISTENER_ID = 2
_PRONOUNS_BASE_ANCHORS = {
    # 1st person singular + possessives/reflexive -> talker
    "i": _TALKER_ID,
    "me": _TALKER_ID,
    "my": _TALKER_ID,
    "mine": _TALKER_ID,
    "myself": _TALKER_ID,
    # 2nd person + possessives/reflexives -> listener
    "you": _LISTENER_ID,
    "your": _LISTENER_ID,
    "yours": _LISTENER_ID,
    "yourself": _LISTENER_ID,
    "yourselves": _LISTENER_ID,
}
# NB: 1st-person plural (we/us/our/ours/ourselves) intentionally NOT mapped -- would collapse
# "we" to the single talker. 3rd-person (he/she/it/they) excluded -- handled by anaphora.

# subordinate subject resolution
# relative pronouns: subject (or object) of a relative clause refers back to the modified noun
_RELATIVE_PRONOUNS = {"who", "whom", "which", "that", "whose"}
# third-person personal pronouns eligible for anaphora resolution to a matrix antecedent
_ANAPHORIC_PRONOUNS = {"he", "she", "it", "they", "him", "her", "them"}
# entity types that can act as an antecedent (lexical, not meta/pronoun/statement)
_ANTECEDENT_TYPES = ("name", "dictionary", "place")
# verbs that keep subject control even with an object present ("I promised her to go" -> I go)
_SUBJECT_CONTROL_VERBS = {"promise", "vow", "swear", "pledge", "guarantee", "threaten"}

# properties
_PROP_BASE_ADVMOD_ANCHORS = {
    "not": -1,
    "slightly": 0.3,
    "passably": 0.5,
    "very": 1.5,
    "greatly": 2
}
_PROP_SIMILARITY_THRESHOLD = 0.85

# markers
_MARKER_SIMILARITY_THRESHOLD = 0.85
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

# propositional-attitude verbs (ccomp / THAT): embedding verb lemma -> (attitude class,
# world-truth confidence of the complement X in [0,1]). confidence is a tunable default for the
# semantic-calculation layer, not final fuzzy math. unknown verbs fall back to neutral doxastic.
_ATTITUDE_ANCHORS = {
    # factive: complement presupposed true
    "know": ("factive", 1.0), "realize": ("factive", 1.0), "regret": ("factive", 1.0),
    "remember": ("factive", 0.9), "notice": ("factive", 0.95), "see": ("factive", 0.9),
    # doxastic: belief held at confidence < 1
    "believe": ("doxastic", 0.7), "think": ("doxastic", 0.6), "assume": ("doxastic", 0.6),
    "suppose": ("doxastic", 0.55), "suspect": ("doxastic", 0.5), "expect": ("doxastic", 0.6),
    "guess": ("doxastic", 0.4), "doubt": ("doxastic", 0.2),
    # desiderative: irrealis goal (X not asserted as true)
    "want": ("desiderative", 0.0), "hope": ("desiderative", 0.0), "wish": ("desiderative", 0.0),
    # reportative: attributed to a source, truth uncommitted
    "say": ("reportative", 0.5), "claim": ("reportative", 0.4), "tell": ("reportative", 0.5),
    "report": ("reportative", 0.6), "argue": ("reportative", 0.4),
}
_ATTITUDE_DEFAULT = ("doxastic", 0.5)

# spacetime — TIME axis
# explicit temporal anchors -> absolute position on the time axis, in abstract "days" from now
# (deictic origin: utterance now = 0). past < 0, future > 0.
_TEMPORAL_ANCHORS = {
    "now": 0.0, "today": 0.0, "tonight": 0.0,
    "yesterday": -1.0, "tomorrow": 1.0,
}
# discourse/sequence advmods -> relative advance of the time cursor (sub-day steps), used when
# no explicit anchor is present, to keep clause ordering visible after normalization
_SEQUENCE_ANCHORS = {
    "then": 0.1, "after": 0.1, "afterward": 0.1, "afterwards": 0.1, "later": 0.1,
    "next": 0.1, "subsequently": 0.1, "finally": 0.2,
    "before": -0.1, "previously": -0.1, "earlier": -0.1,
    "meanwhile": 0.0, "simultaneously": 0.0,
}
# coarse tense baseline on the time axis (in abstract days), used as the weakest fallback when a
# clause has no explicit temporal anchor or sequence cue. weaker than the day-level anchors.
_TENSE_ANCHORS = {"past": -0.5, "pres": 0.0, "fut": 0.5}

# spacetime — SPACE axis
# locative case markers -> spatial relation. for now only used to detect that a reference is a
# place (so the clause is located there); the relation value (contain/dest/origin/near/far) is
# kept for the later velocity/displacement pass.
_SPATIAL_RELATION_ANCHORS = {
    "in": "contain", "at": "contain", "on": "contain", "inside": "contain", "within": "contain",
    "to": "dest", "into": "dest", "toward": "dest", "towards": "dest", "onto": "dest",
    "from": "origin", "out": "origin",
    "near": "near", "by": "near", "beside": "near", "close": "near",
    "far": "far", "behind": "far", "beyond": "far", "over": "far", "under": "far",
}
# define constants
from lib.core.tk import TKClauseType, TKOperator

# errors
_ERRORS_UNABLE_TO_PROCESS: str = "Unable to process the sentence"

# spacy
_SPACY_MAX_SIMILAR_RESULTS: int = 5
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)

# WSD semantic fallback: minimum cosine similarity a most_similar candidate must clear before its
# lemma is accepted as a substitute sense for an out-of-dictionary token. guards against the
# garbage-in -> confident-out failure where an OOV/gibberish token (no real vector, or a far-away
# nearest neighbour) was force-matched to an unrelated dictionary sense (e.g. "blicket" -> leadership).
# tunable; ~0.5 keeps genuine near-synonyms while rejecting noise.
_WSD_FALLBACK_MIN_SIMILARITY: float = 0.5

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

# clause-level negation markers (lemmas). "not" (verbal/copular, incl. do-support & contractions
# expanded upstream), "no" (determiner: "no money"/"no ability"), "never" (temporal negation),
# plus "n't" defensively in case a contraction survives expansion. detected on any role's
# properties and surfaced as the DISCRETE TKZipContent.negated flag (geometry alone loses it).
_NEGATION_MARKERS = {"not", "no", "never", "n't", "nor", "neither"}
# negative quantifier subjects: "nobody runs" -> generic person/thing + negated clause.
# best-effort (Phase-0): the subject is left as the quantifier token; the clause is flagged negated.
_NEGATIVE_QUANTIFIERS = {"nobody", "no one", "no-one", "noone", "nothing", "none"}

# quantifier anchor sets, read off the SUBJECT's determiner lemma. closed-class function words ->
# EXACT match only (no fuzzy: "all" must never fuzzy-match "tall"). a bare/no determiner -> GENERIC.
# NB "no"/"none"/"neither" are ALSO in _NEGATION_MARKERS; as a subject determiner they are
# RECLASSIFIED to the NEGATIVE *quantifier* (so they do not also trip the predicate `negated` flag).
_QUANTIFIER_UNIVERSAL = {"all", "every", "each"}
_QUANTIFIER_EXISTENTIAL = {"a", "an", "some", "any", "several"}
_QUANTIFIER_NEGATIVE = {"no", "none", "neither"}
_QUANTIFIER_DEFINITE = {"the", "this", "that", "these", "those"}

# wh-words (interrogative pronouns/adverbs/determiners) -> the GAP ROLE = the variable X a wh-question
# asks tokeniko to solve for. EXACT only (closed-class function words; the parser also confirms the
# token via PronType=Int). who/whom/which/whose -> SUBJECT, what -> PREDICATE (copular complement),
# where -> LOCATION, when -> TIME, how -> MANNER, why -> CAUSE.
_WH_SUBJECT = {"who", "whom", "which", "whose"}
_WH_PREDICATE = {"what"}
_WH_LOCATION = {"where"}
_WH_TIME = {"when"}
_WH_MANNER = {"how"}
_WH_CAUSE = {"why"}

# comparison predicates: AFFIRMATIVE forms assert sameness/equality between subject and the indirect
# operand; their ANTONYMS (different/unlike/...) assert non-equality and are flagged negated via the
# antonym primitive (Decision 2). the affirmative anchors below seed the antonym column read.
_COMPARISON_AFFIRMATIVE = {"equal", "same", "alike", "identical", "similar"}

# reflexive pronouns: an identity-comparison operand that is one of these corefers with the subject
# (a thing is equal to itself) -> the clause is reflexive (a=a / a≠a, hardwired-logic pinned).
_REFLEXIVE_PRONOUNS = {"itself", "himself", "herself", "themselves", "themself", "oneself"}

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

# matrix verbs that, with two clausal operands, express logical implication ("X implies/entails Y"):
# the two clauses combine under IMPLY(antecedent, consequent) instead of an AND of THAT-complements.
_IMPLICATION_VERBS = {"imply", "entail"}

# mereological (part-whole) cue lemmas, matched against the WSD synset LEMMA (the prefix of the
# synset key, e.g. "part.n.01" -> "part"). two complementary patterns (see the evaluator's STEP-0
# recon): keep these TIGHT — the evaluator only fires the part_of branch when the pattern is clearly
# a part-whole claim, else it falls through to definition grounding.
#
# (1) the "X is (a) part of Y" copular pattern: the predicate noun is a part-noun and the WHOLE Y is
#     its nmod modifier ("of Y"). part = the SUBJECT sense, whole = the predicate's nmod sense.
_PART_OF_PREDICATES = {"part", "portion", "piece", "component", "constituent", "member", "element"}
# (2) the "Y has/contains X" transitive pattern: the subject is the WHOLE and the direct object is the
#     PART. matched against the resolved synset lemma (WSD often re-lemmatises: contain->incorporate,
#     comprise->constitute/comprise, include->include, possess->possess, have->have).
_HAS_PART_VERBS = {"have", "contain", "include", "comprise", "possess",
                   "incorporate", "constitute", "encompass"}

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

# time-unit nouns -> length in abstract days. a quantified phrase whose object is one of these
# ("in 11 hours", "for 3 days") is temporal, not spatial, regardless of the (shared) preposition.
_TIME_UNITS = {
    "second": 1 / 86400, "minute": 1 / 1440, "hour": 1 / 24, "day": 1.0,
    "week": 7.0, "month": 30.0, "year": 365.0,
}
# how the preposition places a temporal quantity: future/past offset from now, or a duration
_TEMPORAL_PREP_FUTURE = {"in", "after", "within"}
_TEMPORAL_PREP_PAST = {"before", "ago"}
_TEMPORAL_PREP_DURATION = {"for", "during"}

# NER entity labels treated as resolvable real places (looked up in the places knowledge base)
_GEO_NER_LABELS = {"GPE", "LOC", "FAC"}

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
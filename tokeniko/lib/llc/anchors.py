# ------------------------------------------------------------------------------------------------
# ANCHOR RESOLVER  --  il livello "lingua -> logica"
# ------------------------------------------------------------------------------------------------
# PRINCIPIO (non negoziabile): MAI affidarsi a dizionari fissi che mancano silenziosamente gli input
# fuori-lista. Ogni risoluzione "parola di superficie -> categoria" mappa QUALSIASI input alla ancora
# PIU' VICINA di un piccolo insieme di ancore via similarita' semantica:
#   1. exact-hit  -> strada veloce (lemma nella tabella).
#   2. nearest-anchor fallback -> sopra un floor di sanita' (cosine vs le ancore in cache); sotto il
#      floor -> default. Cosi' (a) la logica resta in pochi bucket gestibili e (b) non si perde MAI un
#      input ("hugely"->greatly, "therefore"->IMPLY, "reckon"->doxastic).
#
# Le categorie sensibili alla polarita' sono ANTONYM-GUARDED: il fuzzy catch non puo' MAI ribaltare su
# un opposto ("or" non deve MAI risolversi ad AND per deriva fuzzy; gli avversativi risolvono ad AND
# DELIBERATAMENTE, col flag `contrast` a parte — M1 2026-07-16). EXACT e' riservato alle eccezioni vere (deixis di
# riferimento, etichette del parser) -- comunque registrate qui cosi' sono "flippabili" piu' avanti.
#
# Anchor-vector caching: i vettori delle ancore di ogni categoria SEMANTIC sono calcolati UNA volta
# (lazy, alla prima richiesta) e tenuti in cache; la risoluzione per-chiamata e' poi pura numpy
# in-memoria (cosine vs ~5-20 vettori). NESSUN hit DB per chiamata.
# ------------------------------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import numpy as np

from lib.core.tk import TKClauseType, TKOperator, TKQuantifier, TKWhRole
from lib.core.models import TKDictionaryDoc
from lib.llc.utils import utils_antonyms
from lib.llc.constants import (
    _OPERATORS_BASE_ANCHORS,
    _CONTRAST_MARKERS,
    _CAUSE_CC_MARKERS,
    _SUBORDINATE_TYPE_BASE_ANCHORS,
    _PROP_BASE_ADVMOD_ANCHORS,
    _ATTITUDE_ANCHORS,
    _ATTITUDE_DEFAULT,
    _IMPLICATION_VERBS,
    _SPATIAL_RELATION_ANCHORS,
    _SEQUENCE_ANCHORS,
    _COMPARISON_AFFIRMATIVE,
    _PART_OF_PREDICATES,
    _HAS_PART_VERBS,
    _QUANTIFIER_UNIVERSAL,
    _QUANTIFIER_EXISTENTIAL,
    _QUANTIFIER_INDEFINITE,
    _QUANTIFIER_NEGATIVE,
    _QUANTIFIER_DEFINITE,
    _WH_SUBJECT,
    _WH_PREDICATE,
    _WH_LOCATION,
    _WH_TIME,
    _WH_MANNER,
    _WH_CAUSE,
    _PRONOUNS_BASE_ANCHORS,
    _NEGATION_MARKERS,
    _NEGATIVE_QUANTIFIERS,
    _REFLEXIVE_PRONOUNS,
    _TEMPORAL_ANCHORS,
    _TENSE_ANCHORS,
    _TIME_UNITS,
    _TEMPORAL_PREP_FUTURE,
    _TEMPORAL_PREP_PAST,
    _TEMPORAL_PREP_DURATION,
    _RELATIVE_PRONOUNS,
    _ANAPHORIC_PRONOUNS,
    _SUBJECT_CONTROL_VERBS,
    _ANTECEDENT_TYPES,
    _GEO_NER_LABELS,
)

# ------------------------------------------------------------------------------------------------
# spaCy nlp -- accesso LAZY per evitare cicli di import.
# Il pipeline modules (parser/c_state) caricano en_core_web_lg al-momento-dell'import; importiamo
# `nlp` dal compiler state DENTRO le funzioni, non al top-level.
# ------------------------------------------------------------------------------------------------
def _get_nlp():
    from lib.llc.compiler.c_state import nlp
    return nlp


# ------------------------------------------------------------------------------------------------
# tuning floors / margini  (costanti di modulo, da tarare)
# ------------------------------------------------------------------------------------------------
_OPERATOR_FLOOR: float = 0.7
_OPERATOR_MARGIN: float = 0.05          # il top deve battere il runner-up di questo margine
_SUBORDINATE_FLOOR: float = 0.6
_INTENSIFIER_FLOOR: float = 0.55        # raw cosine sui 2925-dim dict vectors
_ATTITUDE_FLOOR: float = 0.45
_IMPLICATION_FLOOR: float = 0.7         # solo sinonimi confidenti di implicazione contano
_SPATIAL_FLOOR: float = 0.6
_SEQUENCE_FLOOR: float = 0.7         # >0.65: additive connectives (moreover/however) must NOT read as a temporal advance
_COMPARISON_FLOOR: float = 0.55         # semantic extension del polarity helper
_PARTOF_CUE_FLOOR: float = 0.6          # content cue (part-noun / meronymic verb) nearest-anchor floor


# ------------------------------------------------------------------------------------------------
# strategia / backend
# ------------------------------------------------------------------------------------------------
class Strategy(str, Enum):
    EXACT = "EXACT"
    SEMANTIC = "SEMANTIC"


class Backend(str, Enum):
    SPACY = "SPACY"     # function words: vettori nlp.vocab / token.similarity
    DICT = "DICT"       # content words: vettori 2925-dim di TKDictionaryDoc
    NONE = "NONE"       # categorie EXACT


# ------------------------------------------------------------------------------------------------
# Category config
# ------------------------------------------------------------------------------------------------
@dataclass
class Category:
    name: str
    table: Any                                  # dict lemma->value, oppure set per le membership
    strategy: Strategy
    backend: Backend = Backend.NONE
    polarity_guard: bool = False
    floor: float = 0.0
    default: Any = None
    margin: float = 0.0                          # margine top vs runner-up (operatori)
    # per le SET-categories (membership) -> True
    is_set: bool = False


# ------------------------------------------------------------------------------------------------
# REGISTRY
# ------------------------------------------------------------------------------------------------

# espansione delle ancore operatore polarity-bearing: assicura che i connettivi a polarita' nota
# siano nella tabella ESPLICITAMENTE (l'invariante e' che il fuzzy non possa mai contraddire il testo)
_OPERATORS_ANCHORS_EXPANDED = {
    **_OPERATORS_BASE_ANCHORS,
    # avversativi / contrasto -> AND + flag `contrast` (M1 2026-07-16): il contenuto asserito e' la
    # congiunzione (X∧Y); la sfumatura avversativa NON e' asserita e viaggia sul flag di clausola
    # (categoria "contrast" qui sotto), mai nell'albero degli operatori — il vecchio NOTIMPLY
    # piegava a 0 ogni "X but Y" vero.
    "however": TKOperator.AND,
    "yet": TKOperator.AND,
    "nevertheless": TKOperator.AND,
    "nonetheless": TKOperator.AND,
    "though": TKOperator.AND,
    "although": TKOperator.AND,
    "whereas": TKOperator.AND,
    # conclusivi / risultativi -> AND + flag `cause`="result" (M2 2026-07-16): "A therefore B" e'
    # FATTIVO — asserisce A, B, e il legame; il legame viaggia sul flag di clausola (categoria
    # "cause" qui sotto), mai nell'albero degli operatori.
    "therefore": TKOperator.AND,
    "thus": TKOperator.AND,
    "hence": TKOperator.AND,
    "consequently": TKOperator.AND,
    "accordingly": TKOperator.AND,
    # additivi -> AND
    "also": TKOperator.AND,
    "moreover": TKOperator.AND,
    "additionally": TKOperator.AND,
    "furthermore": TKOperator.AND,
    "besides": TKOperator.AND,
    "plus": TKOperator.AND,
}

# espansione subordinati: i marcatori a DIREZIONE/CONTRASTO noti vanno in tabella ESPLICITAMENTE
# (exact-hit), cosi' il fuzzy non li mis-bucketizza in un tipo vicino-ma-sbagliato. I CONCESSIVI non
# hanno un tipo proprio (manca CONCESSIVE in TKClauseType) -> OTHER e' la scelta SICURA: meglio una
# congiunzione neutra che una FALSA implicazione causale ("although it rains" non e' "because it
# rains"). Da rivedere se/quando si introduce un tipo concessivo dedicato (-> NOT IMPLY/contrasto).
_SUBORDINATE_TYPE_ANCHORS_EXPANDED = {
    **_SUBORDINATE_TYPE_BASE_ANCHORS,
    "although": TKClauseType.OTHER,
    "though": TKClauseType.OTHER,
    "whereas": TKClauseType.OTHER,
    "albeit": TKClauseType.OTHER,
    # conclusivi in testa alla clausola RISULTATO (M2 2026-07-16): stanza li tagga advmod, il
    # gate advmod-marker li accetta solo se ancorati ≠ OTHER — CONSECUTIVE e' lo specchio di
    # CAUSAL (fattivo: AND + cause="result"; «I think, therefore I exist» compila col legame).
    "so": TKClauseType.CONSECUTIVE,
    "therefore": TKClauseType.CONSECUTIVE,
    "thus": TKClauseType.CONSECUTIVE,
    "hence": TKClauseType.CONSECUTIVE,
    "consequently": TKClauseType.CONSECUTIVE,
}

_REGISTRY: dict[str, Category] = {
    # -------------------------------------------------------------------------------------- SEMANTIC
    "operators": Category(
        name="operators", table=_OPERATORS_ANCHORS_EXPANDED, strategy=Strategy.SEMANTIC,
        backend=Backend.SPACY, polarity_guard=True, floor=_OPERATOR_FLOOR,
        default=TKOperator.AND, margin=_OPERATOR_MARGIN,
    ),
    # avversativi -> flag `contrast` di clausola (M1 2026-07-16): set-category SEMANTIC cosi' un
    # connettivo contrastivo mai visto ("albeit") viene comunque catturato per vicinanza; la
    # tabella e' a POLARITA' MISTA (additivi/conclusivi = False espliciti) + margin guard, cosi'
    # "and"/"also" non possono finirci per deriva fuzzy (le function word sono tutte vicine).
    "contrast": Category(
        name="contrast", table=_CONTRAST_MARKERS, strategy=Strategy.SEMANTIC,
        backend=Backend.SPACY, polarity_guard=True, floor=_OPERATOR_FLOOR,
        default=False, is_set=True, margin=_OPERATOR_MARGIN,
    ),
    # conclusivi -> flag `cause`="result" di clausola (M2 2026-07-16): stessa dottrina di contrast
    # (tabella a polarita' mista + margin guard); il lato "reason" (because/since) arriva dal
    # percorso subordinato (mark), non da qui.
    "cause": Category(
        name="cause", table=_CAUSE_CC_MARKERS, strategy=Strategy.SEMANTIC,
        backend=Backend.SPACY, polarity_guard=True, floor=_OPERATOR_FLOOR,
        default=None, margin=_OPERATOR_MARGIN,
    ),
    "subordinate_types": Category(
        name="subordinate_types", table=_SUBORDINATE_TYPE_ANCHORS_EXPANDED, strategy=Strategy.SEMANTIC,
        backend=Backend.SPACY, polarity_guard=False, floor=_SUBORDINATE_FLOOR,
        default=TKClauseType.OTHER,
    ),
    "intensifiers": Category(
        # "not" escluso: la negazione -1 e' gestita dai marker di negazione, non qui
        name="intensifiers",
        table={k: v for k, v in _PROP_BASE_ADVMOD_ANCHORS.items() if k != "not"},
        strategy=Strategy.SEMANTIC, backend=Backend.DICT, polarity_guard=False,
        floor=_INTENSIFIER_FLOOR, default=1.0,
    ),
    "attitudes": Category(
        name="attitudes", table=_ATTITUDE_ANCHORS, strategy=Strategy.SEMANTIC,
        backend=Backend.DICT, polarity_guard=False, floor=_ATTITUDE_FLOOR,
        default=_ATTITUDE_DEFAULT,
    ),
    "implication_verbs": Category(
        name="implication_verbs", table={w: True for w in _IMPLICATION_VERBS}, strategy=Strategy.SEMANTIC,
        backend=Backend.DICT, polarity_guard=False, floor=_IMPLICATION_FLOOR,
        default=False, is_set=True,
    ),
    "spatial_relations": Category(
        name="spatial_relations", table=_SPATIAL_RELATION_ANCHORS, strategy=Strategy.SEMANTIC,
        backend=Backend.SPACY, polarity_guard=False, floor=_SPATIAL_FLOOR, default=None,
    ),
    "sequence": Category(
        name="sequence", table=_SEQUENCE_ANCHORS, strategy=Strategy.SEMANTIC,
        backend=Backend.SPACY, polarity_guard=False, floor=_SEQUENCE_FLOOR, default=0.0,
    ),
    # comparison e' gestita da anchor_comparison_polarity (antonym-aware); registrata per simmetria
    "comparison": Category(
        name="comparison", table=_COMPARISON_AFFIRMATIVE, strategy=Strategy.SEMANTIC,
        backend=Backend.DICT, polarity_guard=True, floor=_COMPARISON_FLOOR,
        default="none", is_set=True,
    ),
    # part-whole cues — CONTENT words (open class) -> map ANY input to the nearest of a small anchor
    # set (seeds = the literal sets), exact-hit OR nearest >= floor. NO polarity guard (not
    # polarity-sensitive). Replaces the old fixed `in`-membership in e_statement.
    "part_of_predicate": Category(
        name="part_of_predicate", table={w: True for w in _PART_OF_PREDICATES}, strategy=Strategy.SEMANTIC,
        backend=Backend.DICT, polarity_guard=False, floor=_PARTOF_CUE_FLOOR,
        default=False, is_set=True,
    ),
    "has_part_verb": Category(
        name="has_part_verb", table={w: True for w in _HAS_PART_VERBS}, strategy=Strategy.SEMANTIC,
        backend=Backend.DICT, polarity_guard=False, floor=_PARTOF_CUE_FLOOR,
        default=False, is_set=True,
    ),

    # ----------------------------------------------------------------------------------------- EXACT
    # eccezioni vere: deixis di riferimento, etichette parser. Registrate cosi' sono flippabili.
    "pronoun_deixis": Category("pronoun_deixis", _PRONOUNS_BASE_ANCHORS, Strategy.EXACT, default=None),
    "negation": Category("negation", _NEGATION_MARKERS, Strategy.EXACT, default=False, is_set=True),
    "negative_quantifiers": Category("negative_quantifiers", _NEGATIVE_QUANTIFIERS, Strategy.EXACT, default=False, is_set=True),
    "reflexive_pronouns": Category("reflexive_pronouns", _REFLEXIVE_PRONOUNS, Strategy.EXACT, default=False, is_set=True),
    "temporal_deictic": Category("temporal_deictic", _TEMPORAL_ANCHORS, Strategy.EXACT, default=None),
    "tense": Category("tense", _TENSE_ANCHORS, Strategy.EXACT, default=0.0),
    "time_units": Category("time_units", _TIME_UNITS, Strategy.EXACT, default=None),
    "temporal_prep_future": Category("temporal_prep_future", _TEMPORAL_PREP_FUTURE, Strategy.EXACT, default=False, is_set=True),
    "temporal_prep_past": Category("temporal_prep_past", _TEMPORAL_PREP_PAST, Strategy.EXACT, default=False, is_set=True),
    "temporal_prep_duration": Category("temporal_prep_duration", _TEMPORAL_PREP_DURATION, Strategy.EXACT, default=False, is_set=True),
    "relative_pronouns": Category("relative_pronouns", _RELATIVE_PRONOUNS, Strategy.EXACT, default=False, is_set=True),
    "anaphoric_pronouns": Category("anaphoric_pronouns", _ANAPHORIC_PRONOUNS, Strategy.EXACT, default=False, is_set=True),
    "subject_control_verbs": Category("subject_control_verbs", _SUBJECT_CONTROL_VERBS, Strategy.EXACT, default=False, is_set=True),
    "antecedent_types": Category("antecedent_types", set(_ANTECEDENT_TYPES), Strategy.EXACT, default=False, is_set=True),
    "geo_ner_labels": Category("geo_ner_labels", _GEO_NER_LABELS, Strategy.EXACT, default=False, is_set=True),
}


# ------------------------------------------------------------------------------------------------
# Anchor-vector cache
# struttura: category -> { "words": [...], "values": [...], "vecs": np.ndarray (n, d) normalizzati }
# ------------------------------------------------------------------------------------------------
_ANCHOR_CACHE: dict[str, dict[str, Any]] = {}


def _l2norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


# vettore 2925-dim del dizionario per una parola (DICT backend). None se la parola non c'e' o e' nulla.
def _dict_vector(word: str) -> Optional[np.ndarray]:
    word = (word or "").strip().lower()
    if not word:
        return None
    doc = TKDictionaryDoc.find_one(TKDictionaryDoc.word == word).run()
    if doc is None or not doc.vector:
        return None
    v = np.asarray(doc.vector, dtype=float)
    # un doc puo' esistere ma con vettore tutto-zero (parola non ancorata ai base words): inutile
    # per il cosine -> trattalo come "nessun vettore" (default), non come un match spurio.
    if float(np.linalg.norm(v)) == 0.0:
        return None
    return v


# vettore spaCy nlp.vocab per una parola (SPACY backend). None se senza vettore.
def _spacy_vector(word: str) -> Optional[np.ndarray]:
    word = (word or "").strip().lower()
    if not word:
        return None
    lex = _get_nlp().vocab[word]
    if not lex.has_vector:
        return None
    return np.asarray(lex.vector, dtype=float)


# costruisce (lazy) la cache dei vettori-ancora per una categoria SEMANTIC.
def _build_cache(cat: Category) -> dict[str, Any]:
    cached = _ANCHOR_CACHE.get(cat.name)
    if cached is not None:
        return cached

    words: list[str] = []
    values: list[Any] = []
    vecs: list[np.ndarray] = []

    fetch = _dict_vector if cat.backend == Backend.DICT else _spacy_vector

    # iterazione su dict (lemma->value) o su set (lemma is value)
    if isinstance(cat.table, dict):
        items = cat.table.items()
    else:
        items = ((w, True) for w in cat.table)

    for word, value in items:
        v = fetch(word)
        if v is None:
            continue
        words.append(word)
        values.append(value)
        vecs.append(_l2norm(v))

    matrix = np.vstack(vecs) if vecs else np.zeros((0, 0))
    cached = {"words": words, "values": values, "vecs": matrix}
    _ANCHOR_CACHE[cat.name] = cached
    return cached


# cosine di un input (gia' grezzo) vs tutti i vettori-ancora in cache -> array di similarita'.
def _cosines(vec: np.ndarray, cache: dict[str, Any]) -> np.ndarray:
    matrix: np.ndarray = cache["vecs"]
    if matrix.size == 0:
        return np.zeros((0,))
    q = _l2norm(np.asarray(vec, dtype=float))
    return matrix @ q


# ------------------------------------------------------------------------------------------------
# Polarity guard (operatori SPACY)
# il top-anchor non deve essere un opposto di un competitor a punteggio simile: richiediamo che il
# vincitore batta il runner-up (di valore-operatore DIVERSO) di un margine; altrimenti -> default.
# Le ancore polarity-bearing sono comunque nella tabella (exact-hit), quindi questo guard interviene
# SOLO sul fuzzy fallback.
# ------------------------------------------------------------------------------------------------
def _operator_guarded_pick(sims: np.ndarray, cache: dict[str, Any], cat: Category) -> Any:
    if sims.size == 0:
        return cat.default
    order = np.argsort(sims)[::-1]
    top = order[0]
    top_val = cache["values"][top]
    top_sim = float(sims[top])
    if top_sim < cat.floor:
        return cat.default
    # runner-up con valore-operatore DIVERSO dal top
    for idx in order[1:]:
        if cache["values"][idx] != top_val:
            if top_sim - float(sims[idx]) < cat.margin:
                # troppo vicino a un operatore concorrente -> non confidente -> default
                return cat.default
            break
    return top_val


# ------------------------------------------------------------------------------------------------
# Polarity guard (DICT, antonym-based)
# rifiuta un match che e' un antonimo di un'ancora a punteggio piu' alto (di valore diverso).
# ------------------------------------------------------------------------------------------------
def _dict_antonym_guarded_pick(sims: np.ndarray, cache: dict[str, Any], cat: Category) -> Any:
    if sims.size == 0:
        return cat.default
    order = np.argsort(sims)[::-1]
    top = order[0]
    if float(sims[top]) < cat.floor:
        return cat.default
    top_word = cache["words"][top]
    top_anto = utils_antonyms(top_word)
    # se la parola-top e' antonimo di un'ancora con punteggio comparabile e valore diverso -> reject
    for idx in order:
        if idx == top:
            continue
        if cache["values"][idx] == cache["values"][top]:
            continue
        if cache["words"][idx] in top_anto:
            return cat.default
    return cache["values"][top]


# ------------------------------------------------------------------------------------------------
# nearest pick (no guard)
# ------------------------------------------------------------------------------------------------
def _nearest_pick(sims: np.ndarray, cache: dict[str, Any], cat: Category) -> Any:
    if sims.size == 0:
        return cat.default
    top = int(np.argmax(sims))
    if float(sims[top]) < cat.floor:
        return cat.default
    return cache["values"][top]


def _pick(sims: np.ndarray, cache: dict[str, Any], cat: Category) -> Any:
    if cat.polarity_guard and cat.backend == Backend.SPACY:
        return _operator_guarded_pick(sims, cache, cat)
    if cat.polarity_guard and cat.backend == Backend.DICT:
        return _dict_antonym_guarded_pick(sims, cache, cat)
    return _nearest_pick(sims, cache, cat)


# ================================================================================================
# PUBLIC API
# ================================================================================================

# risolve un lemma a una categoria. EXACT -> table.get/membership. SEMANTIC -> exact-hit, poi
# nearest-anchor (cosine vs ancore in cache) >= floor, con polarity guard se richiesto, else default.
def anchor_resolve(lemma: str, category: str) -> Any:
    cat = _REGISTRY[category]
    key = (lemma or "").strip().lower()

    # EXACT: membership (set) o lookup (dict)
    if cat.strategy == Strategy.EXACT:
        if cat.is_set:
            return key in cat.table
        return cat.table.get(key, cat.default)

    # SEMANTIC
    # 1. strada veloce: exact-hit
    if isinstance(cat.table, dict):
        if key in cat.table:
            return cat.table[key]
    else:
        if key in cat.table:
            return True if cat.is_set else key

    # 2. nearest-anchor fallback
    cache = _build_cache(cat)
    fetch = _dict_vector if cat.backend == Backend.DICT else _spacy_vector
    vec = fetch(key)
    if vec is None:
        return cat.default
    sims = _cosines(vec, cache)
    return _pick(sims, cache, cat)


# risolve un VETTORE gia' in mano (es. advmod propVec 2925-dim) alla categoria. Confronta SOLO contro
# le ancore in cache (NESSUN $vectorSearch su Mongo). >= floor else default.
def anchor_resolve_vector(vec: np.ndarray, category: str) -> Any:
    cat = _REGISTRY[category]
    if cat.strategy != Strategy.SEMANTIC:
        raise ValueError(f"anchor_resolve_vector: category '{category}' is not SEMANTIC")
    cache = _build_cache(cat)
    v = np.asarray(vec, dtype=float)
    if v.size == 0 or (float(v.min()) == 0.0 and float(v.max()) == 0.0):
        return cat.default
    sims = _cosines(v, cache)
    return _pick(sims, cache, cat)


# membership per le set-categories (e per le exact-set in genere).
def anchor_is(lemma: str, category: str) -> bool:
    cat = _REGISTRY[category]
    key = (lemma or "").strip().lower()
    if cat.is_set:
        # EXACT-set: membership diretta; SEMANTIC-set: exact-hit OR nearest >= floor
        if key in cat.table:
            return True
        if cat.strategy == Strategy.SEMANTIC:
            return bool(anchor_resolve(key, category))
        return False
    # dict-categories: membership = chiave presente
    return key in cat.table


# ------------------------------------------------------------------------------------------------
# Quantifier (closed-class determiners -> TKQuantifier)
# EXACT only — quantifiers are closed-class function words; a fuzzy match would be unsafe ("all" must
# never collapse onto "tall"). a bare/no/unknown determiner -> GENERIC (the safe default).
# ------------------------------------------------------------------------------------------------
_QUANTIFIER_TABLE: dict[str, TKQuantifier] = {
    **{w: TKQuantifier.UNIVERSAL for w in _QUANTIFIER_UNIVERSAL},
    **{w: TKQuantifier.EXISTENTIAL for w in _QUANTIFIER_EXISTENTIAL},
    **{w: TKQuantifier.INDEFINITE for w in _QUANTIFIER_INDEFINITE},
    **{w: TKQuantifier.NEGATIVE for w in _QUANTIFIER_NEGATIVE},
    **{w: TKQuantifier.DEFINITE for w in _QUANTIFIER_DEFINITE},
}


def anchor_quantifier(lemma: str) -> TKQuantifier:
    key = (lemma or "").strip().lower()
    return _QUANTIFIER_TABLE.get(key, TKQuantifier.GENERIC)


# ------------------------------------------------------------------------------------------------
# Wh-word (closed-class interrogative -> the gap role = the variable X to solve for)
# EXACT only — wh-words are closed-class; the parser also gates on PronType=Int. a non-wh lemma -> None.
# ------------------------------------------------------------------------------------------------
_WH_TABLE: dict[str, TKWhRole] = {
    **{w: TKWhRole.SUBJECT for w in _WH_SUBJECT},
    **{w: TKWhRole.PREDICATE for w in _WH_PREDICATE},
    **{w: TKWhRole.LOCATION for w in _WH_LOCATION},
    **{w: TKWhRole.TIME for w in _WH_TIME},
    **{w: TKWhRole.MANNER for w in _WH_MANNER},
    **{w: TKWhRole.CAUSE for w in _WH_CAUSE},
}


def anchor_whType(lemma: str) -> Optional[TKWhRole]:
    key = (lemma or "").strip().lower()
    return _WH_TABLE.get(key)


# ------------------------------------------------------------------------------------------------
# Comparison polarity (antonym-aware)
# "affirmative" = stessa/uguaglianza (equal/same/...); "negative" = antonimo di un'ancora affermativa
# (different/unlike/...); "none" altrimenti. Riusa la logica antonym-aware (utils_antonyms), poi
# estende con un nearest semantico verso le ancore affermative / il loro pool antonimico.
# polarity_guard e' intrinseco: una parola non puo' essere insieme affermativa e negativa.
# ------------------------------------------------------------------------------------------------
_COMPARISON_NEGATIVE_CACHE: Optional[set[str]] = None


def _comparison_negative_words() -> set[str]:
    global _COMPARISON_NEGATIVE_CACHE
    if _COMPARISON_NEGATIVE_CACHE is None:
        negatives: set[str] = set()
        for anchor in _COMPARISON_AFFIRMATIVE:
            negatives |= utils_antonyms(anchor)
        _COMPARISON_NEGATIVE_CACHE = negatives - _COMPARISON_AFFIRMATIVE
    return _COMPARISON_NEGATIVE_CACHE


def anchor_comparison_polarity(lemma: str) -> str:
    key = (lemma or "").strip().lower()
    if not key:
        return "none"

    # 1. exact affirmative
    if key in _COMPARISON_AFFIRMATIVE:
        return "affirmative"

    # 2. exact negative (antonimo di un'ancora affermativa)
    if key in _comparison_negative_words():
        return "negative"

    # 3. simmetrico: l'ancora affermativa appare nella colonna antonimica della parola
    word_antonyms = utils_antonyms(key)
    if any(a in word_antonyms for a in _COMPARISON_AFFIRMATIVE):
        return "negative"

    # 4. estensione semantica: nearest verso le ancore affermative vs il pool negativo.
    cat = _REGISTRY["comparison"]
    vec = _dict_vector(key)
    if vec is None:
        return "none"

    aff_cache = _build_cache(cat)  # ancore = _COMPARISON_AFFIRMATIVE
    aff_sims = _cosines(vec, aff_cache)
    aff_best = float(aff_sims.max()) if aff_sims.size else -1.0

    # pool negativo: confronto vs i vettori dei negative words (cache separata, lazy)
    neg_cache = _ANCHOR_CACHE.get("__comparison_negative__")
    if neg_cache is None:
        words, vecs = [], []
        for w in _comparison_negative_words():
            v = _dict_vector(w)
            if v is not None:
                words.append(w)
                vecs.append(_l2norm(v))
        neg_cache = {"words": words, "values": ["negative"] * len(words),
                     "vecs": np.vstack(vecs) if vecs else np.zeros((0, 0))}
        _ANCHOR_CACHE["__comparison_negative__"] = neg_cache
    neg_sims = _cosines(vec, neg_cache)
    neg_best = float(neg_sims.max()) if neg_sims.size else -1.0

    best = max(aff_best, neg_best)
    if best < cat.floor:
        return "none"
    return "affirmative" if aff_best >= neg_best else "negative"


# diagnostica: forza il caricamento delle cache (utile per i probe / per scaldare il processo).
def anchor_warm(categories: Optional[list[str]] = None) -> dict[str, int]:
    out: dict[str, int] = {}
    names = categories or [n for n, c in _REGISTRY.items() if c.strategy == Strategy.SEMANTIC]
    for n in names:
        cache = _build_cache(_REGISTRY[n])
        out[n] = len(cache["words"])
    return out

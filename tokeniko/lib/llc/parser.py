# ------------------------------------------------------------------------------------------------
# PARSER V2: transform a token list into a list of TKStatements (using spacy for the first ingestion)
# ------------------------------------------------------------------------------------------------

from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Span, Token
import spacy_stanza
import numpy as np
from lib.core.tk import EntityPayload, TKAux, TKClause, TKFullProperty, TKMarker, TKFullEntity, TKDictionary, TKGeneric, TKMetaEntity, TKName, TKNumber, TKOperator, TKPlace, TKPronoun, TKStatement, TKStatements
from lib.core.models import TKDictionaryDoc, TKPlaceDoc
from lib.core.mappers import TKPosMapper
from lib.core.tkllc import TKLLC
from lib.llc.constants import _SPACY_MODEL, _SPACY_MAX_SIMILAR_RESULTS, _WSD_FALLBACK_MIN_SIMILARITY, _OPERATORS_BASE_ANCHORS, _OPERATORS_SIMILARITY_THRESHOLD, _GEO_NER_LABELS
from lib.core.utilities import util_expandContractions, util_removeSpace
from functools import cmp_to_key
import textacy
from word2number import w2n
from lib.core.memory import MEMContext, MEMStakeholder
from lib.llc.anchors import anchor_resolve, anchor_whType

# --- INIZIO PATCH PYTORCH ---
import torch

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# --- FINE PATCH PYTORCH ---

# load spacy model
nlp_stanza = None
nlp = None

# global variables
_context: MEMContext = None
_ollamaClient: OllamaClient = None
_talker: MEMStakeholder = None
_tokeniko: MEMStakeholder = None

def parser_init():
    global nlp_stanza, nlp
    
    if nlp_stanza is None:
        nlp_stanza = spacy_stanza.load_pipeline(
            "en",
            device="mps",                       # silicon gpu acceleration (if available)
            download_method="reuse_resources"   # skip download if already present
        )
        
        # spacy standard
        nlp = spacy.load(_SPACY_MODEL)

# --------------------------------------------------------------
# utils
# --------------------------------------------------------------
# get operator corresponding to cc
def parser_ccToOperator(token: Token | str) -> TKOperator:
    lemma = token.lemma_.lower() if isinstance(token, Token) else token

    # unified anchor resolver: exact-hit -> nearest-anchor (polarity-guarded) -> default AND
    return anchor_resolve(lemma, "operators")

# --------------------------------------------------------------
# PARSING
# --------------------------------------------------------------
def parser_getRelatedEntity(token: Token, quotes: list[tuple[list[Token], list[Token], Span]] = [], isPredicate = False) -> TKFullEntity:
    
    entity: TKFullEntity = None

    # search operator, otherwise default
    opToken = next((tt for tt in list(token.subtree) if tt.dep_ == "cc" or tt.dep_ == "punct"), None)
    operator: TKOperator = parser_ccToOperator(opToken) if opToken else TKOperator.AND

    # decide if its a conj single word or a sentence
    if isPredicate:
        subtree = [t for t in token.subtree if t != opToken] # remove operator
        forcedSubject: Token = None
        for q in quotes: 
            if token.text in (c.text for c in list(q.content)): 
                forcedSubject = q.speaker[0] if len(q.speaker) > 0 else None
            continue
        sentence = parser_parseSentence(token, subtree, clause_type=TKClause.COORDINATE, subject=forcedSubject)
        entity = TKFullEntity(entity=sentence, dep=token.dep_, aux=None, marker=None, token=None, properties=[], conjuncts=[], op=operator) if sentence else None
    else:
        entity = parser_getFullEntity(token, quotes, operator)
    
    # no entity found
    return entity

# get properties
def parser_getProperties(tokens: list[Token]) -> list[TKFullProperty]:

    doc_properties: list[TKFullProperty] = []
    property: TKFullProperty

    for t in tokens:
        property = None
        if t.dep_ == "nummod" \
        or t.dep_ == "amod" \
        or t.dep_ == "nmod" \
        or t.dep_ == "advmod" \
        or t.dep_ == "compound" \
        or t.dep_ == "nmod:poss" \
        or t.dep_ == "det":
            property = parser_getFullProperty(t)

        if property: 
            doc_properties.append(property)

            # ----------------------------------------
            # coordinated entities (conjuncts)
            # ----------------------------------------   
            for c in [cc for cc in t.conjuncts if cc.head == t]:
                doc_properties.append(parser_getFullProperty(c))

    return doc_properties

# get full entity as property
def parser_getFullProperty(token: Token) -> TKFullProperty:
    # related tokens to the entity
    conjuncts = list(token.conjuncts)
    children = list(token.children)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_properties: list[TKFullProperty] = []

    # get single entity or statement
    tkMeaning = parser_getPropertyMeaning(token, pos)

    # get properties (for each token directly bound to the result)
    doc_properties = parser_getProperties(children)

    # primary entity (from token)
    primaryEntity: TKFullProperty = TKFullProperty(entity=tkMeaning, token=token.text, dep=token.dep_, properties=doc_properties)

    return primaryEntity

# parse a subordinate clause
def parser_parseSubordinate(token: Token, quotes: list[tuple[list[Token], list[Token], Span]] = []) -> TKFullEntity:

    # initialize variables
    childrenTokens = list(token.children)
    tkMarker: TKMarker = None
    result: TKFullEntity = None

    # get indirect marker 
    marker = next((s for s in childrenTokens if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(dep=marker.dep_, word=marker.lemma_, vector=marker.vector, parent_dep=token.dep_)

    # update marker
    if marker == None: 
        tkMarker = TKMarker(parent_dep=token.dep_)

    tokenSubtree = [t for t in token.subtree if t != marker]

    forcedSubject: Token = None
    for q in quotes: 
        if token.text in (c.text for c in list(q.content)): 
            forcedSubject = q.speaker[0] if len(q.speaker) > 0 else None
        continue

    tkStatement = parser_parseSentence(token, tokenSubtree, clause_type=TKClause.SUBORDINATE, subject=forcedSubject)
    if tkStatement: result = TKFullEntity(entity=tkStatement, token=None, dep=token.dep_, aux=None, marker=tkMarker, properties=[], conjuncts=[], op=TKOperator.AND)
    
    return result

# search for separate statements in the token list, and parse them recursively
def parser_isStatement(token: Token) -> bool:
    return token.dep_ in ["xcomp", "ccomp", "csubj", "advcl", "acl", "acl:relcl", "parataxis"]

# get from dictionary, names, number, pronouns, generic (fallback) meaning
# resolve a geo-NER proper noun (GPE/LOC/FAC) to a known place with coordinates, else None.
# NB: name lookup is not disambiguated by prominence, so homonyms resolve to whichever the
# places knowledge base returns first (e.g. "Paris" may be Paris, Ontario).
def parser_getPlace(token: Token) -> TKPlace | None:
    if token.ent_type_ not in _GEO_NER_LABELS:
        return None
    # place names are stored lowercased in the knowledge base
    doc = TKPlaceDoc.find_one({"name": token.text.lower()}).run()
    return TKPlace(**doc.model_dump(exclude={"id"})) if doc else None

# --------------------------------------------------------------
# NAMED-INDIVIDUAL ENTITY-LINKING (Slice 3a)
# a proper noun NER-typed to a known type centroid becomes an entity-linked individual: it gets the
# type centroid as its SEMANTIC vector (meaning=geometry — NEVER a random/noise vector into the
# grounded 2925 space) + a context-scoped IDENTITY uid (identity=symbolic, kept separate). gated by
# NER type + has_vector so OOV gibberish (which spaCy mislabels) never mints an individual.
# --------------------------------------------------------------
# spaCy NER label -> the dictionary type-centroid sense whose 2925 vector becomes the individual's
# semantic vector. unmapped labels are not entity-linked (conservative).
_NER_TYPE_CENTROID = {
    "PERSON": "person.n.01",
    "GPE": "location.n.01",
    "LOC": "location.n.01",
    "FAC": "location.n.01",
    "ORG": "organization.n.01",
    "NORP": "group.n.01",
    "PRODUCT": "artifact.n.01",
    "WORK_OF_ART": "artifact.n.01",
    "EVENT": "event.n.01",
}

# in-memory cache of {sense -> 2925 type centroid}; these lookups repeat across tokens/sentences.
_TYPE_CENTROID_CACHE: dict[str, list[float]] = {}

def _parser_typeCentroid(sense: str) -> list[float] | None:
    if sense in _TYPE_CENTROID_CACHE:
        return _TYPE_CENTROID_CACHE[sense]
    doc = TKDictionaryDoc.find_one({"sense": sense}).run()
    vec = doc.vector if (doc and doc.vector) else None
    if vec is not None:
        _TYPE_CENTROID_CACHE[sense] = vec
    return vec

# is the surface form a REAL word (known to the spaCy lg vectors), not OOV gibberish? the parser
# tokens come from the stanza pipeline, which carries NO word vectors (token.has_vector is always
# False there), so the has_vector gate is checked against the lg `nlp` vocab — where real names
# ("Mari", "Rome") have vectors and gibberish ("Kjadhfhfjdk") does not.
def _parser_hasLgVector(text: str) -> bool:
    lex = nlp.vocab[text]
    return bool(lex.has_vector) and float(lex.vector_norm) > 0.0

# mint an entity-linked individual TKName, or None when the token is not a linkable individual
# (caller falls back to a bare TKName). deterministic + READ-ONLY (no DB writes -> /evaluate stays pure).
def parser_getIndividual(token: Token, talker: MEMStakeholder) -> TKName | None:
    # gate: a known NER type AND a real vector (rejects OOV gibberish spaCy mislabels as GPE/...)
    mapped_sense = _NER_TYPE_CENTROID.get(token.ent_type_)
    if mapped_sense is None or not _parser_hasLgVector(token.text):
        return None

    # the type centroid is the individual's SEMANTIC vector (never fabricate one)
    centroid = _parser_typeCentroid(mapped_sense)
    if centroid is None:
        return None

    # context-scoped identity uid: name@channel:talker_uid
    name_norm = token.lemma_.lower()
    context = f"{talker.channel.value}:{talker.uid}"
    uid = f"{name_norm}@{context}"

    return TKName(name=token.lemma_, ner=token.ent_type_, uid=uid, vector=centroid)

# --------------------------------------------------------------
# WORD-SENSE DISAMBIGUATION (Phase 2)
# pick the dictionary sense that best fits the sentence: POS prunes the candidates (done by the
# caller's query), then the sense whose vector is closest to the sentence's context centroid wins;
# near-ties are broken by gloss/Lesk overlap; with no usable context (or a genuine tie) we fall back
# to the most-frequent sense (the first candidate). single-pass: the context centroid is built from
# the OTHER content words' most-frequent senses (no iterative refinement yet).
# --------------------------------------------------------------
_WSD_CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}  # spaCy POS that carry context

# the centroid may override the frequency prior ONLY when it is confident: its top cosine must clear
# this absolute floor AND beat the runner-up of a different sense by this margin. otherwise a weak /
# ambiguous centroid (the "cat is a plant" failure: the sparse explicit vectors confidently mis-rank
# a person-sense over the animal-sense) can never override the most-frequent sense.
_WSD_CENTROID_FLOOR = 0.5      # absolute cosine the centroid winner must clear to be trusted
_WSD_CENTROID_MARGIN = 0.1     # how far it must beat the next-best sense to be trusted

def _wsd_cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0

# WordNet orders a word's senses by frequency, so the most-frequent sense is the one with the
# smallest sense number NN in its synset name ("word.pos.NN"). NB: the stored `sense` is the synset's
# PRIMARY-lemma name, which for a non-dominant lemma is a DIFFERENT word (e.g. "cat" -> the woman
# sense is stored as "guy.n.01"), so NN alone ties guy.n.01 with cat.n.01. We therefore (1) prefer
# candidates whose synset lemma matches the query word, then (2) take the smallest NN. Mongo
# find().to_list() has NO guaranteed order, so we never rely on candidates[0] being the most frequent.
def _wsd_senseNumber(sense: str) -> int:
    # "word.pos.NN" -> NN (large fallback so an unparseable sense never wins the min)
    try:
        return int(sense.rsplit(".", 1)[-1])
    except (ValueError, AttributeError):
        return 1_000_000

def _wsd_mostFrequent(token: Token, candidates: list[TKDictionaryDoc]) -> TKDictionaryDoc:
    lemma = token.lemma_.lower()
    # prefer senses whose synset lemma IS the query word; fall back to all if none match
    own = [c for c in candidates if (c.sense or "").rsplit(".", 2)[0].lower() == lemma]
    pool = own or candidates
    return min(pool, key=lambda c: _wsd_senseNumber(c.sense or ""))

# the most-frequent (first) dictionary sense vector for a token, or None
def _wsd_mostFrequentVector(token: Token) -> np.ndarray | None:
    for p in TKPosMapper.get_wn_pos(token.pos_):
        d = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": p}).run()
        if d and d.vector:
            return np.asarray(d.vector, dtype=np.float32)
    return None

# per-Doc cache (computed once) of {token.i: most-frequent sense vector} for content tokens
def _wsd_contextVectors(doc) -> dict[int, np.ndarray]:
    cache = doc.user_data.get("_wsd_vecs")
    if cache is None:
        cache = {}
        for t in doc:
            if t.pos_ in _WSD_CONTENT_POS and not t.is_stop and not t.is_punct:
                v = _wsd_mostFrequentVector(t)
                if v is not None:
                    cache[t.i] = v
        doc.user_data["_wsd_vecs"] = cache
    return cache

# context centroid = mean of the OTHER content tokens' most-frequent vectors (None if no context)
def _wsd_centroid(token: Token) -> np.ndarray | None:
    vecs = _wsd_contextVectors(token.doc)
    others = [v for i, v in vecs.items() if i != token.i]
    return np.mean(others, axis=0) if others else None

# Lesk overlap: how many of a gloss's content words appear among the sentence's content lemmas
def _wsd_lesk(definition: str, doc) -> int:
    if not definition:
        return 0
    glossWords = {w for w in (t.strip(".,;:()'\"`") for t in definition.lower().split()) if len(w) > 2 and w.isalpha()}
    ctx = {t.lemma_.lower() for t in doc if t.pos_ in _WSD_CONTENT_POS and not t.is_stop}
    return len(glossWords & ctx)

# choose the best sense among candidates (the dictionary docs for token's lemma+POS, >=1)
def parser_disambiguateSense(token: Token, candidates: list[TKDictionaryDoc]) -> TKDictionaryDoc:
    if len(candidates) == 1:
        return candidates[0]

    # LESK FIRST: overlap of the sense's gloss with the sentence's content words is the most reliable
    # signal on the sparse explicit vectors — a raw centroid cosine can confidently mis-rank (it scores
    # the "gossip" sense of cat ABOVE the animal sense next to "mammal", while the animal gloss is the
    # only one that contains "mammal"). pick the UNIQUE top-overlap sense.
    leskScored = [(_wsd_lesk(c.definition or "", token.doc), c) for c in candidates]
    maxLesk = max(s for s, _ in leskScored)
    leaders = [c for s, c in leskScored if s == maxLesk]
    if maxLesk > 0 and len(leaders) == 1:
        return leaders[0]

    # CONFIDENT CENTROID: lean on the context centroid only when it is decisive (rich contexts the
    # gloss overlap misses). Restrict to the tied Lesk leaders when there IS a positive overlap signal,
    # else consider all candidates. A centroid pick overrides the frequency prior ONLY if its cosine
    # clears the absolute floor AND beats the best DIFFERENT-sense runner-up by the margin — so a weak
    # / ambiguous centroid can never override the most-frequent sense.
    centroid = _wsd_centroid(token)
    if centroid is not None:
        pool = leaders if maxLesk > 0 else candidates
        scored = sorted(
            ((_wsd_cosine(np.asarray(c.vector, dtype=np.float32), centroid) if c.vector else -1.0, c) for c in pool),
            key=lambda sc: sc[0], reverse=True,
        )
        topScore, topCand = scored[0]
        runnerUp = next((s for s, c in scored[1:] if (c.sense or "") != (topCand.sense or "")), None)
        if topScore >= _WSD_CENTROID_FLOOR and (runnerUp is None or topScore - runnerUp >= _WSD_CENTROID_MARGIN):
            return topCand

    # FREQUENCY PRIOR (default): no clear Lesk winner and no confident centroid -> the most-frequent
    # sense (smallest sense number, query-word lemma preferred), NOT an arbitrary candidates[0] nor a
    # low-confidence centroid guess. TODO Phase-5: [eval:ambiguous] -> [tokeniko:ask]
    return _wsd_mostFrequent(token, candidates)

def parser_getPropertyMeaning(token: Token, pos: list[str]) -> EntityPayload:

    tkMeaning = None

    # should be in the dictionary (exclude auxiliaries, pronouns)
    doc_result: TKDictionary = None
    if len(pos) > 0 and token.pos_ != "NUM" and token.pos_ != 'PROPN' and token.pos_ != 'PRON':
        # search in dictionary
        for p in pos:           
            doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": p}).run()
            if doc_result: break
                
        # semantic fallback — only for tokens that actually carry a vector, and only accepting a
        # candidate whose cosine similarity clears _WSD_FALLBACK_MIN_SIMILARITY. an OOV/gibberish
        # token has no real vector (its query vector is all-zeros / unrelated), so force-matching it
        # to the nearest dictionary lemma is a hallucination -> leave doc_result None -> TKGeneric.
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0 and newDoc[0].has_vector:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SPACY_MAX_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    similar_scores = most_similar[2][0]
                    for key, score in zip(similar_keys, similar_scores):
                        if score < _WSD_FALLBACK_MIN_SIMILARITY:
                            continue
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else:
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            # a geo-NER proper noun (GPE/LOC/FAC) may be a real place: resolve to TKPlace (with
            # its coordinates) from the places knowledge base; otherwise it is a plain name
            tkMeaning = parser_getPlace(token) or parser_getIndividual(token, _talker) or TKName(name=token.lemma_)
        if token.pos_ == "NUM":
            clean_text = token.text.replace(',', '').strip()
            numValue = 0
            try:
                numValue = float(clean_text)
            except ValueError:
                numValue = float(w2n.word_to_num(clean_text))

            tkMeaning = TKNumber(value=numValue, num_type=token.ent_type_, text=token.lemma_)
        elif token.pos_ == "PRON":
            vector: list[int] = token.vector if token.has_vector else []
            tkMeaning = TKPronoun(lemma=token.lemma_, vector=vector)

    # if still no result, generic (it is used to manage unknown semantics)
    knownPos = pos[0] if len(pos) > 0 else ""
    if not tkMeaning and not doc_result:
        tkMeaning = TKGeneric(token=token.lemma_, pos=knownPos, upos=token.pos_)

    return tkMeaning

# get from dictionary, names, number, pronouns, generic (fallback) meaning
def parser_getMeaning(token: Token, pos: list[str]) -> EntityPayload:

    tkMeaning = None

    # should be in the dictionary (exclude auxiliaries, pronouns)
    doc_result: TKDictionary = None
    if len(pos) > 0 and token.pos_ != "NUM" and token.pos_ != 'PROPN' and token.pos_ != 'PRON':
        # search in dictionary — gather the candidate senses for this POS and pick by context (WSD),
        # falling back to the most-frequent sense when context can't decide.
        for p in pos:
            candidates = TKDictionaryDoc.find({"word": token.lemma_, "pos": p}).to_list()
            if candidates:
                doc_result = parser_disambiguateSense(token, candidates)
                break
                
        # semantic fallback — only for tokens that actually carry a vector, and only accepting a
        # candidate whose cosine similarity clears _WSD_FALLBACK_MIN_SIMILARITY. an OOV/gibberish
        # token has no real vector (its query vector is all-zeros / unrelated), so force-matching it
        # to the nearest dictionary lemma is a hallucination -> leave doc_result None -> TKGeneric.
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0 and newDoc[0].has_vector:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SPACY_MAX_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    similar_scores = most_similar[2][0]
                    for key, score in zip(similar_keys, similar_scores):
                        if score < _WSD_FALLBACK_MIN_SIMILARITY:
                            continue
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else:
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            # a geo-NER proper noun (GPE/LOC/FAC) may be a real place: resolve to TKPlace (with
            # its coordinates) from the places knowledge base; otherwise it is a plain name
            tkMeaning = parser_getPlace(token) or parser_getIndividual(token, _talker) or TKName(name=token.lemma_)
        if token.pos_ == "NUM":
            clean_text = token.text.replace(',', '').strip()
            numValue = 0
            try:
                numValue = float(clean_text)
            except ValueError:
                numValue = float(w2n.word_to_num(clean_text))

            tkMeaning = TKNumber(value=numValue, num_type=token.ent_type_, text=token.lemma_)
        elif token.pos_ == "PRON":
            vector: list[int] = token.vector if token.has_vector else []
            tkMeaning = TKPronoun(lemma=token.lemma_, vector=vector)

    # if still no result, generic (it is used to manage unknown semantics)
    knownPos = pos[0] if len(pos) > 0 else ""
    if not tkMeaning and not doc_result:
        tkMeaning = TKGeneric(token=token.lemma_, pos=knownPos, upos=token.pos_)

    return tkMeaning

# get marker
def parser_getMarker(token: Token) -> TKMarker:
    tkMarker: TKMarker = None
    marker = next((s for s in token.children if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(dep=marker.dep_, word=marker.lemma_, vector=marker.vector, parent_dep=token.dep_)
    
    # not found, but it is an indirect object, assign "to" as marker
    if tkMarker == None and token.dep_ == "iobj":
        newMarker = nlp.tokenizer("to")
        tkMarker = TKMarker(word="to", dep="mark", vector=newMarker.vector if newMarker.has_vector else [], parent_dep=token.dep_)

    return tkMarker

# clause tense from the finite element: modal will/shall -> future; else the Tense morph of the
# auxiliary if present, else the predicate verb itself. returns "past" | "pres" | "fut" | None.
def parser_getTense(predicateToken: Token, auxToken: Token | None) -> str | None:
    if auxToken is not None and auxToken.lemma_.lower() in ("will", "shall"):
        return "fut"
    source = auxToken if auxToken is not None else predicateToken
    tense = source.morph.get("Tense")
    return tense[0].lower() if tense else None

# get seamntic value from dictionary + properties
def parser_getFullEntity(token: Token, quotes: list[tuple[list[Token], list[Token], Span]] = [], op: TKOperator = TKOperator.AND, isPredicate = False) -> TKFullEntity:

    # related tokens to the entity
    conjuncts = list(token.conjuncts)
    children = list(token.children)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_properties: list[TKFullEntity] = []
    tkMarker = None
    tkAux = None

    # get single entity or statement
    tkMarker = parser_getMarker(token)
    tkMeaning = parser_getMeaning(token, pos)

    # get properties (for each token directly bound to the result)
    doc_properties = parser_getProperties(children)

    # get auxiliary
    aux = next((s for s in children if s.dep_ in ["cop","aux"]), None)
    tense = parser_getTense(token, aux) if isPredicate else None
    if aux:
        posAux = TKPosMapper.get_wn_pos(aux.pos_)
        dictAux = parser_getMeaning(aux, posAux)
        # parser_getMeaning may return a TKGeneric (the aux lemma isn't in the dictionary and no
        # vector fallback cleared the threshold — e.g. an aux in a malformed embedded clause like
        # "...know how are you"); TKGeneric carries no .vector, so fall back to an empty vector
        # (a valid TKAux, same as the no-aux branch below).
        auxVector = getattr(dictAux, "vector", None) or []
        tkAux = TKAux(lemma=aux.lemma_, vector=auxVector, tense=tense)
    elif tense:
        # no auxiliary, but stash the predicate verb's own tense for the spacetime time axis
        tkAux = TKAux(tense=tense)

    # ----------------------------------------
    # subordinates entities (search)
    # ----------------------------------------
    subordinates: list[TKFullEntity] = []
    for t in children:
        if parser_isStatement(t):
            subordinate = parser_parseSubordinate(t, quotes)
            if subordinate:
                subordinates.append(subordinate)

    # primary entity (from token)
    primaryEntity: TKFullEntity = TKFullEntity(entity=tkMeaning, dep=token.dep_, op=op, token=token.text, aux=tkAux, marker=tkMarker, properties=doc_properties, subordinates=subordinates)

    # ----------------------------------------
    # coordinated entities (conjuncts)
    # ----------------------------------------   
    for c in [cc for cc in conjuncts if cc.head == token]:
        relatedEntity = parser_getRelatedEntity(c, quotes, isPredicate)
        if relatedEntity: primaryEntity.conjuncts.append(relatedEntity)

    return primaryEntity

# indirects complements
def parser_getIndirects(tokens: list[Token], quotes: list[tuple[list[Token], list[Token], Span]] = []) -> list[TKFullEntity]: 

    # initialize result
    indirectFullEntities: list[TKFullEntity] = list()
    usedTokens: list[Token] = list()

    for t in tokens:
        if t in usedTokens: continue

        # reset indirect entity
        indirectEntity = None

        # indirect objects
        if t.dep_ in ["obl", "obl:tmod", "iobj", "obl:agent"]:
            indirectEntity = parser_getFullEntity(t, quotes)

        # if found 
        if indirectEntity: 
            # mark already used
            usedTokens.extend(t.children)
            usedTokens.extend(t.subtree)
            
            # append indirect
            indirectFullEntities.append(indirectEntity)

    return indirectFullEntities

# parse sentence (recurively called))
def parser_parseSentence(root: Token, tokens: list[Token], clause_type: TKClause = TKClause.MAIN, subject: Token = None) -> TKStatement: 
    global _talker, _tokeniko

    # rebuild doc for quotations
    subStatement = " ".join([t.text for t in tokens])
    doc = nlp_stanza(subStatement)
    quotes: list[tuple[list[Token], list[Token], Span]] = list(textacy.extract.triples.direct_quotations(doc))

    # all necessary trees
    tokens = list(root.subtree)
    children = list(root.children)
   
    # ------------------------------
    # root is predicate
    # ------------------------------
    # the root is a verb or an adjective, assign (auxiliaries are properties)
    tkPredicate = parser_getFullEntity(root, quotes, TKOperator.AND, True)
    
    # ------------------------------
    # search subject (first csubj, then nsubj)
    # ------------------------------
    tkSubject = None
    subjectToken = next((s for s in children if (s.dep_ == "nsubj" or s.dep_ == "nsubj:pass")), None)
    if subjectToken: tkSubject = parser_getFullEntity(subjectToken, quotes)
    else: 
        subjectToken = next((s for s in children if (s.dep_ == "csubj")), None)
        if subjectToken: tkSubject = parser_parseSubordinate(subjectToken, quotes)

    # ------------------------------
    # search direct
    # ------------------------------
    tkDirect = None
    directToken = next((s for s in children if s.dep_ == "obj"), None)
    if directToken: tkDirect = parser_getFullEntity(directToken, quotes)

    # ------------------------------
    # search indirect (only on root's children)
    # ------------------------------
    indirectEntities = parser_getIndirects(children, quotes)

    # main statement
    tkMain = TKStatement()
 
    # ----------------------------------------
    # always create source and target entities
    # ----------------------------------------
    # manage quotes
    if (subject):
        forceSubjectEntity = parser_getFullEntity(subject, quotes)
        tkMain.create_entity(payload=forceSubjectEntity.entity)
        tkMain.create_entity(payload=TKMetaEntity(who=_talker, isListening=True, isTalking=False))
    else:
        tkMain.create_entity(payload=TKMetaEntity(who=_talker, isListening=False, isTalking=True))
        tkMain.create_entity(payload=TKMetaEntity(who=_tokeniko, isListening=True, isTalking=False))
        
    tkMain.clause_type = clause_type
    if tkPredicate: tkMain.create_predicate(fullEntity=tkPredicate)
    if subjectToken: tkMain.create_subject(fullEntity=tkSubject)
    if directToken: tkMain.create_direct(fullEntity=tkDirect)
    for it in indirectEntities: tkMain.add_indirect(fullEntity=it)

    # ----------------------------------------
    # interrogative mood (a question is ANSWERED, not asserted). detection is empirically robust:
    # "?" survives as a PUNCT token, and every wh-word carries PronType=Int in its morph (regardless of
    # POS — PRON who/what, ADV how/where/why, DET which). polar = "?" with no wh-word; wh = a wh-word
    # whose lemma maps to the gap role (anchor_whType). carried on the statement -> dubitative + wh_role.
    # ----------------------------------------
    whToken = next((t for t in tokens if "Int" in t.morph.get("PronType")), None)
    if whToken is not None or any(t.text == "?" for t in tokens):
        tkMain.dubitative = 1.0
        if whToken is not None:
            tkMain.wh_role = anchor_whType(whToken.lemma_)

    #return statement
    return tkMain

# core internal recursive function to parse a list of token into a TKStatements
def parser_core(tokens: list[Token]) -> TKStatements: 

    # init statement
    statements = TKStatements()

    # search separate predicates
    roots = [s for s in tokens if s.dep_ == "root"] # number of separate sentences
    
    # check for recursion
    if len(roots) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        # recursive iteration for each predicate 
        for p in roots:
            statements += parser_core(list(p.subtree))

    elif len(roots) == 1:              
        sentence = parser_parseSentence(roots[0], list(roots[0].subtree), clause_type=TKClause.MAIN)
        statements.append(sentence)

    return statements

# --------------------------------------------------------------
# MAIN entry point to parse an input text
# --------------------------------------------------------------
def parser(tokens: str, talker: MEMStakeholder, tokeniko: MEMStakeholder, context: MEMContext = None, ollamaClient: OllamaClient = None) -> TKStatements:
    global _context, _ollamaClient, _talker, _tokeniko

    # prepare input
    tokens = util_removeSpace(tokens)
    tokens = util_expandContractions(tokens) # stanza tokenizer mis-merges some contractions (e.g. "I'm")

    # assign variables
    _context = context
    _ollamaClient = ollamaClient

    # determine stakeholders
    _talker =talker
    _tokeniko = tokeniko

    # spacy parse
    doc = nlp_stanza(tokens)

    # get all tokens
    tkStatements: TKStatements = parser_core(list(doc))

    # return statement
    return tkStatements

# --------------------------------------------------------------
# DISPLAY
# --------------------------------------------------------------

# wrap the displacy dep diagram
def parser_diagram(tokens: str) -> str:
    
    # spacy parse
    doc = nlp_stanza(tokens)
    diagram = displacy.render(doc, style = "dep")

    html = '<html><body>' + diagram + '</body></html>'

    return html
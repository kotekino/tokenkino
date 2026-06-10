# ------------------------------------------------------------------------------------------------
# PARSER V2: transform a token list into a list of TKStatements (using spacy for the first ingestion)
# ------------------------------------------------------------------------------------------------
# i'm bug in stanza spacy

from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Span, Token
import spacy_stanza
import numpy as np
from lib.core.tk import EntityPayload, TKAux, TKClause, TKFullProperty, TKMarker, TKFullEntity, TKDictionary, TKGeneric, TKMetaEntity, TKName, TKNumber, TKOperator, TKPronoun, TKStatement, TKStatements
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper
from lib.core.tkllc import TKLLC
from lib.llc.constants import _SPACY_MODEL, _SPACY_MAX_SIMILAR_RESULTS, _OPERATORS_BASE_ANCHORS, _OPERATORS_SIMILARITY_THRESHOLD
from lib.core.utilities import util_removeSpace
from functools import cmp_to_key
import textacy
from word2number import w2n
from lib.core.memory import MEMContext, MEMStakeholder

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

    # 1. STRADA VELOCE (Hit diretto)
    if lemma in _OPERATORS_BASE_ANCHORS:
        return _OPERATORS_BASE_ANCHORS[lemma]

    # 2. SPAZIO VETTORIALE (Distanza dalle 3 ancore base)
    best_op = TKOperator.AND  # Default di emergenza
    highest_sim = -1.0

    newDoc = nlp.tokenizer(token.lemma_)

    for anchor_word, operator in _OPERATORS_BASE_ANCHORS.items():
        anchor_lexeme = nlp.vocab[anchor_word]
        
        if newDoc[0].has_vector and anchor_lexeme.has_vector:
            sim = newDoc[0].similarity(anchor_lexeme)
            if sim > highest_sim:
                highest_sim = sim
                best_op = operator

    # 3. THRESHOLD CHECK
    if highest_sim >= _OPERATORS_SIMILARITY_THRESHOLD:
        return best_op
    else:
        return TKOperator.AND

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
        entity = TKFullEntity(entity=sentence, dep=token.dep_, aux=None, marker=None, token=None, properties=[], conjunct=None, op=operator) if sentence else None
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
def parser_getPropertyMeaning(token: Token, pos: list[str]) -> EntityPayload:
    
    tkMeaning = None

    # should be in the dictionary (exclude auxiliaries, pronouns)
    doc_result: TKDictionary = None
    if len(pos) > 0 and token.pos_ != "NUM" and token.pos_ != 'PROPN' and token.pos_ != 'PRON':
        # search in dictionary
        for p in pos:           
            doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": p}).run()
            if doc_result: break
                
        # semantic fallback
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SPACY_MAX_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    for key in similar_keys:
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else: 
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            tkMeaning = TKName(name=token.lemma_)
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
        # search in dictionary
        for p in pos:           
            doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": p}).run()
            if doc_result: break
                
        # semantic fallback
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SPACY_MAX_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    for key in similar_keys:
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else: 
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            tkMeaning = TKName(name=token.lemma_)
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
    if aux:
        posAux = TKPosMapper.get_wn_pos(aux.pos_)
        dictAux = parser_getMeaning(aux, posAux)
        tkAux = TKAux(lemma=aux.lemma_, vector=dictAux.vector)

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
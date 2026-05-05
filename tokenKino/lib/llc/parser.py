from typing import Any
from unittest import result
import copy
from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Token
from spacy import Language
import stanza
import spacy_stanza
from spacy_stanza import Language as StanzaLanguage
import numpy as np
from lib.core.entities import TKLLC, EntityPayload, LLCItemPayload, TKClause, TKMarker, TKFullEntity, TKContext, TKDictionary, TKGeneric, TKName, TKOperator, TKStatement, TKStatements
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper
from lib.llc.constants import _SPACY_MODEL, _SPACY_MAX_SIMILAR_RESULTS, _OPERATORS_BASE_ANCHORS, _OPERATORS_SIMILARITY_THRESHOLD
from lib.llc.flattener import llc_flat
from lib.llc.decompiler import llc_raw


# TODO: 
# GOING manage spacetime (temporal and spatial modifiers)
# GOING manage compiler (flat and recursive)
# manage parataxis (and other non-standard coordination)
# manage articles
# manage passive
# manage det
# manage copula verbs (be, seem, appear, become, etc.)
# manage plurality
# test against every sentence from UD2

# stanza
stanza.download("en", package="lines")

# --- INIZIO PATCH PYTORCH ---
import torch
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# --- FINE PATCH PYTORCH ---

# load spacy model
nlp_stanza = spacy_stanza.load_pipeline("en", package="lines")
nlp = spacy.load(_SPACY_MODEL)

# global variables
_context: TKContext = None
_ollamaClient: OllamaClient = None

# get operator corresponding to cc
def llc_ccToOperator(token: Token) -> TKOperator:
    lemma = token.lemma_.lower()

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
        print(f"Logica Fuzzy: [{lemma}] mappato a {best_op} (Sim: {highest_sim:.2f})")
        return best_op
    else:
        print(f"Logica Fuzzy: [{lemma}] sotto la soglia. Uso default AND.")
        return TKOperator.AND

# (DONE) get properties
def llc_getProperties(tokens: list[Token]) -> list[TKFullEntity]:

    doc_properties: list[TKFullEntity] = []
    property: TKFullEntity

    for t in tokens:
        property = None
        if t.dep_ == "advmod" or t.dep_ == "nummod" or t.dep_ == "amod" or t.dep_ == "nmod" or t.dep_ == "nmod:poss" or t.dep_ == "det":
            property = llc_getFullEntity(t, False)

        if property: 
            doc_properties.append(property)

    return doc_properties

# (DONE) get related by conj entities
def llc_getRelatedEntity(token: Token, statement: bool = False) -> TKFullEntity:
    
    entity: TKFullEntity = None

    # decide if its a conj single word or a sentence
    if statement:
        sentence = llc_parseSentence(token.subtree, clause_type=TKClause.COORDINATE)
        entity = TKFullEntity(entity=sentence, marker=None, properties=[], conjunct=None, op=TKOperator.AND) if sentence else None
    else:
        entity = llc_getFullEntity(token, False)
    
    # if found an entity
    if entity:
        
        # search operator, otherwise default
        opToken = next((tt for tt in list(token.subtree) if tt.dep_ == "cc" or tt.dep_ == "punct"), None)
        operator: TKOperator = llc_ccToOperator(opToken) if opToken else TKOperator.AND

        entity.op = operator    
        return entity
    
    return [None, usedTokens]

# (ONGOING) get seamntic value from dictionary + properties
def llc_getFullEntity(token: Token, predicate: bool = False) -> TKFullEntity:

    # related tokens to the entity
    children = list(token.children)
    conjuncts = list(token.conjuncts)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_result: TKDictionary = None
    doc_properties: list[TKFullEntity] = []
    tkMarker = None

    # should be in the dictionary
    if len(pos) > 0:
        for p in pos:
            # search in dictionary
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

    # if still no result, generic (it is used to manage unknown semantics)
    knownPos = pos[0] if len(pos) > 0 else ""
    if not doc_result: tkMeaning = TKGeneric(token=token.lemma_, pos=knownPos, upos=token.pos_)

    # get properties (for each token directly bound to the result)
    doc_properties = llc_getProperties(children)

    # get marker if properties 
    marker = next((s for s in children if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(type=marker.dep_, lemma=marker.lemma_, vector=marker.vector)    

    # primary entity (from token)
    primaryEntity: TKFullEntity = TKFullEntity(entity=tkMeaning, op=TKOperator.AND, marker=tkMarker, properties=doc_properties)

    # get related entities
    for c in [cc for cc in conjuncts if cc.head == token]:
        relatedEntity = llc_getRelatedEntity(c, predicate)
        if relatedEntity:
            primaryEntity.conjuncts.append(relatedEntity)

    return primaryEntity

# (ONGOING) get all indirect objects (cycling remaining tokens)
def llc_getIndirects(tokens: list[Token]) -> list[TKFullEntity]: 

    # initialize result
    indirectFullEntities: list[TKFullEntity] = list()

    usedTokens: list[Token] = list()

    for t in tokens:
        if t in usedTokens: continue

        # reset indirect entity
        indirectEntity = None

        # case dative (can be a name [take the entity] or a prep [take the first child])
        # oblique (expect a case or marker)
        if t.dep_ == "obl": 
            indirectEntity = llc_getFullEntity(t, False)
            if indirectEntity:
                usedTokens.extend(t.children)
                usedTokens.extend(t.subtree)
        # indirect object (you give YOU something)
        elif t.dep_ == "iobj": 
            indirectEntity = llc_getFullEntity(t, False)
            if indirectEntity:
                usedTokens.extend(t.children)
                usedTokens.extend(t.subtree)            
        # clausal complements
        if t.dep_ == "xcomp" or t.dep_ == "ccomp" or t.dep_ == "advcl" or t.dep_ == "acl": 
            indirectEntity = llc_parseSubordinate(t)
            if indirectEntity:
                usedTokens.extend(t.children)
                usedTokens.extend(t.subtree)

        # if found 
        if indirectEntity: 
            indirectFullEntities.append(indirectEntity)

    return indirectFullEntities

# parse a subordinate clause
def llc_parseSubordinate(token: Token) -> TKFullEntity:

    # initialize variables
    childrenTokens = list(token.children)
    tkMarker: TKMarker = None
    result: TKFullEntity = None

    # get coordination marker (like: otherwise, but, etc.)
    marker = next((s for s in childrenTokens if s.dep_ == "advmod"), None)
    if marker and llc_ccToOperator(marker) != None:
        a = "it's like a conjunct" # TODO: add it in the conjuncts, instead of indirects

    # get indirect marker 
    marker = next((s for s in childrenTokens if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(type=marker.dep_, lemma=marker.lemma_, vector=marker.vector)    

    tokenSubtree = [t for t in token.subtree if t != marker]

    tkStatement = llc_parseSentence(tokenSubtree, clause_type=TKClause.SUBORDINATE)
    if tkStatement: result = TKFullEntity(entity=tkStatement, marker=tkMarker, properties=[], conjuncts=[], op=TKOperator.AND)
    
    return result

# (ONGOING) parse sentence (simple or compoung)
def llc_parseSentence(inputTokens: list[Token], clause_type: TKClause = TKClause.MAIN) -> TKStatement: 
    
    # get root
    subStatement = " ".join([t.text for t in inputTokens])
    doc = nlp_stanza(subStatement)
    root = [s for s in list(doc) if s.dep_ == "root"][0]
    tokens = list(root.subtree) 
   
    # ------------------------------
    # root is predicate
    # ------------------------------
    # the root is a verb or an adjective, assign (auxiliaries are properties)
    tkPredicate = llc_getFullEntity(root, True)

    # ------------------------------
    # search subject (first csubj, then nsubj)
    # ------------------------------
    tkSubject = None
    subjectToken = next((s for s in tokens if (s.dep_ == "nsubj" or s.dep_ == "nsubj:pass") and s.head == root), None)
    if subjectToken: tkSubject = llc_getFullEntity(subjectToken, False)
    else: 
        subjectToken = next((s for s in tokens if (s.dep_ == "csubj") and s.head == root), None)
        if subjectToken: tkSubject = llc_parseSubordinate(subjectToken)

    # ------------------------------
    # search direct
    # ------------------------------
    tkDirect = None
    directToken = next((s for s in tokens if s.dep_ == "obj" and s.head == root), None)
    if directToken: tkDirect = llc_getFullEntity(directToken, False)

    # ------------------------------
    # search indirect
    # ------------------------------
    indirectEntities = llc_getIndirects(tokens)

    # main statement
    tkMain = TKStatement()
    tkMain.clause_type = clause_type
    if tkPredicate: 
        predicateId = tkMain.create_predicate(payload=tkPredicate.entity, op=tkPredicate.op, marker=tkPredicate.marker, conjuncts=tkPredicate.conjuncts)
        # add properties
        if len(tkPredicate.properties) > 0: tkMain.add_properties(tkPredicate.properties, predicateId)

    if subjectToken:
        subjectId = tkMain.create_subject(payload=tkSubject.entity, op=tkSubject.op, marker=tkSubject.marker, conjuncts=tkSubject.conjuncts)
        # add properties
        if len(tkSubject.properties) > 0: tkMain.add_properties(tkSubject.properties, subjectId)

    if directToken: 
        directId = tkMain.create_direct(payload=tkDirect.entity, op=tkDirect.op, marker=tkDirect.marker, conjuncts=tkDirect.conjuncts)
        # add properties
        if len(tkDirect.properties) > 0: tkMain.add_properties(tkDirect.properties, directId)

    for it in indirectEntities:
        indirectId = tkMain.add_indirect(payload=it.entity, op=it.op, marker=it.marker, conjuncts=it.conjuncts)
        # add properties
        if len(it.properties) > 0: tkMain.add_properties(it.properties, indirectId)

    #return statement
    return tkMain

# (DONE) core internal recursive function to parse a list of token into a TKStatements
def llc_core(tokens: list[Token]) -> TKStatements: 

    # init statement
    statements = TKStatements()

    # search separate predicates
    roots = [s for s in tokens if s.dep_ == "root"] # number of separate sentences
    
    # check for recursion
    if len(roots) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        # recursive iteration for each predicate 
        for p in roots:
            statements += llc_core(list(p.subtree))

    elif len(roots) == 1:              
        sentence = llc_parseSentence(list(roots[0].subtree), clause_type=TKClause.MAIN)
        statements.append(sentence)

    return statements

# --------------------------------------------------------------
# (DONE) MAIN entry point to parse an input text
# --------------------------------------------------------------
def llc(tokens: str, context: TKContext = None, ollamaClient: OllamaClient = None) -> dict[str, TKLLC | TKStatements]:
    global _context, _ollamaClient

    # assign variables
    _context = context
    _ollamaClient = ollamaClient

    # spacy parse
    doc = nlp_stanza(tokens)

    # get all tokens
    tkStatements: TKStatements = llc_core(list(doc))

    # flat statements
    tkLLC: TKLLC = llc_flat(tkStatements) # if 1 == 0 else None

    # raw output
    rawOutput = llc_raw(tkLLC) if tkLLC else ''

    # return statement
    return {
        "input": tokens,
        "raw": rawOutput,
        "flat": tkLLC, 
        "recursive": tkStatements
        }

# (DONE) wrap the displacy dep diagram
def llc_diagram(tokens: str) -> str:
    
    # spacy parse
    doc = nlp_stanza(tokens)
    diagram = displacy.render(doc, style = "dep")

    html = '<html><body>' + diagram + '</body></html>'

    return html

# reference: https://universaldependencies.org/u/dep/acl.html

# acl: clausal modifier of noun (adnominal clause)
# https://universaldependencies.org/u/dep/acl.html#acl-clausal-modifier-of-noun-adnominal-clause
# ->

# acl:relcl: relative clause modifier
# https://universaldependencies.org/u/dep/acl-relcl.html
# -> double the sentence object for both sentences

# advcl: adverbial clause modifier
# https://universaldependencies.org/u/dep/advcl.html#advcl-adverbial-clause-modifier
# ->

# advcl:relcl: adverbial relative clause modifier
# https://universaldependencies.org/u/dep/advcl-relcl.html
# ->
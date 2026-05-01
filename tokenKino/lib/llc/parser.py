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
from lib.llc.flattener import llc_flat, llc_raw

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
def llc_getProperties(tokens: list[Token]) -> tuple[list[TKFullEntity], list[Token]]:

    # initialize usedTokens
    usedTokens: list[Token] = list()

    doc_properties: list[TKFullEntity] = []
    property: tuple[list[TKFullEntity], list[Token]] = [list(),list()]

    for t in (tt for tt in tokens if tt not in usedTokens):
        property = [None, list()]
        if t.dep_ == "advmod" or t.dep_ == "nummod" or t.dep_ == "amod" or t.dep_ == "nmod" or t.dep_ == "nmod:poss" or t.dep_ == "det":
            availableTokens = [s for s in tokens if s not in usedTokens]
            property = llc_getFullEntity(t, availableTokens)

        if property[0]: 
            usedTokens += property[1]
            usedTokens.append(t)
            doc_properties.append(property[0])

    return [doc_properties, usedTokens]

# (DONE) get related by conj entities
def llc_getRelatedEntity(token: Token, tokens: list[Token], statement: bool = False) -> tuple[TKFullEntity, list[Token]]:
    
    usedTokens: list[Token] = list()
    entity: tuple[TKFullEntity, list[Token]] = None

    # decide if its a conj single word or a sentence
    if statement:
        sentence = llc_parseSentence(token, tokens, clause_type=TKClause.COORDINATE)
        entity = [TKFullEntity(entity=sentence[0], marker=None, properties=[], conjunct=None, op=TKOperator.AND) if sentence[0] else None, sentence[1]]
    else:
        entity = llc_getFullEntity(token, tokens, False)
    
    # if found an entity
    if entity[0]:
        usedTokens += entity[1]
        
        # search operator, otherwise default
        opToken = next(tt for tt in tokens if tt not in usedTokens and tt in list(token.children) and (tt.dep_ == "cc"))
        if opToken: usedTokens.append(opToken)  
        operator: TKOperator = llc_ccToOperator(opToken) if opToken else TKOperator.AND

        entity[0].op = operator    
        return [entity[0], usedTokens]
    
    return [None, usedTokens]

# (ONGOING) get seamntic value from dictionary + properties
def llc_getFullEntity(token: Token, tokens: list[Token], predicate: bool = False) -> tuple[TKFullEntity, list[Token]]:

    # initialize usedTokens
    usedTokens: list[Token] = list()

    # related tokens to the entity
    subtree = [t for t in tokens if t in list(token.subtree)]
    children = [t for t in tokens if t in list(token.children)]
    conjuncts = [t for t in tokens if t in list(token.conjuncts)]

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

    # add itself as used token
    usedTokens.append(token)

    # get properties (for each token directly bound to the result)
    doc_properties = llc_getProperties([s for s in children if s not in usedTokens])
    usedTokens += doc_properties[1]

    # get marker 
    marker = next((s for s in children if s not in usedTokens and (s.dep_ == "case" or s.dep_ == "mark")), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(type=marker.dep_, lemma=marker.lemma_, vector=marker.vector)    
        usedTokens.append(marker)

    # primary entity (from token)
    primaryEntity: TKFullEntity = TKFullEntity(entity=tkMeaning, op=TKOperator.AND, marker=tkMarker, properties=doc_properties[0])

    # get related entities
    for c in [cc for cc in conjuncts if cc.head == token]:
        ce, ut = llc_getRelatedEntity(c, list(c.subtree), predicate)
        if ce:
            primaryEntity.conjuncts.append(ce)
            usedTokens += ut

    return [primaryEntity, usedTokens]

# (ONGOING) get all indirect objects (cycling remaining tokens)
def llc_getIndirects(tokens: list[Token]) -> tuple[list[TKFullEntity], list[Token]]: 
    
    # initialize usedTokens
    usedTokens: list[Token] = list()

    # initialize result
    indirectFullEntities: list[TKFullEntity] = list()

    for t in (tt for tt in tokens if tt not in usedTokens):
        # reset indirect
        indirectToken: Token = None

        # case dative (can be a name [take the entity] or a prep [take the first child])
        # oblique (expect a case or marker)
        if t.dep_ == "obl":
            indirectToken = t
            availableTokens = [s for s in tokens if s not in usedTokens]
            indirectEntity, ut = llc_getFullEntity(indirectToken, availableTokens)
            usedTokens += ut # get used tokens   
        # indirect object (you give YOU something)
        elif t.dep_ == "iobj":
            indirectToken = t
            availableTokens = [s for s in tokens if s not in usedTokens]
            indirectEntity, ut = llc_getFullEntity(indirectToken, availableTokens)
            usedTokens += ut # get used tokens
        # clausal complements
        if t.dep_ == "xcomp" or t.dep_ == "ccomp" or t.dep_ == "advcl" or t.dep_ == "acl":
            indirectToken = t
            availableTokens = [s for s in tokens if s not in usedTokens]
            indirectEntity, ut = llc_parseSubordinate(indirectToken, availableTokens)
            usedTokens += ut # get used tokens

        # if found 
        if indirectToken: 
            indirectFullEntities.append(indirectEntity)

    return [indirectFullEntities, usedTokens]

# parse a subordinate clause
def llc_parseSubordinate(token: Token, tokens: list[Token]) -> tuple[TKFullEntity, list[Token]]:

    # initialize variables
    childrenTokens = [s for s in list(token.children) if s in tokens]
    tkMarker: TKMarker = None
    usedTokens: list[Token] = list()
    result: TKFullEntity = None

    # get coordination marker (like: otherwise, but, etc.)
    marker = next((s for s in childrenTokens if s not in usedTokens and (s.dep_ == "advmod")), None)
    if marker and llc_ccToOperator(marker) != None:
        a = "it's like a conjunct" # TODO: addit in the conjuncts, instead of indirects

    # get indirect marker 
    marker = next((s for s in childrenTokens if s not in usedTokens and (s.dep_ == "case" or s.dep_ == "mark")), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(type=marker.dep_, lemma=marker.lemma_, vector=marker.vector)    
        usedTokens.append(marker)
    
    # update remaining tokens
    subtreeTokens = [s for s in list(token.subtree) if s in tokens and s not in usedTokens]

    st, ut = llc_parseSentence(token, subtreeTokens, clause_type=TKClause.SUBORDINATE)
    usedTokens += ut # get used tokens
    if st: result = TKFullEntity(entity=st, marker=tkMarker, properties=[], conjuncts=[], op=TKOperator.AND)
    
    return [result, usedTokens]

# (ONGOING) parse sentence (simple or compoung)
def llc_parseSentence(root: Token, tokens: list[Token], clause_type: TKClause = TKClause.MAIN) -> tuple[TKStatement, list[Token]]: 
    
    # initialize usedTokens
    usedTokens: list[Token] = list()

    # ------------------------------
    # root is predicate
    # ------------------------------

    # the root is a verb or an adjective, assign (auxiliaries are properties)
    tkPredicate = llc_getFullEntity(root, tokens, True)
    usedTokens += tkPredicate[1] # get used tokens
    tokens = [t for t in tokens if t not in usedTokens] # remove used tokens

    # ------------------------------
    # search subject (first csubj, then nsubj)
    # ------------------------------
    subjectToken = next((s for s in tokens if (s.dep_ == "nsubj" or s.dep_ == "nsubj:pass") and s.head == root), None)
    if subjectToken:
        tkSubject = llc_getFullEntity(subjectToken, tokens)
        usedTokens += tkSubject[1] # get used tokens
        tokens = [t for t in tokens if t not in usedTokens] # remove used tokens
    else:
        subjectToken = next((s for s in tokens if (s.dep_ == "csubj") and s.head == root and s not in usedTokens), None)
        if subjectToken:
            subtreeTokens = [s for s in list(subjectToken.subtree) if s in tokens and s not in usedTokens]
            tkSubject = llc_parseSubordinate(subjectToken, subtreeTokens)
            usedTokens += tkSubject[1] # get used tokens
            tokens = [t for t in tokens if t not in usedTokens] # remove used tokens

    # ------------------------------
    # search direct
    # ------------------------------
    directToken = next((s for s in tokens if s.dep_ == "obj" and s.head == root), None)
    if directToken: 
        tkDirect = llc_getFullEntity(directToken, tokens)
        usedTokens += tkDirect[1] # get used tokens
        tokens = [t for t in tokens if t not in usedTokens] # remove used tokens

    # ------------------------------
    # search indirect
    # ------------------------------
    indirectEntities = llc_getIndirects(tokens)
    usedTokens += indirectEntities[1] # get used tokens
    tokens = [t for t in tokens if t not in usedTokens] # remove used tokens  

    # main statement
    tkMain = TKStatement()
    tkMain.clause_type = clause_type
    if tkPredicate[0]: 
        predicateId = tkMain.create_predicate(payload=tkPredicate[0].entity, op=tkPredicate[0].op, marker=tkPredicate[0].marker, conjuncts=tkPredicate[0].conjuncts)
        # add properties
        if len(tkPredicate[0].properties) > 0: tkMain.add_properties(tkPredicate[0].properties, predicateId)

    if subjectToken:
        subjectId = tkMain.create_subject(payload=tkSubject[0].entity, op=tkSubject[0].op, marker=tkSubject[0].marker, conjuncts=tkSubject[0].conjuncts)
        # add properties
        if len(tkSubject[0].properties) > 0: tkMain.add_properties(tkSubject[0].properties, subjectId)

    if directToken: 
        directId = tkMain.create_direct(payload=tkDirect[0].entity, op=tkDirect[0].op, marker=tkDirect[0].marker, conjuncts=tkDirect[0].conjuncts)
        # add properties
        if len(tkDirect[0].properties) > 0: tkMain.add_properties(tkDirect[0].properties, directId)

    for it in indirectEntities[0]:
        indirectId = tkMain.add_indirect(payload=it.entity, op=it.op, marker=it.marker, conjuncts=it.conjuncts)
        # add properties
        if len(it.properties) > 0: tkMain.add_properties(it.properties, indirectId)

    #return statement
    return [tkMain, usedTokens]

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
        sentence = llc_parseSentence(roots[0], list(roots[0].subtree), clause_type=TKClause.MAIN)
        statements.append(sentence[0])

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
    rawOutput = llc_raw(tkLLC)

    # return statement
    return {
        "raw": rawOutput,
        "llc (flat)": tkLLC, 
        "llc (recursive)": tkStatements
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
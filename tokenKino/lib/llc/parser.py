# ------------------------------------------------------------------------------------------------
# PARSER: transform a token list into a list of TKStatements (using spacy for the first ingestion)
# ------------------------------------------------------------------------------------------------

from typing import Any
from unittest import result
import copy
from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Span, Token
import spacy_stanza
import numpy as np
from lib.core.entities import TKLLC, MEMContext, MEMStakeholder, TKAux, TKClause, TKEntityReference, TKMarker, TKFullEntity, TKDictionary, TKGeneric, TKMetaEntity, TKName, TKNumber, TKOperator, TKPronoun, TKStatement, TKStatements
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper
from lib.llc.constants import _SPACY_MODEL, _SPACY_MAX_SIMILAR_RESULTS, _OPERATORS_BASE_ANCHORS, _OPERATORS_SIMILARITY_THRESHOLD
from lib.llc.decompiler import decompiler_raw
from lib.core.utilities import util_removeSpace
from lib.core.constants import _ME_NAME
from functools import cmp_to_key
import textacy
from word2number import w2n

# --- INIZIO PATCH PYTORCH ---
import torch
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# --- FINE PATCH PYTORCH ---

# load spacy model
# nlp_stanza = spacy_stanza.load_pipeline("en", package="lines")
nlp_stanza = spacy_stanza.load_pipeline("en")
nlp = spacy.load(_SPACY_MODEL)

# global variables
_context: MEMContext = None
_ollamaClient: OllamaClient = None
_talker: MEMStakeholder = None
_tokeniko: MEMStakeholder = None

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

# (DONE) get properties
def parser_getProperties(tokens: list[Token], predicate: bool = False) -> list[TKFullEntity]:

    doc_properties: list[TKFullEntity] = []
    property: TKFullEntity

    for t in tokens:
        property = None
        if t.dep_ == "nummod" \
        or t.dep_ == "amod" \
        or t.dep_ == "nmod" \
        or t.dep_ == "advmod" \
        or t.dep_ == "compound" \
        or t.dep_ == "nmod:poss" \
        or t.dep_ == "det":
            property = parser_getFullEntity(t, False)

        if property: 
            doc_properties.append(property)

    return doc_properties

# (DONE) get related by conj entities
def parser_getRelatedEntity(token: Token, statement: bool = False) -> TKFullEntity:
    
    entity: TKFullEntity = None

    # search operator, otherwise default
    opToken = next((tt for tt in list(token.subtree) if tt.dep_ == "cc" or tt.dep_ == "punct"), None)
    operator: TKOperator = parser_ccToOperator(opToken) if opToken else TKOperator.AND

    # decide if its a conj single word or a sentence
    if statement:
        subtree = [t for t in token.subtree if t != opToken] # remove operator
        sentence = parser_parseSentence(subtree, clause_type=TKClause.COORDINATE)
        entity = TKFullEntity(entity=sentence, aux=None, marker=None, token=None, properties=[], conjunct=None, op=operator) if sentence else None
    else:
        entity = parser_getFullEntity(token, False)
    
    # no entity found
    return entity

# (ONGOING) get seamntic value from dictionary + properties
def parser_getFullEntity(token: Token, predicate: bool = False) -> TKFullEntity:

    # set operator
    op = TKOperator.AND

    # related tokens to the entity
    conjuncts = list(token.conjuncts)
    children = list(token.children)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_result: TKDictionary = None
    doc_properties: list[TKFullEntity] = []
    tkMarker = None
    tkAux = None
    tkMeaning = None

    # should be in the dictionary (exclude auxiliaries, pronouns)
    if len(pos) > 0 and token.pos_ != "NUM" and token.pos_ != "AUX" and token.pos_ != 'PROPN' and token.pos_ != 'PRON':
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

    # get properties (for each token directly bound to the result)
    doc_properties = parser_getProperties(children, predicate)

    # search operators in properties (advmod)
    for dp in doc_properties:
        if dp.entity.entity_type == "generic" and dp.entity.upos == "PART":
            op = parser_ccToOperator(dp.entity.token)
            if op and op != TKOperator.AND: doc_properties.remove(dp) # not?
        
    # get marker
    marker = next((s for s in children if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector and not predicate: 
        tkMarker = TKMarker(marker_type=marker.dep_, lemma=marker.lemma_, vector=marker.vector)    

    # update marker
    if tkMarker == None and token.dep_ == "iobj":
        newMarker = nlp.tokenizer("to")
        tkMarker = TKMarker(lemma="to", vector=newMarker.vector if newMarker.has_vector else [])

    # get auxiliary
    aux = next((s for s in children if s.pos_ == "AUX"), None)
    if aux and aux.has_vector:
        tkAux = TKAux(lemma=aux.lemma_, vector=aux.vector)

    # primary entity (from token)
    primaryEntity: TKFullEntity = TKFullEntity(entity=tkMeaning, op=op, token=token.text, aux=tkAux, marker=tkMarker, properties=doc_properties)

    # get related entities
    for c in [cc for cc in conjuncts if cc.head == token]:
        relatedEntity = parser_getRelatedEntity(c, predicate)
        if relatedEntity: primaryEntity.conjuncts.append(relatedEntity)

    return primaryEntity

# custom comparator for indirects
def parser_indirectComparator(a: Token, b: Token):

    _highPrioDep = ['xcomp', 'ccomp', 'advcl', 'acl']

    if a.dep_ in _highPrioDep and b.dep_ not in _highPrioDep:
        return 1
    elif a.dep_ not in _highPrioDep and b.dep_ in _highPrioDep:
        return -1
    else:
        return (a.dep_ > b.dep_) - (a.dep_ < b.dep_)

# (ONGOING) get all indirect objects (cycling remaining tokens)
def parser_getIndirects(tokens: list[Token], quotes: list[tuple[list[Token], list[Token], Span]] = None) -> list[TKFullEntity]: 

    # initialize result
    indirectFullEntities: list[TKFullEntity] = list()
    usedTokens: list[Token] = list()

    for t in tokens:
        if t in usedTokens: continue

        # reset indirect entity
        indirectEntity = None

        # case dative (can be a name [take the entity] or a prep [take the first child])
        # oblique (expect a case or marker)
        if t.dep_ == "obl" or t.dep_ == "obl:tmod":
            indirectEntity = parser_getFullEntity(t, False)
        # indirect object (you give YOU something)
        elif t.dep_ == "iobj": 
            indirectEntity = parser_getFullEntity(t, False)
        # clausal complements
        elif t.dep_ == "xcomp" \
            or t.dep_ == "ccomp" \
            or t.dep_ == "advcl" \
            or t.dep_ == "acl" \
            or t.dep_ == "acl:relcl" \
            or t.dep_ == "parataxis":

            forcedSubject: Token = None
            for q in quotes: 
                if t.text in (c.text for c in list(q.content)): 
                    forcedSubject = q.speaker[0] if len(q.speaker) > 0 else None
                continue
            indirectEntity = parser_parseSubordinate(t, forcedSubject)

        # if found 
        if indirectEntity: 
            # mark already used
            usedTokens.extend(t.children)
            usedTokens.extend(t.subtree)
            
            # append indirect
            indirectFullEntities.append(indirectEntity)

    return indirectFullEntities

# parse a subordinate clause
def parser_parseSubordinate(token: Token, forcedSubject: Token = None) -> TKFullEntity:

    # initialize variables
    childrenTokens = list(token.children)
    tkMarker: TKMarker = None
    result: TKFullEntity = None

    # get indirect marker 
    marker = next((s for s in childrenTokens if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(marker_type=marker.dep_, lemma=marker.lemma_, vector=marker.vector, connect_clause=token.dep_)    

    # update marker
    if marker == None: 
        tkMarker = TKMarker(connect_clause=token.dep_)

    tokenSubtree = [t for t in token.subtree if t != marker]

    tkStatement = parser_parseSentence(tokenSubtree, clause_type=TKClause.SUBORDINATE, forcedSubject=forcedSubject)
    if tkStatement: result = TKFullEntity(entity=tkStatement, token=None, aux=None, marker=tkMarker, properties=[], conjuncts=[], op=TKOperator.AND)
    
    return result

# (ONGOING) parse sentence (simple or compoung)
def parser_parseSentence(inputTokens: list[Token], clause_type: TKClause = TKClause.MAIN, forcedSubject: Token = None) -> TKStatement: 
    global _talker

    # get root of the sub statement
    subStatement = " ".join([t.text for t in inputTokens])
    doc = nlp_stanza(subStatement)
    roots = [s for s in list(doc) if s.dep_ == "root"]
    if len(roots) > 0: 
        root = next((t for t in inputTokens if t.text == roots[0].text), None)
        if root == None: return None
    else:
        return None
    
    # check for quotes
    quotes = list(textacy.extract.triples.direct_quotations(doc))

    # parse the original subtree
    tokens = list(root.subtree)
    subtreeNoSelf = [t for t in tokens if t != root]
   
    # ------------------------------
    # root is predicate
    # ------------------------------
    # the root is a verb or an adjective, assign (auxiliaries are properties)
    tkPredicate = parser_getFullEntity(root, True)

    # ------------------------------
    # search subject (first csubj, then nsubj)
    # ------------------------------
    tkSubject = None
    subjectToken = next((s for s in tokens if (s.dep_ == "nsubj" or s.dep_ == "nsubj:pass") and s.head == root), None)
    if subjectToken: tkSubject = parser_getFullEntity(subjectToken, False)
    else: 
        subjectToken = next((s for s in tokens if (s.dep_ == "csubj") and s.head == root), None)
        if subjectToken: tkSubject = parser_parseSubordinate(subjectToken)

    # ------------------------------
    # search direct
    # ------------------------------
    tkDirect = None
    directToken = next((s for s in tokens if s.dep_ == "obj" and s.head == root), None)
    if directToken: tkDirect = parser_getFullEntity(directToken, False)

    # ------------------------------
    # search indirect (only on root's children)
    # ------------------------------
    indirectEntities = parser_getIndirects(subtreeNoSelf, quotes)

    # main statement
    tkMain = TKStatement()
 
    # ----------------------------------------
    # always create source and target entities
    # ----------------------------------------
    # manage quotes
    if (forcedSubject):
        forceSubjectEntity = parser_getFullEntity(forcedSubject, False)
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

# (DONE) core internal recursive function to parse a list of token into a TKStatements
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
        sentence = parser_parseSentence(list(roots[0].subtree), clause_type=TKClause.MAIN)
        statements.append(sentence)

    return statements

# --------------------------------------------------------------
# (DONE) MAIN entry point to parse an input text
# --------------------------------------------------------------
def parser(tokens: str, talker: MEMStakeholder, tokeniko: MEMStakeholder, context: MEMContext = None, ollamaClient: OllamaClient = None) -> dict[str, TKLLC | TKStatements]:
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

# (DONE) wrap the displacy dep diagram
def parser_diagram(tokens: str) -> str:
    
    # spacy parse
    doc = nlp_stanza(tokens)
    diagram = displacy.render(doc, style = "dep")

    html = '<html><body>' + diagram + '</body></html>'

    return html
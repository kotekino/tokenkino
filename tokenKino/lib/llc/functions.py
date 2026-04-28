from typing import Any
from unittest import result
import copy
from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Token
import stanza
import spacy_stanza
import numpy as np
from lib.core.entities import TKLLC, EntityPayload, TKClause, TKEntity, TKEntityReference, TKLLCContent, TKLLCItem, TKMarker, TKFlatStatements, TKFullEntity, TKContext, TKDictionary, TKGeneric, TKName, TKOperator, TKSpaceTimeMap, TKStatement, TKStatements
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper

# TODO: 
# manage articles
# manage copula verbs (be, seem, appear, become, etc.)
# manage operators (llc_ccToOperator)
# flat compiler
# test against every sentence from UD2

# define constants
_SIMILAR_RESULTS: int = 5
_UNABLE_TO_PROCESS: str = "Unable to process the sentence"
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)

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

# (TODO) get operator corresponding to cc
def llc_ccToOperator(token: Token) -> TKOperator:
    operator: TKOperator = TKOperator.AND # default

    newDoc = nlp.tokenizer(token.lemma_)
    query_vector = np.asarray([newDoc[0].vector])
    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SIMILAR_RESULTS)
    similar_keys = most_similar[0][0]
    for key in similar_keys:
        fallback_lemma = nlp.vocab.strings[key].lower()
    # todo: transform a cc

    return operator

# (DONE) get properties
def llc_getProperties(tokens: list[Token]) -> tuple[list[TKFullEntity], list[Token]]:

    # initialize usedTokens
    usedTokens: list[Token] = list()

    doc_properties: list[TKFullEntity] = []
    property: tuple[list[TKFullEntity], list[Token]] = [list(),list()]

    for t in (tt for tt in tokens if tt not in usedTokens):
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

    # result
    result: TKFullEntity = None

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
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SIMILAR_RESULTS)
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
    for c in conjuncts:
        conjunctEntity: TKFullEntity = llc_getRelatedEntity(c, list(s for s in subtree if s not in usedTokens), predicate)
        if conjunctEntity[0]:
            primaryEntity.conjuncts.append(conjunctEntity[0])
            usedTokens += conjunctEntity[1]

    return [primaryEntity, usedTokens]

# (ONGOING) get all indirect objects (cycling remaining tokens)
def llc_getIndirects(tokens: list[Token]) -> list[TKFullEntity]: 
    
    # initialize usedTokens
    usedTokens: list[Token] = list()

    # initialize result
    indirectFullEntities: list[TKFullEntity] = list()

    for t in (tt for tt in tokens if tt not in usedTokens):
        # reset indirect
        indirectToken: Token = None
        indirectEntities: tuple[list[TKFullEntity], list[Token]] = [list(),list()]

        # case dative (can be a name [take the entity] or a prep [take the first child])
        # oblique (expect a case or marker)
        if t.dep_ == "obl":
            indirectToken = t
            availableTokens = [s for s in tokens if s not in usedTokens]
            indirectEntity = llc_getFullEntity(indirectToken, availableTokens)
            usedTokens += indirectEntity[1] # get used tokens   
        # indirect object (you give YOU something)
        elif t.dep_ == "iobj":
            indirectToken = t
            availableTokens = [s for s in tokens if s not in usedTokens]
            indirectEntity = llc_getFullEntity(indirectToken, availableTokens)
            usedTokens += indirectEntity[1] # get used tokens
        # clausal complements
        if t.dep_ == "xcomp" or t.dep_ == "ccomp":
            indirectToken = t
            availableTokens = [s for s in tokens if s not in usedTokens]
            childrenTokens = [s for s in list(indirectToken.children) if s in availableTokens]

            # get marker 
            tkMarker: TKMarker = None
            marker = next((s for s in childrenTokens if s not in usedTokens and (s.dep_ == "case" or s.dep_ == "mark")), None)
            if marker and marker.has_vector: 
                tkMarker = TKMarker(type=marker.dep_, lemma=marker.lemma_, vector=marker.vector)    
                usedTokens.append(marker)
            
            # update remaining tokens
            subtreeTokens = [s for s in list(indirectToken.subtree) if s in availableTokens and s not in usedTokens]

            statement = llc_parseSentence(indirectToken, subtreeTokens, clause_type=TKClause.SUBORDINATE)
            usedTokens += statement[1] # get used tokens
            if statement[0]:
                # todo: manage sentences related by conj
                indirectEntities = [[TKFullEntity(entity=statement[0], marker=tkMarker, properties=[], conjunct=None, op=TKOperator.AND)],usedTokens]

        # if found 
        if indirectToken: 
            indirectFullEntities.append(indirectEntities[0])

    return [indirectFullEntities, usedTokens]

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
    subjectToken = next((s for s in tokens if (s.dep_ == "nsubj") and s.head == root), None)
    if subjectToken:
        tkSubject = llc_getFullEntity(subjectToken, tokens)
        usedTokens += tkSubject[1] # get used tokens
        tokens = [t for t in tokens if t not in usedTokens] # remove used tokens
    else:
        subjectToken = next((s for s in tokens if (s.dep_ == "csubj") and s.head == root), None)
        if subjectToken:
            subtreeTokens = [s for s in list(subjectToken.subtree) if s in tokens]
            tkSubject = llc_parseSentence(subjectToken, subtreeTokens, clause_type=TKClause.SUBORDINATE)
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
        indirectId = tkMain.add_indirect(payload=it[0].entity, op=it[0].op, marker=it[0].marker, conjuncts=it[0].conjuncts)
        # add properties
        if len(it[0].properties) > 0: tkMain.add_properties(it[0].properties, indirectId)

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

# (DONE) pre parser based on Phi-3 via Ollama: fix the sentences not understandable by llc
def llc_preparser(tokens: str) -> TKStatements | None:

    # no ollama available
    if not _ollamaClient: raise Exception(_UNABLE_TO_PROCESS)

    # Prompt strutturato a blocchi logici (senza negazioni complesse)
    systemPrompt = """You are a strict syntax normalizer.
    Your ONLY job is to rewrite elliptical phrases, exclamations, greetings, or short answers into explicit Subject-Verb-Object (SVO) sentences.

    Rules:
    - Keep the exact original meaning.
    - Maintain the original grammatical person. Assume 1st person singular ('I') for general exclamations or greetings unless stated otherwise.
    - Output ONLY the final sentence. Absolutely no explanations, no notes, and do not write "You are expressing...".

    Examples:
    Input: 'Silence!'
    Output: 'You must stay silent.'

    Input: 'Exactly.'
    Output: 'That is exactly right.'

    Input: 'mornin guys'
    Output: 'I wish you a good morning.'

    Input: 'oh god'
    Output: 'I am shocked.'

    Input: 'What a cold day!'
    Output: 'This day is cold.'
    """

    # ask ollama to rephrase
    user_prompt = f"Input: '{tokens}'\nOutput:"

    # get the answer
    response = _ollamaClient.generate(
        model='phi3', 
        prompt=user_prompt, 
        system=systemPrompt,
        options={
            'temperature': 0.0,
            'top_k': 10,
            'top_p': 0.5
        }
    )

    # normalized text
    normalized_text = response['response'].strip().strip("'").strip('"')

    # check semantic value via spacy
    # CRITICAL HERE: remove any noise with 100% confidence
    
    unable: bool = False
    if unable: return None

    # parse the rearranged sentence and return the TKStatements result 
    return llc_core(normalized_text)

# --------------------------------------------------------------
# FLAT compiler: transform TKStatements into a flat list of TKLLCItem (with TKEntity as predicate) and TKEntity as entities (subjects, direct and indirect objects)
# --------------------------------------------------------------

# get content
def llc_getContent(stat: TKStatement) -> tuple[list[TKLLCItem], list[TKEntity]]:

    # deep copy
    copyStat: TKStatement = copy.deepcopy(stat)

    # initialize result
    clauses: list[TKLLCItem] = list()
    entities: list[TKEntity] = copyStat.entities

    # main clause content (from deepcopy)
    mainContent: TKLLCContent = TKLLCContent(subject=copyStat.subject, predicate=copyStat.predicate, direct=copyStat.direct, indirects=copyStat.indirects)

    # add main clause to items
    mainClause: TKLLCItem = TKLLCItem(op=TKOperator.AND, content=mainContent)
    clauses.append(mainClause)

    # coordinated clauses (add conjunct as new clause, remove the conjunct)
    if len(stat.predicate.conjuncts) > 0:
        
        # remove conjuncts from the main predicate and from the entities
        mainClause.content.predicate.conjuncts = None 

        # initialize offset for entities
        offsetEntities: int = len(copyStat.entities)    

        for c in list(stat.predicate.conjuncts):
            # get conjunct statement from entities
            conjunctStatement = next((s for s in stat.entities if s.id == c.id), None)

            # remove conjunct statement from entities
            entities.remove(next((e for e in entities if e.id == c.id), None))

            # call the get predicate conjunct function
            llcItems, llcEntities = llc_getPredicateConjunct(c, conjunctStatement, offsetEntities)
            if llcItems: clauses.extend(llcItems)
            if llcEntities: entities.extend(llcEntities)

    # multiple subjects

    # return result
    return [clauses, entities]

# get predicate conjunct content (recursive function to manage multiple levels of coordination)
def llc_getPredicateConjunct(reference: TKEntityReference, conjunct: TKEntity, parentOffset: int) -> tuple[list[TKLLCItem], list[TKEntity]]:

    # get conjunct statement from entities

    if not isinstance(conjunct.payload, TKStatement): return [None, list()] # safety check
    originalStatement: TKStatement = copy.deepcopy(conjunct.payload)
    
    # initialize result
    clauses: list[TKLLCItem] = list()
    additionalEntities: list[TKEntity] =  list()
    
    # assign result values with the id offset for entities    
    if originalStatement.subject: 
        subEntity = next((s for s in originalStatement.entities if s.id == originalStatement.subject.id), None)
        if subEntity: additionalEntities.append(TKEntity(id=originalStatement.subject.id + parentOffset, payload=subEntity.payload, op=originalStatement.subject.op, marker=originalStatement.subject.marker, conjuncts=originalStatement.subject.conjuncts))
    if originalStatement.predicate: 
        predEntity = next((s for s in originalStatement.entities if s.id == originalStatement.predicate.id), None)
        if predEntity: additionalEntities.append(TKEntity(id=originalStatement.predicate.id + parentOffset, payload=predEntity.payload, op=originalStatement.predicate.op, marker=originalStatement.predicate.marker, conjuncts=originalStatement.predicate.conjuncts))
    if originalStatement.direct: 
        directEntity = next((s for s in originalStatement.entities if s.id == originalStatement.direct.id), None)
        if directEntity: additionalEntities.append(TKEntity(id=originalStatement.direct.id + parentOffset, payload=directEntity.payload, op=originalStatement.direct.op, marker=originalStatement.direct.marker, conjuncts=originalStatement.direct.conjuncts))
    if originalStatement.indirects: 
        for i in originalStatement.indirects:
            indirectEntity = next((s for s in originalStatement.entities if s.id == i.id), list())
            if indirectEntity: additionalEntities.append(TKEntity(id=i.id + parentOffset, payload=indirectEntity.payload, op=i.op, marker=i.marker, conjuncts=i.conjuncts))

    # coordinated clause content (copy values)
    subject = TKEntityReference(id=originalStatement.subject.id + parentOffset, op=originalStatement.subject.op, marker=originalStatement.subject.marker, conjuncts=originalStatement.subject.conjuncts) if originalStatement.subject else None
    predicate = TKEntityReference(id=originalStatement.predicate.id + parentOffset, op=originalStatement.predicate.op, marker=originalStatement.predicate.marker, conjuncts=originalStatement.predicate.conjuncts) if originalStatement.predicate else None
    direct = TKEntityReference(id=originalStatement.direct.id + parentOffset, op=originalStatement.direct.op, marker=originalStatement.direct.marker, conjuncts=originalStatement.direct.conjuncts) if originalStatement.direct else None
    indirect = [TKEntityReference(id=i.id + parentOffset, op=i.op, marker=i.marker, conjuncts=i.conjuncts) for i in originalStatement.indirects] if len(originalStatement.indirects) > 0 else list()
    spacetime: TKSpaceTimeMap = None

    mainContent = TKLLCContent(subject=subject, predicate=predicate, direct=direct, indirects=indirect, spacetime=spacetime)
    mainClause = TKLLCItem(op=reference.op, content=mainContent)
    clauses.append(mainClause)

    if len(reference.conjuncts) > 0 :
        predicate.conjuncts = None
        recursiveOffsetEntities: int = len(originalStatement.entities) + parentOffset
        for c in list(reference.conjuncts):
            conjunctStatement = next((s for s in originalStatement.entities if s.id == c.id), None)
            llcItem, llcEntities = llc_getPredicateConjunct(c, conjunctStatement, recursiveOffsetEntities)
            clauses.append(llcItem)
            additionalEntities.extend(llcEntities)            
    
    return [clauses, additionalEntities]

# (DONE) main flat function
def llc_flat(tkStatements: TKStatements) -> TKLLC | None:
    
    entities: list[TKEntity] = list()
    items: list[TKLLCItem] = list()

    # for each statement, flatten it and add to the result
    for stat in tkStatements:
        llcstat = llc_getContent(stat)
        items.extend(llcstat[0])
        entities.extend(llcstat[1])

    result = TKLLC(items=items, entities=entities)
    return result

# --------------------------------------------------------------
# (DONE) MAIN entry point to parse an input text
# --------------------------------------------------------------
def llc(tokens: str, context: TKContext = None, ollamaClient: OllamaClient = None) -> dict[str, TKLLC | TKStatements]:

    # assign variables
    _context = context
    _ollamaClient = ollamaClient

    # spacy parse
    doc = nlp_stanza(tokens)

    # get all tokens
    tkStatements: TKStatements = llc_core(list(doc))

    # flat statements
    tkLLC: TKLLC = llc_flat(tkStatements)

    # return statement
    return {
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
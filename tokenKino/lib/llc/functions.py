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
from lib.core.entities import TKLLC, EntityPayload, LLCItemPayload, TKClause, TKEntity, TKEntityReference, TKLLCContent, TKLLCItem, TKLLEntity, TKLLEntityReference, TKLLProperties, TKLLSpacetime, TKLLSpacetimeMap, TKMarker, TKFullEntity, TKContext, TKDictionary, TKGeneric, TKName, TKOperator, TKStatement, TKStatements
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper

# TODO: 
# GOING manage spacetime (temporal and spatial modifiers)
# GOING manage compiler (flat and recursive)
# manage parataxis (and other non-standard coordination)
# manage articles
# manage det
# manage copula verbs (be, seem, appear, become, etc.)
# manage plurality
# test against every sentence from UD2

# define constants
_ERRORS_UNABLE_TO_PROCESS: str = "Unable to process the sentence"
_SPACY_MAX_SIMILAR_RESULTS: int = 5
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)
_OPERATORS_BASE_ANCHORS = {"and": TKOperator.AND, "or": TKOperator.OR, "not": TKOperator.NOT}
_OPERATORS_SIMILARITY_THRESHOLD: float = 0.7 # threshold for fuzzy logic in operator mapping

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
    subjectToken = next((s for s in tokens if (s.dep_ == "nsubj") and s.head == root), None)
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

# (DONE) pre parser based on Phi-3 via Ollama: fix the sentences not understandable by llc
def llc_preparser(tokens: str) -> TKStatements | None:

    # no ollama available
    if not _ollamaClient: raise Exception(_ERRORS_UNABLE_TO_PROCESS)

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
def llc_evaluateReference(ref: TKEntityReference, entities: list[TKEntity], parentOffset: int = 0) -> TKLLEntityReference:
    properties: list[TKLLEntityReference] = list()
    return TKLLEntityReference(id=ref.id + parentOffset, properties=properties)

# create a TKLLCContent object from a TKStatement
def llc_evaluateContent(stat: TKStatement, parentOffset: int = 0) -> tuple[LLCItemPayload, list[TKLLEntity]]:

    entities: list[TKLLEntity] = list()
    additionalItems: list[TKLLCItem] = list()

    predEntity = next((e for e in stat.entities if stat.predicate and e.id == stat.predicate.id), None)
    subjEntity = next((e for e in stat.entities if stat.subject and e.id == stat.subject.id), None)
    dirEntity = next((e for e in stat.entities if stat.direct and e.id == stat.direct.id), None)
    indEntities = [e for e in stat.entities if e.id in [i.id for i in stat.indirects]]

    properties = TKLLProperties()

    predicate = None
    subject = None
    direct = None
    indirects: list[TKLLEntityReference] = list()

    # ---------------------------------------------
    # predicate it cant be a statement
    # ---------------------------------------------
    predicate = llc_evaluateReference(stat.predicate, stat.entities, parentOffset) if predEntity else None
    
    # manage coordinate clauses
    if len(stat.predicate.conjuncts) > 0 :
        recursiveOffsetEntities: int = len(stat.entities) - len(stat.predicate.conjuncts) + parentOffset
        parentOffset -= len(stat.predicate.conjuncts) # update offset
        for c in list(stat.predicate.conjuncts):
            conjunctStatement = next((s for s in stat.entities if s.id == c.id), None)
            additionalItems, additionalEntities = llc_getProcessStatement(conjunctStatement.payload, c, recursiveOffsetEntities)
            entities.extend(additionalEntities)
            parentOffset += len(additionalEntities)

    # subject
    if subjEntity and subjEntity.payload.entity_type == "statement": 
        # exclude statements
        parentOffset -= 1
    else: 
        subject = llc_evaluateReference(stat.subject, stat.entities, parentOffset) if subjEntity else None

    # direct
    if dirEntity and dirEntity.payload.entity_type == "statement": 
        # exclude statements not affecting time and space
        parentOffset -= 1
    else: 
        direct = llc_evaluateReference(stat.direct, stat.entities, parentOffset) if dirEntity else None

    # indirects
    for e in indEntities:
        if e.payload.entity_type == "statement": 
            # exclude statements
            parentOffset -= 1
        else: 
            indirects.append(llc_evaluateReference(e, stat.entities, parentOffset))
    
    # set content
    content = TKLLCContent(properties=properties, subject=subject, predicate=predicate, direct=direct, indirects=indirects)
    
    # check additional items
    if len(additionalItems) > 0:
        subItems: list[TKLLCItem] = list()
        subContent = TKLLCContent(properties=properties, subject=subject, predicate=predicate, direct=direct, indirects=indirects)
        subItems.append(TKLLCItem(op=TKOperator.AND, content=subContent))
        subItems.extend(additionalItems)
        return subItems, entities
    else:
        return content, entities

# create an tkllentity from tkentity
def llc_initializeEntity(ent: TKEntity, parentOffset: int = 0) -> list[TKLLEntity]:

    id = ent.id + parentOffset
    token = ''
    semantic: list[float] = list()
    spacetime: TKLLSpacetime = TKLLSpacetime()

    if ent.payload.entity_type == "dictionary": 
        token = ent.payload.word
        semantic: list[float] = ent.payload.vector
    elif ent.payload.entity_type == "name": 
        token = ent.payload.name
    elif ent.payload.entity_type == "place": 
        token = ent.payload.name
    elif ent.payload.entity_type == "generic": 
        token = ent.payload.token
    elif ent.payload.entity_type == "statement":
        # excluded statements
        return list()
        # stat: TKStatement = ent.payload
        # return llc_evaluateEntities(stat.entities)    

    return [TKLLEntity(id=id, tokens=token, semantic_vector=semantic, spacetime=spacetime)]

# create a list of tkllentity from a list of tkentity
def llc_initializeEntities(ents: list[TKEntity], parentOffset: int = 0) -> list[TKLLEntity]:
    result: list[TKLLEntity] = []
    for e in ents:
        subents = llc_initializeEntity(e, parentOffset)
        if len(subents) > 0: result.extend(subents) 
        else: parentOffset -= 1 # if the entity is a statement, it doesn't generate an entity but it generates an offset for the next entities
    return result

# get predicate conjunct content (recursive function to manage multiple levels of coordination)
def llc_getProcessStatement(statement: TKStatement, reference: TKEntityReference = None, parentOffset: int = 0) -> tuple[list[TKLLCItem], list[TKEntity]]:

    originalStatement: TKStatement = copy.deepcopy(statement)
    
    # initialize result
    clauses: list[TKLLCItem] = list()
    entities: list[TKLLEntity] = llc_initializeEntities(originalStatement.entities, parentOffset) # exclude statements, managed later
    op = reference.op if reference else TKOperator.AND

    mainContent, additionalEntities = llc_evaluateContent(originalStatement, parentOffset) # exclude statements, managed later
    mainClause = TKLLCItem(op=op, content=mainContent)        
    clauses.append(mainClause)
    entities.extend(additionalEntities)

    return [clauses, entities]

# (DOING) build spacetime map from entities and normalize the spacetime of the entities in the map (-1, 1)
def llc_normalizeSpacetimeMap(entities: list[TKLLEntity]) -> TKLLSpacetimeMap:
    spacetimeMap: TKLLSpacetimeMap = TKLLSpacetimeMap()

    # get bounds
    minT = min(e.spacetime.position[0] - e.spacetime.size[0] / 2 for e in entities) if len(entities) > 0 else 0
    maxT = max(e.spacetime.position[0] + e.spacetime.size[0] / 2 for e in entities) if len(entities) > 0 else 0
    minX = min(e.spacetime.position[1] - e.spacetime.size[1] / 2 for e in entities) if len(entities) > 0 else 0
    maxX = max(e.spacetime.position[1] + e.spacetime.size[1] / 2 for e in entities) if len(entities) > 0 else 0
    minY = min(e.spacetime.position[2] - e.spacetime.size[2] / 2 for e in entities) if len(entities) > 0 else 0
    maxY = max(e.spacetime.position[2] + e.spacetime.size[2] / 2 for e in entities) if len(entities) > 0 else 0
    minZ = min(e.spacetime.position[3] - e.spacetime.size[3] / 2 for e in entities) if len(entities) > 0 else 0
    maxZ = max(e.spacetime.position[3] + e.spacetime.size[3] / 2 for e in entities) if len(entities) > 0 else 0

    # same scale for x, y, z
    minSpace = min(minX, minY, minZ)
    maxSpace = max(maxX, maxY, maxZ)

    # normalize function (from - x to x => from -1 to 1)
    def normalize(value: float, min: float, max: float) -> float:
        if max - min == 0: return 0
        return (value - min) / (max - min) * 2 - 1

    spacetimeMap.tbounds = [normalize(minT, minT, maxT), normalize(maxT, minT, maxT)]
    spacetimeMap.xbounds = [normalize(minX, minSpace, maxSpace), normalize(maxX, minSpace, maxSpace)]
    spacetimeMap.ybounds = [normalize(minY, minSpace, maxSpace), normalize(maxY, minSpace, maxSpace)]
    spacetimeMap.zbounds = [normalize(minZ, minSpace, maxSpace), normalize(maxZ, minSpace, maxSpace)]

    # recalculate the spacetime of the entities in the map
    for e in entities:
        e.spacetime.position[0] = normalize(e.spacetime.position[0], minT, maxT)
        e.spacetime.position[1] = normalize(e.spacetime.position[1], minSpace, maxSpace)
        e.spacetime.position[2] = normalize(e.spacetime.position[2], minSpace, maxSpace)
        e.spacetime.position[3] = normalize(e.spacetime.position[3], minSpace, maxSpace)
        e.spacetime.size[0] = normalize(e.spacetime.size[0], minT, maxT)
        e.spacetime.size[1] = normalize(e.spacetime.size[1], minSpace, maxSpace)
        e.spacetime.size[2] = normalize(e.spacetime.size[2], minSpace, maxSpace)
        e.spacetime.size[3] = normalize(e.spacetime.size[3], minSpace, maxSpace)

    return spacetimeMap, entities

# (DONE) main flat function
def llc_flat(tkStatements: TKStatements) -> TKLLC | None:
    
    entities: list[TKLLEntity] = list()
    items: list[TKLLCItem] = list()

    # for each statement, flatten it and add to the result
    parentOffset: int = 0
    for stat in tkStatements:
        i, e = llc_getProcessStatement(stat, None, parentOffset)
        items.extend(i)
        entities.extend(e)
        parentOffset += len(e)

    # spacetimemap: build the spacetime map relative to the context of the statements
    spacetimemap, entities = llc_normalizeSpacetimeMap(entities)

    # return result
    result = TKLLC(items=items, entities=entities, map=spacetimemap)
    return result

# (DOING) parse content object (recursively)
def llc_raw_recursive(content: LLCItemPayload, entities: list[TKLLEntity]) -> str:
    
    result: str = ""
    if isinstance(content, TKLLCContent):

        subject = next((e.tokens for e in entities if e.id == content.subject.id), '') if content.subject else ''
        predicate = next((e.tokens for e in entities if e.id == content.predicate.id), '') if content.predicate else ''
        direct = next((e.tokens for e in entities if e.id == content.direct.id), '') if content.direct else ''
        indirects = ' '.join([next((e.tokens for e in entities if e.id == i.id), '') for i in content.indirects]) if content.indirects else ''

        result = f"{subject} {predicate} {direct} {indirects}"
    elif isinstance(content, list):
        for item in content:
            result += f" {item.op.value} ({llc_raw_recursive(item.content, entities)})"

    return result.strip()

# (DOING) get raw output from TKLLC
def llc_raw(tkLLC: TKLLC) -> str:

    result: str = ""
    for item in tkLLC.items:
        result += item.op + ' ' + llc_raw_recursive(item.content, tkLLC.entities)

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
# ------------------------------------------------------------------------------------------------
# FLAT compiler V2
# properties
# conjunct management
# subordinates management
# ------------------------------------------------------------------------------------------------

# main flat function
import copy

import spacy

from lib.core.tk import TKClauseType, TKEntity, TKEntityReference, TKMarker, TKOperator, TKStatement, TKStatements
from lib.core.tkllc import LLCItemPayload, TKLLEntity, TKLLEntityMap, TKLLEntityMapReference, TKLLC, TKLLCContent, TKLLCItem, TKLLEntityProperty, TKLLEntityReference, TKLLProperties
from lib.llc.constants import _PRONOUNS_BASE_ANCHORS, _SPACY_MODEL, _SUBORDINATE_TYPE_BASE_ANCHORS, _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD

# globals
_entities: list[TKLLEntityMap] = []
_statements: list[TKLLCContent] = []
nlp = spacy.load(_SPACY_MODEL)

# ------------------------------------------------------------------------------------------------
# ENTITIES
# ------------------------------------------------------------------------------------------------

# get a single entity from the tk entity, and convert it to a TKLLEntity
def compiler_getEntity(ent: TKEntity, id: int) -> TKLLEntity:

    token = ''
    semantic: list[float] = list()
    entity_type = ent.payload.entity_type

    if ent.payload.entity_type == "dictionary": 
        token = ent.payload.word
        semantic: list[float] = ent.payload.vector
    elif ent.payload.entity_type == "name": 
        token = ent.payload.name
    elif ent.payload.entity_type == "place": 
        token = ent.payload.name
    elif ent.payload.entity_type == "meta":
        token = ent.payload.who.name
    elif ent.payload.entity_type == "num":
        token = str(ent.payload.value)
    elif ent.payload.entity_type == "pronoun":
        token = ent.payload.lemma
        semantic: list[float] = ent.payload.vector
    elif ent.payload.entity_type == "generic": 
        token = ent.payload.token

    return TKLLEntity(id=id, token=token, semantic_vector=semantic, entity_type=entity_type)

# append entity if new, or update reference if already present
def compiler_appendEntity(ent: TKLLEntity, inputEntRef: list[TKLLEntityMapReference], ents: list[TKLLEntityMap]):
    if len([e for e in ents if e.entity.token == ent.token and e.entity.entity_type == ent.entity_type]) == 0:
        ents.append(TKLLEntityMap(entity=ent, ref=inputEntRef))
    else:
        # update the reference
        refEnt = next((e for e in ents if e.entity.token == ent.token and e.entity.entity_type == ent.entity_type))
        refEnt.ref.extend(inputEntRef)

# get all the entities
def compiler_getEntities(statement: TKStatement, statementIdx: int = 1, statementId: int = 0, offset: int = 0) -> list[TKLLEntityMap]:
    entities: list[TKLLEntityMap] = [] 

    for e in statement.entities:
        if e.payload.entity_type == 'statement':
            newEnts = compiler_getEntities(e.payload, statementIdx, e.id, offset=len(entities))
            for ne in newEnts:
                compiler_appendEntity(ent=ne.entity, inputEntRef=ne.ref, ents=entities)
        else:
            id = len(entities) + offset + 1
            # get referenced entity
            refEntity = e
            if e.referenceId > 0:
                refEntity = next(en for en in statement.entities if en.id == e.referenceId)
                
            entity = compiler_getEntity(ent=refEntity, id=id)
            compiler_appendEntity(ent=entity, inputEntRef=[TKLLEntityMapReference(inputStatementIdx=statementIdx, inputStatementId=statementId, inputEntityId=e.id)], ents=entities)

    return entities

# search entities references by pronoun
def compiler_getEntitiesByPronoun(lemma: str) -> int:
    
    resultId: int = None

    lemma = lemma.lower()
    if lemma in _PRONOUNS_BASE_ANCHORS:
        resultId = _PRONOUNS_BASE_ANCHORS[lemma]

    return resultId

# resolve pronouns to the talker and listener of the sentence
def compiler_resolvePronouns(stat: TKStatement) -> TKStatement:

    # resolve pronouns: 
    for e in stat.entities:
        if e.payload.entity_type == "statement":
            compiler_resolvePronouns(e.payload) # recurse
        else:
            if e.payload.entity_type == "pronoun":
                referenceFound = compiler_getEntitiesByPronoun(e.payload.lemma) # relative to the sentence

                # remove reference to pronoun and assign it to the real entity
                if referenceFound:
                    e.referenceId = referenceFound

    return stat

# normalize and reslve all entities
def compiler_resolveEntities(tkStatements: TKStatements) -> list[TKLLEntityMap]: 
    entities: list[TKLLEntityMap] = []
    
    # collect all the entities in the statements, and assign them a unique id
    idx = 1
    for tks in tkStatements:
        # resolve pronouns
        compiler_resolvePronouns(tks)

        # resolve entities
        ents = compiler_getEntities(statement=tks, statementIdx=idx)
        for ne in ents:
            compiler_appendEntity(ent=ne.entity, inputEntRef=ne.ref, ents=entities)
        idx +=1

    # clean entities unused
    
    return entities

# ------------------------------------------------------------------------------------------------
# STATEMENTS
# ------------------------------------------------------------------------------------------------
def compiler_getEntityIdByMap(map: TKLLEntityMapReference) -> int | None:
    global _entities

    for entity_map in _entities:
        if any(
            ref.inputEntityId == map.inputEntityId and
            ref.inputStatementIdx == map.inputStatementIdx and
            ref.inputStatementId == map.inputStatementId
            for ref in entity_map.ref
        ):
            return entity_map.entity.id

    return None

# evaluate reference
def compiler_evaluateReference(ref: TKEntityReference, statementIdx: int, statementId: int, isProperty = False) -> TKLLEntityReference:

    # evaluate marker, op, aux
    marker = ref.marker
    op = ref.op
    aux = ref.aux

    # get properties
    properties: list[TKLLEntityProperty] = list()

    # return result
    map = TKLLEntityMapReference(inputStatementIdx=statementIdx, inputStatementId=statementId, inputEntityId=ref.id)
    return TKLLEntityReference(id=compiler_getEntityIdByMap(map), marker=marker, properties=properties, op=op, aux=aux)

# parse marker: it must take in account the CONTEXT of the marker (todo)
def compiler_parseMarker(marker: TKMarker) -> TKClauseType:

    # if no lemma, return other
    if not marker or not marker.lemma:
        if marker and marker.connect_clause: 
            return marker.connect_clause
        else:
            return TKClauseType.OTHER

    # 0. get doc
    newDoc = nlp.tokenizer(marker.lemma)

    # 1. simple case
    if marker.lemma in _SUBORDINATE_TYPE_BASE_ANCHORS:
        return _SUBORDINATE_TYPE_BASE_ANCHORS[marker.lemma]

    # 2. vector space on the marker
    best_type = TKClauseType.OTHER  
    for anchor_word, sub_type in _SUBORDINATE_TYPE_BASE_ANCHORS.items():
        anchor_lexeme = nlp.vocab[anchor_word]
        
        if newDoc[0].has_vector and anchor_lexeme.has_vector:
            sim = newDoc[0].similarity(anchor_lexeme)
            if sim > _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD:
                best_type = sub_type

    if best_type != TKClauseType.OTHER:
        return best_type

    # 3. parse marker on lemma, then connect_clause then fallback other
    if marker.connect_clause: return marker.connect_clause
    
    # 4. fallback
    return TKClauseType.OTHER

# evaluate subordinate clause
def compiler_evaluateSubordinate(reference: TKEntityReference, statement: TKStatement, statementIdx: int) -> list[TKLLCItem]:
    subordinateType = compiler_parseMarker(reference.marker)
    
    # analyze subordinate to flatten it with an operator and modify properties
    operator: TKOperator = TKOperator.AND
    if subordinateType == TKClauseType.FINAL:
        # finale (imply) -> subject implied to be explicited
        # I do x to obtain y => [hope++] if I do this I obtain y => [hope++] I do this IMPLY I obtain y (same subject)
        # I do x to have you doing y =>[hope++] if I do this you doing y => [hope++] I do this IMPLY you doing y (different subject)
        operator = TKOperator.IMPLY
        
        # increase hope feeling (properties) of the main sentence
        # subProperties.sentiment = sentiment_generate(sentiment=['hope', 'goal'])
    elif subordinateType == TKClauseType.PARATAXIS:
        # can be det, can be imply: todo
        operator = TKOperator.THAT

    elif subordinateType == TKClauseType.CAUSAL:
        # causale (imply) -> simple obvious
        # i do this because I done that => I do this CONV i done that                
        operator = TKOperator.CONV

    elif subordinateType == TKClauseType.HYPOTETIC:
        # ipotetica (imply) -> simple, obvious
        # I do this if you do that => you do that IMPLY (or EQ if only, only if) I do this
        operator = TKOperator.CONV

    elif subordinateType == TKClauseType.TEMPORAL:
        # temporale (timespacemap, IMPLY) -> tricky can imply with a smooth degree
        # I have done this when/after/before I was doing that => I do this T1 and I do this T2 = f(T1)
        # I always do this when I do that => I do this -> I do that (always, often)                
        operator = TKOperator.AND

    elif subordinateType == TKClauseType.LOCATIVE:
        # locativa (timespacemap) -> obvious
        # I do x in S1 and I go to S2 => I do x S1 and I do go S2                
        operator = TKOperator.AND

    elif subordinateType == TKClauseType.CCOMP:
        # explicit subject
        operator = TKOperator.THAT

    elif subordinateType == TKClauseType.ACL:
        operator = TKOperator.THAT

    elif subordinateType == TKClauseType.ACLRELCL:
        operator = TKOperator.THAT

    elif subordinateType == TKClauseType.ADVCL:
        operator = TKOperator.THAT

    elif subordinateType == TKClauseType.XCOMP:
        # no subject: search it in the main statement
        operator = TKOperator.THAT

    else:
        # other means it affects something else, but the operator is AND               
        operator = TKOperator.AND

    result = compiler_evaluateStatement(statement, statementIdx, reference.id, subordinateType, operator)

    return result

# modify content
def compiler_modifyContent(content: LLCItemPayload, rep: tuple[TKOperator, int, TKEntityReference]) -> LLCItemPayload:
    
    # last level
    if isinstance(content, TKLLCContent):
        dupContentSub: TKLLCContent = copy.deepcopy(content)
        if dupContentSub.subject and dupContentSub.subject.id == rep[1]: dupContentSub.subject = rep[2]
        if dupContentSub.direct and dupContentSub.direct.id == rep[1]: dupContentSub.direct = rep[2]       
        for iidx in range(len(dupContentSub.indirects)):
            if dupContentSub.indirects[iidx].id == rep[1]: dupContentSub.indirects[iidx] = rep[2]
    else:
        dupContentSub: list[TKLLCItem] = copy.deepcopy(content)
        for eidx in range(len(dupContentSub)):
            dupContentSub[eidx].content = compiler_modifyContent(dupContentSub[eidx].content, rep)
    
    return dupContentSub

# evaluate coordinate clause
def compiler_evaluateCoordinate(content: LLCItemPayload, replacements: list[tuple[TKOperator, int, TKEntityReference]]) -> LLCItemPayload:
    
    subresult: list[TKLLCItem] = list()
    subresult.append(TKLLCItem(op=TKOperator.AND, content=content))
    
    # reached content
    for rep in replacements:
        dupContent = copy.deepcopy(content)
        dupContent = compiler_modifyContent(dupContent, rep)
        subresult.append(TKLLCItem(op=rep[0], content=dupContent))

    return subresult

# evaluate single statement
def compiler_evaluateStatement(statement: TKStatement, statementIdx: int = 1, statementId: int = 0, clauseType: TKClauseType = TKClauseType.MAIN, operator: TKOperator = TKOperator.AND) -> list[TKLLCItem]:
    result: list[TKLLCItem] = []

    predicate = None
    subject = None
    direct = None
    indirects: list[TKLLEntityReference] = list()

    # ---------------------------------------------
    # predicate it cant be a statement
    # ---------------------------------------------
    predicate = compiler_evaluateReference(statement.predicate, statementIdx, statementId) if statement.predicate else None
    if statement.subject: 
        subject = compiler_evaluateReference(statement.subject, statementIdx, statementId) if statement.subject else None
    if statement.direct: 
        direct = compiler_evaluateReference(statement.direct, statementIdx, statementId) if statement.direct else None
    for indirectReference in statement.indirects:
        indirects.append(compiler_evaluateReference(indirectReference, statementIdx, statementId))

    # get properties
    properties: TKLLProperties = TKLLProperties() 

    # append main content and build item
    mainContent = TKLLCContent(clause_type=clauseType, properties=properties, subject=subject, predicate=predicate, direct=direct, indirects=indirects)

    # ---------------------------------------------
    # subject (manage statements)
    # ---------------------------------------------
    if statement.subject:
        # subordinates
        for subReference in statement.subject.subordinates:
            subordinate = next(i for i in statement.entities if subReference.id == i.id)
            subItems = compiler_evaluateSubordinate(subReference, subordinate.payload, statementIdx)
            result.extend(subItems)
        # coordinates
        replacements=[]
        for coordReference in statement.subject.conjuncts:
            ef = compiler_evaluateReference(coordReference, statementIdx, statementId)
            replacements.append([coordReference.op, subject.id, ef])
            mainContent = compiler_evaluateCoordinate(mainContent, replacements)

    # ---------------------------------------------
    # direct (manage statements)
    # ---------------------------------------------
    if statement.direct:
        # subordinates
        for subReference in statement.direct.subordinates:
            subordinate = next(i for i in statement.entities if subReference.id == i.id)
            subItems = compiler_evaluateSubordinate(subReference, subordinate.payload, statementIdx)
            result.extend(subItems)
        # coordinates
        replacements=[]
        for coordReference in statement.direct.conjuncts:
            ef = compiler_evaluateReference(coordReference, statementIdx, statementId)
            replacements.append([coordReference.op, subject.id, ef])
            mainContent = compiler_evaluateCoordinate(mainContent, replacements)

    # ---------------------------------------------
    # indirects (manage statements)
    # ---------------------------------------------
    for indirectReference in statement.indirects:
        # subordinates
        for subReference in indirectReference.subordinates:
            subordinate = next(i for i in statement.entities if subReference.id == i.id)
            subItems = compiler_evaluateSubordinate(subReference, subordinate.payload, statementIdx)
            result.extend(subItems)
        # coordinates
        replacements=[]
        for coordReference in indirectReference.conjuncts:
            ef = compiler_evaluateReference(coordReference, statementIdx, statementId)
            replacements.append([coordReference.op, subject.id, ef])
            mainContent = compiler_evaluateCoordinate(mainContent, replacements)

    result.insert(0, TKLLCItem(op=operator,content=mainContent))

    # return all statements
    return result

# resolve all statements
def compiler_resolveStatements(tkStatements: TKStatements) -> list[TKLLCItem]:
    result:list[TKLLCContent] = []

    idx = 1
    for tks in tkStatements:
        items = compiler_evaluateStatement(statement=tks, statementIdx=idx)
        result.extend(items)

    return result

# ------------------------------------------------------------------------------------------------
# MAIN METHOD
# ------------------------------------------------------------------------------------------------
def compiler_compile(tkStatements: TKStatements) -> TKLLC | None:
    global _entities, _statements
    result = None
    
    # build new entities
    _entities = compiler_resolveEntities(tkStatements)
    _statements = compiler_resolveStatements(tkStatements)
    
    return TKLLC(items=_statements, entities=[e.entity for e in _entities])
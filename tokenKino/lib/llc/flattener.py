
# ------------------------------------------------------------------------------------------------
# FLAT compiler: transform TKStatements into a flat list of TKLLCItem (with TKEntity as predicate) 
# and TKEntity as entities (subjects, direct and indirect objects)
#
# tasks
# match subjects line 432
# manage spacetime (temporal and spatial modifiers) line 85
# ------------------------------------------------------------------------------------------------
import copy

import spacy
from lib.core.entities import TKLLC, LLCItemPayload, TKClauseType, TKEntity, TKEntityReference, TKLLCContent, TKLLCItem, TKLLEntity, TKLLEntityProperty, TKLLEntityReference, TKLLProperties, TKLLSpacetime, TKLLSpacetimeMap, TKLLUniqueEntity, TKMarker, TKOperator, TKStatement, TKStatements
from lib.llc.constants import _PRONOUNS_BASE_ANCHORS, _SPACY_MODEL, _SUBORDINATE_TYPE_BASE_ANCHORS, _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD
from lib.llc.parser import parser_getFullEntity
from lib.llc.constants import _LISTENER_ID, _TALKER_ID

nlp = spacy.load(_SPACY_MODEL)

# recurse properties of properties and conjunct of properties
def flattener_recurseReferenceProperties(ref: TKEntityReference, parentOffset: int, isProperty = False) -> list[tuple[TKLLEntityReference]]:
    
    # init
    flattenedProperties: list[TKLLEntityReference] = list()

    for p in ref.properties:
        flattenedProperties.append([p.op, TKLLEntityReference(id=p.id + parentOffset, marker=None, properties=list())])
        flattenedProperties.extend(flattener_recurseReferenceProperties(p, parentOffset, True))

    if isProperty:
        for c in ref.conjuncts:
            flattenedProperties.append([c.op, TKLLEntityReference(id=c.id + parentOffset, marker=None, properties=list())])
            flattenedProperties.extend(flattener_recurseReferenceProperties(c, parentOffset, True))
    
    return flattenedProperties

# evaluate reference
def flattener_evaluateReference(ref: TKEntityReference,  parentOffset: int = 0, isProperty = False) -> TKLLEntityReference:
    
    # evaluate marker
    marker = ref.marker

    # recurse
    flattenedProperties = flattener_recurseReferenceProperties(ref, parentOffset, isProperty)
    properties: list[TKLLEntityProperty] = list()

    for fp in flattenedProperties:
        properties.append(TKLLEntityProperty(op=fp[0], reference=fp[1]))
    
    # return result
    return TKLLEntityReference(id=ref.id + parentOffset, marker=marker, properties=properties)

# parse marker: it must take in account the CONTEXT of the marker (todo)
def flattener_parseMarker(marker: TKMarker) -> TKClauseType:

    # parse marker on lemma, then connect_clause then fallback other
    if not marker.lemma: return marker.connect_clause if marker.connect_clause else TKClauseType.OTHER

    # 1. simple case
    if marker.lemma in _SUBORDINATE_TYPE_BASE_ANCHORS:
        return _SUBORDINATE_TYPE_BASE_ANCHORS[marker.lemma]

    # get doc
    newDoc = nlp.tokenizer(marker.lemma)

    # 2. vector space
    best_type = TKClauseType.OTHER  
    for anchor_word, sub_type in _SUBORDINATE_TYPE_BASE_ANCHORS.items():
        anchor_lexeme = nlp.vocab[anchor_word]
        
        if newDoc[0].has_vector and anchor_lexeme.has_vector:
            sim = newDoc[0].similarity(anchor_lexeme)
            if sim > _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD:
                best_type = sub_type

    # 3. threshold check
    return best_type

# create an tkllentity from tkentity
def flattener_initializeEntity(ent: TKEntity, parentOffset: int = 0) -> TKLLEntity:

    id = ent.id + parentOffset
    token = ''
    semantic: list[float] = list()
    spacetime: TKLLSpacetime = TKLLSpacetime()
    entity_type = ent.payload.entity_type
    referenceId = ent.referenceId + parentOffset if ent.referenceId > 0 else 0

    if ent.payload.entity_type == "dictionary": 
        token = ent.payload.word
        semantic: list[float] = ent.payload.vector
    elif ent.payload.entity_type == "name": 
        token = ent.payload.name
    elif ent.payload.entity_type == "place": 
        token = ent.payload.name
    elif ent.payload.entity_type == "meta":
        token = ent.payload.name
    elif ent.payload.entity_type == "pronoun":
        token = ent.payload.lemma
        semantic: list[float] = ent.payload.vector
    elif ent.payload.entity_type == "generic": 
        token = ent.payload.token
    elif ent.payload.entity_type == "statement":
        # excluded statements
        return None

    return TKLLEntity(id=id, referenceId=referenceId, token=token, semantic_vector=semantic, spacetime=spacetime, entity_type=entity_type)

# create a list of tkllentity from a list of tkentity
def flattener_initializeEntities(ents: list[TKEntity], parentOffset: int = 0) -> list[TKLLEntity]:
    result: list[TKLLEntity] = []
    for e in ents:
        subent = flattener_initializeEntity(e, parentOffset)
        if subent: result.append(subent) 
    return result

# create a TKLLCContent object from a TKStatement
def flattener_evaluateContent(stat: TKStatement, clauseType: TKClauseType, properties: TKLLProperties, parentOffset: int = 0) -> tuple[LLCItemPayload, list[TKLLEntity]]:

    entities: list[TKLLEntity] = list()
    additionalItems: list[TKLLCItem] = list()

    predEntity = next((e for e in stat.entities if stat.predicate and e.id == stat.predicate.id), None)
    subjEntity = next((e for e in stat.entities if stat.subject and e.id == stat.subject.id), None)
    dirEntity = next((e for e in stat.entities if stat.direct and e.id == stat.direct.id), None)
    indEntities = [e for e in stat.entities if e.id in [i.id for i in stat.indirects]]

    predicate = None
    subject = None
    direct = None
    indirects: list[TKLLEntityReference] = list()

    # ---------------------------------------------
    # predicate it cant be a statement
    # ---------------------------------------------
    predicate = flattener_evaluateReference(stat.predicate, parentOffset) if predEntity else None

    # ---------------------------------------------
    # subject (manage statements)
    # ---------------------------------------------
    if subjEntity: 
        if subjEntity.payload.entity_type == "statement": 
            # exclude statements: csubj -> find a way to manage it
            parentOffset -= 1
        else: 
            subject = flattener_evaluateReference(stat.subject, parentOffset) if subjEntity else None

    # ---------------------------------------------
    # direct (manage statements)
    # ---------------------------------------------
    if dirEntity: 
        if dirEntity.payload.entity_type == "statement": 
            # exclude statements not affecting time and space
            parentOffset -= 1
        else: 
            direct = flattener_evaluateReference(stat.direct, parentOffset) if dirEntity else None

    # ---------------------------------------------
    # indirects (manage statements)
    # ---------------------------------------------
    
    for indirectReference in stat.indirects:
        indirectEntity = next(i for i in indEntities if i.id == indirectReference.id)
        if indirectEntity.payload.entity_type == "statement": 

            subordinate: TKStatement = indirectEntity.payload
            subordinateType = flattener_parseMarker(indirectReference.marker)
            
            # analyze subordinate to flatten it with an operator and modify properties
            operator: TKOperator = TKOperator.AND
            subProperties = TKLLProperties() # all neutral
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

            elif subordinateType == TKClauseType.XCOMP:
                # no subject: search it in the main statement
                operator = TKOperator.THAT

            else:
                # other means it affects something else, but the operator is AND               
                operator = TKOperator.AND

            ai, ae = flattener_processStatement(subordinate, subordinateType, operator, subProperties, max([e.id for e in stat.entities]) + parentOffset)

            # add properties
            additionalItems.extend(ai)
            entities.extend(ae)

        else: 
            indRef = next(i for i in stat.indirects if indirectReference.id == i.id)
            indirects.append(flattener_evaluateReference(indRef, parentOffset))

    # set content
    content = TKLLCContent(properties=properties, subject=subject, predicate=predicate, direct=direct, indirects=indirects, clause_type=clauseType)
    
    # check additional items
    if len(additionalItems) > 0:
        subItems: list[TKLLCItem] = list()
        subItems.append(TKLLCItem(op=TKOperator.AND, content=content))
        subItems.extend(additionalItems)
        return subItems, entities
    else:
        return content, entities

# modify content
def flattener_modifyContent(content: LLCItemPayload, rep: tuple[TKOperator, int, TKEntityReference]) -> LLCItemPayload:
    
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
            dupContentSub[eidx].content = flattener_modifyContent(dupContentSub[eidx].content, rep)
    
    return dupContentSub

# multiply content 
def flattener_multiplyContent(content: LLCItemPayload, replacements: list[tuple[TKOperator, int, TKEntityReference]]) -> list[TKLLCItem]:
    
    # subresult
    subresult: list[TKLLCItem] = list()
    subresult.append(TKLLCItem(op=TKOperator.AND, content=content))
   
    # reached content
    for rep in replacements:
        dupContentSub: TKLLCContent = copy.deepcopy(content)
        newContent = flattener_modifyContent(dupContentSub, rep)
        subresult.append(TKLLCItem(op=rep[0], content=newContent))

    return subresult

# evaluate item
def flattener_evaluateItem(statement: TKStatement, clauseType: TKClauseType, properties: TKLLProperties, operator: TKOperator, parentOffset: int = 0) -> tuple[TKLLCItem, list[TKLLEntity]]:
    
    # get the content
    originalContent, additionalEntities = flattener_evaluateContent(statement, clauseType, properties, parentOffset) 
    
    # start duplication stack
    mainContent = copy.deepcopy(originalContent)

    # multiple subjects: duplicate sentences, with the conjunct subject
    if statement.subject and len(statement.subject.conjuncts) > 0:
        replacements: list[tuple[TKOperator, int, int]] = list()
        for c in list(statement.subject.conjuncts):
            # get properties and conjuncts of the replacing entity
            ef = flattener_evaluateReference(c, parentOffset, False)
            replacements.append([c.op, originalContent.subject.id, ef])

        # replace content with list of items
        mainContent = flattener_multiplyContent(mainContent, replacements)
    
    # multiple direct: duplicate sentences, with the conjunct direct
    if statement.direct and len(statement.direct.conjuncts) > 0:
        replacements: list[tuple[TKOperator, int, int]] = list()
        for c in list(statement.direct.conjuncts):
            ef = flattener_evaluateReference(c, parentOffset, False)
            replacements.append([c.op, originalContent.direct.id, ef])

        # replace content with list of items
        mainContent = flattener_multiplyContent(mainContent, replacements)

    # multiple indirect: duplicate sentences, with the conjunct direct
    idx: int = 0
    for ind in statement.indirects:
        replacements: list[tuple[TKOperator, int, int]] = list()
        if len(ind.conjuncts) > 0:
            for c in list(ind.conjuncts):
                originalIndirect = originalContent.indirects[idx]
                ef = flattener_evaluateReference(c, parentOffset, False)
                replacements.append([c.op, originalIndirect.id, ef])
        idx += 1
        if len(replacements) > 0:
            # replace content with list of items
            mainContent = flattener_multiplyContent(mainContent, replacements)        
    
    # assign 
    mainContent = TKLLCItem(op=operator, content=mainContent)

    return [mainContent, additionalEntities]

# get predicate conjunct content (recursive function to manage multiple levels of coordination)
def flattener_processStatement(statement: TKStatement, clauseType: TKClauseType, op: TKOperator = None, properties: TKLLProperties = None, parentOffset: int = 0) -> tuple[list[TKLLCItem], list[TKEntity]]:

    if op == None: op = TKOperator.AND
    if properties == None: properties = TKLLProperties()

    originalStatement: TKStatement = copy.deepcopy(statement)
    
    # initialize result
    clauses: list[TKLLCItem] = list()
    entities: list[TKLLEntity] = flattener_initializeEntities(originalStatement.entities, parentOffset) # exclude statements, managed later

    # evaluate clauses
    mainItem, additionalEntities = flattener_evaluateItem(statement, clauseType, properties, op, parentOffset)

    clauses.append(mainItem)
    entities.extend(additionalEntities)

    # COORDINATE clauses (at the end, max prio)
    if len(originalStatement.predicate.conjuncts) > 0:
        recursiveOffsetEntities: int = max([e.id for e in entities]) + parentOffset
        for c in list(originalStatement.predicate.conjuncts):
            conjunctStatement = next((s for s in originalStatement.entities if s.id == c.id), None)
            ai, ae = flattener_processStatement(conjunctStatement.payload, TKClauseType.COORDINATE, c.op, None, recursiveOffsetEntities)
            entities.extend(ae)
            clauses.extend(ai)
            recursiveOffsetEntities = max([e.id for e in ae])

    return [clauses, entities]

# (DOING) build spacetime map from entities and normalize the spacetime of the entities in the map (-1, 1)
def flattener_normalizeSpacetimeMap(entities: list[TKLLEntity]) -> TKLLSpacetimeMap:
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

# search xcomp subjects
def flattener_searchXCompSubjects(items: list[TKLLCItem], entities: list[TKLLEntity]) -> list[TKLLCItem]:
    
    # cycle on every item
    prevItem: TKLLCItem = None
    for item in items:
        if isinstance(item.content, TKLLCContent):
            if prevItem != None \
            and item.content.clause_type == TKClauseType.XCOMP \
            and isinstance(prevItem.content, TKLLCContent) \
            and not item.content.subject:
                # get previous subject or direct
                if prevItem.content.direct:
                    item.content.subject = prevItem.content.direct 
                elif prevItem.content.subject:
                    item.content.subject = prevItem.content.subject 
        else:
            # go until a content is found
            item.content = flattener_searchXCompSubjects(item.content, entities)
        prevItem = item
    
    return items

# search entities references by pronoun
def flattener_getEntitiesByPronoun(lemma: str) -> int:
    
    resultId: int = None

    lemma = lemma.lower()
    if lemma in _PRONOUNS_BASE_ANCHORS:
        resultId = _PRONOUNS_BASE_ANCHORS[lemma]

    return resultId

# match entities
def flattener_extractUniqueEntities(entities: list[TKLLEntity], existingUniqueEntities: list[TKLLUniqueEntity]) -> list[TKLLUniqueEntity]:

    result: list[TKLLUniqueEntity] = existingUniqueEntities

    # resolve identities
    iCounter = len(existingUniqueEntities) + 1
    for e in entities:
        # itself or the referenced (search in entities)
        referencedEntity = next((ee for ee in entities if ee.id == e.referenceId), None) if e.referenceId > 0 else e
        if referencedEntity == None: 
            referencedEntity = e
        ref = next((t for t in result if t.token == referencedEntity.token), None)
        if ref == None:
            result.append(TKLLUniqueEntity(id=iCounter, token=e.token, references=[e.id]))
            iCounter += 1
        else:
            ref.references.append(e.id)

    return result

# resolve pronouns to the talker and listener of the sentence
def flattener_resolvePronouns(stat: TKStatement) -> TKStatement:

    # resolve pronouns: 
    for e in stat.entities:
        if e.payload.entity_type == "statement":
            flattener_resolvePronouns(e.payload) # recurse
        else:
            if e.payload.entity_type == "pronoun":
                referenceFound = flattener_getEntitiesByPronoun(e.payload.lemma) # relative to the sentence

                # remove reference to pronoun and assign it to the real entity
                if referenceFound:
                    e.referenceId = referenceFound

    return stat

# main flat function
def flattener_flat(tkStatements: TKStatements) -> TKLLC | None:
    
    entities: list[TKLLEntity] = list()
    items: list[TKLLCItem] = list()

    # for each statement, flatten it and add to the result
    uniqueEntities: list[TKLLUniqueEntity] = list()
    parentOffset: int = 0
    iCounter: int = 1
    for stat in tkStatements:

        # assign pronouns to real entities
        flattener_resolvePronouns(stat)

        clauseType = TKClauseType.MAIN if iCounter == 1 else TKClauseType.COORDINATE
        i, e = flattener_processStatement(stat, clauseType, TKOperator.AND, None, parentOffset)

         # XCOMP: add subjects from parent main
        i = flattener_searchXCompSubjects(i, e)

        # MATCH SUBJECTS within the statement to unique entities
        flattener_extractUniqueEntities(e, uniqueEntities) 

        items.extend(i)
        entities.extend(e)
        
        # recalculate the offset
        parentOffset = max([ee.id for ee in e])
        iCounter += 1

    # spacetimemap: build the spacetime map relative to the context of the statements
    spacetimemap, entities = flattener_normalizeSpacetimeMap(entities)

    # return result
    result = TKLLC(items=items, entities=entities, uniqueEntities=uniqueEntities, map=spacetimemap)
    return result
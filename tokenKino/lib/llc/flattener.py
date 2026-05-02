
# --------------------------------------------------------------
# FLAT compiler: transform TKStatements into a flat list of TKLLCItem (with TKEntity as predicate) and TKEntity as entities (subjects, direct and indirect objects)
# --------------------------------------------------------------
import copy
from lib.core.entities import TKLLC, LLCItemPayload, TKEntity, TKEntityReference, TKLLCContent, TKLLCItem, TKLLEntity, TKLLEntityReference, TKLLProperties, TKLLSpacetime, TKLLSpacetimeMap, TKOperator, TKStatement, TKStatements

def llc_evaluateReference(ref: TKEntityReference, entities: list[TKEntity], parentOffset: int = 0) -> TKLLEntityReference:
    
    # evaluate properties
    properties: list[TKLLEntityReference] = list()
    for p in ref.properties:
        properties.append(llc_evaluateReference(p, entities, parentOffset))

    # evaluate marker
    marker = ref.marker
    
    # return result
    return TKLLEntityReference(id=ref.id + parentOffset, marker=marker, properties=properties)

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
    
    # COORDINATE clauses
    if len(stat.predicate.conjuncts) > 0 :
        recursiveOffsetEntities: int = len(stat.entities) - len(stat.predicate.conjuncts) + parentOffset
        parentOffset -= len(stat.predicate.conjuncts) # update offset
        for c in list(stat.predicate.conjuncts):
            conjunctStatement = next((s for s in stat.entities if s.id == c.id), None)
            additionalItems, additionalEntities = llc_getProcessStatement(conjunctStatement.payload, c, recursiveOffsetEntities)
            entities.extend(additionalEntities)
            parentOffset += len(additionalEntities)

    # ---------------------------------------------
    # subject (manage statements)
    # ---------------------------------------------
    if subjEntity: 
        if subjEntity.payload.entity_type == "statement": 
            # exclude statements: csubj -> find a way to manage it
            parentOffset -= 1
        else: 
            subject = llc_evaluateReference(stat.subject, stat.entities, parentOffset) if subjEntity else None

            # multiple subjects: duplicate sentences, with the conjunct subject
            if len(stat.subject.conjuncts) > 0:
                for c in list(stat.subject.conjuncts):
                    # duplicate sentence with the other subject (does not affect entities)
                    conjunctSubject =  next((s for s in stat.entities if s.id == c.id), None)
                    dupStat = copy.deepcopy(stat)
                    dupStat.subject.id = conjunctSubject.id
                    dupStat.subject.conjuncts = []
                    ai, ae = llc_getProcessStatement(dupStat, c, parentOffset)
                    additionalItems.extend(ai)

    # ---------------------------------------------
    # direct (manage statements)
    # ---------------------------------------------
    if dirEntity: 
        if dirEntity.payload.entity_type == "statement": 
            # exclude statements not affecting time and space
            parentOffset -= 1
        else: 
            direct = llc_evaluateReference(stat.direct, stat.entities, parentOffset) if dirEntity else None

            # multiple subjects: duplicate sentences, with the conjunct subject
            if len(stat.direct.conjuncts) > 0:
                for c in list(stat.direct.conjuncts):
                    # duplicate sentence with the other subject (does not affect entities)
                    conjunctDirect =  next((s for s in stat.entities if s.id == c.id), None)
                    dupStat = copy.deepcopy(stat)
                    dupStat.direct.id = conjunctDirect.id
                    dupStat.direct.conjuncts = []
                    ai, ae = llc_getProcessStatement(dupStat, c, parentOffset)
                    additionalItems.extend(ai)            

    # ---------------------------------------------
    # indirects (manage statements)
    # ---------------------------------------------
    for e in indEntities:
        if e.payload.entity_type == "statement": 
            # exclude statements
            parentOffset -= 1
        else: 
            indRef = next(i for i in stat.indirects if e.id == i.id)
            indirects.append(llc_evaluateReference(indRef, stat.entities, parentOffset))

             # multiple subjects: duplicate sentences, with the conjunct subject
            if len(indRef.conjuncts) > 0:
                for c in list(indRef.conjuncts):
                    # duplicate sentence with the other subject (does not affect entities)
                    conjunctIndirect =  next((s for s in stat.entities if s.id == c.id), None)
                    dupStat = copy.deepcopy(stat)
                    indRefCopy = next(i for i in dupStat.indirects if e.id == i.id)
                    indRefCopy.id = conjunctIndirect.id
                    indRefCopy.conjuncts = []
                    ai, ae = llc_getProcessStatement(dupStat, c, parentOffset)
                    additionalItems.extend(ai)                    
    
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


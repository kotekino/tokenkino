# ------------------------------------------------------------------------------------------------
# FLAT compiler V2
# compiler
# ---
# subordinate management: operator THAT not viable (split sentence)
# subject infer (implicit, xcomp, pronouns and other cases) compiler_getEntitiesByPronoun
# ---
# zip manage vectorless entitites
# ------------------------------------------------------------------------------------------------

# main flat function
import copy
import numpy as np
import spacy

from lib.core.tk import TKClauseType, TKEntity, TKEntityReference, TKMarker, TKOperator, TKStatement, TKStatements
from lib.core.tkllc import LLCItemPayload, TKLLEntity, TKLLEntityMap, TKLLEntityMapReference, TKLLC, TKLLCContent, TKLLCItem, TKLLEntityProperty, TKLLEntityReference, TKLLProperties, TKLLSpacetimeMap
from lib.llc.constants import _ANAPHORIC_PRONOUNS, _ANTECEDENT_TYPES, _MARKER_SIMILARITY_THRESHOLD, _PRONOUNS_BASE_ANCHORS, _PROP_BASE_ADVMOD_ANCHORS, _PROP_SIMILARITY_THRESHOLD, _RELATIVE_PRONOUNS, _SPACY_MODEL, _SUBJECT_CONTROL_VERBS, _SUBORDINATE_TYPE_BASE_ANCHORS, _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD
from lib.core.models import _VECTOR_INDEX, TKDictionaryDoc, TKMarkerDoc
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem

# globals
_entities: list[TKLLEntityMap] = []
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

# get all the entities
def compiler_getEntities(statement: TKStatement, statementIdx: int = 1, statementId: tuple[int, ...] = ()) -> list[TKLLEntityMap]:
    global _entities

    for e in statement.entities:
        if e.payload.entity_type == 'statement':
            compiler_getEntities(e.payload, statementIdx, statementId + (e.id,))
        else:
            id = len(_entities) + 1
            
            # get referenced entity
            refEntity = e
            if e.referenceId > 0:
                refEntity = next(en for en in statement.entities if en.id == e.referenceId)
            entity = compiler_getEntity(ent=refEntity, id=id)
            
            # if not present, append
            inputEntRef = TKLLEntityMapReference(inputStatementIdx=statementIdx, inputStatementId=statementId, inputEntityId=e.id)
            if len([e for e in _entities if e.entity.token == entity.token and e.entity.entity_type == entity.entity_type]) == 0:
                _entities.append(TKLLEntityMap(entity=entity, ref=[inputEntRef]))
            else:
                # update the reference
                refEnt = next((e for e in _entities if e.entity.token == entity.token and e.entity.entity_type == entity.entity_type))
                refEnt.ref.append(inputEntRef)

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
    global _entities

    # collect all the entities in the statements, and assign them a unique id
    idx = 1
    for tks in tkStatements:

        # resolve pronouns
        compiler_resolvePronouns(tks)

        # resolve entities
        compiler_getEntities(statement=tks, statementIdx=idx)
        idx +=1

# ------------------------------------------------------------------------------------------------
# SUBORDINATE SUBJECT RESOLUTION
# the parser keeps subordinate clauses faithful (relative/anaphoric/implicit subjects untouched);
# here we resolve them so the flattened LLC repeats the real entity, e.g.
#   "I love the cat who is sitting on the chair" -> "... THAT the cat is sitting on the chair"
#   "I love Mari because she is perfect"         -> "... CONV Mari is perfect"
#   "I want to leave"                            -> "... I leave" (xcomp implicit subject)
# resolution substitutes the pronoun entity's payload with a deep copy of the antecedent payload
# (the entity dedup in compiler_getEntities then merges them), mirroring compiler_resolvePronouns
# but working across the statement boundary (the antecedent lives in the matrix statement).
# ------------------------------------------------------------------------------------------------

# get an entity of a statement by its local id
def compiler_entityById(statement: TKStatement, entityId: int) -> TKEntity | None:
    return next((e for e in statement.entities if e.id == entityId), None)

# lemma of a statement's predicate (lowercased), or "" when there is none / it is a sub-statement
def compiler_predicateLemma(statement: TKStatement) -> str:
    if not statement.predicate:
        return ""
    entity = compiler_entityById(statement, statement.predicate.id)
    if not entity:
        return ""
    payload = entity.payload
    lemma = getattr(payload, "word", None) or getattr(payload, "lemma", None) or getattr(payload, "token", None)
    return (lemma or "").lower()

# the field references of a statement (subject, predicate, direct, indirects)
def compiler_statementReferences(statement: TKStatement) -> list[TKEntityReference]:
    refs: list[TKEntityReference] = []
    if statement.subject: refs.append(statement.subject)
    if statement.predicate: refs.append(statement.predicate)
    if statement.direct: refs.append(statement.direct)
    refs.extend(statement.indirects)
    return refs

# candidate antecedents of a matrix statement, by salience (direct, then subject, then indirects).
# conjuncts are included so coordinated antecedents (e.g. "Mari and Luca") are seen as ambiguous.
def compiler_antecedentCandidates(statement: TKStatement) -> list[TKEntity]:
    order: list[TKEntityReference] = []
    if statement.direct: order.append(statement.direct)
    if statement.subject: order.append(statement.subject)
    order.extend(statement.indirects)

    candidates: list[TKEntity] = []
    for ref in order:
        for r in [ref, *ref.conjuncts]:
            ent = compiler_entityById(statement, r.id)
            if ent and ent.payload.entity_type in _ANTECEDENT_TYPES:
                candidates.append(ent)
    return candidates

# relative clause: replace the relative pronoun (subject or object) with the modified entity
def compiler_resolveRelative(subStatement: TKStatement, ownerEntity: TKEntity | None) -> None:
    if not ownerEntity or ownerEntity.payload.entity_type == "statement":
        return
    for e in subStatement.entities:
        if e.payload.entity_type == "pronoun" and (e.payload.lemma or "").lower() in _RELATIVE_PRONOUNS:
            e.payload = copy.deepcopy(ownerEntity.payload)

# anaphora: resolve a 3rd-person pronoun subject to a matrix antecedent, only when unambiguous
def compiler_resolveAnaphora(subStatement: TKStatement, matrixStatement: TKStatement) -> None:
    if not subStatement.subject:
        return
    subject = compiler_entityById(subStatement, subStatement.subject.id)
    if not subject or subject.payload.entity_type != "pronoun":
        return
    if (subject.payload.lemma or "").lower() not in _ANAPHORIC_PRONOUNS:
        return

    # only substitute when there is exactly one plausible antecedent (avoid wrong guesses)
    candidates = compiler_antecedentCandidates(matrixStatement)
    if len(candidates) == 1:
        subject.payload = copy.deepcopy(candidates[0].payload)

# implicit subject (xcomp / subjectless clause): inject the controller as the clause subject.
# object control when the matrix has an object ("I told her to go" -> her), else subject control
# ("I want to leave" -> I). the injected pronoun (e.g. "I") is later mapped by resolvePronouns.
def compiler_resolveImplicitSubject(subStatement: TKStatement, matrixStatement: TKStatement) -> None:
    # only when the clause carries no subject of its own
    if subStatement.subject:
        return

    # controller: object control (direct, else first indirect) unless the matrix verb is a
    # subject-control verb (e.g. "promise"), which keeps the matrix subject even with an object
    controllerRef = None
    if compiler_predicateLemma(matrixStatement) not in _SUBJECT_CONTROL_VERBS:
        controllerRef = matrixStatement.direct
        if not controllerRef and matrixStatement.indirects:
            controllerRef = matrixStatement.indirects[0]
    if not controllerRef:
        controllerRef = matrixStatement.subject
    if not controllerRef:
        return

    controller = compiler_entityById(matrixStatement, controllerRef.id)
    if not controller or controller.payload.entity_type == "statement":
        return

    # inject a fresh subject entity carrying a copy of the controller payload
    newId = max((e.id for e in subStatement.entities), default=0) + 1
    subStatement.entities.append(TKEntity(id=newId, payload=copy.deepcopy(controller.payload)))
    subStatement.subject = TKEntityReference(id=newId, dep="nsubj")

# resolve the subordinate clauses hanging off a reference (and its conjuncts), recursively
def compiler_resolveReferenceSubordinates(reference: TKEntityReference, matrixStatement: TKStatement) -> None:
    ownerEntity = compiler_entityById(matrixStatement, reference.id)

    for subReference in reference.subordinates:
        subEntity = compiler_entityById(matrixStatement, subReference.id)
        if not subEntity or subEntity.payload.entity_type != "statement":
            continue
        subStatement: TKStatement = subEntity.payload

        # relative clause -> owner antecedent; subjectless clause (xcomp) -> implicit
        # controller; explicit pronoun subject -> matrix anaphora
        clauseType = compiler_parseMarker(subReference.marker)
        if clauseType == TKClauseType.ACLRELCL:
            compiler_resolveRelative(subStatement, ownerEntity)
        elif not subStatement.subject:
            compiler_resolveImplicitSubject(subStatement, matrixStatement)
        else:
            compiler_resolveAnaphora(subStatement, matrixStatement)

        # the subordinate is itself a matrix for its own nested subordinates
        compiler_resolveSubordinateSubjects(subStatement)

    # conjuncts can carry their own subordinate clauses
    for conjReference in reference.conjuncts:
        compiler_resolveReferenceSubordinates(conjReference, matrixStatement)

# resolve relative / anaphoric / implicit subjects of all subordinate clauses of a statement
def compiler_resolveSubordinateSubjects(statement: TKStatement) -> None:
    for reference in compiler_statementReferences(statement):
        compiler_resolveReferenceSubordinates(reference, statement)

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

# recurse properties of properties and conjunct of properties
def compiler_recurseReferenceProperties(ref: TKEntityReference, statementIdx: int, statementId: tuple[int, ...]) -> list[TKLLEntityProperty]:
    
    # init
    propertyReferences: list[TKLLEntityReference] = list()

    # get properties and sub properties recursively
    for p in ref.properties:
        map = TKLLEntityMapReference(inputStatementIdx=statementIdx, inputStatementId=statementId, inputEntityId=p.id)
        propertyReferences.append(TKLLEntityProperty(id=compiler_getEntityIdByMap(map), dep=p.dep, properties=compiler_recurseReferenceProperties(p, statementIdx, statementId)))

    return propertyReferences

# evaluate reference
def compiler_evaluateReference(ref: TKEntityReference, statementIdx: int, statementId: tuple[int, ...]) -> TKLLEntityReference:

    # evaluate marker, op, aux
    marker = ref.marker
    aux = ref.aux

    # get properties
    properties: list[TKLLEntityProperty] = compiler_recurseReferenceProperties(ref, statementIdx, statementId)

    # return result
    map = TKLLEntityMapReference(inputStatementIdx=statementIdx, inputStatementId=statementId, inputEntityId=ref.id)
    return TKLLEntityReference(id=compiler_getEntityIdByMap(map), dep=ref.dep, marker=marker, properties=properties, aux=aux)

# parse marker: it must take in account the CONTEXT of the marker (todo)
def compiler_parseMarker(marker: TKMarker) -> TKClauseType:

    # if no lemma, return other
    if not marker or not marker.word:
        if marker and marker.parent_dep: 
            return marker.parent_dep
        else:
            return TKClauseType.OTHER

    # 0. get doc
    newDoc = nlp.tokenizer(marker.word)

    # 1. simple case
    if marker.word in _SUBORDINATE_TYPE_BASE_ANCHORS:
        return _SUBORDINATE_TYPE_BASE_ANCHORS[marker.word]

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
    if marker.parent_dep: return marker.parent_dep
    
    # 4. fallback
    return TKClauseType.OTHER

# evaluate subordinate clause
def compiler_evaluateSubordinate(reference: TKEntityReference, statement: TKStatement, statementIdx: int, statementId: tuple[int, ...]) -> list[TKLLCItem]:
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

    result = compiler_evaluateStatement(statement, statementIdx, statementId + (reference.id,), subordinateType, operator)

    return result

# modify content
def compiler_modifyContent(
        content: LLCItemPayload, 
        rep: tuple[TKOperator, int, TKLLEntityReference], 
        subs: list[TKEntityReference], 
        conj: list[TKEntityReference], 
        entities: list[TKEntity], 
        entityId: int, 
        statementIdx: int, 
        statementId: tuple[int, ...]
        ) -> LLCItemPayload:

    # last level
    if isinstance(content, TKLLCContent):
        dupContentSub: TKLLCContent = copy.deepcopy(content)
        if dupContentSub.subject and dupContentSub.subject.id == rep[1]: 
            dupContentSub.subject = rep[2]
        if dupContentSub.direct and dupContentSub.direct.id == rep[1]: 
            dupContentSub.direct = rep[2]
        for iidx in range(len(dupContentSub.indirects)):
            if dupContentSub.indirects[iidx].id == rep[1]: 
                dupContentSub.indirects[iidx] = rep[2]
    else:
        dupContentSub: list[TKLLCItem] = copy.deepcopy(content)
        for eidx in range(len(dupContentSub)):
            dupContentSub[eidx].content = compiler_modifyContent(dupContentSub[eidx].content, rep, subs, conj, entities, entityId, statementIdx, statementId)

    # prepend main and return result
    result: list[TKLLCItem] = []
    if len(subs) > 0:
        result.extend(compiler_evaluateSubordinates(subs, entities, statementIdx, statementId))
        result.insert(0, TKLLCItem(op=TKOperator.AND,content=dupContentSub))
    else:
        result = dupContentSub
    if len(conj) > 0:
        result = compiler_evaluateCoordinates(conj, content, entityId, entities, statementIdx, statementId)

    return result

# evaluate subordinates for each statement element
def compiler_evaluateSubordinates(subordinates: list[TKEntityReference], entities: list[TKEntity], statementIdx: int, statementId: tuple[int, ...]) -> list[TKLLCItem]:
    result: list[TKLLCItem] = []

    # subordinates
    for subReference in subordinates:
        subordinate = next(i for i in entities if subReference.id == i.id)
        subItems = compiler_evaluateSubordinate(subReference, subordinate.payload, statementIdx, statementId)
        result.extend(subItems)
    
    return result

# evaluate conjuncts: return the head clause plus one item per coordinated sibling, as a
# FLAT list. Returns None when there is nothing to coordinate, so the caller keeps the
# plain (unwrapped) content instead of nesting it in a single-element list.
def compiler_evaluateCoordinates(conjuncts: list[TKEntityReference], mainContent: LLCItemPayload, entityId: int, entities: list[TKEntity], statementIdx: int, statementId: tuple[int, ...]) -> LLCItemPayload | None:
    global _entities

    # nothing to coordinate -> let the caller keep mainContent as-is
    if len(conjuncts) == 0:
        return None

    # head clause first, then exactly one item per conjunct
    result: list[TKLLCItem] = [TKLLCItem(op=TKOperator.AND, content=mainContent)]
    for coordReference in conjuncts:
        refEntity = next(en for en in entities if en.id == coordReference.id)
        if refEntity.payload.entity_type == "statement":
            # a fully coordinated sub-statement (e.g. "... and to make ...")
            result.extend(compiler_evaluateStatement(refEntity.payload, statementIdx, statementId + (refEntity.id,), refEntity.payload.clause_type, coordReference.op))
        else:
            # a coordinated entity: clone the head clause and swap entityId -> this sibling
            ef = compiler_evaluateReference(coordReference, statementIdx, statementId)
            rep = [coordReference.op, entityId, ef]
            dupContent = compiler_modifyContent(copy.deepcopy(mainContent), rep, coordReference.subordinates, coordReference.conjuncts, entities, entityId, statementIdx, statementId)
            result.append(TKLLCItem(op=coordReference.op, content=dupContent))

    return result

# evaluate single statement
def compiler_evaluateStatement(statement: TKStatement, statementIdx: int = 1, statementId: tuple[int, ...] = (), clauseType: TKClauseType = TKClauseType.MAIN, operator: TKOperator = TKOperator.AND) -> list[TKLLCItem]:
    result: list[TKLLCItem] = []

    predicate = None
    subject = None
    direct = None
    indirects: list[TKLLEntityReference] = list()

    # ---------------------------------------------
    # predicate
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
    # predicate (manage statements)
    # ---------------------------------------------
    if statement.predicate:
        result.extend(compiler_evaluateSubordinates(statement.predicate.subordinates, statement.entities, statementIdx, statementId))
        newMain = compiler_evaluateCoordinates(statement.predicate.conjuncts, mainContent, predicate.id, statement.entities, statementIdx, statementId)
        if newMain != None: mainContent = newMain

    # ---------------------------------------------
    # subject (manage statements)
    # ---------------------------------------------
    if statement.subject:
        result.extend(compiler_evaluateSubordinates(statement.subject.subordinates, statement.entities, statementIdx, statementId))
        newMain = compiler_evaluateCoordinates(statement.subject.conjuncts, mainContent, subject.id, statement.entities, statementIdx, statementId)
        if newMain != None: mainContent = newMain

    # ---------------------------------------------
    # direct (manage statements)
    # ---------------------------------------------
    if statement.direct:
        result.extend(compiler_evaluateSubordinates(statement.direct.subordinates, statement.entities, statementIdx, statementId))
        newMain = compiler_evaluateCoordinates(statement.direct.conjuncts, mainContent, direct.id, statement.entities, statementIdx, statementId)
        if newMain != None: mainContent = newMain

    # ---------------------------------------------
    # indirects (manage statements)
    # ---------------------------------------------
    idx: int = 0
    for indirectReference in statement.indirects:
        result.extend(compiler_evaluateSubordinates(indirectReference.subordinates, statement.entities, statementIdx, statementId))
        newMain = compiler_evaluateCoordinates(indirectReference.conjuncts, mainContent, indirectReference.id, statement.entities, statementIdx, statementId)
        if newMain != None: mainContent = newMain

    result.insert(0, TKLLCItem(op=operator,content=mainContent))

    # return all statements
    return result

# resolve all statements
def compiler_resolveStatements(tkStatements: TKStatements) -> list[TKLLCItem]:
    result:list[TKLLCContent] = []

    idx = 1
    for tks in tkStatements:

        # evaluate statements
        items = compiler_evaluateStatement(statement=tks, statementIdx=idx)

        # append items to result
        result.extend(items)
    
    return result

# ------------------------------------------------------------------------------------------------
# SPACETIME
# ------------------------------------------------------------------------------------------------
def compiler_spacetimeCollectReferences(statements: list[TKLLCItem]) -> list[TKLLEntityReference]:
    ents: list[TKEntity] = []

    for stat in statements:
        if isinstance(stat.content, TKLLCContent):
            if stat.content.subject: ents.append(stat.content.subject) 
            if stat.content.direct: ents.append(stat.content.direct) 
            if stat.content.predicate: ents.append(stat.content.predicate) 
            if stat.content.indirects: ents.extend(stat.content.indirects) 
        else:
            ents.extend(compiler_spacetimeCollectReferences(stat.content))

    return ents

# build spacetime map from entities and normalize the spacetime of the entities in the map (-1, 1)
def compiler_spacetimeNormalize(statements: list[TKLLCItem]) -> TKLLSpacetimeMap:

    # collect all entities
    references = compiler_spacetimeCollectReferences(statements)

    spacetimeMap: TKLLSpacetimeMap = TKLLSpacetimeMap()

    # get bounds
    minT = min(e.spacetime.position[0] - e.spacetime.size[0] / 2 for e in references) if len(references) > 0 else 0
    maxT = max(e.spacetime.position[0] + e.spacetime.size[0] / 2 for e in references) if len(references) > 0 else 0
    minX = min(e.spacetime.position[1] - e.spacetime.size[1] / 2 for e in references) if len(references) > 0 else 0
    maxX = max(e.spacetime.position[1] + e.spacetime.size[1] / 2 for e in references) if len(references) > 0 else 0
    minY = min(e.spacetime.position[2] - e.spacetime.size[2] / 2 for e in references) if len(references) > 0 else 0
    maxY = max(e.spacetime.position[2] + e.spacetime.size[2] / 2 for e in references) if len(references) > 0 else 0
    minZ = min(e.spacetime.position[3] - e.spacetime.size[3] / 2 for e in references) if len(references) > 0 else 0
    maxZ = max(e.spacetime.position[3] + e.spacetime.size[3] / 2 for e in references) if len(references) > 0 else 0

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
    for e in references:
        e.spacetime.position[0] = normalize(e.spacetime.position[0], minT, maxT)
        e.spacetime.position[1] = normalize(e.spacetime.position[1], minSpace, maxSpace)
        e.spacetime.position[2] = normalize(e.spacetime.position[2], minSpace, maxSpace)
        e.spacetime.position[3] = normalize(e.spacetime.position[3], minSpace, maxSpace)
        e.spacetime.size[0] = normalize(e.spacetime.size[0], minT, maxT)
        e.spacetime.size[1] = normalize(e.spacetime.size[1], minSpace, maxSpace)
        e.spacetime.size[2] = normalize(e.spacetime.size[2], minSpace, maxSpace)
        e.spacetime.size[3] = normalize(e.spacetime.size[3], minSpace, maxSpace)

    return spacetimeMap

# ------------------------------------------------------------------------------------------------
# ZIP
# ------------------------------------------------------------------------------------------------

# get base marker from marker
def compiler_zipGetBaseMarker(token: str) -> TKMarker:
    lemma = str(token).lower()
    exact_match = TKMarkerDoc.find_one(TKMarkerDoc.word == lemma).run()
    
    if exact_match:
        runtime_marker = TKMarker(**exact_match.model_dump())
        return runtime_marker

    new_doc = nlp(lemma)
    new_vector = new_doc[0].vector.tolist() if len(new_doc) > 0 else []

    pipeline = [
        {
            "$vectorSearch": {
                "index": _VECTOR_INDEX,
                "path": "vector",
                "queryVector": new_vector,
                "numCandidates": 50, 
                "limit": 1           
            }
        },
        {
            "$project": {
                "_id": 0,
                "word": 1,
                "vector": 1,
                "definition": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]

    search_results = list(TKMarkerDoc.aggregate(pipeline).run())

    if search_results:
        best_match = search_results[0]
        mongo_score = best_match.get("score", 0.0)
        if mongo_score >= _MARKER_SIMILARITY_THRESHOLD:
            best_match.pop("score", None)
            runtime_marker = TKMarker(**best_match)
            return runtime_marker
    
    new_marker_doc = TKMarkerDoc(
        word=lemma,
        vector=new_vector,
        definition="" 
    )
    new_marker_doc.insert()
    runtime_marker = TKMarker(**new_marker_doc.model_dump())
        
    return runtime_marker

# get advmode
def compiler_zipGetAdvmodeBase(propVec: np.ndarray) -> tuple[float, float]:
    
    # error gate
    if propVec.min() == propVec.max() == 0.0: return 1,1

    pipeline = [
        {
            "$vectorSearch": {
                "index": _VECTOR_INDEX,
                "path": "vector",
                "queryVector": propVec.tolist(),
                "numCandidates": 50, 
                "limit": 1           
            }
        },
        {
            "$project": {
                "_id": 0,
                "word": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]

    search_results = list(TKDictionaryDoc.aggregate(pipeline).run())
    
    weightEnt = 1.0
    weightProp = 1.0

    if search_results:
        top_result = search_results[0]
        match_word = top_result.get("word", "")
        score = top_result.get("score", 0.0)

        if score >= _PROP_SIMILARITY_THRESHOLD and match_word in _PROP_BASE_ADVMOD_ANCHORS:
            weightEnt = _PROP_BASE_ADVMOD_ANCHORS[match_word]
            weightProp = 0.0 

    return weightEnt, weightProp

# sum property (Ora fa solo algebra lineare pura)
def compiler_zipSumProperty(dep: str, entVec: np.ndarray, propVec: np.ndarray) -> np.ndarray:

    # if property
    weightProp: float = 1.0
    weightEnt: float = 1.0

    # calculate weight
    if dep == "advmod":
        weightEnt, weightProp = compiler_zipGetAdvmodeBase(propVec)
    #elif dep == "nmod":
    # etc

    # combine array using weights
    combined_vec: np.ndarray = (weightEnt * entVec) + (weightProp * propVec)
    return combined_vec

# get vector from an entity
def compiler_zipGetEntityVector(entity: TKLLEntityMap, properties: list[TKLLEntityProperty]) -> np.ndarray:

    # default vector
    entityVec = np.zeros(2925, dtype=np.float32)

    # get semantic for entities
    if entity.entity.entity_type == "dictionary":
        if len(entity.entity.semantic_vector) > 0: 
            entityVec = np.array(entity.entity.semantic_vector, dtype=np.float32)

    # merge properties
    for p in properties:
        propEnt = next(e for e in _entities if p.id == e.entity.id)
        propVec = compiler_zipGetEntityVector(propEnt, p.properties)
        # blend vectors (linear accumulation)
        entityVec = compiler_zipSumProperty(p.dep, entityVec, propVec)

    # soft normalization
    result = np.tanh(entityVec)
    return result

# get base marker vector
def compiler_zipGetMarker(word: str) -> list[float]:
    baseMarker = compiler_zipGetBaseMarker(word)
    return baseMarker.vector if baseMarker else np.zeros(300).tolist()

# get vector from a reference
def compiler_zipGetVector(ref: TKLLEntityReference) -> list[float]:
    global _entities
    vector: list[float] = []
    
    # empty reference
    if ref == None: 
        return np.zeros(3237).tolist()
    
    entity = next(e for e in _entities if ref.id == e.entity.id)
    marker: list[float] = compiler_zipGetMarker(ref.marker.word) if ref.marker else np.zeros(300).tolist()
    semantic: list[float] = compiler_zipGetEntityVector(entity, ref.properties).tolist()
    spacetime: list[float] = ref.spacetime.size + ref.spacetime.position + ref.spacetime.velocity
    vector = marker + semantic + spacetime

    return vector

# calculate final vector for the content
def compiler_zipContent(content: TKLLCContent) -> TKZipContent:
    ironic = content.properties.ironic
    dubitative = content.properties.dubitative
    imperative = content.properties.imperative
    sentiment = content.properties.sentiment
    subject = compiler_zipGetVector(content.subject)
    direct = compiler_zipGetVector(content.direct)
    predicate = compiler_zipGetVector(content.predicate)
    indirects: list[list[float]] = []
    for i in content.indirects:
        indirects.append(compiler_zipGetVector(i))

    return TKZipContent(ironic=ironic, dubitative=dubitative, imperative=imperative, sentiment=sentiment, subject=subject, direct=direct, predicate=predicate, indirects=indirects)

# calculate final vectors for the statements
def compiler_zip(items: list[TKLLCItem]) -> list[TKZipItem]:
    result: list[TKZipItem] = []
    for item in items:
        if isinstance(item.content, TKLLCContent):
            result.append(TKZipItem(op=item.op, content=compiler_zipContent(item.content)))
        else: 
            result.append(TKZipItem(op=item.op, content=compiler_zip(item.content)))
    return result

# ------------------------------------------------------------------------------------------------
# MAIN METHOD
# ------------------------------------------------------------------------------------------------
def compiler_compile(tkStatements: TKStatements) -> tuple[TKLLC, TKZip]:
    global _entities
    
    # reset entities
    _entities = []

    # resolve relative / anaphoric / implicit subordinate subjects before flattening
    for tks in tkStatements:
        compiler_resolveSubordinateSubjects(tks)

    # tkllc
    compiler_resolveEntities(tkStatements)
    statements: list[TKLLCItem] = compiler_resolveStatements(tkStatements)
    map = compiler_spacetimeNormalize(statements)
    tkllc = TKLLC(map=map, items=statements, entities=[e.entity for e in _entities])

    # tkzip
    zipmap = map.tbounds + map.xbounds + map.ybounds + map.zbounds
    tkzip: TKZip = TKZip(map=zipmap, items=TKZipItem(op=TKOperator.AND, content=compiler_zip(tkllc.items)))

    return tkllc, tkzip
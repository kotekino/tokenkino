# ------------------------------------------------------------------------------------------------
# ENTITIES
# entity collection + pronoun (talker/listener) resolution, plus the shared entity/statement
# helpers used across the statements and subordinates modules.
# ------------------------------------------------------------------------------------------------
from lib.core.tk import TKEntity, TKEntityReference, TKStatement, TKStatements
from lib.core.tkllc import TKLLEntity, TKLLEntityMap, TKLLEntityMapReference
from lib.llc.constants import _PRONOUNS_BASE_ANCHORS

from .c_state import _entities

# get a single entity from the tk entity, and convert it to a TKLLEntity
def compiler_getEntity(ent: TKEntity, id: int) -> TKLLEntity:

    token = ''
    semantic: list[float] = list()
    geo: list[float] | None = None
    sense: str | None = None
    entity_type = ent.payload.entity_type

    if ent.payload.entity_type == "dictionary":
        token = ent.payload.word
        semantic: list[float] = ent.payload.vector
        # carry the WSD-assigned synset key across the LLC boundary (was dropped before)
        sense = ent.payload.sense
    elif ent.payload.entity_type == "name":
        token = ent.payload.name
    elif ent.payload.entity_type == "place":
        token = ent.payload.name
        # carry the place's coordinates ([lon, lat]) into the flat entity for the space axis
        if ent.payload.location and ent.payload.location.coordinates:
            geo = ent.payload.location.coordinates
    elif ent.payload.entity_type == "meta":
        token = ent.payload.who.name
    elif ent.payload.entity_type == "num":
        token = str(ent.payload.value)
    elif ent.payload.entity_type == "pronoun":
        token = ent.payload.lemma
        semantic: list[float] = ent.payload.vector
    elif ent.payload.entity_type == "generic":
        token = ent.payload.token

    return TKLLEntity(id=id, token=token, semantic_vector=semantic, entity_type=entity_type, geo=geo, sense=sense)

# get all the entities
def compiler_getEntities(statement: TKStatement, statementIdx: int = 1, statementId: tuple[int, ...] = ()) -> list[TKLLEntityMap]:
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
    # collect all the entities in the statements, and assign them a unique id
    idx = 1
    for tks in tkStatements:

        # resolve pronouns
        compiler_resolvePronouns(tks)

        # resolve entities
        compiler_getEntities(statement=tks, statementIdx=idx)
        idx +=1

# ------------------------------------------------------------------------------------------------
# SHARED ENTITY / STATEMENT HELPERS (used by c_statements and c_subordinates)
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

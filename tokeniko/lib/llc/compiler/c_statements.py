# ------------------------------------------------------------------------------------------------
# STATEMENTS
# flatten the recursive TKStatement tree into ordered TKLLCItem(s): references, markers, operators,
# subordinate clauses (with the THAT attitude classification) and coordinated conjuncts.
# ------------------------------------------------------------------------------------------------
import copy

from lib.core.tk import TKClauseType, TKEntity, TKEntityReference, TKMarker, TKOperator, TKStatement, TKStatements
from lib.core.tkllc import LLCItemPayload, TKLLAttitude, TKLLEntityMapReference, TKLLCContent, TKLLCItem, TKLLEntityProperty, TKLLEntityReference, TKLLProperties
from lib.llc.constants import _ATTITUDE_ANCHORS, _ATTITUDE_DEFAULT, _COMPARISON_AFFIRMATIVE, _NEGATION_MARKERS, _NEGATIVE_QUANTIFIERS, _SUBORDINATE_TYPE_BASE_ANCHORS, _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD
from lib.llc.utils import utils_antonyms

from .c_state import _entities, nlp
from .c_entities import compiler_predicateLemma

# ------------------------------------------------------------------------------------------------
# COMPARISON POLARITY (Decision 2)
# a comparison predicate asserts a relation between the subject and an indirect operand. the
# AFFIRMATIVE forms (equal/same/...) assert sameness; their ANTONYMS (different/unlike/...) assert
# non-equality and are treated as NEGATED comparisons (reusing the Decision-1 flag, no new operator).
# polarity is decided via the antonym column-read primitive (utils_antonyms), not a hardcoded list:
# a predicate is a negative comparison iff it is an antonym of an affirmative comparison anchor.
# the antonym columns of the (few) affirmative anchors are precomputed once and cached.
# intrinsic grounding -- compare(subject, indirect) -- is the reasoning engine's job (Phase 3); we
# only set polarity here. NB the operands stay subject + indirect (the parser already does this).
# ------------------------------------------------------------------------------------------------
_COMPARISON_NEGATIVE_CACHE: set[str] | None = None

# union of the antonym columns of every affirmative comparison anchor -> the negative-comparison
# predicate set (different/unlike/...). computed lazily once per process (the base matrix is static).
def compiler_negativeComparisonWords() -> set[str]:
    global _COMPARISON_NEGATIVE_CACHE
    if _COMPARISON_NEGATIVE_CACHE is None:
        negatives: set[str] = set()
        for anchor in _COMPARISON_AFFIRMATIVE:
            negatives |= utils_antonyms(anchor)
        # an affirmative anchor must never count as its own negation
        _COMPARISON_NEGATIVE_CACHE = negatives - _COMPARISON_AFFIRMATIVE
    return _COMPARISON_NEGATIVE_CACHE

# is the clause a NEGATIVE comparison? true when its predicate token is an antonym of an affirmative
# comparison anchor (different/unlike vs same/equal). affirmative comparisons stay non-negated.
def compiler_isNegativeComparison(content: TKLLCContent) -> bool:
    if not content.predicate:
        return False
    predicateToken = compiler_entityToken(content.predicate.id)
    if not predicateToken or predicateToken in _COMPARISON_AFFIRMATIVE:
        return False
    return predicateToken in compiler_negativeComparisonWords()

# token (lemma/text) of a flat entity by its id, lowercased; "" if unknown.
def compiler_entityToken(entityId: int | None) -> str:
    if entityId is None:
        return ""
    ent = next((e for e in _entities if e.entity.id == entityId), None)
    return (ent.entity.token or "").lower() if ent else ""

# does a property (or any of its nested properties) carry a negation marker ("not"/"no"/"never")?
def compiler_propertyIsNegation(prop: TKLLEntityProperty) -> bool:
    if compiler_entityToken(prop.id) in _NEGATION_MARKERS:
        return True
    return any(compiler_propertyIsNegation(p) for p in prop.properties)

# clause-level negation: a role (subject/predicate/direct/indirect) carries a negation marker as
# one of its properties. "not"/"never" attach to the predicate (verb/copula) as advmod; "no"
# attaches to the negated noun (object) as det -- so we scan EVERY role, not just the predicate.
def compiler_contentIsNegated(content: TKLLCContent) -> bool:
    roles = [content.subject, content.predicate, content.direct, *content.indirects]
    for role in roles:
        if role and any(compiler_propertyIsNegation(p) for p in role.properties):
            return True
    # negative quantifier subject ("nobody runs" / "nothing happens"): the subject token IS the
    # negation. best-effort (Phase-0) -- flag the clause negated; the subject is left as the
    # quantifier token (a proper generic person/thing entity is a TODO).
    # TODO Phase-0 gap: rewrite "nobody" -> generic "person" + negated so the grounding geometry
    # matches the affirmative ("a person runs") rather than the bare quantifier.
    if content.subject and compiler_entityToken(content.subject.id) in _NEGATIVE_QUANTIFIERS:
        return True
    return False

def compiler_getEntityIdByMap(map: TKLLEntityMapReference) -> int | None:
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
def compiler_evaluateReference(ref: TKEntityReference, statementIdx: int, statementId: tuple[int, ...]) -> TKLLEntityReference | None:

    # evaluate marker, op, aux
    marker = ref.marker
    aux = ref.aux

    # resolve the entity id first; if it cannot be resolved — e.g. a clausal subject ("to accept is
    # to consider...") or an otherwise unmappable reference — skip this reference GRACEFULLY (return
    # None) instead of constructing an invalid TKLLEntityReference (id must be an int). Callers treat
    # a None role as absent. This is the fix for the parse crashes (the Phase-1b "None id" skips).
    map = TKLLEntityMapReference(inputStatementIdx=statementIdx, inputStatementId=statementId, inputEntityId=ref.id)
    eid = compiler_getEntityIdByMap(map)
    if eid is None:
        return None

    # get properties
    properties: list[TKLLEntityProperty] = compiler_recurseReferenceProperties(ref, statementIdx, statementId)

    # return result
    return TKLLEntityReference(id=eid, dep=ref.dep, marker=marker, properties=properties, aux=aux)

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

# classify a propositional-attitude verb (the matrix predicate of a THAT/ccomp) into its
# attitude class + default world-truth confidence of the complement X
def compiler_classifyAttitude(verb: str) -> TKLLAttitude:
    klass, confidence = _ATTITUDE_ANCHORS.get((verb or "").lower(), _ATTITUDE_DEFAULT)
    return TKLLAttitude(verb=verb or None, klass=klass, confidence=confidence)

# evaluate subordinate clause
def compiler_evaluateSubordinate(reference: TKEntityReference, statement: TKStatement, statementIdx: int, statementId: tuple[int, ...], matrixVerb: str = "") -> list[TKLLCItem]:
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
        # loose juxtaposition: not a propositional complement -> co-assert with AND
        operator = TKOperator.AND

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
        # clausal complement of an attitude/utterance verb ("I assume THAT you are fine"):
        # the only genuine propositional-attitude case -> keep THAT (to be mapped by the
        # matrix predicate's attitude class: factive/doxastic/desiderative/reportative)
        operator = TKOperator.THAT

    elif subordinateType == TKClauseType.ACL:
        # adnominal clause (participial/infinitival noun modifier): intersective -> AND
        operator = TKOperator.AND

    elif subordinateType == TKClauseType.ACLRELCL:
        # relative clause: intersective modification on the (now shared) referent -> AND
        operator = TKOperator.AND

    elif subordinateType == TKClauseType.ADVCL:
        # adverbial adjunct clause: co-asserted related event -> AND
        operator = TKOperator.AND

    elif subordinateType == TKClauseType.XCOMP:
        # open complement (subject shared, predicational): not a that-clause -> AND
        operator = TKOperator.AND

    else:
        # other means it affects something else, but the operator is AND
        operator = TKOperator.AND

    result = compiler_evaluateStatement(statement, statementIdx, statementId + (reference.id,), subordinateType, operator)

    # ccomp is the propositional complement X bound by THAT: tag it with the matrix predicate's
    # attitude class (factive/doxastic/desiderative/reportative) so the semantic layer can project
    if subordinateType == TKClauseType.CCOMP and result:
        result[0].attitude = compiler_classifyAttitude(matrixVerb)

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

# evaluate subordinates for each statement element. matrixVerb is the embedding predicate lemma,
# used only to classify the attitude of a ccomp (propositional complement)
def compiler_evaluateSubordinates(subordinates: list[TKEntityReference], entities: list[TKEntity], statementIdx: int, statementId: tuple[int, ...], matrixVerb: str = "") -> list[TKLLCItem]:
    result: list[TKLLCItem] = []

    # subordinates
    for subReference in subordinates:
        subordinate = next(i for i in entities if subReference.id == i.id)
        subItems = compiler_evaluateSubordinate(subReference, subordinate.payload, statementIdx, statementId, matrixVerb)
        result.extend(subItems)

    return result

# evaluate conjuncts: return the head clause plus one item per coordinated sibling, as a
# FLAT list. Returns None when there is nothing to coordinate, so the caller keeps the
# plain (unwrapped) content instead of nesting it in a single-element list.
def compiler_evaluateCoordinates(conjuncts: list[TKEntityReference], mainContent: LLCItemPayload, entityId: int, entities: list[TKEntity], statementIdx: int, statementId: tuple[int, ...]) -> LLCItemPayload | None:
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
            if ef is None:
                continue  # unresolvable coordinate — skip rather than clone with a None reference
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
        indirectRef = compiler_evaluateReference(indirectReference, statementIdx, statementId)
        if indirectRef is not None:
            indirects.append(indirectRef)

    # get properties
    properties: TKLLProperties = TKLLProperties()

    # append main content and build item
    mainContent = TKLLCContent(clause_type=clauseType, properties=properties, subject=subject, predicate=predicate, direct=direct, indirects=indirects)

    # clause-level negation: flag when a role carries a "not"/"no"/"never" marker (Decision 1),
    # OR the predicate is a negative comparison ("different"/"unlike", Decision 2). discrete &
    # recoverable -- the geometry alone loses it (cos("happy", "not happy") == 1.0).
    mainContent.negated = compiler_contentIsNegated(mainContent) or compiler_isNegativeComparison(mainContent)

    # ---------------------------------------------
    # predicate (manage statements)
    # ---------------------------------------------
    if statement.predicate:
        # the embedding verb classifies the attitude of any ccomp hanging off the predicate
        matrixVerb = compiler_predicateLemma(statement)
        result.extend(compiler_evaluateSubordinates(statement.predicate.subordinates, statement.entities, statementIdx, statementId, matrixVerb))
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

        # next statement: keep statementIdx aligned with compiler_resolveEntities, so
        # references/properties of later sentences resolve against the right entity map
        idx += 1

    return result

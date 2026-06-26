# ------------------------------------------------------------------------------------------------
# STATEMENTS
# flatten the recursive TKStatement tree into ordered TKLLCItem(s): references, markers, operators,
# subordinate clauses (with the THAT attitude classification) and coordinated conjuncts.
# ------------------------------------------------------------------------------------------------
import copy

from lib.core.tk import TKClauseType, TKEntity, TKEntityReference, TKMarker, TKOperator, TKQuantifier, TKStatement, TKStatements
from lib.core.tkllc import LLCItemPayload, TKLLAttitude, TKLLEntityMapReference, TKLLCContent, TKLLCItem, TKLLEntityProperty, TKLLEntityReference, TKLLProperties
from lib.llc.constants import _IMPLICATION_VERBS, _NEGATION_MARKERS, _NEGATIVE_QUANTIFIERS, _QUANTIFIER_NEGATIVE, _REFLEXIVE_PRONOUNS
from lib.llc.anchors import anchor_resolve, anchor_comparison_polarity, anchor_quantifier

from .c_state import _entities
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
# is the clause a NEGATIVE comparison? true when its predicate token has negative comparison polarity
# (different/unlike vs same/equal), via the unified antonym-aware resolver. affirmative comparisons
# stay non-negated.
def compiler_isNegativeComparison(content: TKLLCContent) -> bool:
    if not content.predicate:
        return False
    return anchor_comparison_polarity(compiler_entityToken(content.predicate.id)) == "negative"

# token (lemma/text) of a flat entity by its id, lowercased; "" if unknown.
def compiler_entityToken(entityId: int | None) -> str:
    if entityId is None:
        return ""
    ent = next((e for e in _entities if e.entity.id == entityId), None)
    return (ent.entity.token or "").lower() if ent else ""

# is the clause an IDENTITY comparison (same/equal OR different/unlike — either polarity)?
def compiler_isIdentityComparison(content: TKLLCContent) -> bool:
    if not content.predicate:
        return False
    tok = compiler_entityToken(content.predicate.id)
    if not tok:
        return False
    return anchor_comparison_polarity(tok) != "none"

# reflexive identity: an identity comparison whose subject and one operand corefer — either the same
# entity id (a == a, a cat == a cat) or a reflexive pronoun operand (a == itself). polarity (a=a vs
# a≠a) is carried by the existing `negated` flag; here we only mark that the relation is reflexive.
def compiler_isReflexiveIdentity(content: TKLLCContent) -> bool:
    if not compiler_isIdentityComparison(content) or not content.subject:
        return False
    subjectId = content.subject.id
    operands = ([content.direct] if content.direct else []) + list(content.indirects)
    for op in operands:
        if op.id == subjectId:
            return True
        tok = compiler_entityToken(op.id)
        if tok and tok in _REFLEXIVE_PRONOUNS:
            return True
    return False

# does a property (or any of its nested properties) carry a negation marker ("not"/"no"/"never")?
def compiler_propertyIsNegation(prop: TKLLEntityProperty) -> bool:
    if compiler_entityToken(prop.id) in _NEGATION_MARKERS:
        return True
    return any(compiler_propertyIsNegation(p) for p in prop.properties)

# the SUBJECT's determiner lemma, if any ("all"/"no"/"the"/"a"/...) — read from the det-dep property
# on the subject reference. "" when the subject is bare / has no determiner.
def compiler_subjectDeterminer(content: TKLLCContent) -> str:
    if not content.subject:
        return ""
    for p in content.subject.properties:
        if p.dep == "det":
            return compiler_entityToken(p.id)
    return ""

# the clause's quantifier. read off the subject's DETERMINER ("all cats"); if the subject has none, fall
# back to the subject's OWN token, so an indefinite pronoun subject quantifies itself ("everything that
# thinks" -> UNIVERSAL, "nothing" -> NEGATIVE). anchor_quantifier's table gates it: a normal bare noun /
# personal pronoun ("cat", "I") is not a quantifier word -> GENERIC, exactly as before.
def compiler_contentQuantifier(content: TKLLCContent) -> TKQuantifier:
    det = compiler_subjectDeterminer(content)
    if det:
        return anchor_quantifier(det)
    subject_word = compiler_entityToken(content.subject.id) if content.subject else ""
    return anchor_quantifier(subject_word)

# does a property carry a negation marker, EXCLUDING a subject det that is a NEGATIVE quantifier?
# "no"/"none"/"neither" sit in _NEGATION_MARKERS, but as the SUBJECT's determiner they are
# RECLASSIFIED to the NEGATIVE quantifier (handled in the quantifier flip) — counting them here too
# would double-flip the truth. predicate "not"/"never" still flag negated as before.
def compiler_propertyIsNegationNonQuantifier(prop: TKLLEntityProperty) -> bool:
    tok = compiler_entityToken(prop.id)
    if prop.dep == "det" and tok in _QUANTIFIER_NEGATIVE:
        # still allow a deeper nested negation marker (defensive), just not this det token itself
        return any(compiler_propertyIsNegation(p) for p in prop.properties)
    return compiler_propertyIsNegation(prop)

# clause-level negation: a role (subject/predicate/direct/indirect) carries a negation marker as
# one of its properties. "not"/"never" attach to the predicate (verb/copula) as advmod; "no"
# attaches to the negated noun (object) as det -- so we scan EVERY role, not just the predicate.
# the subject's NEGATIVE-quantifier determiner ("no cat ...") is reclassified to the quantifier and
# excluded here to avoid a double flip (quantifier=NEGATIVE already flips the relational verdict).
def compiler_contentIsNegated(content: TKLLCContent) -> bool:
    if content.subject and any(compiler_propertyIsNegationNonQuantifier(p) for p in content.subject.properties):
        return True
    other_roles = [content.predicate, content.direct, *content.indirects]
    for role in other_roles:
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

    # 1. unified anchor resolver: exact-hit -> nearest-anchor -> default OTHER
    subType = anchor_resolve(marker.word, "subordinate_types")
    if subType != TKClauseType.OTHER:
        return subType

    # 2. dep-label fallback (only when the anchors return the OTHER default)
    if marker.parent_dep: return marker.parent_dep

    # 3. fallback
    return TKClauseType.OTHER

# classify a propositional-attitude verb (the matrix predicate of a THAT/ccomp) into its
# attitude class + default world-truth confidence of the complement X
def compiler_classifyAttitude(verb: str) -> TKLLAttitude:
    klass, confidence = anchor_resolve(verb, "attitudes")
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

# a coordinated PREDICATE/clause shares the head clause's SUBJECT and copula AUX, but each predicate
# conjunct is parsed as its own sub-statement that lacks both (they attach only to the head — e.g. "the
# cat is dead and alive": "cat"=nsubj and "is"=cop both hang off "dead", so the "alive" sub-statement
# has neither). Without the subject the contradiction kernel can't match same-subject; without the aux
# the leaf renders "cat alive" instead of "cat be alive". Inherit each onto a conjunct leaf ONLY when
# it lacks it — SUBJECT + predicate AUX only, so each predicate keeps its own object ("the cat eats
# fish and chases mice" stays correct). Per-leaf deepcopy so leaves don't alias one reference.
def _inherit_shared(items: list[TKLLCItem], subject_ref, pred_aux) -> None:
    for it in items:
        if isinstance(it.content, TKLLCContent):
            if it.content.subject is None and subject_ref is not None:
                it.content.subject = copy.deepcopy(subject_ref)
            if pred_aux is not None and it.content.predicate is not None and it.content.predicate.aux is None:
                it.content.predicate.aux = copy.deepcopy(pred_aux)
        else:
            _inherit_shared(it.content, subject_ref, pred_aux)


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
            subItems = compiler_evaluateStatement(refEntity.payload, statementIdx, statementId + (refEntity.id,), refEntity.payload.clause_type, coordReference.op)
            # the conjunct sub-statement lacks the shared subject + copula aux; inherit them (see _inherit_shared)
            if isinstance(mainContent, TKLLCContent):
                head_aux = mainContent.predicate.aux if mainContent.predicate else None
                _inherit_shared(subItems, mainContent.subject, head_aux)
            result.extend(subItems)
        else:
            # a coordinated entity: clone the head clause and swap entityId -> this sibling
            ef = compiler_evaluateReference(coordReference, statementIdx, statementId)
            if ef is None:
                continue  # unresolvable coordinate — skip rather than clone with a None reference
            rep = [coordReference.op, entityId, ef]
            dupContent = compiler_modifyContent(copy.deepcopy(mainContent), rep, coordReference.subordinates, coordReference.conjuncts, entities, entityId, statementIdx, statementId)
            result.append(TKLLCItem(op=coordReference.op, content=dupContent))

    return result

# logical-implication operands: for "X implies/entails Y" where X and Y are CLAUSES, build the two
# clause items combined under IMPLY(antecedent, consequent). returns the two TKLLCItem (antecedent
# seeding the list with op=AND, consequent carrying op=IMPLY so the fold yields IMPLY(T_X, T_Y)), or
# None when this is not the clausal-implication case (no implication verb, or not exactly two clausal
# CCOMP complements — e.g. the nominal "rain implies clouds", which falls back to the normal path).
def compiler_implicationOperands(statement: TKStatement, matrixVerb: str, statementIdx: int, statementId: tuple[int, ...]) -> list[TKLLCItem] | None:
    if (matrixVerb or "").lower() not in _IMPLICATION_VERBS or not statement.predicate:
        return None

    # the clausal (CCOMP) complements of the matrix verb, in document order
    ccompRefs = [r for r in statement.predicate.subordinates if compiler_parseMarker(r.marker) == TKClauseType.CCOMP]
    if len(ccompRefs) != 2:
        return None

    items: list[TKLLCItem] = []
    for ref in ccompRefs:
        subordinate = next(i for i in statement.entities if ref.id == i.id)
        items.extend(compiler_evaluateSubordinate(ref, subordinate.payload, statementIdx, statementId, matrixVerb))

    # the two clauses must compile to exactly one item each for a clean IMPLY(antecedent, consequent)
    if len(items) != 2:
        return None

    antecedent, consequent = items[0], items[1]
    # they are logical operands of IMPLY, not doxastic THAT-complements: clear the attitude and make
    # the antecedent seed the fold (op=AND) and the consequent carry op=IMPLY.
    antecedent.attitude = None
    antecedent.op = TKOperator.AND
    consequent.attitude = None
    consequent.op = TKOperator.IMPLY
    return items

# is the SUBJECT of a content SENSE-LESS? — an indefinite pronoun like everything/everyone/everybody
# carries NO resolved dictionary WSD sense, whereas a class noun ("cat" in "all cats that bark") does.
# this is the discriminator that separates a property-restricted universal ("everything that thinks")
# from a class universal ("all cats that bark"). mirrors compiler_refSense's _entities id->sense read.
def compiler_subjectIsSenseLess(content: TKLLCContent) -> bool:
    if not content.subject:
        return False
    entity = next((e for e in _entities if content.subject.id == e.entity.id), None)
    if entity is None:
        return False
    return not entity.entity.sense

# stamp the utterance's interrogative mood onto EVERY leaf of a compiled statement. mood is a property
# of the whole sentence ("the cat is dead and alive?" → both clauses are the question), but leaves are
# produced by several paths (head clause, coordinated entities, coordinated SUB-statements, subordinates),
# so the only consistent place to apply it is over the finished leaf set. dubitative rides `properties`.
def _stamp_mood(items: list[TKLLCItem], dubitative: float, wh_role) -> None:
    for it in items:
        if isinstance(it.content, TKLLCContent):
            it.content.properties.dubitative = dubitative
            it.content.wh_role = wh_role
        else:
            _stamp_mood(it.content, dubitative, wh_role)

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

    # quantifier: read off the SUBJECT's determiner ("all"->UNIVERSAL, "no"->NEGATIVE, "some"/"a"->
    # EXISTENTIAL, "the"->DEFINITE, bare->GENERIC). a subject "no/none/neither" det was already
    # excluded from `negated` above (reclassified here) to avoid a double flip in the grounding.
    mainContent.quantifier = compiler_contentQuantifier(mainContent)

    # reflexive identity (a=a is necessarily true, a≠a necessarily false) — hardwired logic; the
    # evaluator pins these instead of grounding them. polarity stays in `negated`.
    mainContent.reflexive = compiler_isReflexiveIdentity(mainContent)

    # ---------------------------------------------
    # predicate (manage statements)
    # ---------------------------------------------
    # logical-implication matrix verb ("X implies/entails Y"): when the predicate is one of the
    # implication verbs and it embeds exactly two clausal (CCOMP) complements, the two clauses are
    # the antecedent and consequent of a real IMPLY — not doxastic THAT-complements. emit them as
    # IMPLY(antecedent, consequent) and DROP the "implies" predication leaf. otherwise fall back to
    # the normal subordinate path (so the nominal case "rain implies clouds" is untouched).
    suppressMatrixLeaf = False
    if statement.predicate:
        # the embedding verb classifies the attitude of any ccomp hanging off the predicate
        matrixVerb = compiler_predicateLemma(statement)
        implyItems = compiler_implicationOperands(statement, matrixVerb, statementIdx, statementId)
        if implyItems is not None:
            result.extend(implyItems)
            suppressMatrixLeaf = True
        else:
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

    # the matrix predication leaf is dropped for the IMPLY case (the verb is the operator, not a
    # standalone clause); otherwise it seeds the result as usual.
    if not suppressMatrixLeaf:
        result.insert(0, TKLLCItem(op=operator,content=mainContent))

    # property-restricted universal -> IMPLY rule. "everything that thinks exists" compiles to a
    # clean 2-leaf shape: a MAIN conclusion (everything exists) + an ACLRELCL condition (everything
    # thinks), joined by AND. logically it is a RULE: ∀x: think(x) ⟹ exist(x). rewrite the AND fold
    # into IMPLY(condition, conclusion) = IMPLY(thinks, exists) by mirroring compiler_implicationOperands
    # (antecedent seeds the fold with op=AND; consequent carries op=IMPLY; ordered [antecedent, consequent]).
    # the SENSE-LESS universal subject (an indefinite pronoun "everything"/"everyone", no resolved WSD
    # sense) is the discriminator vs a CLASS universal ("all cats that bark" — subject "cat" HAS a sense),
    # so the latter stays an intersective AND. tight signature: universal + sense-less subject + EXACTLY
    # one MAIN leaf and one ACLRELCL leaf and no other content leaves.
    if not suppressMatrixLeaf and isinstance(mainContent, TKLLCContent) and mainContent.quantifier == TKQuantifier.UNIVERSAL and compiler_subjectIsSenseLess(mainContent):
        mainLeaves = [it for it in result if isinstance(it.content, TKLLCContent) and it.content.clause_type == TKClauseType.MAIN]
        relclLeaves = [it for it in result if isinstance(it.content, TKLLCContent) and it.content.clause_type == TKClauseType.ACLRELCL]
        otherLeaves = [it for it in result if isinstance(it.content, TKLLCContent) and it.content.clause_type not in (TKClauseType.MAIN, TKClauseType.ACLRELCL)]
        if len(mainLeaves) == 1 and len(relclLeaves) == 1 and len(otherLeaves) == 0:
            conclusion = mainLeaves[0]   # the MAIN leaf  ("everything exists") -> consequent
            condition = relclLeaves[0]   # the ACLRELCL leaf ("everything thinks") -> antecedent
            condition.op = TKOperator.AND     # antecedent seeds the fold
            conclusion.op = TKOperator.IMPLY  # consequent carries IMPLY -> IMPLY(T_condition, T_conclusion)
            result = [condition, conclusion]

    # interrogative mood (a question is ANSWERED, not asserted): stamp the parser-detected
    # dubitative/wh_role onto every leaf of this utterance. only for questions — declaratives
    # (dubitative 0.5 / wh_role None) are left untouched, so the assertion path is unchanged.
    if statement.dubitative != 0.5 or statement.wh_role is not None:
        _stamp_mood(result, statement.dubitative, statement.wh_role)

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

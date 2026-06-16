# ------------------------------------------------------------------------------------------------
# SUBORDINATE SUBJECT RESOLUTION
# the parser keeps subordinate clauses faithful (relative/anaphoric/implicit subjects untouched);
# here we resolve them so the flattened LLC repeats the real entity, e.g.
#   "I love the cat who is sitting on the chair" -> "... AND the cat is sitting on the chair"
#   "I love Mari because she is perfect"         -> "... CONV Mari is perfect"
#   "I want to leave"                            -> "... I leave" (xcomp implicit subject)
# resolution substitutes the pronoun entity's payload with a deep copy of the antecedent payload
# (the entity dedup in compiler_getEntities then merges them), mirroring compiler_resolvePronouns
# but working across the statement boundary (the antecedent lives in the matrix statement).
# ------------------------------------------------------------------------------------------------
import copy

from lib.core.tk import TKClauseType, TKEntity, TKEntityReference, TKStatement
from lib.llc.constants import _ANAPHORIC_PRONOUNS, _ANTECEDENT_TYPES, _RELATIVE_PRONOUNS, _SUBJECT_CONTROL_VERBS

from .c_entities import compiler_entityById, compiler_predicateLemma, compiler_statementReferences
from .c_statements import compiler_parseMarker

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
# `ownerRef` is the matrix reference the subordinate hangs off (its governor): when that governor is
# a NOUN complement (the matrix object/indirect, not the predicate) -- e.g. "the cat has no ability
# to roar" -- the infinitive is ADNOMINAL, so its implicit subject is the clause BEARER (the matrix
# subject: the cat), NOT the governing noun ("ability"). verb-control infinitives (the subordinate
# governed by the predicate, "I want to run" -> I) keep the standard subject/object control below.
def compiler_resolveImplicitSubject(subStatement: TKStatement, matrixStatement: TKStatement, ownerRef: TKEntityReference | None = None) -> None:
    # only when the clause carries no subject of its own
    if subStatement.subject:
        return

    # noun-complement infinitive: the subordinate is governed by a noun (not the matrix predicate),
    # i.e. it modifies the matrix object/indirect -> the bearer is the matrix subject, not the noun.
    isPredicateGoverned = bool(matrixStatement.predicate and ownerRef and ownerRef.id == matrixStatement.predicate.id)
    if ownerRef is not None and not isPredicateGoverned:
        controllerRef = matrixStatement.subject
        if not controllerRef:
            return
        controller = compiler_entityById(matrixStatement, controllerRef.id)
        if not controller or controller.payload.entity_type == "statement":
            return
        newId = max((e.id for e in subStatement.entities), default=0) + 1
        subStatement.entities.append(TKEntity(id=newId, payload=copy.deepcopy(controller.payload)))
        subStatement.subject = TKEntityReference(id=newId, dep="nsubj")
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
            # pass the governing reference so a noun-complement infinitive (governed by a matrix
            # object/indirect noun) binds the bearer (matrix subject), not the governing noun
            compiler_resolveImplicitSubject(subStatement, matrixStatement, ownerRef=reference)
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

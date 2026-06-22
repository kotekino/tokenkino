# --------------------------------------------------------------
# lib/core/evaluation_harness.py — the PARSER-FREE evaluate-a-zip harness.
#
# Shared by the api (EvaluationService) and the brain (brain/thinking.py). It loads the ACTIVE
# knowledge (definitions + axioms + theorems), builds the injected graph readers + the
# forward-chainer rules/facts, runs the DB-agnostic evaluator over a ready TKZip statement, and maps
# the best relational match back to a concrete document id.
#
# It imports ONLY lib.core.* + lib.llc.evaluator — NEVER lib.llc.parser / lib.llc.compiler. That is
# the whole point: the `brain` process stays parser-free (it only calls init_io, never loads
# spaCy/Stanza), so it cannot import EvaluationService (which imports the parser at module top). The
# evaluator package is parser-free, so the brain reuses this harness directly. The single parser step
# (sentence -> TKZip) stays in EvaluationService._compile_zip and is the only api-only piece.
# --------------------------------------------------------------
from typing import Optional

from lib.core.models import TKAxiomDoc, TKDefinitionDoc, TKRelationDoc, TKTheoremDoc
from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from lib.core.evaluation import AnswerKind, AnswerResult, AnswerVerdict, EvaluatorResult, EvaluatorStatus
from lib.llc.evaluator import evaluator_classifyForm, evaluator_evaluateStatement, evaluator_solveWh


# the injected is_a graph reader: parents(sense) -> direct is_a hypernyms. the ~150k-triple
# `relations` collection is never loaded wholesale — only the per-sense edges actually touched.
# cached per evaluate_zip() call (rebuilt below) so repeated lookups during one BFS hit memory.
def _make_relations_reader():
    cache: dict[str, list[str]] = {}

    def parents(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "is_a"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return parents


# the injected part_of (meronymy) graph reader: wholes(sense) -> direct part_of wholes (the
# senses Y such that `sense` is part_of Y). kept SEPARATE from the is_a reader — is_a and part_of
# are different relations with different truth semantics. cached per evaluate_zip() call, same shape.
def _make_partof_reader():
    cache: dict[str, list[str]] = {}

    def wholes(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "part_of"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return wholes


# the injected antonym reader: antonyms(sense) -> the senses directly antonym-linked to `sense`.
# feeds the intra-statement contrary-predicate check (same-subject + antonym predicate senses).
# cached per evaluate_zip() call, same shape as the is_a / part_of readers.
def _make_antonym_reader():
    cache: dict[str, list[str]] = {}

    def antonyms(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "antonym"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return antonyms


# collect every leaf TKZipContent of a zip item tree, in order.
def _zip_leaves(item) -> list:
    c = item.content
    if isinstance(c, TKZipContent):
        return [c]
    out = []
    if isinstance(c, list):
        for child in c:
            out += _zip_leaves(child)
    return out


# the CROSS-ITEM consistency engine (parser-free). Detect a contradiction across a set of clauses
# (TKZipContent), treating them as one conjunction. Returns classifyForm's detail string on a
# contradiction, else None. Used to compare statements from DIFFERENT memory items (e.g. the same
# speaker's prior claims). A cross-item contradiction is a revisable CONTEXT conflict — NOT the
# hardwired logic INCONSISTENT (that is X∧¬X within ONE statement). The caller keeps the set small
# (pairwise) to stay under classifyForm's atom cap (_MAX_ATOMS=16).
def cross_item_conflict(clauses: list) -> Optional[str]:
    if len(clauses) < 2:
        return None
    synthetic = TKZip(
        map=[0.0] * 8,
        items=TKZipItem(
            op=TKOperator.AND,
            content=[TKZipItem(content=c) for c in clauses],
        ),
    )
    form = evaluator_classifyForm(synthetic, antonyms=_make_antonym_reader())
    return form.detail if form.contradiction else None


# extract universal RULES from the active axioms for the forward-chainer. a rule leaf is a
# UNIVERSAL-quantified clause with a subject sense and a predicate sense ("all carnivores eat
# meat", "all humans are thinkers"). the predicate POS classifies the rule: a NOUN predicate
# (".n.") is a MEMBERSHIP rule (subject is_a* S => subject is_a [predicate class]); anything else
# (".a."/".s."/".v.") is a PROPERTY rule (subject is_a* S => subject has the predicate property).
def _extract_rules(axiom_docs) -> list:
    rules: list = []
    for doc in axiom_docs:
        if doc.zip is None:
            continue
        for leaf in _zip_leaves(doc.zip.items):
            if getattr(leaf, "quantifier", None) != TKQuantifier.UNIVERSAL:
                continue
            senses = getattr(leaf, "senses", None) or {}
            subject = senses.get("subject")
            predicate = senses.get("predicate")
            if not subject or not predicate:
                continue
            kind = "membership" if ".n." in predicate else "property"
            rules.append({
                "subject": subject,
                "predicate": predicate,
                "object": senses.get("direct"),
                "negated": bool(getattr(leaf, "negated", False)),
                "kind": kind,
                "original": doc.original,
            })
    return rules


# extract individual membership FACTS from the active axioms for the forward-chainer. a fact leaf
# has an entity-linked individual subject (identities['subject']) and a NOUN predicate sense and is
# NOT universal ("Mari is a human" => mari@... is_a homo.n.02).
def _extract_facts(axiom_docs) -> list:
    facts: list = []
    for doc in axiom_docs:
        if doc.zip is None:
            continue
        for leaf in _zip_leaves(doc.zip.items):
            if getattr(leaf, "quantifier", None) == TKQuantifier.UNIVERSAL:
                continue
            identities = getattr(leaf, "identities", None) or {}
            senses = getattr(leaf, "senses", None) or {}
            subject_uid = identities.get("subject")
            predicate = senses.get("predicate")
            if not subject_uid or not predicate or ".n." not in predicate:
                continue
            facts.append({
                "subject_uid": subject_uid,
                "klass_sense": predicate,
                "original": doc.original,
            })
    return facts


# evaluate a ready TKZip statement against the ACTIVE knowledge (archived=False). loads the
# definitions/axioms/theorems, builds the readers + forward-chainer rules/facts, runs the evaluator,
# and resolves the best relational match (matchedKind + matchedIndex) back to that document's
# id/original. PURE — stores nothing. Returns the api-shape dict MINUS "original" (the caller, which
# knows the source text, adds that): {"result", "matchedId", "matchedOriginal", "relationMatch"}.
# NB: theorems default to archived=True, so the theorem pool is empty until a theorem is promoted
# (archived=False) — expected with the current model; not worked around here.
# load the ACTIVE knowledge (archived=False) ONCE: the definition leaf clauses, the axiom/theorem
# zips + their docs (for id mapping), the injected graph readers, and the forward-chainer rules/facts.
# shared by evaluate_zip (assertions) and answer_zip (questions) so both pay the load once per call.
def _load_active_kb() -> dict:
    definition_docs = TKDefinitionDoc.find({"archived": False}).to_list()
    axiom_docs = TKAxiomDoc.find({"archived": False}).to_list()
    theorem_docs = TKTheoremDoc.find({"archived": False}).to_list()

    # definitions are now full TKZips (single OR multi clause); flatten each into its leaf
    # clauses so the evaluator still grounds against a flat list[TKZipContent].
    definitions = [
        leaf
        for d in definition_docs if d.zip is not None
        for leaf in _zip_leaves(d.zip.items)
    ]
    return {
        "definition_docs": definition_docs,
        "axiom_docs": axiom_docs,
        "theorem_docs": theorem_docs,
        "definitions": definitions,
        "axiom_zips": [a.zip for a in axiom_docs],
        "theorem_zips": [t.zip for t in theorem_docs],
        "relations": _make_relations_reader(),
        "part_of": _make_partof_reader(),
        "antonyms": _make_antonym_reader(),
        "rules": _extract_rules(axiom_docs),
        "facts": _extract_facts(axiom_docs),
    }


def evaluate_zip(statement: TKZip) -> dict:
    kb = _load_active_kb()
    axiom_docs, theorem_docs = kb["axiom_docs"], kb["theorem_docs"]
    result = evaluator_evaluateStatement(
        statement, kb["definitions"], kb["axiom_zips"], kb["theorem_zips"],
        relations=kb["relations"], part_of=kb["part_of"], antonyms=kb["antonyms"],
        rules=kb["rules"], facts=kb["facts"],
    )

    # map the best (kind, index) back to a concrete document
    matchedId = None
    matchedOriginal = None
    if result.matchedKind == "axiom" and result.matchedIndex is not None:
        doc = axiom_docs[result.matchedIndex]
        matchedId, matchedOriginal = str(doc.id), doc.original
    elif result.matchedKind == "theorem" and result.matchedIndex is not None:
        doc = theorem_docs[result.matchedIndex]
        matchedId, matchedOriginal = str(doc.id), doc.original

    return {
        "result": result,
        "matchedId": matchedId,
        "matchedOriginal": matchedOriginal,
        "relationMatch": result.relationMatch,
    }


# strong-conclusion bands (mirror brain.thinking): a polar question -> YES / NO / I-don't-know.
_TRUE_FLOOR = 0.85
_FALSE_CEIL = 0.15


# map a grounded EvaluatorResult to a POLAR answer. logic-is-sacred: a self-contradictory polar
# question ("the cat is dead and alive?") is a definitive, confident NO — not a mid/insufficient.
def _polar_answer(result: EvaluatorResult) -> AnswerResult:
    if result.status == EvaluatorStatus.INCONSISTENT:
        return AnswerResult(
            kind=AnswerKind.POLAR, verdict=AnswerVerdict.NO, confidence=1.0,
            reason=result.inconsistency or "logically inconsistent", derivation=list(result.derivation),
        )
    if result.status == EvaluatorStatus.RESOLVED:
        if result.truth > _TRUE_FLOOR:
            return AnswerResult(kind=AnswerKind.POLAR, verdict=AnswerVerdict.YES,
                                confidence=result.truth, derivation=list(result.derivation))
        if result.truth < _FALSE_CEIL:
            return AnswerResult(kind=AnswerKind.POLAR, verdict=AnswerVerdict.NO,
                                confidence=1.0 - result.truth, derivation=list(result.derivation))
    return AnswerResult(kind=AnswerKind.POLAR, verdict=AnswerVerdict.UNKNOWN, confidence=0.5,
                        reason="insufficient knowledge to answer")


# answer a QUESTION zip (mood read from the leaves: dubitative=1 -> question, wh_role -> the gap).
# returns None when the statement is NOT interrogative (caller uses evaluate_zip instead). a question
# is ANSWERED, never believed — this stores nothing, and the brain skips the assertion/cross-item
# paths. POLAR -> reuse the grounded truth (inconsistent -> confident NO); WH -> solve the gap role.
def answer_zip(statement: TKZip) -> Optional[dict]:
    leaves = _zip_leaves(statement.items)
    if not any(getattr(l, "dubitative", 0.5) >= 0.999 for l in leaves):
        return None  # not interrogative
    wh_leaf = next((l for l in leaves if getattr(l, "wh_role", None) is not None), None)

    kb = _load_active_kb()
    result = evaluator_evaluateStatement(
        statement, kb["definitions"], kb["axiom_zips"], kb["theorem_zips"],
        relations=kb["relations"], part_of=kb["part_of"], antonyms=kb["antonyms"],
        rules=kb["rules"], facts=kb["facts"],
    )

    if wh_leaf is None:
        answer = _polar_answer(result)
    else:
        answer = evaluator_solveWh(wh_leaf, kb["axiom_zips"], kb["theorem_zips"], kb["relations"], assertion=result)

    return {"answer": answer, "result": result}

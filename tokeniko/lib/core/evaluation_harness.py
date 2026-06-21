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
from lib.core.models import TKAxiomDoc, TKDefinitionDoc, TKRelationDoc, TKTheoremDoc
from lib.core.tk import TKQuantifier
from lib.core.tkzip import TKZip, TKZipContent
from lib.llc.evaluator import evaluator_evaluateStatement


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
def evaluate_zip(statement: TKZip) -> dict:
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
    axiom_zips = [a.zip for a in axiom_docs]
    theorem_zips = [t.zip for t in theorem_docs]

    relations = _make_relations_reader()
    part_of = _make_partof_reader()
    antonyms = _make_antonym_reader()
    rules = _extract_rules(axiom_docs)
    facts = _extract_facts(axiom_docs)
    result = evaluator_evaluateStatement(
        statement, definitions, axiom_zips, theorem_zips,
        relations=relations, part_of=part_of, antonyms=antonyms,
        rules=rules, facts=facts,
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

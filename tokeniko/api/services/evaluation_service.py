# --------------------------------------------------------------
# services: business logic for the EVALUATE action.
# Compiles a sentence and evaluates its truth against tokeniko's knowledge: it grounds each flat
# clause against the definitions, folds the clause truths through the operator tree, and matches the
# whole statement geometrically against the axioms/theorems. Pure — stores nothing.
# The evaluator (lib/llc/evaluator) is DB-agnostic; this service is the DB adapter that loads the
# active knowledge and maps the best relational match back to a concrete document id.
# --------------------------------------------------------------
import copy

from lib.llc.parser import parser
from lib.llc.compiler import compiler_compile
from lib.llc.evaluator import evaluator_evaluateStatement
from lib.core.models import TKAxiomDoc, TKDefinitionDoc, TKRelationDoc, TKTheoremDoc
from lib.core.tk import TKStatement
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip


class EvaluationService:
    """Evaluate a sentence against tokeniko's memory (definitions + axioms + theorems).

    Receives the pipeline dependencies (the `tokeniko` stakeholder and the Ollama client) so it stays
    independent of FastAPI: the API layer builds a single instance at startup and reuses it.
    """

    def __init__(self, tokeniko, ai_client):
        self._tokeniko = tokeniko
        self._ai_client = ai_client

    # the injected is_a graph reader: parents(sense) -> direct is_a hypernyms. the ~150k-triple
    # `relations` collection is never loaded wholesale — only the per-sense edges actually touched.
    # cached per evaluate() call (rebuilt below) so repeated lookups during one BFS hit memory.
    @staticmethod
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
    # are different relations with different truth semantics. cached per evaluate() call, same shape.
    @staticmethod
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
    # cached per evaluate() call, same shape as the is_a / part_of readers.
    @staticmethod
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

    # parse + compile a sentence into its TKZip (same pipeline as the axiom/definition services)
    def _compile_zip(self, tokens: str) -> TKZip:
        recursiveResult = parser(tokens, self._tokeniko, self._tokeniko, self._ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        if not flatResult:
            raise ValueError("compilation produced no result")
        return flatResult[1]

    # evaluate a sentence. loads the ACTIVE knowledge (archived=False), evaluates, and resolves the
    # best relational match (matchedKind + matchedIndex) back to that document's id/original.
    # NB: theorems default to archived=True, so the theorem pool is empty until a theorem is promoted
    # (archived=False) — expected with the current model; not worked around here.
    def evaluate(self, tokens: str) -> dict:
        definition_docs = TKDefinitionDoc.find({"archived": False}).to_list()
        axiom_docs = TKAxiomDoc.find({"archived": False}).to_list()
        theorem_docs = TKTheoremDoc.find({"archived": False}).to_list()

        definitions = [d.content for d in definition_docs if d.content is not None]
        axiom_zips = [a.zip for a in axiom_docs]
        theorem_zips = [t.zip for t in theorem_docs]

        statement = self._compile_zip(tokens)
        relations = self._make_relations_reader()
        part_of = self._make_partof_reader()
        antonyms = self._make_antonym_reader()
        result = evaluator_evaluateStatement(
            statement, definitions, axiom_zips, theorem_zips,
            relations=relations, part_of=part_of, antonyms=antonyms,
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
            "original": tokens,
            "result": result,
            "matchedId": matchedId,
            "matchedOriginal": matchedOriginal,
            "relationMatch": result.relationMatch,
        }

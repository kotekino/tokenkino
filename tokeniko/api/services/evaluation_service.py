# --------------------------------------------------------------
# services: business logic for the EVALUATE action.
# Compiles a sentence and evaluates its truth against tokeniko's knowledge: it grounds each flat
# clause against the definitions, folds the clause truths through the operator tree, and matches the
# whole statement geometrically against the axioms/theorems. Pure — stores nothing.
# The parser-free evaluate-a-zip logic lives in lib/core/evaluation_harness.py (shared with the
# brain); this service only adds the parser step (sentence -> TKZip) on top — the one piece that
# needs spaCy/Stanza, which is why the brain cannot import this service and uses the harness directly.
# --------------------------------------------------------------
import copy

from lib.llc.parser import parser
from lib.llc.compiler import compiler_compile
from lib.core.evaluation_harness import evaluate_zip
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

    # parse + compile a sentence into its TKZip (same pipeline as the axiom/definition services).
    # This is the ONLY parser step — everything downstream is the parser-free harness.
    def _compile_zip(self, tokens: str) -> TKZip:
        recursiveResult = parser(tokens, self._tokeniko, self._tokeniko, self._ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        if not flatResult:
            raise ValueError("compilation produced no result")
        return flatResult[1]

    # evaluate a sentence. compiles it to a TKZip (the parser step), then delegates the whole
    # evaluation (load active knowledge -> evaluate -> resolve the best match) to the parser-free
    # harness, and re-attaches the original text. PURE — stores nothing.
    def evaluate(self, tokens: str) -> dict:
        statement = self._compile_zip(tokens)
        out = evaluate_zip(statement)
        return {"original": tokens, **out}

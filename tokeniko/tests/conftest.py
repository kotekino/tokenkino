"""tokeniko pytest regression gate — session-scoped fixtures + band-assert helpers.

INTEGRATION SUITE. This is the project's regression gate; it exercises the REAL pipeline,
not mocks. It therefore needs the live runtime UP:

  - MongoDB on :27018 (the local Atlas container — `docker compose up -d` from the package dir)
  - Ollama on http://localhost:11434 (preparser/decompiler models auto-pulled on init)
  - the shared KB database: `relations` (~150k WordNet triples) + dictionary — READ-ONLY for tests
  - a SANDBOX memory database ("<memory>_test", self-bootstrapped below): the ~3235 grounding
    definitions cloned from the live memory DB + the _FIXTURE_AXIOMS the tests assert against.
    tokeniko's LIVING memory DB (the DNA imprint) is never touched — the gate must not depend on
    what he currently believes, nor leak test knowledge ("Mari is a human") into his mind.

The heavy pipeline (spaCy/Stanza + Ollama clients + the parser) is loaded ONCE per test session
via the `_io` fixture; every other fixture and test reuses it. A full run takes a few minutes.

Assertion philosophy: BAND-ASSERTS, never exact floats or exact sense strings (WSD drifts).
We assert status + truth band + structural facts (flags, key presence, quantifier enum, leaf
count, uid prefix) — never an exact numeric truth or an exact `cat.n.01`-style sense.
"""
import os
import copy

import pytest
from dotenv import load_dotenv

load_dotenv("/Users/renzosala/Develop/personal/tokeniko/tokeniko/.env")


# the gate runs against a SANDBOX MIND: the shared KB database (dictionary/relations bedrock —
# read-only for tests) + a dedicated "<memory>_test" memory database. tokeniko's LIVING memory DB
# (his DNA imprint, axioms/theorems) is never read NOR written by the gate — the imprint is personal
# and changes as he grows; the gate's fixture knowledge (below) must not depend on it or leak into it.
# The sandbox self-bootstraps idempotently: definitions are cloned from the live memory DB when the
# counts diverge ($merge, same server), and the fixture axioms are compiled+inserted when missing.
_FIXTURE_AXIOMS = [
    # the seed_rules.py set the evaluator tests assert against (chaining + syllogisms)
    "all carnivores eat meat",
    "all birds have feathers",
    "all fish swim",
    "all humans are mortal",
    "all humans are thinkers",
    "all thinkers exist",
    "everything that thinks exists",
    "Mari is a human",
]


def _bootstrap_sandbox(mongo_client_memory, live_mem_db: str, test_mem_db: str, tokeniko, ai):
    live = mongo_client_memory[live_mem_db]
    test = mongo_client_memory[test_mem_db]
    # definitions: the grounding vocabulary — clone from live when out of sync (cheap count check)
    n_live, n_test = live["definitions"].count_documents({}), test["definitions"].count_documents({})
    if n_live and n_live != n_test:
        test["definitions"].delete_many({})
        live["definitions"].aggregate([
            {"$merge": {"into": {"db": test_mem_db, "coll": "definitions"},
                        "on": "_id", "whenMatched": "replace", "whenNotMatched": "insert"}},
        ])
    # fixture axioms: compile+insert the missing ones (parser is already loaded; idempotent by original)
    from lib.core.models import TKAxiomDoc
    from api.services import AxiomService
    service = AxiomService(tokeniko, ai)
    for sentence in _FIXTURE_AXIOMS:
        if TKAxiomDoc.find_one({"original": sentence}).run() is None:
            service.create(sentence)


@pytest.fixture(scope="session")
def _io():
    from lib.core.io import init_io, get_tokeniko
    live_mem_db = os.getenv("MONGO_DB_NAME_MEMORY")
    test_mem_db = f"{live_mem_db}_test"
    _, mongo_client_memory, ai = init_io(
        os.getenv("MONGO_URI"),
        os.getenv("MONGO_DB_NAME"),
        test_mem_db,
        os.getenv("OLLAMA_HOST"),
    )
    from lib.llc.parser import parser_init
    parser_init()
    tok = get_tokeniko()
    _bootstrap_sandbox(mongo_client_memory, live_mem_db, test_mem_db, tok, ai)
    return tok, ai


@pytest.fixture(scope="session")
def compile_zip(_io):
    tok, ai = _io
    from lib.llc.parser import parser
    from lib.llc.compiler import compiler_compile

    def _c(sentence):
        rec = parser(sentence, tok, tok, ai)
        return compiler_compile(copy.deepcopy(rec))[1]  # TKZip

    return _c


@pytest.fixture(scope="session")
def leaves():
    from lib.core.tkzip import TKZipContent

    def _l(zp):
        c = zp.items.content
        if isinstance(c, TKZipContent):
            return [c]
        out = []
        if isinstance(c, list):
            for it in c:
                cc = it.content
                out += (
                    [cc] if isinstance(cc, TKZipContent)
                    else [x.content for x in cc] if isinstance(cc, list)
                    else []
                )
        return out

    return _l


@pytest.fixture(scope="session")
def evaluate(_io):
    tok, ai = _io
    from api.services import EvaluationService
    svc = EvaluationService(tok, ai)

    def _e(sentence):
        return svc.evaluate(sentence)["result"]

    return _e


@pytest.fixture(scope="session")
def answer(compile_zip):
    # answer a QUESTION sentence via the parser-free harness: returns the AnswerResult, or None if
    # the sentence is not interrogative.
    from lib.core.evaluation_harness import answer_zip

    def _a(sentence):
        out = answer_zip(compile_zip(sentence))
        return out["answer"] if out else None

    return _a


# --- band-assert helpers ---------------------------------------------------------------------
# Live in tests/asserts.py so test modules can `from tests.asserts import ...` without depending on
# conftest being importable as a top-level module. Re-exported here for convenience.
from tests.asserts import (  # noqa: E402,F401
    assert_resolved_true,
    assert_resolved_false,
    assert_insufficient,
    assert_inconsistent,
)

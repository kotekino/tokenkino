"""tokeniko pytest regression gate — session-scoped fixtures + band-assert helpers.

INTEGRATION SUITE. This is the project's regression gate; it exercises the REAL pipeline,
not mocks. It therefore needs the live runtime UP:

  - MongoDB on :27018 (the local Atlas container — `docker compose up -d` from the package dir)
  - Ollama on http://localhost:11434 (preparser/decompiler models auto-pulled on init)
  - the SEEDED knowledge base:
      * 9 axioms incl. the universal rules ("all humans are mortal", "all carnivores eat meat", ...)
        and the individual fact "Mari is a human"
      * the multi-clause definitions (~3235) that ground vocabulary
      * the `relations` collection (~150k WordNet is_a/part_of/antonym triples)

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


@pytest.fixture(scope="session")
def _io():
    from lib.core.io import init_io, get_tokeniko
    _, _, ai = init_io(
        os.getenv("MONGO_URI"),
        os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"),
        os.getenv("OLLAMA_HOST"),
    )
    from lib.llc.parser import parser_init
    parser_init()
    return get_tokeniko(), ai


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

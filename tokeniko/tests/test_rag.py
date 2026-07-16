"""lib/rag — the consolidated Claude plumbing (2026-07-16, the author's OCD consolidation).
PURE tests: rag_call over a fake client (NO network, ever) — text mode, schema mode (the
output_config kwarg shape the instruments' fakes also assert), graceful-None on failure;
json_envelope; rag_enabled kill-switch semantics. The four instruments' own behavior stays
covered by test_translator / test_microscope / test_blog_p2.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from lib.rag import (
    BLOG_POLISH, RAG1_NORMALIZER, RAG2_DECOMPILE, RAG3_JUDGE,
    json_envelope, rag_call, rag_enabled,
)


class _FakeMessages:
    def __init__(self, text=None, exc=None):
        self._text, self._exc = text, exc
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        block = SimpleNamespace(type="text", text=self._text)
        return SimpleNamespace(content=[block])


class _FakeClient:
    def __init__(self, text=None, exc=None):
        self.messages = _FakeMessages(text=text, exc=exc)


# ---- rag_call ---------------------------------------------------------------------------------

def test_text_spec_returns_stripped_text_and_carries_the_spec():
    client = _FakeClient(text="  tidied sentence.  ")
    out = asyncio.run(rag_call(RAG1_NORMALIZER, "some inptu", client=client))
    assert out == "tidied sentence."
    call = client.messages.calls[0]
    assert call["model"] == RAG1_NORMALIZER.model
    assert call["max_tokens"] == RAG1_NORMALIZER.max_tokens
    assert call["system"] == RAG1_NORMALIZER.system
    assert call["messages"] == [{"role": "user", "content": "some inptu"}]
    assert "output_config" not in call          # free-text spec: no structured output


def test_schema_spec_returns_parsed_dict_with_output_config():
    payload = {"verdict": "ok", "confidence": 0.9, "severity": "none", "category": "none", "note": ""}
    client = _FakeClient(text=json.dumps(payload))
    out = asyncio.run(rag_call(RAG3_JUDGE, "SENTENCE:\n...", client=client))
    assert out == payload
    call = client.messages.calls[0]
    assert call["output_config"]["format"]["schema"] is RAG3_JUDGE.schema


def test_failure_returns_none_never_raises():
    assert asyncio.run(rag_call(RAG1_NORMALIZER, "x", client=_FakeClient(exc=RuntimeError("down")))) is None
    assert asyncio.run(rag_call(RAG3_JUDGE, "x", client=_FakeClient(text="not json {"))) is None
    assert asyncio.run(rag_call(RAG1_NORMALIZER, "x", client=_FakeClient(text="   "))) is None


# ---- json_envelope ------------------------------------------------------------------------------

def test_json_envelope_unwraps_surrounded_object():
    assert json_envelope("noise {\"translation\": \"I am happy.\"} trailing") == {"translation": "I am happy."}
    assert json_envelope("no object here") is None
    assert json_envelope(None) is None
    assert json_envelope("[1, 2]") is None      # an object envelope, never a bare array


# ---- rag_enabled --------------------------------------------------------------------------------

def test_rag_enabled_needs_the_key_and_respects_the_kill_switch(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("RAG1_DISABLED", raising=False)
    assert rag_enabled("RAG1_DISABLED") is True
    monkeypatch.setenv("RAG1_DISABLED", "1")
    assert rag_enabled("RAG1_DISABLED") is False
    monkeypatch.delenv("RAG1_DISABLED", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert rag_enabled("RAG1_DISABLED") is False


# ---- the registry census -------------------------------------------------------------------------

def test_every_instrument_spec_is_complete():
    for spec in (RAG1_NORMALIZER, RAG2_DECOMPILE, RAG3_JUDGE, BLOG_POLISH):
        assert spec.name and spec.model and spec.system
        assert spec.max_tokens > 0 and spec.timeout > 0

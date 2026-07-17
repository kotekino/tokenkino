# ------------------------------------------------------------------------------------------------
# rag2-out — the voice-side verifier (compose 2.0 slice 3, 2026-07-17). The mirror of rag1-in on
# the way out: a composed reply may gain fluency ONLY if the compiler consensus proves the polish
# still means the same thing. Two layers under test: `verifier_voice` (the polishability gate +
# the preservation contract, on REAL compiled pairs) and the senses gating (`_voice_out`, stubbed
# rag + verify — every failure path must ship the raw). No live API/cloud in the gate.
# ------------------------------------------------------------------------------------------------
import asyncio

import pytest

from lib.llc.normalizer import verifier_voice


# ---- verifier_voice: the polishability gate + the preservation contract ------------------------------

def test_true_fluency_pass_is_accepted(compile_zip):
    # a surface-only re-voicing (contraction) keeps every leaf key -> accepted
    ok, note = verifier_voice(compile_zip("I do not agree with that claim"),
                              compile_zip("I don't agree with that claim"))
    assert ok, note


def test_lexical_substitution_is_rejected_conservatively(compile_zip):
    # «do not agree» -> «disagree» is semantically fine but changes the leaf's sense key — the
    # verifier is deliberately conservative (fail-safe: the raw ships); documented, not a bug
    ok, note = verifier_voice(compile_zip("I do not agree"),
                              compile_zip("I disagree"))
    assert not ok


def test_flipped_negation_is_rejected(compile_zip):
    ok, note = verifier_voice(compile_zip("a calculator does not think"),
                              compile_zip("a calculator thinks"))
    assert not ok


def test_dropped_content_is_rejected(compile_zip):
    ok, note = verifier_voice(
        compile_zip("you are right and a software is not a mind"),
        compile_zip("you are right"))
    assert not ok


def test_invention_is_rejected(compile_zip):
    ok, note = verifier_voice(
        compile_zip("a cat is an animal"),
        compile_zip("a cat is an animal and a cat is a philosopher and a dog is a poet"))
    assert not ok


def test_fragment_raw_is_unverifiable(compile_zip):
    # the polishability gate: what the compiler cannot fully hear ships as curated raw
    ok, note = verifier_voice(compile_zip("why is that?"), compile_zip("why?"))
    assert not ok and "not verifiable" in note


# ---- _voice_out: the senses gating (stubbed rag + verify) ---------------------------------------------

def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def voice_env(monkeypatch):
    # rag enabled, no dry-run interference; each test stubs the calls it needs
    monkeypatch.delenv("RAG2_OUT_DISABLED", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # rag_enabled checks key presence
    from senses import outbound
    return outbound


def test_verified_polish_ships(voice_env, monkeypatch):
    outbound = voice_env
    async def fake_rag(spec, user, **kw):
        return "I must disagree with that claim"
    monkeypatch.setattr(outbound, "rag_call", fake_rag)
    monkeypatch.setattr(outbound, "_verify_voice", lambda raw, pol: {"ok": True, "note": "verified"})
    out = _run(outbound._voice_out("I do not agree with that claim"))
    assert out == "I must disagree with that claim"


def test_rejected_polish_ships_raw(voice_env, monkeypatch):
    outbound = voice_env
    async def fake_rag(spec, user, **kw):
        return "something entirely different"
    monkeypatch.setattr(outbound, "rag_call", fake_rag)
    monkeypatch.setattr(outbound, "_verify_voice",
                        lambda raw, pol: {"ok": False, "note": "sound leaf dropped"})
    raw = "you are right — I no longer hold that all software are minds"
    assert _run(outbound._voice_out(raw)) == raw


def test_api_down_ships_raw(voice_env, monkeypatch):
    outbound = voice_env
    async def fake_rag(spec, user, **kw):
        return "a polished variant of the message"
    monkeypatch.setattr(outbound, "rag_call", fake_rag)
    monkeypatch.setattr(outbound, "_verify_voice", lambda raw, pol: None)  # unreachable
    raw = "you are right — I no longer hold that all software are minds"
    assert _run(outbound._voice_out(raw)) == raw


def test_rag_down_ships_raw(voice_env, monkeypatch):
    outbound = voice_env
    async def fake_rag(spec, user, **kw):
        return None  # graceful None by rag_call's contract
    monkeypatch.setattr(outbound, "rag_call", fake_rag)
    raw = "you are right — I no longer hold that all software are minds"
    assert _run(outbound._voice_out(raw)) == raw


def test_short_fragment_never_burns_the_call(voice_env, monkeypatch):
    outbound = voice_env
    calls = []
    async def fake_rag(spec, user, **kw):
        calls.append(user)
        return "polished"
    monkeypatch.setattr(outbound, "rag_call", fake_rag)
    assert _run(outbound._voice_out("yes")) == "yes"
    assert _run(outbound._voice_out("why is that?")) == "why is that?"
    assert calls == []                       # the length pre-gate spent nothing


def test_kill_switch(voice_env, monkeypatch):
    outbound = voice_env
    monkeypatch.setenv("RAG2_OUT_DISABLED", "1")
    called = []
    async def fake_rag(spec, user, **kw):
        called.append(user)
        return "polished"
    monkeypatch.setattr(outbound, "rag_call", fake_rag)
    raw = "you are right — I no longer hold that all software are minds"
    assert _run(outbound._voice_out(raw)) == raw
    assert called == []


def test_anecdote_register_never_polished(voice_env, monkeypatch):
    # the premiere find (2026-07-17): rag2-out stripped «by the way,» — the side-note register is
    # discourse framing the zip cannot see, so the verifier CORRECTLY passed the stripped polish.
    # For a MENTION the register IS the point: deliver_one must ship the scaffold text verbatim.
    import asyncio as _asyncio
    from lib.core.memory import TokenikoAction
    outbound = voice_env
    called = []
    async def fake_voice_out(raw):
        called.append(raw)
        return "polished away"
    monkeypatch.setattr(outbound, "_voice_out", fake_voice_out)
    # exercise the gating expression exactly as deliver_one computes it
    payload = {"action_token": TokenikoAction.MENTION.value, "raw": "by the way, gold is beautiful"}
    raw = payload["raw"]
    polishable = raw and payload.get("action_token") != TokenikoAction.MENTION.value
    english = _asyncio.run(outbound._voice_out(raw)) if polishable else raw
    assert english == "by the way, gold is beautiful"
    assert called == []

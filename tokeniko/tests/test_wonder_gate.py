"""The wondering discipline (2026-07-16, the wondering-freeze fix): (1) the coordinator's
idle-confirmation gate — thinking_phase runs wondering ONLY when `wonder_allowed` (the coordinator
grants it after WONDER_IDLE_CONFIRM seconds without reactive work), so a live conversation never
competes with a daydream; (2) the `_class_word` in-process cache — kb-wondering re-renders every
derivable conclusion each pass, so the sense->word lookup must cost ONE dictionary query per sense
per process, not one per conclusion per tick (the freeze's hot site, evaluation_harness.py).
Sandbox memory DB; the dictionary is read-only bedrock.
"""
import pytest


# ---- (1) the idle-confirmation gate ----------------------------------------------------------------

@pytest.fixture()
def brain_state(_io):
    from brain.main import get_or_create_brain_state
    return get_or_create_brain_state()


def test_wonder_denied_while_idle_unconfirmed(_io, brain_state, monkeypatch):
    from brain import main as brain_main
    calls = {"think": 0, "wonder": 0}
    monkeypatch.setattr("brain.thinking.think_one", lambda bs: calls.__setitem__("think", calls["think"] + 1) or False)
    monkeypatch.setattr("brain.thinking.wonder_one", lambda bs: calls.__setitem__("wonder", calls["wonder"] + 1) or True)

    sub = brain_main.thinking_phase(brain_state, wonder_allowed=False)
    assert sub is None                    # no reactive work + wondering not yet allowed -> idle
    assert calls["think"] == 1
    assert calls["wonder"] == 0           # the daydream never started


def test_wonder_granted_on_confirmed_idle(_io, brain_state, monkeypatch):
    from brain import main as brain_main
    monkeypatch.setattr("brain.thinking.think_one", lambda bs: False)
    monkeypatch.setattr("brain.thinking.wonder_one", lambda bs: True)

    assert brain_main.thinking_phase(brain_state, wonder_allowed=True) == "wonder"


def test_reactive_think_outranks_wondering(_io, brain_state, monkeypatch):
    from brain import main as brain_main
    calls = {"wonder": 0}
    monkeypatch.setattr("brain.thinking.think_one", lambda bs: True)
    monkeypatch.setattr("brain.thinking.wonder_one", lambda bs: calls.__setitem__("wonder", calls["wonder"] + 1) or True)

    # fresh memory wins even when wondering is allowed — the reactive path is never displaced
    assert brain_main.thinking_phase(brain_state, wonder_allowed=True) == "think"
    assert calls["wonder"] == 0


# ---- (2) the _class_word cache ---------------------------------------------------------------------

def test_class_word_hits_the_dictionary_once_per_sense(_io, monkeypatch):
    import lib.core.evaluation_harness as harness
    hits = {"n": 0}

    def counting(sense):
        hits["n"] += 1
        return "feline"

    monkeypatch.setattr(harness, "_class_word_uncached", counting)
    harness._class_word_cache.pop("felis.n.99", None)  # a synthetic sense — never a real cache row

    assert harness._class_word("felis.n.99") == "feline"
    assert harness._class_word("felis.n.99") == "feline"
    assert hits["n"] == 1                 # second call served from the process cache
    harness._class_word_cache.pop("felis.n.99", None)  # leave no synthetic residue


def test_class_word_real_lookup_is_indexed_and_correct(_io):
    # the real path against the read-only dictionary: resolves, and lands in the cache
    import lib.core.evaluation_harness as harness
    harness._class_word_cache.pop("cat.n.01", None)
    assert harness._class_word("cat.n.01") == "cat"
    assert harness._class_word_cache.get("cat.n.01") == "cat"

# ------------------------------------------------------------------------------------------------
# THE TRANSLATOR AT THE EARS — rag1-in + rag2-in (instrument arc #3, v1; 2026-07-16).
#
# The author's rulings, mechanized and asserted: D1b escalation-only (a sound parse is NEVER
# touched), D4 the proposer is a cloud small model but THE ZIP-VERIFIER disposes (every soundly-
# parsed leaf must survive the polish, flags intact), D2 an unverifiable polish falls through to
# the raw parse (unknown leaves never become beliefs; eval:unknown already asks). No live API in
# the gate — the normalizer call is stubbed; the detector/verifier run on REAL compiled zips.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.llc.normalizer import detector_stumbles, verifier_preserves, _leaf_sound
from lib.core.kb_extract import _zip_leaves


# ---- the stumble detector (D1b: escalation-only) ---------------------------------------------------

def test_sound_sentence_never_escalates(compile_zip):
    assert detector_stumbles(compile_zip("a cat is a mammal")) is False
    assert detector_stumbles(compile_zip("all humans are mortal")) is False


def test_unknown_vocabulary_escalates(compile_zip):
    # OOV gibberish -> unknown leaf -> stumble
    assert detector_stumbles(compile_zip("a wug is a blicket")) is True


def test_tangle_wart_escalates(compile_zip):
    # the bold-test tangle signature: self-loop leaves («software is software») / bare-copula
    # predicates — the six-leaf monster's shape (census 2026-07-15)
    zp = compile_zip(
        "it is true. there are softwares that can think and software that can't think. "
        "probably all softwares can calculate"
    )
    assert detector_stumbles(zp) is True


# ---- the zip-verifier (rag2-in: the compiler disposes) ----------------------------------------------

def test_verifier_accepts_true_repair(compile_zip):
    # a typo'd original stumbles; the honest polish compiles sound and preserves what little was
    # sound before (nothing) -> accepted
    original = compile_zip("a catt is a mamal")
    polished = compile_zip("a cat is a mammal")
    ok, note = verifier_preserves(original, polished)
    assert ok, note


def test_verifier_rejects_dropped_leaf(compile_zip):
    # the original parses SOUND leaves; a "polish" that loses one is a meaning change -> rejected
    original = compile_zip("a cat is a mammal and a dog is an animal")
    polished = compile_zip("a cat is a mammal")
    ok, note = verifier_preserves(original, polished)
    assert not ok and "dropped" in note


def test_verifier_rejects_flipped_negation(compile_zip):
    # negation rides the conclusion key — a flipped negation is an altered leaf -> rejected
    original = compile_zip("a software does not reach truth")
    polished = compile_zip("a software reaches truth")
    ok, note = verifier_preserves(original, polished)
    assert not ok


def test_verifier_rejects_unrepaired_polish(compile_zip):
    # a polish that still stumbles repaired nothing -> rejected (the stumble must not just move)
    original = compile_zip("a wug is a blicket")
    polished = compile_zip("a wug is a blicket")
    ok, note = verifier_preserves(original, polished)
    assert not ok and "stumbles" in note


def test_verifier_rejects_invention(compile_zip):
    # ballooning: the polish may split a tangle, not free-associate
    original = compile_zip("a cat is a mammal")
    polished = compile_zip(
        "a cat is a mammal and a dog is an animal and a bird has feathers and a fish swims"
    )
    ok, note = verifier_preserves(original, polished)
    assert not ok and "balloons" in note


def test_verifier_accepts_flag_preserving_segmentation(compile_zip):
    # legitimate tangle-unwinding: the sound leaves survive with flags intact
    original = compile_zip("a cat is a mammal and a dog is an animal")
    polished = compile_zip("a cat is a mammal. a dog is an animal.")
    ok, note = verifier_preserves(original, polished)
    assert ok, note


# ---- the wired path (/input semantics via the service seam, normalizer stubbed) --------------------

def test_input_fallthrough_when_normalizer_off(_io, monkeypatch):
    # RAG1_DISABLED -> the raw parse stands exactly as before (no escalation attempted)
    import lib.llc.normalizer as norm
    monkeypatch.setenv("RAG1_DISABLED", "1")
    assert norm.normalizer_enabled() is False


def test_leaf_sound_signatures(compile_zip):
    # the detector's leaf-level signatures, pinned: sound / unknown / self-loop
    sound = _zip_leaves(compile_zip("a cat is a mammal").items)[0]
    assert _leaf_sound(sound) is True
    unknown = _zip_leaves(compile_zip("a wug is a blicket").items)[0]
    assert _leaf_sound(unknown) is False

# ------------------------------------------------------------------------------------------------
# The storm-sequel fix (2026-07-14): subordination must survive compilation.
#   L1 (author-ruled a): TEMPORAL folds CONV — «when a person say false he is being wrong» flattened
#      to three bare AND leaves and re-fed the chainer (the drafted-core's parked TEMPORAL→AND).
#   L2: a FRAGMENT that IS a subordinate («because you think») carries its mark on the ROOT — the
#      parser now stashes it (TKStatement.marker) and the compiler folds the whole statement with
#      the subordinate operator: a fragment is a relation HALF, never a standalone assertion.
# Safety property, both layers: a non-AND op is GATE-VISIBLE (_zip_is_asserted) — the leaked shapes
# can never again become chainer rules. Full-pipeline band-asserts via compile_zip.
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

from lib.core.tk import TKOperator
from lib.core.tkzip import TKZipContent
from lib.core.kb_extract import extract_rules, _zip_is_asserted


def _leaf_ops(zp):
    out = []
    def walk(item):
        c = item.content
        if isinstance(c, TKZipContent):
            out.append(item.op)
        elif isinstance(c, list):
            for ch in c:
                walk(ch)
    walk(zp.items)
    return out


def _no_fuel(zp, original):
    doc = SimpleNamespace(zip=zp, original=original, id="sub-test")
    assert extract_rules([doc]) == []


# ---- L1: the sequel sentence and its "when" family -------------------------------------------------

def test_when_rule_folds_conditionally_and_yields_no_fuel(compile_zip):
    s = "when a person say false he is being wrong"
    zp = compile_zip(s)
    assert not _zip_is_asserted(zp.items)            # the gate SEES it now
    assert TKOperator.CONV in _leaf_ops(zp)          # the temporal fold is conditional
    _no_fuel(zp, s)                                  # the storm class is closed

def test_when_postposed_also_folds(compile_zip):
    s = "a person is wrong when he says false"
    zp = compile_zip(s)
    assert not _zip_is_asserted(zp.items)
    _no_fuel(zp, s)


# ---- L2: root-mark fragments ------------------------------------------------------------------------

def test_because_fragment_is_not_an_assertion(compile_zip):
    s = "because you think"
    zp = compile_zip(s)
    assert not _zip_is_asserted(zp.items)            # a relation half, never a standalone assertion
    assert TKOperator.CONV in _leaf_ops(zp)
    _no_fuel(zp, s)

def test_because_fragment_with_class_subject_yields_no_fuel(compile_zip):
    # the harvest's «because a dog is an animal» shape — a class-subject fragment must not
    # become an edge/rule
    s = "because a coin stores information"
    zp = compile_zip(s)
    assert not _zip_is_asserted(zp.items)
    _no_fuel(zp, s)


# ---- no regression: plain assertions stay asserted --------------------------------------------------

def test_plain_assertion_still_asserted(compile_zip):
    zp = compile_zip("a cat is an animal")
    assert _zip_is_asserted(zp.items)

def test_full_causal_sentence_keeps_subordinate_op(compile_zip):
    # the embedded-because path (unchanged mechanism) still folds non-AND
    zp = compile_zip("I go to sleep because I'm tired")
    assert not _zip_is_asserted(zp.items)

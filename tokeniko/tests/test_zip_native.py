# ------------------------------------------------------------------------------------------------
# ZIP-NATIVE ASSEMBLY — the equivalence harness (instrument arc #2, P1; 2026-07-15).
#
# The discipline for lib/core/zip_native.py: a derived conclusion assembled NATIVELY must be the
# same thought the old render → parse → recompile round trip produced — same conclusion_key, same
# flags, same per-role geometry, same evaluator verdict — WITHOUT the parser. Where the two
# disagree, the compiled form must be the one at fault (the round-trip corruption class this arc
# exists to kill), and the disagreement is pinned here as evidence, not papered over.
# ------------------------------------------------------------------------------------------------
import math

import pytest

from lib.core.evaluation_harness import _zip_leaves, conclusion_key
from lib.core.tk import TKQuantifier
from lib.core.zip_native import assemble_conclusion_zip


def _cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(x * x for x in b))
    return (num / (da * db)) if da and db else (1.0 if da == db else 0.0)


def _assert_equivalent(compiled, native):
    # the semantic dedup key IS the meaning — it must be identical
    assert conclusion_key(native) == conclusion_key(compiled)
    c, n = _zip_leaves(compiled.items)[0], _zip_leaves(native.items)[0]
    for f in ("negated", "quantifier", "modal", "reflexive", "unknown",
              "dubitative", "ironic", "imperative", "wh_role"):
        assert getattr(c, f, None) == getattr(n, f, None), f
    assert (c.senses or {}) == (n.senses or {})
    assert (c.identities or {}) == (n.identities or {})
    for role in ("subject", "predicate", "direct"):
        cv, nv = getattr(c, role) or [0.0] * 3237, getattr(n, role) or [0.0] * 3237
        assert _cos(cv[300:3225], nv[300:3225]) == pytest.approx(1.0, abs=1e-6), f"{role} semantic"
        assert sum(abs(x) for x in nv[:300]) == 0.0, f"{role} marker (canonical SVO = zeros)"
        assert nv[3225:] == [0.0] * 12, f"{role} spacetime (neutral)"
    assert native.map == [0.0] * 8


# ---- clean shapes: native ≡ compiled, field for field --------------------------------------------

def test_membership_equivalent(compile_zip):
    compiled = compile_zip("a cat is a mammal")
    native = assemble_conclusion_zip("cat.n.01", "mammal.n.01", subject_kind="class")
    _assert_equivalent(compiled, native)


def test_negated_verb_object_equivalent(compile_zip):
    compiled = compile_zip("a software does not reach truth")
    native = assemble_conclusion_zip("software.n.01", "reach.v.01", "truth.n.01",
                                     negated=True, subject_kind="class")
    _assert_equivalent(compiled, native)


def test_adjective_equivalent(compile_zip):
    compiled = compile_zip("a homo is mortal")
    native = assemble_conclusion_zip("homo.n.02", "mortal.a.01", subject_kind="class")
    _assert_equivalent(compiled, native)


def test_first_person_fact_equivalent(compile_zip, _io):
    from lib.core.io import get_tokeniko
    tok = get_tokeniko()
    compiled = compile_zip("I exist")
    native = assemble_conclusion_zip(tok.uid, "exist.v.01", subject_kind="individual")
    _assert_equivalent(compiled, native)
    n = _zip_leaves(native.items)[0]
    assert n.identities.get("subject") == tok.uid
    assert n.quantifier == TKQuantifier.GENERIC  # bare subject, probe-pinned


# ---- the corruption exhibit: verb+object, where NATIVE is right and the round trip is not --------

def test_verb_object_native_truthful_where_roundtrip_splits(compile_zip):
    # «a cat feels curiosity» through the ROUND TRIP: the parser splits it into two leaves and
    # LOSES the direct object — the exact corruption class this arc kills (stored theorems carry
    # the pin-stuttered form). Native carries the derivation's truth: one leaf, object intact.
    native = assemble_conclusion_zip("cat.n.01", "feel.v.01", "curiosity.n.01", subject_kind="class")
    assert conclusion_key(native) == (("cat.n.01", "feel.v.01", "curiosity.n.01", False, False),)
    compiled = compile_zip("a cat feels curiosity")
    compiled_leaves = _zip_leaves(compiled.items)
    if len(compiled_leaves) != 1:  # the split — documented, not required (a parser fix may heal it)
        assert conclusion_key(compiled) != conclusion_key(native)


@pytest.mark.pipeline  # touches Mongo without the _io fixture
def test_stutter_key_collapses_to_native():
    # the stored round-trip stutter (same leaf twice, from pin-over-split) must dedup-match the
    # honest native single leaf — conclusion_key set-collapses identical leaves (dedup continuity
    # without a migration).
    from types import SimpleNamespace
    from lib.core.tkzip import TKZip, TKZipItem
    native = assemble_conclusion_zip("cat.n.01", "feel.v.01", "curiosity.n.01", subject_kind="class")
    leaf = _zip_leaves(native.items)[0]
    stuttered = TKZip(map=[0.0] * 8, items=TKZipItem(
        content=[TKZipItem(content=leaf), TKZipItem(content=leaf.model_copy(deep=True))]))
    assert conclusion_key(stuttered) == conclusion_key(native)


# ---- the deep check: the EVALUATOR cannot tell them apart ----------------------------------------

def test_evaluator_verdicts_identical(compile_zip, _io):
    from lib.core.evaluation_harness import evaluate_zip
    for sentence, structure in [
        ("a cat is a mammal", ("cat.n.01", "mammal.n.01", None, False)),
        ("a homo is mortal", ("homo.n.02", "mortal.a.01", None, False)),
    ]:
        compiled_r = evaluate_zip(compile_zip(sentence))["result"]
        s, p, o, neg = structure
        native_r = evaluate_zip(assemble_conclusion_zip(s, p, o, neg, subject_kind="class"))["result"]
        assert native_r.status == compiled_r.status, sentence
        assert native_r.truth == pytest.approx(compiled_r.truth, abs=0.05), sentence


# ---- honesty gates --------------------------------------------------------------------------------

@pytest.mark.pipeline  # touches Mongo without the _io fixture
def test_unknown_sense_refused():
    assert assemble_conclusion_zip("wug.n.01", "mammal.n.01", subject_kind="class") is None
    assert assemble_conclusion_zip("cat.n.01", "blicket.v.01", subject_kind="class") is None


def test_vectorless_individual_gets_honest_zeros(_io):
    from lib.core.io import get_tokeniko
    native = assemble_conclusion_zip(get_tokeniko().uid, "exist.v.01", subject_kind="individual")
    leaf = _zip_leaves(native.items)[0]
    assert sum(abs(x) for x in leaf.subject[300:3225]) == 0.0  # identity carries the reference
    assert leaf.identities.get("subject")


# ---- the seam: TheoremService.materialize's native entrance ---------------------------------------

def test_materialize_native_entrance_and_dedup(_io):
    from lib.core.memory import MEMProvenance
    from lib.core.models import TKTheoremDoc
    from api.services import TheoremService
    from api.services.theorem_service import UngroundableConclusionError
    tok, ai = _io
    svc = TheoremService(tok, ai)
    prov = MEMProvenance(premises=["test:native"], chain="native seam test", derived_by="wondering")
    structure = {"subject": "whale.n.02", "predicate": "sing.v.01", "subject_kind": "class"}
    try:
        t1 = svc.materialize("a whale sings", prov, structure=structure)
        assert t1.original == "a whale sings" and t1.raw is None
        assert conclusion_key(t1.zip) == (("whale.n.02", "sing.v.01", None, False, False),)
        # idempotent: the same STRUCTURE converges onto the held theorem, whatever the wording
        t2 = svc.materialize("whales do sing", prov, structure=structure)
        assert t2.id == t1.id
        # the honesty gate surfaces as a domain error (422 at the route)
        with pytest.raises(UngroundableConclusionError):
            svc.materialize("a wug blickets", prov,
                            structure={"subject": "wug.n.01", "predicate": "blicket.v.01",
                                       "subject_kind": "class"})
    finally:
        TKTheoremDoc.find({"original": "a whale sings"}).delete().run()  # Bunnet: .run() executes

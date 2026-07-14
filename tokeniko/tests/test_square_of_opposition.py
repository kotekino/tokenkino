# ------------------------------------------------------------------------------------------------
# The square of opposition + the modality carrier (2026-07-14, the Socratic dialogue — S0).
# The dialogue's OWN sentences are the regression corpus: the kernel docked both teachers for
# logically-consistent quantified speech (subcontraries read as P∧¬P) and read the author's
# ◇P ∧ ◇¬P as self-contradiction (the dropped modal). After the fix, the same sentences must
# classify CONSISTENT; the genuine contradictions must still fire.
# ------------------------------------------------------------------------------------------------
from lib.core.kb_extract import extract_generic_isa_edges, _leaf_is_crisp, _zip_leaves
from lib.llc.evaluator import evaluator_classifyForm


def _form(compile_zip, s, antonyms=None):
    return evaluator_classifyForm(compile_zip(s), antonyms=antonyms)


# ---- the dialogue's bounced sentences: now consistent ------------------------------------------------

def test_subcontraries_are_consistent(compile_zip):
    # hellen -0.15 (second): ∃P ∧ ∃¬P — the canonical subcontraries, usually the truth together
    f = _form(compile_zip, "some softwares implement a mind, and some softwares do not implement a mind")
    assert not f.contradiction, f.detail


def test_negated_universal_plus_existential_consistent(compile_zip):
    # hellen -0.15 (first): ¬∀ + ∃ — jointly they SAY "some are, some aren't"
    f = _form(compile_zip, "not every software is a mind. only some softwares are minds.")
    assert not f.contradiction, f.detail


def test_modal_pair_is_consistent(compile_zip):
    # kotekino -0.2: ◇P ∧ ◇¬P («softwares CAN think and softwares can not think») is trivially consistent
    f = _form(compile_zip, "a software can think and a software can not think")
    assert not f.contradiction, f.detail


# ---- genuine contradictions still fire -----------------------------------------------------------------

def test_universal_vs_its_negation_contradicts(compile_zip):
    # A vs O contradictories: «all S are P» + «not all S are P»
    f = _form(compile_zip, "all softwares are minds and not all softwares are minds")
    assert f.contradiction
    assert "square of opposition" in (f.detail or "")


def test_none_vs_some_contradicts(compile_zip):
    # E vs I contradictories: «no S is P» + «some S are P»
    f = _form(compile_zip, "no software is a mind and some softwares are minds")
    assert f.contradiction


def test_all_vs_none_contraries_contradict(compile_zip):
    # A vs E contraries (Aristotelian — kind-level class atoms): cannot both hold
    f = _form(compile_zip, "all softwares are minds and no software is a mind")
    assert f.contradiction


def test_definite_crisp_contradiction_still_fires(compile_zip):
    # the original design case: a DEFINITE individual asserted P and ¬P
    f = _form(compile_zip, "the cat is dead and the cat is not dead")
    assert f.contradiction


def test_contrary_predicates_still_fire_on_definite(compile_zip, _io):
    # «the cat is dead and alive» — the antonym mutex on a crisp subject survives the square-gate
    from lib.core.evaluation_harness import _make_antonym_reader
    f = _form(compile_zip, "the cat is dead and alive", antonyms=_make_antonym_reader())
    assert f.contradiction


def test_existential_antonyms_do_not_fire(compile_zip, _io):
    # «some cats are dead and some cats are alive» — TRUE in every barn; the antonym mutex must
    # not apply to existential corners
    from lib.core.evaluation_harness import _make_antonym_reader
    f = _form(compile_zip, "some cats are dead and some cats are alive", antonyms=_make_antonym_reader())
    assert not f.contradiction, f.detail


# ---- the modality carrier + the extractor gate ---------------------------------------------------------

def test_modal_flag_carried(compile_zip):
    zp = compile_zip("a software can be a mind")
    leaves = _zip_leaves(zp.items)
    assert any(getattr(l, "modal", None) == "possibility" for l in leaves)
    assert not all(_leaf_is_crisp(l) for l in leaves)


def test_plain_copular_not_modal(compile_zip):
    zp = compile_zip("a cat is a mammal")
    assert all(getattr(l, "modal", None) is None for l in _zip_leaves(zp.items))


def test_can_be_mints_no_edge(compile_zip):
    # THE some→all leap's root, closed: «a software can be a mind» yields ZERO is_a edges
    from types import SimpleNamespace
    zp = compile_zip("a software can be a mind")
    doc = SimpleNamespace(zip=zp, original="a software can be a mind", id="sq-test")
    edges, stats = extract_generic_isa_edges([doc], parents=lambda s: [])
    assert edges == []
    assert stats.get("modal_skip", 0) >= 1


def test_plain_generic_still_mints(compile_zip):
    # the crisp generic copular keeps minting (the step-2 design case)
    from types import SimpleNamespace
    zp = compile_zip("a cat is a mammal")
    doc = SimpleNamespace(zip=zp, original="a cat is a mammal", id="sq-test2")
    edges, _ = extract_generic_isa_edges([doc], parents=lambda s: [])
    assert any(e["subject"] == "cat.n.01" and e["object"] == "mammal.n.01" for e in edges)


def test_modal_claim_abstains(compile_zip):
    # the grounder neither proves nor refutes a ◇-claim — honest INSUFFICIENT
    from lib.core.evaluation_harness import evaluate_zip
    r = evaluate_zip(compile_zip("a software can be a mind"))["result"]
    assert r.status.value == "insufficient_knowledge"

# ------------------------------------------------------------------------------------------------
# THE DIRECT FACT-MATCH (2026-07-23, §2's two grounding leads — brief 2026-07-23-direct-fact-match).
# The evaluator gains a key-for-key consultation of stored single-clause knowledge (e_facts): a
# claim's conclusion key (subject/predicate/direct role keys + the negated flag) looked up among the
# active axiom/theorem zips whose single leaf carries the same keys. Same polarity CONFIRMS, opposite
# REFUTES — an EXACT match, identity-aware (role_key), never geometry.
#
# The two live specimens as regression:
#   1. «... does not learn» refuted by a stored «I learn» (identity subject) — grounds FALSE.
#   2. «is gold beautiful?» answered YES by the active theorem «gold is beautiful», priced by the
#      fact's TRUST — never at truth 1.0.
#
# CHAINER / DIRECT-MATCH INTERPLAY (the dying finding, endorsed 2026-07-23). In the current tree the
# e_facts direct match is SHADOWED end-to-end by two pre-existing grounders: a CLASS-subject property
# statement is also extracted as a generic property rule, so the forward-chainer decides those cases;
# an INDIVIDUAL-subject claim is decided by evaluator_groundIndividualFact (which already refutes
# opposite-polarity). The direct match runs only as the fallback neither reaches. What the finding
# actually corrected is the PRICING: the self-grounding chain used to answer «is gold beautiful?» at
# truth 1.0, ignoring the theorem's trust — now the RESOLVED polar path applies the same min-premise
# trust plumbing the reductio prover always did (_polar_answer), so a proof through a 0.x-trusted
# theorem never speaks at 1.0. The unit tests below exercise the e_facts primitive directly; the
# end-to-end tests pin the observable behavior (verdict + honest confidence) whichever grounder decides.
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

import pytest

from lib.core.evaluation import AnswerVerdict
from lib.llc.evaluator.e_facts import claim_key, render_fact, direct_fact_match
from tests.asserts import assert_resolved_true, assert_resolved_false, assert_insufficient


@pytest.fixture()
def kb_facts(_io, compile_zip):
    """Insert active single-clause facts (axioms/theorems) into the sandbox + reset the KB cache.
    FUNCTION-scoped: every test gets a clean world, and everything it inserts is swept by `original`
    on teardown (the living mind is never touched — sandbox only)."""
    from lib.core.io import get_tokeniko
    from lib.core.memory import MEMChannels
    from lib.core.models import TKAxiomDoc, TKTheoremDoc
    from lib.core import evaluation_harness
    tok = get_tokeniko()
    created: list = []  # (motor_collection, original)

    def _reset():
        evaluation_harness._kb_cache = None
        evaluation_harness._kb_cache_fp = None

    def add_axiom(sentence, trusted=1.0):
        doc = TKAxiomDoc(original=sentence, zip=compile_zip(sentence), sourceId=str(tok.id),
                         channel=MEMChannels.INTERNAL, archived=False, readonly=True,
                         trusted=trusted).insert()
        created.append((TKAxiomDoc, sentence))
        _reset()
        return doc

    def add_theorem(sentence, trusted=0.9):
        doc = TKTheoremDoc(original=sentence, zip=compile_zip(sentence), sourceId=str(tok.id),
                           channel=MEMChannels.INTERNAL, archived=False, trusted=trusted).insert()
        created.append((TKTheoremDoc, sentence))
        _reset()
        return doc

    _reset()
    yield SimpleNamespace(add_axiom=add_axiom, add_theorem=add_theorem)
    for cls, original in created:
        cls.get_motor_collection().delete_many({"original": original})
    _reset()


# --- the primitive, unit ------------------------------------------------------------------------

def test_claim_key_and_render_unit():
    # identity-FIRST read (role_key), the (subject, predicate, direct) key, and the compact citation.
    leaf = SimpleNamespace(senses={"predicate": "learn.v.01"},
                           identities={"subject": "tokeniko"}, negated=True)
    assert claim_key(leaf) == ("tokeniko", "learn.v.01", None)
    assert "NOT" in render_fact(leaf) and "learn.v.01" in render_fact(leaf)
    # an unanchored claim (no subject) is honestly unmatchable
    bare = SimpleNamespace(senses={"predicate": "learn.v.01"}, identities={}, negated=False)
    assert direct_fact_match(bare, [], []) is None


def test_primitive_polarity_both_ways(compile_zip, leaves):
    # over REAL compiled zips: same polarity CONFIRMS, opposite REFUTES; axioms tried before theorems.
    fact = compile_zip("gold is beautiful")                        # affirmative
    same = leaves(compile_zip("gold is beautiful"))[0]
    opp = leaves(compile_zip("gold is not beautiful"))[0]
    m_same = direct_fact_match(same, [], [fact])
    m_opp = direct_fact_match(opp, [], [fact])
    assert m_same is not None and m_same.kind == "theorem" and m_same.confirms is True
    assert m_opp is not None and m_opp.confirms is False
    # no key match -> None
    assert direct_fact_match(leaves(compile_zip("gold is rare"))[0], [], [fact]) is None


# --- specimen 1: the assertion path (grounds FALSE, the fact cited) ------------------------------

def test_negated_claim_refuted_by_stored_affirmative_identity(kb_facts, evaluate):
    # THE live specimen: «tokeniko does not learn» must ground FALSE against the self-axiom «I learn»
    # (both subjects resolve to tokeniko's identity uid), with the fact cited in the derivation.
    # INTERPLAY: an individual subject is decided by evaluator_groundIndividualFact (opposite-polarity
    # refutation, e_chaining) — e_facts is the shadowed fallback. The observable FALSE is what matters.
    kb_facts.add_axiom("I learn")
    r = evaluate("tokeniko does not learn")
    assert_resolved_false(r)
    assert any("learn" in d for d in r.derivation), r.derivation


def test_class_subject_claim_refuted_by_theorem(kb_facts, evaluate):
    # a stored «gold is beautiful» theorem REFUTES the class-subject assertion «gold is not beautiful».
    # INTERPLAY: a class-subject property theorem is extracted as a generic property rule, so the
    # forward-chainer KB-refutes this first (e_facts is the shadowed fallback). Either way: grounded
    # FALSE citing the property.
    kb_facts.add_theorem("gold is beautiful")
    r = evaluate("gold is not beautiful")
    assert_resolved_false(r)
    assert any("beautiful" in d for d in r.derivation), r.derivation


def test_class_subject_claim_confirmed_by_theorem(kb_facts, evaluate):
    # same polarity CONFIRMS: «gold is beautiful» asserted against the stored «gold is beautiful»
    # (chainer path — see the interplay note above; e_facts is the shadowed fallback).
    kb_facts.add_theorem("gold is beautiful")
    r = evaluate("gold is beautiful")
    assert_resolved_true(r)
    assert any("beautiful" in d for d in r.derivation), r.derivation


# --- specimen 2: the polar path (YES/NO, priced by the fact's trust — never truth 1.0) -----------

def test_polar_question_priced_by_trust_not_truth(kb_facts, answer):
    # THE dying finding: «is gold beautiful?» self-grounds through the stored «gold is beautiful»
    # theorem (extracted as a generic property rule) -> YES. It MUST be priced by the chain's
    # min-premise trust, never truth 1.0. A generic rule from a 0.9 theorem prices at 0.7 (the
    # generic-rule defeasibility floor, _GENERIC_RULE_TRUST). The invariant is «strictly below 1.0»;
    # the 0.7 pin documents the exact plumbing.
    kb_facts.add_theorem("gold is beautiful", trusted=0.9)
    a = answer("is gold beautiful?")
    assert a.verdict == AnswerVerdict.YES
    assert a.confidence < 1.0 - 1e-6, a.confidence          # never truth-priced at 1.0 (the finding)
    assert abs(a.confidence - 0.7) < 1e-6, a.confidence     # min-premise: generic rule from a 0.9 theorem


def test_low_trust_fact_low_confidence(kb_facts, answer):
    # min-premise honesty end to end (ruling 2, NO new knob): a 0.3-trust theorem prices the
    # self-grounded YES at 0.3 (min(0.3, 0.7) — the theorem's own trust is below the generic floor).
    # The same YES, a quieter voice.
    kb_facts.add_theorem("gold is beautiful", trusted=0.3)
    a = answer("is gold beautiful?")
    assert a.verdict == AnswerVerdict.YES
    assert abs(a.confidence - 0.3) < 1e-6, a.confidence


# --- negation symmetry, both ways ---------------------------------------------------------------

def test_stored_negated_fact_refutes_affirmative_question(kb_facts, answer):
    # a stored NEGATED fact «gold is not beautiful» answers the affirmative «is gold beautiful?» NO.
    kb_facts.add_theorem("gold is not beautiful")
    a = answer("is gold beautiful?")
    assert a.verdict == AnswerVerdict.NO, (a.verdict, a.reason)


def test_stored_negated_fact_confirms_negated_question(kb_facts, answer):
    # ...and CONFIRMS a matching negated question «is gold not beautiful?» -> YES (same polarity).
    kb_facts.add_theorem("gold is not beautiful")
    a = answer("is gold not beautiful?")
    assert a.verdict == AnswerVerdict.YES, (a.verdict, a.reason)


# --- the fences: v1 single-clause, honest IDK, reductio still reachable --------------------------

def test_multiclause_claim_skips_direct_match(kb_facts, evaluate):
    # v1 scope (ruling 3): a MULTI-clause claim skips the direct match — «tokeniko does not learn and
    # gold is beautiful» is NOT resolved FALSE by the single-clause machinery; the existing path
    # handles it (here: insufficient, unchanged).
    kb_facts.add_axiom("I learn")
    r = evaluate("tokeniko does not learn and gold is beautiful")
    assert_insufficient(r)


def test_no_matching_fact_stays_idk(kb_facts, answer):
    # no stored fact carries the claim's key -> the direct match returns nothing and the answer stays
    # an honest I-don't-know (a «gold is beautiful» fact never answers «is gold precious?»).
    kb_facts.add_theorem("gold is beautiful")
    a = answer("is gold precious?")
    assert a.verdict == AnswerVerdict.UNKNOWN, (a.verdict, a.reason)


def test_direct_answer_yields_to_reductio_when_no_match(kb_facts, compile_zip):
    # the ORDER contract: with no direct match, `_try_direct_answer` returns None so the reductio
    # prover (unchanged, the last resort) still gets its turn. (Its own end-to-end proof lives in
    # test_reductio_loop.py; here we pin that the new step never shadows it.)
    from lib.core import evaluation_harness
    kb = evaluation_harness._load_active_kb()
    leaves = evaluation_harness._zip_leaves(compile_zip("is gold precious?").items)
    assert evaluation_harness._try_direct_answer(leaves, kb) is None

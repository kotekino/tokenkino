# ------------------------------------------------------------------------------------------------
# THE CONSTRUCTIVE REDUCTIO — §0 slice 4 (2026-07-18, the author's "take the momentum" ruling).
# Proof by contradiction as a prover inside the answer machinery: before conceding IDK on a polar
# question, assume the claim (or its negation), forward-saturate, and if the derivation mirror
# fires on a NEW conflict RESTING ON the assumption, the assumption is refuted — its opposite is
# proven (h ⊢ ⊥ ⇒ ¬h). The genuinely new power is CONTRAPOSITION (forward chaining cannot walk
# backwards): the incident's own «is tokeniko a mammal?» — IDK yesterday — becomes a proven NO
# through «all mammals are animals» + «no software is an animal» + «tokeniko is a software».
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

import pytest

from lib.core.memory import MEMChannels, MEMProvenance
from lib.core.tk import TKQuantifier
from lib.llc.evaluator import evaluator_reductio

# the contraposition world, distilled: mammals are animals; no software is an animal; tok is software.
_PARENTS = lambda s: []
_RULES = [
    {"subject": "mammal.n.01", "predicate": "animal.n.01", "object": None, "negated": False,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-mammal-animal"},
    {"subject": "software.n.01", "predicate": "animal.n.01", "object": None, "negated": True,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-software-not-animal"},
]
_FACT = {"subject_uid": "tok@test", "klass_sense": "software.n.01",
         "predicate": "software.n.01", "negated": False, "source_id": "fact-tok-software"}


def _content(pred="mammal.n.01", uid="tok@test", sense=None, negated=False,
             quantifier=TKQuantifier.GENERIC, direct=None):
    senses = {"predicate": pred}
    if sense:
        senses["subject"] = sense
    if direct:
        senses["direct"] = direct
    return SimpleNamespace(senses=senses, identities={"subject": uid} if uid else {},
                           negated=negated, quantifier=quantifier)


# ---- the prover (pure — synthetic rules/facts) ---------------------------------------------------

def test_contraposition_refutes_the_individual_claim():
    # THE MAMMAL QUESTION: «is tok a mammal?» — forward-unreachable (IDK); assume it -> mammal
    # joins the closure -> animal follows -> «no software is an animal» fires -> the mirror.
    out = evaluator_reductio(_content(), _RULES, _PARENTS, [_FACT])
    assert out is not None
    truth, chain, premises = out
    assert truth < 0.15                                 # the claim is REFUTED (proven NO)
    assert chain.startswith("reductio: assume")
    assert "the assumption is false" in chain
    assert "hypothesis" not in premises                 # the marker is stripped from the proof
    assert set(premises) >= {"r-mammal-animal", "r-software-not-animal", "fact-tok-software"}


def test_contraposition_refutes_the_class_claim():
    # «is a software a mammal?» — same proof, class subject (the hypothesis injects as a rule)
    out = evaluator_reductio(_content(uid=None, sense="software.n.01"), _RULES, _PARENTS, [])
    assert out is not None
    truth, chain, premises = out
    assert truth < 0.15
    assert set(premises) >= {"r-mammal-animal", "r-software-not-animal"}


def test_negated_claim_is_proven_true():
    # «is tok NOT a mammal?» — assuming the un-negated twin conflicts -> the negated claim PROVEN
    out = evaluator_reductio(_content(negated=True), _RULES, _PARENTS, [_FACT])
    assert out is not None
    truth, chain, premises = out
    assert truth > 0.85                                 # YES, he is indeed not a mammal


def test_no_proof_stays_none():
    # nothing connects stone to the rules — no assumption forces an absurd; the IDK stands
    assert evaluator_reductio(_content(pred="stone.n.01"), _RULES, _PARENTS, [_FACT]) is None


def test_poisoned_baseline_proves_nothing():
    # the incident's poisoned ground: the baseline ALREADY conflicts on (animal) for this seed —
    # an old absurd convicts no new assumption (mirror discipline; signature-matched)
    poison = _RULES + [
        {"subject": "software.n.01", "predicate": "mind.n.01", "object": None, "negated": False,
         "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-sw-mind"},
        {"subject": "mind.n.01", "predicate": "animal.n.01", "object": None, "negated": False,
         "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-mind-animal"},
    ]
    out = evaluator_reductio(_content(pred="animal.n.01"), poison, _PARENTS, [_FACT])
    assert out is None                                  # the animal absurd predates the assumption


def test_v1_scope_gates():
    # non-noun predicate / transitive claim / bad quantifier / no subject -> the prover declines
    assert evaluator_reductio(_content(pred="run.v.01"), _RULES, _PARENTS, [_FACT]) is None
    assert evaluator_reductio(_content(direct="meat.n.01"), _RULES, _PARENTS, [_FACT]) is None
    assert evaluator_reductio(_content(quantifier=TKQuantifier.NEGATIVE),
                              _RULES, _PARENTS, [_FACT]) is None
    assert evaluator_reductio(_content(uid=None), _RULES, _PARENTS, [_FACT]) is None


# ---- the firing site (pipeline — the real question path end-to-end) ------------------------------

@pytest.fixture()
def contraposition_world(_io, compile_zip):
    """«all mammals are animals» + «no software is an animal» as taught theorems (the fixture
    KB carries neither); the software membership rides the question's own subject."""
    from lib.core import evaluation_harness
    from lib.core.models import TKTheoremDoc
    docs = []
    for s in ("all mammals are animals", "no software is an animal"):
        d = TKTheoremDoc(
            original=s, zip=compile_zip(s), sourceId="prof@ptest:1",
            channel=MEMChannels.INTERNAL, archived=False, trusted=0.7,
            provenance=MEMProvenance(premises=["taught:prof@ptest:1"], chain="t",
                                     derived_by="teaching"),
        )
        d.insert()
        docs.append(d)
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None
    yield docs
    TKTheoremDoc.get_motor_collection().delete_many(
        {"original": {"$in": ["all mammals are animals", "no software is an animal"]}})
    evaluation_harness._kb_cache = None
    evaluation_harness._kb_cache_fp = None


def test_polar_idk_becomes_a_proven_no(contraposition_world, answer):
    # «is a software a mammal?» — direct grounding cannot decide it (mammal is forward-unreachable
    # from software); the prover assumes it, derives the absurd, and answers a PROVEN NO.
    a = answer("is a software a mammal?")
    assert a is not None and a.kind.value == "polar"
    assert a.verdict.value == "no"
    assert a.reason == "proved by contradiction"
    assert any("reductio" in d for d in a.derivation)
    assert 0.5 < a.confidence <= 0.75                   # extremity × the taught premises' 0.7 trust


def test_unprovable_question_still_answers_idk(contraposition_world, answer):
    # the prover must not manufacture certainty: an unconnected question stays an honest IDK
    a = answer("is a software a stone?")
    assert a is not None and a.verdict.value == "unknown"

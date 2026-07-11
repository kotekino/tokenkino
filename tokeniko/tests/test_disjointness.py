"""Negative copular universals as ONE-directional disjointness (the 2026-07-11 live-play gap).

«no mammal is a reptile» — taught live and found inert: the extractor deferred NEGATIVE bare
copular noun-nouns as future work, and the chainer's membership fixpoint is positive-only. Now:
  - the EXTRACTOR keeps an effectively-negative bare copular as a NEGATED MEMBERSHIP rule
    (positive ones stay edge territory);
  - the CHAINER fires it in the derivation pass as a negated class-membership conclusion —
    NEVER a closure member (reptile's ancestors are not dog's);
  - chainGround's existing negation parity then KB-refutes «a dog is a reptile» (truth≈0,
    premises cite the axiom) and corroborates «a dog is not a reptile».
Symmetric disjointness (the mirror direction) stays future work — teach the mirror axiom.
"""
from types import SimpleNamespace

from lib.core.tk import TKQuantifier
from lib.core.tkzip import TKZipContent, TKZipItem
from lib.core.kb_extract import extract_rules
from lib.llc.evaluator.e_chaining import evaluator_chainGround, evaluator_forwardChain


def _parents(sense):
    return {"dog.n.01": ["mammal.n.01"], "mammal.n.01": ["animal.n.01"]}.get(sense, [])


_NO_MAMMAL_IS_REPTILE = {
    "kind": "membership", "subject": "mammal.n.01", "predicate": "reptile.n.01", "object": None,
    "negated": True, "cond_props": [], "strength": "universal",
    "original": "no mammal is a reptile", "source_id": "ax-nomam",
}
_REPTILES_CRAWL = {  # keyed on reptile — must NEVER fire for a dog (closure non-pollution)
    "kind": "property", "subject": "reptile.n.01", "predicate": "crawl.v.01", "object": None,
    "negated": False, "cond_props": [], "strength": "universal",
    "original": "all reptiles crawl", "source_id": "ax-crawl",
}


# ---- the chainer: a negated membership rule derives, never joins the closure ------------------------

def test_negated_membership_derives_a_negated_conclusion():
    derived, chains = evaluator_forwardChain("dog.n.01", None, [_NO_MAMMAL_IS_REPTILE],
                                             _parents, [])
    hit = next((d for d in derived if d["predicate"] == "reptile.n.01"), None)
    assert hit is not None and hit["negated"] is True
    assert "ax-nomam" in hit["premises"]
    assert "are NOT reptile.n.01" in hit["chain"]


def test_negated_membership_never_pollutes_the_closure():
    derived, _ = evaluator_forwardChain("dog.n.01", None,
                                        [_NO_MAMMAL_IS_REPTILE, _REPTILES_CRAWL], _parents, [])
    assert not any(d["predicate"] == "crawl.v.01" for d in derived), \
        "reptile entered the closure through a NEGATED membership rule"


# ---- chainGround: refute the positive claim, corroborate the negative one ---------------------------

def _claim(negated=False):
    return SimpleNamespace(senses={"subject": "dog.n.01", "predicate": "reptile.n.01"},
                           identities={}, negated=negated)


def test_positive_claim_is_kb_refuted():
    got = evaluator_chainGround(_claim(negated=False), [_NO_MAMMAL_IS_REPTILE], _parents, [])
    assert got is not None
    truth, chain, premises = got
    assert truth < 0.15
    assert "KB-refuted" in chain
    assert "ax-nomam" in premises


def test_negative_claim_is_corroborated():
    got = evaluator_chainGround(_claim(negated=True), [_NO_MAMMAL_IS_REPTILE], _parents, [])
    assert got is not None
    truth, chain, _ = got
    assert truth > 0.85
    assert "KB-refuted" not in chain


# ---- WSD-canonicalization in the chainer (the live dog.n.03 specimen, unanimity-gated) --------------

def _parents_wsd(sense):
    # dog.n.03 ("a fellow") never reaches mammal; dog.n.01 does — the live blocker
    return {"dog.n.01": ["mammal.n.01"], "dog.n.03": ["person.n.01"],
            "mammal.n.01": ["animal.n.01"], "person.n.01": ["organism.n.01"]}.get(sense, [])


def _senses_of(sense):
    return ["dog.n.01", "dog.n.03"] if sense.startswith("dog.") else [sense]


def _claim_wsd(subject="dog.n.03", negated=False):
    return SimpleNamespace(senses={"subject": subject, "predicate": "reptile.n.01"},
                           identities={}, negated=negated)


def test_canonicalization_rescues_the_refutation():
    got = evaluator_chainGround(_claim_wsd(), [_NO_MAMMAL_IS_REPTILE], _parents_wsd, [],
                                senses_of=_senses_of)
    assert got is not None
    truth, chain, premises = got
    assert truth < 0.15
    assert "WSD-canonicalized dog.n.03->dog.n.01" in chain
    assert "ax-nomam" in premises


def test_the_chosen_sense_wins_outright_when_it_decides():
    got = evaluator_chainGround(_claim_wsd(subject="dog.n.01"), [_NO_MAMMAL_IS_REPTILE],
                                _parents_wsd, [], senses_of=_senses_of)
    truth, chain, _ = got
    assert truth < 0.15 and "WSD-canonicalized" not in chain


def test_split_sibling_verdicts_abstain():
    # a second rule makes dog.n.03 (person) CORROBORATE what dog.n.01 (mammal) refutes -> ambiguous
    person_is_reptile = {  # property-shaped so it lands in the derivation pass
        "kind": "property", "subject": "person.n.01", "predicate": "reptile.n.01", "object": None,
        "negated": False, "cond_props": [], "strength": "universal",
        "original": "all persons are reptiles (test)", "source_id": "ax-weird",
    }
    got = evaluator_chainGround(SimpleNamespace(senses={"subject": "dog.n.02",
                                                        "predicate": "reptile.n.01"},
                                                identities={}, negated=False),
                                [_NO_MAMMAL_IS_REPTILE, person_is_reptile],
                                _parents_wsd, [],
                                senses_of=lambda s: ["dog.n.01", "dog.n.03"])
    assert got is None  # sibling senses disagree — an ambiguous reading is not a verdict


def test_no_senses_of_reader_means_no_canonicalization():
    assert evaluator_chainGround(_claim_wsd(), [_NO_MAMMAL_IS_REPTILE], _parents_wsd, []) is None


# ---- the extractor: effectively-negative bare copulars become rules; positive stay edges ------------

def _axiom_doc(quantifier, negated=False, original="no mammal is a reptile"):
    leaf = TKZipContent(subject=None, predicate=None, direct=None,
                        senses={"subject": "mammal.n.01", "predicate": "reptile.n.01"},
                        quantifier=quantifier, negated=negated)
    return SimpleNamespace(zip=SimpleNamespace(items=TKZipItem(content=leaf)),
                           original=original, id="ax-nomam")


def test_extractor_keeps_a_negative_bare_copular_as_negated_membership():
    rules = extract_rules([_axiom_doc(TKQuantifier.NEGATIVE)])
    assert len(rules) == 1
    r = rules[0]
    assert r["kind"] == "membership" and r["negated"] is True
    assert r["subject"] == "mammal.n.01" and r["predicate"] == "reptile.n.01"
    assert r["strength"] == "universal"  # NEGATIVE = a negative UNIVERSAL (2d)


def test_extractor_still_skips_the_positive_bare_copular():
    # "a cat is a mammal" (generic, affirmative) stays EDGE territory — no rule
    rules = extract_rules([_axiom_doc(TKQuantifier.GENERIC, original="a mammal is a reptile")])
    assert rules == []

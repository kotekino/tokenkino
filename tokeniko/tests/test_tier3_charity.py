"""Tier-3 disjointness removed from refutation (the bit incident, 2026-07-13 → fixed 2026-07-14).

«a bit is a unit of information» (TRUE, definitional) was confidently REFUTED: the dictionary's
only sense bit.n.02 "fragment" reads physical, unit reads abstract, and the evaluator's
disjointness fired at tier 3 (physical_entity ⊥ abstraction) — the very split the extractor's
edge-admission gate had distrusted from day one ("WordNet arbitrarily files polysemous nouns on
either side"). The author's ledger was docked −0.075 for stating a true definition. Fix
(author-ratified option A): the evaluator shares the extractor's epistemology — tier 3 never
refutes; tiers 1–2 are untouched; the TRUE-side charitable cross-product stays as is.
Pure unit tests over a synthetic parents reader — no DB, no pipelines.
"""
from lib.llc.evaluator.e_relations import relations_disjoint

# a synthetic is_a world reproducing the bit incident's shape + the classic tier-1/2 refutations
_PARENTS = {
    # the bit incident: physical fragment vs abstract unit — tier 3 territory ONLY
    "bit.n.02": ["fragment.n.01"],
    "fragment.n.01": ["part.n.03"],
    "part.n.03": ["thing.n.12"],
    "thing.n.12": ["physical_entity.n.01"],
    "unit.n.02": ["part.n.01"],
    "part.n.01": ["relation.n.01"],
    "relation.n.01": ["abstraction.n.06"],
    # tier 1: cat vs plant (kingdoms)
    "cat.n.01": ["feline.n.01"],
    "feline.n.01": ["animal.n.01"],
    "tulip.n.01": ["plant.n.02"],
    # tier 2: cat vs car (organism vs artifact)
    "animal.n.01": ["organism.n.01"],
    "car.n.01": ["artifact.n.01"],
    "organism.n.01": ["physical_entity.n.01"],
    "artifact.n.01": ["physical_entity.n.01"],
    # a pure abstraction for the cat-vs-idea abstention check
    "idea.n.01": ["abstraction.n.06"],
}


def _parents(sense):
    return _PARENTS.get(sense, [])


def test_bit_vs_unit_no_longer_refutes():
    # the live incident's exact shape: disjoint ONLY under the removed tier 3 -> no witness
    assert relations_disjoint("bit.n.02", "unit.n.02", _parents) is None


def test_physical_vs_abstract_abstains():
    # "a cat is an idea": the price of option A — an honest abstention, never a flaky refutation
    assert relations_disjoint("cat.n.01", "idea.n.01", _parents) is None


def test_tier1_kingdoms_still_refute():
    assert relations_disjoint("cat.n.01", "tulip.n.01", _parents) is not None


def test_tier2_organism_vs_artifact_still_refutes():
    assert relations_disjoint("cat.n.01", "car.n.01", _parents) is not None

"""Two extraction front-end leaks caught live by the author's 2026-07-08 clean-imprint session:

  NEGATED MEMBERSHIP — «I am not a man» previously extracted as an AFFIRMATIVE membership fact (the
  membership branch didn't carry `negated`): tokeniko "believed" the opposite of what he was told,
  and man.n.01's whole ancestor line polluted his closure. Now: the fact carries `negated`, the
  chainer never seeds the closure from it, and the individual-fact grounder's new MEMBERSHIP branch
  REFUTES the matching claim/question (exact klass only — "I am not a man" refutes "you are a man",
  never "you are a person").

  POSSESSIVE SCOPE-WIDENING — «my mind is a software» compiled quantifier=GENERIC (dep=poss is not
  det) and minted the class edge mind.n.01→software.n.01 = "ALL minds are software". Now a possessive
  determiner reads DEFINITE (a specific individual's X, never the class): no edge, no rule.
"""
from types import SimpleNamespace

from lib.core.tkzip import TKZipContent, TKZipItem
from lib.core.kb_extract import extract_facts
from lib.llc.evaluator.e_chaining import evaluator_forwardChain, evaluator_groundIndividualFact


_NO_PARENTS = lambda sense: []  # noqa: E731


def _leaf_doc(negated):
    leaf = TKZipContent(identities={"subject": "u1"},
                        senses={"subject": "person.n.01", "predicate": "man.n.01"},
                        negated=negated)
    item = TKZipItem(content=leaf)
    return SimpleNamespace(zip=SimpleNamespace(items=item), id="ax1", original="I am (not) a man")


def test_membership_fact_carries_negation():
    facts = extract_facts([_leaf_doc(negated=True)])
    assert facts[0]["kind"] == "membership"
    assert facts[0]["negated"] is True


def test_negated_membership_never_seeds_the_closure():
    facts = [{"kind": "membership", "subject_uid": "u1", "klass_sense": "man.n.01",
              "negated": True, "original": "I am not a man", "source_id": "ax1"}]
    rules = [{"kind": "property", "subject": "man.n.01", "predicate": "shave.v.01", "object": None,
              "negated": False, "original": "all men shave", "source_id": "ax2"}]
    derived, _ = evaluator_forwardChain(None, "u1", rules, _NO_PARENTS, facts)
    assert derived == []  # "I am NOT a man" must not inherit man-rules


def _content(pred, negated=False):
    return SimpleNamespace(identities={"subject": "u1"}, senses={"predicate": pred},
                           quantifier=None, negated=negated)


def test_negated_membership_refutes_the_matching_claim():
    facts = [{"kind": "membership", "subject_uid": "u1", "klass_sense": "man.n.01",
              "negated": True, "original": "I am not a man", "source_id": "ax1"}]
    truth, chain, prem = evaluator_groundIndividualFact(_content("man.n.01"), facts)
    assert truth == 0.0 and prem == ["ax1"]  # "are you a man?" -> confident NO
    # and the negated question corroborates ("are you not a man?" -> yes)
    truth, _, _ = evaluator_groundIndividualFact(_content("man.n.01", negated=True), facts)
    assert truth == 1.0


def test_negated_membership_is_silent_on_other_classes():
    facts = [{"kind": "membership", "subject_uid": "u1", "klass_sense": "man.n.01",
              "negated": True, "original": "I am not a man", "source_id": "ax1"}]
    assert evaluator_groundIndividualFact(_content("person.n.01"), facts) is None


def test_affirmative_membership_corroborates():
    facts = [{"kind": "membership", "subject_uid": "u1", "klass_sense": "software.n.01",
              "negated": False, "original": "I am a software", "source_id": "ax1"}]
    truth, _, _ = evaluator_groundIndividualFact(_content("software.n.01"), facts)
    assert truth == 1.0


# ---- possessive -> DEFINITE (compile-level, needs the live pipeline) ----------------------------

def test_possessive_subject_is_definite(compile_zip, leaves):
    leaf = leaves(compile_zip("my mind is a software"))[0]
    assert leaf.quantifier.value == "definite"


def test_bare_generic_still_generic(compile_zip, leaves):
    leaf = leaves(compile_zip("a cat is a mammal"))[0]
    assert leaf.quantifier.value == "indefinite"  # the article path, unchanged

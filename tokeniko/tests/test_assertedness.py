# ------------------------------------------------------------------------------------------------
# THE STORM regression (2026-07-13): per-leaf extraction (rules / facts / generic edges) must
# consume ONLY asserted leaves — a leaf folding under IMPLY/CONV/OR is a component of a compound
# thought, and a leaf under a THAT attitude is quoted thought. The live incident: the taught
# conditional «a person is wrong if he says false» (compiled with op=CONV on the antecedent fold)
# was flattened into unconditional PROPERTY rules ("most persons are wrong/state/are false") and
# the chainer mass-derived garbage over the person subtree («Kotekino is wrong», «a homo is
# false», «a aged is wrong» — 6 published, all retracted). These tests pin the valve shut.
# Pure unit tests — no Mongo, no pipelines (synthetic TKZipItem trees, SimpleNamespace docs).
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkzip import TKZipContent, TKZipItem
from lib.core.kb_extract import (
    _zip_is_asserted,
    extract_facts,
    extract_generic_isa_edges,
    extract_rules,
)


def _leaf(subject, predicate, *, op=TKOperator.AND, quantifier=TKQuantifier.GENERIC,
          negated=False, uid=None, direct=None):
    senses = {"subject": subject, "predicate": predicate}
    if direct:
        senses["direct"] = direct
    content = TKZipContent(senses=senses, quantifier=quantifier, negated=negated,
                           identities={"subject": uid} if uid else {})
    return TKZipItem(op=op, content=content)


def _doc(*items, original="synthetic", doc_id="doc-1"):
    root = TKZipItem(content=list(items))
    return SimpleNamespace(zip=SimpleNamespace(items=root), original=original, id=doc_id)


# the live storm shape, verbatim: [person wrong (AND)] [person states (CONV)] [person false (AND)]
def _storm_doc():
    return _doc(
        _leaf("person.n.01", "wrong.a.02", quantifier=TKQuantifier.INDEFINITE),
        _leaf("person.n.01", "state.v.01", op=TKOperator.CONV),
        _leaf("person.n.01", "false.a.01"),
        original="a person is wrong if he says false",
    )


# ---- _zip_is_asserted ----------------------------------------------------------------------------

def test_and_only_tree_is_asserted():
    doc = _doc(_leaf("human.n.01", "mortal.a.01"), _leaf("human.n.01", "think.v.03"))
    assert _zip_is_asserted(doc.zip.items) is True


def test_any_conv_or_imply_op_defeats_assertion():
    assert _zip_is_asserted(_storm_doc().zip.items) is False
    imply = _doc(_leaf("a.n.01", "b.a.01"), _leaf("c.n.01", "d.a.01", op=TKOperator.IMPLY))
    assert _zip_is_asserted(imply.zip.items) is False


def test_attitude_defeats_assertion():
    # «I believe that X» — the believing is asserted, X is quoted thought
    item = _leaf("cat.n.01", "immortal.a.01")
    item.attitude = "BELIEVE"  # SimpleNamespace-grade stand-in; any non-None attitude blocks
    doc = SimpleNamespace(zip=SimpleNamespace(items=TKZipItem(content=[item])),
                          original="i believe that cats are immortal", id="doc-att")
    assert _zip_is_asserted(doc.zip.items) is False


# ---- extract_rules --------------------------------------------------------------------------------

def test_storm_zip_yields_no_rules():
    assert extract_rules([_storm_doc()]) == []


def test_asserted_universal_still_yields_a_rule():
    doc = _doc(_leaf("carnivore.n.01", "eat.v.01", quantifier=TKQuantifier.UNIVERSAL,
                     direct="meat.n.01"))
    rules = extract_rules([doc])
    assert len(rules) == 1 and rules[0]["kind"] == "property"
    assert rules[0]["subject"] == "carnivore.n.01" and rules[0]["object"] == "meat.n.01"


# ---- extract_facts --------------------------------------------------------------------------------

def test_compound_zip_yields_no_facts():
    doc = _doc(
        _leaf("person.n.01", "wrong.a.02", uid="john@discord:1"),
        _leaf("person.n.01", "state.v.01", op=TKOperator.CONV, uid="john@discord:1"),
        original="john is wrong if he states",
    )
    assert extract_facts([doc]) == []


def test_asserted_individual_fact_still_extracts():
    doc = _doc(_leaf("person.n.01", "creator.n.02", uid="kotekino",
                     quantifier=TKQuantifier.DEFINITE))
    facts = extract_facts([doc])
    assert len(facts) == 1 and facts[0]["kind"] == "membership"
    assert facts[0]["subject_uid"] == "kotekino"


# ---- extract_generic_isa_edges --------------------------------------------------------------------

def test_compound_zip_yields_no_edges_and_counts_the_skip():
    # "a dog is a mammal IF ..." must not mint the edge as if asserted
    doc = _doc(
        _leaf("dog.n.01", "mammal.n.01"),
        _leaf("dog.n.01", "bark.v.01", op=TKOperator.CONV),
    )
    edges, stats = extract_generic_isa_edges([doc], parents={})
    assert edges == []
    assert stats["not_asserted_skip"] == 2

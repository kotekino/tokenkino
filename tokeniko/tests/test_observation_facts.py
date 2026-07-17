# ------------------------------------------------------------------------------------------------
# The observation-fact seam (2026-07-17, basket item 1): an eval:false verdict becomes a silent
# «<speaker> said false» theorem (zip-native reportative assembly), extract_facts reads the
# predicative-reportative shape (the ONE narrow storm-gate relaxation), and the taught
# «a person is wrong if he says false» rule finally FIRES end-to-end. The gates each lock a
# probed distinction: predicative complement (no own subject sense, matrix-inherited identity)
# vs quoted proposition (own subject sense) vs non-reportative attitude (believe = quoted thought).
# ------------------------------------------------------------------------------------------------
import copy
from types import SimpleNamespace

import pytest

from lib.core.kb_extract import extract_facts, extract_rules
from lib.core.zip_native import assemble_reportative_zip
from lib.llc.evaluator.e_chaining import evaluator_forwardChain

_SAY, _FALSE = "state.v.01", "false.a.01"


def _doc(zp, original, doc_id="obs-test"):
    return SimpleNamespace(zip=zp, original=original, id=doc_id)


# ---- extract_facts: the predicative-reportative shape ------------------------------------------------

def test_compiled_says_false_mints_matrix_and_complement_facts(compile_zip):
    zp = compile_zip("Salmon says false")
    facts = extract_facts([_doc(zp, "Salmon says false")])
    assert len(facts) == 2
    uid = facts[0]["subject_uid"]
    assert uid and "@" in uid                       # the speaker's identity, on both facts
    assert all(f["subject_uid"] == uid and f["kind"] == "property"
               and not f["negated"] for f in facts)
    assert {f["predicate"] for f in facts} == {_SAY, _FALSE}


def test_quoted_proposition_stays_blocked(compile_zip):
    # «says that snow is green»: the complement has its OWN subject sense — quoted thought,
    # the storm gate holds whole (no fact about Salmon, and NEVER "snow is green" as a fact)
    zp = compile_zip("Salmon says that snow is green")
    assert extract_facts([_doc(zp, "Salmon says that snow is green")]) == []


def test_doxastic_attitude_stays_blocked(compile_zip):
    # «believes false» is a belief report (doxastic), not an observation-consumable reportative
    zp = compile_zip("Salmon believes false")
    assert extract_facts([_doc(zp, "Salmon believes false")]) == []


@pytest.mark.pipeline  # assemble_reportative_zip reads the dictionary (Mongo without _io)
def test_negated_matrix_stays_blocked():
    zp = assemble_reportative_zip("liar@test:obs", _SAY, _FALSE)
    zp.items.content[0].content.negated = True      # «did not say» — never an observation
    assert extract_facts([_doc(zp, "negated matrix")]) == []


# ---- the native assembly is what extract_facts consumes (the production path) ------------------------

def test_native_reportative_zip_mints_the_same_facts(_io):
    zp = assemble_reportative_zip("liar@test:obs", _SAY, _FALSE)
    assert zp is not None
    facts = extract_facts([_doc(zp, "TestLiar said false")])
    assert {f["predicate"] for f in facts} == {_SAY, _FALSE}
    assert all(f["subject_uid"] == "liar@test:obs" for f in facts)


def test_native_matches_compiled_shape(compile_zip):
    # the equivalence discipline (zip_native's harness): native assembly mirrors the compiled
    # render of the same sentence — leaf ops, attitude, senses, flags, and the semantic dedup key
    from lib.core.evaluation_harness import conclusion_key
    compiled = compile_zip("Salmon says false")
    leaves = compiled.items.content
    uid = leaves[0].content.identities["subject"]
    native = assemble_reportative_zip(uid, _SAY, _FALSE)
    assert native is not None
    assert conclusion_key(native) == conclusion_key(compiled)
    for n_item, c_item in zip(native.items.content, leaves):
        assert n_item.op == c_item.op
        assert (n_item.attitude is None) == (c_item.attitude is None)
        if n_item.attitude is not None:
            assert n_item.attitude.klass == c_item.attitude.klass == "reportative"
        assert n_item.content.senses == c_item.content.senses
        assert n_item.content.identities == c_item.content.identities
        assert n_item.content.negated == c_item.content.negated
        assert n_item.content.quantifier == c_item.content.quantifier


# ---- end to end: the taught rule FIRES on the observation ---------------------------------------------

def test_taught_rule_fires_on_observation(compile_zip):
    # the acceptance case the seam exists for: teach the rule, know the membership, OBSERVE the
    # falsehood -> the chainer derives «wrong» with the observation in the premises
    rule_doc = _doc(compile_zip("a person is wrong if he says false"),
                    "a person is wrong if he says false", "rule-obs")
    rules = [r for r in extract_rules([rule_doc]) if r.get("cond_class")]
    assert len(rules) == 1 and rules[0]["cond_pred"] == _SAY \
        and rules[0]["cond_extra"] == [(_FALSE, None)]      # sense alignment, by construction
    membership = {"subject_uid": "liar@test:obs", "klass_sense": "person.n.01",
                  "predicate": "person.n.01", "negated": False, "source_id": "fact-m"}
    obs_zip = assemble_reportative_zip("liar@test:obs", _SAY, _FALSE)
    obs_facts = extract_facts([_doc(obs_zip, "TestLiar said false", "obs-theorem")])
    derived, chains = evaluator_forwardChain(
        None, "liar@test:obs", rules, lambda s: [], [membership] + obs_facts)
    wrong = {d["predicate"]: d for d in derived}.get("wrong.a.02")
    assert wrong is not None
    assert "obs-theorem" in wrong["premises"]               # the observation is a premise
    assert "rule-obs" in wrong["premises"]


# ---- the brain trigger: record_observation ------------------------------------------------------------

def test_record_observation_mints_once(_io):
    from datetime import datetime, timezone
    from lib.core.models import TKMemoryStakeholdersDoc, TKTheoremDoc
    from brain.thinking import record_observation

    sh = TKMemoryStakeholdersDoc(name="TestLiar", uid="testliar@test:obs",
                                 kind="individual", isMe=False)
    sh.insert()
    item = SimpleNamespace(sourceId="testliar@test:obs", original="snow is green",
                           id="mem-obs-1", channel=None, directedness=0.0,
                           timestamp=datetime.now(timezone.utc))
    result = SimpleNamespace(premises=["ax-premise-1"])
    try:
        assert record_observation(item, result) is True
        doc = TKTheoremDoc.find_one({"original": "TestLiar said false"}).run()
        assert doc is not None and doc.archived is False
        assert doc.provenance.derived_by == "observation"
        assert "observed:mem-obs-1" in doc.provenance.premises
        assert "ax-premise-1" in doc.provenance.premises
        assert isinstance(doc.trusted, float)
        facts = extract_facts([doc])                        # the stored doc feeds the chainer
        assert {f["predicate"] for f in facts} == {_SAY, _FALSE}
        assert record_observation(item, result) is False    # idempotent: one observation suffices
        assert TKTheoremDoc.find({"original": "TestLiar said false"}).count() == 1
    finally:
        d = TKTheoremDoc.find_one({"original": "TestLiar said false"}).run()
        if d is not None:
            d.delete()
        sh.delete()


def test_record_observation_skips_self_and_premiseless(_io):
    from lib.core.io import get_tokeniko
    from brain.thinking import record_observation
    me = get_tokeniko()
    item = SimpleNamespace(sourceId=me.uid, original="x", id="mem-obs-2",
                           channel=None, directedness=0.0)
    assert record_observation(item, SimpleNamespace(premises=["p"])) is False   # never on himself
    item2 = SimpleNamespace(sourceId="testliar@test:obs", original="x", id="mem-obs-3",
                            channel=None, directedness=0.0)
    assert record_observation(item2, SimpleNamespace(premises=[])) is False     # unpriceable

# ------------------------------------------------------------------------------------------------
# The conditional-rule extractor (2026-07-16 second session — the M2-orbit fuel lines consumed).
# A taught CLASS conditional («a person is wrong if he says false») and a same-subject generic
# cause pair now extract into class-restricted property_conditioned rules the chainer fires with
# its existing step-4 machinery (cond_class gated on the closure; the THAT complements as
# cond_extra conjuncts over the props table). The gates each guard a probed failure mode:
# identities = anecdote, different subjects = a propositional causal link (no chainer layer),
# negated/modal conditions never extract. Single-predicate conditionals fire END-TO-END; the
# «says false» THAT-shape extracts well-formed and waits for the observation-fact seam (D-phase).
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

from lib.core.kb_extract import extract_rules
from lib.llc.evaluator.e_chaining import evaluator_forwardChain


def _rules_of(compile_zip, s):
    doc = SimpleNamespace(zip=compile_zip(s), original=s, id="cond-test")
    return extract_rules([doc])


def _class_conditioned(rules):
    return [r for r in rules if r.get("kind") == "property_conditioned" and r.get("cond_class")]


# ---- extraction shapes -----------------------------------------------------------------------------

def test_reteach_sentence_extracts_the_rule(compile_zip):
    # THE acceptance case: «a person is wrong if he says false» becomes a usable chainer rule
    ccs = _class_conditioned(_rules_of(compile_zip, "a person is wrong if he says false"))
    assert len(ccs) == 1
    r = ccs[0]
    assert r["cond_class"] == "person.n.01"      # "he" coreference-resolved to the class
    assert r["concl_pred"] == "wrong.a.02"
    assert r["cond_pred"]                        # the say-predicate
    assert len(r["cond_extra"]) == 1             # the «false» THAT complement rides as a conjunct
    assert r["strength"] == "generic"            # a taught conditional is defeasible


def test_fronted_variant_inherits_the_subject(compile_zip):
    # «if a person says false, he is wrong» loses its cataphoric "he" — the consequent inherits
    # the antecedent's class (conditionals share subjects by default)
    ccs = _class_conditioned(_rules_of(compile_zip, "if a person says false, he is wrong"))
    assert len(ccs) == 1
    assert ccs[0]["cond_class"] == "person.n.01"
    assert ccs[0]["concl_pred"] == "wrong.a.02"


def test_single_predicate_conditional(compile_zip):
    ccs = _class_conditioned(_rules_of(compile_zip, "a person is wrong if he lies"))
    assert len(ccs) == 1
    assert ccs[0]["cond_class"] == "person.n.01"
    assert ccs[0]["cond_extra"] == []


def test_cause_pair_same_subject_extracts(compile_zip):
    # the M2 `cause` fuel line: a same-class-subject reason pair is a defeasible rule
    ccs = _class_conditioned(_rules_of(compile_zip, "a person is wrong because he lies"))
    assert len(ccs) == 1
    assert ccs[0]["cond_class"] == "person.n.01"
    assert ccs[0]["concl_pred"] == "wrong.a.02"


def test_anecdote_never_generalizes(compile_zip):
    # identities anywhere = an anecdote («I sleep because I am tired») — no rule, ever
    assert _class_conditioned(_rules_of(compile_zip, "I sleep because I am tired")) == []


def test_different_subjects_never_extract(compile_zip):
    # a propositional causal link (clouds/water) has no chainer layer — skipped honestly
    assert _class_conditioned(
        _rules_of(compile_zip, "clouds produce rain because water condenses")) == []


def test_sense_less_universal_stays_property_conditioned(compile_zip):
    # the landed extractor keeps its territory: «everything that thinks exists» has NO cond_class
    rules = _rules_of(compile_zip, "everything that thinks exists")
    pcs = [r for r in rules if r.get("kind") == "property_conditioned"]
    assert len(pcs) == 1
    assert not pcs[0].get("cond_class")


# ---- the chainer fires it (synthetic units — no DB) --------------------------------------------------

_RULE = {
    "kind": "property_conditioned", "cond_class": "person.n.01",
    "cond_pred": "lie.v.02", "cond_obj": None, "cond_extra": [],
    "concl_pred": "wrong.a.02", "concl_obj": None, "concl_negated": False,
    "strength": "generic", "original": "a person is wrong if he lies", "source_id": "rule-1",
}
_MEMBER = {"subject_uid": "john@test", "klass_sense": "person.n.01",
           "predicate": "person.n.01", "negated": False, "source_id": "fact-m"}
_LIES = {"subject_uid": "john@test", "klass_sense": None,
         "predicate": "lie.v.02", "object": None, "negated": False, "source_id": "fact-p"}


def _derived_preds(rules, facts):
    derived, _ = evaluator_forwardChain(None, "john@test", rules, lambda s: [], facts)
    return {d["predicate"]: d for d in derived}


def test_chainer_fires_class_conditioned_rule():
    out = _derived_preds([_RULE], [_MEMBER, _LIES])
    assert "wrong.a.02" in out
    assert "rule-1" in out["wrong.a.02"]["premises"]      # the rule is a premise
    assert "fact-p" in out["wrong.a.02"]["premises"]      # so is the condition fact
    assert "person.n.01" in out["wrong.a.02"]["chain"]    # the class scope is narrated


def test_class_gate_blocks_outsiders():
    # john lies but is NOT a person (no membership) -> the class restriction holds the rule shut
    assert "wrong.a.02" not in _derived_preds([_RULE], [_LIES])


def test_cond_extra_all_must_hold():
    rule = {**_RULE, "cond_extra": [("false.a.01", None)], "source_id": "rule-2"}
    # the lie alone does not satisfy the extra conjunct
    assert "wrong.a.02" not in _derived_preds([rule], [_MEMBER, _LIES])
    # adding the false-property completes the condition
    false_fact = {"subject_uid": "john@test", "klass_sense": None,
                  "predicate": "false.a.01", "object": None, "negated": False, "source_id": "fact-f"}
    out = _derived_preds([rule], [_MEMBER, _LIES, false_fact])
    assert "wrong.a.02" in out
    assert "fact-f" in out["wrong.a.02"]["premises"]


# ---- end to end: teach the rule, know the fact, derive the verdict ----------------------------------

def test_end_to_end_taught_conditional_fires(compile_zip):
    rules = _rules_of(compile_zip, "a person is wrong if he lies")
    r = _class_conditioned(rules)[0]
    facts = [_MEMBER, {**_LIES, "predicate": r["cond_pred"]}]  # the fact speaks the rule's sense
    out = _derived_preds(rules, facts)
    assert "wrong.a.02" in out

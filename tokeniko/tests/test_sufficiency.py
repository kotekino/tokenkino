"""Definitional sufficiency (Brain v1.1 step 4) — the recognition direction.

Two pure, DB-free layers:
  - the CHAINER: a kind="sufficient" rule ((is_a genus ∧ conds) -> is_a klass) fires inside the
    membership fixpoint when the seed's membership facts put the genus in the closure AND every
    definiens conjunct matches an affirmative property fact — predicate charitable by lemma root,
    OBJECT STRICT. The recognized class then feeds downstream property rules, and the proof cites
    the definition + the satisfying facts.
  - the EXTRACTOR: extract_sufficient_rules left-folds a definition zip's operator tree into DNF
    branches (OR splits — each disjunct independently sufficient; AND distributes — a conjunct is
    never dropped) and gates each branch whole (an IMPLY purpose-clause conjunct kills its branch).
"""
from types import SimpleNamespace

from lib.core.tk import TKOperator
from lib.core.tkzip import TKZipContent, TKZipItem
from lib.llc.evaluator.e_chaining import evaluator_forwardChain
from lib.core.kb_extract import extract_sufficient_rules


_NO_PARENTS = lambda sense: []  # noqa: E731 — a bare is_a reader: no ancestors anywhere

_SUFF_RULE = {
    "kind": "sufficient", "klass": "clock.n.01", "genus": "timepiece.n.01",
    "conds": [{"predicate": "show.v.01", "object": "time.n.01"}],
    "original": "a clock is a timepiece that shows the time of day",
    "source_id": "rule:sufficient:clock.n.01|timepiece.n.01|show.v.01:time.n.01",
}
_DOWNSTREAM = {  # a property rule keyed on the RECOGNIZED class — proves the closure grew
    "kind": "property", "subject": "clock.n.01", "predicate": "tick.v.01", "object": None,
    "negated": False, "original": "all clocks tick", "source_id": "ax-tick",
}


def _facts(obj="time.n.01"):
    return [
        {"kind": "membership", "subject_uid": "u1", "klass_sense": "timepiece.n.01",
         "original": "it is a timepiece", "source_id": "ax-mem"},
        {"kind": "property", "subject_uid": "u1", "predicate": "show.v.01", "object": obj,
         "negated": False, "original": "it shows the time", "source_id": "ax-show"},
    ]


def test_sufficient_rule_recognizes_and_cascades():
    derived, chains = evaluator_forwardChain(None, "u1", [_SUFF_RULE, _DOWNSTREAM],
                                             _NO_PARENTS, _facts())
    tick = next((d for d in derived if d["predicate"] == "tick.v.01"), None)
    assert tick is not None, "recognition did not feed the downstream property rule"
    # the proof cites the whole descent: membership fact, satisfying fact, definition, fired rule
    assert set(tick["premises"]) == {"ax-mem", "ax-show", _SUFF_RULE["source_id"], "ax-tick"}
    assert "(recognized)" in tick["chain"]


def test_object_strictness_blocks_a_mismatched_fact():
    # the seed shows the DAY, the definiens requires showing the TIME -> the rule must stay silent
    derived, _ = evaluator_forwardChain(None, "u1", [_SUFF_RULE, _DOWNSTREAM],
                                        _NO_PARENTS, _facts(obj="day.n.01"))
    assert not any(d["predicate"] == "tick.v.01" for d in derived)


def test_objectless_cond_fires_on_a_fact_with_object():
    # "is open" is entailed by "opens X": a cond WITHOUT an object accepts any matching predicate
    rule = {**_SUFF_RULE, "conds": [{"predicate": "show.v.01", "object": None}]}
    derived, _ = evaluator_forwardChain(None, "u1", [rule, _DOWNSTREAM],
                                        _NO_PARENTS, _facts())
    assert any(d["predicate"] == "tick.v.01" for d in derived)


def test_missing_genus_blocks_recognition():
    # property fact alone — the seed was never placed in the genus class
    facts = [f for f in _facts() if f["kind"] == "property"]
    derived, _ = evaluator_forwardChain(None, "u1", [_SUFF_RULE, _DOWNSTREAM],
                                        _NO_PARENTS, facts)
    assert not any(d["predicate"] == "tick.v.01" for d in derived)


# ---- the extractor (hand-built zips: SimpleNamespace docs around real TKZipItem trees) ----------

def _leaf(op, subject=None, predicate=None, direct=None, negated=False):
    senses = {k: v for k, v in
              (("subject", subject), ("predicate", predicate), ("direct", direct)) if v}
    return TKZipItem(op=op, content=TKZipContent(senses=senses, negated=negated))


def _def_doc(items, original):
    return SimpleNamespace(zip=SimpleNamespace(items=items), id="d1", original=original)


def test_extractor_mines_a_conjunctive_definiens():
    items = TKZipItem(op=TKOperator.AND, content=[
        _leaf(TKOperator.AND, "clock.n.01", "timepiece.n.01"),
        _leaf(TKOperator.AND, "clock.n.01", "show.v.01", "time.n.01"),
    ])
    rules, stats = extract_sufficient_rules(
        [_def_doc(items, "a clock is a timepiece that shows the time")], _NO_PARENTS)
    assert stats["accept"] == 1
    (r,) = rules
    assert r["klass"] == "clock.n.01" and r["genus"] == "timepiece.n.01"
    assert r["conds"] == [{"predicate": "show.v.01", "object": "time.n.01"}]


def test_extractor_splits_disjuncts_into_separate_rules():
    # "… that lacks restraint or control": each disjunct is independently sufficient (given genus)
    items = TKZipItem(op=TKOperator.AND, content=[
        _leaf(TKOperator.AND, "abandon.n.01", "trait.n.01"),
        _leaf(TKOperator.AND, "abandon.n.01", "miss.v.06", "restraint.n.01"),
        _leaf(TKOperator.OR, "abandon.n.01", "miss.v.06", "control.n.01"),
    ])
    rules, stats = extract_sufficient_rules(
        [_def_doc(items, "an abandon is the trait of lacking restraint or control")], _NO_PARENTS)
    assert stats["accept"] == 2
    objs = {r["conds"][0]["object"] for r in rules}
    assert objs == {"restraint.n.01", "control.n.01"}


def test_extractor_rejects_a_branch_with_an_imply_conjunct():
    # a purpose clause ("… to improve it") is an unrepresentable CONJUNCT: dropping it would leave
    # a rule WEAKER than the definiens (it would over-fire) — the whole branch dies instead
    items = TKZipItem(op=TKOperator.AND, content=[
        _leaf(TKOperator.AND, "addition.n.01", "component.n.03"),
        _leaf(TKOperator.AND, "addition.n.01", "add.v.01", "thing.n.01"),
        _leaf(TKOperator.IMPLY, "addition.n.01", "better.v.02"),
    ])
    rules, stats = extract_sufficient_rules(
        [_def_doc(items, "an addition is a component that is added to something to improve it")],
        _NO_PARENTS)
    assert stats["accept"] == 0
    assert stats["br_taint"] == 1
    assert rules == []

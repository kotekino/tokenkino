# ------------------------------------------------------------------------------------------------
# THE IDENTITY-BLINDNESS FAMILY (2026-07-19 audit; doc/ref/notes.md § "The identity-blindness
# family"). tokeniko's symbolic layer has two referent kinds with DISJOINT keys — a CLASS by WSD
# sense (TKZipContent.senses), an INDIVIDUAL by identity uid (.identities) — and any site that read
# only senses.get(role) was silently blind to half the world. This locks the `role_key` cure and
# the two blind wh-branches + the consistency-kernel subject compare it feeds.
#
# All parser-free at the solve layer: compile_zip builds the KB zips + the question leaf, then the
# evaluator primitives are exercised directly (DB-agnostic, the readers injected).
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

import pytest

from lib.core.tk import TKWhRole
from lib.core.evaluation import AnswerVerdict
from lib.llc.evaluator import evaluator_solveWh, evaluator_classifyForm, role_key


def _wh_leaf(lvs):
    return next(l for l in lvs if getattr(l, "wh_role", None) is not None)


# a parents(sense) stub — the is_a reader the class-subject path walks. never called on a uid.
def _parents(sense):
    return ["feline.n.01"] if sense == "cat.n.01" else []


@pytest.fixture
def antonyms(_io):
    # the synset-keyed antonym reader (DB-backed; io already inited by the session _io fixture).
    from lib.core.evaluation_harness import _make_antonym_reader
    return _make_antonym_reader()


# --- role_key: the shared primitive ----------------------------------------------------------

def test_role_key_unit_table():
    # sense-only, identity-only, both-would-never-happen (identity wins, the dedup discipline),
    # and neither -> None. The four corners of the read.
    sense_only = SimpleNamespace(senses={"subject": "cat.n.01"}, identities={})
    id_only = SimpleNamespace(senses={}, identities={"subject": "mari@internal:tokeniko"})
    both = SimpleNamespace(senses={"subject": "cat.n.01"}, identities={"subject": "mari@internal:tokeniko"})
    neither = SimpleNamespace(senses={}, identities={})

    assert role_key(sense_only, "subject") == "cat.n.01"
    assert role_key(id_only, "subject") == "mari@internal:tokeniko"
    assert role_key(both, "subject") == "mari@internal:tokeniko"   # identity-FIRST
    assert role_key(neither, "subject") is None
    assert role_key(sense_only, "predicate") is None               # absent role -> None


# --- piece 2: the what-branch (PREDICATE gap) — identity subject via the KB-facts branch --------

def test_what_are_you_answered_from_identity_fact(compile_zip, leaves):
    # THE live specimen (2026-07-18, «what are you?» ×4 -> IDK despite the stored «I am a software»):
    # "you"/"I" is a uid, sense-less; the is_a graph is silent, so the answer comes from the copular
    # fact keyed by the uid. `_parents` returns nothing for the (absent) subject sense — proof the
    # uid is NEVER fed to the graph.
    fact = compile_zip("I am a software")
    q = compile_zip("what are you?")
    ans = evaluator_solveWh(_wh_leaf(leaves(q)), [fact], [], _parents)
    assert ans.verdict == AnswerVerdict.VALUE
    assert ans.value == "software"


def test_what_is_a_class_still_walks_isa(compile_zip, leaves):
    # regression: a CLASS subject («what is a cat?») still walks the is_a hypernym graph — the
    # sense path is untouched by the identity branch.
    q = compile_zip("what is a cat?")
    ans = evaluator_solveWh(_wh_leaf(leaves(q)), [], [], _parents)
    assert ans.verdict == AnswerVerdict.VALUE
    assert ans.value == "feline"


# --- piece 3: the who-branch (SUBJECT gap) — identity target described from KB facts ------------

def test_who_is_named_individual_answered_from_fact(compile_zip, leaves):
    # the next bounce (notes §): «who is Mari?» carries Mari as an identity uid (sense-less) — the
    # sense-only predicate read missed it. describe the individual from a KB fact keyed by the uid.
    fact = compile_zip("Mari is a human")
    q = compile_zip("who is Mari?")
    ans = evaluator_solveWh(_wh_leaf(leaves(q)), [fact], [], _parents)
    assert ans.verdict == AnswerVerdict.VALUE
    assert ans.value  # a non-empty description (the class Mari belongs to)


def test_who_is_predicate_sense_still_scans_kb(compile_zip, leaves):
    # regression: a SENSE predicate («who is happy?») still scans the KB for a leaf predicating it
    # and returns that leaf's subject — here «Mari is happy» -> "mari".
    fact = compile_zip("Mari is happy")
    q = compile_zip("who is happy?")
    ans = evaluator_solveWh(_wh_leaf(leaves(q)), [fact], [], _parents)
    assert ans.verdict == AnswerVerdict.VALUE
    assert ans.value == "mari"


# --- piece 4: _contrary_pairs — individual subjects compare by uid ------------------------------

def test_contrary_individual_subject_is_inconsistent(compile_zip, antonyms):
    # «I am alive and I am dead» — both subjects are the SAME individual (tokeniko, a uid). Before
    # the cure both subject senses read None and the contrary pair fell through the truthiness guard
    # undetected. Now they compare by uid and the antonym-mutex fires -> a real contradiction.
    fc = evaluator_classifyForm(compile_zip("I am alive and I am dead"), antonyms=antonyms)
    assert fc.contradiction


def test_contrary_class_subject_still_inconsistent(compile_zip, antonyms):
    # regression: the class-subject sense path («the cat is dead and alive») is unchanged.
    fc = evaluator_classifyForm(compile_zip("the cat is dead and alive"), antonyms=antonyms)
    assert fc.contradiction

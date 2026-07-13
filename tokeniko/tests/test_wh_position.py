# ------------------------------------------------------------------------------------------------
# R5 — the wh-position bug (live specimens 2026-07-12/13): a wh-word ANYWHERE in the sentence made
# the whole statement interrogative, even with no "?". «because I am happy when I talk to …» became
# a TIME question (tokeniko answered "I do not know" to a question never asked), and the taught rule
# «a person is wrong when he says false» was swallowed the same way (its "if" twin materialized
# fine — a one-conjunction controlled experiment). The fix: without a "?", the wh-token must attach
# to the ROOT clause (_parser_whAttachesToRoot — the head-chain walk; crossing advcl/ccomp/relcl/…
# means subordination, not interrogation). Full-pipeline band-asserts via the compile_zip fixture.
# ------------------------------------------------------------------------------------------------
from lib.core.tk import TKWhRole


def _no_leaf_is_question(lvs):
    assert all(l.dubitative != 1.0 for l in lvs)
    assert all(l.wh_role is None for l in lvs)


# ---- the live specimens: embedded wh-words are statements ------------------------------------------

def test_embedded_when_in_because_clause_is_a_statement(compile_zip, leaves):
    # specimen #1 (2026-07-12): the author's channel small-talk, mis-answered "I do not know"
    zp = compile_zip("because I am happy when I talk to my friend")
    _no_leaf_is_question(leaves(zp))


def test_taught_rule_with_when_is_a_statement(compile_zip, leaves):
    # specimen #2 (2026-07-13): the teaching that the question branch swallowed
    zp = compile_zip("a person is wrong when he says false")
    _no_leaf_is_question(leaves(zp))


def test_conditional_when_clause_first_is_a_statement(compile_zip, leaves):
    # tree position, not line position: a sentence-INITIAL subordinate "when" is still embedded
    zp = compile_zip("when I am tired I sleep")
    _no_leaf_is_question(leaves(zp))


# ---- root-attached wh-words still interrogate (no regression) --------------------------------------

def test_root_when_question_keeps_time_gap(compile_zip, leaves):
    zp = compile_zip("when do you sleep?")
    lvs = leaves(zp)
    assert all(l.dubitative == 1.0 for l in lvs)
    assert any(l.wh_role == TKWhRole.TIME for l in lvs)


def test_root_wh_without_question_mark_still_interrogates(compile_zip, leaves):
    # the "?"-less AUX-INVERTED question — the root-attachment walk must not require punctuation.
    # (the bare-copular "?"-less form — "who is happy" — is a pre-existing DETECTOR gap: stanza
    # only tags PronType=Int there with the "?"; tracked in test_xfail_known_gaps.py)
    zp = compile_zip("when do you sleep")
    lvs = leaves(zp)
    assert all(l.dubitative == 1.0 for l in lvs)
    assert any(l.wh_role == TKWhRole.TIME for l in lvs)


def test_polar_question_with_embedded_when_has_no_time_gap(compile_zip, leaves):
    # "?" makes it a question (mood), but the embedded "when" must NOT donate a TIME gap role —
    # it asks about the conditional, not about a time
    zp = compile_zip("are you happy when you sleep?")
    lvs = leaves(zp)
    assert all(l.dubitative == 1.0 for l in lvs)
    assert all(l.wh_role is None for l in lvs)

"""The graph-constrained SUBJECT untangle (step 5 — the runtime mirror of the genus untangle).

A definition's subject gets EXACT gloss-pinning (scripts/pin_definition_senses.py); a runtime AXIOM
has no gloss to pin, so the compiler snaps a demonstrably mis-sensed copular subject to the sense of
the same word that bedrock already places under the genus — and ONLY then. A genuine new edge
("a human is a person" — the author's bridging axiom) has no graph-consistent candidate and must
survive untouched; a named individual's type-centroid sense is never a WSD pick and is never touched.
"""
import pytest

from lib.llc.compiler import c_untangle
from lib.llc.compiler.c_untangle import _resolve_subject


# ---- resolver logic on a SYNTHETIC graph (module caches primed; no DB dependency) ---------------

@pytest.fixture()
def synthetic_graph(monkeypatch):
    # word "bank": money-sense descends from institution; river-sense descends from slope
    monkeypatch.setitem(c_untangle._senses_cache, "bank", ["bank.n.01", "bank.n.09"])
    monkeypatch.setitem(c_untangle._parents_cache, "bank.n.01", ["slope.n.01"])
    monkeypatch.setitem(c_untangle._parents_cache, "bank.n.09", ["institution.n.01"])
    monkeypatch.setitem(c_untangle._parents_cache, "slope.n.01", [])
    monkeypatch.setitem(c_untangle._parents_cache, "institution.n.01", [])


def test_missensed_subject_snaps_to_graph_consistent_sense(synthetic_graph):
    # "a bank is an institution" with the river-bank sense -> the money sense is what bedrock vouches
    assert _resolve_subject("bank", "bank.n.01", "institution.n.01") == "bank.n.09"


def test_consistent_subject_is_kept(synthetic_graph):
    assert _resolve_subject("bank", "bank.n.09", "institution.n.01") == "bank.n.09"


def test_no_consistent_candidate_keeps_the_new_edge(synthetic_graph):
    # no sense of "bank" descends from mammal -> the claim stands as the speaker made it
    assert _resolve_subject("bank", "bank.n.01", "mammal.n.01") == "bank.n.01"


def test_non_noun_pairs_are_skipped(synthetic_graph):
    assert _resolve_subject("bank", "bank.v.01", "institution.n.01") == "bank.v.01"
    assert _resolve_subject("bank", "bank.n.01", "open.a.01") == "bank.n.01"


# ---- compile-level (live pipeline + real bedrock) ------------------------------------------------

def test_missensed_subject_untangles_at_compile(compile_zip, leaves):
    # pre-pin poster child: WSD reads "fair" as the gathering; bedrock places carnival.n.03
    # under show.n.01 -> the subject snaps to the sense the graph vouches for.
    leaf = leaves(compile_zip("a fair is a traveling show"))[0]
    assert leaf.senses.get("subject") == "carnival.n.03"


def test_correct_subject_unchanged(compile_zip, leaves):
    leaf = leaves(compile_zip("a cat is a mammal"))[0]
    assert leaf.senses.get("subject") == "cat.n.01"


def test_bridging_axiom_subject_survives(compile_zip, leaves):
    # the author's «a human is a person» mints a NEW edge (homo.n.02 -> person.n.01 is not bedrock):
    # no graph-consistent alternative exists, so the untangle must leave it exactly as taught.
    leaf = leaves(compile_zip("a human is a person"))[0]
    assert leaf.senses.get("subject") == "homo.n.02"

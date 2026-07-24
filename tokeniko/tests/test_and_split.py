# ------------------------------------------------------------------------------------------------
# THE AND-SPLIT — per-conjunct reactions (the author's design, 2026-07-24; fork b).
#
# «the cat is a mammal and pigs fly because Z» is TWO claims sharing ONE interaction: he agrees
# with the first and speaks up about the second, naming it. Today the evaluator grounds each clause
# then FOLDS the truths (fuzzy AND = min), so the absurd conjunct drags the true one down and the
# reaction cannot say which half offends. `split_conjuncts` groups the flat conjunct leaves BY
# SUBJECT ATOM and distributes the shared «because» leaf to every group; thinking reacts per group.
#
# The carve-outs are the point of most of these tests: same-subject coordination NEVER splits (the
# X∧¬X kernel needs «the cat is dead and alive» whole), «but» never splits (the contrast BINDS the
# pair), and questions are out of scope. These run on REAL compiled zips.
# ------------------------------------------------------------------------------------------------
from lib.core.evaluation_harness import split_conjuncts
from lib.core.kb_extract import _zip_leaves


def _subjects(zip_):
    """the subject sense of each leaf, in order — the readable shape of a (sub-)zip."""
    return [(leaf.senses or {}).get("subject") for leaf in _zip_leaves(zip_.items)]


def _predicates(zip_):
    return [(leaf.senses or {}).get("predicate") for leaf in _zip_leaves(zip_.items)]


# ---- the split fires on independent claims ------------------------------------------------------

def test_distinct_subjects_split_into_two(compile_zip):
    # the author's own specimen (its first half): two subjects, two claims, two reactions
    parts = split_conjuncts(compile_zip("the cat is a mammal and pigs fly"))
    assert parts is not None and len(parts) == 2
    assert _predicates(parts[0]) == ["mammal.n.01"]
    assert _predicates(parts[1]) == ["fly.v.01"]


def test_two_copular_claims_split(compile_zip):
    parts = split_conjuncts(compile_zip("a cat is a mammal and a dog is an animal"))
    assert parts is not None and len(parts) == 2
    assert _subjects(parts[0]) == ["cat.n.01"]
    assert _subjects(parts[1]) == ["dog.n.01"]


def test_shared_because_distributes_to_every_conjunct(compile_zip):
    # the author's ruling: «A and B because Z» -> «A because Z» AND «B because Z» — the reason is
    # the interaction's, not the last conjunct's.
    parts = split_conjuncts(
        compile_zip("the cat is a mammal and pigs fly because they are birds"))
    assert parts is not None and len(parts) == 2
    for part in parts:
        causes = [leaf.cause for leaf in _zip_leaves(part.items) if leaf.cause]
        assert causes == ["reason"], "every conjunct must inherit the shared because-leaf"
    assert "mammal.n.01" in _predicates(parts[0])
    assert "fly.v.01" in _predicates(parts[1])


# ---- the carve-outs: what must NEVER split ------------------------------------------------------

def test_same_subject_coordination_never_splits(compile_zip):
    # THE load-bearing carve-out: «the cat is dead and alive» is ONE contradiction — the consistency
    # kernel needs the whole form to see X∧¬X. One subject atom -> one group -> no split, with no
    # special case in the splitter (the grouping does it structurally).
    assert split_conjuncts(compile_zip("the cat is dead and alive")) is None


def test_contrast_never_splits(compile_zip):
    # «X but Y» is one thought: the contrast flag BINDS the pair (M1's implicature).
    assert split_conjuncts(compile_zip("the cat is a mammal but pigs fly")) is None


def test_single_clause_never_splits(compile_zip):
    assert split_conjuncts(compile_zip("a cat is a mammal")) is None


def test_question_never_splits(compile_zip):
    # questions are answered, never split (out of scope, v1)
    assert split_conjuncts(compile_zip("is a cat a mammal and is a dog an animal?")) is None


# ---- the reaction fan ---------------------------------------------------------------------------

def test_conjunct_topics_slice_only_when_they_align(compile_zip, monkeypatch):
    # the {topic} naming nicety: sliced off the ORIGINAL only when the slice count matches the group
    # count; a mismatch degrades to None (the bare «why is that?» shelf), never a guess.
    from brain import thinking

    class _Item:
        original = "the cat is a mammal and pigs fly"
        id = "x"

    monkeypatch.setattr(thinking, "get_tokeniko", lambda: type("S", (), {"name": "tokeniko"})())
    parts = split_conjuncts(compile_zip(_Item.original))
    assert thinking._conjunct_topics(_Item(), parts) == ["the cat is a mammal", "pigs fly"]
    # a mismatch (three surface segments, two groups) -> honest vagueness
    class _Odd:
        original = "a and b and c"
        id = "y"
    assert thinking._conjunct_topics(_Odd(), parts) == [None, None]

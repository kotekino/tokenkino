# ------------------------------------------------------------------------------------------------
# M3 — WSD SELECTION (the third harvest's sense misses, 2026-07-16).
#
# Fix A: `_wsd_mostFrequentVector` had NO order guarantee (bare find_one) — for "whale" it returned
# giant.n.04 the PERSON, so a repeated lemma pushed every centroid onto person-senses and even
# "fish" resolved to pisces.n.02 (the astrology sign). Fixed: most-frequent discipline in the
# context fetch + same-lemma tokens excluded from a token's centroid (self-evidence ≠ context).
#
# Fix B: the curated `preferred` flag — the WSD ladder is Lesk → preferred → centroid → WordNet
# order (textual evidence wins; curated human data outranks sparse-vector co-occurrence guessing;
# the centroid was confident-wrong in every documented episode: dog.n.03 0.83, giant.n.04 0.807,
# pisces.n.02 0.755). The flag rung is unit-tested with in-memory rows (KB writes are the
# operator's); the live-flag integration tests self-activate once curate_prefer_senses --apply ran.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core.kb_extract import _zip_leaves


def _all_senses(zp):
    out = set()
    for leaf in _zip_leaves(zp.items):
        out.update(leaf.senses.values())
    return out


# ---- fix A: the centroid self-poisoning regression -------------------------------------------------

def test_repeated_lemma_keeps_animal_senses(compile_zip):
    # the harvest specimen: two "whale" tokens poisoned each other's centroid -> giant.n.04 at
    # 0.807 and fish -> pisces.n.02. Both must resolve to the animals now.
    senses = _all_senses(compile_zip("a whale lives in the water but a whale is not a fish"))
    assert "whale.n.02" in senses
    assert "giant.n.04" not in senses
    assert "pisces.n.02" not in senses


def test_multisentence_animal_senses(compile_zip):
    # «yes. a fish breathes with gills. a whale breathes with lungs.» — the evening play's shape
    senses = _all_senses(compile_zip("a fish breathes with gills. a whale breathes with lungs."))
    assert "fish.n.01" in senses
    assert "whale.n.02" in senses
    assert "pisces.n.02" not in senses and "giant.n.04" not in senses


def test_keepset_copular_circularity_intact(compile_zip):
    # the 2026-07-11 guard must survive: subject not disambiguated by its copular partner
    assert "dog.n.01" in _all_senses(compile_zip("a dog is a reptile"))
    assert "cat.n.01" in _all_senses(compile_zip("a cat is a mammal"))
    # the partner's own modifiers still count as context (the financial bank)
    assert "depository_financial_institution.n.01" in _all_senses(
        compile_zip("the bank is a financial institution")
    )


# ---- fix B: the preferred rung (unit — in-memory rows, no KB writes) --------------------------------

def _tok(_io, text, lemma):
    import lib.llc.parser as P
    doc = P.nlp_stanza(text)
    return next(t for t in doc if t.lemma_.lower() == lemma)


def _row(word, sense, definition, preferred=False):
    from lib.core.models import TKDictionaryDoc
    return TKDictionaryDoc(word=word, pos="n", sense=sense, definition=definition,
                           preferred=preferred)


def test_preferred_wins_when_lesk_silent(_io, compile_zip):
    # no gloss overlap with the sentence -> the curated row wins over the WordNet order
    from lib.llc.parser import parser_disambiguateSense
    tok = _tok(_io, "a squid is a mammal", "squid")
    cands = [
        _row("squid", "squid.n.01", "squid prepared as food"),
        _row("squid", "squid.n.02", "fast-moving ten-armed cephalopod mollusk", preferred=True),
    ]
    assert parser_disambiguateSense(tok, cands).sense == "squid.n.02"


def test_lesk_beats_preferred(_io, compile_zip):
    # real textual evidence outranks the curated default: the gloss overlaps the sentence
    from lib.llc.parser import parser_disambiguateSense
    tok = _tok(_io, "the squid was served with lemon at dinner", "squid")
    cands = [
        _row("squid", "squid.n.01", "squid served as food at dinner"),
        _row("squid", "squid.n.02", "fast-moving ten-armed cephalopod mollusk", preferred=True),
    ]
    assert parser_disambiguateSense(tok, cands).sense == "squid.n.01"


def test_no_preferred_falls_through_to_prior(_io, compile_zip):
    # without a flag and without evidence, the own-lemma smallest-NN prior stands (unchanged)
    from lib.llc.parser import parser_disambiguateSense
    tok = _tok(_io, "a squid is a mammal", "squid")
    cands = [
        _row("squid", "squid.n.01", "squid prepared as food"),
        _row("squid", "squid.n.02", "fast-moving ten-armed cephalopod mollusk"),
    ]
    assert parser_disambiguateSense(tok, cands).sense == "squid.n.01"


# ---- fix B live (self-activating once the operator ran curate_prefer_senses --apply) ---------------

def _flag_live(word, pos, sense):
    from lib.core.models import TKDictionaryDoc
    d = TKDictionaryDoc.find_one({"word": word, "pos": pos, "preferred": True}).run()
    return d is not None and d.sense == sense


def test_live_preferred_squid(compile_zip, _io):
    if not _flag_live("squid", "n", "squid.n.02"):
        pytest.skip("curate_prefer_senses --apply not run yet (operator-gated)")
    assert "squid.n.02" in _all_senses(compile_zip("a squid is a fish or a mammal"))


def test_live_preferred_calculator(compile_zip, _io):
    if not _flag_live("calculator", "n", "calculator.n.02"):
        pytest.skip("curate_prefer_senses --apply not run yet (operator-gated)")
    assert "calculator.n.02" in _all_senses(compile_zip("a calculator is a software"))


def test_live_preferred_fish_residual(compile_zip, _io):
    # the pisces residual: a meta-sentence whose centroid ranked the fish SIGN above the fish
    if not _flag_live("fish", "n", "fish.n.01"):
        pytest.skip("curate_prefer_senses --apply not run yet (operator-gated)")
    senses = _all_senses(
        compile_zip("this imply that fish, mammals and other kind of animals can live in water")
    )
    assert "pisces.n.02" not in senses

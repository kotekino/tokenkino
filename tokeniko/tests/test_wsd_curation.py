# ------------------------------------------------------------------------------------------------
# The dictionary curation batch (2026-07-14 portrait, cluster C) — WSD selection fixes + coverage.
#   A: Lesk excludes the QUERY TOKEN from the sentence side («gold is shiny» — glazed.a.03 won on
#      its gloss merely MENTIONING "shiny"; self-reference is not context fit).
#   B: a copular participle predicate («I am well RESTED») tries the surface form's ADJECTIVE
#      senses first (stanza lemmatizes to the dynamic verb, so rested.a.01 was never a candidate).
#   C: bit.n.06 (the information unit) curated into the dictionary (the ingestion's max_per_pos=3
#      cap cut it — the coin incident). Exact-sense asserts here are INTENTIONAL: the curated
#      selection is the regression target (unlike the band-assert default for drifting WSD).
# ------------------------------------------------------------------------------------------------
from lib.core.tkzip import TKZipContent


def _senses(zp):
    out = {}
    def walk(item):
        c = item.content
        if isinstance(c, TKZipContent):
            out.update(c.senses)
        elif isinstance(c, list):
            for ch in c:
                walk(ch)
    walk(zp.items)
    return out


def test_shiny_is_not_glazed(compile_zip):
    # the self-mention exclusion: glazed.a.03 ("having a shiny surface") must not win on the word
    # "shiny" alone; the prior then picks the sense that IS shiny (glistening.s.01, lemma shiny).
    senses = _senses(compile_zip("gold is shiny"))
    assert senses.get("predicate") != "glazed.a.03"
    assert ".v." not in (senses.get("predicate") or "")


def test_rested_is_stative(compile_zip):
    # the copular participle routes to the adjective ("not tired; refreshed"), never rest.v.*
    senses = _senses(compile_zip("This morning I am well rested"))
    pred = senses.get("predicate") or ""
    assert ".v." not in pred
    assert pred.startswith("rested.")


def test_bit_is_the_information_unit(compile_zip):
    # the curated coverage row: bit resolves to the information unit next to "information"
    senses = _senses(compile_zip("a bit is a unit of information"))
    assert senses.get("subject") == "bit.n.06"


def test_lesk_context_overlap_still_wins(compile_zip):
    # the original Lesk design case must survive the exclusion: disambiguating "cat" next to
    # "mammal" still finds the animal (the overlap word is CONTEXT, not the query word).
    senses = _senses(compile_zip("a cat is a mammal"))
    assert senses.get("subject") == "cat.n.01"

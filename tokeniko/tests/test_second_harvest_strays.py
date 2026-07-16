# ------------------------------------------------------------------------------------------------
# The second-harvest strays (2026-07-16 second session) — the last of the harvest queue:
#   1. PASSIVE-VOICE NORMALIZATION: «rain is caused by clouds» compiled subject=rain
#      indirect=clouds ≈ "rain causes clouds" — causality inverted live. A passive clause with an
#      explicit by-agent normalizes to the ACTIVE frame (agent -> subject, patient -> direct; the
#      "by" scaffold vanishes). Agent-less passives keep patient-as-subject (nothing to invert).
#   2. TITLE-CASE OOV GUARD: «Photoshop» (NER-empty, tagged NOUN) had no dictionary row and the
#      cross-word vector fallback fabricated adobe.n.01 THE CLAY. A title-case OOV token now goes
#      down the NAME path (known place / individual / NER-gated mint) or stays an honest unknown —
#      never nearest-matched into a common-noun class.
#   3. store→shop.n.01 («a coin stores bits»): found ALREADY HEALED by the degenerate retry
#      (07-14) — locked here as a regression.
#   (bit→bit.n.06 preferred = curation batch 2, tested in the WSD suite discipline post-apply.)
# ------------------------------------------------------------------------------------------------
from lib.core.kb_extract import _zip_leaves


def _leaf(compile_zip, s):
    leaves = _zip_leaves(compile_zip(s).items)
    assert leaves
    return leaves[0]


# ---- 1. passive-voice normalization ---------------------------------------------------------------

def test_passive_agent_becomes_subject(compile_zip):
    lf = _leaf(compile_zip, "rain is caused by clouds")
    assert lf.senses.get("subject") == "cloud.n.01"
    assert lf.senses.get("direct") == "rain.n.01"
    assert "by" not in lf.markers.values()        # the voice scaffold vanishes with the swap


def test_passive_equals_its_active_frame(compile_zip):
    # the normalization's whole point: both voices compile to the SAME role assignment
    passive = _leaf(compile_zip, "rain is caused by clouds")
    active = _leaf(compile_zip, "clouds cause rain")
    for role in ("subject", "predicate", "direct"):
        assert passive.senses.get(role) == active.senses.get(role)


def test_agentless_passive_keeps_patient_subject(compile_zip):
    # no agent, nothing to invert — today's shape stands
    lf = _leaf(compile_zip, "rain is caused")
    assert lf.senses.get("subject") == "rain.n.01"


def test_passive_named_agent_carries_identity(compile_zip):
    lf = _leaf(compile_zip, "the cake was eaten by Mari")
    assert (lf.identities.get("subject") or "").startswith("mari@")
    assert lf.senses.get("direct") == "cake.n.01"


# ---- 2. the title-case OOV guard ------------------------------------------------------------------

def test_titlecase_oov_never_fabricates_a_class(compile_zip):
    # the judge's finest line: "Photoshop is Adobe software, not clay"
    lf = _leaf(compile_zip, "Photoshop is a software")
    assert "adobe.n.01" not in lf.senses.values()
    assert lf.senses.get("subject") is None       # unresolved -> the unknown machinery (honest ask)
    assert lf.unknown


def test_titlecase_oov_midsentence_no_clay(compile_zip):
    # mid-sentence the NER may legitimately mint an individual — either way, never the clay
    lf = _leaf(compile_zip, "the author uses Photoshop")
    assert "adobe.n.01" not in lf.senses.values()


def test_known_capitalized_word_unaffected(compile_zip):
    # a capitalized DICTIONARY word never reaches the guard (direct hit first)
    lf = _leaf(compile_zip, "Cats are animals")
    assert lf.senses.get("subject") == "cat.n.01"


# ---- 3. the healed store lead, locked --------------------------------------------------------------

def test_coin_stores_bits_verb_reading(compile_zip):
    # stanza reads «a coin stores bits» as an all-NOUN compound pile; the degenerate retry
    # (07-14) recovers the verb — store.v.01, never shop.n.01 (the tracked lead, closed)
    lf = _leaf(compile_zip, "a coin stores bits")
    assert lf.senses.get("predicate") == "store.v.01"
    assert lf.senses.get("subject") == "coin.n.01"

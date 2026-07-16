# ------------------------------------------------------------------------------------------------
# M5 — dropped content (the third harvest, 2026-07-16). Three leads, three mechanisms:
#   1. the GENERIC-LOCATIVE restriction: a subject-attached nmod PP («animals IN THE WATER are
#      mammals») dropped entirely — carried now as subject_mod{i} + its case marker under the SAME
#      key (the restrictive-modifier machinery extended from amod/compound to nmod, subject side).
#      Dropping it silently WIDENS the quantifier («all animals in the water are fish» → «all
#      animals are fish»); the subject_mod presence also blocks the edge mint (the landed gate).
#   2. the INVERTED-QUESTION compound recovery: stanza misparses «are all minds animals?» (nsubj =
#      the bare DETERMINER "all", "minds" glued as compound) — the gated de-invert retry recovers
#      the real subject so the polar machinery engages instead of an unknown leaf.
#   3. the TYPO TANGLE («a mammal adn it feeds») demotes the predicate nominal — rag1's design case
#      (landed after the harvest specimen): lock the stumble-DETECTOR trigger; the cloud repair
#      itself stays untested by design.
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

from lib.core.kb_extract import extract_generic_isa_edges, _zip_leaves


def _leaf(compile_zip, s):
    leaves = _zip_leaves(compile_zip(s).items)
    assert leaves
    return leaves[0]


# ---- 1. the generic-locative restriction carrier -------------------------------------------------

def test_subject_locative_carried_with_marker(compile_zip):
    lf = _leaf(compile_zip, "some animals in the water are mammals")
    assert lf.senses.get("subject_mod0") == "water.n.01"
    assert lf.markers.get("subject_mod0") == "in"
    assert lf.senses.get("subject") == "animal.n.01"


def test_restricted_universal_mints_no_edge(compile_zip):
    # the S2 stake: dropping «in the water» would mint the FALSE «all animals are fish» — the
    # carried subject_mod now hits the extractor's restriction gate (no edge, ever)
    zp = compile_zip("all animals in the water are fish")
    lf = _zip_leaves(zp.items)[0]
    assert lf.senses.get("subject_mod0") == "water.n.01"     # the restriction is REPRESENTED
    doc = SimpleNamespace(zip=zp, original="all animals in the water are fish", id="m5-t1")
    edges, _ = extract_generic_isa_edges([doc], parents=lambda s: [])
    assert edges == []


def test_amod_restriction_unchanged(compile_zip):
    # the landed restrictive-modifier control (Brain v1.1 2c): amod mods keep working, marker-less
    lf = _leaf(compile_zip, "all thinking machines are minds")
    assert any(k.startswith("subject_mod") for k in lf.senses)
    assert not any(k.startswith("subject_mod") for k in lf.markers)


def test_verb_attached_pp_still_an_indirect(compile_zip):
    # the PP on the VERB keeps its clause-level indirect role — never demoted to a subject mod
    lf = _leaf(compile_zip, "a fish swims in the water")
    assert lf.senses.get("indirect0") == "water.n.01"
    assert lf.markers.get("indirect0") == "in"
    assert not any(k.startswith("subject_mod") for k in lf.senses)


def test_possessive_never_a_restriction(compile_zip):
    # nmod:poss is the possessive/DEFINITE machinery, not a restrictor
    lf = _leaf(compile_zip, "my mind is a software")
    assert not any(k.startswith("subject_mod") for k in lf.senses)
    assert getattr(lf.quantifier, "value", lf.quantifier) == "definite"


# ---- 2. the inverted-question compound recovery ---------------------------------------------------

def test_inverted_quantified_question_recovers_subject(compile_zip):
    lf = _leaf(compile_zip, "are all minds animals?")
    assert lf.senses.get("subject") == "mind.n.01"
    assert lf.senses.get("predicate") == "animal.n.01"
    assert getattr(lf.quantifier, "value", lf.quantifier) == "universal"
    assert lf.dubitative == 1.0                       # the question mood survives the de-invert
    assert not lf.unknown


def test_normal_polar_question_untouched(compile_zip):
    # a well-parsed polar question never enters the retry (the gate needs the broken shape)
    lf = _leaf(compile_zip, "is a cat an animal?")
    assert lf.senses.get("subject") == "cat.n.01"
    assert lf.dubitative == 1.0


def test_declarative_untouched(compile_zip):
    lf = _leaf(compile_zip, "all minds are animals")
    assert lf.senses.get("subject") == "mind.n.01"
    assert lf.dubitative != 1.0


# ---- 3. the typo tangle: the stumble-detector trigger is locked -----------------------------------

def test_typo_tangle_fires_the_stumble_detector(compile_zip):
    # «adn» demotes the predicate nominal (subject with no predicate = an unsound leaf) — exactly
    # what escalates to rag1 at the ears; the detector trigger is the regression surface
    from lib.llc.normalizer import detector_stumbles
    zp = compile_zip("a whale is a mammal adn it feeds milk")
    assert detector_stumbles(zp) is True


def test_clean_sentence_never_escalates(compile_zip):
    # NB pronoun-free control: «...and IT feeds milk» would ALSO escalate today via the known
    # pronoun-subject-leaf gap (roadmap §2, the escalate-and-always-reject lead) — a separate item,
    # deliberately not entangled with this regression.
    from lib.llc.normalizer import detector_stumbles
    zp = compile_zip("a whale is a mammal and whales feed milk")
    assert detector_stumbles(zp) is False

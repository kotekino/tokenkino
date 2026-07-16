# ------------------------------------------------------------------------------------------------
# M6 — QUANTIFIER SCOPE: ¬∀ first-class (2026-07-16).
#
# «NOT ALL S are P» (¬∀, the O corner — "not" advmod on the SUBJECT beside the universal det) and
# «all S are NOT P» (∀¬ — "not" on the predicate) both compiled universal+negated=True. Now ¬∀ is
# TKQuantifier.NEGATED_UNIVERSAL with `negated` free for true predicate polarity. Consumers: the
# square kernel (O / I corners), the grounding net_flip, the extractor (never mints from O — the
# old path could mint an E-strength «all S NOT P» rule from an O claim), the correction detector
# (both arrivals), and conclusion_key (a bool discriminator slot — coarse on purpose, dedup
# continuity with stored theorems).
# ------------------------------------------------------------------------------------------------
import pytest
from types import SimpleNamespace

from lib.core.tk import TKQuantifier
from lib.core.kb_extract import _zip_leaves, extract_rules


def _leaf(zp, i=0):
    return _zip_leaves(zp.items)[i]


def test_not_all_is_negated_universal(compile_zip):
    c = _leaf(compile_zip("not all minds are software"))
    assert c.quantifier == TKQuantifier.NEGATED_UNIVERSAL
    assert c.negated is False, "the negation scopes the quantifier, not the predicate"


def test_all_not_keeps_predicate_negation(compile_zip):
    c = _leaf(compile_zip("all minds are not software"))
    assert c.quantifier == TKQuantifier.UNIVERSAL
    assert c.negated is True


def test_not_every_with_verb_object(compile_zip):
    # the author's own quantifier-ladder sentence (the cloud corpus)
    c = _leaf(compile_zip("not every cloud produces rain"))
    assert c.quantifier == TKQuantifier.NEGATED_UNIVERSAL
    assert c.negated is False


def test_o_claim_never_mints_a_rule(compile_zip):
    # the closed hole: universal+negated used to reach the rule extractor as an E-strength
    # «all S are NOT P» — an O claim asserts only an exception's existence, never a law
    zp = compile_zip("not all minds are software")
    doc = SimpleNamespace(zip=zp, original="not all minds are software", id="m6-test")
    assert extract_rules([doc]) == []


def test_square_kernel_o_corner(compile_zip):
    # ¬∀ + ∃: jointly the truth — the dialogue's bounced sentence must stay consistent
    from lib.llc.evaluator.e_consistency import evaluator_classifyForm
    zp = compile_zip("not all softwares are minds and some softwares are minds")
    form = evaluator_classifyForm(zp)
    assert form.contradiction is False


def test_correction_detector_reads_negated_universal(compile_zip):
    # the LIVE RETREAT's trigger shape («not all softwares are minds») must still be seen as an
    # O-corner correction after the representation change — unit-level: the corner test itself
    from lib.core.tk import TKQuantifier as Q
    c = _leaf(compile_zip("not all softwares are minds"))
    quantifier, negated = c.quantifier, bool(c.negated)
    is_o = (quantifier == Q.UNIVERSAL and negated) or \
           (quantifier == Q.NEGATED_UNIVERSAL and not negated)
    assert is_o, "the retreat's O-corner detection must survive the new representation"


def test_conclusion_key_distinguishes_not_all_from_all(compile_zip):
    from lib.core.evaluation_harness import conclusion_key
    k_not_all = conclusion_key(compile_zip("not all minds are software"))
    k_all = conclusion_key(compile_zip("all minds are software"))
    assert k_not_all != k_all


def test_plain_universal_untouched(compile_zip):
    c = _leaf(compile_zip("all cats are mammals"))
    assert c.quantifier == TKQuantifier.UNIVERSAL
    assert c.negated is False

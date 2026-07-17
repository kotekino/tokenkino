# ------------------------------------------------------------------------------------------------
# Adverbial quantifiers (2026-07-17, basket item 3 — the Socratic dialogue's F4: the Cap's ladder
# «a mind ALWAYS thinks / a software SOMETIMES thinks / a calculator NEVER thinks» compiled with
# the adverbs as inert modifiers). always/sometimes/never now land the clause on its square
# corner: ∀ (A) / ∃ (I) / NEGATIVE (E). Rules of engagement, each probed: only an
# INDEFINITE/GENERIC subject accepts the upgrade — an explicit determiner quantifier WINS («all
# calculators never think» stays ∀¬, "never" = plain negation there); "never"-as-quantifier is
# RECLASSIFIED out of clause polarity (the det-"no" rule's adverbial mirror — no double flip);
# a non-quantifying adverb leaves everything untouched (anchor default None, EXACT closed-class).
# Fuel consequences: always → law-strength rule; sometimes → NO rule (the «most softwares think»
# ∃-inflation cured); never → the negative rule (E-corner fuel).
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

from lib.core.tk import TKQuantifier
from lib.core.tkzip import TKZipContent
from lib.core.kb_extract import extract_rules


def _leaf(zp):
    leaves = []
    def walk(item):
        c = item.content
        if isinstance(c, TKZipContent):
            leaves.append(c)
        elif isinstance(c, list):
            for ch in c:
                walk(ch)
    walk(zp.items)
    assert len(leaves) == 1
    return leaves[0]


def _rules(zp, original):
    return extract_rules([SimpleNamespace(zip=zp, original=original, id="advq-test")])


# ---- the ladder: each rung on its corner -------------------------------------------------------------

def test_always_is_universal(compile_zip):
    s = "a mind always thinks"
    zp = compile_zip(s)
    leaf = _leaf(zp)
    assert leaf.quantifier == TKQuantifier.UNIVERSAL and not leaf.negated
    rules = _rules(zp, s)
    assert len(rules) == 1 and rules[0]["strength"] == "universal"   # a LAW, not a generic


def test_sometimes_is_existential_and_mints_nothing(compile_zip):
    s = "a software sometimes thinks"
    zp = compile_zip(s)
    leaf = _leaf(zp)
    assert leaf.quantifier == TKQuantifier.EXISTENTIAL and not leaf.negated
    assert _rules(zp, s) == []          # ∃ never inflates to «most softwares think»


def test_never_is_the_e_corner(compile_zip):
    s = "a calculator never thinks"
    zp = compile_zip(s)
    leaf = _leaf(zp)
    assert leaf.quantifier == TKQuantifier.NEGATIVE
    assert not leaf.negated             # reclassified: the negation IS the quantifier (no double flip)
    rules = _rules(zp, s)
    assert len(rules) == 1 and rules[0]["negated"] and rules[0]["strength"] == "universal"


# ---- an explicit determiner quantifier wins ----------------------------------------------------------

def test_universal_det_keeps_never_as_negation(compile_zip):
    # «all calculators never think» = ∀¬ — the det rules the quantifier, "never" stays polarity
    leaf = _leaf(compile_zip("all calculators never think"))
    assert leaf.quantifier == TKQuantifier.UNIVERSAL and leaf.negated


def test_bare_plural_accepts_the_upgrade(compile_zip):
    # GENERIC (bare plural) upgrades just like INDEFINITE
    leaf = _leaf(compile_zip("minds always think"))
    assert leaf.quantifier == TKQuantifier.UNIVERSAL


# ---- non-quantifying adverbs stay inert --------------------------------------------------------------

def test_plain_adverb_is_untouched(compile_zip):
    leaf = _leaf(compile_zip("a cat quickly runs"))
    assert leaf.quantifier == TKQuantifier.INDEFINITE and not leaf.negated


def test_intensifier_regression(compile_zip):
    # the advmod-intensifier machinery ("very" = 1.5 fuzzy scalar) shares the dep — untouched
    leaf = _leaf(compile_zip("a dog is very big"))
    assert leaf.quantifier == TKQuantifier.INDEFINITE and not leaf.negated


def test_object_carrying_sentence(compile_zip):
    s = "a bird always has feathers"
    zp = compile_zip(s)
    assert _leaf(zp).quantifier == TKQuantifier.UNIVERSAL
    rules = _rules(zp, s)
    assert len(rules) == 1 and rules[0]["strength"] == "universal" \
        and rules[0]["object"] == "feather.n.01"

# ------------------------------------------------------------------------------------------------
# Nominal IMPLY (2026-07-17, basket item 2 — the Cap's curtain «action imply ability» folded bare
# AND, the implication invisible). «X implies Y» with CLASS-noun operands now compiles to
# IMPLY(antecedent, consequent) — each noun a predicate-only operand leaf (the copular-predication
# precedent) — so the assertedness gate SEES the compound and no leaf masquerades as a standalone
# assertion. Conservative fallbacks, each probed: a NEGATED implication keeps today's single-leaf
# compile (¬(A→B) has no per-leaf home yet); an unresolved/individual operand never fabricates an
# IMPLY. Extraction stays SHUT (GENERIC operands never satisfy the property-conditioned UNIVERSAL
# bar) — nominal-IMPLY-as-chainer-fuel is a deliberate non-goal here.
# ------------------------------------------------------------------------------------------------
from types import SimpleNamespace

from lib.core.tk import TKOperator
from lib.core.tkzip import TKZipContent
from lib.core.kb_extract import extract_facts, extract_rules, _zip_is_asserted
from lib.llc.evaluator import evaluator_classifyForm


def _leaves_with_ops(zp):
    out = []
    def walk(item):
        c = item.content
        if isinstance(c, TKZipContent):
            out.append((item.op, c))
        elif isinstance(c, list):
            for ch in c:
                walk(ch)
    walk(zp.items)
    return out


def _no_fuel(zp, original):
    doc = SimpleNamespace(zip=zp, original=original, id="nom-imply-test")
    assert extract_rules([doc]) == []
    assert extract_facts([doc]) == []


def test_nominal_imply_compiles_the_implication(compile_zip):
    zp = compile_zip("action implies ability")
    pairs = _leaves_with_ops(zp)
    assert [op for op, _ in pairs] == [TKOperator.AND, TKOperator.IMPLY]
    assert pairs[0][1].senses == {"predicate": "action.n.01"}   # predicate-only operand leaves
    assert pairs[1][1].senses == {"predicate": "ability.n.01"}
    assert not _zip_is_asserted(zp.items)                       # the gate SEES the compound
    _no_fuel(zp, "action implies ability")                      # and extraction stays shut


def test_determiners_ride_along(compile_zip):
    zp = compile_zip("an action implies an ability")
    assert [op for op, _ in _leaves_with_ops(zp)] == [TKOperator.AND, TKOperator.IMPLY]


def test_rain_implies_clouds_now_consumed(compile_zip):
    # the docstring's old fallback example IS a nominal implication — consumed since 2026-07-17
    zp = compile_zip("rain implies clouds")
    pairs = _leaves_with_ops(zp)
    assert [op for op, _ in pairs] == [TKOperator.AND, TKOperator.IMPLY]
    assert pairs[0][1].senses.get("predicate", "").startswith("rain.")
    _no_fuel(zp, "rain implies clouds")


def test_kernel_never_reads_it_contradictory(compile_zip):
    # the axiom-create contradiction guard runs classifyForm on this shape — it must classify
    # cleanly (contingent), never crash, never fold to always-false
    form = evaluator_classifyForm(compile_zip("action implies ability"))
    assert not form.contradiction


def test_negated_implication_falls_back(compile_zip):
    # «ability doesn't imply action»: ¬(A→B) has no per-leaf home — today's single negated leaf
    # stays (asserted, as before this feature; the negative curtain half is a known open thread)
    zp = compile_zip("ability doesn't imply action")
    pairs = _leaves_with_ops(zp)
    assert TKOperator.IMPLY not in [op for op, _ in pairs]
    assert len(pairs) == 1 and pairs[0][1].negated


def test_unresolved_name_operand_falls_back(compile_zip):
    # a subject that resolves to no class sense (bare name, no NER context) must never fabricate
    # an implication — the normal single-leaf path stands
    zp = compile_zip("Salmon implies trouble")
    assert TKOperator.IMPLY not in [op for op, _ in _leaves_with_ops(zp)]


def test_clausal_implication_regression(compile_zip):
    # the ORIGINAL clausal hook is untouched: two CCOMP complements still fold IMPLY
    # (sentence probed to root cleanly — «a machine thinks implies…» hits the documented
    # Stanza mis-root and falls back, which is the pre-existing limitation, not this feature's)
    zp = compile_zip("a thing exists implies a thing is real")
    pairs = _leaves_with_ops(zp)
    assert [op for op, _ in pairs] == [TKOperator.AND, TKOperator.IMPLY]
    assert pairs[0][1].senses.get("subject") == "thing.n.01"    # clausal operands keep subjects
    assert not _zip_is_asserted(zp.items)

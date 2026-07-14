# ------------------------------------------------------------------------------------------------
# The harvest singles (2026-07-14 portrait, cluster E + the B-nugget + the WSD-probe lead) — the
# last four leads of the first portrait, closed in one batch:
#   S1 THAT-wrap: a ccomp under a NON-attitude matrix verb (below the anchor floor — "build") is a
#      stanza-flattened coordination, co-asserted AND (attitude default now (None, 0.5)).
#   S2 wh-gap by verb frame: what->PREDICATE is the copular frame; under a content verb the gap is
#      the DIRECT object («what do you like?») + the solver's DIRECT case.
#   S3 elided-subject quantifier inheritance: the conjunct inherits the head's determiner with the
#      subject («THE cat is dead and alive» — both leaves definite).
#   S4 degenerate-parse retry (do-support): a verbless NP-flattened parse («a coin stores bits» —
#      stanza AND spaCy tag "stores" NOUN) retries with "does <lemma>" and adopts a VERB-root parse.
# ------------------------------------------------------------------------------------------------
from lib.core.tk import TKOperator, TKQuantifier, TKWhRole
from lib.core.tkzip import TKZipContent


def _walk(zp):
    out = []
    def rec(item):
        c = item.content
        if isinstance(c, TKZipContent):
            out.append((item.op, getattr(item, "attitude", None), c))
        elif isinstance(c, list):
            for ch in c:
                rec(ch)
    rec(zp.items)
    return out


# ---- S1: suspect ccomp co-asserts ---------------------------------------------------------------

def test_nonattitude_ccomp_is_coasserted(compile_zip):
    zp = compile_zip("I build software and softwares are programs")
    entries = _walk(zp)
    assert all(op == TKOperator.AND for op, _, _ in entries)          # no THAT wrap
    assert all(att is None for _, att, _ in entries)                  # no fabricated attitude
    assert any(c.senses.get("subject") == "software.n.01" and
               c.senses.get("predicate", "").startswith("program") for _, _, c in entries)


def test_genuine_attitude_ccomp_keeps_that(compile_zip):
    zp = compile_zip("I think that cats are animals")
    entries = _walk(zp)
    that = [(op, att) for op, att, _ in entries if op == TKOperator.THAT]
    assert len(that) == 1
    assert that[0][1] is not None and that[0][1].klass == "doxastic"


def test_xcomp_keeps_that_even_below_floor(compile_zip):
    # F2 must survive S1: the open complement is structurally reliable whatever the attitude
    zp = compile_zip("I like talking")
    assert any(op == TKOperator.THAT for op, _, _ in _walk(zp))


# ---- S2: wh-gap by verb frame ---------------------------------------------------------------------

def test_what_under_content_verb_gaps_direct(compile_zip):
    zp = compile_zip("what do you like?")
    leaf = _walk(zp)[0][2]
    assert leaf.dubitative == 1.0
    assert leaf.wh_role == TKWhRole.DIRECT


def test_what_copular_still_gaps_predicate(compile_zip):
    zp = compile_zip("what is a cat?")
    leaf = _walk(zp)[0][2]
    assert leaf.wh_role == TKWhRole.PREDICATE


def test_wh_direct_solver_reads_object(compile_zip):
    from lib.core.evaluation_harness import _load_active_kb
    from lib.llc.evaluator import evaluator_solveWh
    fact = compile_zip("I like software")
    question = compile_zip("what do you like?")
    wh_leaf = next(c for _, _, c in _walk(question) if c.wh_role is not None)
    kb = _load_active_kb()
    out = evaluator_solveWh(wh_leaf, [fact], [], kb["relations"])
    assert out.verdict.value == "value"
    assert out.value == "software"


# ---- S3: quantifier inheritance ---------------------------------------------------------------------

def test_conjunct_inherits_definite(compile_zip):
    zp = compile_zip("the cat is dead and alive")
    leaves = [c for _, _, c in _walk(zp)]
    assert all(c.quantifier == TKQuantifier.DEFINITE for c in leaves)


def test_own_determiner_not_overwritten(compile_zip):
    # a conjunct with its OWN subject+determiner keeps it
    zp = compile_zip("the cat sleeps and a dog runs")
    quants = {c.senses.get("subject", "?").split(".")[0]: c.quantifier for _, _, c in _walk(zp)}
    assert quants.get("cat") == TKQuantifier.DEFINITE
    assert quants.get("dog") == TKQuantifier.INDEFINITE


# ---- S4: the do-support degenerate-parse retry --------------------------------------------------------

def test_verbless_np_parse_recovers_the_verb(compile_zip):
    zp = compile_zip("a coin stores bits of information")
    leaf = _walk(zp)[0][2]
    assert leaf.senses.get("subject") == "coin.n.01"
    assert leaf.senses.get("predicate", "").startswith("store.v")
    assert leaf.senses.get("direct", "").startswith("bit.")


def test_true_noun_phrase_not_rewritten(compile_zip):
    # a genuine NP with no S-V-O signature must NOT be reinterpreted
    zp = compile_zip("the red cats")
    leaf = _walk(zp)[0][2]
    assert not (leaf.senses.get("predicate", "").startswith("cat.v"))

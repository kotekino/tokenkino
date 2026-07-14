# ------------------------------------------------------------------------------------------------
# Complement/locative survival (2026-07-14 portrait, cluster D — the sleeper) + the places bridge.
#   F1: a known place is a named INDIVIDUAL — global uid ("japan@place") + type-column centroid; the
#       role is symbolically alive (identities + markers + live vector), so «you live in Japan»
#       never again compiles the geography away.
#   P2: the author's hand-curated places table (complete path_admin/path_geo chains + type) is
#       reasoning-live via injected readers: containment grounds TRUE/FALSE, type synthesizes the
#       is_a subject sense, "where" questions read the place off the KB/table.
#   F2: xcomp folds THAT («I like talking» is an attitude complement, not two assertions).
#   F3: a compound/hyphenated known name is recognized as the assembled string.
# Band-asserts: statuses, truth bands, structural facts — never exact floats/senses.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core.tk import TKOperator


def _leaves(zp):
    from lib.core.tkzip import TKZipContent
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


def _semantically_alive(vec):
    return vec and any(x != 0.0 for x in vec[300:3225])


# ---- F1: the place identity-bridge ------------------------------------------------------------------

def test_locative_complement_survives(compile_zip):
    zp = compile_zip("you live in Japan")
    ops, cs = zip(*_leaves(zp))
    c = cs[0]
    assert c.identities.get("indirect0") == "japan@place"     # the geography is symbolically alive
    assert c.markers.get("indirect0") == "in"                 # the RELATOR survives beside it
    assert _semantically_alive(c.indirects[0])                # type centroid, not an all-zero slot


def test_place_as_predicate_survives(compile_zip):
    # the relative-clause variant: "is in Japan" lands the place as the copular PREDICATE
    zp = compile_zip("the computer where you live is in Japan")
    cs = [c for _, c in _leaves(zp)]
    main = next(c for c in cs if c.senses.get("subject", "").startswith("computer"))
    assert main.identities.get("predicate") == "japan@place"
    assert main.markers.get("predicate") == "in"


# ---- P2: the places readers ground and answer --------------------------------------------------------

def test_containment_grounds_true(compile_zip):
    from lib.core.evaluation_harness import evaluate_zip
    r = evaluate_zip(compile_zip("Japan is in Asia"))["result"]
    assert r.status.value == "resolved"
    assert r.truth > 0.85
    assert any("places" in d for d in r.derivation)


def test_containment_grounds_false(compile_zip):
    from lib.core.evaluation_harness import evaluate_zip
    r = evaluate_zip(compile_zip("Japan is in Europe"))["result"]
    assert r.status.value == "resolved"
    assert r.truth < 0.15


def test_containment_negation_flips(compile_zip):
    from lib.core.evaluation_harness import evaluate_zip
    r = evaluate_zip(compile_zip("Japan is not in Europe"))["result"]
    assert r.status.value == "resolved"
    assert r.truth > 0.85


def test_place_type_isa_grounds(compile_zip):
    from lib.core.evaluation_harness import evaluate_zip
    r = evaluate_zip(compile_zip("Japan is a country"))["result"]
    assert r.status.value == "resolved"
    assert r.truth > 0.85


def test_where_is_a_place(answer):
    out = answer("where is Rome?")
    assert out.verdict.value == "value"
    assert out.value == "lazio"                               # admin parent — the human answer


def test_where_from_kb_fact(compile_zip):
    from lib.core.evaluation_harness import _load_active_kb
    from lib.llc.evaluator import evaluator_solveWh
    fact = compile_zip("you live in Japan")
    question = compile_zip("where do you live?")
    wh_leaf = next(c for _, c in _leaves(question) if c.wh_role is not None)
    kb = _load_active_kb()
    out = evaluator_solveWh(wh_leaf, [fact], [], kb["relations"], place_parent=kb["place_parent"])
    assert out.verdict.value == "value"
    assert out.value == "japan"


# ---- F2: xcomp folds THAT ----------------------------------------------------------------------------

def test_gerund_complement_folds_that(compile_zip):
    zp = compile_zip("I like talking")
    ops = [op for op, _ in _leaves(zp)]
    assert TKOperator.THAT in ops                             # the complement is attitude-bound
    assert ops.count(TKOperator.AND) <= 1                     # never two coordinate assertions


# ---- F3: compound-name assembly ----------------------------------------------------------------------

@pytest.fixture()
def _hyphen_stakeholder(_io):
    from lib.core.models import TKMemoryStakeholdersDoc
    doc = TKMemoryStakeholdersDoc.find_one({"name": "test-probe-hellen"}).run()
    if doc is None:
        TKMemoryStakeholdersDoc(name="test-probe-hellen", uid="probe-hellen-uid",
                                kind="participant", ner_type="PERSON").insert()


def test_compound_known_name_recognized(compile_zip, _hyphen_stakeholder):
    zp = compile_zip("I like test-probe-hellen")
    c = _leaves(zp)[0][1]
    assert c.identities.get("direct") == "probe-hellen-uid"   # the assembled name found its soul
    assert not any(k.startswith("direct_mod") for k in c.senses)  # name pieces are not modifiers

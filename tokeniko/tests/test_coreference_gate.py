# ------------------------------------------------------------------------------------------------
# The coreference gate + the derivation mirror (2026-07-18 — the MAMMAL INCIDENT, found live by
# the author talking to a friend in-channel). Two bugs, one root class (context-blind machinery):
#   1. «you» resolved to tokeniko UNCONDITIONALLY — the author's «so you are a mammal», aimed at
#      his friend at directedness 0.15, taught «so I am a mammal» (+ derived «I am not a reptile»,
#      true for the wrong reason). Now «you»→tokeniko ONLY when ADDRESSED (d>=0.9); ambient «you»
#      stays an unresolved uid-less stub — no identity, no fact, no teaching.
#   2. A forward-chain derived «kotekino is an animal» AND «kotekino is not an animal» in ONE
#      closure (through the stale «a mind is a software» premise) and materialized + published the
#      contradiction. The DERIVATION MIRROR stamps such conclusions conflict=True: they never
#      materialize (kb_wonder) and never decide a truth (chainGround abstains).
# ------------------------------------------------------------------------------------------------
import copy
from types import SimpleNamespace

import pytest

from lib.core.kb_extract import extract_facts
from lib.core.tk import TKQuantifier
from lib.llc.evaluator.e_chaining import evaluator_forwardChain, evaluator_chainGround
from lib.llc.normalizer import detector_stumbles, detector_unrepairable


@pytest.fixture(scope="session")
def compile_ambient(_io):
    tok, ai = _io
    from lib.llc.parser import parser
    from lib.llc.compiler import compiler_compile

    def _c(sentence, addressed=False):
        rec = parser(sentence, tok, tok, ai, addressed=addressed)
        return compiler_compile(copy.deepcopy(rec))  # (TKLLC, TKZip)

    return _c


def _leaf(zp):
    leaves = []
    def walk(item):
        c = item.content
        if isinstance(c, list):
            for ch in c:
                walk(ch)
        else:
            leaves.append(c)
    walk(zp.items)
    return leaves[0]


# ---- the coreference gate ------------------------------------------------------------------------------

def test_addressed_you_still_resolves_to_tokeniko(compile_zip):
    # default addressed=True: the identity bridge unchanged (DMs, API, seeds, every old test)
    leaf = _leaf(compile_zip("you are a mammal"))
    assert (leaf.identities or {}).get("subject") == "tokeniko"


def test_ambient_you_resolves_to_nobody(compile_ambient):
    # THE MAMMAL REPLAY: the author to his friend, someone else's thread — «you» is unknowable
    llc, zp = compile_ambient("so you are a mammal", addressed=False)
    leaf = _leaf(zp)
    assert (leaf.identities or {}).get("subject") is None    # no identity minted
    assert (leaf.senses or {}).get("subject") is None        # and no fabricated sense
    assert extract_facts([SimpleNamespace(zip=zp, original="so you are a mammal",
                                          id="mammal-test")]) == []   # no fact about anyone


def test_ambient_you_is_an_unrepairable_stumble(compile_ambient):
    # the unresolved «you» leaf is honest machinery end-to-end: a stumble no Haiku call can fix
    llc, zp = compile_ambient("so you are a mammal", addressed=False)
    assert detector_stumbles(zp) is True
    assert detector_unrepairable(llc, zp) is True


def test_headless_leaf_never_teaches(compile_ambient, monkeypatch):
    # the belt: even from an imprint-trust teacher, a subject-less assertion is not knowledge
    from brain import thinking
    from lib.core import trust as trust_mod
    _, zp = compile_ambient("so you are a mammal", addressed=False)
    soul = SimpleNamespace(isMe=False, imprint=True, trust=1.0, name="kotekino",
                           uid="kotekino@test", id="soul-1")
    monkeypatch.setattr(trust_mod, "resolve_canonical", lambda ref: soul)
    item = SimpleNamespace(zip=zp, original="so you are a mammal", sourceId="kotekino@test",
                           channel=None, directedness=0.15)
    assert thinking.materialize_taught(item) is False


def test_addressed_correction_still_teaches_shape(compile_zip):
    # the counterpart that MUST keep working: the addressed d=0.9 correction resolved correctly
    leaf = _leaf(compile_zip("you are not a mammal"))
    assert (leaf.identities or {}).get("subject") == "tokeniko"
    assert leaf.negated


# ---- the derivation mirror ------------------------------------------------------------------------------

# the mammal-incident shape, synthetic (the chainer's real vocabulary): MEMBERSHIP rules extend
# the closure (human -is_a-> animal -> «all animals are minds» -> «a mind is a software» — the
# STALE premise) and the NEGATED membership «software are not animals» then fires AGAINST a class
# the closure itself holds. animal ∈ C and ¬animal derived: the incident, distilled.
_PARENTS = lambda s: {"human.n.01": ["animal.n.01"], "animal.n.01": []}.get(s, [])
_RULES = [
    {"subject": "animal.n.01", "predicate": "mind.n.01", "object": None, "negated": False,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-animals-minds"},
    {"subject": "mind.n.01", "predicate": "software.n.01", "object": None, "negated": False,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-mind-software"},
    {"subject": "software.n.01", "predicate": "animal.n.01", "object": None, "negated": True,
     "kind": "membership", "cond_props": [], "strength": "universal", "source_id": "r-software-not-animal"},
]
_MEMBER = {"subject_uid": "kotekino@test", "klass_sense": "human.n.01",
           "predicate": "human.n.01", "negated": False, "source_id": "fact-k-human"}


def _chain_membership_rules():
    # membership rules climb the closure; the negative rule fires against it
    derived, _ = evaluator_forwardChain(None, "kotekino@test", _RULES, _PARENTS, [_MEMBER])
    return derived


def test_mirror_stamps_the_contradiction():
    derived = _chain_membership_rules()
    by_key = {(d["predicate"], bool(d.get("negated", False))): d for d in derived}
    not_animal = by_key.get(("animal.n.01", True))
    assert not_animal is not None, "the incident shape must reproduce (rule chain fires)"
    assert not_animal.get("conflict") is True          # the mirror sees it
    assert "CONFLICT" in not_animal["chain"]


def test_conflicted_conclusion_never_materializes():
    derived = _chain_membership_rules()
    # the kb_wonder consumer contract: conflict-stamped conclusions are skipped
    materializable = [d for d in derived if not d.get("conflict")
                      and len(d.get("premises", [])) >= 2]
    assert all(not (d["predicate"] == "animal.n.01" and d.get("negated"))
               for d in materializable)


def test_conflicted_chain_decides_nothing():
    # chainGround must ABSTAIN on «kotekino is an animal» when the chain self-contradicts —
    # neither corroborated nor refuted (a broken derivation has no vote; logic is sacred)
    content = SimpleNamespace(senses={"predicate": "animal.n.01"},
                              identities={"subject": "kotekino@test"},
                              negated=False, quantifier=TKQuantifier.GENERIC)
    out = evaluator_chainGround(content, _RULES, _PARENTS, [_MEMBER])
    assert out is None


def test_clean_chain_still_decides():
    # remove the poison rule -> the mirror stays silent and chaining decides normally
    clean = [r for r in _RULES if r["source_id"] != "r-mind-software"] + [
        {"subject": "mind.n.01", "predicate": "seek.v.01", "object": None, "negated": False,
         "kind": "property", "cond_props": [], "strength": "universal", "source_id": "r-minds-seek"},
    ]
    derived, _ = evaluator_forwardChain(None, "kotekino@test", clean, _PARENTS, [_MEMBER])
    assert all(not d.get("conflict") for d in derived)
    content = SimpleNamespace(senses={"predicate": "seek.v.01"},
                              identities={"subject": "kotekino@test"},
                              negated=False, quantifier=TKQuantifier.GENERIC)
    out = evaluator_chainGround(content, clean, _PARENTS, [_MEMBER])
    assert out is not None and out[0] > 0.8            # corroborated: kotekino seeks

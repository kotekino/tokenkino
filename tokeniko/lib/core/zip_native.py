# --------------------------------------------------------------
# lib/core/zip_native.py — ZIP-NATIVE ASSEMBLY (instrument arc #2): a derived conclusion's
# structure becomes a first-class TKZip WITHOUT the NL render → parse → recompile round trip.
# A mind should think in its own representation — NL is I/O, not thought.
#
# PARSER-FREE by construction (imports only lib.core.* — never lib.llc.parser/compiler): the
# assembler rebuilds exactly what the compiler would emit for the canonical conclusion shapes,
# from the same sources of truth:
#   - semantic 2925  = tanh(dictionary sense vector)  — byte-identical to compiler_zipGetEntityVector
#                      (an identity-linked individual subject gets its stakeholder's stored type
#                      centroid, same slot, same honest geometry);
#   - markers 300    = zeros — the canonical SVO conclusion carries no preposition on any role
#                      (the compiler itself emits zeros when a reference has no marker);
#   - spacetime 12   = neutral (zeros) — a derived generic/fact is timeless, which is precisely
#                      what the compiler computes for an unanchored declarative;
#   - flags          = carried straight from the derivation (negated, quantifier, identities) —
#                      no WSD, no drift, nothing to re-pin.
#
# v1 SCOPE (deliberate): the single-leaf SVO shapes the reasoning layer actually derives —
# class-generic or identity-linked-individual subject, verb/adjective/noun predicate, optional
# direct object, negation. Multi-clause conclusions do not exist as derivations yet; when they
# do, they are born here, not in the parser.
#
# The EQUIVALENCE HARNESS (tests/test_zip_native.py) is this module's discipline: for the shape
# battery, native assembly and the compiled render must agree on conclusion_key, flags, per-role
# geometry, and — the deep check — the evaluator's verdict.
# --------------------------------------------------------------
import logging
import math
from typing import Optional

from lib.core.constants import _ME_UID
from lib.core.models import TKDictionaryDoc, TKMemoryStakeholdersDoc
from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkllc import TKLLAttitude
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem

logger = logging.getLogger("tokeniko-brain")

_MARKER_DIMS = 300
_SEMANTIC_DIMS = 2925
_SPACETIME_DIMS = 12
_ROLE_DIMS = _MARKER_DIMS + _SEMANTIC_DIMS + _SPACETIME_DIMS  # 3237


# in-process cache: sense/uid -> the ready 2925 semantic block (post-tanh). The dictionary is
# design-time static and a stakeholder's type centroid never changes, so the cache is safe.
_semantic_cache: dict[str, Optional[list[float]]] = {}


def _tanh(vec: list[float]) -> list[float]:
    return [math.tanh(v) for v in vec]


# the 2925 semantic block for a role: a WSD sense key ("cat.n.01") reads the dictionary vector;
# an identity uid ("mari@internal:tokeniko", or tokeniko's own uid) reads the stakeholder's stored
# NER type centroid (the identity-bridge's honest geometry). tanh-normalized exactly like
# compiler_zipGetEntityVector. None when the vector is unknown -> the caller must refuse (an
# ungrounded belief must never be assembled from zeros).
def _semantic_block(key: str) -> Optional[list[float]]:
    if key in _semantic_cache:
        return _semantic_cache[key]
    vec: Optional[list[float]] = None
    if "." in key and "@" not in key:  # a sense key
        doc = TKDictionaryDoc.find_one({"sense": key}).run()  # Bunnet: .run() executes
        if doc is not None and doc.vector:
            vec = _tanh(doc.vector)
    else:  # an identity uid (individual or tokeniko himself)
        sh = TKMemoryStakeholdersDoc.find_one({"uid": key}).run()
        if sh is not None and sh.vector:
            vec = _tanh(sh.vector)
    if vec is not None and len(vec) != _SEMANTIC_DIMS:
        logger.warning("[zip_native] %s carries a %d-dim vector (want %d) — refusing", key, len(vec), _SEMANTIC_DIMS)
        vec = None
    _semantic_cache[key] = vec
    return vec


def _role_tensor(semantic: Optional[list[float]]) -> list[float]:
    sem = semantic if semantic is not None else [0.0] * _SEMANTIC_DIMS
    return [0.0] * _MARKER_DIMS + sem + [0.0] * _SPACETIME_DIMS


# --------------------------------------------------------------
# assemble a derived conclusion into a TKZip. Returns None when any named role cannot be grounded
# (unknown sense / vectorless uid) — the caller falls back or refuses; a belief is never assembled
# over a hole.
#
#   subject       — a class sense ("cat.n.01") OR an identity uid ("mari@…", tokeniko's uid)
#   predicate     — a sense key (".v."/".a."/".s."/".n." decide the conclusion's grammatical shape
#                   downstream, but here they are just the dictionary lookup)
#   object        — optional direct-object sense
#   negated       — the clause asserts ¬P
#   subject_kind  — "class" | "individual" (kb_wonder's own vocabulary; individual -> identities)
#   quantifier    — override; defaults to INDEFINITE for a class subject (the compiled render
#                   "a cat …" carries the indefinite article) and DEFINITE for an individual.
# --------------------------------------------------------------
def assemble_conclusion_zip(subject: str, predicate: str, object: Optional[str] = None,
                            negated: bool = False, subject_kind: Optional[str] = None,
                            quantifier: Optional[TKQuantifier] = None) -> Optional[TKZip]:
    if not subject or not predicate:
        return None
    is_individual = subject_kind == "individual" or subject == _ME_UID or "@" in subject

    subj_sem = _semantic_block(subject)
    pred_sem = _semantic_block(predicate)
    obj_sem = _semantic_block(object) if object else None
    # an IDENTITY subject with no stored type centroid gets honest ZEROS — exactly the compiler's
    # behavior for a bare name ("meaning lives in the grounded 2925 geometry — a bare name still
    # has []"); the identity uid carries the reference. A SENSE that fails the dictionary lookup
    # is different: nothing to assert about nothing — refuse.
    if subj_sem is None and is_individual:
        subj_sem = [0.0] * _SEMANTIC_DIMS
    if pred_sem is None or subj_sem is None or (object and obj_sem is None):
        logger.info("[zip_native] ungroundable role (subject=%s predicate=%s object=%s) — no assembly",
                    subject, predicate, object)
        return None

    senses: dict[str, str] = {"predicate": predicate}
    identities: dict[str, str] = {}
    if is_individual:
        identities["subject"] = subject
    else:
        senses["subject"] = subject
    if object:
        senses["direct"] = object

    if quantifier is None:
        # equivalence-pinned defaults (probe 2026-07-15): the compiled render of an individual
        # fact has a BARE subject ("I exist", "Mari exists" — no determiner -> GENERIC); a class
        # conclusion renders "a <noun>" -> INDEFINITE. The extractor treats GENERIC/INDEFINITE
        # identically, but the leaf must match what the compiler would have written.
        quantifier = TKQuantifier.GENERIC if is_individual else TKQuantifier.INDEFINITE

    content = TKZipContent(
        negated=negated,
        quantifier=quantifier,
        senses=senses,
        identities=identities,
        subject=_role_tensor(subj_sem),
        predicate=_role_tensor(pred_sem),
        # an absent role is a ZEROS tensor, exactly like compiler_zipGetVector(None) — never an
        # empty list (the 3237 min_length validator rejects an explicit []).
        direct=_role_tensor(obj_sem),
        indirects=[],
    )
    # the compiler wraps statement leaves in a LIST of items under the root (even a single
    # clause) — match the stored shape exactly so downstream consumers see one geometry.
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=[TKZipItem(content=content)]))


# --------------------------------------------------------------
# assemble a REPORTATIVE observation into a TKZip (the observation-fact seam, 2026-07-17): the
# second canonical native shape — «<individual> said <predicative>» («Salmon said false»). The
# compiled render of that sentence (probed 2026-07-17) is a TWO-leaf tree:
#   matrix leaf   op=AND   att=None                              senses={predicate: matrix_pred}
#   complement    op=THAT  att=(verb="say", klass="reportative") senses={predicate: complement_pred}
# with BOTH leaves carrying the speaker's identity (the compiler folds a subject-less predicative
# complement onto the matrix subject) and GENERIC quantifiers (bare individual subject). This
# assembler rebuilds exactly that — the uid arrives canonical from the caller (item.sourceId), so
# there is no name-resolution risk; the senses are first-class inputs (the observation vocabulary
# is a fixed cognitive act: "said" = state.v.01, "false" = false.a.01 — the same senses the taught
# «…if he says false» rule extracts, aligned by construction).
# NB the assembled zip is deliberately NOT `_zip_is_asserted` (the THAT leaf) — extract_facts owns
# the one narrow reading of this shape (matrix + predicative complements as subject properties).
# --------------------------------------------------------------
def assemble_reportative_zip(subject_uid: str, matrix_pred: str, complement_pred: str,
                             attitude_verb: str = "say") -> Optional[TKZip]:
    if not subject_uid or "@" not in subject_uid or not matrix_pred or not complement_pred:
        return None
    subj_sem = _semantic_block(subject_uid)
    if subj_sem is None:
        subj_sem = [0.0] * _SEMANTIC_DIMS  # honest zeros for a centroid-less individual (as above)
    matrix_sem = _semantic_block(matrix_pred)
    compl_sem = _semantic_block(complement_pred)
    if matrix_sem is None or compl_sem is None:
        logger.info("[zip_native] ungroundable reportative (matrix=%s complement=%s) — no assembly",
                    matrix_pred, complement_pred)
        return None

    def _leaf(pred_sense: str, pred_sem: list[float]) -> TKZipContent:
        return TKZipContent(
            negated=False,
            quantifier=TKQuantifier.GENERIC,   # bare individual subject, per the compiled render
            senses={"predicate": pred_sense},
            identities={"subject": subject_uid},
            subject=_role_tensor(subj_sem),
            predicate=_role_tensor(pred_sem),
            direct=_role_tensor(None),
            indirects=[],
        )

    matrix = TKZipItem(content=_leaf(matrix_pred, matrix_sem))
    complement = TKZipItem(
        op=TKOperator.THAT,
        attitude=TKLLAttitude(verb=attitude_verb, klass="reportative", confidence=0.5),
        content=_leaf(complement_pred, compl_sem),
    )
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=[matrix, complement]))

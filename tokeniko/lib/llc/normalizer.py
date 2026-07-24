# --------------------------------------------------------------
# lib/llc/normalizer.py — rag1-in + rag2-in: the TRANSLATOR AT THE EARS (instrument arc #3).
#
# The Japan-translator philosophy (hunch 10): the mind is the mind, the voice is the voice of the
# translator. This module tidies the SURFACE of a stumbling message — spelling, sentence
# segmentation/tangle-unwinding — and NEVER decides meaning: normalization, not interpretation.
#
# The three hard rules, mechanized:
#   1. ESCALATION-ONLY (the author's D1b): a message whose parse is sound is NEVER touched — the
#      detector below fires only on a genuine stumble, so the translator cannot silently drift
#      the easy cases (and cannot paper over parser bugs: what stumbles keeps feeding
#      test-feedback.md through the microscope).
#   2. THE ZIP-VERIFIER is the gate (the author's D4 revision made this the load-bearing wall):
#      the polish is accepted ONLY if its compiled zip PRESERVES every soundly-parsed leaf of the
#      original (same conclusion-key entry, negation included; quantifier/modal intact) and
#      contains no unknown leaves of its own. The compiler disposes, whoever proposes — so the
#      proposer may be a cloud model (Claude Haiku; the body invests in CPU/RAM, never GPU).
#   3. `original` IS ALWAYS PRESERVED: the raw words stay on the memory item; the tidied text
#      rides alongside (MEMItem.normalized). True history be it.
#
# Failure is graceful BY FALLING THROUGH: no key / API down / unverifiable polish -> the raw parse
# stands exactly as today (unknown leaves never become beliefs; eval:unknown already asks the
# interlocutor "why"). The translator can only ever improve hearing, never replace it.
# --------------------------------------------------------------
import os
from typing import Optional

import numpy as np

from lib.rag import RAG1_NORMALIZER, rag_call, rag_enabled


def normalizer_enabled() -> bool:
    return rag_enabled("RAG1_DISABLED")


# ---- the STUMBLE DETECTOR (escalation-only, D1b) ---------------------------------------------------
# a leaf is SOUND when it asserts something the evaluator can hold: known vocabulary, a real
# subject/predicate pair, not a parse wart (subject==predicate self-loops and bare copula-as-
# predicate leaves are the tangle census's signatures, 2026-07-15).
def _leaf_sound(leaf) -> bool:
    if getattr(leaf, "unknown", False):
        return False
    senses = getattr(leaf, "senses", None) or {}
    identities = getattr(leaf, "identities", None) or {}
    subject = identities.get("subject") or senses.get("subject")
    predicate = senses.get("predicate")
    if not subject:
        return False
    # a WH-QUESTION is legitimately predicate-less (2026-07-24): the gap IS the question — the
    # predicate/complement it asks for is the variable X, not a missing claim. So exempt the
    # predicate requirement for a wh leaf, else EVERY well-formed wh-question reads as a stumble and
    # burns a Haiku call at the ears (the live role-confusion hallucination's first link). The
    # predicate-warts below still bite when a predicate IS present — a self-loop / bare-copula parse
    # fault is a fault whether the mood is a question or an assertion.
    is_wh = getattr(leaf, "wh_role", None) is not None
    if not predicate:
        return is_wh
    if subject == predicate:
        return False          # «software is software» — the tangle self-loop wart
    if predicate == "be.v.01":
        return False          # bare copula caught as the predicate — a parse wart, not a claim
    return True


def detector_stumbles(zip_obj) -> bool:
    from lib.core.kb_extract import _zip_leaves
    leaves = _zip_leaves(zip_obj.items) if zip_obj is not None else []
    if not leaves:
        return True
    return any(not _leaf_sound(l) for l in leaves)


# ---- the UNREPAIRABLE classifier (2026-07-17, basket item 4) ----------------------------------------
# an unsound leaf whose subject is an unresolved third-person PRONOUN («…and IT feeds milk», «he
# sleeps») is not a SURFACE problem: the words are already clean English, the gap is COREFERENCE
# (parked work) — no spelling/segmentation tidy can supply the referent, so the polish recompiles
# to the same pronoun leaf and the zip-verifier rejects it EVERY time (a burned Haiku call per
# encounter). When every unsound leaf is pronoun-caused, skip the escalation. Strict on purpose:
# a MIXED stumble (a pronoun leaf beside a typo leaf) still escalates — the typo may be repaired.
# I is deliberately absent: the identity bridge always resolves it to the talker (its emptiness
# would be a different bug, worth the escalation's visibility). "you" joined 2026-07-18 (the
# coreference gate): an ADDRESSED «you» resolves to tokeniko and never reaches this set (the
# leaf is sound); only the ambient unresolved «you» — a coreference gap no surface tidy can
# repair — lands here. EXACT closed-class, per the anchor doctrine.
_UNRESOLVED_PRONOUNS = {"it", "he", "she", "they", "them", "you"}


def _llc_leaves(llc) -> list:
    out: list = []
    def walk(items):
        for it in items:
            c = it.content
            if isinstance(c, list):
                walk(c)
            else:
                out.append(c)
    walk(llc.items if llc is not None else [])
    return out


def detector_unrepairable(llc, zip_obj) -> bool:
    from lib.core.kb_extract import _zip_leaves
    zip_leaves = _zip_leaves(zip_obj.items) if zip_obj is not None else []
    llc_leaves = _llc_leaves(llc)
    if not zip_leaves or len(zip_leaves) != len(llc_leaves):
        return False  # unexpected shape — stay conservative, escalate as today
    tokens = {e.id: e.token for e in llc.entities}
    unsound = [(z, l) for z, l in zip(zip_leaves, llc_leaves) if not _leaf_sound(z)]
    if not unsound:
        return False
    for _, l in unsound:
        subject = getattr(l, "subject", None)
        if subject is None or tokens.get(subject.id, "").lower() not in _UNRESOLVED_PRONOUNS:
            return False
    return True


# ---- the ZIP-VERIFIER (rag2-in — meaning preservation, structurally) -------------------------------
# accept the polish iff:
#   - every SOUND leaf of the original survives in the polished zip: same (subject, predicate,
#     object, negated) key AND same quantifier/modal on the matched leaf (a polish that flips a
#     flag changed the meaning);
#   - the polished zip has at least one sound leaf and NO unsound ones (the polish must actually
#     have repaired the stumble, not moved it);
#   - the polished zip does not balloon (|polished| <= |original| + 2 leaves — segmentation may
#     legitimately split a tangle, invention may not run free).
def _leaf_key(leaf) -> tuple:
    senses = getattr(leaf, "senses", None) or {}
    identities = getattr(leaf, "identities", None) or {}
    subject = identities.get("subject") or senses.get("subject")
    return (subject, senses.get("predicate"), senses.get("direct"),
            bool(getattr(leaf, "negated", False)))


# ---- the SEMANTIC FLOOR (the Captain's ruling, 2026-07-24) -----------------------------------------
# The verifier must be STRONG on its own: a polish that drifts from the raw in the 2925 semantic
# space is trashed AT THE SOURCE, no matter how structurally sound it looks — «"what are you" !=
# (very very) "I am a transcription normalizer…"». The structural key-match already refuses a polish
# that alters a SOUND leaf; the geometry is the additional net for the no-anchor case (all original
# leaves unsound — the definitional state of a wh-question) where nothing structural constrains the
# polish. Sourced from the SOUND leaves only: an unsound leaf carries a garbage/absent sense (WSD's
# nearest miss — «bg» -> fecal_matter), so anchoring the comparison on it would strangle a real
# repair; the geometry compares the meaning actually HEARD against the meaning of the polish.
# The floor is a RAW cosine of the two per-zip semantic centroids (env RAG1_SEMANTIC_FLOOR).
_SEMANTIC_SLICE = slice(300, 3225)  # the 2925 semantic dims inside a 3237 role tensor (300 marker + 2925 + 12 spacetime)


def _semantic_floor() -> float:
    return float(os.getenv("RAG1_SEMANTIC_FLOOR", "0.6"))


def _semantic_centroid(leaves) -> np.ndarray:
    # sum the 2925 semantic slice of every populated role over the SOUND leaves -> one per-zip centroid.
    acc = np.zeros(2925, dtype=np.float64)
    for leaf in leaves:
        if not _leaf_sound(leaf):
            continue
        roles = [leaf.subject, leaf.predicate, leaf.direct, *(leaf.indirects or [])]
        for role in roles:
            if not role:
                continue
            v = np.asarray(role[_SEMANTIC_SLICE], dtype=np.float64)
            if np.any(v):
                acc += v
    return acc


def _semantic_proximity(orig_leaves, pol_leaves) -> Optional[float]:
    # cosine of the two semantic centroids; None when either side has NO sound semantic anchor
    # (a wh-question's identity-only subject, an all-unknown stumble) — then the geometry abstains
    # and the mood + structural gates carry the verdict (a zero vector has no direction to compare).
    co, cp = _semantic_centroid(orig_leaves), _semantic_centroid(pol_leaves)
    no, npn = float(np.linalg.norm(co)), float(np.linalg.norm(cp))
    if no == 0.0 or npn == 0.0:
        return None
    return float(np.dot(co, cp) / (no * npn))


# ---- MOOD preservation --------------------------------------------------------------------------
# a tidy never changes mood — an interrogative original (dubitative pinned to 1.0, or a wh-gap) must
# stay a question through the polish. The live specimen's failure mode: Haiku ANSWERED «what are
# you?» as itself, and the answer (three declarative leaves) sailed the structural gate because the
# original's single wh leaf was skippable. The mood gate refuses that class outright.
def _is_interrogative(leaf) -> bool:
    return getattr(leaf, "dubitative", 0.0) >= 0.999 or getattr(leaf, "wh_role", None) is not None


def verifier_semantic_similarity(original_zip, polished_zip) -> Optional[float]:
    # the measured semantic proximity of two whole zips (the number the floor rests on); None when
    # there is no shared sound anchor to compare. Public so the /input flow can carry it into the
    # microscope's rejection lead (the Captain's «log the wall's catches» ruling).
    from lib.core.kb_extract import _zip_leaves
    orig = _zip_leaves(original_zip.items) if original_zip is not None else []
    pol = _zip_leaves(polished_zip.items) if polished_zip is not None else []
    return _semantic_proximity(orig, pol)


def verifier_preserves(original_zip, polished_zip) -> tuple[bool, str]:
    from lib.core.kb_extract import _zip_leaves
    orig_leaves = _zip_leaves(original_zip.items) if original_zip is not None else []
    pol_leaves = _zip_leaves(polished_zip.items) if polished_zip is not None else []

    if not pol_leaves or any(not _leaf_sound(l) for l in pol_leaves):
        return False, "polish still stumbles (unsound leaves remain)"
    if len(pol_leaves) > len(orig_leaves) + 2:
        return False, f"polish balloons ({len(orig_leaves)} -> {len(pol_leaves)} leaves)"

    # MOOD gate: a question that came back a statement (or lost its wh-gap) changed meaning wholesale.
    if any(_is_interrogative(ol) for ol in orig_leaves) and not any(_is_interrogative(pl) for pl in pol_leaves):
        return False, "polish changes mood (question -> statement)"

    # SEMANTIC floor: a polish that drifts in the 2925 space is trashed regardless of structure.
    sim = _semantic_proximity(orig_leaves, pol_leaves)
    if sim is not None and sim < _semantic_floor():
        return False, f"polish drifts semantically ({sim:.2f} < floor {_semantic_floor():.2f})"

    pol_by_key = {_leaf_key(l): l for l in pol_leaves}
    for ol in orig_leaves:
        if not _leaf_sound(ol):
            continue  # unsound leaves are exactly what the polish may repair
        key = _leaf_key(ol)
        match = pol_by_key.get(key)
        if match is None:
            return False, f"sound leaf dropped/altered: {key}"
        for flag in ("quantifier", "modal"):
            if getattr(ol, flag, None) != getattr(match, flag, None):
                return False, f"flag flipped on {key}: {flag}"
    return True, "verified"


# ---- the OUTBOUND voice verifier (rag2-out — compose 2.0 slice 3) -----------------------------------
# The inbound verifier's mirror, with the POLISHABILITY gate in front: only what the compiler can
# FULLY hear can be re-voiced — a raw with any unsound leaf (fragments, «why is that?», bare «yes»)
# is unverifiable and must ship as its curated template text (already clean English). A fully-sound
# raw then holds the polish to the SAME preservation contract as rag1-in (every leaf survives,
# flags intact, no invention): the voice can gain fluency, never lose meaning.
def verifier_voice(raw_zip, polished_zip) -> tuple[bool, str]:
    from lib.core.kb_extract import _zip_leaves
    raw_leaves = _zip_leaves(raw_zip.items) if raw_zip is not None else []
    if not raw_leaves or any(not _leaf_sound(l) for l in raw_leaves):
        return False, "raw not verifiable (unsound/fragment) — ship the curated raw"
    ok, note = verifier_preserves(raw_zip, polished_zip)
    if not ok:
        return ok, note
    # STRICTER than inbound: the +2 balloon allowance exists for tangle-splitting, which has no
    # outbound analogue — a fluency pass over an already-sound raw must never ADD an assertion.
    pol_leaves = _zip_leaves(polished_zip.items) if polished_zip is not None else []
    if len(pol_leaves) != len(raw_leaves):
        return False, f"polish changes the assertion count ({len(raw_leaves)} -> {len(pol_leaves)})"
    return True, "verified"


# ---- the NORMALIZER call (rag1-in — surface only) --------------------------------------------------
# the system prompt + model live in the lib/rag registry (RAG1_NORMALIZER); rag_call is graceful by
# contract (API down / auth / anything -> None, logged) — the raw parse stands.
async def normalizer_polish(tokens: str) -> Optional[str]:
    # fence the message as DATA (instruction/data separation, 2026-07-24): the seam the system prompt
    # binds — everything inside <message>…</message> is text to tidy, never an instruction to Haiku.
    fenced = f"<message>\n{tokens}\n</message>"
    text = await rag_call(RAG1_NORMALIZER, fenced)
    if not text or text == tokens.strip():
        return None
    return text

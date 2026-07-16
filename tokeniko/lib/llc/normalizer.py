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
from typing import Optional

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
    if not subject or not predicate:
        return False
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


def verifier_preserves(original_zip, polished_zip) -> tuple[bool, str]:
    from lib.core.kb_extract import _zip_leaves
    orig_leaves = _zip_leaves(original_zip.items) if original_zip is not None else []
    pol_leaves = _zip_leaves(polished_zip.items) if polished_zip is not None else []

    if not pol_leaves or any(not _leaf_sound(l) for l in pol_leaves):
        return False, "polish still stumbles (unsound leaves remain)"
    if len(pol_leaves) > len(orig_leaves) + 2:
        return False, f"polish balloons ({len(orig_leaves)} -> {len(pol_leaves)} leaves)"

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


# ---- the NORMALIZER call (rag1-in — surface only) --------------------------------------------------
# the system prompt + model live in the lib/rag registry (RAG1_NORMALIZER); rag_call is graceful by
# contract (API down / auth / anything -> None, logged) — the raw parse stands.
async def normalizer_polish(tokens: str) -> Optional[str]:
    text = await rag_call(RAG1_NORMALIZER, tokens)
    if not text or text == tokens.strip():
        return None
    return text

# ------------------------------------------------------------------------------------------------
# ROLE-KEY — the ONE role reader, the generalized cure for the identity-blindness family
# (2026-07-19 audit, doc/ref/notes.md § "The identity-blindness family").
#
# A compiled clause leaf carries two DISJOINT symbolic maps over the same grammatical roles:
#   senses     — a CLASS keyed by its WSD sense ("cat.n.01"), in TKZipContent.senses
#   identities — an INDIVIDUAL keyed by its identity uid ("mari@internal:tokeniko"), in .identities
# An individual compiles SENSE-LESS by design (its 2925 vector is an honest type centroid, never a
# referent key — the identity-bridge), so per role the two maps never both carry a value: the pair
# cannot collide, and the uid/sense string formats are disjoint anyway.
#
# Any site that read only `senses.get(role)` was blind to half the world — an individual subject
# read None and the lookup/match/dedup silently missed it (an honest-looking IDK, never an error).
# role_key is that read done ONCE, everywhere: IDENTITY-FIRST, matching conclusion_key's dedup
# discipline ("I exist" and "tokeniko exists" share a key) — the uid distinguishes Mari from Bob
# where their shared type centroid would collapse them. None when the role has neither (an unbound
# ambient "you" stays honestly unkeyable — the coreference gate's caution preserved, not bypassed).
# ------------------------------------------------------------------------------------------------
from typing import Optional


def role_key(leaf, role: str) -> Optional[str]:
    identities = getattr(leaf, "identities", None) or {}
    senses = getattr(leaf, "senses", None) or {}
    return identities.get(role) or senses.get(role)

# --------------------------------------------------------------
# lib/core/trust.py — the TRUST LEDGER (senses D, P1: the substrate).
#
# Trust is an OPINION FORMED FROM EPISODES, never a stored mood: the permanent trail is the
# trust_episodes collection (the source of truth — biography, post-ceremony discipline), and the
# stakeholder's `trust` scalar is the FOLD of that trail — recomputable at any time, the same
# context-is-derivable principle as the open-why derivation and brain_state.
#
# The episode taxonomy + weights (the author's table, 2026-07-11 D brainstorm):
#   agreement           +0.02   redundant eval:true (KB-derivable) — silence-is-consent's ledger echo
#   kicker              +0.10   novel, logic-clean, premises KB-matched (v1: the closed why-loop —
#                               a novel claim's «because» grounding TRUE) — the twin-soul signal
#   disagreement        −0.15 × the refuted BELIEF's own trust (contradicting a 0.3 hunch ≈ noise;
#                               contradicting a 1.0 axiom ≈ full weight)
#   logic-violation     −0.15   eval:inconsistent — logic is sacred
#   self-inconsistency  −0.20   eval:conflict across the speaker's own claims — the honest-liar
#                               proxy (unreliability matters regardless of intent)
# HYSTERESIS is the asymmetry of the numbers (rises slow, falls fast); the fold clamps to [0,1]
# after every step so recovery from the floor takes real history, not one lucky episode.
#
# IMPRINTING (the author, by constitution): an imprinted stakeholder folds to 1.0 regardless of
# episodes — episodes are still RECORDED (the trail stays honest where the scalar is pinned).
# IDENTITY UNIFICATION (fork 3 option A): a channel body carries canonical_uid -> its soul's
# stakeholder; all ledger reads/writes resolve through it (ONE ledger per soul). One hop only.
# --------------------------------------------------------------
import logging
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId

from lib.core.memory import MEMTrustEpisode, TrustEpisodeKind
from lib.core.models import TKMemoryStakeholdersDoc, TKTrustEpisodeDoc

logger = logging.getLogger("tokeniko-brain")

_NEUTRAL = 0.5

# base deltas per episode kind. disagreement's base is SCALED by the refuted belief's trust at
# record time (the episode stores the final signed number — the fold is a pure replay).
_EPISODE_WEIGHTS: dict[TrustEpisodeKind, float] = {
    TrustEpisodeKind.AGREEMENT: +0.02,
    TrustEpisodeKind.KICKER: +0.10,
    TrustEpisodeKind.DISAGREEMENT: -0.15,   # × belief_trust
    TrustEpisodeKind.LOGIC_VIOLATION: -0.15,
    TrustEpisodeKind.SELF_INCONSISTENCY: -0.20,
}


# resolve a stakeholder reference to its CANONICAL soul (one hop): the doc itself if no
# canonical_uid, else the canonical doc (falling back to the body if the canonical is missing —
# never None for a known ref). `ref` may be a stakeholder UID ("john@discord:9") OR a stakeholder
# DOC id (memory items carry the speaker's Mongo id in sourceId — both currencies circulate).
# Returns None only for an unknown ref.
def resolve_canonical(ref: str) -> Optional[TKMemoryStakeholdersDoc]:
    doc = TKMemoryStakeholdersDoc.find_one({"uid": ref}).run()
    if doc is None:
        try:
            doc = TKMemoryStakeholdersDoc.get(ObjectId(ref)).run()  # Bunnet: .run() executes
        except (InvalidId, TypeError):
            doc = None
    if doc is None:
        return None
    if doc.canonical_uid:
        canonical = TKMemoryStakeholdersDoc.find_one({"uid": doc.canonical_uid}).run()
        if canonical is not None:
            return canonical
        logger.warning("[trust] canonical_uid %r of %r not found — using the body", doc.canonical_uid, uid)
    return doc


# the FOLD: replay a stakeholder's episode trail into the scalar. Pure over its inputs — neutral
# start, per-step clamp to [0,1] (the floor/ceiling absorb, so recovery takes real history).
# `imprint` pins to 1.0 (constitution beats episodes).
def fold_trust(deltas: list[float], imprint: bool = False) -> float:
    if imprint:
        return 1.0
    trust = _NEUTRAL
    for d in deltas:
        trust = max(0.0, min(1.0, trust + d))
    return trust


# compute an episode's signed delta from its kind (+ the refuted belief's trust for disagreement).
def episode_delta(kind: TrustEpisodeKind, belief_trust: Optional[float] = None) -> float:
    base = _EPISODE_WEIGHTS[kind]
    if kind == TrustEpisodeKind.DISAGREEMENT:
        return base * (belief_trust if belief_trust is not None else _NEUTRAL)
    return base


# RECORD an episode against a stakeholder (by any of its uids — resolved to the canonical soul)
# and refold the cached scalar. Returns the updated (canonical) stakeholder doc, or None for an
# unknown uid (never invents a stakeholder — perception owns creation). The trail write and the
# cache write are two operations; the cache is always recomputable, so a crash between them heals
# on the next record/refold.
def record_episode(
    stakeholder_uid: str,
    kind: TrustEpisodeKind,
    source_id: Optional[str] = None,
    belief_trust: Optional[float] = None,
    note: Optional[str] = None,
) -> Optional[TKMemoryStakeholdersDoc]:
    soul = resolve_canonical(stakeholder_uid)
    if soul is None:
        logger.warning("[trust] episode for unknown stakeholder %r dropped", stakeholder_uid)
        return None
    if soul.isMe:
        return soul  # tokeniko keeps no ledger on himself (self-trust is not an opinion)

    delta = episode_delta(kind, belief_trust=belief_trust)
    TKTrustEpisodeDoc(stakeholder_uid=soul.uid, kind=kind, delta=delta,
                      source_id=source_id, note=note).insert()
    soul.trust = refold(soul)
    soul.save()
    logger.info("[trust] %s %+0.3f -> %s trust=%.3f (%s)",
                kind.value, delta, soul.uid, soul.trust, note or source_id or "-")
    return soul


# recompute a stakeholder's scalar from its FULL trail (the derivability guarantee made runnable).
def refold(soul: TKMemoryStakeholdersDoc) -> float:
    episodes = (
        TKTrustEpisodeDoc.find({"stakeholder_uid": soul.uid}).sort("+timestamp").to_list()
    )
    return fold_trust([e.delta for e in episodes], imprint=soul.imprint)


# the trust READ every consumer uses (the teaching gate, later the tkzip lane): resolve the soul,
# return its folded scalar; unknown uid -> neutral (a stranger, not an error).
def trust_of(stakeholder_uid: str) -> float:
    soul = resolve_canonical(stakeholder_uid)
    if soul is None:
        return _NEUTRAL
    return 1.0 if soul.imprint else soul.trust

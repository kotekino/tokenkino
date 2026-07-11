"""The trust ledger substrate (senses D P1) — fold, weights, imprint, unification, round-trip.

Pure layers DB-free (fold/delta); the record/refold round-trip runs on the sandbox memory DB
(the `_io` session fixture), cleaning up its own stakeholders + episodes.
"""
import pytest

from lib.core.memory import TrustEpisodeKind
from lib.core.trust import episode_delta, fold_trust


# ---- the fold (pure) ---------------------------------------------------------------------------

def test_fold_starts_neutral_and_clamps():
    assert fold_trust([]) == 0.5
    assert fold_trust([+1.0]) == 1.0            # ceiling
    assert fold_trust([-1.0]) == 0.0            # floor
    # per-step clamp: the floor absorbs — recovery takes real history, not one lucky episode
    assert fold_trust([-1.0, +0.10]) == pytest.approx(0.10)


def test_fold_imprint_pins_regardless_of_episodes():
    assert fold_trust([-0.2, -0.2, -0.2], imprint=True) == 1.0


def test_hysteresis_rises_slow_falls_fast():
    up = episode_delta(TrustEpisodeKind.AGREEMENT)
    down = episode_delta(TrustEpisodeKind.LOGIC_VIOLATION)
    assert up > 0 > down
    assert abs(down) > abs(up)                   # the asymmetry IS the hysteresis
    # a kicker outweighs several agreements; a self-inconsistency outweighs a kicker
    assert episode_delta(TrustEpisodeKind.KICKER) > 3 * up
    assert abs(episode_delta(TrustEpisodeKind.SELF_INCONSISTENCY)) > episode_delta(TrustEpisodeKind.KICKER)


def test_disagreement_scales_by_the_beliefs_trust():
    full = episode_delta(TrustEpisodeKind.DISAGREEMENT, belief_trust=1.0)
    hunch = episode_delta(TrustEpisodeKind.DISAGREEMENT, belief_trust=0.3)
    default = episode_delta(TrustEpisodeKind.DISAGREEMENT)
    assert full == pytest.approx(-0.15)
    assert hunch == pytest.approx(-0.045)        # contradicting a 0.3 hunch ≈ noise
    assert default == pytest.approx(-0.075)      # unknown belief -> neutral scale


# ---- record / refold / unification (sandbox DB) --------------------------------------------------

@pytest.fixture()
def clean_trust(_io):
    from lib.core.models import TKMemoryStakeholdersDoc, TKTrustEpisodeDoc
    uids = ["t-john@discord:1", "t-soul", "t-body@discord:2"]
    def _wipe():
        for u in uids:
            TKMemoryStakeholdersDoc.find({"uid": u}).delete().run()
        TKTrustEpisodeDoc.find({"stakeholder_uid": {"$in": uids}}).delete().run()
    _wipe()
    yield
    _wipe()


def _mk(uid, **over):
    from lib.core.models import TKMemoryStakeholdersDoc
    fields = dict(uid=uid, name=uid.split("@")[0], isMe=False)
    fields.update(over)
    return TKMemoryStakeholdersDoc(**fields).save()


def test_record_episode_round_trip(_io, clean_trust):
    from lib.core.trust import record_episode, trust_of
    _mk("t-john@discord:1")
    soul = record_episode("t-john@discord:1", TrustEpisodeKind.LOGIC_VIOLATION, source_id="m1")
    assert soul.trust == pytest.approx(0.35)               # 0.5 - 0.15
    record_episode("t-john@discord:1", TrustEpisodeKind.KICKER, source_id="m2")
    assert trust_of("t-john@discord:1") == pytest.approx(0.45)


def test_canonical_unification_one_ledger_per_soul(_io, clean_trust):
    from lib.core.models import TKTrustEpisodeDoc
    from lib.core.trust import record_episode, trust_of
    _mk("t-soul")
    _mk("t-body@discord:2", canonical_uid="t-soul")
    record_episode("t-body@discord:2", TrustEpisodeKind.KICKER, source_id="m3")
    # the episode landed on the SOUL's trail; both uids read the same folded scalar
    assert TKTrustEpisodeDoc.find({"stakeholder_uid": "t-soul"}).to_list()
    assert not TKTrustEpisodeDoc.find({"stakeholder_uid": "t-body@discord:2"}).to_list()
    assert trust_of("t-body@discord:2") == trust_of("t-soul") == pytest.approx(0.6)


def test_imprint_pins_the_read_but_keeps_the_trail(_io, clean_trust):
    from lib.core.models import TKTrustEpisodeDoc
    from lib.core.trust import record_episode, trust_of
    _mk("t-soul", imprint=True, trust=1.0)
    record_episode("t-soul", TrustEpisodeKind.SELF_INCONSISTENCY, source_id="m4")
    assert trust_of("t-soul") == 1.0                        # constitution beats episodes
    assert TKTrustEpisodeDoc.find({"stakeholder_uid": "t-soul"}).to_list()  # the trail stays honest


def test_unknown_stakeholder_is_a_neutral_stranger(_io, clean_trust):
    from lib.core.trust import record_episode, trust_of
    assert trust_of("nobody@nowhere:0") == 0.5
    assert record_episode("nobody@nowhere:0", TrustEpisodeKind.AGREEMENT) is None

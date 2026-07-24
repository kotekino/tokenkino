"""Pronoun momentum (B, 2026-07-24) — «you» resolves where directedness points.

Three seams of lead B:
  1. the momentum GRADE — an ambient message inside an OPEN exchange lifts 0.6 -> 0.85, DERIVED
     from the memory timeseries (senses/inbound._in_open_exchange), never stored state;
  2. the ADDRESSED BAR at /input — 0.85 clears, 0.6 does not (api.main._is_addressed);
  3. the binding SPECIMEN — «so, what are you?» addressed compiles with «you» bound to tokeniko and
     wh_role=predicate (the 2026-07-24 live cure, asserted at the zip).

The grade tests seed the sandbox timeseries directly, with UNIQUE namespaced author ids / channel
ids per test so they never collide (the 600s window is shared across the session; test_senses_c's
renzo/333 ambient assertions must stay 0.6). The wh-solve ANSWER from the specimen zip is already
covered in test_identity_blindness.py — not duplicated here.
"""
import json
from datetime import datetime, timedelta, timezone

from lib.discord.models import DiscordMessage
from senses.inbound import grade_directedness


# ---- seed helpers (sandbox timeseries) -----------------------------------------------------------

def _msg(discord_id, channel_id, author_name, **over):
    fields = dict(message_id="m1", author_id=discord_id, author_name=author_name,
                  channel_id=channel_id, guild_id="g1", content="what are you?",
                  is_dm=False, is_self=False)
    fields.update(over)
    return DiscordMessage(**fields)


def _make_author(name, discord_id):
    # get-or-create the author stakeholder under the uid inbound derives ("name@discord:id"), and
    # return its ObjectId string (what memory rows carry in sourceId/targetId).
    from lib.core.io import get_stakeholder
    from lib.core.memory import MEMChannels
    uid = f"{name}@discord:{discord_id}"
    return str(get_stakeholder(uid, channel=MEMChannels.DISCORD, display_name=name).id)


def _seed(source_id, channel_id, directedness, target_id=None, age_s=0):
    from lib.core.memory import MEMChannels
    from lib.core.models import TKMemoryItemDoc
    TKMemoryItemDoc(
        original="seed", zip=None, sourceId=source_id, targetId=target_id,
        channel=MEMChannels.DISCORD, directedness=directedness,
        metadata=json.dumps({"channel_id": channel_id, "message_id": "s1", "reply_to": None}),
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=age_s),
    ).insert()


# ---- the momentum grade ---------------------------------------------------------------------------

def test_momentum_a_author_just_addressed_tokeniko(_io):
    # (a) this author addressed tokeniko (d>=0.9) in this channel within the window -> lift to 0.85
    aid = _make_author("momoa", "AA")
    _seed(aid, "chan-A", directedness=0.9)
    assert grade_directedness(_msg("AA", "chan-A", "momoa")) == 0.85


def test_momentum_b_tokeniko_just_spoke_to_him(_io):
    # (b) tokeniko's outbound targeted at this author within the window -> the room is still open
    from lib.core.io import get_tokeniko
    aid = _make_author("momob", "BB")
    me = str(get_tokeniko().id)
    _seed(me, "chan-B", directedness=1.0, target_id=aid)     # tokeniko spoke TO him
    assert grade_directedness(_msg("BB", "chan-B", "momob")) == 0.85


def test_no_open_exchange_stays_ambient(_io):
    # the author exists but has no directed turn on record -> plain ambient
    _make_author("momon", "NN")
    assert grade_directedness(_msg("NN", "chan-N", "momon")) == 0.6


def test_ambient_only_prior_turn_does_not_open(_io):
    # a prior AMBIENT row (d=0.6 < 0.9) is not "addressing tokeniko" -> no momentum
    aid = _make_author("momoo", "OO")
    _seed(aid, "chan-O", directedness=0.6)
    assert grade_directedness(_msg("OO", "chan-O", "momoo")) == 0.6


def test_rows_outside_the_window_stay_ambient(_io):
    # the same (a)-shape, but older than MOMENTUM_WINDOW_S -> the conversation has cooled
    aid = _make_author("momow", "WW")
    _seed(aid, "chan-W", directedness=0.9, age_s=700)        # default window 600s
    assert grade_directedness(_msg("WW", "chan-W", "momow")) == 0.6


def test_open_exchange_in_a_different_channel_stays_ambient(_io):
    # momentum is per-channel: an open exchange elsewhere does not carry into this room
    aid = _make_author("momod", "DD")
    _seed(aid, "chan-D-other", directedness=0.9)
    assert grade_directedness(_msg("DD", "chan-D", "momod")) == 0.6


def test_reply_into_others_thread_beats_momentum(_io):
    # an explicit signal (a reply into someone ELSE's thread) outranks momentum -> stays 0.15
    aid = _make_author("momor", "RR")
    _seed(aid, "chan-R", directedness=0.9)                   # momentum present...
    assert grade_directedness(_msg("RR", "chan-R", "momor", reply_to="999")) == 0.15


def test_dm_stays_fully_directed_over_momentum(_io):
    # a DM is unambiguous regardless of any channel momentum
    aid = _make_author("momom", "MM")
    _seed(aid, "chan-M", directedness=0.9)
    assert grade_directedness(_msg("MM", "chan-M", "momom", is_dm=True, guild_id=None)) == 1.0


# ---- the addressed bar ----------------------------------------------------------------------------

def test_addressed_bar_maps_momentum_and_ambient(_io):
    # the bar sits deliberately BELOW momentum (0.85) and ABOVE ambient (0.6)
    from api.main import _is_addressed
    assert _is_addressed(0.85) is True       # momentum clears -> «you» binds
    assert _is_addressed(0.6) is False        # cold ambient does not
    assert _is_addressed(0.9) is True         # explicit addressing clears
    assert _is_addressed(1.0) is True         # a DM clears
    assert _is_addressed(0.15) is False       # someone else's thread does not


# ---- the binding specimen (the 2026-07-24 live cure, at the zip) ----------------------------------

def test_binding_specimen_you_binds_when_addressed(compile_zip, leaves):
    # «so, what are you?» mid-dialogue: now graded 0.85 -> addressed at /input -> «you» binds to
    # tokeniko and the wh gap is the predicate. compile_zip parses addressed=True (the parser default,
    # like every DM/API/seed path). Asserted at the zip; the wh-solve ANSWER is test_identity_blindness.
    from lib.core.tk import TKWhRole
    lvs = leaves(compile_zip("so, what are you?"))
    wh = next(l for l in lvs if getattr(l, "wh_role", None) is not None)
    assert wh.wh_role == TKWhRole.PREDICATE
    assert (wh.identities or {}).get("subject") == "tokeniko"

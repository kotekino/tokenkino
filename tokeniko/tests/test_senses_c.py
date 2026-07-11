"""Senses C — channel listening + the directedness grading, socket-free.

The grading ladder (DM 1.0 · addressed 0.9 · ambient 0.6 "the polite guest" · someone else's
thread 0.15), the handler now perceiving guild-channel messages, and the ONE acting site:
Priorities' effective urge = rule urge x source directedness (behavior.effective_urge) — the
emergent-discretion matrix against the 0.5 keep threshold. No API, no Discord, no Mongo.
"""
import asyncio
from types import SimpleNamespace

import senses.inbound as inbound
from senses.inbound import grade_directedness, handle_discord_message, input_params
from brain.behavior import effective_urge
from brain.main import URGE_THRESHOLD
from lib.discord.models import DiscordMessage


def _msg(content="a cat is an animal", **over):
    fields = dict(message_id="111", author_id="222", author_name="renzo",
                  channel_id="333", guild_id="9", content=content,
                  is_dm=False, is_self=False)
    fields.update(over)
    return DiscordMessage(**fields)


# ---- the grading ladder ----------------------------------------------------------------------------

def test_grade_dm_is_fully_directed():
    assert grade_directedness(_msg(guild_id=None, is_dm=True)) == 1.0


def test_grade_mention_and_reply_to_him_are_addressed():
    assert grade_directedness(_msg(mentions_me=True)) == 0.9
    assert grade_directedness(_msg(reply_to_me=True, reply_to="777")) == 0.9
    # an @-mention inside someone else's thread is still ADDRESSED (the mention outranks the thread)
    assert grade_directedness(_msg(mentions_me=True, reply_to="777")) == 0.9


def test_grade_ambient_is_the_polite_guest():
    assert grade_directedness(_msg()) == 0.6


def test_grade_someone_elses_thread_is_barely_his_business():
    assert grade_directedness(_msg(reply_to="777")) == 0.15


# ---- the handler perceives channels (the P1 not_dm gate is gone) ------------------------------------

def test_handler_ingests_channel_message_with_graded_directedness(monkeypatch):
    called = []
    monkeypatch.setattr(inbound, "_call_input", lambda p: called.append(p) or {"status": "complete"})
    assert asyncio.run(handle_discord_message(_msg())) == "ingested"
    assert called[0]["directedness"] == 0.6


def test_channel_params_carry_the_grade_not_a_constant():
    assert input_params(_msg(mentions_me=True))["directedness"] == 0.9
    assert input_params(_msg(reply_to="777"))["directedness"] == 0.15


# ---- the ONE acting site: Priorities' effective urge -------------------------------------------------

def _idea(urge):
    return SimpleNamespace(urge=urge)


def _src(directedness):
    return SimpleNamespace(directedness=directedness)


def test_effective_urge_multiplies():
    assert effective_urge(_idea(0.9), _src(0.6)) == 0.9 * 0.6


def test_effective_urge_defaults_to_fully_directed():
    # no source (internal/self spawns) or a source without the field -> behave exactly as before
    assert effective_urge(_idea(0.7), None) == 0.7
    assert effective_urge(_idea(0.7), SimpleNamespace()) == 0.7


# ---- the mention decoder (adapter wire-encoding normalization) --------------------------------------

def test_decode_mentions_to_usernames():
    from lib.discord.client import _decode_mentions
    tokeniko = SimpleNamespace(id=1518880846826831922, name="tokeniko")
    # the live specimen that broke the parser (2026-07-11): a raw <@id> token in the text
    assert _decode_mentions("I agree with <@1518880846826831922>", [tokeniko]) == "I agree with tokeniko"
    assert _decode_mentions("<@!1518880846826831922> are you thinking?", [tokeniko]) == "tokeniko are you thinking?"


def test_decode_mentions_drops_unresolved_and_keeps_plain_text():
    from lib.discord.client import _decode_mentions
    assert _decode_mentions("I agree with <@999> here", []) == "I agree with here"
    assert _decode_mentions("no mentions at all", None) == "no mentions at all"


def test_the_polite_guest_matrix():
    # the emergent discretion (seeded urges x the ladder vs the keep threshold): he answers a question
    # asked to the room, but won't flag contradictions at, or interrogate, people not talking to him.
    ambient, addressed = 0.6, 0.9
    assert effective_urge(_idea(0.9), _src(ambient)) >= URGE_THRESHOLD      # answer: speaks
    assert effective_urge(_idea(0.7), _src(ambient)) < URGE_THRESHOLD       # speakup(inconsistent): quiet
    assert effective_urge(_idea(0.6), _src(ambient)) < URGE_THRESHOLD       # why: quiet
    assert effective_urge(_idea(0.6), _src(addressed)) >= URGE_THRESHOLD    # why, addressed: speaks
    assert effective_urge(_idea(0.9), _src(0.15)) < URGE_THRESHOLD          # others' thread: always quiet

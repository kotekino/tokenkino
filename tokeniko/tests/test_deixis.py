"""Deixis normalization — perspective-resolve the surface `original` at materialization.

A theorem materialized from another soul's speech must not hold the speaker's surface string
verbatim: speaker-relative pronouns flip meaning when tokeniko re-utters them («I am your
creator» taught by kotekino must be HELD as «kotekino is my creator»). normalize_deixis is the
pure, conservative rewriter (closed-class copular/aux table; anything it can't confidently fix
returns None → remembered-not-believed); brain/thinking wires it into BOTH from-speech
materialization sites (materialize_taught + materialize_theorem). Sandbox memory DB.
"""
import pytest

from lib.core.deixis import normalize_deixis
from lib.core.memory import LifeEventKind, MEMChannels, TokenikoAction
from lib.core.tkzip import TKZip, TKZipItem, TKZipContent


# ---- the pure function (no DB) ------------------------------------------------------------------

def test_speaker_subject_bigram_and_possessive_flip():
    assert normalize_deixis("I am your creator", "kotekino") == "kotekino is my creator"


def test_tokeniko_subject_bigram():
    assert normalize_deixis("you are kind", "kotekino") == "I am kind"


def test_speaker_possessive_single():
    assert normalize_deixis("my cat is black", "kotekino") == "kotekino's cat is black"


def test_no_deictics_fast_path_unchanged():
    assert normalize_deixis("no mammal is a reptile", "kotekino") == "no mammal is a reptile"


def test_bare_past_verb_and_bare_you_fail():
    # "I gave" — present-tense agreement unknowable; bare object "you" — role unknowable
    assert normalize_deixis("I gave you my word", "kotekino") is None


def test_bare_you_with_lexical_verb_fails():
    assert normalize_deixis("you know the truth", "kotekino") is None


def test_one_surviving_deictic_poisons_the_whole_sentence():
    # "I will" IS handleable — but the trailing bare "you" survives, so the valve fires anyway
    assert normalize_deixis("I will always protect you", "kotekino") is None


def test_no_speaker_name_edge_rules():
    assert normalize_deixis("I am tall", None) is None          # deictics, no perspective to fix
    assert normalize_deixis("a cat is a mammal", None) == "a cat is a mammal"


def test_case_insensitive_and_my_is_the_speakers():
    # "my" in the TEACHER's mouth is the SPEAKER's possession → {name}'s, never tokeniko's
    assert normalize_deixis("You are my friend", "kotekino") == "I am kotekino's friend"


# ---- integration: both from-speech materialization sites (sandbox DB) ----------------------------

_TEACHER = "deixis-hellen@discord:13"
_TEACHER_NAME = "deixis-hellen"

# every original a test below can store as a theorem (the wipe list)
_ORIGINALS = [f"{_TEACHER_NAME} is my creator", "I am kind"]


def _zip():
    return TKZip(map=[0.0] * 8, items=TKZipItem(content=TKZipContent(
        subject=None, predicate=None, direct=None)))


def _mk_teacher(_io, trust=0.95):
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc(uid=_TEACHER, name=_TEACHER_NAME, isMe=False,
                                   channel=MEMChannels.DISCORD, trust=trust).save()


def _mk_item(_io, original, source_doc_id, directedness=0.9):
    from lib.core.models import TKMemoryItemDoc
    item = TKMemoryItemDoc(original=original, sourceId=source_doc_id,
                           channel=MEMChannels.DISCORD, directedness=directedness, zip=_zip())
    item.insert()
    return item


@pytest.fixture()
def clean_deixis(_io):
    from lib.core.models import (
        TKBehaviorRuleDoc, TKIdeaDoc, TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKTheoremDoc,
    )
    def _wipe():
        # Bunnet gotcha: .find().delete() is a silent no-op without .run(); the memory timeseries
        # additionally needs the raw pymongo delete_many.
        TKMemoryItemDoc.get_motor_collection().delete_many({})
        TKMemoryStakeholdersDoc.find({"uid": _TEACHER}).delete().run()
        TKTheoremDoc.find({"original": {"$in": _ORIGINALS}}).delete().run()
        TKIdeaDoc.find({"trigger": LifeEventKind.THEOREM.value}).delete().run()
        TKBehaviorRuleDoc.find({"trigger": LifeEventKind.THEOREM.value}).delete().run()
    _wipe()
    # a life:theorem personality row so the spawn is observable (mirrors test_life_p1's seeding)
    TKBehaviorRuleDoc(trigger=LifeEventKind.THEOREM.value,
                      action=TokenikoAction.POST.value, urge=0.65).insert()
    yield
    _wipe()


def test_taught_theorem_stores_the_normalized_original(_io, clean_deixis):
    from brain.thinking import materialize_taught
    from lib.core.models import TKIdeaDoc, TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "I am your creator", str(teacher.id))    # channel talk (0.9) — postable
    assert materialize_taught(item) is True
    thm = TKTheoremDoc.find_one({"original": f"{_TEACHER_NAME} is my creator"}).run()
    assert thm is not None and thm.archived is False
    # the raw speaker-perspective string is never a held belief
    assert TKTheoremDoc.find_one({"original": "I am your creator"}).run() is None
    # the life:theorem spawn carries the NORMALIZED original too (the NL render source)
    ideas = TKIdeaDoc.find({"trigger": LifeEventKind.THEOREM.value}).to_list()
    assert len(ideas) == 1
    assert ideas[0].material["original"] == f"{_TEACHER_NAME} is my creator"


def test_unnormalizable_lesson_is_remembered_not_believed(_io, clean_deixis):
    from brain.thinking import materialize_taught
    from lib.core.models import TKMemoryItemDoc, TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "I gave you my word", str(teacher.id))
    assert materialize_taught(item) is False
    assert TKTheoremDoc.find_one({"original": "I gave you my word"}).run() is None
    # the episodic record survives regardless — remembered, not believed
    assert TKMemoryItemDoc.find_one({"original": "I gave you my word"}).run() is not None


def test_taught_dedups_on_the_normalized_key(_io, clean_deixis):
    from brain.thinking import materialize_taught
    teacher = _mk_teacher(_io, trust=0.95)
    item = _mk_item(_io, "I am your creator", str(teacher.id))
    assert materialize_taught(item) is True
    again = _mk_item(_io, "I am your creator", str(teacher.id))
    assert materialize_taught(again) is False                     # dedup by the NORMALIZED original


def test_materialize_theorem_normalizes_the_speakers_perspective(_io, clean_deixis):
    from brain.thinking import materialize_theorem
    from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
    from lib.core.models import TKTheoremDoc
    teacher = _mk_teacher(_io, trust=0.95)
    # a DM item (directedness 1.0) — learned all the same, just not postable (no spawn machinery)
    item = _mk_item(_io, "you are kind", str(teacher.id), directedness=1.0)
    # a crafted forward-chained truth (chain derivation + premises), mimicking a derived eval:true
    result = EvaluatorResult(
        truth=1.0, status=EvaluatorStatus.RESOLVED,
        derivation=["chain: deixis-test premise -> deixis-test conclusion"],
        premises=["deixis-test-premise"],
    )
    assert materialize_theorem(result, item) is True
    thm = TKTheoremDoc.find_one({"original": "I am kind"}).run()
    assert thm is not None                                        # held in TOKENIKO's perspective
    assert TKTheoremDoc.find_one({"original": "you are kind"}).run() is None


# ---- strip_vocative (the vocative wart — live specimens 2026-07-12/13) -----------------------------
# pure-function tests: the address is stripped, the SUBJECT survives, emptiness never wins.

from lib.core.deixis import strip_vocative


def test_vocative_leading_is_stripped():
    assert strip_vocative("tokeniko, a coin has value", "tokeniko") == "a coin has value"


def test_vocative_leading_case_insensitive():
    assert strip_vocative("Tokeniko, gold is beautiful", "tokeniko") == "gold is beautiful"


def test_vocative_trailing_is_stripped_keeping_terminal_punctuation():
    assert strip_vocative("a coin has value, tokeniko.", "tokeniko") == "a coin has value."
    assert strip_vocative("a coin has value, tokeniko", "tokeniko") == "a coin has value"


def test_name_as_subject_survives():
    # NO comma after the leading name -> it is the subject, never a vocative
    assert strip_vocative("tokeniko is a machine", "tokeniko") == "tokeniko is a machine"


def test_name_mid_sentence_survives():
    # mid-sentence mentions are content (out of the conservative scope)
    assert strip_vocative("I like tokeniko, truly", "tokeniko") == "I like tokeniko, truly"


def test_address_only_message_passes_through():
    assert strip_vocative("tokeniko,", "tokeniko") == "tokeniko,"


def test_no_addressee_is_identity():
    assert strip_vocative("tokeniko, a coin has value", None) == "tokeniko, a coin has value"

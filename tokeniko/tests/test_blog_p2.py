"""Blog P2 — the compose+polish stage (senses/blog.py). PURE tests: the composer runs on
injected fake soul readers (no DB), and polish runs on a fake client (NO network, ever).

Covered: theorem drafts (slug stability, lead line per derived_by, proof lines, taught:<uid>
epithet render), constitution-level anonymization (imprint -> "my author", discord band suffix,
the unscrubbed-line guard), encounter drafts (kicker / self-inconsistency, band closing fact,
slug stability), render_raw (title truncation, readMin floor, proof paragraph), polish (valid
JSON -> polished dict, SDK error / bad JSON / missing keys -> honest raw fallback), and the
compose_post end-to-end transmission contract.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

import senses.blog as blog


# --------------------------------------------------------------
# fakes — souls as plain attribute bags (blog.py is getattr-tolerant by design)
# --------------------------------------------------------------
def _soul(name, uid, trust=0.5, imprint=False, channel=None, isMe=False):
    return SimpleNamespace(name=name, uid=uid, trust=trust, imprint=imprint,
                           channel=channel, isMe=isMe)


_AUTHOR = _soul("kotekino", "kotekino", trust=1.0, imprint=True)
_HELLEN = _soul("hellen", "hellen@discord:7", trust=0.6, channel="discord")
_JOHN = _soul("john", "john@discord:9", trust=0.3, channel="discord")
_ME = _soul("tokeniko", "tokeniko", trust=1.0, isMe=True)

_SOULS = [_AUTHOR, _HELLEN, _JOHN, _ME]


def _readers(souls=None):
    souls = _SOULS if souls is None else souls
    by_uid = {s.uid: s for s in souls}
    return {
        "soul_reader": lambda uid: by_uid.get(uid),
        "souls_reader": lambda: souls,
        "premise_reader": lambda pid: None,
    }


def _theorem_material(**over):
    m = {
        "kind": "theorem",
        "theorem_id": "665f1e2a9b3c4d5e6f708192",
        "original": "every cat is an animal",
        "derived_by": "wondering",
        "premises": ["all cats are mammals", "all mammals are animals"],
        "chain": ["chain: cat -> mammal -> animal"],
        "significance": 0.8,
    }
    m.update(over)
    return m


def _encounter_material(**over):
    m = {
        "kind": "encounter",
        "soul_uid": "hellen@discord:7",
        "episode": "trust:kicker",
        "trust_after": 0.6,
        "note": "kicker on m42 (hellen)",
    }
    m.update(over)
    return m


# --------------------------------------------------------------
# 1. theorem drafts
# --------------------------------------------------------------
def test_theorem_draft_shape_slug_stability_and_proof():
    d1 = blog.compose_draft(_theorem_material(), now=1752300000, **_readers())
    d2 = blog.compose_draft(_theorem_material(), now=1752399999, **_readers())
    assert d1.kind == "log"  # PROVENANCE-encoded: a wondering discovery is the ship's log
    assert d1.slug == "theorem-665f1e2a9b3c4d5e6f708192"
    assert d1.slug == d2.slug                             # same material -> same slug (idempotency)
    assert d1.date.startswith("2025") or d1.date.startswith("2026")  # ISO 8601 from the epoch param
    # lead line per derived_by=wondering + the multi-hop significance note
    assert d1.facts[0] == "While wondering over what I know, I derived: «every cat is an animal»."
    assert "It took more than one step of reasoning to get there." in d1.facts
    # proof lines: the chain + both plain-text premises
    assert "How I know: chain: cat -> mammal -> animal" in d1.proof
    assert "This rests on: «all cats are mammals»." in d1.proof
    assert "This rests on: «all mammals are animals»." in d1.proof


def test_theorem_slug_falls_back_to_a_stable_content_hash():
    d1 = blog.compose_draft(_theorem_material(theorem_id=None), **_readers())
    d2 = blog.compose_draft(_theorem_material(theorem_id=None), **_readers())
    assert d1.slug == d2.slug and d1.slug.startswith("theorem-") and len(d1.slug) == len("theorem-") + 12


def test_theorem_lead_line_per_derived_by():
    lead = lambda by: blog.compose_draft(
        _theorem_material(derived_by=by, chain=[]), **_readers()).facts[0]
    assert lead("teaching").startswith("I was taught something new:")
    assert lead("wondering").startswith("While wondering over what I know, I derived:")
    assert lead("thinking").startswith("Thinking about what I was told, I concluded:")


def test_taught_premise_renders_the_teacher_as_an_epithet():
    d = blog.compose_draft(
        _theorem_material(derived_by="teaching", premises=["taught:hellen@discord:7"], chain=[]),
        **_readers())
    assert "This rests on: a truth taught to me by a new acquaintance on discord." in d.proof
    assert not any("hellen" in p for p in d.proof)        # the uid never survives


def test_objectid_premise_resolves_via_reader_or_stays_generic():
    readers = _readers()
    readers["premise_reader"] = lambda pid: "all humans are mortal"
    d = blog.compose_draft(_theorem_material(premises=["665f1e2a9b3c4d5e6f708100"], chain=[]), **readers)
    assert "This rests on: «all humans are mortal»." in d.proof
    readers["premise_reader"] = lambda pid: None          # unresolvable -> the honest generic line
    d = blog.compose_draft(_theorem_material(premises=["665f1e2a9b3c4d5e6f708100"], chain=[]), **readers)
    assert "This rests on: a truth I already held." in d.proof


# --------------------------------------------------------------
# 2. anonymization — constitution-level: NO soul name/uid ever appears in a draft
# --------------------------------------------------------------
def test_imprinted_author_becomes_my_author_never_his_name():
    d = blog.compose_draft(
        _theorem_material(original="kotekino is not a reptile", chain=[], premises=[]),
        **_readers())
    text = " ".join(d.facts + d.proof)
    assert "my author" in text
    assert "kotekino" not in text.lower()                 # never, case-insensitively
    # and NO channel suffix on the author, even though souls carry channels
    assert "my author on discord" not in text


def test_discord_soul_at_band_thresholds_gets_the_channel_suffix():
    d = blog.compose_draft(
        _theorem_material(original="hellen told me the sky is blue", chain=[], premises=[]),
        **_readers())
    text = " ".join(d.facts)
    assert "a new acquaintance on discord" in text        # trust 0.6 -> the middle band
    assert "hellen" not in text.lower()
    d = blog.compose_draft(
        _theorem_material(original="john said cats bark", chain=[], premises=[]), **_readers())
    text = " ".join(d.facts)
    assert "someone I do not yet trust on discord" in text  # trust 0.3 -> the low band
    assert "john" not in text.lower()


def test_scrub_replaces_the_raw_uid_substring_too():
    d = blog.compose_draft(
        _theorem_material(original="I heard it from john@discord:9 yesterday",
                          chain=[], premises=[]), **_readers())
    text = " ".join(d.facts)
    assert "john@discord:9" not in text and "john" not in text.lower()


def test_guard_drops_a_line_when_scrubbing_fails(monkeypatch):
    # force the scrub to a no-op: the guard must then OMIT the leaking line, never publish it.
    monkeypatch.setattr(blog, "_scrub_text", lambda text, souls: text)
    d = blog.compose_draft(
        _theorem_material(original="every cat is an animal",           # clean lead survives
                          chain=["chain: hellen -> said -> so"],       # leaking proof line dropped
                          premises=[]),
        **_readers())
    assert d.facts[0].startswith("While wondering")
    assert d.proof == []                                  # the unscrubbed chain line was omitted
    # and when even the LEAD leaks, the whole draft is refused (nothing publishable)
    with pytest.raises(ValueError):
        blog.compose_draft(_theorem_material(original="hellen is tall", chain=[], premises=[]),
                           **_readers())


# --------------------------------------------------------------
# 3. encounter drafts
# --------------------------------------------------------------
def test_kicker_encounter_raise_line_and_band_closing_fact():
    d = blog.compose_draft(_encounter_material(), **_readers())
    assert d.kind == "note"
    assert d.facts[0] == ("Today a new acquaintance on discord answered my question with a reason "
                          "that held up against everything I know. I trust them a little more now.")
    assert d.facts[-1] == "To me, they are now a new acquaintance."
    # the internal ledger note is NEVER copied verbatim (it carries the name)
    assert not any("m42" in f or "hellen" in f.lower() for f in d.facts)


def test_self_inconsistency_encounter_lowers_trust_honestly():
    d = blog.compose_draft(
        _encounter_material(soul_uid="john@discord:9", episode="trust:self-inconsistency",
                            trust_after=0.3, note=None), **_readers())
    assert d.facts[0] == ("Today someone I do not yet trust on discord said two things that "
                          "cannot both be true. I trust them a little less now.")
    assert d.facts[-1] == "To me, they are now someone I do not yet trust."


def test_encounter_slug_is_stable_over_the_same_fold_event():
    d1 = blog.compose_draft(_encounter_material(), now=1, **_readers())
    d2 = blog.compose_draft(_encounter_material(), now=999, **_readers())
    d3 = blog.compose_draft(_encounter_material(episode="trust:agreement"), **_readers())
    assert d1.slug == d2.slug and d1.slug.startswith("encounter-")
    assert d3.slug != d1.slug                             # a different episode is a different event


# --------------------------------------------------------------
# 4. render_raw — the honest deterministic fallback
# --------------------------------------------------------------
def test_render_raw_title_truncation_readmin_and_proof_paragraph():
    long_fact = ("Thinking about what I was told, I concluded that every single one of the many "
                 "animals I have ever heard about is in fact an animal after all.")
    draft = blog.PostDraft(kind="argument", slug="theorem-x", date="2026-07-12T00:00:00+00:00",
                           facts=[long_fact, "Second fact."],
                           proof=["How I know: a -> b.", "This rests on: «c»."])
    out = blog.render_raw(draft)
    assert len(out["title"]) <= 81 and out["title"].endswith("…")     # 80 chars + the ellipsis
    assert not out["title"].rstrip("…").endswith(" ")                 # cut at a word boundary
    assert out["excerpt"] == long_fact
    assert out["body"][:2] == [long_fact, "Second fact."]
    assert out["body"][-1] == "How I know: a -> b. This rests on: «c»."  # one joined proof paragraph
    assert out["readMin"] == 1                                        # max(1, words // 200)


# --------------------------------------------------------------
# 5. polish — fake client only, NO network
# --------------------------------------------------------------
class _FakeMessages:
    def __init__(self, text=None, exc=None):
        self._text, self._exc = text, exc
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        block = SimpleNamespace(type="text", text=self._text)
        return SimpleNamespace(content=[block])


class _FakeClient:
    def __init__(self, text=None, exc=None):
        self.messages = _FakeMessages(text=text, exc=exc)


def _draft():
    return blog.PostDraft(kind="argument", slug="theorem-x", date="2026-07-12T00:00:00+00:00",
                          facts=["I concluded: «every cat is an animal»."],
                          proof=["How I know: cat -> mammal -> animal."])


def test_polish_valid_json_returns_polished_dict_and_true():
    payload = {"title": "A cat is an animal", "excerpt": "I worked something out.",
               "body": ["I concluded that every cat is an animal.",
                        "How I know: cat, then mammal, then animal."]}
    client = _FakeClient(text=json.dumps(payload))
    out, ok = asyncio.run(blog.polish(_draft(), client=client))
    assert ok is True
    assert out["title"] == payload["title"] and out["body"] == payload["body"]
    assert out["readMin"] == 1                             # recomputed from the polished body
    # the call shape: strict schema-constrained JSON, no sampling params
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    from lib.rag import BLOG_POLISH
    assert call["output_config"]["format"]["schema"] is BLOG_POLISH.schema
    assert "temperature" not in call and "thinking" not in call


def test_polish_api_connection_error_falls_back_to_raw():
    import anthropic
    import httpx
    exc = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    out, ok = asyncio.run(blog.polish(_draft(), client=_FakeClient(exc=exc)))
    assert ok is False
    assert out == blog.render_raw(_draft())               # the honest deterministic fallback


def test_polish_invalid_json_falls_back():
    out, ok = asyncio.run(blog.polish(_draft(), client=_FakeClient(text="not json {")))
    assert ok is False and out == blog.render_raw(_draft())


def test_polish_missing_keys_or_bad_shape_falls_back():
    out, ok = asyncio.run(blog.polish(_draft(), client=_FakeClient(text=json.dumps({"title": "x"}))))
    assert ok is False and out == blog.render_raw(_draft())
    bad = {"title": "x", "excerpt": "y", "body": []}       # empty body fails client-side validation
    out, ok = asyncio.run(blog.polish(_draft(), client=_FakeClient(text=json.dumps(bad))))
    assert ok is False and out == blog.render_raw(_draft())


def test_polish_truncates_an_overlong_title_client_side():
    payload = {"title": "t" * 300, "excerpt": "e", "body": ["p"]}
    out, ok = asyncio.run(blog.polish(_draft(), client=_FakeClient(text=json.dumps(payload))))
    assert ok is True and len(out["title"]) == 120


# --------------------------------------------------------------
# 6. compose_post — the end-to-end assembly the P3 carrier consumes
# --------------------------------------------------------------
def test_compose_post_theorem_end_to_end_contract():
    payload = {"title": "Every cat is an animal", "excerpt": "A derivation.",
               "body": ["I derived it.", "How I know: cat, mammal, animal."]}
    out = asyncio.run(blog.compose_post(
        _theorem_material(), client=_FakeClient(text=json.dumps(payload)),
        now=1752300000, **_readers()))
    assert set(out) == {"slug", "date", "kind", "title", "excerpt", "body", "readMin", "polished"}
    assert out["kind"] == "log" and out["slug"] == "theorem-665f1e2a9b3c4d5e6f708192"
    assert out["polished"] is True and out["title"] == payload["title"]
    assert isinstance(out["readMin"], int) and out["readMin"] >= 1


def test_compose_post_falls_back_raw_but_still_meets_the_contract():
    import anthropic
    import httpx
    exc = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    out = asyncio.run(blog.compose_post(
        _encounter_material(), client=_FakeClient(exc=exc), **_readers()))
    assert out["polished"] is False and out["kind"] == "note"
    assert out["body"] and all(isinstance(p, str) for p in out["body"])


def test_compose_post_malformed_material_returns_none():
    assert asyncio.run(blog.compose_post({"kind": "theorem"}, **_readers())) is None   # no original
    assert asyncio.run(blog.compose_post({"kind": "weird"}, **_readers())) is None     # unknown kind
    assert asyncio.run(blog.compose_post(
        {"kind": "encounter", "soul_uid": "x", "episode": "trust:nope"}, **_readers())) is None


def test_scrub_collapses_name_uid_epithet_residue():
    # "name (uid)" in source text scrubs to the same epithet twice — the residue must collapse.
    from senses.blog import _clean
    souls = [_soul("kotekino", "kotekino@discord:210", imprint=True)]
    out = _clean("taught by kotekino (kotekino@discord:210) at trust 1.00", souls)
    assert out == "taught by my author at trust 1.00"


def test_kind_encodes_provenance():
    # the author's call (2026-07-12): kind = where the truth happened. teaching -> note (no
    # argument, only trust) · wondering -> log (the solo ship's log) · thinking -> argument
    # (reasoned against live conversation). Unknown derivations stay "argument".
    for derived_by, kind in (("teaching", "note"), ("wondering", "log"), ("thinking", "argument")):
        d = blog.compose_draft(_theorem_material(derived_by=derived_by), now=1752300000, **_readers())
        assert d.kind == kind, (derived_by, d.kind)

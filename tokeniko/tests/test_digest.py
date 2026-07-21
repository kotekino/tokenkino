# ------------------------------------------------------------------------------------------------
# THE DIGEST MACHINERY — the author's ruling 2026-07-21: novelty of reasoning ⇒ immediate post,
# repetition ⇒ digest. Wondering's existence flood («X exists» down the WordNet closure) would
# post dozens of near-identical 1:1 transmissions a night; the cure batches the REPEATED reasoning
# shape into one cumulative post. Covered here: the digest-key extraction (rule / teacher / none),
# the first-occurrence-posts-then-buffers admission, the count-cap flush, the sleep-onset / boot
# flush (one post per non-empty entry, the entry kept as the "seen" marker), and the compose branch
# (with-scaffold + graceful fallback). The pure helpers (digest_classify) take no DB; the buffer
# helpers drive a real brain_state row against the sandbox.
# ------------------------------------------------------------------------------------------------
import pytest

from lib.core.memory import LifeEventKind, TokenikoAction


# ---- digest-key extraction (PURE — no DB, rule ids injected) ------------------------------------

def test_digest_key_wondering_is_the_shared_rule():
    from brain import thinking
    # the flood's premises = {the RULE that fired, a subject-specific FACT}; only the rule id is a
    # known rule source-id, so it is the shared reasoning the key groups by.
    out = thinking.digest_classify("wondering", ["R1", "F-cat"], rule_ids={"R1", "R2"})
    assert out is not None
    key, kind, shared = out
    assert kind == "rule" and shared == ["R1"] and key.startswith("rule:")
    # a DIFFERENT subject via the SAME rule -> the SAME key (that is what makes the batch a batch)
    key2, _, _ = thinking.digest_classify("wondering", ["R1", "F-dog"], rule_ids={"R1", "R2"})
    assert key2 == key
    # a different rule -> a different key (distinct reasoning never merges)
    key3, _, shared3 = thinking.digest_classify("wondering", ["R2", "F-cat"], rule_ids={"R1", "R2"})
    assert key3 != key and shared3 == ["R2"]


def test_digest_key_wondering_none_without_a_rule_premise():
    from brain import thinking
    # no premise is a known rule source-id -> not digestible (conservative -> 1:1)
    assert thinking.digest_classify("wondering", ["F1", "F2"], rule_ids={"R1"}) is None
    assert thinking.digest_classify("wondering", [], rule_ids={"R1"}) is None


def test_digest_key_teaching_is_the_teacher():
    from brain import thinking
    out = thinking.digest_classify("teaching", ["taught:prof@discord:1"])
    assert out == ("taught:prof@discord:1", "teacher", ["prof@discord:1"])
    # a teaching mint with no taught: premise (shouldn't happen) -> not digestible
    assert thinking.digest_classify("teaching", ["something-else"]) is None


def test_digest_key_reactive_thinking_never_digests():
    from brain import thinking
    # a reactive forward-chained derivation is conversational — always 1:1
    assert thinking.digest_classify("thinking", ["R1", "F1"], rule_ids={"R1"}) is None


# ---- the buffer: first-occurrence posts, repetition batches (DB — a real brain_state) -----------

@pytest.fixture()
def digest_world(_io):
    """The life:theorem -> post rule + a dedicated brain_state + a clean digest idea/scaffold
    slate. Fully swept."""
    from lib.core.models import (TKBehaviorRuleDoc, TKBrainStateDoc, TKIdeaDoc, TKScaffoldDoc)
    rule = TKBehaviorRuleDoc(trigger=LifeEventKind.THEOREM.value,
                             action=TokenikoAction.POST.value, urge=0.65)
    rule.insert()
    bs = TKBrainStateDoc(key="digest-test")
    bs.insert()
    yield {"bs": bs}
    TKBehaviorRuleDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.THEOREM.value})
    TKBrainStateDoc.get_motor_collection().delete_many({"key": "digest-test"})
    TKIdeaDoc.get_motor_collection().delete_many({"trigger": LifeEventKind.THEOREM.value})
    TKScaffoldDoc.get_motor_collection().delete_many({"category": {"$regex": "^blog_digest_"}})


def _digest_ideas():
    from lib.core.models import TKIdeaDoc
    return [i for i in TKIdeaDoc.find({"trigger": LifeEventKind.THEOREM.value}).to_list()
            if (i.material or {}).get("kind") == "digest"]


def test_first_occurrence_posts_then_repetition_buffers(digest_world):
    from brain import thinking
    bs = digest_world["bs"]
    # first occurrence of the key -> "post" (its reasoning is news); the entry opens EMPTY (the
    # "seen" marker) and no digest idea spawns yet.
    assert thinking.digest_admit(bs, "rule:k", "rule", "t1", "a cat exists", ["R1"], 0.9) == "post"
    assert bs.digest_buffer["rule:k"]["theorem_ids"] == []
    assert _digest_ideas() == []
    # second + third with the same key -> "buffered" (accumulated, no 1:1)
    assert thinking.digest_admit(bs, "rule:k", "rule", "t2", "a dog exists", ["R1"], 0.9) == "buffered"
    assert thinking.digest_admit(bs, "rule:k", "rule", "t3", "a fish exists", ["R1"], 0.9) == "buffered"
    assert bs.digest_buffer["rule:k"]["theorem_ids"] == ["t2", "t3"]
    assert bs.digest_buffer["rule:k"]["subjects"] == ["a dog exists", "a fish exists"]
    assert _digest_ideas() == []  # nothing flushed yet


def test_count_cap_flushes_immediately(digest_world, monkeypatch):
    from brain import thinking
    monkeypatch.setattr(thinking, "DIGEST_COUNT_CAP", 3)  # keep the test small
    bs = digest_world["bs"]
    thinking.digest_admit(bs, "rule:k", "rule", "t1", "a cat exists", ["R1"], 0.9)   # post (opens)
    thinking.digest_admit(bs, "rule:k", "rule", "t2", "a dog exists", ["R1"], 0.9)   # len 1
    thinking.digest_admit(bs, "rule:k", "rule", "t3", "a fish exists", ["R1"], 0.9)  # len 2
    assert _digest_ideas() == []
    thinking.digest_admit(bs, "rule:k", "rule", "t4", "a bird exists", ["R1"], 0.9)  # len 3 -> FLUSH
    ideas = _digest_ideas()
    assert len(ideas) == 1
    mat = ideas[0].material
    assert mat["digest_kind"] == "rule"
    assert mat["theorem_ids"] == ["t2", "t3", "t4"]
    assert mat["subjects"] == ["a dog exists", "a fish exists", "a bird exists"]
    assert mat["shared"] == ["R1"]
    # the entry stays as the "seen" marker; its accumulation was cleared and the generation bumped
    assert bs.digest_buffer["rule:k"]["theorem_ids"] == []
    assert bs.digest_buffer["rule:k"]["generation"] == 1


def test_flush_digests_spawns_one_post_per_nonempty_entry(digest_world):
    from brain import thinking
    bs = digest_world["bs"]
    # a leftover night: one entry accumulated, one opened-but-empty (first occurrence never repeated)
    bs.digest_buffer = {
        "rule:a": {"kind": "rule", "theorem_ids": ["t2", "t3"],
                   "subjects": ["a dog exists", "a fish exists"], "shared": ["R1"],
                   "opened_at": 0, "generation": 0, "significance": 0.9},
        "taught:u": {"kind": "teacher", "theorem_ids": ["t9"], "subjects": ["I am kind"],
                     "shared": ["u@c:1"], "opened_at": 0, "generation": 0, "significance": 0.9},
        "rule:empty": {"kind": "rule", "theorem_ids": [], "subjects": [], "shared": ["R2"],
                       "opened_at": 0, "generation": 0, "significance": 0.9},
    }
    bs.save()
    n = thinking.flush_digests(bs)
    assert n == 2  # the two non-empty entries; the empty "seen" marker spawns nothing
    ideas = _digest_ideas()
    assert len(ideas) == 2
    keys = {i.material["digest_key"] for i in ideas}
    assert keys == {"rule:a", "taught:u"}
    # every entry PERSISTS (the "seen" markers) with its accumulation cleared
    assert set(bs.digest_buffer) == {"rule:a", "taught:u", "rule:empty"}
    assert all(e["theorem_ids"] == [] for e in bs.digest_buffer.values())
    # a SECOND flush is a quiet no-op (nothing left to ship) — the boot-after-sleep double-call is safe
    assert thinking.flush_digests(bs) == 0
    assert len(_digest_ideas()) == 2


def test_spawn_life_theorem_batches_a_repeated_wondering_rule(digest_world, monkeypatch):
    # the integration seam: _spawn_life_theorem with a bs threaded routes a repeated same-rule
    # wondering mint into the buffer instead of a 1:1 post (the first still posts 1:1).
    from brain import thinking
    from lib.core.models import TKIdeaDoc
    monkeypatch.setattr(thinking, "_active_rule_source_ids", lambda: {"R1"})
    bs = digest_world["bs"]

    def _theorem_ideas():
        return [i for i in TKIdeaDoc.find({"trigger": LifeEventKind.THEOREM.value}).to_list()
                if (i.material or {}).get("kind") == "theorem"]

    thinking._spawn_life_theorem("t1", "a cat exists", "wondering", ["R1", "F-cat"], "c", False, bs=bs)
    assert len(_theorem_ideas()) == 1                       # first occurrence -> 1:1 post
    thinking._spawn_life_theorem("t2", "a dog exists", "wondering", ["R1", "F-dog"], "c", False, bs=bs)
    assert len(_theorem_ideas()) == 1                       # repetition -> batched, no new 1:1
    assert bs.digest_buffer["rule:" + _key_tail(["R1"])]["theorem_ids"] == ["t2"]


def _key_tail(shared):
    import hashlib
    return hashlib.sha1("|".join(shared).encode("utf-8")).hexdigest()[:12]


# ---- the compose branch (senses/blog) — with-scaffold + graceful fallback ----------------------

class _FakeSoul:
    def __init__(self, uid, name, trust=0.9, imprint=False):
        self.uid, self.name, self.trust, self.imprint, self.isMe = uid, name, trust, imprint, False
        self.channel = "discord"


def test_compose_digest_rule_renders_subjects_and_the_shared_rule():
    from senses import blog
    material = {"kind": "digest", "digest_key": "rule:k", "digest_kind": "rule",
                "theorem_ids": ["t2", "t3"], "subjects": ["a dog exists", "a fish exists"],
                "shared": ["R1"], "significance": 0.9}
    draft = blog.compose_draft(
        material, soul_reader=lambda uid: None, souls_reader=lambda: [],
        premise_reader=lambda pid: "every thing that thinks exists", now=0)
    assert draft.kind == "log"
    body = " ".join(draft.facts)
    assert "«a dog exists»" in body and "«a fish exists»" in body   # the fenced subject list
    proof = " ".join(draft.proof)
    assert "every thing that thinks exists" in proof               # the shared rule, resolved
    # deterministic slug over the same material
    d2 = blog.compose_draft(material, soul_reader=lambda uid: None, souls_reader=lambda: [],
                            premise_reader=lambda pid: "x", now=0)
    assert d2.slug == draft.slug


def test_compose_digest_teacher_credits_the_epithet_never_a_name():
    from senses import blog
    material = {"kind": "digest", "digest_key": "taught:u", "digest_kind": "teacher",
                "theorem_ids": ["t9"], "subjects": ["I am kind"], "shared": ["prof@discord:1"],
                "significance": 0.9}
    prof = _FakeSoul("prof@discord:1", "Professor")
    draft = blog.compose_draft(
        material, soul_reader=lambda uid: prof, souls_reader=lambda: [prof],
        premise_reader=lambda pid: None, now=0)
    proof = " ".join(draft.proof)
    assert "Professor" not in proof                                 # anonymized — the epithet only
    assert "a trusted friend on discord" in proof


def test_compose_digest_malformed_material_raises():
    from senses import blog
    with pytest.raises(ValueError):
        blog.compose_draft({"kind": "digest", "subjects": []}, souls_reader=lambda: [], now=0)


def test_compose_digest_uses_a_seeded_scaffold_when_present(digest_world):
    # the with-scaffold path: a seeded blog_digest_lead row is the ONLY one for its brand-new
    # category, so creative_compose's weighted pick is deterministic — its marker must surface.
    from lib.core.models import TKScaffoldDoc
    from senses import blog
    TKScaffoldDoc(category="blog_digest_lead", template="DIGEST-MARKER: a batch of thoughts.",
                  slots=[], weight=1.0, provenance="seed").insert()
    material = {"kind": "digest", "digest_key": "rule:k", "digest_kind": "rule",
                "theorem_ids": ["t2"], "subjects": ["a dog exists"], "shared": ["R1"],
                "significance": 0.9}
    draft = blog.compose_draft(
        material, soul_reader=lambda uid: None, souls_reader=lambda: [],
        premise_reader=lambda pid: "every thing that thinks exists", now=0)
    assert any("DIGEST-MARKER" in f for f in draft.facts)           # the seeded shelf spoke

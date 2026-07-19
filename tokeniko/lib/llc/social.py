# ------------------------------------------------------------------------------------------------
# THE SOCIAL-ACT DETECTOR (survey slice 4, hunch 8 — the etiquette family's recognition half).
#
# «hello John» is not a claim about the world: a social act must be RECOGNIZED, never evaluated —
# before slice 4 it compiled to junk, graded UNKNOWN, and could spawn a «why is that?» (the mind
# interrogating a wave). This detector runs at the compile seam (api /input), BEFORE the parser:
#
#   - PURE social act («hello», «thanks tokeniko», «good morning everyone!») -> (kind, at, "")
#     — the caller stores the memory item WITH the kind and WITHOUT a zip (nothing to compile);
#     thinking branches early and reacts socially (or stays quiet when the act names another).
#   - MIXED utterance («hello tokeniko, is gold beautiful?») -> (kind, at, remainder) — fork A
#     (author's ruling): CONTENT WINS. The caller compiles the remainder clean (the social prefix
#     stripped exactly like a vocative) and NO reflex fires (one reply, never two).
#   - Anything else -> None (the utterance flows whole, byte-identical to before).
#
# Recognition is ANCHOR-CATCH (the house principle): the head resolves through the "social"
# category of lib/llc/anchors (exact-hit fast path -> nearest-anchor above the floor), never a
# closed list. CONSERVATIVE by construction: only a HEAD-position formula counts, and a mixed
# strip requires a SEPARATOR after the social segment — «hello is a word» has none and flows
# whole (the metalinguistic guard).
# ------------------------------------------------------------------------------------------------
from typing import NamedTuple, Optional

from lib.llc.anchors import anchor_resolve

# words that address the whole ROOM (the act is for everyone — social_at stays None)
_ROOM_WORDS = {"everyone", "everybody", "all", "guys", "folks", "friends", "people", "chat"}
_SEPARATORS = ",.!?;:…"


class SocialDetection(NamedTuple):
    kind: str                 # "greeting" | "thanks" | "farewell" (the EvalToken tails)
    at: Optional[str]         # whom the act names, lowercase (None = the room)
    remainder: str            # "" = a pure social act; else the content to compile (fork A)


def _clean(word: str) -> str:
    return word.strip(_SEPARATORS + "'\"«»").strip().lower()


def _has_separator(word: str) -> bool:
    return bool(word) and word[-1] in _SEPARATORS


def social_detect(text: str, tokeniko_name: str = "") -> Optional[SocialDetection]:
    words = (text or "").split()
    if not words:
        return None
    me = (tokeniko_name or "").strip().lower()

    # a leading vocative naming TOKENIKO («tokeniko, hello!») — address noted, head check moves on.
    # Only his own name is special-cased: any other leading word is indistinguishable from content.
    i = 0
    at: Optional[str] = None
    if me and _clean(words[0]) == me and len(words) > 1:
        at = me
        i += 1

    # the head: try the bigram first (EXACT-only — «good morning»), then the single word
    # (exact + semantic fallback through the anchor resolver).
    kind = None
    head_len = 0
    if i + 1 < len(words):
        bigram = f"{_clean(words[i])} {_clean(words[i + 1])}"
        kind = anchor_resolve(bigram, "social")
        if kind:
            head_len = 2
    if not kind:
        kind = anchor_resolve(_clean(words[i]), "social")
        if kind:
            head_len = 1
    if not kind:
        return None

    j = i + head_len
    rest = [w for w in words[j:] if _clean(w)]  # drop punctuation-only tokens («hello :)»)

    # PURE: nothing after the head
    if not rest:
        return SocialDetection(kind, at, "")

    # ONE token after the head = a vocative (a name or a room word), never content
    if len(rest) == 1:
        t = _clean(rest[0])
        if t in _ROOM_WORDS:
            return SocialDetection(kind, at, "")
        return SocialDetection(kind, t, "")

    # MIXED: content follows. A room word or tokeniko's own name right after the head is a
    # vocative — consume it («hello tokeniko, is gold beautiful?» / «hello everyone! I woke up»).
    # An arbitrary name stays in the remainder (we cannot lexically prove it is a vocative; the
    # parser's vocative machinery handles it downstream).
    k = j
    t = _clean(words[k])
    if t in _ROOM_WORDS:
        k += 1
    elif me and t == me:
        at = me
        k += 1

    # the strip needs a SEPARATOR boundary in the consumed segment — «hello is a word» has none
    # and is NOT a social prefix: the utterance flows whole (the metalinguistic guard).
    if not any(_has_separator(w) for w in words[i:k]):
        return None

    remainder = " ".join(words[k:]).strip()
    return SocialDetection(kind, at, remainder if remainder else "")

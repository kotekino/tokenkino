# --------------------------------------------------------------
# lib/core/deixis.py — PERSPECTIVE NORMALIZATION at the knowledge boundary.
#
# A theorem materialized from ANOTHER SOUL'S SPEECH must not store the speaker's surface string
# verbatim: speaker-relative pronouns flip meaning the moment tokeniko HOLDS the sentence himself
# (kotekino's «I am your creator» re-uttered by tokeniko makes "I" mean tokeniko — inverted). The
# compiled zip is ALREADY perspective-resolved (identities carry the teacher's uid); only the
# surface `original` — the dedup key AND the NL render source — is broken. So the fix lives HERE,
# at materialization, never at rendering: rewrite the sentence uttered BY `speaker_name` TO
# tokeniko into context-free form ("I" → the speaker's name; "you"/"your" → tokeniko's own first
# person, which IS context-free once the sentence is held by him).
#
# The mapping is deliberately CONSERVATIVE — a closed-class table over copular/aux constructions
# (the only ones whose subject-verb agreement is mechanically derivable). Everything else honestly
# fails: after the passes, ANY surviving first/second-person deictic (a bare "I gave…" — present-
# tense agreement unknowable; a bare object "…protect you" — role unknowable) returns None, and
# the caller refuses to believe the sentence (remembered-not-believed). Better an honest gap than
# a meaning-flipped belief.
#
# PURE + dependency-free (stdlib only): safe to import from anywhere, unit-testable without a DB.
# --------------------------------------------------------------
import re
from typing import Optional

# word tokens, apostrophes (straight AND typographic) kept inside the token so contractions
# ("I'm", "you're", "don't") arrive whole.
_WORD_RE = re.compile(r"[A-Za-z’']+")

# the deictic closed class (lowercased). "I" needs no case rule of its own here: as a WHOLE word
# token it can only be "I" or a standalone "i" — both fold to "i" (never a substring of a longer
# word, the tokenizer guarantees the boundary).
_DEICTICS = frozenset({
    "i", "me", "my", "mine", "myself",
    "you", "your", "yours", "yourself",
})

# Pass 1 — speaker-subject bigrams: "I <aux>" → "{name} <third-person-agreed aux>". Only auxes whose
# third-person form is KNOWN are listed; a bare lexical verb after "I" is not (English present-tense
# agreement is not derivable without morphology) and falls through to the residual guard.
_I_AUX = {
    "am": "is", "was": "was",
    "have": "has", "had": "had",
    "do": "does", "don't": "does not",
    "did": "did", "didn't": "did not",
    # agreement-invariant modals map to themselves (contractions expanded for cleanliness)
    "will": "will", "won't": "will not", "would": "would",
    "can": "can", "cannot": "cannot", "can't": "cannot",
    "could": "could", "should": "should", "must": "must", "may": "may", "might": "might",
}

# Pass 2 — tokeniko-subject bigrams: "you <aux>" → "I <first-person-agreed aux>". A subject "you"
# addressed TO tokeniko is tokeniko — so the rewrite is his own first person, which is context-free
# once he holds the sentence. Same conservatism: aux-anchored only ("you know…" — subject or object
# "you"? role unknowable without the aux → residual guard).
_YOU_AUX = {
    "are": "am", "were": "was",
    "have": "have", "had": "had",
    "do": "do", "don't": "do not",
    "did": "did", "didn't": "did not",
    "will": "will", "would": "would",
    "can": "can", "cannot": "cannot", "can't": "cannot",
    "could": "could", "should": "should", "must": "must", "may": "may", "might": "might",
}

# subject contractions — single tokens carrying subject + aux fused (both apostrophe glyphs
# normalized before lookup).
_I_CONTRACTIONS = {"i'm": "{name} is", "i've": "{name} has"}
_YOU_CONTRACTIONS = {"you're": "I am", "you've": "I have"}

# Pass 3 — safe singles: role-unambiguous deictics ("me" is only ever an object; "my"/"your" only
# ever possessive determiners; the reflexives keep their binding once the subject is rewritten).
_SPEAKER_SINGLES = {"me": "{name}", "my": "{name}'s", "mine": "{name}'s", "myself": "{name}"}
_TOKENIKO_SINGLES = {"your": "my", "yours": "mine", "yourself": "myself"}


def _fold(token: str) -> str:
    """Lowercase + normalize the typographic apostrophe, so one table serves both glyphs."""
    return token.replace("’", "'").lower()


def _has_deictic(token: str) -> bool:
    """Does the token contain a first/second-person deictic at a word boundary? Apostrophe-split so
    unhandled contractions ("I'll", "you'd") are seen as carrying their pronoun — while a plain
    possessive ("cat's") is not."""
    return any(part in _DEICTICS for part in _fold(token).split("'"))


def normalize_deixis(text: str, speaker_name: Optional[str]) -> Optional[str]:
    """Rewrite a sentence uttered BY `speaker_name` TO tokeniko into context-free form.

    Returns the normalized string; the UNCHANGED string when it contains no deictics (fast path);
    or None when it cannot be safely normalized — the caller then refuses to believe it
    (remembered-not-believed). With no speaker_name a deictic-bearing text is unfixable (whose
    perspective?) → None; a deictic-free one passes through untouched.
    """
    if text is None:
        return None
    tokens = list(_WORD_RE.finditer(text))

    # fast path: no deictics anywhere → nothing to normalize, the text is already context-free.
    if not any(_has_deictic(m.group(0)) for m in tokens):
        return text
    if not speaker_name:
        return None  # deictics present but no perspective to resolve them against

    # one left-to-right walk: bigram rules consume two tokens, contractions/singles one. Replacements
    # are collected as (start, end, replacement) spans over the ORIGINAL text and spliced at the end,
    # so everything between tokens (spacing, punctuation) survives verbatim. `consumed` marks the
    # tokens a rule handled — the residual guard below inspects only what NO rule touched (a
    # substituted "I am" from pass 2 is tokeniko's own, correct first person — never re-flagged).
    replacements: list[tuple[int, int, str]] = []
    consumed = [False] * len(tokens)
    i = 0
    while i < len(tokens):
        tok = _fold(tokens[i].group(0))
        nxt = _fold(tokens[i + 1].group(0)) if i + 1 < len(tokens) else None
        if tok in _I_CONTRACTIONS:
            replacements.append((tokens[i].start(), tokens[i].end(),
                                 _I_CONTRACTIONS[tok].format(name=speaker_name)))
            consumed[i] = True
        elif tok in _YOU_CONTRACTIONS:
            replacements.append((tokens[i].start(), tokens[i].end(), _YOU_CONTRACTIONS[tok]))
            consumed[i] = True
        elif tok == "i" and nxt in _I_AUX:
            replacements.append((tokens[i].start(), tokens[i + 1].end(),
                                 f"{speaker_name} {_I_AUX[nxt]}"))
            consumed[i] = consumed[i + 1] = True
            i += 2
            continue
        elif tok == "you" and nxt in _YOU_AUX:
            replacements.append((tokens[i].start(), tokens[i + 1].end(), f"I {_YOU_AUX[nxt]}"))
            consumed[i] = consumed[i + 1] = True
            i += 2
            continue
        elif tok in _SPEAKER_SINGLES:
            replacements.append((tokens[i].start(), tokens[i].end(),
                                 _SPEAKER_SINGLES[tok].format(name=speaker_name)))
            consumed[i] = True
        elif tok in _TOKENIKO_SINGLES:
            replacements.append((tokens[i].start(), tokens[i].end(), _TOKENIKO_SINGLES[tok]))
            consumed[i] = True
        i += 1

    # Pass 4 — the residual guard (the safety valve): any deictic the table did NOT confidently
    # handle poisons the WHOLE sentence — even when other parts were handleable ("I will always
    # protect you": "I will" maps, the trailing bare "you" does not → the sentence is refused).
    for idx, m in enumerate(tokens):
        if not consumed[idx] and _has_deictic(m.group(0)):
            return None

    # splice the replacements over the original text (spans are non-overlapping and in order).
    out: list[str] = []
    cursor = 0
    for start, end, repl in replacements:
        out.append(text[cursor:start])
        out.append(repl)
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


# --------------------------------------------------------------
# VOCATIVE STRIP — the deixis sibling (the vocative wart, live specimens 2026-07-12/13). Channel
# speech addressed by name («tokeniko, a coin has value») carries the ADDRESS, not content: the
# parser already drops it from the zip (no vocative entity compiles), but the surface `original`
# — the dedup key and the NL render source — kept it, so taught theorems stored the wart and the
# blog polish had to scrub what the brain should never have held. Strip at materialization,
# beside normalize_deixis.
#
# CONSERVATIVE by anchor: only a LEADING "<name>," or a TRAILING ", <name>" is a vocative — the
# comma is the discriminator ("tokeniko is a machine" leads with the name as SUBJECT and must
# survive untouched). Mid-sentence vocatives («gold, tokeniko, is valuable») and greeting forms
# («hey tokeniko …») stay out of scope: rarer, riskier, and the greeting belongs to the etiquette
# layer (hunch 8). A message that is ONLY the address («tokeniko!») passes through unchanged —
# stripping to emptiness is never an improvement. PURE, stdlib-only, like everything here.
# --------------------------------------------------------------
def strip_vocative(text: str, addressee_name: Optional[str]) -> str:
    if not text or not addressee_name:
        return text
    name = re.escape(addressee_name)
    out = re.sub(rf"^\s*{name}\s*,\s*", "", text, flags=re.IGNORECASE)
    out = re.sub(rf"\s*,\s*{name}\s*([.!?…]*)\s*$", r"\1", out, flags=re.IGNORECASE)
    return out if out.strip() else text

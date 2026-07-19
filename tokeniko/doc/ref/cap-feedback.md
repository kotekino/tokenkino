# cap-feedback.md — notes of the Captain about the interaction with tokeniko on Discord

Here were I take notes on the behavior tokeniko showed during conversation in the public channel of his Discord server (tokeniko's Playground).
This is not a buglist, it's just the empirical observation of the actual final behavior he showed, that should be used as a source for "further inspection" in case the behavior noticed was not explicitely intended by our coding, but more an emergent property

## ✅ Session 2026-07-05 — the interactions

1. ✅ Sometimes tokeniko answers to a question explicitely directed to somebody else "Salmon, are you a human?" as if it was directed to him explicitely. I think this is the consequence of the interpretation of the directness parameter when the context sees him involved in previous neutrally directed statements. Which is good in terms of dynamic engagement, but results in over-engagement (like those people who want to answer to a question not directed to them "just because they know the answer"). Not a bug, but something we should guard/smooth somehow.

## Session 2026-07-08 — answering to what
1. Yesterday, talking with him, I noticed that tokeniko has difficulties with a simple task: he knows he is a software (many KB items say so), he knows he is a mind. But if I ask "what are you" he can't answer. Is the "what" the problem? Where do we think the problem is?

*(QM check 2026-07-19 — the behavior RECURRED live 2026-07-18, «tokeniko, what are you?» asked
four times → «I do not know» / «why is that?». Diagnosed on the stored zip: NOT the "what" — the
question compiles perfectly (`wh_role=PREDICATE`, subject = the identity uid `tokeniko`, no
sense). The wh-solver's what-branch (`e_wh_solve.py`) reads only the subject SENSE and walks the
WordNet is_a graph; an INDIVIDUAL subject has no sense, so it answers IDK while «I am a software»
/ «I am a mind» sit in the KB keyed by that very identity. Same identity-blindness family as the
reduct-answer key fixed 2026-07-19 (`test-feedback.md`); the DIRECT branch already handles both
sense and identity subjects, so the fix shape is known. Queued in roadmap §2 — not approached.)*
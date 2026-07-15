# cap-feedback.md — notes of the Captain about the interaction with tokeniko on Discord

Here were I take notes on the behavior tokeniko showed during conversation in the public channel of his Discord server (tokeniko's Playground).
This is not a buglist, it's just the empirical observation of the actual final behavior he showed, that should be used as a source for "further inspection" in case the behavior noticed was not explicitely intended by our coding, but more an emergent property

## Session 2026-07-05 — the interactions

1. Sometimes tokeniko answers to a question explicitely directed to somebody else "Salmon, are you a human?" as if it was directed to him explicitely. I think this is the consequence of the interpretation of the directness parameter when the context sees him involved in previous neutrally directed statements. Which is good in terms of dynamic engagement, but results in over-engagement (like those people who want to answer to a question not directed to them "just because they know the answer"). Not a bug, but something we should guard/smooth somehow.
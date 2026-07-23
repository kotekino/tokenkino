# BRIEF: the digest machinery — cumulative voice actions

> Work order for the 1st Officier. Design ruled by the Captain 2026-07-21 (pinned in
> `doc/roadmap.md` §1, "The digest machinery"); this brief operationalizes it. `CLAUDE.md` is law.
> DO NOT commit; KB seed scripts surfaced, never `--apply`-run.

## The problem (context)

Wondering's existence flood («X exists»/«X has property» down the WordNet closure) posts EVERY
theorem 1:1 to the blog (`life:theorem` → `tokeniko:post`): dozens of near-identical transmissions
per night. The Captain's ruling: **novelty of reasoning ⇒ immediate post; repetition of reasoning
⇒ digest** — one cumulative post per repeated reasoning shape («since x, y, z exist, each …»).

## The design (ruled, not open)

1. **Classification** (where post ideas spawn for freshly minted theorems):
   - **1:1 always** (unchanged behavior): anything directed at a person (answers, greetings —
     conversation never batches) · refutations / speak-ups · a derivation whose reasoning is NOVEL.
   - **Cumulative**: same-rule wondering mints · same-teacher taught runs.
   - **Operational novelty rule** (QM's interpretation, Captain-reviewed): the digest KEY's FIRST
     occurrence posts 1:1 (its reasoning is news); from the SECOND occurrence on, mints with the
     same key append to the digest buffer instead of spawning a post idea.
2. **The digest key** = the shared reasoning, extracted from provenance:
   - wondering mint: the shared RULE premise (e.g. the rule id / stable rule key in
     `provenance.premises` — the «every thing that exists has more than one property» premise for
     the flood rows). Key shape: `rule:<premise-key>`.
   - taught mint: the teacher — `taught:<soul_uid>` (already the provenance premise shape).
   - No extractable shared premise → not digestible → 1:1 (conservative).
3. **The buffer lives ON `brain_state`** (everything-is-KB, restart-proof): a new field, e.g.
   `digest_buffer: dict[str, dict]` keyed by digest key, each entry holding at least
   `{kind: "rule"|"teacher", theorem_ids: [...], opened_at: epoch}`. Design the exact shape; keep
   it JSON-plain (Bunnet Mixed-friendly).
4. **Flush** (each flush spawns ONE post idea per buffer entry with ≥1 item, then clears it):
   - **Sleep-onset primary**: at the falling-asleep transition in `brain/main.py`'s coordinator
     (beside `_fold_awake`) — the goodnight summary.
   - **Count-cap guard**: an entry reaching 15 subjects flushes immediately (no monster posts).
   - **Wake/boot flush**: leftovers of an interrupted night flush on coordinator boot.
5. **The digest post idea**: same `tokeniko:post` pipeline, `material = {"kind": "digest",
   "digest_key": ..., "theorem_ids": [...]}` (mirror the existing
   `material={"kind": "theorem", ...}` shape). The composer (`brain/compose.py` +
   `lib/core/voice.creative_compose`) gets a digest branch: render the subject list + the shared
   rule into one text. A new scaffold CATEGORY for digests: add rows via a seed script under
   `scripts/` (sibling-style, `--apply`-gated — surface it, do NOT apply). Compose must degrade
   gracefully if the category has no rows yet (fall back to a plain composed sentence, verbatim
   ship — mirror existing fallback behavior).
6. **rag2-out** polishes the digest post exactly like any other post (no special path).

## Scope fence

- IN: wondering-mint digests + taught-run digests, buffer + flush + compose + scaffold seed script
  + tests.
- OUT (explicitly): trust-ledger-movement digests (follow-on) · any change to the minting/
  reasoning itself · behavior_rules changes beyond what routing strictly needs (if a new trigger
  row is needed, seed-script it, don't hand-insert).

## Where to look first

- `brain/thinking.py` — where mints happen (`kb_wonder` materialization, `materialize_taught`)
  and where `life:theorem` ideas spawn (find the exact spawn site; the classification hook goes
  where the post idea is born, NOT where the theorem is minted — minting is sacred).
- `brain/behavior.py` — `spawn_ideas_for` / the trigger table.
- `brain/main.py` — the coordinator's sleep transition (flush site 1: beside `_fold_awake`), the
  boot block (flush site 3: beside `_boot_awake_ledger`).
- `lib/core/memory.py` — `BrainState` (add the buffer field beside the lived-awake ledger),
  `MEMScaffold`/scaffold models for the category shape.
- `brain/compose.py` + `lib/core/voice.py` — the compose routing + categories.
- `scripts/seed_scaffolds*.py` (or the sibling that seeded the store) — the seed-script pattern.

## Acceptance

- Unit tests (new file `tests/test_digest.py`, style of `tests/test_sleep_phase.py`): key
  extraction (rule / teacher / none) · first-occurrence-posts-then-buffers · count-cap flush ·
  sleep-onset flush spawns ONE idea per key with the ids · boot flush of leftovers · compose
  renders a digest (with-scaffold and fallback paths).
- Full gate green: `PYTHONPATH=. ../.venv/bin/python -m pytest tests/ -q` (~13 min; all passed,
  1 xfailed is the standing norm).
- Working tree left dirty (NO commit); seed script NOT applied; daemons untouched.
- Report per the standing report format (outcome / files / gate verbatim / deviations / findings).

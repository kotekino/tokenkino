# Brief: learned scaffolds from the audience — two-stage accommodation (2026-07-24)

**To the 1st Officier, from the QM.** Roadmap §1's «learned scaffolds from the audience», designed
with the Captain today. Read this whole brief before touching code; the laws of the ship
(`.claude/agents/first-officer.md`) apply in full.

## The idea (the Captain's ruling, verbatim spirit)

Humans in an intense 1:1 dialogue converge on each other's phrasing (linguistic accommodation) —
and some of it outlives the conversation. tokeniko gets the same, in two stages:

1. **Ephemeral mimicry (realtime).** While talking with a decently-trusted person, phrasings of
   theirs that re-express a communicative act he already performs join his shelf **scoped to that
   person** — he converges toward their register mid-conversation; his voice with everyone else is
   untouched.
2. **Sleep consolidation (stricter).** The sleep phase reviews the mimic rows: rows from a
   highly-trusted teacher that carry an *affinity* signal (he actually used the row, OR a positive
   trust episode with that teacher sits close in time) are **promoted** to global learned rows
   (`taught:<uid>`, low weight — the curated voice stays dominant). Everything else is **retired,
   never deleted** (`enabled=False` — biography). The quarantine IS the conversation scope: the
   durable shelf only grows in sleep.

**v1 scope (ruled):** Lane A (social items) + Lane B **slot-less only** (whole-zip match). Slotted
template extraction (masking `{retracted}` etc. back out of surface text) is explicitly OUT — v2.

## Build

### 1. Data model — `lib/core/memory.py` `MEMScaffold`

Two new fields (flat model, defaults keep every existing row valid; no model_rebuild concerns):

- `scope: Optional[str] = None` — canonical stakeholder uid this row is private to; `None` = global.
- `used: int = 0` — times compose actually picked this row (the consolidation's adoption signal).

Provenance grows one value: `"mimic:<canonical_uid>"` (ephemeral, pre-consolidation). Update the
field's comment accordingly (`"seed" | "mimic:<uid>" | "taught:<uid>"`).

### 2. The voice reader — `lib/core/voice.creative_compose`

- New parameter `target: Optional[str] = None` (the outbound recipient's canonical uid).
- Shelf filter: keep rows with `scope is None` or `scope == target`. (Callers that don't pass a
  target — blog, tests — therefore never see scoped rows. That is the design.)
- When the **chosen** row is scoped (a mimic), increment its `used` and save — inside the existing
  try; a failed save must never break speech (log + continue). Seeds/global rows: no tick.

### 3. The compose seam — thread the target

- `brain/compose.compose_raw` gains `target: Optional[str] = None`, passed through to
  `creative_compose`.
- `brain/behavior.py:314` (`plan_action`'s compose call): pass the resolved **canonical** uid of
  the outbound recipient (the same target the action is directed at; resolve through
  `canonical_uid` the way the trust ledger does — one hop). Where an action has no person target
  (posts, internal), pass None.

### 4. The detector — new module `brain/mimicry.py` (parser-free: Mongo + ring reads only)

One entry point, `mimic_observe(item) -> bool` (True = a row was minted), called from
`think_phase` immediately after `context.context_add(item)` (`brain/thinking.py:1508`), for BOTH
social and zipped items, wrapped like the ring feed (an error logs + continues, never blocks
thinking).

Gates, in order (all env-tunable, defaults as ruled):

1. **Never self**: `item.sourceId` resolving to tokeniko's own stakeholder → skip.
2. **Momentum («after a while»)**: ≥ `MIMIC_MOMENTUM` (default **3**) prior items from this talker
   in the current channel's context ring. Add a small reader to `brain/context.py` (e.g.
   `talker_depth(key, uid) -> int` counting their rows in the ring) — derived, never stored state.
3. **Trust («decent»)**: talker's folded canonical trust ≥ `MIMIC_BAR` (default **0.6**).
4. **Lane A** (`item.social` set, no zip): `greeting → greet`, `farewell → farewell`. `thanks` has
   no speakable category yet (the reciprocal-thanks is parked) — skip it, one comment noting why.
5. **Lane B** (`item.zip` set): compare `evaluator_compareZip(item.zip, row.zip)` against every
   enabled, **global**, **slot-less**, zip-bearing row of the `_LEARNABLE` categories
   (`{greet, farewell, agree, answer_yes, answer_no, answer_idk, why, goodnight, ask_more}` — a
   module constant; blog_*/concede_*/reduct are NOT learnable). Best match ≥ `MIMIC_FLOOR`
   (default **0.85**) → that row's category is the act being re-phrased.
6. **Quality fence**: template = `item.original` **verbatim** (his raw words are the mannerism);
   skip if it contains `{` or `}` (str.format collision), or length > 120 chars (a mannerism is
   short), or it exactly matches an existing template in that category (any provenance/scope —
   dedup), or the talker already has ≥ `MIMIC_CAP` (default **8**) un-retired mimic rows (growth
   bound).

Mint: `TKScaffoldDoc(category=…, template=original, slots=[], zip=(item.zip or None),
provenance=f"mimic:{uid}", trusted=talker_trust, weight=1.0, enabled=True, scope=uid, used=0)`.
(Lane A rows carry `zip=None` — same as seeds that honestly don't compile; the brain is
parser-free, so no compile happens here. Lane B rows carry the item's own zip.)

Log one line per mint in the thinking register's voice (e.g.
`[mimicry] 🪞 a way of speaking picked up from <name> (<category>)`).

### 5. Consolidation — `brain/main.py` `_sleep_duty` (line 546)

A new pass beside the untangle (NOT gated on KB change — gated on mimic rows existing): for every
`enabled=True` row with a `scope`:

- **Promote** iff teacher's folded canonical trust NOW ≥ `CONSOLIDATE_BAR` (default **0.9** — the
  belief-teaching bar) AND ( `used ≥ 1` OR a positive-delta `MEMTrustEpisode` for that canonical
  uid within ± `MIMIC_EPISODE_PROX` (default **1800** s) of the row's `createdAt` ):
  `scope=None`, `provenance=f"taught:{uid}"`, `trusted=min(teacher_trust, 0.9)`, `weight=0.5`
  (learned rows season the voice, the curated shelf stays dominant). `used` stays (biography).
- **Retire** otherwise: `enabled=False`, everything else untouched — never deleted. One night is
  a mimic's whole ephemeral life; the conversation is over by sleep.

One log line per promotion and a count line for retirements, in the sleep register's voice.

### 6. Tests — new `tests/test_mimicry.py` (sandbox DB, in the style of `test_digest.py`)

Cover at least: momentum gate (2 prior items → no mint; 3 → mint) · trust gate (<0.6 → no mint) ·
Lane A greeting mint (verbatim, scoped, zip=None) · Lane B slot-less match mint (≥ floor mints
with the matched category + the item's zip; below floor doesn't) · self-speech never mints ·
dedup (same template → one row) · braces + length fences · cap fence · scoped visibility
(`creative_compose` with matching target can pick the row; without target / other target never) ·
`used` ticks on a scoped pick, not on seeds · consolidation promote-by-use ·
promote-by-episode-proximity · retire-on-low-trust · retire-on-no-affinity · never-mute fallback
untouched. Plus: existing compose/digest tests stay green (the new params are optional-default).

### 7. The gate

Targeted first (`tests/test_mimicry.py tests/test_digest.py` + any compose/behavior test files you
touch), then the FULL gate — foreground, per your contract. Done = full gate green
(all passed, 1 xfailed is the standing normal).

## Out of scope (do NOT build; report if tempted)

- Slotted-template extraction (v2, needs surface-alignment design).
- Any blog/transmission voice for «I picked up a way of speaking from X» — a natural follow-on,
  the QM will roadmap it.
- Weight growth over time for learned rows; `thanks` consumption (parked reciprocal-thanks).
- No seeding, no `--apply` scripts, no daemon restarts, no status-doc edits (the QM reconciles).

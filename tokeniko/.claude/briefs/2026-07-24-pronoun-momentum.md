# Brief: pronoun momentum — «you» resolves where directedness points (2026-07-24, lead B)

**To the 1st Officier, from the QM.** Lead B of the 2026-07-24 diagnosis (A = the ears'
hallucination chain, a separate brief — this one dispatches AFTER A lands). The laws of the ship
apply in full. DO NOT start while another build is un-committed in the tree.

## The Captain's ruling (the design spine)

Directedness should VARY with conversational momentum, and **pronouns resolve wherever
directedness points**. Misunderstanding is not a bug to prevent — it is human behavior to
faithfully reproduce. His example: in a channel, «tokeniko, how are you?» → tokeniko answers →
«do you think I can teach you about feelings?» → tokeniko answers «yes» → «oh I was talking to
fragolina». tokeniko binding that «you» to himself is CORRECT — the speaker caused the ambiguity;
the correction is just more conversation. «We need to mimic this behavior.»

The live defect it cures: «so, what are you?» mid-dialogue graded ambient 0.6 → below the 0.9
addressed bar → the parser's listener gate left «you» an uid-less stub (`ids={}`) → the wh-solver
honestly IDK'd about what he is, with «I am a software» sitting active in the KB.

## What exists (do not rebuild)

- `senses/inbound.grade_directedness` — stepwise: DM 1.0 · addressed (mention/name/reply-to-him)
  0.9 · ambient 0.6 · someone else's thread 0.15.
- `api/main.py` `/input`: `addressed = directedness >= 0.9` → `parser(..., addressed=)` →
  `_listener_meta` (`lib/llc/parser.py`): addressed → «you» = tokeniko (uid bound); else the
  honest uid-less stub. The bind machinery is DONE — B changes what counts as addressed.

## Build

### 1. The momentum grade — `senses/inbound.py`

A channel message that would grade AMBIENT (0.6) inherits from the open exchange instead:

- New `_DIR_MOMENTUM = 0.85` (module constant beside its siblings, env-overridable like the rest
  if they are; match the file's existing pattern).
- The open-exchange check (a small helper, e.g. `_in_open_exchange(msg) -> bool`): within
  `MOMENTUM_WINDOW_S` (env, default **600**) in the SAME channel (`metadata.channel_id`), the
  memory timeseries holds either (a) an item from THIS author with directedness ≥ 0.9 (he was
  just addressing tokeniko), or (b) an outbound item from tokeniko targeted at this author
  (tokeniko was just talking to him). Derived from the timeseries — never stored state (the
  open-why derivation principle; `senses` has Mongo, the brain's RAM ring is not reachable and
  must not be).
- Scope: the lift applies ONLY to the ambient grade. DM stays 1.0; explicit addressing stays
  0.9; a reply into someone ELSE's thread stays 0.15 — an explicit signal beats momentum (that
  is the human rule too, and it keeps the fragolina misunderstanding faithful: kotekino's
  follow-up was plain channel talk, not a reply to fragolina).

### 2. The bind bar — `api/main.py`

`ADDRESSED_BAR` (env, default **0.75**) replaces the hardwired `0.9` in the `/input` addressed
mapping (both parser call sites — the original and the normalized re-parse use the same flag).
Momentum (0.85) and explicit addressing (0.9, 1.0) clear it; ambient (0.6) and others-thread
(0.15) do not. One comment: the bar is deliberately below momentum and above ambient.

### 3. Tests (sibling style; sandbox DB via conftest)

- Momentum grade: an ambient message with a recent (a)-seed row → 0.85; with a recent (b)-seed
  (tokeniko's outbound to the author) → 0.85; with neither, or the rows outside the window, or
  in a DIFFERENT channel_id → 0.6; a reply into someone else's thread stays 0.15 even with
  momentum present; DM stays 1.0.
- The bar: 0.85 → addressed True; 0.6 → False (test the mapping however the api seam is already
  tested — extract the one-liner into a testable helper if none exists).
- The binding specimen (parser-level, in the style of the parser test files): «so, what are
  you?» parsed with `addressed=True` compiles with `identities.subject` = tokeniko's uid and
  `wh_role=predicate` — the 2026-07-24 live specimen's cure, asserted at the zip. (The wh-solve
  answer from that zip is already covered by `test_identity_blindness.py` — do not duplicate.)
- Full gate green (all passed, 1 xfailed standing normal), foreground, `pgrep -f pytest` first.

## Design notes (context, not tasks)

- The stored `directedness` also multiplies behavior-rule urges at Priorities — the momentum
  lift therefore ALSO makes him a more engaged participant mid-dialogue. That is intended: this
  build PROMOTES the parked «conversation momentum» item (its promote condition — «when the
  missing lift is actually felt» — was felt today as the pronoun defect). The parked.md
  reconciliation is the QM's, not yours.
- Wider coreference (it/he/she, cross-speaker) stays parked — out of scope.

## Out of scope (do NOT build; report if tempted)

- Anything in lead A's files (`lib/llc/normalizer.py`, the rag registry) — a sibling build owns
  them. The blog-consensus brief (queued separately). No commits, no daemon restarts, no
  status-doc edits.

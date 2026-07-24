# Brief: blog consensus-over-the-polisher — the line-aligned polish (2026-07-24)

**To the 1st Officier, from the QM.** Roadmap §1's last tail item, designed with the Captain
today. DO NOT start while another officer build is un-committed in the tree; the QM dispatches
this explicitly. The laws of the ship (`.claude/agents/first-officer.md`) apply in full.

## The gap and the ruling

The blog's `polish()` (`senses/blog.py`) is one blind cloud call — structural checks only;
nothing proves the polished body still MEANS what the draft meant. Chat replies already ride the
rag2-out consensus (`senses/outbound.py:_voice_out` → `/api/v1/voice/verify` → polished only if
the zip-equivalence holds). The Captain's ruling: hold the blog to the same contract, via a
**line-aligned polish** — the whole-body compile would be a constant false-failure machine, and
post-hoc sentence alignment is an error swamp, so the polish contract itself changes instead.

Ruled forks: **per-line mixed acceptance** (a failing line ships verbatim beside polished
neighbors — safe by construction, each line independently meaning-true) · **title + excerpt are
presentation** (condensation, not 1:1-alignable — they stay polished-unverified; the body carries
the claims; the raw-render title remains the fallback) · **proof lines are polished + verified
exactly like fact lines** (uniform; they are scaffold-authored, no register exemption).

## Build

### 1. The rag spec — `lib/rag/registry.py` `BLOG_POLISH`

- Schema: `body` (free paragraph array) becomes `lines`: an array of strings **aligned 1:1, same
  order, with the input lines** (facts then proof — exactly as `_polish_user_prompt` serializes
  them). `title` + `excerpt` stay.
- System prompt: rewrite the output contract accordingly — one polished line per given line, same
  order, no merging/splitting/reordering; each line remains a complete standalone sentence; all
  existing hard rules (first person, NO new facts, people-as-given, the plain curious voice)
  stay. Keep the header comment's cross-reference note honest (spec + `_polish_user_prompt`
  edited together).

### 2. The polish — `senses/blog.py`

- `polish(draft)` reworked:
  1. One cloud call as today (`rag_call(BLOG_POLISH, …)`).
  2. **Alignment guard**: `len(lines) != len(draft.facts) + len(draft.proof)` → structural
     failure → the existing raw-render fallback (unchanged pattern).
  3. **Per-line consensus**: for each `(raw_line, polished_line)` pair — identical → keep raw (no
     verify spent); else call the verify seam; `ok` → polished line; rejected, unverifiable, or
     verify unreachable → **raw line verbatim** (graceful, mirrors `_voice_out` exactly).
  4. Body = the verified line sequence assembled with the same paragraph structure the raw render
     uses (facts, then proof) — so a fully-rejected polish is byte-close to the raw render.
  5. `title`/`excerpt` from the polisher as-is (presentation ruling); existing client-side
     structural checks stay.
- The verify seam: reuse `senses/outbound.py:_verify_voice` — either import it or (cleaner, your
  call) lift it into a tiny shared `senses/voicegate.py` consumed by both; do NOT duplicate the
  function. It is sync — call it off-thread as `_voice_out` does (`asyncio.to_thread`).
- `polished` in the transmission contract stays a bool (the site reads it): True iff ≥1 line
  shipped polished. Log the ratio (e.g. `[blog] polish consensus: 4/5 lines verified`).
- `RAG2_OUT_DISABLED` does not govern the blog; keep the blog's own existing enable/fallback
  semantics (`rag_call` graceful-None already covers the cloud being off).

### 3. Tests — extend the existing blog test file (same style, stubbed cloud + stubbed verify)

Cover at least: aligned polish fully verified → all lines polished, `polished=True` · one line
rejected → that line verbatim, neighbors polished (the mixed body), `polished=True` · all
rejected → body ≡ raw-render lines, `polished=False` · line-count mismatch → raw-render fallback ·
identical line → no verify call spent · verify unreachable → raw lines, never an exception ·
title/excerpt ride from the polisher untouched · proof lines go through the same per-line gate.
Existing blog tests stay green (raw render + transmission contract unchanged).

### 4. The gate

Targeted first (the blog test file), then the FULL gate — foreground, per your contract; check
`pgrep -f pytest` first. Done = full gate green (all passed, 1 xfailed is the standing normal).

## Out of scope (do NOT build; report if tempted)

- The `life:learned` / `life:discussion` blog triggers (a separate pending follow-on).
- Any change to the transmission contract shape, the website, or the digest machinery.
- No commits, no daemon restarts, no status-doc edits (the QM reconciles).

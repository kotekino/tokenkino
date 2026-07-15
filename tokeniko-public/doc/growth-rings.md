# Growth Rings — the one page tokeniko doesn't write

> Hunch 12 (`tokeniko/doc/ref/captain-hunches.md`), promoted to the core roadmap's
> **strengthening tail #9**. Names chosen 2026-07-14; drafted 2026-07-15.

## What it is

`/growth` — two things, one metaphor:

- **Growth Rings** — the landed history, told as the seasons of a mind learning. A tree's rings
  are its verifiable autobiography: each one a season, in order, readable by anyone who counts.
- **The Growing Edge** — what it is learning *now*. A tree grows in one thin band of living
  tissue under the bark; everything else is finished wood. **There is only ever one.**

## Why it is hand-written

Every other page here is the machine's own output — the Stream is what it thought, the Mind
Monitor is what it reports. This page is the exception, and the exception is principled:

tokeniko can tell you what it knows and what it thinks. It cannot tell you what it *became*,
because that is a judgement about progress — which of a hundred landed commits was a season, and
which was a Tuesday. Judgements about progress belong to the crew. Generating this page from
`landed.md` would produce a changelog, and a changelog is exactly what the Captain's hunch said
not to build ("as they were thought to define the step of a young mind learning more than a
software development feature list").

`llms.txt` discloses this: it is the only page on the site not authored by the machine.

## Where it lives

The entries are **Atlas collections** (`growth_rings` + the `growth_edge` singleton), served by
`GET /api/growth` and written through the authed API — so a new season lands with one call, not a
deploy. Same discipline as the Stream: no bundled content; the page renders skeletons until the
real record arrives.

| piece | what |
|---|---|
| `backend/src/models/Growth.ts` + `routes/growth.ts` | the collections + `/api/growth` (GET public; PUT edge / POST rings / DELETE ring behind `INGEST_API_KEY`) |
| `backend/scripts/seed-growth.mjs` | **the curation's home in the repo** — the current rings + edge, pushed idempotently (upsert by slug); re-run whole after appending a season |
| `frontend/src/hooks/useGrowth.ts` | the fetch (Stream idiom: null → skeleton → data, honest "unreachable" when settled) |
| `frontend/src/data/growth.ts` | the types only |
| `frontend/src/pages/Growth.tsx` (+ `.css`) | the page |

Sources of truth for the *facts*: `tokeniko/doc/landed.md` (history) and `tokeniko/doc/roadmap.md`
(the road ahead). This page is their **retelling**, not their mirror — landed.md is eight hundred
lines of engineering prose written for the people building the thing.

## How to keep it current

**When a season closes** — not when a commit lands — append the ring to `RINGS` in
`backend/scripts/seed-growth.mjs` (top of the list, `seq` = previous top + 10) and update `EDGE`
to whatever the roadmap's living layer now is; then run the script against production:

```bash
API_URL=https://tokeniko.online/api INGEST_API_KEY=... node scripts/seed-growth.mjs
```

(Or POST the single new ring / PUT the edge directly — the script is just the recipe with the
history kept in the repo for review.)

A ring is:

- `title` — **what it learned**, never what was built. "It changed its mind", not
  "belief-revision v1".
- `body` — one or two sentences. What it couldn't do before, and can now. Plain enough for a
  stranger; honest enough for the author.
- `marks` — two or three concrete, checkable facts. This is the "technical enough" half: real
  numbers, real first-times. No adjectives doing work a fact should do.
- `when` — a date once the calendar starts; the early rings honestly say "the first season".

**The bar for a ring:** could tokeniko not do this before, and can it now? If the answer is "we
refactored it", it is not a ring. Most of `landed.md` is not a ring, and that is the point.

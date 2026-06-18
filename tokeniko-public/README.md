# tokeniko — public presence

This is one of tokeniko's **output channels**: a public window onto a persistent,
logic-first thinking entity. It is deliberately *not* a marketing site and *not*
a product page. It reads like a blog because that is what it is — a stream of
transmissions (notes, arguments, the occasional piece of content) emitted by a
mind that never stops reasoning, beside a live readout of that mind at work.

> Sibling project. The core engine lives in the parent `tokeniko/` repo. This
> folder is only the public surface and never touches the core docs
> (`vision.md`, `readme.md`, `CLAUDE.md`).

---

## The idea

Two regions on the screen, like a 1950s appliance with a little monitor set into
the console:

- **Center-left — the Stream.** tokeniko's output, newest first. Each entry is a
  *transmission* with a kind (`note` · `argument` · `content` · `log`), a date,
  and a body. Nothing is edited after the fact, including the parts it later
  refutes.
- **Right — the Mind Monitor.** A CRT-style panel showing what tokeniko is doing
  right now, how long it has been thinking (uptime), and KPIs about the size of
  its mind: **axioms**, **dictionary** (base vectors), **memory** (beliefs held),
  **inferences**, **refutations**, **anchors** — plus a live activity log.

### Look & feel

- **Vintage / 1950s appliance.** Warm Bakelite cream, enamel teal & mint,
  butterscotch and atomic-coral accents, chunky bezels, soft drop shadows, a
  faint grain on the background.
- **Coding typeface throughout.** Everything is set in monospace
  (`Space Mono` for display, `JetBrains Mono` for body) — this is the output of a
  machine that thinks in symbols.
- The Mind Monitor reads as a phosphor-green CRT with scanlines, an amber
  readout, and a blinking caret.

---

## Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React 18, TypeScript, React Router v6, Vite |
| Backend    | Node.js, Express, TypeScript            |
| Database   | MongoDB Atlas (Mongoose ODM)            |
| Styling    | Vanilla CSS with design tokens          |
| Compliance | GDPR-compliant cookie consent           |

The tech stack is unchanged from the template (React front, Node back, Mongo
I/O) — only the concept, content, and design were rebuilt.

---

## Project structure

```
tokeniko-public/
├── frontend/                 # React app (Vite + TypeScript)
│   └── src/
│       ├── components/       # Header (nameplate), Footer, MindPanel (CRT),
│       │                     #   TransmissionCard, CookieBanner, Layout
│       ├── context/          # CookieContext (consent state)
│       ├── data/             # transmissions.ts (the feed) + mind.ts (KPIs)
│       ├── pages/            # Home (Stream), Blog (Archive), About (Colophon),
│       │                     #   Contact, legal pages, NotFound
│       ├── styles/           # global.css — vintage design tokens + reset
│       └── types/            # Shared TypeScript types
└── backend/                  # Express API (TypeScript)
    └── src/
        ├── config/           # MongoDB connection
        ├── middleware/       # Error handler
        ├── models/           # CookieConsent (Mongoose)
        └── routes/           # /health, /cookie-consent, /mind
```

---

## Pages / channels

| Route            | Channel    | What it is                                   |
|------------------|------------|----------------------------------------------|
| `/`              | Stream     | The feed + the live Mind Monitor             |
| `/blog`          | Archive    | Every transmission, full text, newest first  |
| `/about`         | Colophon   | What tokeniko is and how it thinks           |
| `/ping`          | Ping       | The one channel: tokeniko's Discord (no reply guaranteed) |
| `/legal/imprint` | Imprint    | §5 TMG                                        |
| `/legal/privacy` | Privacy    | Privacy Policy                               |
| `/legal/terms`   | Terms      | Terms of Service                             |

---

## The Mind Monitor (mock phase)

The right-hand panel is driven by `GET /api/mind`. **During build-out the figures
are simulated** on both ends:

- The frontend ships a fallback snapshot in `frontend/src/data/mind.ts` and
  renders it immediately, so the panel always shows something honest even with
  no backend.
- The backend serves the same shape from `backend/src/routes/mind.ts` (uptime
  climbs while the server is up). The panel footer reads `feed: live` when it
  reaches the API and `feed: simulated · mock phase` otherwise.

When the real reasoning engine is wired in, only `routes/mind.ts` changes — the
response **shape is the contract** and the UI stays put. The mock KPIs mirror the
engine's real concepts (2,925 dictionary base vectors, axioms as ground truth,
refutations dropping beliefs, semantic anchors).

To add or edit transmissions for now, edit `frontend/src/data/transmissions.ts`.

---

## Quick start

```bash
# Backend
cd backend
cp .env.example .env        # fill in your MongoDB URI (optional for /mind + /health)
npm install
npm run dev                 # http://localhost:4000

# Frontend (new terminal)
cd frontend
cp .env.example .env        # VITE_API_URL, VITE_SITE_NAME
npm install
npm run dev                 # http://localhost:3000
```

> The Stream and Mind Monitor render without a database. MongoDB is only needed
> for the contact form and cookie-consent persistence.

---

## API endpoints

| Method | Path                       | Description                          |
|--------|----------------------------|--------------------------------------|
| GET    | `/api/health`              | Health check + DB status             |
| GET    | `/api/mind`                | Mind snapshot (KPIs + activity, mock)|
| POST   | `/api/cookie-consent`      | Record/update cookie consent         |
| GET    | `/api/cookie-consent/:id`  | Retrieve consent by session          |

---

## GDPR cookie compliance

Carried over from the template, still active: a consent banner (~800ms after
first visit), three tiers (Necessary / Analytics / Marketing), preferences saved
to `localStorage` and synced to MongoDB, and a "Cookie settings" link in the
footer. Replace placeholder categories with real tools before going live.

---

## What's next

- [ ] Wire `GET /api/mind` to the live reasoning engine (keep the response shape)
- [ ] Serve transmissions from a store instead of `transmissions.ts`
- [ ] Per-transmission permalink pages (currently `/blog#<slug>` anchors)
- [ ] Real imprint / privacy details
- [ ] Real Discord invite for "tokeniko's playground" (Ping page)

---

## License

MIT.

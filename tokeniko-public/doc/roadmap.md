# tokeniko-public — roadmap

The **public website's** own roadmap — distinct from the core engine roadmap
(`tokeniko/doc/roadmap.md`). This covers the cloud site: the Stream, the Mind Monitor, the
ingestion API, and the publish seam to the embodied brain.

Legend: ✅ done · 🔄 in progress · 🔭 next · ⏸️ parked

---

## ✅ Landed

**Look & identity**
- Vintage 1950s-appliance design system; CRT Mind Monitor; coding-font typography.
- Brand CI alignment: official **`tk` emblem** (primary/reverse colourways), **synapse** device,
  **12-glyph icon set**, palette named to the CI (`ci/tokeniko CI.html`). Favicon/og set; "a
  thinking machine" tagline; Made in Japan.

**Frontend (mock phase)**
- **Stream** (transmission feed) + **Mind Monitor** (KPIs, uptime, activity) + **Signal Scope**
  (inferences sparkline + beliefs bars), all on local fallbacks (`data/*.ts`).
- **Ping** (Discord channel), **Colophon**, personal-project **Imprint**, cookie-consent menu.

**Backend — ingestion API** (this milestone)
- Mongo models: `mind_snapshots` (**timeseries** archive), `mind_current` (singleton), `transmissions`.
- `POST /api/mind` (raw metrics → backend-derived KPIs/trend/sparkline), `GET /api/mind` (current,
  mock fallback), `GET /api/mind/history` (archive).
- Transmissions REST: `GET` list/`:slug`, `POST` (idempotent upsert by slug), `DELETE`.
- **Bearer-key** auth on writes (`requireIngestKey`); reads public. Hardened DB connect
  (timeseries ensured, serves fallbacks if DB down). Verified end-to-end against Mongo 7.
- Contract documented in `doc/ingestion-api.md`.

**Frontend live-wiring + coming-soon + deploy** (this milestone)
- **Live data via backend**: `useMind` + `useTransmissions` hooks read `/api/mind` +
  `/api/transmissions`; `MindPanel`/`MindCharts` are prop-driven; Stream/Archive render fetched
  data. Curated bundled data stays the **fallback** (empty Atlas still looks good); the
  "feed: live / simulated" footer flips automatically on real data.
- **Coming-soon page** (`/soon`): standalone, on-brand (emblem, teasers of the Stream / Mind
  Monitor / Signal Scope, Discord CTA) + a `VITE_COMING_SOON` gate flag (default OFF).
- **Azure deploy ready**: zero-dep SPA server (`frontend/server.cjs`, SPA fallback), `engines`
  + prod `start` scripts, comma-separated `CORS_ORIGIN`. Full strategy in `doc/deploy-azure.md`.

---

## 🔭 Next (ordered)

1. **First full publication to Azure** — two App Services per `doc/deploy-azure.md`; run the smoke
   tests (esp. the authed `POST /api/mind` to prove Atlas + ingestion live).
2. **Brain push side (local).** The other agent implements the actions-loop publish against
   `doc/ingestion-api.md` (snapshots periodically; transmissions on `tokeniko:post`). Shared
   `INGEST_API_KEY`.
3. **Coming-soon gating.** Once the full publication is verified, flip `VITE_COMING_SOON=1` so the
   coming-soon page is the only visible page until launch.
4. **Social card.** Add `public/og-image.png` (1200×630) — re-export from the brand tool with the
   "a thinking machine" tagline; the meta tags already point at it.
5. **Analytics + cookies.** Wire GA (or a privacy-respecting alternative) behind the existing
   opt-in consent; fill the cookie/data note in the Imprint.

## ⏸️ Parked

- Per-transmission permalink pages (currently `/blog#slug` anchors) + pagination on the list.
- Snapshot **TTL / downsampling** on `mind_snapshots` once the archive grows; richer stats views
  off `GET /api/mind/history`.
- Multi-body `meta.body` tagging (future "species") on snapshots/transmissions.
- Ingestion key **rotation** + optional IP allowlist for the brain's egress.

---

## Doc map

- `README.md` — the site's concept + stack + structure.
- `doc/roadmap.md` — *(this)* the public-site status.
- `doc/ingestion-api.md` — the brain↔site publish contract (for the local push agent).
- `doc/deploy-azure.md` — the Azure App Service deploy strategy + smoke tests.
- Core engine docs live in the sibling `tokeniko/` package (`VISION.md`, `CLAUDE.md`,
  `doc/roadmap.md`).

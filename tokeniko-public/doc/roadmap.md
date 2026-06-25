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

---

## 🔭 Next (ordered)

1. **Wire the frontend to the live API.** `MindPanel` + `MindCharts` read `GET /api/mind`
   (one fetch, use `data.charts`); the Stream/Archive read `GET /api/transmissions`. Keep the
   local fallbacks as the offline/empty state; flip the "feed: live" indicator on real data.
   Optional light polling for the monitor.
2. **Brain push side (local).** The other agent implements the actions-loop publish against
   `doc/ingestion-api.md` (snapshots periodically; transmissions on `tokeniko:post`). Shared
   `INGEST_API_KEY`.
3. **Deploy.** Backend on the cloud against the public Atlas; `CORS_ORIGIN=https://tokeniko.online`;
   set the real `INGEST_API_KEY`. Front end at `tokeniko.online`.
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
- Core engine docs live in the sibling `tokeniko/` package (`VISION.md`, `CLAUDE.md`,
  `doc/roadmap.md`).

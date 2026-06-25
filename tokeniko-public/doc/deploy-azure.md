# Deploying tokeniko-public to Azure App Service

The first **full** publication: **two Azure App Services** (Linux, Node 20) — the **backend**
(Express API → public Atlas) and the **frontend** (the Vite SPA, served by a tiny zero-dep Node
server). No Docker. Goal: prove the whole chain live, especially **Atlas connectivity** and the
**ingestion endpoints**.

> **Domain association is done by you in the Azure portal.** This doc uses placeholders:
> `FRONT_URL` (e.g. `https://tokeniko.online` or the default `*.azurewebsites.net`) and
> `API_URL` (e.g. `https://tokeniko-api.azurewebsites.net`).

---

## 0. Prerequisites

- Azure subscription + `az` CLI (`az login`).
- The public **Atlas** connection string, and Atlas **Network Access** allowing the App Service
  to connect — simplest for the first publication: allow `0.0.0.0/0` (or add the backend's
  outbound IPs from *App Service → Networking → outbound addresses*).
- A strong `INGEST_API_KEY` (the same secret the brain will use).

```bash
RG=tokeniko-rg
LOC=japaneast            # close to home; any region is fine
PLAN=tokeniko-plan
API_APP=tokeniko-api     # → https://tokeniko-api.azurewebsites.net
WEB_APP=tokeniko-web     # → https://tokeniko-web.azurewebsites.net (map tokeniko.online later)

az group create -n $RG -l $LOC
az appservice plan create -g $RG -n $PLAN --is-linux --sku B1
```

---

## 1. Backend App Service (the API)

Already deploy-ready: `build` = `tsc`, `start` = `node dist/index.js`, `engines.node >=20`.
Azure's Oryx builder runs `npm install && npm run build` on deploy, then `npm start`.

```bash
az webapp create -g $RG -p $PLAN -n $API_APP --runtime "NODE:20-lts"

az webapp config appsettings set -g $RG -n $API_APP --settings \
  NODE_ENV=production \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  MONGODB_URI="<your atlas SRV string>" \
  MONGODB_DB="tokeniko_public" \
  INGEST_API_KEY="<the shared secret>" \
  MIND_TREND_WINDOW=12 \
  CORS_ORIGIN="FRONT_URL"          # comma-separated to allow several origins

# Health-check probe
az webapp config set -g $RG -n $API_APP --generic-configurations '{"healthCheckPath":"/api/health"}'

# Deploy from the backend folder (zip-deploy with Oryx build)
cd tokeniko-public/backend
az webapp up -g $RG -n $API_APP --runtime "NODE:20-lts"
```

App Service injects `PORT` — the code already reads `process.env.PORT`. `CORS_ORIGIN` accepts a
**comma-separated list**, so you can list both the default `*.azurewebsites.net` URL and
`https://tokeniko.online`.

---

## 2. Frontend App Service (the SPA)

`VITE_API_URL` is **baked at build time**. Set it as an app setting and let Oryx build on deploy,
so the bundle points at the live API. `server.cjs` serves `dist/` with SPA fallback.

```bash
az webapp create -g $RG -p $PLAN -n $WEB_APP --runtime "NODE:20-lts"

az webapp config appsettings set -g $RG -n $WEB_APP --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  VITE_API_URL="API_URL/api" \
  VITE_SITE_NAME=tokeniko
  # VITE_COMING_SOON=1   ← later, to make the coming-soon page the ONLY page

cd tokeniko-public/frontend
az webapp up -g $RG -n $WEB_APP --runtime "NODE:20-lts"
```

`npm start` runs `node server.cjs` (zero deps) → deep links like `/ping` survive refresh.

> If you'd rather not build on Azure: run `VITE_API_URL=API_URL/api npm run build` locally and
> zip-deploy `dist/` + `server.cjs` + `package.json` (set `SCM_DO_BUILD_DURING_DEPLOYMENT=false`).

---

## 3. Wire the two together

- **Backend `CORS_ORIGIN`** must include the frontend's public origin(s) — update it whenever you
  map a new domain (e.g. `https://tokeniko-web.azurewebsites.net,https://tokeniko.online`).
- **Frontend `VITE_API_URL`** must point at the backend (rebuild if the API domain changes).
- **Custom domain** (you, in the portal): map `tokeniko.online` → the frontend app; optionally map
  `api.tokeniko.online` → the backend app, then update `VITE_API_URL` + `CORS_ORIGIN` to match and
  redeploy the frontend.

---

## 4. Post-deploy smoke tests

```bash
API=API_URL ; KEY="<INGEST_API_KEY>"

# 1. backend health + DB status
curl -s $API/api/health | jq

# 2. current mind (mock fallback until the brain pushes)
curl -s $API/api/mind | jq '.data.kpis[0]'

# 3. prove Atlas WRITE + the ingestion auth (this is the key test)
curl -s -X POST $API/api/mind -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $KEY" \
  -d '{"state":"thinking","doing":"first live breath","uptimeSec":1,
       "metrics":{"definitions":3235,"axiomsRules":14,"theorems":6,"dictionary":2925,
                  "chains":4902,"anchors":128,"inferencesPerCycle":40},
       "beliefsByDomain":[{"label":"logic","value":47}],
       "activity":[{"at":"2026-06-25T09:00:00Z","text":"hello, world"}]}'
# → 201 ; then GET /api/mind shows live KPIs, and the frontend footer flips to "feed: live"

# 4. a transmission
curl -s -X POST $API/api/transmissions -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $KEY" \
  -d '{"slug":"hello","kind":"log","title":"Hello","excerpt":"first transmission","body":["…"]}'

# 5. auth must fail without the key → 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST $API/api/mind -d '{}'
```

Then open `FRONT_URL`: empty Atlas → curated fallback (footer "simulated"); after step 3–4 →
the Mind Monitor / Signal Scope / Stream show **live** data. Visit `FRONT_URL/soon` to preview
the coming-soon page.

---

## 5. Optional — GitHub Actions (instead of `az webapp up`)

Per app, using a publish profile saved as a repo secret (`AZURE_*_PUBLISH_PROFILE`). Build in CI,
deploy the folder. Sketch for the frontend (backend mirrors it with its own folder/app + no
`VITE_*`):

```yaml
name: deploy-frontend
on: { push: { branches: [main], paths: ['tokeniko-public/frontend/**'] } }
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: tokeniko-public/frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run build
        env: { VITE_API_URL: ${{ vars.VITE_API_URL }} }
      - uses: azure/webapps-deploy@v3
        with:
          app-name: tokeniko-web
          publish-profile: ${{ secrets.AZURE_WEB_PUBLISH_PROFILE }}
          package: tokeniko-public/frontend
```

---

## Notes

- The existing `Dockerfile`s / `docker-compose.yml` / `nginx.conf` are **unused** by this App
  Service path — kept for a future container route.
- Rate limit: the brain's push cadence must stay under `RATE_LIMIT_MAX` (default 100 / 15 min per
  IP) or raise it for the brain's egress.
- Making coming-soon the **only** page is a later, deliberate step: set `VITE_COMING_SOON=1` on the
  frontend app and redeploy/rebuild.

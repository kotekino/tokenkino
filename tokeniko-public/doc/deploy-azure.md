# Deploying tokeniko-public to Azure App Service

Two **Azure App Services** (Linux, **Node 22-lts**) — the **backend** (Express API → public Atlas)
and the **frontend** (the Vite SPA, served by a tiny zero-dep Node server). No Docker.

> This reflects what actually worked for the first publication (live at
> `tokeniko-{api,web}.azurewebsites.net`). **Build locally and deploy prebuilt artifacts with the
> server-side build OFF** — the Oryx/Kudu git build stalled on the B1 tier, and a prebuilt deploy
> is faster and deterministic. **Domain association is done in the Azure portal** (placeholders:
> `FRONT_URL`, `API_URL` e.g. `https://tokeniko-api.azurewebsites.net`).

---

## 0. Prerequisites

- Azure subscription + `az login`.
- **Atlas → Network Access must allow the App Service.** This was *the* gotcha: "works from my
  laptop, `disconnected` from the server" = the allowlist had the local IP only. Add **`0.0.0.0/0`**
  (simplest) or the app's outbound IPs (`az webapp show … --query possibleOutboundIpAddresses`).
- A strong `INGEST_API_KEY` (the same secret the brain uses).

```bash
RG=tokeniko-rg
LOC=westeurope           # central Europe (Netherlands). Alt: germanywestcentral, francecentral
PLAN=tokeniko-plan
API_APP=tokeniko-api     # → https://tokeniko-api.azurewebsites.net
WEB_APP=tokeniko-web     # → https://tokeniko-web.azurewebsites.net (map tokeniko.online later)

az group create -n $RG -l $LOC
az appservice plan create -g $RG -n $PLAN --is-linux --sku B1
az webapp create -g $RG -p $PLAN -n $API_APP --runtime "NODE:22-lts"
az webapp create -g $RG -p $PLAN -n $WEB_APP --runtime "NODE:22-lts"
```

---

## 1. App settings

Build is **off** on both (we deploy prebuilt). The frontend's `VITE_API_URL` is baked at *local*
build time (below), so it isn't needed as a runtime setting.

```bash
# Backend
az webapp config appsettings set -g $RG -n $API_APP --settings \
  NODE_ENV=production \
  SCM_DO_BUILD_DURING_DEPLOYMENT=false \
  MONGODB_URI="<atlas SRV string>" \
  MONGODB_DB="tokeniko_public" \
  INGEST_API_KEY="<the shared secret>" \
  MIND_TREND_WINDOW=12 \
  CORS_ORIGIN="https://tokeniko-web.azurewebsites.net,https://tokeniko.online,https://www.tokeniko.online"
az webapp config set -g $RG -n $API_APP --startup-file "node dist/index.js" \
  --generic-configurations '{"healthCheckPath":"/api/health"}'

# Frontend
az webapp config appsettings set -g $RG -n $WEB_APP --settings SCM_DO_BUILD_DURING_DEPLOYMENT=false
az webapp config set -g $RG -n $WEB_APP --startup-file "node server.cjs"
```

`CORS_ORIGIN` is a **comma-separated** list (the code allows any listed origin). App Service injects
`PORT`; both the API and `server.cjs` read `process.env.PORT`.

---

## 2. Build locally + deploy (prebuilt, build OFF)

**Backend** — compile, install prod deps, zip `{dist, node_modules, package.json}`:

```bash
cd tokeniko-public/backend
npm install && npm run build                 # tsc → dist/
rm -rf .deploy && mkdir .deploy
cp -R dist package.json package-lock.json .deploy/
( cd .deploy && npm install --omit=dev )     # prod-only node_modules (pure-JS deps → portable)
( cd .deploy && zip -qr ../api.zip . )
az webapp deploy -g $RG -n $API_APP --src-path api.zip --type zip
```

**Frontend** — build with the live API baked in, zip `{dist, server.cjs, package.json}` (the
server is zero-dep, so no `node_modules`):

```bash
cd tokeniko-public/frontend
VITE_API_URL="API_URL/api" npm install && VITE_API_URL="API_URL/api" npm run build
rm -rf .deploy && mkdir .deploy
cp -R dist server.cjs package.json .deploy/
( cd .deploy && zip -qr ../web.zip . )
az webapp deploy -g $RG -n $WEB_APP --src-path web.zip --type zip
```

> **If `az webapp deploy` returns a 502/504 gateway error**, it's usually just the SCM tracking
> layer timing out on B1 — the deploy often still lands. Restart (`az webapp restart`) to clear a
> wedged SCM, then push straight through Kudu and poll:
> ```bash
> U=$(az webapp deployment list-publishing-credentials -g $RG -n $API_APP --query publishingUserName -o tsv)
> P=$(az webapp deployment list-publishing-credentials -g $RG -n $API_APP --query publishingPassword -o tsv)
> curl -X POST -u "$U:$P" --data-binary @api.zip -H 'Content-Type: application/zip' \
>   "https://$API_APP.scm.azurewebsites.net/api/zipdeploy?isAsync=true"
> # poll https://$API_APP.scm.azurewebsites.net/api/deployments/latest  (status 4 = success)
> ```

The backend connects to Mongo **non-blocking** and retries, so it starts fast and **self-heals**:
if you open the Atlas allowlist *after* it booted, just `az webapp restart -g $RG -n $API_APP`.

---

## 3. Custom domains (portal) + re-point

Map `tokeniko.online → $WEB_APP` and `api.tokeniko.online → $API_APP`. CORS already lists
`tokeniko.online`. Then rebuild the frontend with **`VITE_API_URL=https://api.tokeniko.online/api`**
and redeploy (step 2). The brain already targets `api.tokeniko.online`, so it publishes as soon as
that domain resolves.

---

## 4. Post-deploy smoke tests

```bash
API=API_URL ; KEY="<INGEST_API_KEY>"
curl -s $API/api/health                         # → "database":"connected"
curl -s $API/api/mind        | head -c 200      # current snapshot
curl -s -o /dev/null -w '%{http_code}\n' -X POST $API/api/mind -d '{}'   # → 401 (auth works)
```

**Seed the curated mock content** (same Stream + Mind data the frontend ships as fallback):

```bash
API_BASE="$API/api" INGEST_API_KEY="$KEY" node tokeniko-public/scripts/seed-public.mjs
```

Open `FRONT_URL`: with data seeded, the Mind Monitor / Signal Scope / Stream read **live** (footer
"feed: live"); empty Atlas falls back to the curated content ("simulated"). `FRONT_URL/soon`
previews the coming-soon page.

---

## Notes

- **Diagnostics:** read app stdout at `…scm.azurewebsites.net/api/vfs/LogFiles/*_containerStream.log`;
  run a command in the container via `POST …/api/command {"command","dir"}` (no shell — wrap shell
  syntax in `bash -c "…"`). Note App Service runs the app from `/tmp/zipdeploy/extracted`, not
  `wwwroot`.
- **Pure-JS deps** (express, mongoose, …) make the locally-built `node_modules` portable to Linux;
  a native addon would need a Linux build (or server-side `npm install`).
- The existing `Dockerfile`s / `docker-compose.yml` / `nginx.conf` are **unused** by this path.
- Rate limit: keep the brain's push cadence under `RATE_LIMIT_MAX` (default 100 / 15 min per IP).
- Coming-soon as the **only** page: set `VITE_COMING_SOON=1`, rebuild + redeploy the frontend.
```

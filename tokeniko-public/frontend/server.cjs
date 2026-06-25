/**
 * Production static server for the tokeniko-public SPA (Azure App Service, Node).
 *
 * Zero dependencies (Node built-ins only): serves the Vite `dist/` build, returns
 * index.html for any client route (SPA fallback, so /ping, /about… survive a
 * refresh), sets long-cache on hashed assets and no-cache on HTML, and guards
 * against path traversal. App Service runs `npm start` → `node server.cjs`.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const DIST = path.join(__dirname, 'dist');
const INDEX = path.join(DIST, 'index.html');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
  '.map': 'application/json; charset=utf-8',
};

const send = (res, status, body, headers) => {
  res.writeHead(status, headers || {});
  res.end(body);
};

function serveFile(file, res, isFallback) {
  fs.readFile(file, (err, data) => {
    if (err) return send(res, 404, 'Not found');
    const ext = path.extname(file).toLowerCase();
    const type = MIME[ext] || 'application/octet-stream';
    // Vite emits hash-fingerprinted asset names → safe to cache forever.
    const hashed = /-[A-Za-z0-9_-]{8,}\.[a-z0-9]+$/.test(path.basename(file));
    const cache =
      isFallback || ext === '.html'
        ? 'no-cache'
        : hashed
        ? 'public, max-age=31536000, immutable'
        : 'public, max-age=3600';
    send(res, 200, data, { 'Content-Type': type, 'Cache-Control': cache });
  });
}

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  if (urlPath.includes('\0')) return send(res, 400, 'Bad request');

  const resolved = path.normalize(path.join(DIST, urlPath));
  if (resolved !== DIST && !resolved.startsWith(DIST + path.sep)) {
    return send(res, 403, 'Forbidden');
  }

  fs.stat(resolved, (err, stat) => {
    if (!err && stat.isFile()) return serveFile(resolved, res, false);
    serveFile(INDEX, res, true); // SPA fallback (client routes)
  });
});

server.listen(PORT, () => {
  console.log(`tokeniko-public frontend serving ${DIST} on :${PORT}`);
});

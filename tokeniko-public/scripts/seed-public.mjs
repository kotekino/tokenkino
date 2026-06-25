#!/usr/bin/env node
/**
 * Seed the public Atlas (through the backend ingestion API) with the curated
 * mock content — the same Stream + Mind data the frontend ships as its
 * fallback. Useful to populate a fresh DB or re-seed after a wipe.
 *
 *   • Transmissions are idempotent (upsert by slug).
 *   • Mind snapshots append; the Signal Scope shows the last N, so re-running
 *     is harmless (just grows the archive).
 *
 * Targets the LOCAL backend by default. Override for a deployed instance:
 *
 *   API_BASE=https://tokeniko-api.azurewebsites.net/api \
 *   INGEST_API_KEY=… node tokeniko-public/scripts/seed-public.mjs
 *
 * When not given via env, INGEST_API_KEY + PORT are read from ../backend/.env.
 * Transmissions are loaded from the frontend source (single source of truth)
 * via esbuild — run with the repo's deps available (esbuild ships with the
 * frontend devDependencies).
 */
import { readFileSync } from 'fs';
import { execFileSync } from 'child_process';
import { fileURLToPath, pathToFileURL } from 'url';
import { dirname, join } from 'path';
import { tmpdir } from 'os';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..'); // tokeniko-public/

const fileEnv = (() => {
  try {
    return Object.fromEntries(
      readFileSync(join(root, 'backend', '.env'), 'utf8')
        .split('\n')
        .filter((l) => l && !l.trimStart().startsWith('#') && l.includes('='))
        .map((l) => { const i = l.indexOf('='); return [l.slice(0, i).trim(), l.slice(i + 1).trim()]; })
    );
  } catch {
    return {};
  }
})();

const KEY = process.env.INGEST_API_KEY || fileEnv.INGEST_API_KEY;
const PORT = process.env.PORT || fileEnv.PORT || 4000;
const API_BASE = process.env.API_BASE || `http://localhost:${PORT}/api`;
if (!KEY) {
  console.error('✗ Missing INGEST_API_KEY (set it in the env or backend/.env).');
  process.exit(1);
}

// Transmissions — loaded from the frontend source so this never drifts.
const out = join(tmpdir(), `tk-transmissions-${Date.now()}.mjs`);
execFileSync(
  'npx',
  ['esbuild', 'src/data/transmissions.ts', '--bundle', '--format=esm', `--outfile=${out}`, '--log-level=error'],
  { cwd: join(root, 'frontend'), stdio: 'inherit' }
);
const { transmissions } = await import(pathToFileURL(out).href);

const H = { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` };
const post = async (path, body, label) => {
  const r = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: H, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${label}: HTTP ${r.status} — ${await r.text()}`);
};

// Mind — a 12-cycle series mirroring the frontend MIND_FALLBACK. The final
// snapshot carries the full counts (+ activity/beliefs); earlier ones differ by
// one on the growing metrics so the ▲/▼ trend lands right on the current.
const spark = [38, 41, 36, 52, 48, 63, 59, 71, 66, 80, 77, 92];
const activity = [
  { at: '2026-06-21T09:41:12Z', text: 'followed a thought to its end — Mari is human, so Mari exists' },
  { at: '2026-06-21T09:41:09Z', text: 'caught a contradiction — “the door is open and not open” — and spoke up' },
  { at: '2026-06-21T09:41:02Z', text: 'told two people apart — Mari is not Luca' },
  { at: '2026-06-21T09:40:54Z', text: 'met a new word — guessed “flabbergasting” ≈ overwhelming, to confirm later' },
  { at: '2026-06-21T09:40:51Z', text: 'grounded “a raven is an animal” — raven → bird → animal' },
  { at: '2026-06-21T09:40:38Z', text: 'held the floor — refused a ≠ a' },
  { at: '2026-06-21T09:40:20Z', text: 'measured love against hate — 0.86, not opposites' },
];
const beliefs = [
  { label: 'vocabulary', value: 88 },
  { label: 'taxonomy', value: 61 },
  { label: 'logic', value: 47 },
  { label: 'self', value: 24 },
];

const now = Date.now();
for (let i = 0; i < spark.length; i++) {
  const final = i === spark.length - 1;
  const metrics = final
    ? { definitions: 3235, axiomsRules: 14, theorems: 6, dictionary: 2925, chains: 4902, anchors: 128, inferencesPerCycle: spark[i] }
    : { definitions: 3234, axiomsRules: 13, theorems: 5, dictionary: 2925, chains: 4901, anchors: 128, inferencesPerCycle: spark[i] };
  await post('/mind', {
    capturedAt: new Date(now - (spark.length - 1 - i) * 60000).toISOString(),
    state: 'thinking',
    doing: 'following a thought to its end — “Mari exists”',
    uptimeSec: 1_788_540,
    metrics,
    beliefsByDomain: beliefs,
    activity: final ? activity : [],
  }, `mind#${i}`);
}
console.log(`✓ ${spark.length} mind snapshots → ${API_BASE}`);

for (const t of transmissions) await post('/transmissions', t, `tx ${t.slug}`);
console.log(`✓ ${transmissions.length} transmissions → ${API_BASE}`);

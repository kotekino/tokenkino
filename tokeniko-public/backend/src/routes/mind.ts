import { Router, Request, Response } from 'express';

/**
 * GET /api/mind — a snapshot of tokeniko's mind for the public CRT panel.
 *
 * MOCK PHASE: figures are simulated here. When the reasoning engine is wired
 * in, this handler will read live counts (axioms, dictionary, memory, …) and
 * the recent activity log. The response SHAPE is the contract the frontend
 * already consumes (see frontend/src/data/mind.ts) — keep it stable.
 */

const router = Router();

// Process start, so uptime climbs realistically while the server is up.
const STARTED_AT = Date.now();
const BASE_UPTIME_SEC = 1_788_540; // pretend it has been thinking for a while

const seededActivity = (nowIso: string) => [
  { at: nowIso, text: 'followed a thought to its end — Mari is human, so Mari exists' },
  { at: nowIso, text: 'caught a contradiction — “the door is open and not open” — and spoke up' },
  { at: nowIso, text: 'told two people apart — Mari is not Luca' },
  { at: nowIso, text: 'met a new word — guessed “flabbergasting” ≈ overwhelming, to confirm later' },
  { at: nowIso, text: 'grounded “a raven is an animal” — raven → bird → animal' },
  { at: nowIso, text: 'held the floor — refused a ≠ a' },
  { at: nowIso, text: 'measured love against hate — 0.86, not opposites' },
];

router.get('/', (_req: Request, res: Response) => {
  const elapsedSec = Math.floor((Date.now() - STARTED_AT) / 1000);
  const now = new Date().toISOString();

  res.json({
    success: true,
    data: {
      doing: 'following a thought to its end — “Mari exists”',
      state: 'thinking',
      uptimeSec: BASE_UPTIME_SEC + elapsedSec,
      kpis: [
        { label: 'Definitions', value: '3,235', unit: 'vocabulary', trend: 1 },
        { label: 'Axioms & rules', value: '14', unit: 'ground truths', trend: 1 },
        { label: 'Theorems', value: '6', unit: 'derived', trend: 1 },
        { label: 'Dictionary', value: '2,925', unit: 'base vectors', trend: 0 },
        { label: 'Chains', value: '4,902', unit: 'multi-hop', trend: 1 },
        { label: 'Anchors', value: '128', unit: 'semantic', trend: 0 },
      ],
      activity: seededActivity(now),
    },
  });
});

export default router;

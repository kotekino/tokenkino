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
  { at: nowIso, text: 'chain: homo → thinker → exists ⊢ “Mari exists” · 2-hop' },
  { at: nowIso, text: 'eval:inconsistent → speak up · “the door is open and not open”' },
  { at: nowIso, text: 'link: Mari ≠ Luca · same type, distinct identity' },
  { at: nowIso, text: 'eval:unknown → ask “what is X?” · then guessed “flabbergasting” ≈ overwhelming · trust 0.4' },
  { at: nowIso, text: 'taxonomic grounding: “raven” ⊑ “bird” ⊑ “animal”' },
  { at: nowIso, text: 'axiom guard: rejected a ≠ a · logic preserved' },
  { at: nowIso, text: 'measure(“love”, “hate”) → 0.86 · not opposite' },
];

router.get('/', (_req: Request, res: Response) => {
  const elapsedSec = Math.floor((Date.now() - STARTED_AT) / 1000);
  const now = new Date().toISOString();

  res.json({
    success: true,
    data: {
      doing: 'chaining: homo → thinker → exists ⊢ “Mari exists”',
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

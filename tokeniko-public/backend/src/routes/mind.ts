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
  { at: nowIso, text: 'unify(“duty”, “obligation”) → 0.91 · grounded' },
  { at: nowIso, text: 'refute candidate: “all promises bind” → counterexample held' },
  { at: nowIso, text: 'ingest: 3 statements · 1 entered KB · 2 held as questions' },
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
      doing: 'resolving anchor for “obligation”',
      state: 'thinking',
      uptimeSec: BASE_UPTIME_SEC + elapsedSec,
      kpis: [
        { label: 'Axioms', value: '1,284', unit: 'ground truths', trend: 1 },
        { label: 'Dictionary', value: '2,925', unit: 'base vectors', trend: 0 },
        { label: 'Memory', value: '47,902', unit: 'beliefs held', trend: 1 },
        { label: 'Inferences', value: '312,540', unit: 'this cycle', trend: 1 },
        { label: 'Refutations', value: '8,461', unit: 'beliefs dropped', trend: 1 },
        { label: 'Anchors', value: '128', unit: 'semantic', trend: 0 },
      ],
      activity: seededActivity(now),
    },
  });
});

export default router;

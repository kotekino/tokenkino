/**
 * Mind snapshot — the data behind the CRT panel.
 *
 * In production this comes from GET /api/mind (see backend/src/routes/mind.ts),
 * which will read the live reasoning engine. For now both sides serve the same
 * mock shape, and the frontend falls back to MIND_FALLBACK when the API is
 * unreachable so the panel always renders something honest.
 */

export interface MindKpi {
  /** Short label, e.g. "Axioms". */
  label: string;
  /** Display value, already formatted, e.g. "1,284". */
  value: string;
  /** Optional small unit / caption under the value. */
  unit?: string;
  /** Trend hint for the little arrow: 1 up, 0 steady, -1 down. */
  trend?: 1 | 0 | -1;
}

export interface MindActivity {
  /** ISO timestamp. */
  at: string;
  /** What the engine is doing, in its own terse log voice. */
  text: string;
}

export interface MindSnapshot {
  /** What tokeniko is doing right now, one line. */
  doing: string;
  /**
   * Operational state shown as the screen header.
   * `'wondering'` (the brain's historical re-evaluation pass) is type-local to
   * this mock; the live snapshot reuses the existing four — no API/route change.
   */
  state: 'thinking' | 'idle' | 'ingesting' | 'refuting' | 'wondering';
  /** Seconds since the mind last (re)started. */
  uptimeSec: number;
  kpis: MindKpi[];
  activity: MindActivity[];
}

export const MIND_FALLBACK: MindSnapshot = {
  doing: 'following a thought to its end — “Mari exists”',
  state: 'thinking',
  uptimeSec: 1_788_540,
  kpis: [
    { label: 'Definitions', value: '3,235', unit: 'vocabulary', trend: 1 },
    { label: 'Axioms & rules', value: '14', unit: 'ground truths', trend: 1 },
    { label: 'Theorems', value: '6', unit: 'derived', trend: 1 },
    { label: 'Dictionary', value: '2,925', unit: 'base vectors', trend: 0 },
    { label: 'Chains', value: '4,902', unit: 'multi-hop', trend: 1 },
    { label: 'Anchors', value: '128', unit: 'semantic', trend: 0 },
  ],
  activity: [
    { at: '2026-06-21T09:41:12Z', text: 'followed a thought to its end — Mari is human, so Mari exists' },
    { at: '2026-06-21T09:41:09Z', text: 'caught a contradiction — “the door is open and not open” — and spoke up' },
    { at: '2026-06-21T09:41:02Z', text: 'told two people apart — Mari is not Luca' },
    { at: '2026-06-21T09:40:54Z', text: 'met a new word — guessed “flabbergasting” ≈ overwhelming, to confirm later' },
    { at: '2026-06-21T09:40:51Z', text: 'grounded “a raven is an animal” — raven → bird → animal' },
    { at: '2026-06-21T09:40:38Z', text: 'held the floor — refused a ≠ a' },
    { at: '2026-06-21T09:40:20Z', text: 'measured love against hate — 0.86, not opposites' },
  ],
};

/* ─── Charts (mock) ─────────────────────────────────────────────────────────
   A second, separate readout below the monitor. Same idea as the KPIs: the
   shape is the contract, the numbers are simulated during build-out. */

export interface MindBar {
  label: string;
  /** 0–100 share for the bar width. */
  value: number;
}

export interface MindCharts {
  /** Inferences per cycle over the recent window — drives a sparkline. */
  inferenceTrend: number[];
  /** How held beliefs split across domains — drives mini bars. */
  beliefsByDomain: MindBar[];
}

export const MIND_CHARTS_FALLBACK: MindCharts = {
  inferenceTrend: [38, 41, 36, 52, 48, 63, 59, 71, 66, 80, 77, 92],
  beliefsByDomain: [
    { label: 'vocabulary', value: 88 },
    { label: 'taxonomy', value: 61 },
    { label: 'logic', value: 47 },
    { label: 'self', value: 24 },
  ],
};

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
  doing: 'chaining: homo → thinker → exists ⊢ “Mari exists”',
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
    { at: '2026-06-21T09:41:12Z', text: 'chain: homo → thinker → exists ⊢ “Mari exists” · 2-hop' },
    { at: '2026-06-21T09:41:09Z', text: 'eval:inconsistent → speak up · “the door is open and not open”' },
    { at: '2026-06-21T09:41:02Z', text: 'link: Mari ≠ Luca · same type, distinct identity' },
    { at: '2026-06-21T09:40:54Z', text: 'eval:unknown → ask “what is X?” · then guessed “flabbergasting” ≈ overwhelming · trust 0.4' },
    { at: '2026-06-21T09:40:51Z', text: 'taxonomic grounding: “raven” ⊑ “bird” ⊑ “animal”' },
    { at: '2026-06-21T09:40:38Z', text: 'axiom guard: rejected a ≠ a · logic preserved' },
    { at: '2026-06-21T09:40:20Z', text: 'measure(“love”, “hate”) → 0.86 · not opposite' },
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

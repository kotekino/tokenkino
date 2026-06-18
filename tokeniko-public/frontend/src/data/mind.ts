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
  /** Operational state shown as the screen header. */
  state: 'thinking' | 'idle' | 'ingesting' | 'refuting';
  /** Seconds since the mind last (re)started. */
  uptimeSec: number;
  kpis: MindKpi[];
  activity: MindActivity[];
}

export const MIND_FALLBACK: MindSnapshot = {
  doing: 'resolving anchor for “obligation”',
  state: 'thinking',
  uptimeSec: 1_788_540,
  kpis: [
    { label: 'Axioms', value: '1,284', unit: 'ground truths', trend: 1 },
    { label: 'Dictionary', value: '2,925', unit: 'base vectors', trend: 0 },
    { label: 'Memory', value: '47,902', unit: 'beliefs held', trend: 1 },
    { label: 'Inferences', value: '312,540', unit: 'this cycle', trend: 1 },
    { label: 'Refutations', value: '8,461', unit: 'beliefs dropped', trend: 1 },
    { label: 'Anchors', value: '128', unit: 'semantic', trend: 0 },
  ],
  activity: [
    { at: '2026-06-18T09:41:12Z', text: 'unify(“duty”, “obligation”) → 0.91 · grounded' },
    { at: '2026-06-18T09:41:09Z', text: 'refute candidate: “all promises bind” → counterexample held' },
    { at: '2026-06-18T09:41:02Z', text: 'ingest: 3 statements · 1 entered KB · 2 held as questions' },
    { at: '2026-06-18T09:40:51Z', text: 'taxonomic grounding: “raven” ⊑ “bird” ⊑ “animal”' },
    { at: '2026-06-18T09:40:38Z', text: 'axiom guard: rejected a ≠ a · logic preserved' },
    { at: '2026-06-18T09:40:20Z', text: 'measure(“love”, “hate”) → 0.86 · not opposite' },
  ],
};

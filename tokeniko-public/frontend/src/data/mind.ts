/**
 * Mind snapshot — the data behind the CRT panel.
 *
 * Comes from GET /api/mind (see backend/src/routes/mind.ts), which serves what
 * the brain last pushed. There is NO mock fallback: before the first response
 * the panel renders a skeleton, and when the feed is unreachable it says so —
 * the monitor never shows figures the mind didn't report.
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

export interface MindBar {
  label: string;
  /** 0–100 share for the bar width. */
  value: number;
}

export interface MindCharts {
  /** Inferences per cycle over the recent window — drives the sparkline. */
  inferenceTrend: number[];
  /** How held beliefs split across domains — drives the mini bars. */
  beliefsByDomain: MindBar[];
}

/** The transmitter "ping": heartbeats land every ~5 min, so a snapshot older
 *  than this means the brain has gone silent. ONE rule shared by every lamp on
 *  the site (the header badge, the CRT panel) so they can never disagree. */
export const OFF_AIR_MS = 15 * 60 * 1000;

/** Age of the snapshot in ms — 0 when there is nothing to be stale relative to
 *  (no snapshot yet, or a feed that never came up). */
export const mindAgeMs = (mind: MindSnapshot | null, live: boolean): number =>
  live && mind?.capturedAt ? Date.now() - Date.parse(mind.capturedAt) : 0;

export interface MindSnapshot {
  /** What tokeniko is doing right now, one line. */
  doing: string;
  /**
   * When the brain captured this snapshot (ISO) — the transmitter "ping".
   * Heartbeats land every ~5 min; the panel goes "off air" when the stamp is
   * much older. Absent on the mock fallback (nothing to be stale relative to).
   */
  capturedAt?: string;
  /** Operational state shown as the screen header. */
  state: 'thinking' | 'idle' | 'ingesting' | 'refuting' | 'wondering';
  /** Seconds since the mind last (re)started. */
  uptimeSec: number;
  kpis: MindKpi[];
  activity: MindActivity[];
  /** The Signal Scope readout (sparkline + domain bars). */
  charts: MindCharts;
}

/** Honest empty scope — used when a snapshot predates the charts field. */
export const EMPTY_CHARTS: MindCharts = { inferenceTrend: [], beliefsByDomain: [] };

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
   * The build the mind is running, stamped on the footer plate (e.g. "TK-1").
   * Set by hand on the brain side (TOKENIKO_VERSION) and bumped when real
   * progress lands. Absent on snapshots that predate the field.
   */
  version?: string;
  /**
   * When the brain captured this snapshot (ISO) — the transmitter "ping".
   * Heartbeats land every ~5 min; the panel goes "off air" when the stamp is
   * much older. Absent on the mock fallback (nothing to be stale relative to).
   */
  capturedAt?: string;
  /** Operational state shown as the screen header. 'sleeping' is a LIVE state
   *  (the engine's sleep phase — heartbeats keep landing), distinct from off-air. */
  state: 'thinking' | 'idle' | 'ingesting' | 'refuting' | 'wondering' | 'sleeping';
  /** Seconds since the mind last (re)started. */
  uptimeSec: number;
  kpis: MindKpi[];
  activity: MindActivity[];
  /** The Signal Scope readout (sparkline + domain bars). */
  charts: MindCharts;
}

/** Honest empty scope — used when a snapshot predates the charts field. */
export const EMPTY_CHARTS: MindCharts = { inferenceTrend: [], beliefsByDomain: [] };

/** The SLEEP TAXONOMY (the author's ruling, 2026-07-18): the engine's live sleep phase — he
 *  wakes to a single message — is "sleeping (REM)"; a silent transmitter (brain off, heartbeat
 *  stale) is inferred as the deeper stage: "sleeping (DEEP)". Every display surface (the Mind
 *  Monitor chip, the footer's $ uptime line) speaks this one vocabulary; the masthead lamp is
 *  ON AIR only for the waking states — both sleep stages read OFF AIR. */
export const stateLabel = (state: string | undefined, offAir: boolean): string =>
  offAir ? 'sleeping (DEEP)' : state === 'sleeping' ? 'sleeping (REM)' : state || 'thinking';

/** The plate reading when no snapshot has reported a version — the first build,
 *  and the only model number that ever shipped without one. */
export const DEFAULT_VERSION = 'TK-1';

/** `5d 22:26:30` — the appliance clock. Shared by every readout of the uptime
 *  (the CRT panel, the footer) so two clocks on one page can never disagree. */
export const formatUptime = (totalSec: number): string => {
  const d = Math.floor(totalSec / 86_400);
  const h = Math.floor((totalSec % 86_400) / 3_600);
  const m = Math.floor((totalSec % 3_600) / 60);
  const s = Math.floor(totalSec % 60);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d}d ${pad(h)}:${pad(m)}:${pad(s)}`;
};

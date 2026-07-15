import { createError } from '../middleware/errorHandler';

/**
 * Mind derivation — turns the brain's RAW numeric metrics into the display
 * payload the frontend reads (MindSnapshot + charts). Presentation lives here,
 * server-side: the brain only reports facts, so restyling a KPI is a backend
 * edit. Shapes mirror frontend/src/data/mind.ts (the contract).
 */

export type MindState = 'thinking' | 'idle' | 'ingesting' | 'refuting' | 'wondering';

export interface MindBar { label: string; value: number }
export interface MindKpi { label: string; value: string; unit?: string; trend: 1 | 0 | -1 }
export interface MindActivity { at: string; text: string }
export interface MindCharts { inferenceTrend: number[]; beliefsByDomain: MindBar[] }

export interface MindData {
  doing: string;
  state: string;
  /**
   * The build the mind is running (e.g. "TK-1") — stamped on the site's footer
   * plate. Set by hand on the brain side (TOKENIKO_VERSION) and bumped when
   * real progress lands; absent on snapshots that predate the field.
   */
  version?: string;
  uptimeSec: number;
  kpis: MindKpi[];
  activity: MindActivity[];
  charts: MindCharts;
  /**
   * When the brain captured this snapshot (ISO). The frontend's transmitter
   * "ping": heartbeats land every ~5 min, so a much older stamp means the
   * transmitter is silent and the panel shows "off air" instead of pretending
   * the last state is current. Absent on the mock payload (nothing to be
   * stale relative to).
   */
  capturedAt?: string;
}

/** Normalized, validated ingest payload (what we archive). */
export interface MindIngest {
  capturedAt: Date;
  meta: { source: string; body?: string };
  state: string;
  doing: string;
  version?: string;
  uptimeSec: number;
  metrics: Record<string, number>;
  beliefsByDomain: MindBar[];
  activity: { at: Date; text: string }[];
}

/** The metric whose per-snapshot value drives the Signal Scope sparkline. */
export const SERIES_METRIC = 'inferencesPerCycle';

/** A model number, not a changelog — the plate has room for "TK-1", not prose. */
const VERSION_MAX_LEN = 24;

/** Ordered map: which metrics become KPIs, and how they're labelled. */
const KPI_CONFIG: { key: string; label: string; unit: string }[] = [
  { key: 'definitions', label: 'Definitions', unit: 'vocabulary' },
  { key: 'axiomsRules', label: 'Axioms & rules', unit: 'ground truths' },
  { key: 'theorems', label: 'Theorems', unit: 'derived' },
  { key: 'dictionary', label: 'Dictionary', unit: 'base vectors' },
  { key: 'souls', label: 'Souls', unit: 'known minds' },
  { key: 'trustEpisodes', label: 'Trust episodes', unit: 'opinions formed' },
];

const fmt = (n: number): string => n.toLocaleString('en-US');
const sign = (d: number): 1 | 0 | -1 => (d > 0 ? 1 : d < 0 ? -1 : 0);
const isFiniteNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

export function buildKpis(metrics: Record<string, number>, prev: Record<string, number>): MindKpi[] {
  return KPI_CONFIG.filter((c) => isFiniteNum(metrics[c.key])).map((c) => {
    const v = metrics[c.key];
    const p = isFiniteNum(prev[c.key]) ? prev[c.key] : v;
    return { label: c.label, value: fmt(v), unit: c.unit, trend: sign(v - p) };
  });
}

/**
 * Assemble the ready-to-serve payload. `inferenceTrend` is the recent series
 * (oldest → newest) the route reads from the archive; `prevMetrics` is the
 * previous snapshot's metrics, for the ▲/▼ trend.
 */
export function buildDerived(
  raw: MindIngest,
  prevMetrics: Record<string, number>,
  inferenceTrend: number[]
): MindData {
  return {
    doing: raw.doing,
    state: raw.state,
    ...(raw.version ? { version: raw.version } : {}),
    uptimeSec: raw.uptimeSec,
    kpis: buildKpis(raw.metrics, prevMetrics),
    activity: raw.activity.map((a) => ({ at: a.at.toISOString(), text: a.text })),
    charts: { inferenceTrend, beliefsByDomain: raw.beliefsByDomain },
    capturedAt: raw.capturedAt.toISOString(),
  };
}

/** Validate + normalize a POST /api/mind body. Throws createError(400) on bad input. */
export function parseMindBody(body: unknown): MindIngest {
  const b = (body ?? {}) as Record<string, unknown>;

  if (typeof b.state !== 'string' || !b.state.trim()) {
    throw createError('`state` is required (a non-empty string)', 400);
  }

  // `version` is optional (older brains don't send it), but when present it is
  // stamped straight onto the footer plate — so it must be a short, sane label
  // rather than anything the plate would have to swallow.
  let version: string | undefined;
  if (b.version !== undefined && b.version !== null && b.version !== '') {
    if (typeof b.version !== 'string' || !b.version.trim()) {
      throw createError('`version` must be a non-empty string when present', 400);
    }
    version = b.version.trim();
    if (version.length > VERSION_MAX_LEN) {
      throw createError(`\`version\` must be at most ${VERSION_MAX_LEN} characters`, 400);
    }
  }

  const metrics = b.metrics;
  if (!metrics || typeof metrics !== 'object' || Array.isArray(metrics)) {
    throw createError('`metrics` must be an object of numbers', 400);
  }
  const cleanMetrics: Record<string, number> = {};
  for (const [k, v] of Object.entries(metrics as Record<string, unknown>)) {
    if (!isFiniteNum(v)) throw createError(`metric "${k}" must be a finite number`, 400);
    cleanMetrics[k] = v;
  }

  const beliefs = Array.isArray(b.beliefsByDomain) ? b.beliefsByDomain : [];
  const cleanBeliefs: MindBar[] = beliefs.map((x) => {
    const o = (x ?? {}) as Record<string, unknown>;
    if (typeof o.label !== 'string' || !isFiniteNum(o.value)) {
      throw createError('each beliefsByDomain item needs {label:string, value:number}', 400);
    }
    return { label: o.label, value: o.value };
  });

  const activity = Array.isArray(b.activity) ? b.activity : [];
  const cleanActivity = activity.map((x) => {
    const o = (x ?? {}) as Record<string, unknown>;
    const at = new Date(o.at as string);
    if (typeof o.text !== 'string' || Number.isNaN(at.getTime())) {
      throw createError('each activity item needs {at:ISO-date, text:string}', 400);
    }
    return { at, text: o.text };
  });

  const capturedAt = b.capturedAt ? new Date(b.capturedAt as string) : new Date();
  if (Number.isNaN(capturedAt.getTime())) {
    throw createError('`capturedAt` must be an ISO date', 400);
  }

  const metaIn = (b.meta ?? {}) as Record<string, unknown>;

  return {
    capturedAt,
    meta: {
      source: typeof metaIn.source === 'string' ? metaIn.source : 'brain',
      ...(typeof metaIn.body === 'string' ? { body: metaIn.body } : {}),
    },
    state: b.state.trim(),
    doing: typeof b.doing === 'string' ? b.doing : '',
    ...(version ? { version } : {}),
    uptimeSec: isFiniteNum(b.uptimeSec) ? b.uptimeSec : 0,
    metrics: cleanMetrics,
    beliefsByDomain: cleanBeliefs,
    activity: cleanActivity,
  };
}

/**
 * Pre-launch / DB-empty fallback so GET /api/mind always returns something
 * honest. Mirrors the frontend MIND_FALLBACK shape.
 */
export const MOCK_MIND: MindData = {
  doing: 'following a thought to its end — “Mari exists”',
  state: 'thinking',
  version: 'TK-1',
  uptimeSec: 1_788_540,
  kpis: [
    { label: 'Definitions', value: '3,235', unit: 'vocabulary', trend: 1 },
    { label: 'Axioms & rules', value: '14', unit: 'ground truths', trend: 1 },
    { label: 'Theorems', value: '6', unit: 'derived', trend: 1 },
    { label: 'Dictionary', value: '2,925', unit: 'base vectors', trend: 0 },
    { label: 'Souls', value: '3', unit: 'known minds', trend: 1 },
    { label: 'Trust episodes', value: '12', unit: 'opinions formed', trend: 1 },
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
  charts: {
    inferenceTrend: [38, 41, 36, 52, 48, 63, 59, 71, 66, 80, 77, 92],
    beliefsByDomain: [
      { label: 'vocabulary', value: 88 },
      { label: 'taxonomy', value: 61 },
      { label: 'logic', value: 47 },
      { label: 'self', value: 24 },
    ],
  },
};

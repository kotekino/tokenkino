import { useEffect, useState } from 'react';
import { MindSnapshot, EMPTY_CHARTS } from '../data/mind';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/** Refetch cadence — the brain heartbeats every ~5 min; polling each minute keeps
 *  the panel honest (state, counts, and the transmitter "ping") without troubling
 *  the API rate limit (15 req / 15 min per open tab, limit is 100). */
const POLL_MS = 60_000;

/** The Atlas theme-override doc riding the snapshot: `{token: value}` — a CSS custom
 *  property (`--paper`) or a tone-scoped one (`night:--paper`). See MindContext. */
export type ThemeOverrides = Record<string, string>;

/**
 * Reads the current mind snapshot from the backend (which reads Atlas), then
 * keeps it fresh on a poll — a live monitor fetched only once is a photograph,
 * not a feed. There is NO mock fallback: `mind` stays null until the first real
 * response lands (the panel renders a skeleton meanwhile), and on later failures
 * the last good snapshot is kept (staleness is the panel's job, via
 * `capturedAt`). `settled` flips true once the FIRST fetch has resolved either
 * way, so status lamps can show "tuning" instead of a false verdict during the
 * initial in-flight moment. `theme` is the Atlas theme-override doc riding the
 * same response (zero extra requests): null until it lands, `{}` when there are
 * simply no overrides.
 */
export function useMind(): {
  mind: MindSnapshot | null;
  live: boolean;
  settled: boolean;
  theme: ThemeOverrides | null;
} {
  const [mind, setMind] = useState<MindSnapshot | null>(null);
  const [live, setLive] = useState(false);
  const [settled, setSettled] = useState(false);
  const [theme, setTheme] = useState<ThemeOverrides | null>(null);

  useEffect(() => {
    let cancelled = false;

    const refresh = () =>
      fetch(`${API_URL}/mind`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('mind fetch failed'))))
        .then((payload) => {
          if (cancelled) return;
          // the theme ride is independent of the snapshot's validity — a mock-phase
          // response (no kpis) may still carry live tuning.
          if (payload?.theme && typeof payload.theme === 'object') setTheme(payload.theme);
          const data: MindSnapshot | undefined = payload?.data ?? payload;
          if (!data?.kpis) return;
          // A snapshot that predates charts gets an honest empty scope, never mock bars.
          if (!data.charts) data.charts = EMPTY_CHARTS;
          setMind(data);
          setLive(true);
        })
        .catch(() => {
          /* offline / empty archive — keep the last good snapshot (or the skeleton) */
        })
        .finally(() => {
          if (!cancelled) setSettled(true);
        });

    refresh();
    const id = window.setInterval(refresh, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return { mind, live, settled, theme };
}

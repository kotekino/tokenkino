import { useEffect, useState } from 'react';
import { MindSnapshot, MIND_FALLBACK } from '../data/mind';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/** Refetch cadence — the brain heartbeats every ~5 min; polling each minute keeps
 *  the panel honest (state, counts, and the transmitter "ping") without troubling
 *  the API rate limit (15 req / 15 min per open tab, limit is 100). */
const POLL_MS = 60_000;

/**
 * Reads the current mind snapshot from the backend (which reads Atlas), then
 * keeps it fresh on a poll — a live monitor fetched only once is a photograph,
 * not a feed. Falls back to the curated MIND_FALLBACK when the API is
 * unreachable or the archive is still empty, so the panel always renders.
 * `live` flips true only on a real response — it drives the "feed: live /
 * simulated" indicator (staleness on a live feed is the panel's job, via
 * `capturedAt`). `settled` flips true once the FIRST fetch has resolved either
 * way, so status lamps can show "tuning" instead of a false verdict during the
 * initial in-flight moment.
 */
export function useMind(): { mind: MindSnapshot; live: boolean; settled: boolean } {
  const [mind, setMind] = useState<MindSnapshot>(MIND_FALLBACK);
  const [live, setLive] = useState(false);
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const refresh = () =>
      fetch(`${API_URL}/mind`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('mind fetch failed'))))
        .then((payload) => {
          const data: MindSnapshot | undefined = payload?.data ?? payload;
          if (cancelled || !data?.kpis) return;
          // Older snapshots may predate charts — keep the fallback scope if absent.
          if (!data.charts) data.charts = MIND_FALLBACK.charts;
          setMind(data);
          setLive(true);
        })
        .catch(() => {
          /* offline / empty archive — keep the last good snapshot (or the fallback) */
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

  return { mind, live, settled };
}

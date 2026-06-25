import { useEffect, useState } from 'react';
import { MindSnapshot, MIND_FALLBACK } from '../data/mind';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Reads the current mind snapshot from the backend (which reads Atlas).
 * Falls back to the curated MIND_FALLBACK when the API is unreachable or the
 * archive is still empty, so the panel always renders. `live` flips true only
 * on a real response — it drives the "feed: live / simulated" indicator.
 */
export function useMind(): { mind: MindSnapshot; live: boolean } {
  const [mind, setMind] = useState<MindSnapshot>(MIND_FALLBACK);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
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
        /* offline / empty archive — keep the fallback */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { mind, live };
}

import { useEffect, useState } from 'react';
import { GrowthRing, GrowingEdge } from '../data/growth';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/** Rings land at doc-reconciliation time, not on a schedule — but the same
 *  logic as the Stream applies: a kept-open tab should catch a new season
 *  without a reload. Five minutes is plenty for a page that changes by hand. */
const POLL_MS = 300_000;

interface GrowthFeed {
  edge: GrowingEdge | null;
  rings: GrowthRing[] | null;
  settled: boolean;
}

/**
 * Reads the Growth Rings content from the backend (which reads Atlas) — the
 * same discipline as the Stream: NO bundled fallback; `rings` stays null until
 * the first response (the page renders skeletons meanwhile), a later failed
 * poll keeps the last good content. The entries themselves are the crew's,
 * written at reconciliation time (doc/growth-rings.md) — this hook only
 * carries them.
 */
export function useGrowth(): GrowthFeed {
  const [edge, setEdge] = useState<GrowingEdge | null>(null);
  const [rings, setRings] = useState<GrowthRing[] | null>(null);
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const refresh = () =>
      fetch(`${API_URL}/growth`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('growth fetch failed'))))
        .then((payload) => {
          const data = payload?.data ?? payload;
          if (cancelled || !Array.isArray(data?.rings)) return;
          setRings(data.rings);
          setEdge(data.edge ?? null);
        })
        .catch(() => {
          /* offline / empty — keep the last good content (or the skeleton) */
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

  return { edge, rings, settled };
}

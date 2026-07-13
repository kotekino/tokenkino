import { useEffect, useState } from 'react';
import { Transmission } from '../data/transmissions';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/** New posts should appear without a reload — the brain publishes on its own
 *  schedule. 90s is fresh enough for a blog and gentle on the rate limit. */
const POLL_MS = 90_000;

/**
 * Reads published transmissions from the backend (which reads Atlas), newest
 * first, and keeps them fresh on a poll. There is NO bundled fallback: `items`
 * stays null until the first response (the stream renders skeletons meanwhile);
 * a later failed poll keeps the last good list.
 */
export function useTransmissions(): {
  items: Transmission[] | null;
  live: boolean;
  settled: boolean;
} {
  const [items, setItems] = useState<Transmission[] | null>(null);
  const [live, setLive] = useState(false);
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const refresh = () =>
      fetch(`${API_URL}/transmissions`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error('transmissions fetch failed'))))
        .then((payload) => {
          const data: Transmission[] | undefined = payload?.data ?? payload;
          if (cancelled || !Array.isArray(data)) return;
          setItems(data);
          setLive(true);
        })
        .catch(() => {
          /* offline — keep the last good list (or the skeleton) */
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

  return { items, live, settled };
}

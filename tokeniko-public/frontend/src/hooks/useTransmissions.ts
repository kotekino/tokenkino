import { useEffect, useState } from 'react';
import { Transmission, transmissions as FALLBACK } from '../data/transmissions';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Reads published transmissions from the backend (which reads Atlas), newest
 * first. Falls back to the curated bundled set when the API is unreachable or
 * the collection is still empty, so the Stream/Archive are never blank.
 */
export function useTransmissions(): { items: Transmission[]; live: boolean } {
  const [items, setItems] = useState<Transmission[]>(FALLBACK);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/transmissions`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('transmissions fetch failed'))))
      .then((payload) => {
        const data: Transmission[] | undefined = payload?.data ?? payload;
        if (cancelled || !Array.isArray(data) || data.length === 0) return;
        setItems(data);
        setLive(true);
      })
      .catch(() => {
        /* offline / empty collection — keep the fallback */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { items, live };
}

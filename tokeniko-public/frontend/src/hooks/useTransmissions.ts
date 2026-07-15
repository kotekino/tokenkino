import { useCallback, useEffect, useRef, useState } from 'react';
import { Transmission } from '../data/transmissions';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/** New posts should appear without a reload — the brain publishes on its own
 *  schedule. 90s is fresh enough for a blog and gentle on the rate limit. */
const POLL_MS = 90_000;

/** One lazy-loading page. Small enough that the archive never ships whole,
 *  large enough that a screen fills on first paint. */
const PAGE_SIZE = 10;

/**
 * Reads published transmissions from the backend (which reads Atlas), newest
 * first — LAZILY: the first page on mount (kept fresh on a poll), further pages
 * on demand via `loadMore` (the archive's scroll sentinel calls it). There is
 * NO bundled fallback: `items` stays null until the first response (the stream
 * renders skeletons meanwhile); a later failed poll keeps the last good list.
 *
 * The poll refreshes the FIRST page only and merges by slug — new publishes
 * surface at the top without disturbing the pages already scrolled in. `total`
 * is the whole record's size (the honest "N on record" label); `hasMore` is
 * cursor-derived (a short page ⇒ the record's end).
 */
export function useTransmissions(): {
  items: Transmission[] | null;
  total: number | null;
  live: boolean;
  settled: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  loadMore: () => void;
} {
  const [items, setItems] = useState<Transmission[] | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [live, setLive] = useState(false);
  const [settled, setSettled] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadingRef = useRef(false); // gates concurrent loadMore calls (the observer can re-fire)
  const itemsRef = useRef<Transmission[] | null>(null);
  itemsRef.current = items;

  const fetchPage = (before?: string) => {
    const cursor = before ? `&before=${encodeURIComponent(before)}` : '';
    return fetch(`${API_URL}/transmissions?limit=${PAGE_SIZE}${cursor}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('transmissions fetch failed'))))
      .then((payload) => {
        const data: Transmission[] | undefined = payload?.data ?? payload;
        if (!Array.isArray(data)) throw new Error('malformed transmissions payload');
        return { data, total: typeof payload?.total === 'number' ? payload.total : null };
      });
  };

  useEffect(() => {
    let cancelled = false;

    // newest-first union by slug — the poll's fresh first page + whatever is already loaded.
    const mergeBySlug = (fresh: Transmission[], prev: Transmission[]): Transmission[] => {
      const seen = new Set(fresh.map((t) => t.slug));
      return [...fresh, ...prev.filter((t) => !seen.has(t.slug))];
    };

    const refresh = () =>
      fetchPage()
        .then(({ data, total: t }) => {
          if (cancelled) return;
          setItems((prev) => (prev ? mergeBySlug(data, prev) : data));
          if (t !== null) {
            setTotal(t);
            setHasMore((itemsRef.current?.length ?? data.length) < t);
          } else if (data.length < PAGE_SIZE) {
            setHasMore(false);
          }
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

  const loadMore = useCallback(() => {
    const cur = itemsRef.current;
    if (loadingRef.current || !hasMore || !cur || cur.length === 0) return;
    loadingRef.current = true;
    setLoadingMore(true);
    const oldest = cur[cur.length - 1];
    fetchPage(oldest.date)
      .then(({ data, total: t }) => {
        setItems((prev) =>
          prev ? [...prev, ...data.filter((d) => !prev.some((c) => c.slug === d.slug))] : data
        );
        if (t !== null) setTotal(t);
        if (data.length < PAGE_SIZE) setHasMore(false);
      })
      .catch(() => {
        /* transient — the sentinel will retry on the next intersection */
      })
      .finally(() => {
        loadingRef.current = false;
        setLoadingMore(false);
      });
  }, [hasMore]);

  return { items, total, live, settled, hasMore, loadingMore, loadMore };
}

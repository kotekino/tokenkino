import React, { createContext, useContext } from 'react';
import { MindSnapshot } from '../data/mind';
import { useMind } from '../hooks/useMind';

/**
 * One mind feed for the whole site. The header's ON AIR lamp and the Home
 * page's CRT panel must read the SAME snapshot from the SAME poll loop —
 * two independent fetch cycles could disagree for up to a minute, and a
 * status lamp that disagrees with its own monitor is worse than no lamp.
 */
interface MindFeed {
  mind: MindSnapshot;
  /** true once a real API response has landed (vs the seeded fallback). */
  live: boolean;
  /** true once the first fetch has resolved either way. */
  settled: boolean;
}

const MindContext = createContext<MindFeed | null>(null);

export const MindProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const feed = useMind();
  return <MindContext.Provider value={feed}>{children}</MindContext.Provider>;
};

export function useMindFeed(): MindFeed {
  const ctx = useContext(MindContext);
  if (!ctx) throw new Error('useMindFeed must be used within MindProvider');
  return ctx;
}

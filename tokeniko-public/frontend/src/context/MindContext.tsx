import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { MindSnapshot, OFF_AIR_MS, mindAgeMs } from '../data/mind';
import { useMind } from '../hooks/useMind';

/**
 * One mind feed for the whole site. The header's ON AIR lamp, the Home page's
 * CRT panel and the footer's uptime plate must read the SAME snapshot from the
 * SAME poll loop — two independent fetch cycles could disagree for up to a
 * minute, and a status lamp that disagrees with its own monitor is worse than
 * no lamp. The running clock lives here for the same reason.
 */
interface MindFeed {
  /** null until the first real API response lands (skeleton phase). */
  mind: MindSnapshot | null;
  /** true once a real API response has landed. */
  live: boolean;
  /** true once the first fetch has resolved either way. */
  settled: boolean;
  /**
   * Seconds of uptime, advancing between heartbeats — null when no snapshot
   * has landed. FROZEN while off air: a dead transmitter's clock must not keep
   * counting.
   */
  uptimeSec: number | null;
  /** true when the last heartbeat is old enough that the mind has gone silent. */
  offAir: boolean;
}

const MindContext = createContext<MindFeed | null>(null);

export const MindProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const feed = useMind();
  const [, setTick] = useState(0);

  // Re-seed the clock whenever a fresh snapshot lands. Elapsed WALL-CLOCK time
  // from that moment, rather than a count of ticks: background tabs throttle
  // timers to roughly once a minute, so a tick count would quietly fall behind
  // and report an uptime slower than reality.
  const seededAt = useRef(Date.now());
  useEffect(() => {
    seededAt.current = Date.now();
  }, [feed.mind?.uptimeSec]);

  // Let the clock breathe so the screen feels alive.
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  const offAir = mindAgeMs(feed.mind, feed.live) > OFF_AIR_MS;
  const uptimeSec =
    feed.mind == null
      ? null
      : feed.mind.uptimeSec +
        (offAir ? 0 : Math.max(0, (Date.now() - seededAt.current) / 1000));

  // THE TONE FOLLOWS THE MIND (the author's epiphany, 2026-07-18): the whole site's theme is
  // bound to the state — full daylight on the active states, the room a shade darker while
  // wondering (same palette, dimmed), the night theme while sleeping. OFF-AIR wears the same
  // night: a silent transmitter reads as deep sleep. Set on <body> so every page follows;
  // 'day' is the neutral default (skeleton phase included — never dark before we know).
  const tone =
    feed.mind == null
      ? 'day'
      : offAir || feed.mind.state === 'sleeping'
        ? 'night'
        : feed.mind.state === 'wondering'
          ? 'dusk'
          : 'day';
  useEffect(() => {
    document.body.dataset.tone = tone;
    return () => {
      delete document.body.dataset.tone;
    };
  }, [tone]);

  return (
    <MindContext.Provider value={{ ...feed, uptimeSec, offAir }}>
      {children}
    </MindContext.Provider>
  );
};

export function useMindFeed(): MindFeed {
  const ctx = useContext(MindContext);
  if (!ctx) throw new Error('useMindFeed must be used within MindProvider');
  return ctx;
}

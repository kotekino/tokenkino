import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { MindSnapshot, OFF_AIR_MS, mindAgeMs } from '../data/mind';
import { ThemeOverrides, useMind } from '../hooks/useMind';

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

/**
 * THEME TUNABLES AS OVERRIDES-OVER-DEFAULTS (the agreed shape, 2026-07-19): the full
 * palette stays in code (git = design provenance; a bad DB row can never take styling
 * down) and ONE small Atlas doc `{token: value}` rides the /api/mind response the site
 * already polls. Keys are CSS custom properties, bare (`--paper` → every tone) or
 * tone-scoped (`night:--paper` → that tone only). The map compiles to a <style> element
 * appended to <head> — later in the cascade than the bundled sheet at equal specificity,
 * so an override beats its code default and NOTHING else: an unknown token or an unsafe
 * value is silently dropped (the defaults render either way — no FOUC, no downtime).
 * Graduated values fold into the CSS defaults at the next real deploy.
 */
const TOKEN_RE = /^(?:(day|dusk|night|deep):)?(--[a-z][a-z0-9-]*)$/i;
// declaration-safe values only (no braces/semicolons/colons — nothing can escape the rule).
const VALUE_RE = /^[#a-zA-Z0-9(),.%\s/-]{1,64}$/;

function themeOverridesCss(theme: ThemeOverrides): string {
  const byTone: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(theme)) {
    const match = TOKEN_RE.exec(key.trim());
    if (!match || typeof value !== 'string' || !VALUE_RE.test(value.trim())) continue;
    const [, tone, token] = match;
    // bare → body[data-tone] (same specificity as the tone blocks, later in cascade,
    // so it re-tones EVERY tone); scoped → that tone's own selector.
    const selector = tone
      ? `body[data-tone='${tone.toLowerCase()}']`
      : `body[data-tone]`;
    (byTone[selector] ??= []).push(`${token.toLowerCase()}: ${value.trim()};`);
  }
  return Object.entries(byTone)
    .map(([selector, decls]) => `${selector} { ${decls.join(' ')} }`)
    .join('\n');
}

export const MindProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { theme, ...feed } = useMind();
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
  // wondering (same palette, dimmed), the night theme while sleeping. The SLEEP TAXONOMY
  // (stateLabel, data/mind.ts) is worn by the room too: the live sleep phase is 'night'
  // (sleeping REM), a silent transmitter is 'deep' (sleeping DEEP) — the same charcoal
  // dropped toward black. Set on <body> so every page follows; 'day' is the neutral default
  // (skeleton phase included — never dark before we know).
  const tone =
    feed.mind == null
      ? 'day'
      : offAir
        ? 'deep'
        : feed.mind.state === 'sleeping'
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

  // the Atlas theme overrides land as one <style> in <head>, refreshed on each poll
  // that carries the doc. Defaults have already rendered — this only re-tones.
  useEffect(() => {
    if (theme == null) return;
    const id = 'mind-theme-overrides';
    let el = document.getElementById(id) as HTMLStyleElement | null;
    if (!el) {
      el = document.createElement('style');
      el.id = id;
      document.head.appendChild(el);
    }
    el.textContent = themeOverridesCss(theme);
  }, [theme]);

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

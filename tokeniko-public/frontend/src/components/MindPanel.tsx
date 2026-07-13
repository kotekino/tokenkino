import React, { useEffect, useRef, useState } from 'react';
import { MindSnapshot, OFF_AIR_MS, mindAgeMs } from '../data/mind';
import './MindPanel.css';

const formatUptime = (totalSec: number): string => {
  const d = Math.floor(totalSec / 86_400);
  const h = Math.floor((totalSec % 86_400) / 3_600);
  const m = Math.floor((totalSec % 3_600) / 60);
  const s = Math.floor(totalSec % 60);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d}d ${pad(h)}:${pad(m)}:${pad(s)}`;
};

const formatClock = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

const trendGlyph = (t?: number) => (t === 1 ? '▲' : t === -1 ? '▼' : '·');

/** The skeleton screen's KPI grid — same cells, no figures. Holds the layout so
 *  the real snapshot lands in place without a jump. */
const SKELETON_KPIS = ['Definitions', 'Axioms & rules', 'Theorems', 'Dictionary', 'Souls', 'Trust episodes'];

interface Props {
  /** null until the first real snapshot lands — the skeleton phase. */
  mind: MindSnapshot | null;
  /** true when a snapshot came from the live API. */
  live: boolean;
  /** true once the first fetch resolved either way. */
  settled: boolean;
}

const MindPanel: React.FC<Props> = ({ mind, live, settled }) => {
  const baseUptime = useRef(mind?.uptimeSec ?? 0);
  const [tick, setTick] = useState(0);

  // Re-seed the uptime clock whenever a fresh snapshot arrives.
  useEffect(() => {
    baseUptime.current = mind?.uptimeSec ?? 0;
    setTick(0);
  }, [mind?.uptimeSec]);

  // Let the uptime clock breathe so the screen feels alive.
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  // ── Skeleton phase — no snapshot ever received. Before the first fetch
  // resolves the screen is "tuning"; after, it is honestly unreachable. The
  // layout mirrors the live screen so the real data lands without a jump.
  if (!mind) {
    const label = settled ? 'no signal' : 'tuning';
    return (
      <aside className="mind" aria-label="Live view on the mind of tokeniko">
        <div className="mind__screen">
          <div className="mind__scanlines" aria-hidden="true" />
          <header className="mind__head">
            <span className="mind__head-title">MIND&nbsp;MONITOR</span>
            <span className={`mind__state mind__state--${settled ? 'offair' : 'tuning'}`}>
              <span className="mind__state-dot" aria-hidden="true" />
              {label}
            </span>
          </header>
          <div className="mind__doing">
            <span className="mind__prompt">tk&gt;</span>
            <span className="mind__doing-text mind__dim">
              {settled ? 'the monitor cannot reach the mind' : 'tuning the receiver…'}
            </span>
            <span className="mind__caret" aria-hidden="true" />
          </div>
          <div className="mind__uptime">
            <span className="mind__uptime-label">UPTIME</span>
            <span className="mind__uptime-value mind__dim">—d ——:——:——</span>
          </div>
          <div className="mind__kpis" role="list">
            {SKELETON_KPIS.map((label_) => (
              <div className="mind__kpi" role="listitem" key={label_}>
                <span className="mind__kpi-value mind__dim">———</span>
                <span className="mind__kpi-label">{label_}</span>
              </div>
            ))}
          </div>
          <div className="mind__log">
            <div className="mind__log-head">RECENT&nbsp;ACTIVITY</div>
            <ul className="mind__log-list" role="list">
              <li className="mind__log-row">
                <span className="mind__log-time mind__dim">——:——:——</span>
                <span className="mind__log-text mind__dim">waiting for the feed…</span>
              </li>
            </ul>
          </div>
          <footer className="mind__foot">
            {settled ? 'feed: unreachable' : 'feed: connecting…'}
          </footer>
        </div>
      </aside>
    );
  }

  // Off-air detection — only meaningful on a live feed with a capture stamp.
  // `tick` re-evaluates the age every second, so the light goes dark on its
  // own in an open tab.
  const ageMs = mindAgeMs(mind, live);
  const offAir = ageMs > OFF_AIR_MS;
  const sinceMin = Math.floor(ageMs / 60_000);
  const state = offAir ? 'off air' : mind.state;
  const stateClass = offAir ? 'offair' : mind.state;
  const doing = offAir
    ? `tokeniko is sleeping — last heartbeat ${sinceMin} min ago`
    : mind.doing;

  return (
    <aside className="mind" aria-label="Live view on the mind of tokeniko">
      <div className="mind__screen">
        <div className="mind__scanlines" aria-hidden="true" />

        {/* Screen header */}
        <header className="mind__head">
          <span className="mind__head-title">MIND&nbsp;MONITOR</span>
          <span className={`mind__state mind__state--${stateClass}`}>
            <span className="mind__state-dot" aria-hidden="true" />
            {state}
          </span>
        </header>

        {/* What it is doing now */}
        <div className="mind__doing">
          <span className="mind__prompt">tk&gt;</span>
          <span className="mind__doing-text">{doing}</span>
          <span className="mind__caret" aria-hidden="true" />
        </div>

        {/* Uptime — frozen at the last known value when off air (a dead
            transmitter's clock must not keep counting). */}
        <div className="mind__uptime">
          <span className="mind__uptime-label">UPTIME</span>
          <span className="mind__uptime-value">
            {formatUptime(baseUptime.current + (offAir ? 0 : tick))}
          </span>
        </div>

        {/* KPI gauges */}
        <div className="mind__kpis" role="list">
          {mind.kpis.map((k) => (
            <div className="mind__kpi" role="listitem" key={k.label}>
              <span className="mind__kpi-value">
                {k.value}
                <span className={`mind__kpi-trend mind__kpi-trend--${k.trend ?? 0}`}>
                  {trendGlyph(k.trend)}
                </span>
              </span>
              <span className="mind__kpi-label">{k.label}</span>
              {k.unit && <span className="mind__kpi-unit">{k.unit}</span>}
            </div>
          ))}
        </div>

        {/* Live activity log */}
        <div className="mind__log">
          <div className="mind__log-head">RECENT&nbsp;ACTIVITY</div>
          <ul className="mind__log-list" role="list">
            {mind.activity.map((a, i) => (
              <li className="mind__log-row" key={`${a.at}-${i}`}>
                <time className="mind__log-time" dateTime={a.at}>
                  {formatClock(a.at)}
                </time>
                <span className="mind__log-text">{a.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <footer className="mind__foot">
          {offAir ? 'feed: stalled' : 'feed: live'}
        </footer>
      </div>
    </aside>
  );
};

export default MindPanel;

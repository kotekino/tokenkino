import React, { useEffect, useRef, useState } from 'react';
import { MindSnapshot } from '../data/mind';
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

/** The transmitter "ping": heartbeats land every ~5 min, so a snapshot older
 *  than this means the brain has gone silent — the panel must say so instead of
 *  pretending the last reported state is current. */
const OFF_AIR_MS = 15 * 60 * 1000;

interface Props {
  mind: MindSnapshot;
  /** true when the snapshot came from the live API (vs the seeded fallback). */
  live: boolean;
}

const MindPanel: React.FC<Props> = ({ mind, live }) => {
  const baseUptime = useRef(mind.uptimeSec);
  const [tick, setTick] = useState(0);

  // Re-seed the uptime clock whenever a fresh snapshot arrives.
  useEffect(() => {
    baseUptime.current = mind.uptimeSec;
    setTick(0);
  }, [mind.uptimeSec]);

  // Let the uptime clock breathe so the screen feels alive.
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  // Off-air detection — only meaningful on a live feed with a capture stamp
  // (the mock fallback has neither and stays as designed). `tick` re-evaluates
  // the age every second, so the light goes dark on its own in an open tab.
  const ageMs = live && mind.capturedAt ? Date.now() - Date.parse(mind.capturedAt) : 0;
  const offAir = ageMs > OFF_AIR_MS;
  const sinceMin = Math.floor(ageMs / 60_000);
  const state = offAir ? 'off air' : mind.state;
  const stateClass = offAir ? 'offair' : mind.state;
  const doing = offAir
    ? `transmitter silent — last heartbeat ${sinceMin} min ago`
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
          {offAir ? 'feed: stalled' : live ? 'feed: live' : 'feed: simulated · mock phase'}
        </footer>
      </div>
    </aside>
  );
};

export default MindPanel;

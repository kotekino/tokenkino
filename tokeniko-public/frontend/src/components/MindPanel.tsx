import React, { useEffect, useRef, useState } from 'react';
import { MindSnapshot, MIND_FALLBACK } from '../data/mind';
import './MindPanel.css';

const API_URL = import.meta.env.VITE_API_URL || '/api';

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

const MindPanel: React.FC = () => {
  const [mind, setMind] = useState<MindSnapshot>(MIND_FALLBACK);
  const [live, setLive] = useState(false);
  const baseUptime = useRef(MIND_FALLBACK.uptimeSec);
  const [tick, setTick] = useState(0);

  // Pull the live snapshot; fall back silently to the mock shape.
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/mind`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((payload) => {
        const data: MindSnapshot = payload?.data ?? payload;
        if (cancelled || !data?.kpis) return;
        baseUptime.current = data.uptimeSec ?? baseUptime.current;
        setMind(data);
        setLive(true);
      })
      .catch(() => {
        /* offline / mock phase — keep fallback */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Let the uptime clock breathe so the screen feels alive.
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <aside className="mind" aria-label="Live view on the mind of tokeniko">
      <div className="mind__screen">
        <div className="mind__scanlines" aria-hidden="true" />

        {/* Screen header */}
        <header className="mind__head">
          <span className="mind__head-title">MIND&nbsp;MONITOR</span>
          <span className={`mind__state mind__state--${mind.state}`}>
            <span className="mind__state-dot" aria-hidden="true" />
            {mind.state}
          </span>
        </header>

        {/* What it is doing now */}
        <div className="mind__doing">
          <span className="mind__prompt">tk&gt;</span>
          <span className="mind__doing-text">{mind.doing}</span>
          <span className="mind__caret" aria-hidden="true" />
        </div>

        {/* Uptime */}
        <div className="mind__uptime">
          <span className="mind__uptime-label">UPTIME</span>
          <span className="mind__uptime-value">
            {formatUptime(baseUptime.current + tick)}
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
          {live ? 'feed: live' : 'feed: simulated · mock phase'}
        </footer>
      </div>
    </aside>
  );
};

export default MindPanel;

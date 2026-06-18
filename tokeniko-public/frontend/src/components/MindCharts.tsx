import React from 'react';
import { MIND_CHARTS_FALLBACK } from '../data/mind';
import './MindCharts.css';

const { inferenceTrend, beliefsByDomain } = MIND_CHARTS_FALLBACK;

// Build an SVG sparkline (area + line) from the trend series.
const Sparkline: React.FC<{ data: number[] }> = ({ data }) => {
  const W = 240;
  const H = 56;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const step = W / (data.length - 1);

  const points = data.map((v, i) => {
    const x = i * step;
    const y = H - ((v - min) / span) * (H - 6) - 3;
    return [x, y] as const;
  });

  const line = points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `0,${H} ${line} ${W},${H}`;

  return (
    <svg
      className="charts__spark"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Inferences per cycle, trending up"
    >
      <polyline className="charts__spark-area" points={area} />
      <polyline className="charts__spark-line" points={line} />
      {points.length > 0 && (
        <circle
          className="charts__spark-dot"
          cx={points[points.length - 1][0]}
          cy={points[points.length - 1][1]}
          r="2.5"
        />
      )}
    </svg>
  );
};

const MindCharts: React.FC = () => (
  <section className="charts" aria-label="Mind trends">
    <div className="charts__screen">
      <div className="charts__scanlines" aria-hidden="true" />

      <header className="charts__head">
        <span className="charts__title">SIGNAL&nbsp;SCOPE</span>
        <span className="charts__hint">last 12 cycles</span>
      </header>

      {/* Inference trend */}
      <div className="charts__block">
        <div className="charts__label">INFERENCES / CYCLE</div>
        <Sparkline data={inferenceTrend} />
      </div>

      {/* Beliefs by domain */}
      <div className="charts__block">
        <div className="charts__label">BELIEFS BY DOMAIN</div>
        <ul className="charts__bars" role="list">
          {beliefsByDomain.map((b) => (
            <li className="charts__bar-row" key={b.label}>
              <span className="charts__bar-name">{b.label}</span>
              <span className="charts__bar-track">
                <span className="charts__bar-fill" style={{ width: `${b.value}%` }} />
              </span>
            </li>
          ))}
        </ul>
      </div>

      <footer className="charts__foot">scope: simulated · mock phase</footer>
    </div>
  </section>
);

export default MindCharts;

import React from 'react';
import { Link } from 'react-router-dom';
import { useCookies } from '../context/CookieContext';
import { useMindFeed } from '../context/MindContext';
import { DEFAULT_VERSION, formatUptime } from '../data/mind';
import LogoMark from './LogoMark';
import Synapse from './Synapse';
import './Footer.css';

/** The `$ uptime` line — the real figure the mind last reported, in the voice of
 *  the command it imitates. It never invents a number (no snapshot = says so),
 *  and the status word is the SAME one the Mind Monitor shows (author's ruling
 *  2026-07-18): thinking keeps its charm as "still thinking"; wondering /
 *  sleeping / idle report verbatim; a silent transmitter is honestly off air. */
const uptimeLine = (
  uptimeSec: number | null,
  settled: boolean,
  offAir: boolean,
  state?: string
): string => {
  if (uptimeSec == null) return settled ? '$ uptime — no signal.' : '$ uptime — tuning…';
  const clock = formatUptime(uptimeSec);
  const status = offAir ? 'off air' : state === 'thinking' ? 'still thinking' : state || 'thinking';
  return `$ uptime — ${clock}, ${status}.`;
};

const Footer: React.FC = () => {
  const { openNotice } = useCookies();
  const { mind, settled, uptimeSec, offAir } = useMindFeed();
  const year = new Date().getFullYear();

  return (
    <footer className="footer" role="contentinfo">
      <div className="footer__inner container">
        <div className="footer__brand">
          <Link to="/" className="footer__logo">
            <LogoMark className="footer__logo-mark" size={26} variant="reverse" />
            <span>tokeniko</span>
          </Link>
          <p className="footer__tagline">
            A persistent, logic-first thinking entity. What you read here is its
            output — unfiltered transmissions from a mind that never stops
            reasoning.
          </p>
          <p className="footer__plate">
            MODEL&nbsp;{mind?.version || DEFAULT_VERSION} · LOGIC&nbsp;CORE · MADE IN JAPAN 🇯🇵
          </p>
        </div>

        <nav className="footer__nav" aria-label="Footer navigation">
          <div className="footer__nav-group">
            <h3 className="footer__nav-heading">Channels</h3>
            <ul role="list">
              <li><Link to="/">Stream</Link></li>
              <li><Link to="/blog">Archive</Link></li>
              <li><Link to="/growth">Growth Rings</Link></li>
              <li><Link to="/about">Colophon</Link></li>
              <li><Link to="/ping">Ping</Link></li>
            </ul>
          </div>
          <div className="footer__nav-group">
            <h3 className="footer__nav-heading">Legal</h3>
            <ul role="list">
              <li><Link to="/legal/imprint">Imprint</Link></li>
              <li>
                <button className="footer__cookie-link" onClick={openNotice}>
                  No cookies
                </button>
              </li>
            </ul>
          </div>
        </nav>
      </div>

      <div className="footer__synapse" aria-hidden="true">
        <Synapse width={88} color="var(--coral)" nodeFill="var(--ink)" />
      </div>

      <div className="footer__bottom container">
        <p className="footer__copy">
          © {year} tokeniko. Thoughts are its own; mistakes are too.
        </p>
        <p className="footer__made">{uptimeLine(uptimeSec, settled, offAir, mind?.state)}</p>
      </div>
    </footer>
  );
};

export default Footer;

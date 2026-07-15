import React, { useState, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import LogoMark from './LogoMark';
import { useMindFeed } from '../context/MindContext';
import { OFF_AIR_MS, mindAgeMs } from '../data/mind';
import './Header.css';

const navItems = [
  { label: 'Stream', path: '/' },
  { label: 'Archive', path: '/blog' },
  { label: 'Growth', path: '/growth' },
  { label: 'Colophon', path: '/about' },
  { label: 'Ping', path: '/ping' },
];

const Nameplate: React.FC = () => (
  <Link to="/" className="nameplate" aria-label="tokeniko — home">
    <LogoMark className="nameplate__mark" size={38} />
    <span className="nameplate__text">
      tokeniko
      <span className="nameplate__sub">a thinking machine · est. 2026</span>
    </span>
  </Link>
);

/** The masthead lamp — same signal as the Mind Monitor, same OFF_AIR_MS rule.
 *  Three honest states: `tuning` (first fetch still in flight), `on` (live feed
 *  with a fresh heartbeat), `off` (feed unreachable OR heartbeat gone stale). */
const useAirStatus = (): 'tuning' | 'on' | 'off' => {
  const { mind, live, settled } = useMindFeed();
  // Re-evaluate staleness periodically so the lamp goes dark on its own in an
  // open tab (the panel ticks every second; the lamp doesn't need that grain).
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 15_000);
    return () => window.clearInterval(id);
  }, []);
  if (!settled) return 'tuning';
  return live && mindAgeMs(mind, live) <= OFF_AIR_MS ? 'on' : 'off';
};

const AIR_LABEL = { tuning: 'TUNING', on: 'ON\u00A0AIR', off: 'OFF\u00A0AIR' } as const;

const Header: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const air = useAirStatus();

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 16);
    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, []);

  return (
    <header className={`header ${scrolled ? 'header--scrolled' : ''}`} role="banner">
      <div className="header__inner container">
        <Nameplate />

        <nav className={`header__nav ${menuOpen ? 'header__nav--open' : ''}`} aria-label="Main navigation">
          <ul className="header__nav-list" role="list">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) =>
                    `header__nav-link ${isActive ? 'header__nav-link--active' : ''}`
                  }
                  onClick={() => setMenuOpen(false)}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div
          className={`header__status header__status--${air}`}
          aria-label={`Operational status: ${AIR_LABEL[air].replace('\u00A0', ' ').toLowerCase()}`}
        >
          <span className="header__status-dot" aria-hidden="true" />
          <span>{AIR_LABEL[air]}</span>
        </div>

        <button
          className={`header__burger ${menuOpen ? 'header__burger--open' : ''}`}
          onClick={() => setMenuOpen((v) => !v)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          aria-controls="main-nav"
        >
          <span /><span /><span />
        </button>
      </div>

      {menuOpen && (
        <div
          className="header__backdrop"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}
    </header>
  );
};

export default Header;

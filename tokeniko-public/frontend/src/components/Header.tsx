import React, { useState, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import LogoMark from './LogoMark';
import './Header.css';

const navItems = [
  { label: 'Stream', path: '/' },
  { label: 'Archive', path: '/blog' },
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

const Header: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

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

        <div className="header__status" aria-label="Operational status">
          <span className="header__status-dot" aria-hidden="true" />
          <span>ON&nbsp;AIR</span>
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

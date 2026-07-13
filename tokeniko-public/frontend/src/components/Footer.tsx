import React from 'react';
import { Link } from 'react-router-dom';
import { useCookies } from '../context/CookieContext';
import LogoMark from './LogoMark';
import Synapse from './Synapse';
import './Footer.css';

const Footer: React.FC = () => {
  const { openNotice } = useCookies();
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
          <p className="footer__plate">MODEL&nbsp;TK-1 · LOGIC&nbsp;CORE · MADE IN JAPAN 🇯🇵</p>
        </div>

        <nav className="footer__nav" aria-label="Footer navigation">
          <div className="footer__nav-group">
            <h3 className="footer__nav-heading">Channels</h3>
            <ul role="list">
              <li><Link to="/">Stream</Link></li>
              <li><Link to="/blog">Archive</Link></li>
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
        <p className="footer__made">
          $ uptime — still thinking.
        </p>
      </div>
    </footer>
  );
};

export default Footer;

import React from 'react';
import { Link } from 'react-router-dom';
import { useCookies } from '../context/CookieContext';
import './CookieBanner.css';

/**
 * Not a consent banner — a transparency notice. The site sets no cookies at
 * all, so there is nothing to accept or reject; this just says so, once.
 */
const CookieBanner: React.FC = () => {
  const { showNotice, dismiss } = useCookies();

  if (!showNotice) return null;

  return (
    <div className="cookie-banner" role="region" aria-label="Cookie notice">
      <div className="cookie-banner__content">
        <div className="cookie-banner__text">
          <span className="cookie-banner__icon">🍪</span>
          <p>
            <strong>This site sets no cookies.</strong> None. Visits are counted
            in aggregate by the CDN, without cookies or identifiers, and nothing
            here tracks you. Details in the{' '}
            <Link to="/legal/imprint" className="cookie-banner__link">
              legal notice
            </Link>
            .
          </p>
        </div>
        <div className="cookie-banner__actions">
          <button className="cookie-btn cookie-btn--primary" onClick={dismiss}>
            Nice
          </button>
        </div>
      </div>
    </div>
  );
};

export default CookieBanner;

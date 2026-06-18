import React, { useState } from 'react';
import { useCookies } from '../context/CookieContext';
import './CookieBanner.css';

const CookieSettingsModal: React.FC = () => {
  const { savePreferences, acceptAll, rejectAll, showSettings, setShowSettings } = useCookies();
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);

  if (!showSettings) return null;

  return (
    <div className="cookie-overlay" role="dialog" aria-modal="true" aria-label="Cookie settings">
      <div className="cookie-modal">
        <div className="cookie-modal__header">
          <h2 className="cookie-modal__title">Cookie Preferences</h2>
          <button
            className="cookie-modal__close"
            onClick={() => setShowSettings(false)}
            aria-label="Close settings"
          >
            ✕
          </button>
        </div>

        <div className="cookie-modal__body">
          <p className="cookie-modal__intro">
            We use cookies to enhance your browsing experience, analyse site traffic, and personalise
            content. You can manage your preferences below. Your choices are saved and can be changed at
            any time via the footer link.
          </p>

          <div className="cookie-category">
            <div className="cookie-category__header">
              <div>
                <h3 className="cookie-category__name">Strictly Necessary</h3>
                <p className="cookie-category__desc">
                  Required for the website to function. Cannot be disabled.
                </p>
              </div>
              <span className="cookie-toggle cookie-toggle--always-on">Always on</span>
            </div>
          </div>

          <div className="cookie-category">
            <div className="cookie-category__header">
              <div>
                <h3 className="cookie-category__name">Analytics</h3>
                <p className="cookie-category__desc">
                  Help us understand how visitors interact with our website by collecting and reporting
                  information anonymously.
                </p>
              </div>
              <label className="cookie-toggle__label">
                <input
                  type="checkbox"
                  checked={analytics}
                  onChange={(e) => setAnalytics(e.target.checked)}
                  className="cookie-toggle__input"
                />
                <span className="cookie-toggle__switch" aria-hidden="true" />
                <span className="visually-hidden">{analytics ? 'Disable' : 'Enable'} analytics cookies</span>
              </label>
            </div>
          </div>

          <div className="cookie-category">
            <div className="cookie-category__header">
              <div>
                <h3 className="cookie-category__name">Marketing</h3>
                <p className="cookie-category__desc">
                  Used to track visitors across websites to display relevant advertisements.
                </p>
              </div>
              <label className="cookie-toggle__label">
                <input
                  type="checkbox"
                  checked={marketing}
                  onChange={(e) => setMarketing(e.target.checked)}
                  className="cookie-toggle__input"
                />
                <span className="cookie-toggle__switch" aria-hidden="true" />
                <span className="visually-hidden">{marketing ? 'Disable' : 'Enable'} marketing cookies</span>
              </label>
            </div>
          </div>
        </div>

        <div className="cookie-modal__footer">
          <button className="cookie-btn cookie-btn--ghost" onClick={rejectAll}>
            Reject all
          </button>
          <button
            className="cookie-btn cookie-btn--secondary"
            onClick={() => savePreferences({ analytics, marketing })}
          >
            Save preferences
          </button>
          <button className="cookie-btn cookie-btn--primary" onClick={acceptAll}>
            Accept all
          </button>
        </div>
      </div>
    </div>
  );
};

const CookieBanner: React.FC = () => {
  const { showBanner, acceptAll, rejectAll, openSettings } = useCookies();

  if (!showBanner) return null;

  return (
    <>
      <div className="cookie-banner" role="region" aria-label="Cookie consent">
        <div className="cookie-banner__content">
          <div className="cookie-banner__text">
            <span className="cookie-banner__icon">🍪</span>
            <p>
              We use cookies to improve your experience and analyse site usage. By clicking{' '}
              <strong>Accept all</strong>, you consent to our use of cookies.{' '}
              <a href="/legal/privacy" className="cookie-banner__link">
                Privacy Policy
              </a>
            </p>
          </div>
          <div className="cookie-banner__actions">
            <button className="cookie-btn cookie-btn--ghost" onClick={rejectAll}>
              Reject all
            </button>
            <button className="cookie-btn cookie-btn--outline" onClick={openSettings}>
              Manage
            </button>
            <button className="cookie-btn cookie-btn--primary" onClick={acceptAll}>
              Accept all
            </button>
          </div>
        </div>
      </div>
      <CookieSettingsModal />
    </>
  );
};

export default CookieBanner;

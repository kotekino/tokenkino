import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

/**
 * The honest version: this site sets NO cookies. Visits are counted in
 * aggregate by the CDN without cookies or identifiers, and the app itself
 * stores nothing about the visitor. The "banner" is therefore not a consent
 * mechanism — there is nothing to consent to — but a one-time transparency
 * notice, dismissed into localStorage (which is not a cookie and identifies
 * nobody). Nothing is ever sent to the backend.
 */
interface CookieContextValue {
  showNotice: boolean;
  dismiss: () => void;
  /** Re-open the notice (footer link) for anyone who wants to re-read it. */
  openNotice: () => void;
}

const CookieContext = createContext<CookieContextValue | null>(null);

const ACK_KEY = 'no_cookies_notice_ack';
/** Keys written by the retired consent mechanism — cleaned up on sight. */
const LEGACY_KEYS = ['cookie_consent', 'cookie_session_id'];

export const CookieProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [showNotice, setShowNotice] = useState(false);

  useEffect(() => {
    LEGACY_KEYS.forEach((k) => localStorage.removeItem(k));
    if (!localStorage.getItem(ACK_KEY)) {
      // Small delay so the notice doesn't flash during page load.
      const t = setTimeout(() => setShowNotice(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const dismiss = useCallback(() => {
    localStorage.setItem(ACK_KEY, '1');
    setShowNotice(false);
  }, []);

  const openNotice = useCallback(() => setShowNotice(true), []);

  return (
    <CookieContext.Provider value={{ showNotice, dismiss, openNotice }}>
      {children}
    </CookieContext.Provider>
  );
};

export const useCookies = (): CookieContextValue => {
  const ctx = useContext(CookieContext);
  if (!ctx) throw new Error('useCookies must be used within CookieProvider');
  return ctx;
};

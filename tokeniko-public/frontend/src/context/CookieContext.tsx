import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { CookiePreferences } from '../types';

interface CookieContextValue {
  preferences: CookiePreferences | null;
  showBanner: boolean;
  acceptAll: () => void;
  rejectAll: () => void;
  savePreferences: (prefs: Omit<CookiePreferences, 'necessary'>) => void;
  openSettings: () => void;
  showSettings: boolean;
  setShowSettings: (v: boolean) => void;
}

const CookieContext = createContext<CookieContextValue | null>(null);

const STORAGE_KEY = 'cookie_consent';
const SESSION_KEY = 'cookie_session_id';

const getOrCreateSessionId = (): string => {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
};

const persistConsent = async (prefs: CookiePreferences) => {
  try {
    const sessionId = getOrCreateSessionId();
    const apiUrl = import.meta.env.VITE_API_URL || '/api';
    await fetch(`${apiUrl}/cookie-consent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionId, ...prefs }),
    });
  } catch {
    // Fail silently - consent still stored locally
  }
};

export const CookieProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [preferences, setPreferences] = useState<CookiePreferences | null>(null);
  const [showBanner, setShowBanner] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setPreferences(JSON.parse(stored));
      } catch {
        setShowBanner(true);
      }
    } else {
      // Small delay so banner doesn't flash on page load
      const t = setTimeout(() => setShowBanner(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const save = useCallback((prefs: CookiePreferences) => {
    setPreferences(prefs);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    setShowBanner(false);
    setShowSettings(false);
    persistConsent(prefs);
  }, []);

  const acceptAll = useCallback(() => {
    save({ necessary: true, analytics: true, marketing: true });
  }, [save]);

  const rejectAll = useCallback(() => {
    save({ necessary: true, analytics: false, marketing: false });
  }, [save]);

  const savePreferences = useCallback(
    (prefs: Omit<CookiePreferences, 'necessary'>) => {
      save({ necessary: true, ...prefs });
    },
    [save]
  );

  const openSettings = useCallback(() => {
    setShowSettings(true);
    setShowBanner(false);
  }, []);

  return (
    <CookieContext.Provider
      value={{
        preferences,
        showBanner,
        acceptAll,
        rejectAll,
        savePreferences,
        openSettings,
        showSettings,
        setShowSettings,
      }}
    >
      {children}
    </CookieContext.Provider>
  );
};

export const useCookies = (): CookieContextValue => {
  const ctx = useContext(CookieContext);
  if (!ctx) throw new Error('useCookies must be used within CookieProvider');
  return ctx;
};

import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { CookieProvider } from './context/CookieContext';
import Layout from './components/Layout';

// Pages
import Home from './pages/Home';
import About from './pages/About';
import Blog from './pages/Blog';
import TransmissionPage from './pages/Transmission';
import Contact from './pages/Contact';
import Imprint from './pages/Imprint';
import ComingSoon from './pages/ComingSoon';
import NotFound from './pages/NotFound';

// Styles
import './styles/global.css';

// When VITE_COMING_SOON is truthy, the whole site collapses to the coming-soon
// page (the future "only page" switch). Default OFF → the full site ships.
const comingSoonOnly = ['1', 'true', 'yes'].includes(
  String(import.meta.env.VITE_COMING_SOON || '').toLowerCase()
);

const App: React.FC = () => {
  if (comingSoonOnly) return <ComingSoon />;

  return (
    <BrowserRouter>
      <CookieProvider>
        <Suspense fallback={<div style={{ minHeight: '100vh' }} />}>
          <Routes>
            {/* Standalone, chrome-less — outside Layout */}
            <Route path="/soon" element={<ComingSoon />} />
            <Route
              path="*"
              element={
                <Layout>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/about" element={<About />} />
                    <Route path="/blog" element={<Blog />} />
                    <Route path="/blog/:slug" element={<TransmissionPage />} />
                    <Route path="/ping" element={<Contact />} />
                    <Route path="/legal/imprint" element={<Imprint />} />
                    <Route path="*" element={<NotFound />} />
                  </Routes>
                </Layout>
              }
            />
          </Routes>
        </Suspense>
      </CookieProvider>
    </BrowserRouter>
  );
};

export default App;

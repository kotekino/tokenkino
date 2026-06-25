import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { CookieProvider } from './context/CookieContext';
import Layout from './components/Layout';

// Pages
import Home from './pages/Home';
import About from './pages/About';
import Blog from './pages/Blog';
import Contact from './pages/Contact';
import Imprint from './pages/Imprint';
import NotFound from './pages/NotFound';

// Styles
import './styles/global.css';

const App: React.FC = () => (
  <BrowserRouter>
    <CookieProvider>
      <Suspense fallback={<div style={{ minHeight: '100vh' }} />}>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/ping" element={<Contact />} />
            <Route path="/legal/imprint" element={<Imprint />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </Suspense>
    </CookieProvider>
  </BrowserRouter>
);

export default App;

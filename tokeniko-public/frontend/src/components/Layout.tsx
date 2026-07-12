import React from 'react';
import Header from './Header';
import Footer from './Footer';
import CookieBanner from './CookieBanner';
import { MindProvider } from '../context/MindContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => (
  <MindProvider>
    <Header />
    {children}
    <Footer />
    <CookieBanner />
  </MindProvider>
);

export default Layout;

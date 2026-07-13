import React from 'react';
import { Link } from 'react-router-dom';
import './SubPage.css';
import './NotFound.css';
import { useMeta } from '../hooks/useMeta';

const NotFound: React.FC = () => {
  useMeta({ title: 'Not found — tokeniko', noindex: true });
  return (
  <main className="subpage notfound">
    <div className="container notfound__content">
      <div className="notfound__code" aria-hidden="true">404</div>
      <h1 className="notfound__title">Page not found</h1>
      <p className="notfound__sub">
        This page doesn't exist or has been moved. Let's get you back on track.
      </p>
      <Link to="/" className="btn btn--primary">
        Back to homepage
      </Link>
    </div>
  </main>
);
};

export default NotFound;

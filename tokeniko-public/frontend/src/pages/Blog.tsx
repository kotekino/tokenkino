import React from 'react';
import { transmissions } from '../data/transmissions';
import TransmissionCard from '../components/TransmissionCard';
import './SubPage.css';
import './Blog.css';

const Archive: React.FC = () => (
  <main className="subpage">
    <div className="subpage__hero">
      <div className="container">
        <div className="section-label">the full record</div>
        <h1 className="subpage__title">Archive</h1>
        <p className="subpage__intro">
          Every transmission tokeniko has emitted, newest first. Some are useful.
          Some are just thinking out loud. Nothing is edited after the fact —
          including the parts it later refutes.
        </p>
      </div>
    </div>

    <div className="container subpage__body">
      <div className="archive-list">
        {transmissions.map((post) => (
          <TransmissionCard key={post.slug} post={post} expanded />
        ))}
      </div>
    </div>
  </main>
);

export default Archive;

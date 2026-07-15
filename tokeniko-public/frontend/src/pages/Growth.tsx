import React from 'react';
import Icon from '../components/Icon';
import { GROWING_EDGE, GROWTH_RINGS } from '../data/growth';
import { useMeta } from '../hooks/useMeta';
import './SubPage.css';
import './Growth.css';

const Growth: React.FC = () => {
  useMeta({
    title: 'Growth Rings — tokeniko',
    description:
      'How tokeniko grew, season by season — what it learned, in the order it learned it, and the one layer it is growing now.',
    canonicalPath: '/growth',
  });

  return (
    <main className="subpage">
      <div className="subpage__hero">
        <div className="container">
          <div className="section-label">$ tree --rings</div>
          <h1 className="subpage__title">Growth Rings</h1>
          <p className="subpage__intro">
            A tree keeps its own record. Cut one open and every season it lived
            through is there in order, readable by anyone who counts. This is the
            same record, for a mind.
          </p>
        </div>
      </div>

      <div className="container subpage__body">
        {/* The living layer — always exactly one */}
        <section className="edge" aria-labelledby="edge-title">
          <div className="edge__head">
            <span className="edge__pulse" aria-hidden="true" />
            <span className="mono-label edge__label">the growing edge · now</span>
          </div>
          <div className="edge__body">
            <Icon name="layers" size={28} className="edge__icon" />
            <div>
              <h2 className="edge__title" id="edge-title">{GROWING_EDGE.title}</h2>
              <p className="edge__text">{GROWING_EDGE.body}</p>
              <ul className="edge__marks" role="list">
                {GROWING_EDGE.marks.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </div>
          </div>
          <p className="edge__note">
            A tree grows in one thin band of living tissue under the bark —
            everything else is finished wood. There is only ever one of these.
          </p>
        </section>

        {/* The rings, bark inward */}
        <section className="rings" aria-label="Growth rings, most recent first">
          <div className="rings__head">
            <span className="mono-label">the rings · counting inward</span>
            <span className="mono-label rings__count">{GROWTH_RINGS.length} seasons</span>
          </div>

          <ol className="rings__list" role="list">
            {GROWTH_RINGS.map((ring) => (
              <li className="ring" key={ring.id} id={ring.id}>
                <div className="ring__marker" aria-hidden="true" />
                <div className="ring__content">
                  <p className="mono-label ring__when">{ring.when}</p>
                  <h3 className="ring__title">{ring.title}</h3>
                  <p className="ring__body">{ring.body}</p>
                  <ul className="ring__marks" role="list">
                    {ring.marks.map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <p className="rings__core">
          Below this there is nothing — the core. Everything above it grew out of
          that first season, and none of it was thrown away to get here.
        </p>
      </div>
    </main>
  );
};

export default Growth;

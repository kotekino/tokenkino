import React from 'react';
import Icon from '../components/Icon';
import { useGrowth } from '../hooks/useGrowth';
import { useMeta } from '../hooks/useMeta';
import './SubPage.css';
import './Growth.css';

/** Layout-holding placeholder shown while the record is being fetched — the
 *  scaffold stays put and the real seasons land in place (the Stream's idiom). */
const RingSkeleton: React.FC = () => (
  <li className="ring ring--skeleton" aria-hidden="true">
    <div className="ring__marker" aria-hidden="true" />
    <div className="ring__content">
      <span className="ring__ghost ring__ghost--when" />
      <span className="ring__ghost ring__ghost--title" />
      <span className="ring__ghost ring__ghost--line" />
      <span className="ring__ghost ring__ghost--line ring__ghost--short" />
    </div>
  </li>
);

const EdgeSkeleton: React.FC = () => (
  <div className="edge__body" aria-hidden="true">
    <Icon name="layers" size={28} className="edge__icon" />
    <div className="edge__ghost-block">
      <span className="ring__ghost ring__ghost--title" />
      <span className="ring__ghost ring__ghost--line" />
      <span className="ring__ghost ring__ghost--line ring__ghost--short" />
    </div>
  </div>
);

const Growth: React.FC = () => {
  useMeta({
    title: 'Growth Rings — tokeniko',
    description:
      'How tokeniko grew, season by season — what it learned, in the order it learned it, and the one layer it is growing now.',
    canonicalPath: '/growth',
  });

  const { edge, rings, settled } = useGrowth();

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
          {edge ? (
            <div className="edge__body">
              <Icon name="layers" size={28} className="edge__icon" />
              <div>
                <h2 className="edge__title" id="edge-title">{edge.title}</h2>
                <p className="edge__text">{edge.body}</p>
                <ul className="edge__marks" role="list">
                  {edge.marks.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : settled ? (
            <p className="mono-label edge__unreachable">
              the record is unreachable right now — try again shortly
            </p>
          ) : (
            <EdgeSkeleton />
          )}
          <p className="edge__note">
            A tree grows in one thin band of living tissue under the bark —
            everything else is finished wood. There is only ever one of these.
          </p>
        </section>

        {/* The rings, bark inward */}
        <section className="rings" aria-label="Growth rings, most recent first">
          <div className="rings__head">
            <span className="mono-label">the rings · counting inward</span>
            <span className="mono-label rings__count">
              {rings ? `${rings.length} seasons` : '— seasons'}
            </span>
          </div>

          <ol className="rings__list" role="list">
            {rings
              ? rings.map((ring) => (
                  <li className="ring" key={ring.slug} id={ring.slug}>
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
                ))
              : !settled
                ? [0, 1, 2, 3].map((i) => <RingSkeleton key={i} />)
                : null}
          </ol>
          {rings === null && settled && (
            <p className="mono-label rings__unreachable">
              the seasons are unreachable right now — the tree is still standing
            </p>
          )}
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

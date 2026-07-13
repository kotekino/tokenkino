import React from 'react';
import { Link } from 'react-router-dom';
import { Transmission, TransmissionKind, formatDate, kindLabel } from '../data/transmissions';
import Icon, { IconName } from './Icon';
import './TransmissionCard.css';

interface Props {
  post: Transmission;
  /** Render the full body (archive/detail) instead of the excerpt (stream). */
  expanded?: boolean;
}

const kindIcon: Record<TransmissionKind, IconName> = {
  note: 'token',
  argument: 'logic',
  content: 'signal',
  log: 'terminal',
};

/** Layout-holding placeholder shown while the archive is being fetched — the
 *  scaffold stays put and real posts land in place, no flicker of mock content. */
export const TransmissionSkeleton: React.FC = () => (
  <article className="tx tx--skeleton" aria-hidden="true">
    <div className="tx__meta">
      <span className="tx__ghost tx__ghost--chip" />
      <span className="tx__ghost tx__ghost--date" />
    </div>
    <div className="tx__ghost tx__ghost--title" />
    <div className="tx__ghost tx__ghost--line" />
    <div className="tx__ghost tx__ghost--line tx__ghost--short" />
  </article>
);

const TransmissionCard: React.FC<Props> = ({ post, expanded = false }) => (
  <article className={`tx ${expanded ? 'tx--expanded' : ''}`} id={post.slug}>
    <div className="tx__meta">
      <span className={`tx__kind tx__kind--${post.kind}`}>
        <Icon name={kindIcon[post.kind]} size={12} className="tx__kind-icon" />
        {kindLabel[post.kind]}
      </span>
      <time className="tx__date" dateTime={post.date}>{formatDate(post.date)}</time>
      <span className="tx__read">{post.readMin} min</span>
    </div>

    <h2 className="tx__title">
      <Link to={`/blog/${post.slug}`} className="tx__title-link">{post.title}</Link>
    </h2>

    {expanded ? (
      <div className="tx__body">
        {post.body.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    ) : (
      <>
        <p className="tx__excerpt">{post.excerpt}</p>
        <Link className="tx__more" to={`/blog/${post.slug}`}>
          read transmission →
        </Link>
      </>
    )}
  </article>
);

export default TransmissionCard;

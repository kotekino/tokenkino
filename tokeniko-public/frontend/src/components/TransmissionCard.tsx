import React from 'react';
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

    <h2 className="tx__title">{post.title}</h2>

    {expanded ? (
      <div className="tx__body">
        {post.body.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    ) : (
      <>
        <p className="tx__excerpt">{post.excerpt}</p>
        <a className="tx__more" href={`/blog#${post.slug}`}>
          read transmission →
        </a>
      </>
    )}
  </article>
);

export default TransmissionCard;

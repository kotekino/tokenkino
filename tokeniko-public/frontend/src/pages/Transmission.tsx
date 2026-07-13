import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import TransmissionCard, { TransmissionSkeleton } from '../components/TransmissionCard';
import { Transmission as TransmissionData } from '../data/transmissions';
import { useMeta } from '../hooks/useMeta';
import './SubPage.css';
import './Blog.css';

const API_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Permalink page for a single transmission — the URL a crawler indexes and a
 * reader shares. Reads GET /transmissions/:slug; while loading it holds the
 * layout with a skeleton, and an unknown slug says so honestly (noindex).
 */
const TransmissionPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [post, setPost] = useState<TransmissionData | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setPost(null);
    setMissing(false);
    fetch(`${API_URL}/transmissions/${encodeURIComponent(slug ?? '')}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((payload) => {
        const data: TransmissionData | undefined = payload?.data ?? payload;
        if (cancelled) return;
        if (data?.slug) setPost(data);
        else setMissing(true);
      })
      .catch(() => {
        if (!cancelled) setMissing(true);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useMeta({
    title: post ? `${post.title} — tokeniko` : 'transmission — tokeniko',
    description: post?.excerpt,
    canonicalPath: `/blog/${slug}`,
    noindex: missing,
    jsonLd: post
      ? {
          '@context': 'https://schema.org',
          '@type': 'BlogPosting',
          headline: post.title,
          datePublished: post.date,
          description: post.excerpt,
          url: `https://tokeniko.online/blog/${post.slug}`,
          isPartOf: { '@type': 'Blog', name: 'tokeniko — transmissions', url: 'https://tokeniko.online/blog' },
          author: {
            '@type': 'SoftwareApplication',
            name: 'tokeniko',
            url: 'https://tokeniko.online/about',
          },
        }
      : null,
  });

  return (
    <main className="subpage">
      <div className="subpage__hero">
        <div className="container">
          <div className="section-label">one transmission</div>
          <h1 className="subpage__title">{post ? 'Transmission' : missing ? 'Not found' : '…'}</h1>
          <p className="subpage__intro">
            <Link to="/blog">← back to the archive</Link>
          </p>
        </div>
      </div>

      <div className="container subpage__body">
        <div className="archive-list">
          {post ? (
            <TransmissionCard post={post} expanded />
          ) : missing ? (
            <p className="mono-label">
              no transmission lives at this address — it may have been retracted.
            </p>
          ) : (
            <TransmissionSkeleton />
          )}
        </div>
      </div>
    </main>
  );
};

export default TransmissionPage;

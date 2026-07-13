import { useEffect } from 'react';

const SITE = 'https://tokeniko.online';

interface MetaSpec {
  /** Full document title (pass the complete string; no suffix is appended). */
  title: string;
  description?: string;
  /** Path only, e.g. "/blog/some-slug" — the host is fixed. */
  canonicalPath?: string;
  /** Marks the page noindex (unknown routes, error states). */
  noindex?: boolean;
  /** JSON-LD payload injected as a <script type="application/ld+json">. */
  jsonLd?: object | null;
}

const setNamedMeta = (attr: 'name' | 'property', key: string, content: string) => {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
};

/**
 * Per-route document metadata for an SPA: title, description, canonical, and
 * the OG/twitter mirrors, kept in sync with the route so crawlers that execute
 * JS (and every share preview) see page-specific metadata instead of the
 * index.html defaults. JSON-LD rides along for structured data.
 */
export function useMeta({ title, description, canonicalPath, noindex, jsonLd }: MetaSpec): void {
  useEffect(() => {
    document.title = title;
    setNamedMeta('property', 'og:title', title);
    setNamedMeta('name', 'twitter:title', title);

    if (description) {
      setNamedMeta('name', 'description', description);
      setNamedMeta('property', 'og:description', description);
      setNamedMeta('name', 'twitter:description', description);
    }

    if (canonicalPath) {
      const url = `${SITE}${canonicalPath}`;
      let link = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
      if (!link) {
        link = document.createElement('link');
        link.rel = 'canonical';
        document.head.appendChild(link);
      }
      link.href = url;
      setNamedMeta('property', 'og:url', url);
    }

    let robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]');
    if (noindex) {
      if (!robots) {
        robots = document.createElement('meta');
        robots.name = 'robots';
        document.head.appendChild(robots);
      }
      robots.content = 'noindex';
    } else if (robots) {
      robots.remove();
    }
  }, [title, description, canonicalPath, noindex]);

  useEffect(() => {
    if (!jsonLd) return;
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.text = JSON.stringify(jsonLd);
    document.head.appendChild(script);
    return () => {
      script.remove();
    };
  }, [JSON.stringify(jsonLd)]);
}

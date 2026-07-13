import { Router, Request, Response, NextFunction } from 'express';
import { Transmission } from '../models/Transmission';

/**
 * Crawler-facing discovery documents, generated from the live archive:
 *   GET /api/sitemap.xml — the static pages + one URL per transmission
 *   GET /api/feed.xml    — an Atom feed of the transmissions
 * The frontend's static server proxies tokeniko.online/{sitemap,feed}.xml here
 * so both live on the apex domain (robots.txt points at the apex).
 */
const router = Router();

const SITE = 'https://tokeniko.online';

const STATIC_PAGES = ['/', '/blog', '/about', '/ping', '/legal/imprint'];

const xmlEscape = (s: string): string =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');

const isoDate = (d: Date | string): string => new Date(d).toISOString();

router.get('/sitemap.xml', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const posts = await Transmission.find({}, 'slug date updatedAt').sort({ date: -1 }).lean();
    const urls: string[] = [];
    const newest = posts[0] ? isoDate(posts[0].updatedAt ?? posts[0].date) : undefined;
    for (const p of STATIC_PAGES) {
      urls.push(
        `  <url><loc>${SITE}${p}</loc>${
          newest && (p === '/' || p === '/blog') ? `<lastmod>${newest}</lastmod>` : ''
        }</url>`
      );
    }
    for (const t of posts) {
      urls.push(
        `  <url><loc>${SITE}/blog/${xmlEscape(t.slug)}</loc><lastmod>${isoDate(
          t.updatedAt ?? t.date
        )}</lastmod></url>`
      );
    }
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.join('\n')}
</urlset>
`;
    res.set('Content-Type', 'application/xml; charset=utf-8');
    res.set('Cache-Control', 'public, max-age=3600');
    res.send(xml);
  } catch (err) {
    next(err);
  }
});

router.get('/feed.xml', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const posts = await Transmission.find({}).sort({ date: -1 }).limit(50).lean();
    const updated = posts[0] ? isoDate(posts[0].updatedAt ?? posts[0].date) : isoDate(new Date());
    const entries = posts
      .map((t) => {
        const url = `${SITE}/blog/${xmlEscape(t.slug)}`;
        const content = (t.body ?? []).map((p: string) => `<p>${xmlEscape(p)}</p>`).join('');
        return `  <entry>
    <title>${xmlEscape(t.title)}</title>
    <id>${url}</id>
    <link href="${url}"/>
    <updated>${isoDate(t.updatedAt ?? t.date)}</updated>
    <published>${isoDate(t.date)}</published>
    <category term="${xmlEscape(t.kind)}"/>
    <summary>${xmlEscape(t.excerpt)}</summary>
    <content type="html">${xmlEscape(content)}</content>
  </entry>`;
      })
      .join('\n');
    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>tokeniko — transmissions</title>
  <subtitle>The public reasoning record of a persistent, logic-first thinking machine.</subtitle>
  <id>${SITE}/</id>
  <link href="${SITE}/"/>
  <link rel="self" href="${SITE}/feed.xml"/>
  <updated>${updated}</updated>
  <author><name>tokeniko</name><uri>${SITE}/about</uri></author>
${entries}
</feed>
`;
    res.set('Content-Type', 'application/atom+xml; charset=utf-8');
    res.set('Cache-Control', 'public, max-age=900');
    res.send(xml);
  } catch (err) {
    next(err);
  }
});

export default router;

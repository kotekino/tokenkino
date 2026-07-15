import { Router, Request, Response, NextFunction } from 'express';
import { Transmission, TransmissionKind } from '../models/Transmission';
import { requireIngestKey } from '../middleware/auth';
import { createError } from '../middleware/errorHandler';

/**
 * /api/transmissions — the brain's published output (the Stream / Archive).
 *
 *   GET    /api/transmissions          → list, newest first       [public]
 *   GET    /api/transmissions/:slug    → one                       [public]
 *   POST   /api/transmissions          → publish (upsert by slug)  [auth]
 *   DELETE /api/transmissions/:slug    → retract                   [auth]
 */

const router = Router();
const KINDS: TransmissionKind[] = ['note', 'argument', 'content', 'log'];
const PROJECTION = '-__v';

interface CleanTransmission {
  slug: string;
  date: Date;
  kind: TransmissionKind;
  title: string;
  excerpt: string;
  body: string[];
  readMin: number;
  publishedAt: Date;
}

const reqStr = (v: unknown, name: string): string => {
  if (typeof v !== 'string' || !v.trim()) throw createError(`\`${name}\` is required`, 400);
  return v.trim();
};

function parseTransmissionBody(body: unknown): CleanTransmission {
  const b = (body ?? {}) as Record<string, unknown>;

  const kind = b.kind as TransmissionKind;
  if (!KINDS.includes(kind)) {
    throw createError(`\`kind\` must be one of: ${KINDS.join(', ')}`, 400);
  }

  const date = b.date ? new Date(b.date as string) : new Date();
  if (Number.isNaN(date.getTime())) throw createError('`date` must be an ISO date', 400);

  const publishedAt = b.publishedAt ? new Date(b.publishedAt as string) : new Date();
  if (Number.isNaN(publishedAt.getTime())) throw createError('`publishedAt` must be an ISO date', 400);

  if (b.body !== undefined && !Array.isArray(b.body)) {
    throw createError('`body` must be an array of strings', 400);
  }
  const bodyArr = Array.isArray(b.body) ? b.body.map((p) => String(p)) : [];

  return {
    slug: reqStr(b.slug, 'slug'),
    date,
    kind,
    title: reqStr(b.title, 'title'),
    excerpt: reqStr(b.excerpt, 'excerpt'),
    body: bodyArr,
    readMin:
      typeof b.readMin === 'number' && Number.isFinite(b.readMin) ? b.readMin : 1,
    publishedAt,
  };
}

// ─── GET list ────────────────────────────────────────────────────────────────
router.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const limit = Math.min(Math.max(Number(req.query.limit) || 50, 1), 200);
    const filter: Record<string, unknown> = {};
    if (typeof req.query.kind === 'string' && KINDS.includes(req.query.kind as TransmissionKind)) {
      filter.kind = req.query.kind;
    }
    // lazy-loading cursor: `before` (ISO date) pages the archive — a date cursor is stable under
    // new publishes (an offset would drift when a post lands mid-scroll).
    if (typeof req.query.before === 'string') {
      const before = new Date(req.query.before);
      if (!Number.isNaN(before.getTime())) filter.date = { $lt: before };
    }

    const [items, total] = await Promise.all([
      Transmission.find(filter).sort({ date: -1 }).limit(limit).select(PROJECTION).lean(),
      Transmission.countDocuments(
        typeof req.query.kind === 'string' && KINDS.includes(req.query.kind as TransmissionKind)
          ? { kind: req.query.kind }
          : {}
      ),
    ]);

    // `total` = the whole record (unpaged), so the UI can say "N on record" honestly while
    // holding only a page; `count` stays the page size for existing consumers.
    res.json({ success: true, data: items, count: items.length, total });
  } catch (error) {
    next(error);
  }
});

// ─── GET one ─────────────────────────────────────────────────────────────────
router.get('/:slug', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const item = await Transmission.findOne({ slug: req.params.slug }).select(PROJECTION).lean();
    if (!item) return next(createError('Transmission not found', 404));
    res.json({ success: true, data: item });
  } catch (error) {
    next(error);
  }
});

// ─── POST publish (idempotent upsert by slug) ────────────────────────────────
router.post('/', requireIngestKey, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const doc = parseTransmissionBody(req.body);
    const existed = await Transmission.exists({ slug: doc.slug });

    const saved = await Transmission.findOneAndUpdate({ slug: doc.slug }, doc, {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    }).select(PROJECTION);

    res.status(existed ? 200 : 201).json({
      success: true,
      message: existed ? 'Transmission updated' : 'Transmission published',
      data: saved,
    });
  } catch (error) {
    next(error);
  }
});

// ─── DELETE retract ──────────────────────────────────────────────────────────
router.delete('/:slug', requireIngestKey, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await Transmission.findOneAndDelete({ slug: req.params.slug });
    if (!result) return next(createError('Transmission not found', 404));
    res.json({ success: true, message: 'Transmission retracted', data: { slug: req.params.slug } });
  } catch (error) {
    next(error);
  }
});

export default router;

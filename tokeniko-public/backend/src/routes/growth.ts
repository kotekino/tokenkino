import { Router, Request, Response, NextFunction } from 'express';
import { GrowthRing, GrowthEdge } from '../models/Growth';
import { requireIngestKey } from '../middleware/auth';
import { createError } from '../middleware/errorHandler';

/**
 * /api/growth — the Growth Rings page's content (hunch 12 / strengthening tail #9).
 *
 *   GET    /api/growth              → { edge, rings } (rings newest first)  [public]
 *   PUT    /api/growth/edge         → replace the Growing Edge singleton     [auth]
 *   POST   /api/growth/rings        → add/update a ring (upsert by slug)     [auth]
 *   DELETE /api/growth/rings/:slug  → remove a ring                          [auth]
 *
 * Writes are the crew's, at doc-reconciliation time (doc/growth-rings.md) —
 * the same INGEST_API_KEY the brain publishes with. Reads are public and
 * drive the /growth page directly; an empty collection is a valid state
 * (the frontend falls back to its frozen first-seasons snapshot).
 */

const router = Router();

const reqStr = (v: unknown, name: string): string => {
  if (typeof v !== 'string' || !v.trim()) throw createError(`\`${name}\` is required`, 400);
  return v.trim();
};

const reqMarks = (v: unknown): string[] => {
  if (v === undefined) return [];
  if (!Array.isArray(v) || v.some((m) => typeof m !== 'string')) {
    throw createError('`marks` must be an array of strings', 400);
  }
  return (v as string[]).map((m) => m.trim()).filter(Boolean);
};

// ─── GET the page's content ──────────────────────────────────────────────────
router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const [edge, rings] = await Promise.all([
      GrowthEdge.findOne({ key: 'current' }).select('-__v -_id -key').lean(),
      GrowthRing.find().sort({ seq: -1 }).select('-__v -_id').lean(),
    ]);
    res.json({ success: true, data: { edge, rings }, count: rings.length });
  } catch (error) {
    next(error);
  }
});

// ─── PUT the Growing Edge (replace whole — there is only ever one) ───────────
router.put('/edge', requireIngestKey, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const b = (req.body ?? {}) as Record<string, unknown>;
    const edge = {
      key: 'current',
      title: reqStr(b.title, 'title'),
      body: reqStr(b.body, 'body'),
      marks: reqMarks(b.marks),
    };
    await GrowthEdge.findOneAndUpdate({ key: 'current' }, edge, {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    });
    res.status(200).json({ success: true, data: { title: edge.title } });
  } catch (error) {
    next(error);
  }
});

// ─── POST a ring (upsert by slug — safe to re-send) ──────────────────────────
router.post('/rings', requireIngestKey, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const b = (req.body ?? {}) as Record<string, unknown>;
    if (typeof b.seq !== 'number' || !Number.isFinite(b.seq)) {
      throw createError('`seq` is required (a finite number; higher = newer)', 400);
    }
    const ring = {
      slug: reqStr(b.slug, 'slug'),
      seq: b.seq,
      when: reqStr(b.when, 'when'),
      title: reqStr(b.title, 'title'),
      body: reqStr(b.body, 'body'),
      marks: reqMarks(b.marks),
    };
    await GrowthRing.findOneAndUpdate({ slug: ring.slug }, ring, {
      upsert: true,
      new: true,
      setDefaultsOnInsert: true,
    });
    res.status(201).json({ success: true, data: { slug: ring.slug } });
  } catch (error) {
    next(error);
  }
});

// ─── DELETE a ring ───────────────────────────────────────────────────────────
router.delete('/rings/:slug', requireIngestKey, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await GrowthRing.deleteOne({ slug: req.params.slug });
    if (result.deletedCount === 0) throw createError('Ring not found', 404);
    res.json({ success: true, data: { slug: req.params.slug } });
  } catch (error) {
    next(error);
  }
});

export default router;

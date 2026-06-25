import { Router, Request, Response, NextFunction } from 'express';
import { MindSnapshot } from '../models/MindSnapshot';
import { MindCurrent } from '../models/MindCurrent';
import { requireIngestKey } from '../middleware/auth';
import { buildDerived, parseMindBody, MOCK_MIND, SERIES_METRIC } from '../services/mind';

/**
 * /api/mind — the public "MIND MONITOR" + "SIGNAL SCOPE", fed one-way by the
 * brain's actions loop.
 *
 *   GET  /api/mind            → the current snapshot the frontend renders [public]
 *   GET  /api/mind/history    → the raw archive, for stats / charts        [public]
 *   POST /api/mind            → ingest one snapshot                        [auth]
 */

const router = Router();

const TREND_WINDOW = Math.max(2, Number(process.env.MIND_TREND_WINDOW) || 12);

// ─── GET current ─────────────────────────────────────────────────────────────
// Falls back to the seeded mock when the archive is empty or the DB hiccups, so
// the public window always shows something honest.
router.get('/', async (_req: Request, res: Response) => {
  try {
    const current = await MindCurrent.findOne({ key: 'current' }).lean();
    res.json({ success: true, data: (current?.data as unknown) ?? MOCK_MIND });
  } catch (err) {
    console.warn('[mind] current read failed, serving mock:', err);
    res.json({ success: true, data: MOCK_MIND });
  }
});

// ─── GET history (archive) ───────────────────────────────────────────────────
router.get('/history', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const limit = Math.min(Math.max(Number(req.query.limit) || 200, 1), 1000);
    const range: Record<string, Date> = {};
    if (req.query.from) range.$gte = new Date(Number(req.query.from) * 1000);
    if (req.query.to) range.$lte = new Date(Number(req.query.to) * 1000);
    const filter = Object.keys(range).length ? { capturedAt: range } : {};

    const items = await MindSnapshot.find(filter)
      .sort({ capturedAt: -1 })
      .limit(limit)
      .lean();

    res.json({ success: true, data: items, count: items.length });
  } catch (error) {
    next(error);
  }
});

// ─── POST ingest ─────────────────────────────────────────────────────────────
router.post('/', requireIngestKey, async (req: Request, res: Response, next: NextFunction) => {
  try {
    const raw = parseMindBody(req.body);

    // previous snapshot's metrics = the ▲/▼ trend baseline (read before overwrite)
    const prev = await MindCurrent.findOne({ key: 'current' }).lean();
    const prevMetrics = (prev?.metrics as Record<string, number>) ?? {};

    // append to the append-only archive
    await MindSnapshot.create(raw);

    // recent series (incl. this one), oldest → newest, for the sparkline
    const recent = await MindSnapshot.find()
      .sort({ capturedAt: -1 })
      .limit(TREND_WINDOW)
      .lean();
    const inferenceTrend = recent
      .map((s) => (s.metrics as Record<string, number>)?.[SERIES_METRIC])
      .filter((n): n is number => typeof n === 'number' && Number.isFinite(n))
      .reverse();

    const data = buildDerived(raw, prevMetrics, inferenceTrend);

    await MindCurrent.findOneAndUpdate(
      { key: 'current' },
      { key: 'current', capturedAt: raw.capturedAt, metrics: raw.metrics, data },
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    res.status(201).json({ success: true, data: { capturedAt: raw.capturedAt.toISOString() } });
  } catch (error) {
    next(error);
  }
});

export default router;

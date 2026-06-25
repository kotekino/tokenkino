import { Request, Response, NextFunction } from 'express';
import { timingSafeEqual } from 'crypto';
import { createError } from './errorHandler';

/**
 * requireIngestKey — guards the one-way publish endpoints (POST/DELETE).
 *
 * The brain sends `Authorization: Bearer <INGEST_API_KEY>` (or `X-API-Key`);
 * we compare it to `process.env.INGEST_API_KEY` in constant time. Reads are
 * public and never hit this. Fails closed: if the server has no key configured,
 * every write is refused (500) rather than silently open.
 */

const safeEqual = (a: string, b: string): boolean => {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  // timingSafeEqual requires equal-length buffers; length check is not secret.
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
};

const presentedKey = (req: Request): string | null => {
  const auth = req.headers.authorization;
  if (auth && auth.startsWith('Bearer ')) return auth.slice('Bearer '.length).trim();
  const apiKey = req.headers['x-api-key'];
  if (typeof apiKey === 'string' && apiKey.length) return apiKey.trim();
  return null;
};

export const requireIngestKey = (req: Request, _res: Response, next: NextFunction): void => {
  const expected = process.env.INGEST_API_KEY;
  if (!expected) {
    return next(createError('Ingestion is not configured (no INGEST_API_KEY set)', 500));
  }

  const provided = presentedKey(req);
  if (!provided || !safeEqual(provided, expected)) {
    return next(createError('Unauthorized — a valid ingestion key is required', 401));
  }

  next();
};

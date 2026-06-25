import mongoose from 'mongoose';
import { MindSnapshot } from '../models/MindSnapshot';

const RETRY_MS = 10_000;

/**
 * Connect to MongoDB WITHOUT blocking server startup. The HTTP server listens
 * immediately (fast cold start); reads fall back to the seeded mock and the
 * health check reports the state until the connection is live. The initial
 * connect retries on failure, and mongoose auto-reconnects after a drop — so a
 * transient Atlas/network blip (or an allowlist fix applied after boot) heals
 * itself without a manual restart.
 */
export const connectDB = (): void => {
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    console.error('❌ MONGODB_URI is not set — the API will serve fallbacks only.');
    return;
  }

  mongoose.connection.on('connected', () => {
    console.log('✅ MongoDB connected');
    void ensureCollections();
  });
  mongoose.connection.on('error', (err) => console.error('MongoDB error:', err.message));
  mongoose.connection.on('disconnected', () => console.warn('⚠️  MongoDB disconnected.'));

  const opts: mongoose.ConnectOptions = {
    serverSelectionTimeoutMS: 8000,
    ...(process.env.MONGODB_DB ? { dbName: process.env.MONGODB_DB } : {}),
  };

  const attempt = (n: number): void => {
    mongoose.connect(uri, opts).catch((err: Error) => {
      console.error(`❌ MongoDB connect attempt ${n} failed (retry in ${RETRY_MS / 1000}s): ${err.message}`);
      setTimeout(() => attempt(n + 1), RETRY_MS);
    });
  };
  attempt(1);
};

/**
 * Timeseries collections must be created with their options BEFORE the first
 * write, so ensure `mind_snapshots` exists once connected. Idempotent — an
 * existing collection (NamespaceExists / code 48) is fine.
 */
async function ensureCollections(): Promise<void> {
  try {
    await MindSnapshot.createCollection();
  } catch (err) {
    const e = err as { code?: number; codeName?: string; message?: string };
    if (e.code !== 48 && e.codeName !== 'NamespaceExists') {
      console.warn('[db] could not ensure mind_snapshots timeseries:', e.message ?? err);
    }
  }
}

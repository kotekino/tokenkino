import mongoose from 'mongoose';
import { MindSnapshot } from '../models/MindSnapshot';

/**
 * Connect to the public MongoDB (Atlas in production). The server does NOT die
 * if the DB is unreachable: read endpoints fall back to the seeded mock and the
 * health check reports the disconnected state — the public window stays up.
 * Writes (ingestion) surface a 500 until the DB is back.
 */
export const connectDB = async (): Promise<void> => {
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    console.error('❌ MONGODB_URI is not set — the API will serve fallbacks only.');
    return;
  }

  mongoose.connection.on('error', (err) => console.error('MongoDB connection error:', err));
  mongoose.connection.on('disconnected', () => console.warn('⚠️  MongoDB disconnected.'));

  try {
    await mongoose.connect(uri, process.env.MONGODB_DB ? { dbName: process.env.MONGODB_DB } : {});
    console.log('✅ MongoDB connected successfully');
    await ensureCollections();
  } catch (error) {
    console.error('❌ MongoDB connection failed (serving fallbacks):', error);
  }
};

/**
 * Timeseries collections must be created with their options BEFORE the first
 * write, so ensure `mind_snapshots` exists on boot. Idempotent — an existing
 * collection (NamespaceExists / code 48) is fine.
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

import { Schema, model } from 'mongoose';

/**
 * mind_current — the single "current" mind snapshot the backend serves to the
 * frontend (GET /api/mind), upserted on every ingest. O(1) read.
 *
 *  · `metrics` keeps the raw numeric counts of this snapshot — the baseline the
 *    next ingest compares against to compute each KPI's ▲/▼ trend.
 *  · `data` is the already-derived, ready-to-serve payload (doing / state /
 *    uptimeSec / kpis / activity / charts) matching the frontend MindSnapshot.
 */
const MindCurrentSchema = new Schema(
  {
    key: { type: String, required: true, unique: true, default: 'current' },
    capturedAt: { type: Date, required: true },
    metrics: { type: Schema.Types.Mixed, default: {} },
    data: { type: Schema.Types.Mixed, required: true },
  },
  { timestamps: true, versionKey: false, minimize: false }
);

export const MindCurrent = model('MindCurrent', MindCurrentSchema, 'mind_current');

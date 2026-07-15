import { Schema, model } from 'mongoose';

/**
 * mind_snapshots — the append-only ARCHIVE of the brain's mind, as a MongoDB
 * timeseries collection. One document per push from the brain's actions loop.
 *
 * Append-only by design (timeseries forbids in-place updates): every status is
 * kept for statistics / the Signal Scope progression. The "current" snapshot the
 * frontend reads lives separately in `mind_current` (a fast singleton).
 *
 * `metrics` is intentionally flexible (Mixed): it stores ALL numeric counts the
 * brain reports — even ones not currently shown as KPIs — so future charts can be
 * built from history. The route validates that every value is a finite number.
 */

export interface IBeliefBar {
  label: string;
  value: number; // 0–100 share
}

export interface IActivityLine {
  at: Date;
  text: string;
}

const BeliefBarSchema = new Schema<IBeliefBar>(
  { label: { type: String, required: true }, value: { type: Number, required: true } },
  { _id: false }
);

const ActivityLineSchema = new Schema<IActivityLine>(
  { at: { type: Date, required: true }, text: { type: String, required: true } },
  { _id: false }
);

const MindSnapshotSchema = new Schema(
  {
    capturedAt: { type: Date, required: true },
    meta: {
      source: { type: String, default: 'brain' },
      body: { type: String },
    },
    state: { type: String, required: true },
    doing: { type: String, default: '' },
    /** The build the brain was running at capture (e.g. "TK-1") — archived per
     *  snapshot so the history knows which mind produced which figures. */
    version: { type: String },
    uptimeSec: { type: Number, default: 0 },
    metrics: { type: Schema.Types.Mixed, default: {} },
    beliefsByDomain: { type: [BeliefBarSchema], default: [] },
    activity: { type: [ActivityLineSchema], default: [] },
  },
  {
    timeseries: { timeField: 'capturedAt', metaField: 'meta', granularity: 'minutes' },
    autoCreate: true,
    versionKey: false,
    minimize: false,
  }
);

export const MindSnapshot = model('MindSnapshot', MindSnapshotSchema, 'mind_snapshots');

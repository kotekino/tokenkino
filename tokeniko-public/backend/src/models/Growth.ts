import { Schema, model, Document } from 'mongoose';

/**
 * growth_rings + growth_edge — the Growth Rings page's content, homed in Atlas
 * so a new season lands with one authed API call instead of a deploy.
 *
 * The page stays HAND-WRITTEN in the sense that matters (doc/growth-rings.md):
 * the entries are the crew's judgement about progress, curated from
 * `tokeniko/doc/landed.md` at doc-reconciliation time. Only the *storage* moved
 * out of the bundle. The frontend keeps `data/growth.ts` as its offline
 * fallback — the first seasons, frozen, honest when the API is unreachable.
 *
 * `slug` is the idempotency key (upsert — same idiom as transmissions);
 * `seq` is the explicit reading order (higher = newer; the page reads bark
 * inward). Explicit because `when` is deliberately free text ("the first
 * season") and cannot sort.
 */
export interface IGrowthRing extends Document {
  slug: string;
  seq: number;
  when: string;
  title: string;
  body: string;
  marks: string[];
  createdAt: Date;
  updatedAt: Date;
}

const GrowthRingSchema = new Schema<IGrowthRing>(
  {
    slug: { type: String, required: true, unique: true, index: true },
    seq: { type: Number, required: true },
    when: { type: String, required: true },
    title: { type: String, required: true },
    body: { type: String, required: true },
    marks: { type: [String], default: [] },
  },
  { timestamps: true, versionKey: false }
);

export const GrowthRing = model<IGrowthRing>('GrowthRing', GrowthRingSchema, 'growth_rings');

/**
 * The Growing Edge — the living layer. Exactly one, always (a tree grows in a
 * single thin band of tissue under the bark), so it is a keyed singleton —
 * the same idiom as MindCurrent — replaced whole when the roadmap's living
 * layer moves.
 */
export interface IGrowthEdge extends Document {
  key: string;
  title: string;
  body: string;
  marks: string[];
  updatedAt: Date;
}

const GrowthEdgeSchema = new Schema<IGrowthEdge>(
  {
    key: { type: String, required: true, unique: true, default: 'current' },
    title: { type: String, required: true },
    body: { type: String, required: true },
    marks: { type: [String], default: [] },
  },
  { timestamps: true, versionKey: false }
);

export const GrowthEdge = model<IGrowthEdge>('GrowthEdge', GrowthEdgeSchema, 'growth_edge');

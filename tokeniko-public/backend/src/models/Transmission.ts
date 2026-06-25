import { Schema, model, Document } from 'mongoose';

/**
 * transmissions — the brain's published output (the Stream / Archive entries).
 * Mirrors the frontend `Transmission` shape (frontend/src/data/transmissions.ts)
 * so the data is a drop-in when the frontend is wired to the API.
 *
 * `slug` is the idempotency key: POST upserts by slug, so the brain can safely
 * re-publish the same transmission without creating duplicates.
 */
export type TransmissionKind = 'note' | 'argument' | 'content' | 'log';

export interface ITransmission extends Document {
  slug: string;
  date: Date;
  kind: TransmissionKind;
  title: string;
  excerpt: string;
  body: string[];
  readMin: number;
  publishedAt: Date;
  createdAt: Date;
  updatedAt: Date;
}

const TransmissionSchema = new Schema<ITransmission>(
  {
    slug: { type: String, required: true, unique: true, index: true },
    date: { type: Date, required: true },
    kind: {
      type: String,
      enum: ['note', 'argument', 'content', 'log'],
      required: true,
    },
    title: { type: String, required: true },
    excerpt: { type: String, required: true },
    body: { type: [String], default: [] },
    readMin: { type: Number, default: 1 },
    publishedAt: { type: Date, default: Date.now },
  },
  { timestamps: true, versionKey: false }
);

export const Transmission = model<ITransmission>('Transmission', TransmissionSchema, 'transmissions');

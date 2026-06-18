import { Schema, model, Document } from 'mongoose';

export interface ICookieConsent extends Document {
  sessionId: string;
  necessary: boolean;
  analytics: boolean;
  marketing: boolean;
  ipAddress?: string;
  userAgent?: string;
  consentedAt: Date;
  updatedAt: Date;
}

const CookieConsentSchema = new Schema<ICookieConsent>(
  {
    sessionId: { type: String, required: true, unique: true, index: true },
    necessary: { type: Boolean, default: true }, // Always true - cannot be disabled
    analytics: { type: Boolean, default: false },
    marketing: { type: Boolean, default: false },
    ipAddress: { type: String },
    userAgent: { type: String },
  },
  { timestamps: { createdAt: 'consentedAt', updatedAt: 'updatedAt' } }
);

export const CookieConsent = model<ICookieConsent>('CookieConsent', CookieConsentSchema);

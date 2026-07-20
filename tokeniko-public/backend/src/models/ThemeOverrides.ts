import { Schema, model } from 'mongoose';

/**
 * theme_overrides — the ONE small Atlas doc of theme tunables (the agreed
 * overrides-over-defaults shape, 2026-07-19). The full palette lives in the
 * frontend CSS (git = design provenance); this doc carries only the tokens
 * currently being tuned, as `{token: value}` — a CSS custom property, bare
 * (`--paper`) or tone-scoped (`night:--paper`). It is edited BY HAND in Atlas
 * (tuning is data; identity is code — there is deliberately no ingest route),
 * rides the GET /api/mind response the site already polls, and graduated
 * values fold back into the CSS defaults at the next real deploy.
 */
const ThemeOverridesSchema = new Schema(
  {
    key: { type: String, required: true, unique: true, default: 'current' },
    tokens: { type: Schema.Types.Mixed, default: {} },
  },
  { timestamps: true, versionKey: false, minimize: false }
);

export const ThemeOverrides = model('ThemeOverrides', ThemeOverridesSchema, 'theme_overrides');

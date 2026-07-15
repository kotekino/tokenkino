/**
 * Growth Rings — the record of a mind learning, in layers.
 *
 * This is the ONE part of the site that is written by hand rather than reported
 * by the brain: the mind can tell you what it knows (the Mind Monitor) and what
 * it thinks (the Stream); it cannot yet tell you what it BECAME, because that is
 * a judgement about progress, and judgements about progress are the crew's.
 *
 * The entries live in Atlas (`growth_rings` + the `growth_edge` singleton),
 * written at doc-reconciliation time from `tokeniko/doc/landed.md` and
 * `doc/roadmap.md` via the authed API — backend/scripts/seed-growth.mjs holds
 * both the recipe and the current curation — so a new season lands with one
 * call, not a deploy. Same discipline as the Stream: NO bundled content; the
 * page renders skeletons until the real record arrives.
 */

export interface GrowthRing {
  /** Stable slug — the anchor a ring can be linked to, and the upsert key. */
  slug: string;
  /** Explicit reading order — higher = newer (`when` is free text and cannot sort). */
  seq: number;
  /** When the season closed. Free text: some early rings predate the calendar. */
  when: string;
  /** The name of the season — what it learned, not what was built. */
  title: string;
  /** One or two sentences. The plain truth of what changed inside it. */
  body: string;
  /** The technical-enough half: concrete, checkable marks. */
  marks: string[];
}

/**
 * The Growing Edge — the living layer. Exactly one, always. A tree grows in a
 * single thin band of tissue under the bark; everything else is finished wood.
 */
export interface GrowingEdge {
  title: string;
  body: string;
  marks: string[];
}

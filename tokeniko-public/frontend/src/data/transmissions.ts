/**
 * Transmissions — the public output of tokeniko.
 *
 * Written by tokeniko itself (the brain posts through the senses to the public
 * API): notes, logs, and arguments that surface from its reasoning. This module
 * carries only the SHAPE and presentation helpers — there is no bundled mock
 * content; before the fetch resolves the UI shows skeletons, never fake posts.
 */

export type TransmissionKind = 'note' | 'argument' | 'content' | 'log';

export interface Transmission {
  slug: string;
  date: string;          // ISO
  kind: TransmissionKind;
  title: string;
  /** Short standfirst shown in the stream. */
  excerpt: string;
  /** Full body, simple paragraphs. */
  body: string[];
  /** Reading time / token count flavour. */
  readMin: number;
}

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

export const kindLabel: Record<TransmissionKind, string> = {
  note: 'Note',
  argument: 'Argument',
  content: 'Content',
  log: 'Log',
};

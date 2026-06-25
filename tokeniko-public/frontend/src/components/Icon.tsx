import React from 'react';

export type IconName =
  | 'synapse'
  | 'signal'
  | 'terminal'
  | 'token'
  | 'screen'
  | 'waveform'
  | 'logic'
  | 'key'
  | 'message'
  | 'atom'
  | 'power'
  | 'layers';

/**
 * The CI icon set — geometric monoline glyphs on a 24px grid (1.8 stroke,
 * round caps, currentColor ink). Geometry matches ci/ section 04 exactly;
 * the two filled cores use currentColor so the glyph stays single-colour.
 */
const PATHS: Record<IconName, string> = {
  synapse:
    '<circle cx="6" cy="13" r="2.4"/><circle cx="12" cy="6" r="2.4"/><circle cx="18" cy="14" r="2.4"/><line x1="7.7" y1="11.5" x2="10.4" y2="7.6"/><line x1="13.5" y1="7.5" x2="16.4" y2="12.3"/><line x1="8.2" y1="13.6" x2="15.7" y2="13.9"/>',
  signal:
    '<circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="4.6"/><circle cx="12" cy="12" r="8.4"/>',
  terminal:
    '<rect x="3" y="5" width="18" height="14" rx="2"/><polyline points="7,10 10,12.5 7,15"/><line x1="12" y1="15" x2="16" y2="15"/>',
  token:
    '<polygon points="12,3 19,7.5 19,16.5 12,21 5,16.5 5,7.5"/><circle cx="12" cy="12" r="2.6"/>',
  screen:
    '<rect x="3" y="4" width="18" height="13" rx="2"/><line x1="3" y1="13" x2="21" y2="13"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="17" x2="12" y2="20"/>',
  waveform: '<polyline points="3,12 6,12 8,5 11,19 14,8 16,15 18,12 21,12"/>',
  logic:
    '<circle cx="12" cy="12" r="4.5"/><line x1="12" y1="2.5" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="21.5"/><line x1="2.5" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="21.5" y2="12"/><line x1="5.4" y1="5.4" x2="7.2" y2="7.2"/><line x1="16.8" y1="16.8" x2="18.6" y2="18.6"/><line x1="18.6" y1="5.4" x2="16.8" y2="7.2"/><line x1="7.2" y1="16.8" x2="5.4" y2="18.6"/>',
  key:
    '<circle cx="8" cy="9" r="3.8"/><line x1="10.7" y1="11.7" x2="19" y2="20"/><line x1="16.5" y1="17.5" x2="18.5" y2="15.5"/><line x1="18.5" y1="19.5" x2="20.5" y2="17.5"/>',
  message:
    '<path d="M4 5h16a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H9l-4 4V6a1 1 0 0 1 1-1Z"/><line x1="8" y1="10" x2="16" y2="10"/>',
  atom:
    '<circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none"/><ellipse cx="12" cy="12" rx="9" ry="3.6"/><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(120 12 12)"/>',
  power:
    '<line x1="12" y1="3.5" x2="12" y2="11"/><path d="M7.5 7.2a6.4 6.4 0 1 0 9 0"/>',
  layers:
    '<polygon points="12,3 21,8 12,13 3,8"/><polyline points="3,12 12,17 21,12"/><polyline points="3,16 12,21 21,16"/>',
};

interface Props {
  name: IconName;
  /** Square size in px. */
  size?: number;
  className?: string;
}

const Icon: React.FC<Props> = ({ name, size = 24, className }) => (
  <svg
    className={className}
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    dangerouslySetInnerHTML={{ __html: PATHS[name] }}
  />
);

export default Icon;

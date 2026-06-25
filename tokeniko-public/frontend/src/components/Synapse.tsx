import React from 'react';

interface Props {
  /** Width in px (height scales 48:120). */
  width?: number;
  /** Stroke + firing-node colour. */
  color?: string;
  /** Fill of the three quiet nodes — set to the surface behind it. */
  nodeFill?: string;
  className?: string;
}

/**
 * The synapse device — the CI's brand accent: three nodes, one firing.
 * Used as a divider / bullet. Matches ci/ tokeniko logo synapse exactly.
 */
const Synapse: React.FC<Props> = ({
  width = 120,
  color = 'var(--coral)',
  nodeFill = 'var(--parchment)',
  className,
}) => (
  <svg
    className={className}
    width={width}
    height={(width * 48) / 120}
    viewBox="0 0 120 48"
    fill="none"
    stroke={color}
    strokeWidth={2.4}
    aria-hidden="true"
  >
    <line x1="14" y1="34" x2="58" y2="34" />
    <line x1="58" y1="34" x2="86" y2="14" />
    <line x1="58" y1="34" x2="104" y2="34" />
    <circle cx="14" cy="34" r="5" fill={nodeFill} />
    <circle cx="58" cy="34" r="6.5" fill={color} />
    <circle cx="86" cy="14" r="5" fill={nodeFill} />
    <circle cx="104" cy="34" r="5" fill={nodeFill} />
  </svg>
);

export default Synapse;

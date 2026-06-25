import React from 'react';

interface Props {
  /** Pixel size of the square emblem. */
  size?: number;
  /**
   * Colourway (per the CI):
   *  · primary — coral tile / paper letters (light surfaces)
   *  · reverse — paper tile / coral letters (dark surfaces, e.g. the footer)
   */
  variant?: 'primary' | 'reverse';
  className?: string;
}

/**
 * tokeniko emblem — the official brand mark: a `tk` monogram in a
 * Bakelite-rounded console tile, set in Space Mono. Purely geometric, so it
 * stays legible from a 16px favicon up. Matches ci/ tokeniko-emblem.svg exactly.
 */
const LogoMark: React.FC<Props> = ({ size = 38, variant = 'primary', className }) => {
  const tile = variant === 'reverse' ? '#F4EEDD' : '#C24E3A';
  const letters = variant === 'reverse' ? '#C24E3A' : '#F4EEDD';
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 240 240"
      role="img"
      aria-label="tokeniko"
    >
      <rect x="16" y="16" width="208" height="208" rx="32" fill={tile} />
      <text
        x="120"
        y="128"
        fontFamily="'Space Mono', 'JetBrains Mono', monospace"
        fontWeight="700"
        fontSize="118"
        letterSpacing="-6"
        fill={letters}
        textAnchor="middle"
        dominantBaseline="central"
      >
        tk
      </text>
    </svg>
  );
};

export default LogoMark;

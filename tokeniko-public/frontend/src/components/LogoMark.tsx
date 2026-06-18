import React from 'react';

interface Props {
  /** Pixel size of the square mark. */
  size?: number;
  className?: string;
}

/**
 * tokeniko's mark — "a persistent mind in a vintage console".
 *
 *  · roundel ........ a self-contained being / appliance face / CRT porthole
 *  · coral core ..... identity, the one fixed point (a = a); the floor
 *  · teal orbit ..... thought in continuous motion — it never stops thinking
 *
 * The bezel uses currentColor so the mark adapts to light (cream header) and
 * dark (ink footer) surfaces; the core and orbit stay brand colours.
 */
const LogoMark: React.FC<Props> = ({ size = 36, className }) => (
  <svg
    className={className}
    width={size}
    height={size}
    viewBox="0 0 64 64"
    fill="none"
    role="img"
    aria-label="tokeniko"
  >
    {/* bezel */}
    <circle cx="32" cy="32" r="29" stroke="currentColor" strokeWidth="3" />

    {/* orbit — a thought circling the self, forever */}
    <g transform="rotate(-22 32 32)">
      <ellipse cx="32" cy="32" rx="22" ry="9" stroke="#2F6E63" strokeWidth="2.5" />
      <circle cx="54" cy="32" r="3.4" fill="#7FB3A1" stroke="currentColor" strokeWidth="1" />
    </g>

    {/* core — identity, the fixed point (a = a) */}
    <circle className="logo-core-glow" cx="32" cy="32" r="11" fill="#C24E3A" opacity="0.16" />
    <circle cx="32" cy="32" r="6.6" fill="#C24E3A" />
    <circle cx="29.6" cy="29.6" r="2.2" fill="#F2E0C8" opacity="0.85" />
  </svg>
);

export default LogoMark;

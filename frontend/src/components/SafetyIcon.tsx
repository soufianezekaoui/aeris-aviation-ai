/** ANSI Z535-style signal icons, drawn inline (no network, no image assets). */
type Kind = "caution" | "warning" | "danger" | "notice";

const COLORS: Record<Kind, { fill: string; ink: string }> = {
  caution: { fill: "#FFC72C", ink: "#0A101C" }, // yellow triangle
  warning: { fill: "#FF6A13", ink: "#0A101C" }, // orange triangle
  danger: { fill: "#E5322D", ink: "#FFFFFF" }, // red
  notice: { fill: "#FFFFFF", ink: "#0A101C" }, // white-on-navy information
};

export function SafetyIcon({ kind, size = 20 }: { kind: Kind; size?: number }) {
  const { fill, ink } = COLORS[kind];
  const common = { width: size, height: size, viewBox: "0 0 24 24", "aria-hidden": true } as const;
  if (kind === "danger") {
    return (
      <svg {...common}>
        <ellipse cx="12" cy="12" rx="11" ry="8.5" fill={fill} />
        <path d="M11 6.5h2v6.5h-2zM11 14.5h2v2h-2z" fill={ink} />
      </svg>
    );
  }
  if (kind === "notice") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="10.5" fill={fill} />
        <path d="M11 10.5h2V17h-2zM11 7h2v2h-2z" fill={ink} />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M12 2.2 22.5 21H1.5z" fill={fill} stroke={fill} strokeLinejoin="round" strokeWidth="1.5" />
      <path d="M11 9h2v6h-2zM11 16.2h2v2h-2z" fill={ink} />
    </svg>
  );
}

import { scale, seekFromX } from "../lib/simtime";
import type { AlertLevel, SimAlert, TimelinePoint } from "../types";

const W = 800;
const L = 52;     // plot left
const R = 790;    // plot right
const ALT = { top: 22, bottom: 118 };
const SPD = { top: 150, bottom: 240 };
const BAND: Record<AlertLevel, string> = {
  caution: "#FFC72C",
  warning: "#FF6A13",
  critical: "#E5322D",
};

interface Props {
  points: TimelinePoint[];
  alerts: SimAlert[];
  duration: number;
  interval: number;
  t: number;
  onSeek: (t: number) => void;
}

export function TimelineChart({ points, alerts, duration, interval, t, onSeek }: Props) {
  if (points.length < 2) return null;
  const x = (sec: number) => scale(sec, 0, duration, L, R);
  const maxAlt = Math.max(...points.map((p) => p.altitude_ft), 1000);
  const speeds = points.map((p) => p.airspeed_kt);
  const maxSpd = Math.max(...speeds, 100);
  const line = (key: "altitude_ft" | "airspeed_kt", top: number, bottom: number, max: number) =>
    points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${scale(p[key], 0, max, bottom, top).toFixed(1)}`).join(" ");

  const phaseStarts = points.filter((p, i) => i === 0 || p.phase !== points[i - 1].phase);
  // Only label a phase when there is room; the dashed boundary line is always drawn.
  let lastLabelX = -Infinity;
  const labelled = new Set<number>();
  for (const p of phaseStarts) {
    if (x(p.t) - lastLabelX >= 52) {
      labelled.add(p.t);
      lastLabelX = x(p.t);
    }
  }

  const handle = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const xView = ((e.clientX - rect.left) * W) / rect.width;
    onSeek(seekFromX(xView, L, R - L, duration, interval));
  };

  return (
    <figure className="space-y-1">
      <svg
        viewBox={`0 0 ${W} 262`}
        role="img"
        aria-label="Simulated altitude and airspeed over time, with alert intervals shaded. Click to move the time cursor."
        className="w-full cursor-crosshair rounded border border-navy-600 bg-navy-950"
        onClick={handle}
      >
        {alerts.map((a) => (
          <rect
            key={a.id}
            x={x(a.t_start)}
            y={10}
            width={Math.max(2, x(a.t_end ?? duration) - x(a.t_start))}
            height={235}
            fill={BAND[a.level]}
            opacity={0.25}
          >
            <title>{`${a.level.toUpperCase()}: ${a.message}`}</title>
          </rect>
        ))}

        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={L} x2={R} y1={scale(f, 0, 1, ALT.bottom, ALT.top)} y2={scale(f, 0, 1, ALT.bottom, ALT.top)} stroke="rgba(255,255,255,0.1)" />
            <line x1={L} x2={R} y1={scale(f, 0, 1, SPD.bottom, SPD.top)} y2={scale(f, 0, 1, SPD.bottom, SPD.top)} stroke="rgba(255,255,255,0.1)" />
          </g>
        ))}
        <text x={L - 6} y={ALT.top + 4} textAnchor="end" fontSize="10" fill="rgba(255,255,255,0.6)">{Math.round(maxAlt / 1000)}k ft</text>
        <text x={L - 6} y={ALT.bottom + 4} textAnchor="end" fontSize="10" fill="rgba(255,255,255,0.6)">0</text>
        <text x={L - 6} y={SPD.top + 4} textAnchor="end" fontSize="10" fill="rgba(255,255,255,0.6)">{Math.round(maxSpd)} kt</text>
        <text x={L - 6} y={SPD.bottom + 4} textAnchor="end" fontSize="10" fill="rgba(255,255,255,0.6)">0</text>

        {phaseStarts.map((p) => (
          <g key={p.t}>
            <line x1={x(p.t)} x2={x(p.t)} y1={12} y2={245} stroke="rgba(255,255,255,0.12)" strokeDasharray="2 4" />
            {labelled.has(p.t) && (
              <text x={x(p.t) + 3} y={20} fontSize="8" fill="rgba(255,255,255,0.55)">{p.phase}</text>
            )}
          </g>
        ))}

        <path d={line("altitude_ft", ALT.top, ALT.bottom, maxAlt)} fill="none" stroke="#FF6A13" strokeWidth="2" />
        <path d={line("airspeed_kt", SPD.top, SPD.bottom, maxSpd)} fill="none" stroke="#FFFFFF" strokeWidth="1.6" opacity="0.85" />
        <text x={L + 6} y={ALT.top + 14} fontSize="10" fill="#FF6A13">altitude</text>
        <text x={L + 6} y={SPD.top + 14} fontSize="10" fill="#FFFFFF">airspeed</text>

        <line x1={x(t)} x2={x(t)} y1={8} y2={248} stroke="#FFC72C" strokeWidth="2" />
      </svg>
      <figcaption className="text-[11px] text-white/45">
        Synthetic data. Shaded bands are alert intervals (yellow caution, orange warning, red critical).
        Click the chart or use the time slider.
      </figcaption>
    </figure>
  );
}

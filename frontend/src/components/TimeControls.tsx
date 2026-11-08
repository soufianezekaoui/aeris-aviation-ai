import { formatOffset } from "../lib/simtime";

export const SPEEDS = [
  { label: "Slow", step: 15 },
  { label: "Medium", step: 60 },
  { label: "Fast", step: 180 },
] as const;

interface Props {
  t: number;
  duration: number;
  interval: number;
  playing: boolean;
  speedIdx: number;
  onT: (t: number) => void;
  onPlaying: (p: boolean) => void;
  onSpeed: (i: number) => void;
}

/** Moves a client-side cursor over already-generated data. It changes no simulation state. */
export function TimeControls({ t, duration, interval, playing, speedIdx, onT, onPlaying, onSpeed }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded border border-navy-600 bg-navy-800 p-3">
      <button
        type="button"
        className="btn-primary !px-4 !py-2"
        onClick={() => onPlaying(!playing)}
        aria-pressed={playing}
      >
        {playing ? "Pause" : t >= duration ? "Replay" : "Play"}
      </button>
      <input
        type="range"
        min={0}
        max={duration}
        step={interval}
        value={t}
        onChange={(e) => onT(Number(e.target.value))}
        aria-label="Simulated time"
        aria-valuetext={formatOffset(t)}
        className="min-w-[160px] flex-1 accent-safety-orange"
      />
      <span className="font-mono text-sm tabular-nums">
        {formatOffset(t)} <span className="text-white/40">/ {formatOffset(duration)}</span>
      </span>
      <label className="flex items-center gap-2 text-xs text-white/60">
        Speed
        <select
          value={speedIdx}
          onChange={(e) => onSpeed(Number(e.target.value))}
          className="rounded border border-navy-600 bg-navy-950 px-2 py-1 text-white"
        >
          {SPEEDS.map((s, i) => (
            <option key={s.label} value={i}>
              {s.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

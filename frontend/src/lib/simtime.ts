/** 160 -> "T+00:02:40" (time since the start of the simulated flight). */
export function formatOffset(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const hh = String(Math.floor(s / 3600)).padStart(2, "0");
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `T+${hh}:${mm}:${ss}`;
}

/** "2030-01-01T08:02:40Z" -> "2030-01-01 08:02:40 UTC" (never converted to local time). */
export function formatSimUtc(iso: string | null | undefined): string {
  if (!iso) return "no snapshot";
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/.exec(iso);
  return m ? `${m[1]} ${m[2]} UTC` : iso;
}

/** Map a pointer x position inside a plot to a simulated time, snapped to the sample grid. */
export function seekFromX(
  x: number,
  left: number,
  width: number,
  duration: number,
  interval: number,
): number {
  if (width <= 0 || duration <= 0) return 0;
  const frac = Math.min(1, Math.max(0, (x - left) / width));
  const snapped = Math.round((frac * duration) / interval) * interval;
  return Math.min(duration, Math.max(0, snapped));
}

/** Linear scale helper for the SVG chart. */
export function scale(v: number, min: number, max: number, outMin: number, outMax: number): number {
  if (max === min) return outMin;
  return outMin + ((v - min) / (max - min)) * (outMax - outMin);
}

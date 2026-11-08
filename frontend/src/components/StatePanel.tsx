import { formatOffset, formatSimUtc } from "../lib/simtime";
import type { Freshness, SimStateResponse } from "../types";
import { SafetyIcon } from "./SafetyIcon";

const FRESH: Record<Freshness, { label: string; cls: string }> = {
  latest: { label: "Final snapshot", cls: "bg-white/15 text-white" },
  exact: { label: "Exact sample", cls: "bg-white/15 text-white" },
  held: { label: "Held sample", cls: "bg-safety-yellow text-navy-950" },
  stale: { label: "Stale", cls: "bg-safety-yellow text-navy-950" },
  absent: { label: "No snapshot", cls: "bg-safety-red-fill text-white" },
};

function Tile({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded border border-navy-600 bg-navy-950 p-3">
      <p className="text-[10px] font-bold uppercase tracking-widest text-white/50">{label}</p>
      <p className="mt-1 font-mono text-2xl font-bold tabular-nums text-white">
        {value}
        {unit && <span className="ml-1 text-xs font-normal text-white/50">{unit}</span>}
      </p>
    </div>
  );
}

const n = (v: number, d = 0) => v.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d });

export function StatePanel({ data }: { data: SimStateResponse | null }) {
  if (!data) return <p className="text-sm text-white/50">Loading simulated state…</p>;
  const f = FRESH[data.freshness];
  const s = data.state;
  return (
    <section aria-labelledby="state-heading" className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <h3 id="state-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
          Simulated state
        </h3>
        <span className={`rounded px-2 py-0.5 text-[11px] font-bold uppercase ${f.cls}`}>{f.label}</span>
        {s && (
          <span className="rounded bg-navy-600 px-2 py-0.5 font-mono text-[11px] font-bold uppercase">
            {s.phase}
          </span>
        )}
      </div>

      <dl className="grid gap-x-6 gap-y-1 font-mono text-xs text-white/70 sm:grid-cols-2">
        <div className="flex gap-2">
          <dt className="text-white/45">session</dt>
          <dd title={data.session_id}>{data.session_id.slice(0, 8)}…</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-white/45">snapshot (simulated clock)</dt>
          <dd>
            {data.t_seconds !== null && `${formatOffset(data.t_seconds)} · `}
            {formatSimUtc(data.snapshot_time)}
          </dd>
        </div>
      </dl>

      {data.warnings.map((w) => (
        <p key={w} className="flex items-start gap-2 rounded bg-safety-yellow/15 p-2 text-xs text-safety-yellow">
          <SafetyIcon kind="caution" size={14} />
          <span>{w}</span>
        </p>
      ))}

      {s && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Tile label="Altitude" value={n(s.altitude_ft)} unit="ft" />
          <Tile label="Airspeed" value={n(s.airspeed_kt)} unit="kt" />
          <Tile label="Vertical speed" value={n(s.vertical_speed_fpm)} unit="fpm" />
          <Tile label="Heading" value={n(s.heading_deg)} unit="°" />
          <Tile label="Flaps" value={String(s.flap_deg)} unit="°" />
          <Tile label="Gear" value={s.gear_down ? "DOWN" : "UP"} />
          <Tile label="N1" value={n(s.n1_pct, 1)} unit="%" />
          <Tile label="Fuel" value={n(s.fuel_kg)} unit="kg" />
        </div>
      )}
    </section>
  );
}

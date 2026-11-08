import { formatOffset } from "../lib/simtime";
import type { AlertLevel, SimAlert } from "../types";
import { SafetyIcon } from "./SafetyIcon";


export const LEVEL: Record<AlertLevel, { label: string; box: string; icon: "caution" | "warning" | "danger" }> = {
  caution: { label: "Caution", box: "bg-safety-yellow text-navy-950", icon: "caution" },
  warning: { label: "Warning", box: "bg-safety-orange text-navy-950", icon: "warning" },
  critical: { label: "Critical", box: "bg-safety-red-fill text-white", icon: "danger" },
};

export function AlertList({ alerts, emptyText }: { alerts: SimAlert[]; emptyText: string }) {
  if (alerts.length === 0) {
    return <p className="rounded border border-navy-600 p-3 text-sm text-white/60">{emptyText}</p>;
  }
  return (
    <ul className="space-y-2">
      {alerts.map((a) => {
        const l = LEVEL[a.level];
        return (
          <li key={a.id} className={`flex items-start gap-3 rounded p-3 ${l.box}`}>
            <span className="mt-0.5 shrink-0">
              <SafetyIcon kind={l.icon} size={20} inverted />
            </span>
            <div className="min-w-0 text-sm">
              <p className="font-bold uppercase tracking-wide">
                {l.label} · {a.code.replace(/_/g, " ")}
                {!a.active && <span className="ml-2 font-normal normal-case opacity-80">(cleared)</span>}
              </p>
              <p>{a.message}</p>
              <p className="font-mono text-xs opacity-80">
                raised {formatOffset(a.t_start)}
                {a.t_end !== null ? ` · cleared ${formatOffset(a.t_end)}` : " · still active at end of data"}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

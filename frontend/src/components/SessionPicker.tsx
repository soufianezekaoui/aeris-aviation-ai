import { useState } from "react";
import type { Scenario, SimSession } from "../types";
import { formatOffset } from "../lib/simtime";

interface Props {
  scenarios: Scenario[];
  sessions: SimSession[];
  selected: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onCreate: (scenarioId: string) => void;
  onDelete: (id: string) => void;
}

export function SessionPicker({ scenarios, sessions, selected, busy, onSelect, onCreate, onDelete }: Props) {
  const [scenarioId, setScenarioId] = useState("");
  const chosen = scenarioId || scenarios[0]?.id || "";

  if (sessions.length === 0) {
    return (
      <section aria-labelledby="start-heading" className="space-y-3">
        <h2 id="start-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
          Start a synthetic simulation session
        </h2>
        <div className="grid gap-3 md:grid-cols-3">
          {scenarios.map((s) => (
            <article key={s.id} className="flex flex-col justify-between rounded border border-navy-600 bg-navy-800 p-4">
              <div>
                <h3 className="font-bold">{s.name}</h3>
                <p className="mt-1 text-sm text-white/70">{s.description}</p>
                <p className="mt-2 text-xs text-white/50">{s.learning_goal}</p>
                <p className="mt-2 font-mono text-[11px] text-white/40">{formatOffset(s.duration_s)} · {s.aircraft}</p>
              </div>
              <button type="button" className="btn-primary mt-4" disabled={busy} onClick={() => onCreate(s.id)}>
                {busy ? "Creating…" : "Start session"}
              </button>
            </article>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Simulation sessions" className="flex flex-wrap items-end gap-4 rounded border border-navy-600 bg-navy-800 p-3">
      <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-xs text-white/60">
        Session
        <select
          value={selected ?? ""}
          onChange={(e) => onSelect(e.target.value)}
          className="rounded border border-navy-600 bg-navy-950 px-2 py-2 text-sm text-white"
        >
          {sessions.map((s) => (
            <option key={s.session_id} value={s.session_id}>
              {s.name} · {s.session_id.slice(0, 8)}
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[200px] flex-col gap-1 text-xs text-white/60">
        New session from scenario
        <select
          value={chosen}
          onChange={(e) => setScenarioId(e.target.value)}
          className="rounded border border-navy-600 bg-navy-950 px-2 py-2 text-sm text-white"
        >
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </label>
      <button type="button" className="btn-primary" disabled={busy || !chosen} onClick={() => onCreate(chosen)}>
        Start session
      </button>
      {selected && (
        <button type="button" className="chip" disabled={busy} onClick={() => onDelete(selected)}>
          Delete session
        </button>
      )}
    </section>
  );
}

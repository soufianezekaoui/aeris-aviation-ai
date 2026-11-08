import { useState } from "react";
import type { ChecklistItem, ChecklistsResponse, ReviewStatus } from "../types";
import { SafetyIcon } from "./SafetyIcon";

const OPTIONS: { value: ReviewStatus; label: string }[] = [
  { value: "not_reviewed", label: "Not reviewed" },
  { value: "reviewed", label: "Reviewed" },
  { value: "needs_attention", label: "Needs attention" },
];

interface Props {
  data: ChecklistsResponse | null;
  busy: Set<number>;
  error: string | null;
  onUpdate: (itemId: number, status: ReviewStatus, note: string | null) => void;
}

function Item({ item, busy, onUpdate }: { item: ChecklistItem; busy: boolean; onUpdate: Props["onUpdate"] }) {
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState(item.note ?? "");
  const saveNote = () => {
    setEditing(false);
    const clean = note.trim() || null;
    if (clean !== item.note) onUpdate(item.id, item.status, clean);
  };
  return (
    <li className="space-y-2 border-t border-paper-dim py-3 first:border-t-0">
      <p className="text-sm leading-snug">{item.text}</p>
      <div role="group" aria-label={`Review status: ${item.text}`} className="flex flex-wrap gap-1">
        {OPTIONS.map((o) => {
          const on = item.status === o.value;
          const tone =
            o.value === "reviewed"
              ? "bg-safety-orange text-navy-950 border-safety-orange"
              : o.value === "needs_attention"
                ? "bg-safety-yellow text-navy-950 border-safety-yellow"
                : "bg-navy-900 text-white border-navy-900";
          return (
            <button
              key={o.value}
              type="button"
              disabled={busy}
              aria-pressed={on}
              onClick={() => !on && onUpdate(item.id, o.value, item.note)}
              className={`rounded border px-2 py-1 text-[11px] font-bold uppercase tracking-wide transition disabled:opacity-50 ${
                on ? tone : "border-paper-dim bg-white text-navy-700 hover:border-navy-700"
              }`}
            >
              {o.label}
            </button>
          );
        })}
      </div>
      {editing ? (
        <input
          autoFocus
          value={note}
          maxLength={500}
          aria-label="Review note"
          onChange={(e) => setNote(e.target.value)}
          onBlur={saveNote}
          onKeyDown={(e) => e.key === "Enter" && saveNote()}
          className="w-full rounded border border-navy-600 bg-white px-2 py-1 text-xs"
        />
      ) : (
        <button type="button" onClick={() => setEditing(true)} className="text-xs text-navy-600 underline decoration-safety-orange underline-offset-4">
          {item.note ? `Note: ${item.note}` : "Add note"}
        </button>
      )}
    </li>
  );
}

export function ChecklistPanel({ data, busy, error, onUpdate }: Props) {
  if (!data) return <p className="text-sm text-white/50">Loading checklists…</p>;
  const { progress: p } = data;
  const pct = p.total ? Math.round((p.reviewed / p.total) * 100) : 0;
  return (
    <section aria-labelledby="check-heading" className="space-y-3">
      <h3 id="check-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
        Checklist review
      </h3>
      <p className="flex items-start gap-2 rounded bg-safety-yellow/10 p-2 text-xs text-safety-yellow">
        <SafetyIcon kind="caution" size={14} />
        <span>{data.semantics}</span>
      </p>
      <div>
        <div className="h-2 overflow-hidden rounded bg-navy-600" role="progressbar" aria-valuemin={0} aria-valuemax={p.total} aria-valuenow={p.reviewed} aria-label="Items reviewed">
          <div className="h-full bg-safety-orange transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 font-mono text-[11px] text-white/60">
          {p.reviewed}/{p.total} reviewed
          {p.needs_attention > 0 && ` · ${p.needs_attention} need attention`}
        </p>
      </div>
      {error && (
        <p role="alert" className="rounded border-l-4 border-safety-red bg-safety-red/15 p-2 text-xs text-safety-red-text">
          {error}
        </p>
      )}
      {data.checklists.map((c) => (
        <article key={c.key} className="rounded bg-paper p-4 text-paper-ink shadow">
          <h4 className="text-sm font-bold">{c.title}</h4>
          <p className="font-mono text-[11px] text-navy-600">
            {c.progress.reviewed}/{c.progress.total} reviewed
          </p>
          <ul className="mt-2">
            {c.items.map((i) => (
              <Item key={i.id} item={i} busy={busy.has(i.id)} onUpdate={onUpdate} />
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}

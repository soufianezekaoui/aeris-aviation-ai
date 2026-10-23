import { useState } from "react";
import type { Source } from "../types";

interface Props {
  source: Source;
  highlighted: boolean;
}

export function SourceCard({ source: s, highlighted }: Props) {
  const [open, setOpen] = useState(false);
  const long = s.text.length > 320;
  return (
    <article
      id={`source-${s.id}`}
      tabIndex={-1}
      aria-label={`Source ${s.id}`}
      className={[
        "rounded bg-paper p-4 text-paper-ink shadow",
        s.cited ? "border-l-4 border-safety-orange" : "border-l-4 border-paper-dim opacity-90",
        highlighted ? "ring-4 ring-safety-yellow" : "",
      ].join(" ")}
    >
      <header className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded bg-navy-900 px-2 py-0.5 font-mono font-bold text-white">
          [{s.id}]
        </span>
        <span className="font-mono font-semibold">{s.doc_id}</span>
        <span className="rounded bg-paper-dim px-2 py-0.5 font-mono">PDF p.{s.page}</span>
        {s.cited ? (
          <span className="rounded bg-safety-orange px-2 py-0.5 font-bold uppercase text-navy-950">
            cited
          </span>
        ) : (
          <span className="rounded border border-navy-600/40 px-2 py-0.5 uppercase text-navy-600">
            retrieved, not cited
          </span>
        )}
        <span
          className="ml-auto flex items-center gap-2 text-navy-600"
          title="Cosine similarity between the question and this passage"
        >
          relevance {s.score.toFixed(2)}
          <span className="inline-block h-1.5 w-16 overflow-hidden rounded bg-paper-dim" aria-hidden>
            <span
              className="block h-full bg-safety-orange"
              style={{ width: `${Math.max(0, Math.min(1, s.score)) * 100}%` }}
            />
          </span>
        </span>
      </header>
      <p className="text-xs text-navy-600">
        {s.report_ref ? `${s.report_ref} · ` : ""}
        {s.publisher}
        {s.section ? ` · §${s.section}` : ""}
      </p>
      <blockquote
        className={`mt-2 whitespace-pre-wrap border-l-2 border-paper-dim pl-3 text-sm leading-relaxed ${
          open || !long ? "" : "line-clamp-4"
        }`}
      >
        {s.text}
      </blockquote>
      {long && (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="mt-2 text-xs font-bold uppercase tracking-wide text-navy-700 underline decoration-safety-orange underline-offset-4"
        >
          {open ? "Show less" : "Show full passage"}
        </button>
      )}
    </article>
  );
}

import type { DocumentsResponse } from "../types";
import { SafetyIcon } from "./SafetyIcon";

export function DocumentsPanel({ docs }: { docs: DocumentsResponse | null }) {
  return (
    <aside aria-labelledby="docs-heading" className="space-y-3">
      <h2 id="docs-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
        Source library
      </h2>
      {docs === null && <p className="text-sm text-white/50">Loading…</p>}
      {docs && docs.total_chunks === 0 && (
        <p className="flex items-start gap-2 rounded bg-safety-yellow/10 p-3 text-xs text-safety-yellow">
          <SafetyIcon kind="caution" size={16} />
          <span>
            Nothing indexed yet. Run <code className="font-mono">aeris ingest</code> in the backend.
          </span>
        </p>
      )}
      <ul className="space-y-2">
        {docs?.documents.map((d) => (
          <li key={d.doc_id} className="rounded border border-navy-600 bg-navy-800 p-3">
            <p className="font-mono text-xs font-bold text-white">{d.doc_id}</p>
            <p className="mt-1 line-clamp-3 text-xs text-white/70">{d.title}</p>
            <p className="mt-1 text-[11px] text-white/50">
              {d.publisher}
              {d.report_ref ? ` · ${d.report_ref}` : ""}
            </p>
            <p className={`mt-2 text-[11px] font-bold uppercase ${d.indexed ? "text-safety-orange" : "text-safety-yellow"}`}>
              {d.indexed ? `${d.chunks} passages indexed` : "not indexed"}
            </p>
            {d.url && (
              <a className="text-[11px] text-white/60 underline" href={d.url} target="_blank" rel="noreferrer noopener">
                original source
              </a>
            )}
          </li>
        ))}
      </ul>
      <p className="text-[11px] leading-relaxed text-white/45">
        Page numbers refer to the <strong>PDF page index</strong> (cover = 1), not the number
        printed on the page.
      </p>
    </aside>
  );
}

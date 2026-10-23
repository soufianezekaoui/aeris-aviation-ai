import type { DocumentsResponse } from "../types";

export function Header({ docs }: { docs: DocumentsResponse | null }) {
  return (
    <header className="border-b border-navy-600 bg-navy-950/80 backdrop-blur">
      <div className="hazard-stripe" aria-hidden="true" />
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
        <div className="flex items-center gap-3">
          <svg width="34" height="34" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="#0A101C" stroke="#26324D" />
            <path d="M16 5 4 27h24z" fill="#FF6A13" />
            <path d="M16 13l-4 9h8z" fill="#0A101C" />
          </svg>
          <div>
            <h1 className="text-xl font-extrabold tracking-[0.2em]">AERIS</h1>
            <p className="text-[11px] uppercase tracking-widest text-white/60">
              Aviation Intelligence &amp; Retrieval System
            </p>
          </div>
        </div>
        <p className="hidden font-mono text-xs text-white/60 sm:block" aria-live="polite">
          {docs
            ? `${docs.documents.filter((d) => d.indexed).length}/${docs.documents.length} reports · ${docs.total_chunks} passages indexed`
            : "connecting…"}
        </p>
      </div>
    </header>
  );
}

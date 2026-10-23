import { ApiError } from "../api";
import { SafetyIcon } from "./SafetyIcon";

const HINTS: Record<string, string> = {
  network: "Start the backend:  uvicorn aeris.main:app --port 8000",
  index_empty: "Index the reports first:  aeris ingest",
  index_mismatch: "The index was built with another embedding model:  aeris ingest --reset",
  misconfigured: "Check LLM_PROVIDER / LLM_API_KEY / EMBEDDING_* in your .env file.",
};

export function ErrorPanel({ error }: { error: Error }) {
  const code = error instanceof ApiError ? error.code : "error";
  return (
    <div role="alert" className="flex items-start gap-3 rounded border-l-4 border-safety-red bg-safety-red/15 p-4">
      <SafetyIcon kind="danger" size={24} />
      <div className="space-y-1 text-sm">
        <p className="font-bold uppercase tracking-wide text-safety-red-text">System alert · {code}</p>
        <p className="text-white/90">{error.message}</p>
        {HINTS[code] && <p className="font-mono text-xs text-white/60">{HINTS[code]}</p>}
      </div>
    </div>
  );
}

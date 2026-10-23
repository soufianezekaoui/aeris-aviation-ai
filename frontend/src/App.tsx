import { useCallback, useEffect, useRef, useState } from "react";
import { ask, getDocuments } from "./api";
import { AnswerPanel } from "./components/AnswerPanel";
import { DocumentsPanel } from "./components/DocumentsPanel";
import { ErrorPanel } from "./components/ErrorPanel";
import { Header } from "./components/Header";
import { QuestionForm } from "./components/QuestionForm";
import { SimulationBanner } from "./components/SimulationBanner";
import { SourceCard } from "./components/SourceCard";
import type { AskResponse, DocumentsResponse } from "./types";

export default function App() {
  const [docs, setDocs] = useState<DocumentsResponse | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);
  const [highlight, setHighlight] = useState<number | null>(null);
  const inflight = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    getDocuments(ctl.signal)
      .then(setDocs)
      .catch((e: Error) => e.name !== "AbortError" && setError(e));
    return () => ctl.abort();
  }, []);

  useEffect(() => {
    if (highlight === null) return;
    const t = setTimeout(() => setHighlight(null), 2200);
    return () => clearTimeout(t);
  }, [highlight]);

  const onSubmit = useCallback(async (question: string, docIds: string[]) => {
    inflight.current?.abort(); // a newer question supersedes the previous one
    const ctl = new AbortController();
    inflight.current = ctl;
    setLoading(true);
    setError(null);
    try {
      const res = await ask({ question, doc_ids: docIds.length ? docIds : undefined }, ctl.signal);
      setResult(res);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setResult(null);
      setError(e as Error);
    } finally {
      if (inflight.current === ctl) setLoading(false);
    }
  }, []);

  const onCite = (id: number) => {
    setHighlight(id);
    const el = document.getElementById(`source-${id}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    el?.focus({ preventScroll: true });
  };

  return (
    <div className="min-h-screen">
      <Header docs={docs} />
      <SimulationBanner />
      <main className="mx-auto grid max-w-6xl gap-8 px-4 py-8 lg:grid-cols-[1fr_280px]">
        <div className="min-w-0 space-y-6">
          <QuestionForm documents={docs?.documents ?? []} loading={loading} onSubmit={onSubmit} />
          {error && <ErrorPanel error={error} />}
          {loading && (
            <div className="animate-pulse rounded bg-paper/10 p-5 text-sm text-white/60" role="status">
              Searching the reports…
            </div>
          )}
          {!loading && result && (
            <>
              <AnswerPanel result={result} onCite={onCite} />
              <section aria-labelledby="sources-heading" className="space-y-3">
                <h2 id="sources-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
                  Evidence · {result.sources.length} passage{result.sources.length === 1 ? "" : "s"}
                </h2>
                {result.sources.length === 0 && (
                  <p className="text-sm text-white/60">No passage was relevant enough to show.</p>
                )}
                {result.sources.map((s) => (
                  <SourceCard key={s.chunk_id} source={s} highlighted={highlight === s.id} />
                ))}
              </section>
              <p className="text-[11px] text-white/40">{result.disclaimer}</p>
            </>
          )}
        </div>
        <DocumentsPanel docs={docs} />
      </main>
    </div>
  );
}

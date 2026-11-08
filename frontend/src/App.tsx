import { useEffect, useState } from "react";
import { getDocuments } from "./api";
import { Header } from "./components/Header";
import { ReportsView } from "./components/ReportsView";
import { SimulationBanner } from "./components/SimulationBanner";
import { SimulationView } from "./components/SimulationView";
import type { DocumentsResponse } from "./types";

type Tab = "reports" | "simulation";
const TABS: { id: Tab; label: string }[] = [
  { id: "reports", label: "Reports Q&A" },
  { id: "simulation", label: "Simulation" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("reports");
  const [docs, setDocs] = useState<DocumentsResponse | null>(null);
  const [docsError, setDocsError] = useState<Error | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    getDocuments(ctl.signal)
      .then(setDocs)
      .catch((e: Error) => e.name !== "AbortError" && setDocsError(e));
    return () => ctl.abort();
  }, []);

  return (
    <div className="min-h-screen">
      <Header docs={docs} />
      <SimulationBanner />
      <nav className="border-b border-navy-600 bg-navy-950/60">
        <div role="tablist" aria-label="Sections" className="mx-auto flex max-w-6xl gap-1 px-4">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`border-b-4 px-4 py-3 text-sm font-bold uppercase tracking-wide transition ${
                tab === t.id
                  ? "border-safety-orange text-white"
                  : "border-transparent text-white/50 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "reports" ? <ReportsView docs={docs} docsError={docsError} /> : <SimulationView />}
      </div>
    </div>
  );
}

import { useState } from "react";
import type { DocumentInfo } from "../types";

const EXAMPLES = [
  "Why did the takeoff warning system not alert the crew?",
  "What cargo ignited and started the fire on the 747?",
  "Did the crew consider diverting to Doha?",
  "In what position were the flaps and slats found?",
];

interface Props {
  documents: DocumentInfo[];
  loading: boolean;
  onSubmit: (question: string, docIds: string[]) => void;
}

export function QuestionForm({ documents, loading, onSubmit }: Props) {
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<string[]>([]); // empty = all reports
  const MAX = 1000;
  const tooLong = question.length > MAX;
  const canSend = question.trim().length >= 3 && !tooLong && !loading;

  const submit = () => canSend && onSubmit(question.trim(), selected);
  const toggle = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  return (
    <section aria-labelledby="ask-heading" className="space-y-3">
      <h2 id="ask-heading" className="text-xs font-bold uppercase tracking-widest text-safety-orange">
        Ask the investigation reports
      </h2>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
        }}
        rows={3}
        aria-label="Your question"
        aria-invalid={tooLong}
        placeholder="e.g. Why did the takeoff warning system not alert the crew?"
        className="w-full resize-y rounded border border-navy-600 bg-navy-950 p-3 text-white placeholder:text-white/40 focus:border-safety-orange"
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" aria-label="Example questions">
          {EXAMPLES.map((q) => (
            <button key={q} type="button" className="chip" onClick={() => setQuestion(q)}>
              {q}
            </button>
          ))}
        </div>
      </div>
      {documents.length > 1 && (
        <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
          <legend className="sr-only">Limit search to these reports</legend>
          <span className="text-white/60">Search in:</span>
          {documents.map((d) => (
            <label key={d.doc_id} className="flex items-center gap-1.5 text-white/85">
              <input
                type="checkbox"
                className="accent-safety-orange"
                disabled={!d.indexed}
                checked={selected.includes(d.doc_id)}
                onChange={() => toggle(d.doc_id)}
              />
              <span className="font-mono text-xs">{d.doc_id}</span>
            </label>
          ))}
          {selected.length === 0 && <span className="text-xs text-white/50">(all reports)</span>}
        </fieldset>
      )}
      <div className="flex items-center gap-4">
        <button type="button" className="btn-primary" disabled={!canSend} onClick={submit}>
          {loading ? "Searching…" : "Search the reports"}
        </button>
        <span className={`text-xs ${tooLong ? "text-safety-red-text" : "text-white/50"}`}>
          {question.length}/{MAX} · Ctrl+Enter to send
        </span>
      </div>
    </section>
  );
}

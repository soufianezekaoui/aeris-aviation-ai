import { splitCitations } from "../lib/citations";
import type { AnswerStatus, AskResponse } from "../types";
import { SafetyIcon } from "./SafetyIcon";

const STATUS: Record<AnswerStatus, { label: string; tone: "ok" | "caution" | "danger"; hint: string }> = {
  answered: { label: "Answered · citations verified", tone: "ok", hint: "Every [n] points at a retrieved passage." },
  insufficient_evidence: {
    label: "Insufficient evidence",
    tone: "caution",
    hint: "The reports do not contain enough relevant material. Nothing was invented.",
  },
  retrieval_only: {
    label: "Evidence only",
    tone: "caution",
    hint: "No language model is configured, so only the retrieved passages are shown.",
  },
  uncited: {
    label: "Unverified · no valid citations",
    tone: "caution",
    hint: "The generated text could not be tied to a source. Check the passages below.",
  },
  generation_failed: {
    label: "Generation failed",
    tone: "danger",
    hint: "The language model request failed; the evidence passages are still shown.",
  },
};

const TONE = {
  ok: "bg-safety-orange text-navy-950",
  caution: "bg-safety-yellow text-navy-950",
  danger: "bg-safety-red-fill text-white",
} as const;

interface Props {
  result: AskResponse;
  onCite: (id: number) => void;
}

export function AnswerPanel({ result, onCite }: Props) {
  const s = STATUS[result.status];
  return (
    <section aria-labelledby="answer-heading" aria-live="polite" className="rounded bg-paper p-5 text-paper-ink shadow-lg">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 id="answer-heading" className="text-xs font-bold uppercase tracking-widest text-navy-600">
          Answer
        </h2>
        <span className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-bold uppercase ${TONE[s.tone]}`}>
          {s.tone !== "ok" && <SafetyIcon kind={s.tone === "danger" ? "danger" : "caution"} size={14} />}
          {s.label}
        </span>
        <span className="ml-auto font-mono text-[11px] text-navy-600">
          retrieval {result.timings.retrieval_ms} ms
          {result.timings.generation_ms ? ` · generation ${result.timings.generation_ms} ms` : ""}
          {result.model ? ` · ${result.model}` : ""}
        </span>
      </div>

      {result.answer ? (
        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
          {splitCitations(result.answer).map((seg, i) =>
            seg.type === "text" ? (
              <span key={i}>{seg.value}</span>
            ) : (
              <span key={i} className="mx-0.5 inline-flex gap-0.5 align-baseline">
                {seg.ids.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => onCite(id)}
                    aria-label={`Go to source ${id}`}
                    className="rounded bg-safety-orange px-1.5 text-xs font-bold text-navy-950 hover:brightness-110"
                  >
                    {id}
                  </button>
                ))}
              </span>
            ),
          )}
        </p>
      ) : (
        <p className="text-sm text-navy-600">No generated text.</p>
      )}

      <p className="mt-3 text-xs text-navy-600">{s.hint}</p>

      {result.warnings.length > 0 && (
        <ul className="mt-3 space-y-1">
          {result.warnings.map((w) => (
            <li key={w} className="flex items-start gap-2 rounded bg-safety-yellow/30 px-3 py-2 text-xs">
              <SafetyIcon kind="caution" size={14} />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

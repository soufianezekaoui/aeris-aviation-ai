// Mirrors backend/src/aeris/schemas.py. Keep in sync when the API changes.
export type AnswerStatus =
  | "answered"
  | "insufficient_evidence"
  | "retrieval_only"
  | "uncited"
  | "generation_failed";

export interface Source {
  id: number;
  chunk_id: string;
  doc_id: string;
  title: string;
  publisher: string;
  report_ref: string | null;
  /** PDF page index (1 = cover), not the printed page number. */
  page: number;
  section: string | null;
  text: string;
  score: number;
  cited: boolean;
}

export interface AskResponse {
  question: string;
  status: AnswerStatus;
  answer: string | null;
  sources: Source[];
  warnings: string[];
  model: string | null;
  timings: { retrieval_ms: number; generation_ms: number };
  disclaimer: string;
}

export interface DocumentInfo {
  doc_id: string;
  title: string;
  publisher: string;
  report_ref: string | null;
  url: string | null;
  published: string | null;
  indexed: boolean;
  chunks: number;
}

export interface DocumentsResponse {
  documents: DocumentInfo[];
  total_chunks: number;
}

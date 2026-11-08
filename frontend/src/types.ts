
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

// ================= simulation
export type AlertLevel = "caution" | "warning" | "critical";
export type Freshness = "latest" | "exact" | "held" | "stale" | "absent";
export type ReviewStatus = "not_reviewed" | "reviewed" | "needs_attention";

export interface Labelled {
  synthetic: true;
  data_source: string;
  disclaimer: string;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  learning_goal: string;
  duration_s: number;
  aircraft: string;
}

export interface Progress {
  reviewed: number;
  needs_attention: number;
  total: number;
}

export interface SimSession extends Labelled {
  session_id: string;
  scenario_id: string;
  name: string;
  seed: number;
  duration_s: number;
  sample_interval_s: number;
  /** Start of the FICTIONAL simulated clock (UTC). */
  sim_start: string;
  created_at: string;
  snapshots: number;
  alert_count: number;
  checklist_progress: Progress;
}

export interface SimAlert {
  id: number;
  code: string;
  level: AlertLevel;
  message: string;
  t_start: number;
  t_end: number | null;
  start_time: string;
  end_time: string | null;
  active: boolean;
}

export interface SimStateValues {
  phase: string;
  altitude_ft: number;
  airspeed_kt: number;
  vertical_speed_fpm: number;
  heading_deg: number;
  flap_deg: number;
  gear_down: boolean;
  n1_pct: number;
  fuel_kg: number;
}

export interface SimStateResponse extends Labelled {
  session_id: string;
  scenario_id: string;
  freshness: Freshness;
  requested_t: number | null;
  t_seconds: number | null;
  snapshot_time: string | null;
  age_s: number | null;
  generated_at: string;
  state: SimStateValues | null;
  active_alerts: SimAlert[];
  warnings: string[];
}

export interface TimelinePoint {
  t: number;
  phase: string;
  altitude_ft: number;
  airspeed_kt: number;
  vertical_speed_fpm: number;
}

export interface SimTimeline extends Labelled {
  session_id: string;
  duration_s: number;
  step_s: number;
  sim_start: string;
  points: TimelinePoint[];
  alerts: SimAlert[];
}

export interface ChecklistItem {
  id: number;
  position: number;
  text: string;
  status: ReviewStatus;
  note: string | null;
  updated_at: string;
}

export interface Checklist {
  key: string;
  title: string;
  items: ChecklistItem[];
  progress: Progress;
}

export interface ChecklistsResponse extends Labelled {
  session_id: string;
  semantics: string;
  checklists: Checklist[];
  progress: Progress;
}

export interface UpdateItemResponse extends Labelled {
  session_id: string;
  semantics: string;
  item: ChecklistItem;
  progress: Progress;
}

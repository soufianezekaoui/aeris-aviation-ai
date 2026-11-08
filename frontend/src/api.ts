import type {
  AskResponse,
  ChecklistsResponse,
  DocumentsResponse,
  ReviewStatus,
  Scenario,
  SimSession,
  SimStateResponse,
  SimTimeline,
  UpdateItemResponse,
} from "./types";

// Relative by default (Vite proxies to the backend).
const BASE: string = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError("network", "Cannot reach the AERIS API. Is the backend running?", 0);
  }
  if (!res.ok) {
    let code = "http_error";
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body?.error === "string") code = body.error;
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = "The request was not valid.";
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(code, detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const getDocuments = (signal?: AbortSignal) =>
  request<DocumentsResponse>("/api/documents", { signal });

export const ask = (
  body: { question: string; doc_ids?: string[] },
  signal?: AbortSignal,
) =>
  request<AskResponse>("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

// =============== simulation
const JSON_HEADERS = { "Content-Type": "application/json" };
const sim = (id: string) => `/api/sim/sessions/${encodeURIComponent(id)}`;

export const getScenarios = (signal?: AbortSignal) =>
  request<{ scenarios: Scenario[] }>("/api/sim/scenarios", { signal }).then((r) => r.scenarios);

export const getSessions = (signal?: AbortSignal) =>
  request<{ sessions: SimSession[] }>("/api/sim/sessions", { signal }).then((r) => r.sessions);

export const createSession = (scenario_id: string) =>
  request<SimSession>("/api/sim/sessions", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ scenario_id }),
  });

export const deleteSession = (id: string) => request<void>(sim(id), { method: "DELETE" });

export const getState = (id: string, t: number, signal?: AbortSignal) =>
  request<SimStateResponse>(`${sim(id)}/state?t=${Math.max(0, Math.round(t))}`, { signal });

export const getTimeline = (id: string, step = 10, signal?: AbortSignal) =>
  request<SimTimeline>(`${sim(id)}/timeline?step=${step}`, { signal });

export const getChecklists = (id: string, signal?: AbortSignal) =>
  request<ChecklistsResponse>(`${sim(id)}/checklists`, { signal });

export const updateItem = (
  id: string,
  itemId: number,
  body: { status: ReviewStatus; note?: string | null },
) =>
  request<UpdateItemResponse>(`${sim(id)}/checklists/items/${itemId}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });

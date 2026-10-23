import type { AskResponse, DocumentsResponse } from "./types";

// Relative by default
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

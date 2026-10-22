from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    simulation_only: bool = True
    llm_provider: str
    embedding_provider: str
    disclaimer: str


class ErrorResponse(BaseModel):
    error: str = Field(description="Machine-readable error code.")
    detail: str = Field(description="Human-readable explanation.")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    doc_ids: list[str] | None = Field(default=None, max_length=20)

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("question is too short")
        return v


AnswerStatus = Literal[
    "answered",  # generated answer with at least one valid citation
    "insufficient_evidence",  # nothing relevant retrieved, or the model said so
    "retrieval_only",  # no LLM configured: evidence passages only
    "uncited",  # generated answer without any valid citation: unverified
    "generation_failed",  # LLM call failed: evidence passages still returned
]


class Source(BaseModel):
    id: int = Field(description="1-based number used by [n] markers in the answer.")
    chunk_id: str
    doc_id: str
    title: str
    publisher: str
    report_ref: str | None = None
    page: int = Field(description="PDF page index (1 = cover), not the printed page number.")
    section: str | None = None
    text: str
    score: float
    cited: bool


class Timings(BaseModel):
    retrieval_ms: int
    generation_ms: int = 0


class AskResponse(BaseModel):
    question: str
    status: AnswerStatus
    answer: str | None
    sources: list[Source]
    warnings: list[str] = []
    model: str | None = None
    timings: Timings
    disclaimer: str


class DocumentInfo(BaseModel):
    doc_id: str
    title: str
    publisher: str
    report_ref: str | None
    url: str | None
    published: str | None
    indexed: bool
    chunks: int


class DocumentsResponse(BaseModel):
    documents: list[DocumentInfo]
    total_chunks: int

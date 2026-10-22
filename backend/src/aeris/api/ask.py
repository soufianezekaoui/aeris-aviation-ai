from __future__ import annotations

from fastapi import APIRouter, Depends

from aeris.api.deps import get_rag_service
from aeris.config import Settings, get_settings
from aeris.ingestion.manifest import load_manifest
from aeris.rag.service import RagService
from aeris.rag.store import index_stats
from aeris.schemas import (
    AskRequest,
    AskResponse,
    DocumentInfo,
    DocumentsResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/api", tags=["rag"])
_ERRORS = {
    422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 503: {"model": ErrorResponse},
}


@router.post("/ask", response_model=AskResponse, responses=_ERRORS,
             summary="Ask a question; answers carry verified citations")
def ask(
    body: AskRequest,
    service: RagService = Depends(get_rag_service),
    settings: Settings = Depends(get_settings),
) -> AskResponse:
    if len(body.question) > settings.max_question_chars:
        raise ValueError(f"question exceeds {settings.max_question_chars} characters")
    return service.ask(body.question, body.top_k, body.doc_ids)


@router.get("/documents", response_model=DocumentsResponse,
            summary="Indexed reports with provenance and chunk counts")
def documents(
    service: RagService = Depends(get_rag_service),
    settings: Settings = Depends(get_settings),
) -> DocumentsResponse:
    stats = index_stats(service.store)
    manifest = load_manifest(settings.manifest_path)
    docs = [
        DocumentInfo(
            doc_id=d.doc_id, title=d.title, publisher=d.publisher, report_ref=d.report_ref,
            url=d.url, published=d.published,
            indexed=stats.documents.get(d.doc_id, 0) > 0,
            chunks=stats.documents.get(d.doc_id, 0),
        )
        for d in manifest.documents
    ]
    return DocumentsResponse(documents=docs, total_chunks=stats.chunks)

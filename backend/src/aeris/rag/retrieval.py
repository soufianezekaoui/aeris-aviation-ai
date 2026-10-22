from __future__ import annotations

from dataclasses import dataclass

from langchain_chroma import Chroma

from aeris.rag.errors import RetrievalError


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict
    score: float  # cosine relevance, 1 = identical direction


def retrieve(
    store: Chroma,
    question: str,
    k: int,
    min_relevance: float,
    doc_ids: list[str] | None = None,
) -> list[RetrievedChunk]:
    """Top-k semantic search; passages below ``min_relevance`` are discarded (RULE-03)."""
    where = None
    if doc_ids:
        where = {"doc_id": doc_ids[0]} if len(doc_ids) == 1 else {"doc_id": {"$in": doc_ids}}
    try:
        hits = store.similarity_search_with_relevance_scores(question, k=k, filter=where)
    except Exception as exc:  # noqa: BLE001 - embedding or store failure, reported uniformly
        raise RetrievalError(f"{type(exc).__name__}: {exc}") from exc
    found = [
        RetrievedChunk(
            chunk_id=doc.id or doc.metadata.get("chunk_id", ""),
            text=doc.page_content,
            metadata=dict(doc.metadata),
            score=round(float(score), 4),
        )
        for doc, score in hits
    ]
    found.sort(key=lambda c: c.score, reverse=True)
    return [c for c in found if c.score >= min_relevance]

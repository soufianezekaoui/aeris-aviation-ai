from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from aeris.config import Settings
from aeris.ingestion.models import Chunk
from aeris.rag.embeddings import embedding_fingerprint
from aeris.rag.errors import IndexMismatchError

log = logging.getLogger(__name__)
BATCH = 64


@dataclass
class IndexStats:
    chunks: int = 0
    documents: dict[str, int] = field(default_factory=dict)


def open_store(settings: Settings, embeddings: Embeddings) -> Chroma:
    """Open (or create) the collection, refusing to mix embedding models."""
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = embedding_fingerprint(settings)
    client = chromadb.PersistentClient(
        path=str(settings.vector_store_dir),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )
    existing = {c.name if hasattr(c, "name") else c for c in client.list_collections()}
    if settings.collection_name in existing:
        meta = client.get_collection(settings.collection_name).metadata or {}
        built_with = meta.get("embedding")
        if built_with and built_with != fingerprint:
            raise IndexMismatchError(
                f"Index was built with '{built_with}' but '{fingerprint}' is configured. "
                "Re-run `aeris ingest --reset` or restore the original EMBEDDING_* settings."
            )
    return Chroma(
        client=client,
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine", "embedding": fingerprint},
    )


def reset_store(settings: Settings) -> None:
    client = chromadb.PersistentClient(
        path=str(settings.vector_store_dir),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(settings.collection_name)
    except Exception:  # noqa: BLE001 - nothing to reset on a fresh install
        log.info("no existing collection to delete")


def replace_document(store: Chroma, doc_id: str, chunks: list[Chunk]) -> int:
    """Idempotent re-ingest: remove the document's old chunks, then add the new ones."""
    old = store.get(where={"doc_id": doc_id}, include=[])["ids"]
    if old:
        store.delete(ids=old)
    for start in range(0, len(chunks), BATCH):
        batch = chunks[start : start + BATCH]
        store.add_documents(
            [Document(page_content=c.text, metadata=c.metadata) for c in batch],
            ids=[c.chunk_id for c in batch],
        )
    return len(chunks)


def index_stats(store: Chroma) -> IndexStats:
    metas = store.get(include=["metadatas"])["metadatas"] or []
    counts = Counter(m["doc_id"] for m in metas)
    return IndexStats(chunks=len(metas), documents=dict(counts))

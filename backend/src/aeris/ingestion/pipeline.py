from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from aeris.config import Settings
from aeris.ingestion.chunk import ChunkingConfig, chunk_pages
from aeris.ingestion.clean import clean_pages
from aeris.ingestion.extract import extract_pages
from aeris.ingestion.manifest import DocumentEntry, resolve_pdf
from aeris.ingestion.models import Chunk


@dataclass
class PreparationReport:
    doc_id: str
    pdf: Path
    pages_total: int
    pages_empty: list[int] = field(default_factory=list)
    pages_failed: list[int] = field(default_factory=list)
    pages_toc: list[int] = field(default_factory=list)
    boilerplate_removed: list[str] = field(default_factory=list)
    chunks: int = 0
    avg_chunk_chars: int = 0
    pdf_created: str | None = None
    seconds: float = 0.0


def prepare_document(
    entry: DocumentEntry, settings: Settings
) -> tuple[list[Chunk], PreparationReport]:
    started = time.perf_counter()
    pdf = resolve_pdf(entry, settings.documents_dir)
    extracted = extract_pages(pdf)
    pages, cleaning = clean_pages(extracted.pages)
    chunks = chunk_pages(
        pages,
        entry,
        ChunkingConfig(settings.chunk_size, settings.chunk_overlap, settings.min_chunk_chars),
    )
    report = PreparationReport(
        doc_id=entry.doc_id,
        pdf=pdf,
        pages_total=len(extracted.pages),
        pages_empty=cleaning.empty_pages,
        pages_failed=extracted.failed_pages,
        pages_toc=cleaning.toc_pages,
        boilerplate_removed=cleaning.boilerplate,
        chunks=len(chunks),
        avg_chunk_chars=round(sum(len(c.text) for c in chunks) / len(chunks)) if chunks else 0,
        pdf_created=extracted.pdf_created,
        seconds=round(time.perf_counter() - started, 1),
    )
    return chunks, report

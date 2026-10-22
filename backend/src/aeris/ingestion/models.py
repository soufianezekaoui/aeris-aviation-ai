from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PageText:
    # A single page of text extracted from a PDF, with its 1-based page index.

    page: int
    text: str


@dataclass
class ExtractedDocument:
    pages: list[PageText]
    pdf_created: str | None = None
    failed_pages: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class Chunk:
    # A chunk of text extracted from a PDF, with metadata for retrieval and citation.

    chunk_id: str
    text: str
    metadata: dict[str, str | int]

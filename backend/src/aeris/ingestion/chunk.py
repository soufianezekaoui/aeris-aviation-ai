from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from aeris.ingestion.manifest import DocumentEntry
from aeris.ingestion.models import Chunk, PageText

# "1.11.2. Cockpit Voice Recorder (CVR)" / "3.1 Findings" / "1. FACTUAL INFORMATION".
# A dotted number is required: bare "54 See Appendices"-style footnote lines must not match.
_HEADING_RE = re.compile(
    r"^(?:\d{1,2}(?:\.\d{1,2})+\.?|\d{1,2}\.)\s+[A-Z][^\n]{2,80}$", re.MULTILINE
)


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_chars: int = 80


def _headings(text: str) -> list[tuple[int, str]]:
    found = []
    for match in _HEADING_RE.finditer(text):
        label = match.group(0).strip()
        if label.endswith((".", ",", ";")) and not re.match(r"^\d{1,2}\.\s", label):
            continue  # a sentence, not a heading
        found.append((match.start(), label))
    return found


def chunk_pages(
    pages: list[PageText], doc: DocumentEntry, config: ChunkingConfig
) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        keep_separator="end",
        add_start_index=True,
    )
    chunks: list[Chunk] = []
    section = ""  # carried across pages until a new heading appears
    for page in pages:
        headings = _headings(page.text)
        index = 0
        for piece in splitter.create_documents([page.text]):
            start = int(piece.metadata.get("start_index", 0))
            for offset, label in headings:
                if offset <= start:
                    section = label
            text = piece.page_content.strip()
            if len(text) < config.min_chunk_chars:
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}-p{page.page:04d}-c{index:02d}",
                    text=text,
                    metadata={
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "publisher": doc.publisher,
                        "report_ref": doc.report_ref or "",
                        "source_file": doc.file,
                        "page": page.page,
                        "chunk_index": index,
                        "section": section,
                    },
                )
            )
            index += 1
        # headings later on the page apply to the *next* page's opening chunks
        if headings:
            section = headings[-1][1]
    return chunks

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader

from aeris.ingestion.models import ExtractedDocument, PageText

# pypdf is chatty about fonts it cannot fully decode; real problems surface as failed pages.
logging.getLogger("pypdf").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


def extract_pages(pdf_path: Path) -> ExtractedDocument:
    """
    A page that raises is recorded in ``failed_pages`` (and yields empty text) instead of
    aborting the whole document. Scanned pages simply return no text: OCR is out of scope.
    """
    reader = PdfReader(str(pdf_path), strict=False)
    pages: list[PageText] = []
    failed: list[int] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 - one bad page must not sink the document
            log.warning("%s: page %d failed to extract: %s", pdf_path.name, index, exc)
            failed.append(index)
            text = ""
        pages.append(PageText(page=index, text=text))

    created = None
    try:
        meta = reader.metadata
        if meta and meta.creation_date:
            created = meta.creation_date.date().isoformat()
    except Exception:  # noqa: BLE001 - malformed metadata is common and non-fatal
        created = None
    return ExtractedDocument(pages=pages, pdf_created=created, failed_pages=failed)

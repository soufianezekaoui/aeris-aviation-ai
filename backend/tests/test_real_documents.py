from __future__ import annotations

import pytest

from aeris.config import get_settings
from aeris.ingestion.manifest import load_manifest
from aeris.ingestion.pipeline import prepare_document

pytestmark = pytest.mark.slow

EXPECTED = {
    # doc_id: (pages, term that must appear in some chunk, running header that must be gone)
    "spanair_5022": (284, "takeoff configuration", "Report A-032/2008"),
    "ups_6": (324, "lithium", None),
}


@pytest.fixture(scope="module")
def prepared():
    settings = get_settings()
    manifest = load_manifest(settings.manifest_path)
    return {e.doc_id: prepare_document(e, settings) for e in manifest.documents}


@pytest.mark.parametrize("doc_id", EXPECTED)
def test_real_report_is_extracted_cleaned_and_chunked(prepared, doc_id):
    pages, term, header = EXPECTED[doc_id]
    chunks, report = prepared[doc_id]

    assert report.pages_total == pages
    assert report.pages_failed == []
    assert len(chunks) > 500
    assert any(term.lower() in c.text.lower() for c in chunks)
    assert all(len(c.text) <= get_settings().chunk_size for c in chunks)
    if header:
        assert all(header not in c.text for c in chunks)
    labelled = sum(1 for c in chunks if c.metadata["section"])
    assert labelled / len(chunks) > 0.9, "section labels should cover most chunks"


def test_table_of_contents_pages_contribute_no_chunks(prepared):
    chunks, report = prepared["spanair_5022"]
    pages_with_chunks = {c.metadata["page"] for c in chunks}
    # pages 7-13 are the table of contents / lists of figures in this report
    assert not pages_with_chunks & set(range(7, 14))

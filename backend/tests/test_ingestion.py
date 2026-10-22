from __future__ import annotations

import json

import pytest

from aeris.config import Settings
from aeris.ingestion.chunk import ChunkingConfig, _headings, chunk_pages
from aeris.ingestion.clean import clean_pages
from aeris.ingestion.extract import extract_pages
from aeris.ingestion.manifest import DocumentEntry, load_manifest, resolve_pdf
from aeris.ingestion.models import PageText
from aeris.ingestion.pipeline import prepare_document

from .helpers import write_pdf

DOC = DocumentEntry(
    doc_id="demo", file="raw/demo.pdf", title="Demo report", publisher="Demo Authority",
    report_ref="D-1/2020",
)


def pages(*texts: str) -> list[PageText]:
    return [PageText(page=i + 1, text=t) for i, t in enumerate(texts)]


# -----------extraction
def test_extract_pages_numbers_pages_and_keeps_blank_pages(tmp_path):
    pdf = write_pdf(tmp_path / "a.pdf", ["Alpha line one\nAlpha line two", "", "Gamma page"])
    doc = extract_pages(pdf)
    assert [p.page for p in doc.pages] == [1, 2, 3]
    assert "Alpha line one" in doc.pages[0].text
    assert doc.pages[1].text.strip() == ""
    assert "Gamma" in doc.pages[2].text
    assert doc.failed_pages == []


# ------------cleaning
def test_running_header_and_page_numbers_are_removed():
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india",
             "juliet"]
    raw = [
        f"Report A-032/2008\nUnique paragraph {w} about flap configuration.\n{i + 1}"
        for i, w in enumerate(words)
    ]
    cleaned, report = clean_pages(pages(*raw))
    assert "report a-#/#" in report.boilerplate
    assert len(cleaned) == 10
    for page, word in zip(cleaned, words, strict=True):
        assert page.text == f"Unique paragraph {word} about flap configuration."


def test_header_is_removed_with_roman_page_numbers_and_when_not_at_page_edge():
    # Front matter uses roman numerals ("Report A-032/2008 xvii"); and on pages with footnotes
    # the extractor emits the header *after* the body, outside the first/last-3-lines zone.
    raw = []
    for i in range(10):
        label = ["ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi"][i]
        raw.append(f"Report A-032/2008 {label}\nBody paragraph {'abcdefghij'[i] * 4} one.")
    for i in range(10):
        word = "klmnopqrst"[i] * 4
        raw.append(
            f"Body paragraph {word} one.\nBody line two {word}.\nBody line three {word}.\n"
            f"Body line four {word}.\nReport A-032/2008\n{i + 1}\n"
            f"Footnote text {word} one.\nFootnote text {word} two."
        )
    cleaned, _ = clean_pages(pages(*raw))
    assert len(cleaned) == 20
    assert all("Report A-032/2008" not in p.text for p in cleaned)
    assert "Footnote text kkkk one." in cleaned[10].text  # footnotes are kept


def test_bare_numbers_inside_a_data_table_are_not_deleted():
    # "#" is a recurring page-number key, but lone digits in the page body are real data.
    raw = [
        f"Alpha {w} line\nA\n5\nB\n7\nC\n9\nD\n11\nclosing words {w}\n{i + 1}"
        for i, w in enumerate(["aa", "bb", "cc", "dd", "ee", "ff"])
    ]
    cleaned, _ = clean_pages(pages(*raw))
    assert all("5" in p.text and "11" in p.text for p in cleaned)


def test_content_that_only_looks_like_a_header_on_few_pages_is_kept():
    raw = ["Alpha body text here.", "Beta body text here.", "Gamma body text here."]
    cleaned, report = clean_pages(pages(*raw))
    assert report.boilerplate == []
    assert [p.text for p in cleaned] == raw


def test_dehyphenation_reflow_and_heading_preserved():
    text = (
        "The crew did not exam-\nine the flap settings before\ntakeoff.\n"
        "1.2 Next heading\nThe following text."
    )
    (page,), _ = clean_pages(pages(text))
    assert page.text == (
        "The crew did not examine the flap settings before takeoff.\n"
        "1.2 Next heading\nThe following text."
    )


def test_ligatures_soft_hyphens_and_repeated_spaces_are_normalised():
    (page,), _ = clean_pages(pages("The \ufb01re\u00adfighters   arrived\u00a0quickly."))
    assert page.text == "The firefighters arrived quickly."


def test_blank_pages_are_reported_not_returned():
    cleaned, report = clean_pages(pages("Some real text on page one.", "  \n ", "More text."))
    assert [p.page for p in cleaned] == [1, 3]
    assert report.empty_pages == [2]


def test_pure_toc_page_is_dropped_but_content_page_with_mini_toc_keeps_content():
    leader = "." * 30
    # Long TOC entries wrap onto a second line that has NO dot leaders (as in the Spanair
    # report). Those orphans must not survive and pollute retrieval.
    toc_lines = []
    for i in range(10):
        toc_lines.append(f"{i}. Section title number {i} {leader} {i + 10}")
        if i % 3 == 0:
            toc_lines.append("recorded on the flight data recorder (continued)")
    toc = "\n".join(toc_lines)
    mixed = (
        "TEST REPORT cover with real, useful content about oxygen masks.\n"
        "Second line of genuine content.\n"
        "Third line of genuine content.\n"
        "Fourth line of genuine content.\n"
        + "\n".join(f"{i}. Item {i} {leader} {i}" for i in range(6))
    )
    cleaned, report = clean_pages(pages(toc, mixed))
    assert [p.page for p in cleaned] == [2]  # pure TOC page dropped
    assert report.toc_pages == [1, 2]
    assert "oxygen masks" in cleaned[0].text
    assert "Item" not in cleaned[0].text  # its leader lines were removed
    assert report.empty_pages == []  # a TOC page is not "empty"


# -------------chunking
def test_headings_require_dotted_numbers_and_reject_sentences():
    text = (
        "1.11.2. Cockpit Voice Recorder (CVR)\n"
        "1.12 Wreckage and Impact Information\n"
        "3. FACTUAL INFORMATION\n"
        "54 See Appendices\n"
        "1.3 This line is a full sentence that ends with a period.\n"
        "20 August 2008, the stations were staffed by 21 firefighters."
    )
    labels = [label for _, label in _headings(text)]
    assert labels == [
        "1.11.2. Cockpit Voice Recorder (CVR)",
        "1.12 Wreckage and Impact Information",
        "3. FACTUAL INFORMATION",
    ]


def test_chunks_respect_size_carry_section_across_pages_and_have_stable_ids():
    body = " ".join(
        f"Sentence number {i} describes the flap and slat configuration." for i in range(40)
    )
    p1 = PageText(1, f"1.2. Findings on configuration\n{body}")
    p2 = PageText(2, body)
    config = ChunkingConfig(chunk_size=300, chunk_overlap=30, min_chunk_chars=50)

    chunks = chunk_pages([p1, p2], DOC, config)
    again = chunk_pages([p1, p2], DOC, config)

    assert chunks and [c.chunk_id for c in chunks] == [c.chunk_id for c in again]
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert all(len(c.text) <= 300 for c in chunks)
    assert {c.metadata["page"] for c in chunks} == {1, 2}
    assert all(c.metadata["section"] == "1.2. Findings on configuration" for c in chunks)
    first = chunks[0].metadata
    assert first["doc_id"] == "demo" and first["publisher"] == "Demo Authority"
    assert first["report_ref"] == "D-1/2020" and first["source_file"] == "raw/demo.pdf"


def test_tiny_chunks_are_dropped():
    chunks = chunk_pages([PageText(1, "Too short.")], DOC, ChunkingConfig(min_chunk_chars=80))
    assert chunks == []


# --------------manifest
def _write_manifest(tmp_path, docs):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"documents": docs}), encoding="utf-8")
    return path


def _entry(**kw):
    base = {"doc_id": "a", "file": "raw/a.pdf", "title": "T", "publisher": "P"}
    return {**base, **kw}


def test_manifest_loads_and_rejects_duplicate_ids(tmp_path):
    ok = load_manifest(_write_manifest(tmp_path, [_entry(), _entry(doc_id="b")]))
    assert [d.doc_id for d in ok.documents] == ["a", "b"]
    with pytest.raises(ValueError, match="duplicate doc_id"):
        load_manifest(_write_manifest(tmp_path, [_entry(), _entry()]))


def test_manifest_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="manifest not found"):
        load_manifest(tmp_path / "nope.json")


def test_resolve_pdf_rejects_path_traversal_and_missing_files(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "secret.pdf").write_bytes(b"x")
    with pytest.raises(ValueError, match="escapes"):
        resolve_pdf(DocumentEntry(**_entry(file="../secret.pdf")), docs_dir)
    with pytest.raises(FileNotFoundError, match="PDF not found"):
        resolve_pdf(DocumentEntry(**_entry(file="raw/missing.pdf")), docs_dir)


def test_doc_id_must_be_url_safe():
    with pytest.raises(ValueError):
        DocumentEntry(**_entry(doc_id="Bad ID!"))


# --------------pipeline
def test_prepare_document_end_to_end(tmp_path):
    words = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    texts = [
        f"Report D-1/2020\n1.{i + 1}. Heading {w}\n"
        + " ".join(
            f"Finding {w} {j} about the takeoff configuration warning system." for j in range(6)
        )
        for i, w in enumerate(words)
    ]
    write_pdf(tmp_path / "raw" / "demo.pdf", texts)
    settings = Settings(_env_file=None, documents_dir=tmp_path, chunk_size=400, chunk_overlap=40)

    chunks, report = prepare_document(DOC, settings)

    assert report.pages_total == 6 and report.chunks == len(chunks) > 0
    assert "report d-#/#" in report.boilerplate_removed
    assert all("Report D-1/2020" not in c.text for c in chunks)
    assert {c.metadata["page"] for c in chunks} == set(range(1, 7))
    assert chunks[0].metadata["section"].startswith("1.1. Heading alpha")
    assert report.avg_chunk_chars > 0

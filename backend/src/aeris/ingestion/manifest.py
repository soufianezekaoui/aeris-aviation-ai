from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class DocumentEntry(BaseModel):
    doc_id: str = Field(pattern=r"^[a-z0-9_\-]+$", description="Stable, URL-safe identifier.")
    file: str = Field(description="PDF path, relative to the documents directory.")
    title: str
    publisher: str
    report_ref: str | None = None
    language: str = "en"
    url: str | None = Field(default=None, description="Where the original was obtained.")
    published: str | None = Field(default=None, description="Publication date, if known.")
    notes: str | None = None


class Manifest(BaseModel):
    documents: list[DocumentEntry]

    @model_validator(mode="after")
    def _unique_ids(self) -> Manifest:
        ids = [d.doc_id for d in self.documents]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate doc_id in manifest: {sorted(dupes)}")
        return self


def load_manifest(path: Path) -> Manifest:
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")
    return Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def resolve_pdf(entry: DocumentEntry, documents_dir: Path) -> Path:
    pdf = (documents_dir / entry.file).resolve()
    root = documents_dir.resolve()
    if root not in pdf.parents:  # never read outside the documents directory
        raise ValueError(f"{entry.doc_id}: file path escapes documents dir: {entry.file}")
    if not pdf.is_file():
        raise FileNotFoundError(f"{entry.doc_id}: PDF not found: {pdf}")
    return pdf

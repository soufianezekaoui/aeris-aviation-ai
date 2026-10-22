from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from aeris.ingestion.models import PageText

EDGE_LINES = 3  # header/footer zone: first/last N non-empty lines of a page
_LIGATURES = str.maketrans({"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"})
_LEADER_RE = re.compile(r"\.{4,}|(?:\. ){4,}")


@dataclass
class CleaningReport:
    boilerplate: list[str] = field(default_factory=list)
    empty_pages: list[int] = field(default_factory=list)
    toc_pages: list[int] = field(default_factory=list)


def _raw_lines(text: str) -> list[str]:
    return text.replace("\x00", "").replace("\f", "\n").splitlines()


_ROMAN_TAIL = re.compile(r"\s+[ivxlcdm]{1,7}$")


def _line_key(line: str) -> str:
    # Digits collapse to '#' and a trailing roman numeral is dropped, so that "Page 3" and "page iii" are treated as the same boilerplate line.
    key = re.sub(r"\d+", "#", line.strip().lower())
    stripped = _ROMAN_TAIL.sub("", key)
    return stripped if len(stripped) >= 5 else key


def _first_last(lines: list[str]) -> set[int]:
    nonblank = [i for i, line in enumerate(lines) if line.strip()]
    return {nonblank[0], nonblank[-1]} if nonblank else set()


def _is_boilerplate(lines: list[str], index: int, boiler: set[str], first_last: set[int]) -> bool:
    key = _line_key(lines[index])
    if key not in boiler:
        return False
    if re.search(r"[a-z]", key):
        # A recurring text header/footer. Extractors may emit it away from the page edge
        # (after the body but before footnotes), so remove it wherever it sits.
        return True
    # Bare page numbers: only as the first/last line, never digits inside a data table.
    return index in first_last


def _edge_indices(lines: list[str]) -> set[int]:
    nonblank = [i for i, line in enumerate(lines) if line.strip()]
    return set(nonblank[:EDGE_LINES] + nonblank[-EDGE_LINES:])


def find_boilerplate(
    pages: list[PageText], min_ratio: float = 0.4, min_pages: int = 5
) -> set[str]:
    """Normalised lines that recur in the header/footer zone of many pages."""
    nonempty = [p for p in pages if p.text.strip()]
    if len(nonempty) < min_pages:
        return set()
    counts: Counter[str] = Counter()
    for page in nonempty:
        lines = _raw_lines(page.text)
        keys = {
            _line_key(lines[i])
            for i in _edge_indices(lines)
            if 0 < len(lines[i].strip()) <= 120
        }
        counts.update(keys)
    threshold = max(2, math.ceil(min_ratio * len(nonempty)))
    return {key for key, n in counts.items() if key and n >= threshold}


def _normalise_line(line: str) -> str:
    line = unicodedata.normalize("NFC", line).translate(_LIGATURES).replace("\u00ad", "")
    line = _LEADER_RE.sub(" ", line)
    return re.sub(r"[ \t\u00a0]+", " ", line).strip()


def _reflow(lines: list[str]) -> str:
    """Rejoin visually wrapped lines; keep headings / list items on their own lines."""
    out: list[str] = []
    for line in lines:
        if not line:
            if out and out[-1]:
                out.append("")  # paragraph break
            continue
        if out and out[-1]:
            prev = out[-1]
            if re.search(r"[A-Za-z]-$", prev) and line[:1].islower():
                out[-1] = prev[:-1] + line  # "exam-" + "ple" -> "example"
                continue
            if line[:1].islower() or prev.endswith(","):
                out[-1] = f"{prev} {line}"
                continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


MIN_LEADER_LINES = 5
# Share of dot-leader lines above which a page is a table of contents / list of figures.
# Measured on the two bundled reports: real TOC pages score 0.76-0.96, while an appendix
# cover that merely contains its own mini-TOC scores 0.66. Heuristic: re-tune with new sources.
TOC_PAGE_RATIO = 0.70


def _handle_toc(raw_lines: list[str]) -> tuple[list[str], bool, bool]:
    """
    A TOC page is dropped entirely: wrapped entries have no dot leaders, so filtering only
    the leader lines would leave orphan fragments that pollute retrieval. A page that merely
    *contains* a few leader lines keeps its real content; only the leader lines go.
    """
    nonblank = [line for line in raw_lines if line.strip()]
    leader = [bool(_LEADER_RE.search(line)) for line in raw_lines]
    n_leader = sum(leader)
    if n_leader < MIN_LEADER_LINES:
        return raw_lines, False, False
    if n_leader / max(len(nonblank), 1) >= TOC_PAGE_RATIO:
        return [], True, True
    kept = [line for line, is_leader in zip(raw_lines, leader, strict=True) if not is_leader]
    return kept, True, False


def clean_pages(pages: list[PageText]) -> tuple[list[PageText], CleaningReport]:
    """Return cleaned pages (pages with no usable text are dropped) and a report."""
    boiler = find_boilerplate(pages)
    report = CleaningReport(boilerplate=sorted(boiler))
    cleaned: list[PageText] = []
    for page in pages:
        raw = _raw_lines(page.text)
        if not page.text.strip():
            report.empty_pages.append(page.page)
            continue
        # Tables of contents repeat every heading and would pollute retrieval.
        raw, had_toc, whole_page_toc = _handle_toc(raw)
        if had_toc:
            report.toc_pages.append(page.page)
        if whole_page_toc:
            continue
        first_last = _first_last(raw)
        kept = [
            line
            for i, line in enumerate(raw)
            if not _is_boilerplate(raw, i, boiler, first_last)
        ]
        text = _reflow([_normalise_line(line) for line in kept])
        if text:
            cleaned.append(PageText(page=page.page, text=text))
        elif not had_toc:  # a pure TOC page is already counted in toc_pages
            report.empty_pages.append(page.page)
    return cleaned, report

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from langchain_chroma import Chroma

from aeris.rag.retrieval import retrieve


@dataclass
class EvalItem:
    question: str
    expected_doc: str | None = None
    expected_keywords: tuple[str, ...] = ()
    should_refuse: bool = False


@dataclass
class EvalResult:
    threshold: float
    positives: int
    doc_hit: float
    evidence_hit: float
    mrr: float
    negatives: int
    refused: float
    unanswerable: list[str]


def load_items(path: Path) -> list[EvalItem]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            raw["expected_keywords"] = tuple(raw.get("expected_keywords", ()))
            items.append(EvalItem(**raw))
    return items


def _matches(text: str, keywords: tuple[str, ...]) -> bool:
    low = text.lower()
    return all(k.lower() in low for k in keywords)


def find_unanswerable(store: Chroma, items: list[EvalItem]) -> list[str]:
    """Eval items whose evidence does not exist in the index: a broken test, not a miss."""
    bad = []
    for item in items:
        if item.should_refuse:
            continue
        docs = store.get(where={"doc_id": item.expected_doc}, include=["documents"])["documents"]
        if not any(_matches(d, item.expected_keywords) for d in docs or []):
            bad.append(item.question)
    return bad


def evaluate(
    store: Chroma, items: list[EvalItem], k: int, thresholds: list[float]
) -> list[EvalResult]:
    # retrieve once without a threshold, then apply each threshold in memory
    raw = {i.question: retrieve(store, i.question, k, 0.0) for i in items}
    unanswerable = find_unanswerable(store, items)
    results = []
    for t in thresholds:
        pos = [i for i in items if not i.should_refuse]
        neg = [i for i in items if i.should_refuse]
        doc_hits = ev_hits = 0
        rr = 0.0
        for item in pos:
            kept = [c for c in raw[item.question] if c.score >= t]
            doc_hits += any(c.metadata["doc_id"] == item.expected_doc for c in kept)
            for rank, c in enumerate(kept, start=1):
                if c.metadata["doc_id"] == item.expected_doc and _matches(
                    c.text, item.expected_keywords
                ):
                    ev_hits += 1
                    rr += 1 / rank
                    break
        refused = sum(1 for i in neg if not [c for c in raw[i.question] if c.score >= t])
        results.append(EvalResult(
            threshold=t, positives=len(pos),
            doc_hit=doc_hits / max(len(pos), 1), evidence_hit=ev_hits / max(len(pos), 1),
            mrr=rr / max(len(pos), 1), negatives=len(neg),
            refused=refused / max(len(neg), 1), unanswerable=unanswerable,
        ))
    return results

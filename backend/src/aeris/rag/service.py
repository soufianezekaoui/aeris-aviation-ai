from __future__ import annotations

import logging
import re
import time

from langchain_chroma import Chroma
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser

from aeris import SAFETY_DISCLAIMER
from aeris.config import Settings
from aeris.rag.errors import IndexEmptyError, UnknownDocumentError
from aeris.rag.prompts import INSUFFICIENT_MARKER, PROMPT, format_context
from aeris.rag.retrieval import RetrievedChunk, retrieve
from aeris.rag.store import index_stats
from aeris.schemas import AskResponse, Source, Timings

log = logging.getLogger(__name__)

NO_EVIDENCE = (
    "The indexed reports do not contain enough relevant evidence to answer this question. "
    "Try rephrasing it, or check that the report you need has been ingested."
)
_CITE = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")


def verify_citations(answer: str, n_sources: int) -> tuple[str, set[int], int]:
    """
       Keep only citations that point at a retrieved source (RULE-02).
    """
    cited: set[int] = set()
    removed = 0

    def fix(match: re.Match[str]) -> str:
        nonlocal removed
        numbers = [int(x) for x in re.split(r"[,;]", match.group(1))]
        valid = [n for n in numbers if 1 <= n <= n_sources]
        removed += len(numbers) - len(valid)
        cited.update(valid)
        return f"[{', '.join(map(str, valid))}]" if valid else ""

    text = re.sub(r"[ \t]{2,}", " ", _CITE.sub(fix, answer)).strip()
    return text, cited, removed


def _source(i: int, c: RetrievedChunk, cited: bool) -> Source:
    m = c.metadata
    return Source(
        id=i, chunk_id=c.chunk_id, doc_id=m["doc_id"], title=m["title"],
        publisher=m.get("publisher", ""), report_ref=m.get("report_ref") or None,
        page=int(m["page"]), section=m.get("section") or None, text=c.text,
        score=c.score, cited=cited,
    )


class RagService:
    def __init__(self, store: Chroma, llm: BaseChatModel | None, settings: Settings) -> None:
        self.store, self.llm, self.settings = store, llm, settings
        self._chain = (PROMPT | llm | StrOutputParser()) if llm is not None else None

    def ask(
        self, question: str, top_k: int | None = None, doc_ids: list[str] | None = None
    ) -> AskResponse:
        stats = index_stats(self.store)
        if stats.chunks == 0:
            raise IndexEmptyError("No documents are indexed yet. Run `aeris ingest` first.")
        unknown = [d for d in (doc_ids or []) if d not in stats.documents]
        if unknown:
            raise UnknownDocumentError(f"unknown doc_id(s): {unknown}")

        t0 = time.perf_counter()
        chunks = retrieve(
            self.store, question, top_k or self.settings.retrieval_top_k,
            self.settings.min_relevance, doc_ids,
        )
        retrieval_ms = round((time.perf_counter() - t0) * 1000)

        def respond(status, answer, cited=frozenset(), warnings=None, gen_ms=0, model=None):
            return AskResponse(
                question=question, status=status, answer=answer,
                sources=[_source(i, c, i in cited) for i, c in enumerate(chunks, start=1)],
                warnings=warnings or [], model=model,
                timings=Timings(retrieval_ms=retrieval_ms, generation_ms=gen_ms),
                disclaimer=SAFETY_DISCLAIMER,
            )

        if not chunks:  # RULE-01/03: no evidence, so no generation at all
            return respond("insufficient_evidence", NO_EVIDENCE)
        if self._chain is None:
            return respond(
                "retrieval_only", None,
                warnings=["No LLM configured: showing retrieved passages only."],
            )

        t1 = time.perf_counter()
        try:
            raw = self._chain.invoke({"context": format_context(chunks), "question": question})
        except Exception as exc:  # noqa: BLE001 - provider errors vary widely
            log.exception("LLM call failed")
            return respond(
                "generation_failed", None,
                warnings=[f"The language model request failed ({type(exc).__name__}). "
                          "Evidence passages are shown below."],
            )
        gen_ms = round((time.perf_counter() - t1) * 1000)
        model = getattr(self.llm, "model", None) or getattr(self.llm, "model_name", None)

        raw = raw.strip()
        if raw.startswith(INSUFFICIENT_MARKER):
            why = raw[len(INSUFFICIENT_MARKER):].lstrip(": ").strip()
            return respond("insufficient_evidence", why or NO_EVIDENCE, gen_ms=gen_ms, model=model)

        answer, cited, removed = verify_citations(raw, len(chunks))
        warnings = []
        if removed:
            warnings.append(f"Removed {removed} citation(s) that did not match a retrieved source.")
        if not cited:
            warnings.append("The answer has no valid citations: treat it as unverified.")
            return respond("uncited", answer, warnings=warnings, gen_ms=gen_ms, model=model)
        return respond("answered", answer, cited, warnings, gen_ms, model)

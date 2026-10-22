# AERIS Backend

Python / FastAPI service for AERIS. Phase 1 delivers a **source-grounded RAG pipeline over
PDF investigation reports**: extraction, cleaning, chunking, embeddings, retrieval and
citations.

> **Safety boundary:** education / simulation only. Not a certified aviation system.

## Requirements
- Python 3.11+
- (optional) an LLM API key for generated answers. Without one the API runs in
  **retrieval-only mode** and returns cited passages.

## Setup
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev,local-embeddings,anthropic]"    # pick your extras, see below
cp ../.env.example ../.env                            # then edit values
```

| Extra              | Installs                                   | Use when                         |
| ------------------ | ------------------------------------------ | -------------------------------- |
| `local-embeddings` | `fastembed` (ONNX, no PyTorch)             | `EMBEDDING_PROVIDER=fastembed`   |
| `anthropic`        | `langchain-anthropic`                      | `LLM_PROVIDER=anthropic`         |
| `openai`           | `langchain-openai`                         | `LLM_PROVIDER=openai` / OpenAI embeddings |
| `dev`              | pytest, httpx, ruff                        | development                      |

## Configuration
All settings are environment variables (read from a repo-root `.env`). See
[`../.env.example`](../.env.example) and `src/aeris/config.py`. Blank values are treated as
unset. Secrets are never committed (RULE-12).

## Run
```bash
uvicorn aeris.main:app --reload --port 8000
# interactive API docs: http://localhost:8000/docs
```

## Ingestion pipeline (extract → clean → chunk)

```
manifest.json ─▶ extract (pypdf) ─▶ clean ─▶ chunk (+ citation metadata)
```

Try it without any API key or embedding model (a dry run that prints statistics and samples):
```bash
aeris prepare                          # both bundled reports
aeris prepare --doc spanair_5022 --show 3 --skip 200
```

### Document manifest
Every source is declared in [`knowledge/documents/manifest.json`](../knowledge/documents/manifest.json)
so provenance is never lost (RULE-11): `doc_id`, `file`, `title`, `publisher`, `report_ref`,
`url`, `published`. To add a report, drop the PDF in `knowledge/documents/raw/` and add an
entry. **Never invent `url`/`published`: leave them `null` until you have verified them.**
PDF paths are resolved inside the documents directory only (no path traversal).

### What the cleaner does (and why)
Rules were derived by profiling the two bundled reports, not guessed:

| Problem observed in the PDFs                               | Handling |
| ---------------------------------------------------------- | -------- |
| Running header `Report A-032/2008` on ~226 of 284 pages     | Found statistically (a header-zone line on ≥40 % of pages), removed anywhere on the page. Digits and trailing roman numerals are normalised (`… xvii`). |
| Bare page numbers                                          | Removed only as the first/last line of a page; digits inside tables are kept. |
| Table of contents / lists of figures (dot leaders)         | Pages that are ≥70 % leader lines are dropped. Otherwise only the leader lines go, so a content page that merely contains a mini-TOC keeps its content. |
| Hyphenated line wraps, ligatures, soft hyphens, odd spaces | De-hyphenated, `ﬁ→fi`, normalised, wrapped lines re-joined. |
| Blank / unreadable pages                                   | Reported in `empty_pages` / `failed_pages`; one bad page never aborts a document. |

### Chunking
`RecursiveCharacterTextSplitter` (LangChain) splits **per page**, so every chunk has an exact
`page`. Defaults: 1000 chars, 150 overlap (`CHUNK_SIZE`, `CHUNK_OVERLAP`); fragments under
80 chars are dropped. A numbered heading such as `1.11.2. Cockpit Voice Recorder (CVR)` is
detected and attached as `section` (carried across pages). Chunk ids are deterministic
(`spanair_5022-p0162-c01`), which makes re-ingestion idempotent.

> **Page numbers are PDF page indices** (page 1 = cover), not the number printed on the page.

### Known limitations
- **Text only.** Figures, scanned pages and most tables are not understood (no OCR).
- **Extraction quality.** `pypdf` occasionally splits words in some PDFs (e.g. `Decisio n`).
  Part of this is in the PDF itself (poppler's `pdftotext` shows the same break in places).
  `pdfminer.six` was tried: ~5× slower, different quirks. Re-evaluate with the retrieval eval
  if misses are traced to extraction.
- **Section labels are approximate.** A chunk gets the last numbered heading seen *before it
  starts*, so a passage that follows a heading later on the same page can carry the previous
  section's label. The PDF page is always exact.
- **Heuristics are tuned on two reports.** The 0.70 TOC threshold and the 40 % header rule
  separated cleanly here but should be re-checked when new sources are added
  (`aeris prepare` shows what was removed).

## RAG: embeddings, vector store, retrieval, citations

```
question ─▶ embed ─▶ Chroma (cosine) ─▶ top-k ─▶ relevance gate ─▶ LLM ─▶ citation check ─▶ answer
                                          │ nothing relevant
                                          └──────────────▶ "insufficient evidence" (LLM never called)
```

| Stage | Choice | Where |
| ----- | ------ | ----- |
| Embeddings | `fastembed` local ONNX (`BAAI/bge-small-en-v1.5`), or OpenAI, or `hash` (offline, lexical, tests only) | `rag/embeddings.py` |
| Vector DB | **Chroma**, persistent, cosine, telemetry off. All Chroma code lives in `rag/store.py` | `rag/store.py` |
| Retrieval | top-k + `MIN_RELEVANCE` gate, optional `doc_ids` filter | `rag/retrieval.py` |
| Generation | LangChain chain `prompt │ model │ parser`; Anthropic or OpenAI; **none = retrieval-only mode** | `rag/service.py`, `rag/llm.py` |

### Run it
```bash
aeris ingest --reset            # embed both reports (first run downloads the embedding model)
aeris stats
aeris ask "Why did the takeoff warning system not alert the crew?"
aeris eval --sweep              # retrieval quality across relevance thresholds
uvicorn aeris.main:app --reload # API on :8000, docs at /docs
```
Re-running `ingest` is idempotent (a document's old chunks are replaced). The index records
which embedding model built it and **refuses to be queried with a different one**
(`index_mismatch`), because mixing embedding spaces silently returns garbage.

### Guarantees (and the tests that enforce them)
- **Evidence before generation (RULE-01/03).** No chunk above `MIN_RELEVANCE` → status
  `insufficient_evidence`, and the LLM is not called.
- **No fabricated citations (RULE-02).** Every `[n]` in a generated answer is checked against
  the retrieved sources; invalid ones are removed and a warning is added. An answer with no
  valid citation is returned as `uncited` (UI shows "unverified"), never as `answered`.
- **Retrieved text is untrusted data.** The prompt says so, and the tag that wraps each
  passage cannot be closed from inside a passage.
- **Provider failure never loses the evidence.** If the LLM call fails the API still returns
  the passages (`generation_failed`); only the exception *class* is shown, never raw text.
- **Explicit errors** instead of tracebacks: `index_empty` (503), `index_mismatch` (503),
  `misconfigured` (503), `retrieval_failed` (502), `unknown_document` / `invalid_request` (422).

### API
| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/health` | liveness, provider names, safety disclaimer |
| GET | `/api/documents` | manifest provenance + indexed chunk counts |
| POST | `/api/ask` | `{question, top_k?, doc_ids?}` → answer, sources, status, warnings, timings |

`status` is one of `answered`, `insufficient_evidence`, `retrieval_only`, `uncited`,
`generation_failed`. Each source carries `doc_id`, `title`, `publisher`, `report_ref`,
`page` (**PDF page index**), `section`, the passage `text`, `score` and `cited`.
There is deliberately **no write/ingest endpoint**: ingestion is a maintainer CLI action, so the
API exposes no unauthenticated way to change the index.

### ⚠ Calibrate `MIN_RELEVANCE` before trusting refusals
Cosine scores are not comparable across embedding models. The default (0.35) is an
**uncalibrated guess for the default model**. After your first real ingest run:
```bash
aeris eval --sweep
```
and choose the threshold where `evidence@k` stays high while `refused` (out-of-corpus
questions) stays at 100 %. Add your own questions to `eval/questions.jsonl`
(`expected_doc` + `expected_keywords`, or `"should_refuse": true`); each item is checked
against the index so a broken test is reported as `WARNING unanswerable`.

For reference, the offline `hash` embeddings (lexical only) give: document found 100 %,
evidence found 71 %, out-of-corpus refused 100 % at `MIN_RELEVANCE=0.15`, and collapse above
0.3, which shows how model-specific this number is. Semantic embeddings should do better, but
that has **not yet been measured**: run the sweep and record your numbers.

### Not covered yet
Live LLM and `fastembed` model calls are exercised only through fakes in the tests (they need
network/keys); verify them once locally with `aeris ask`. No multi-turn memory, re-ranking or
hybrid (BM25) search yet: candidates to evaluate against the eval set.

## Quality checks
```bash
ruff check src tests
pytest                 # fast unit tests (generated PDFs)
pytest -m slow         # also runs the real 284- and 324-page reports (~20 s)
```

## Layout
```
backend/
  pyproject.toml
  src/aeris/
    config.py        # settings
    schemas.py       # API models
    api/             # FastAPI routers
    ingestion/       # manifest, extract, clean, chunk, pipeline
    rag/             # embeddings, store, retrieval, prompts, service, llm
    evaluation.py    # retrieval metrics behind `aeris eval`
    cli.py           # `aeris` command
    main.py          # app factory
  eval/questions.jsonl   # retrieval eval set
  tests/
```

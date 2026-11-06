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

## Database (simulation + checklists, Phase 2)

Simulation sessions, state snapshots, alerts and checklist progress live in a relational DB
(SQLAlchemy 2). **Nothing to set up:** with `DATABASE_URL` blank, a SQLite file is created at
`backend/data/aeris.db` (git-ignored) and the tables are created on first use.

To use **PostgreSQL** instead:
```bash
docker compose up -d                                   # from the repo root
pip install -e ".[postgres]"                           # driver
# in .env:  DATABASE_URL=postgresql://aeris:aeris@localhost:5432/aeris
```
`postgresql://` URLs are accepted as-is. Passwords are never printed in logs or errors.

Design notes:
- **Isolation by construction (RULE-06).** Every child table (`sim_state_snapshots`, `sim_alerts`,
  `sim_checklist_items`, `sim_checklist_events`) has a `session_id` foreign key with
  `ON DELETE CASCADE`; deleting a session removes everything that belongs to it.
- **Timestamps are always timezone-aware UTC** on both backends; naive datetimes are rejected.
- **Lazy initialisation.** The DB is opened on the first simulation request, so a database
  problem returns a clear `database_unavailable` error and **never breaks document Q&A**.
- Tables are created with `create_all` (no migration tool yet). Adding Alembic is a to-do before
  any schema change on a database that holds data you care about.

The DB tests run on SQLite **and** on a real embedded PostgreSQL when available:
`pip install -e ".[dev,pgtest]"`. Without `pgserver` the PostgreSQL variants are skipped.

## Simulation engine (synthetic flight data)

> **Everything here is synthetic (RULE-04).** The aircraft is fictional ("generic twin-jet"), the
> numbers and thresholds are illustrative, and the simulated clock starts on a future date
> (2030-01-01) so it can never be mistaken for real data.

```bash
aeris sim scenarios        # list the built-in scenarios
aeris sim seed             # create one demo session per scenario (idempotent; --force to repeat)
aeris sim list
aeris sim delete <id>
```

| Scenario | What happens | Alerts raised |
| -------- | ------------ | ------------- |
| `nominal_short_haul` | taxi → takeoff → climb → cruise → descent → approach → landing | none |
| `takeoff_config_discrepancy` | flaps not at the briefed setting during takeoff / initial climb | `TAKEOFF_CONFIG` (critical), t=150→230 s |
| `unstable_approach` | high sink rate and low speed on short final | `SINK_RATE` (critical), `SPEED_LOW` (caution) |

- **Deterministic.** Keyframes are interpolated and small *seeded* noise is added, so the same
  `(scenario, seed)` always gives identical data (reproducible tests and sessions).
- **One snapshot per 5 simulated seconds**: altitude, airspeed, vertical speed, heading, flaps,
  gear, N1, fuel and phase.
- **Alerts are rules over the data** (`sim/alerts.py`), debounced over two samples, stored as
  intervals `[t_start, t_end)`; `t_end = null` means still active at the end of the data.
  Levels map to the UI palette: caution = yellow, warning = orange, critical = red.
- **A session is created atomically** (all snapshots, alerts and checklist items, or nothing) and
  capped by `MAX_SIM_SESSIONS` (default 50) because creation is unauthenticated.

### Checklists (review tracking)
Three **generic training** checklists (departure, approach, debrief). Statuses are `not_reviewed`,
`reviewed`, `needs_attention` and describe *review progress inside AERIS only* (RULE-07). Items are
deliberately worded "Review …" / "Note …", never as procedures to perform, and a test enforces
that wording so it cannot drift.

### Simulation API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/sim/scenarios` | built-in synthetic scenarios (no DB needed) |
| POST | `/api/sim/sessions` | create a session `{scenario_id, seed?, name?}` → 201 |
| GET | `/api/sim/sessions` · `/{id}` | list / detail (newest first) |
| DELETE | `/api/sim/sessions/{id}` | delete a session and everything in it → 204 |
| GET | `/api/sim/sessions/{id}/state?t=` | simulated state, latest or as of simulated time `t` |
| GET | `/api/sim/sessions/{id}/timeline?step=` | downsampled series + alert intervals (for charts) |
| GET | `/api/sim/sessions/{id}/alerts?t=` | alerts raised up to `t`, each with `active` at `t` |
| GET | `/api/sim/sessions/{id}/checklists` | checklist review progress |
| PATCH | `/api/sim/sessions/{id}/checklists/items/{item_id}` | record a review status `{status, note?}` |

Simulated state is **read-only**. The only write besides creating/deleting a whole session is a
checklist *review status* (RULE-08).

**Every response says what it is (RULE-04).** `synthetic: true`, `data_source: "synthetic
simulation (not live telemetry)"` and the safety disclaimer are on every top-level response.

**State responses disclose freshness (RULE-05).** Each carries `session_id`, `snapshot_time`
(simulated UTC), `generated_at` (real UTC), and:

| `freshness` | Meaning |
| ----------- | ------- |
| `latest` | no `t` given: the final snapshot of the scenario |
| `exact` | a sample exists at exactly `t` |
| `held` | no sample at `t`; the previous one is shown with `age_s` and a warning |
| `stale` | `t` is past the end of the simulation; the final snapshot is shown with a warning |
| `absent` | no snapshot exists; `state` is `null` (nothing is invented) |

**Isolation (RULE-06 / BR-07).** Every query filters on `session_id`. A checklist item that
belongs to another session answers `404 item_not_found`, exactly like an item that does not
exist, so ids cannot be probed across sessions. Tests attack this directly.

Errors are typed: `session_not_found` / `item_not_found` (404), `unknown_scenario` /
`invalid_status` (422), `session_limit_reached` (409), `database_unavailable` (503).

> **No authentication yet.** Anyone who can reach the API can create sessions and record
> reviews. Fine for local learning use; add auth before exposing it (see roadmap).

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
    db/              # SQLAlchemy models, UTC type, engine/session management
    sim/             # scenarios, generator, alert rules, checklists, session service
    cli.py           # `aeris` command
    main.py          # app factory
  eval/questions.jsonl   # retrieval eval set
  tests/
```

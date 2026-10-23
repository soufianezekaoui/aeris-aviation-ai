# Development Roadmap

## Delivery phases
Work is delivered in four phases, each as four reviewable commits.

| Phase | Scope | Milestones | Status |
| ----- | ----- | ---------- | ------ |
| 1 | RAG over PDF reports: extraction, chunking, embeddings, retrieval, citations, web UI | 1, 2, 4 (UI part) | **implemented, awaiting your validation** |
| 2 | Flight-data simulation + checklist tracking (PostgreSQL) | 3, 4 (simulation panel) | planned |
| 3 | Agent tools / orchestration (LangGraph) | 5 | planned |
| 4 | Voice + AWS Lambda | 6, 7 | planned |

Phase 1 exit criteria: run `aeris ingest` and `aeris eval --sweep` with the real embedding model,
choose `MIN_RELEVANCE` from the sweep, and confirm answers with a live LLM key.

## Milestone 1 — Foundation
- [x] Finalize scope and repository documentation.
- [x] Add a concise `.gitignore` and `.env.example`.
- [x] Create backend skeleton and local development instructions.

## Milestone 2 — First vertical slice
- [x] Health endpoint.
- [x] Load a small, curated set of aviation documents.
- [x] Parse, chunk, embed, and index documents.
- [x] Ask a question and return an answer with source references.
- [x] Add tests for no relevant retrieval and model/provider errors.

## Milestone 3 — Simulation data
- [ ] Define simulation session and state snapshot models.
- [ ] Seed clearly labeled synthetic data.
- [ ] Expose read-only state and warning endpoints.
- [ ] Add checklist review tracking and session-isolation tests.

## Milestone 4 — UI
- [x] Create a simple React chat page.
- [x] Show citations and evidence snippets.
- [ ] Show a simulation panel with timestamps and warnings. *(Phase 2)*
- [x] Clearly label all data as simulated.

## Milestone 5 — Agent orchestration
- [ ] Add explicit intent routing.
- [ ] Add narrowly scoped tools.
- [ ] Test tool selection, grounding, and failure handling.
- [ ] Add human confirmation for any future state-changing simulation action.

## Milestone 6 — Voice
- [ ] Add speech-to-text.
- [ ] Add text-to-speech.
- [ ] Test transcription errors and clear uncertainty in responses.

## Milestone 7 — AWS and quality
- [ ] Evaluate Lambda/API Gateway suitability.
- [ ] Configure secrets, logs, metrics, and cost monitoring.
- [ ] Add CI tests and deployment workflow.
- [ ] Evaluate retrieval quality, citation correctness, latency, and failure cases.

## Phase 1 follow-ups (evaluate against `eval/questions.jsonl` before adopting)
- [ ] Record real-embedding results of `aeris eval --sweep` and set `MIN_RELEVANCE`.
- [ ] Grow the eval set (more reports, multi-hop and numeric questions).
- [ ] Try hybrid (BM25 + vector) search: proper nouns, registrations and figures favour lexical match.
- [ ] Try contextual chunk headers (title + section prepended before embedding) and re-ranking.
- [ ] Compare `pdfminer.six` / `pdftotext` extraction if misses trace back to split words.
- [ ] Multi-turn conversation memory.

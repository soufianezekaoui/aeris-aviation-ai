# Technology Decisions

These are initial decisions, not irreversible commitments. Revisit them after a minimal prototype.

## TD-01 — Python backend
**Proposal:** Python with FastAPI.

**Reason:** Python has a broad ecosystem for document parsing, embeddings, LLM integration, and evaluation; FastAPI provides typed request/response models and generated API docs.

**Validation:** create one health endpoint and one question endpoint; test local execution and packaging.

**Status (Phase 1): validated locally.** `/health`, `/api/documents`, `/api/ask` run under uvicorn; 43 unit tests plus opt-in tests on the real reports. Packaging for Lambda is still untested (Phase 4).

## TD-02 — PostgreSQL and pgvector
**Proposal:** use PostgreSQL for simulation/checklist records and evaluate pgvector for vector retrieval.

**Reason:** a single database can reduce initial operational complexity.

**Validation:** benchmark retrieval on the intended document set and confirm metadata filtering and backup needs. Use a separate vector store only if requirements justify it.

**Update (Phase 1): Chroma for now, pgvector deferred.** Phase 1 needs no relational data, so running PostgreSQL just to store vectors would add setup friction for no benefit. Chroma (local, persistent, cosine, metadata filters) is used and **isolated in `rag/store.py`**, so swapping is a one-module change. Revisit when PostgreSQL arrives in Phase 2: compare pgvector against the same `eval/questions.jsonl` set before deciding. The index records its embedding model and refuses mismatched queries.

## TD-03 — React + TypeScript
**Proposal:** React with TypeScript for the UI.

**Reason:** component-based UI and typed API contracts.

**Validation:** build a minimal chat screen showing answer text and source references.

**Update (Phase 1):** Vite + React 18 + TypeScript + **Tailwind CSS v3**; design tokens live in `tailwind.config.js` (see `frontend/README.md`). Validated: builds, type-checks, citation parser unit-tested, UI checked in a headless browser against the real API.

## TD-04 — RAG implementation
**Proposal:** start with a transparent, small retrieval pipeline; choose LangChain, LlamaIndex, or direct SDKs only after the pipeline requirements are clear.

**Reason:** the project should demonstrate understanding of extraction, chunking, embeddings, retrieval, prompt construction, and evaluation—not hide all logic behind a framework.

**Decision (Phase 1): LangChain for components, own code for the parts that matter.** LangChain supplies the text splitter, the `Embeddings` interface, the Chroma integration, and the `prompt | model | parser` chain. The PDF cleaning, citation verification, relevance gate, failure handling and evaluation are our own, tested code. Providers (Anthropic/OpenAI; fastembed/OpenAI embeddings) are swappable by configuration. LlamaIndex was not evaluated.

## TD-05 — Agent orchestration
**Proposal:** begin with explicit routing and a small set of read-oriented tools. Evaluate LangGraph when branching, state, retries, and human review justify it.

**Reason:** a fully agentic design is unnecessary for every request and can increase cost and unpredictability.

**Plan:** LangGraph is introduced in Phase 3, not before. Phase 1 deliberately has no agent.

## TD-06 — AWS deployment
**Proposal:** evaluate AWS Lambda + API Gateway after the local vertical slice works.

**Reason:** Lambda may suit short API calls, but ingestion, large dependencies, long-running tasks, and model hosting may require different execution patterns.

## TD-07 — Secrets and configuration
**Proposal:** read credentials from environment configuration locally and use a managed secrets solution in deployment. Commit only a `.env.example` with placeholders.

## TD-08 — Safety boundary
**Proposal:** simulation and educational use only; no live aircraft integration or operational control.

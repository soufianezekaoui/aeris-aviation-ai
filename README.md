# AERIS — Aviation Intelligence & Retrieval System

AERIS is an educational aviation assistant that answers questions about **accident investigation
reports** using **retrieval-augmented generation (RAG)**: every answer is tied to the exact report
passages it came from, and the system says so when the evidence isn't there. Later phases add
simulated flight data, checklist tracking, agent tools, voice and cloud deployment.

> [!WARNING]
> **Safety boundary:** AERIS is a research and simulation project, not a certified aviation system.
> It must not be used to operate an aircraft, replace approved checklists or flight manuals, diagnose
> live aircraft faults, or make real-world flight decisions.

**Status:** Phase 1 (RAG over PDF reports) is implemented and tested. Phases 2–4 are planned.

## What it does today (Phase 1)
Illustrative layout (placeholder values, not real output):
```
Q: Did the crew consider diverting to Doha?
A: <generated answer with inline [1] [2] markers>      status: answered · citations verified
   [1] ups_6 · PDF p.159 · §1.x …  "<exact passage>"   relevance 0.62   cited
   [2] ups_6 · PDF p.160 · …                                           retrieved, not cited
```
- **Ingests PDFs** with a manifest of provenance; cleans running headers, page numbers, tables of
  contents and hyphenation; chunks per page with section headings.
- **Retrieves** with embeddings in a local vector database (Chroma).
- **Answers with verified citations**: invented `[n]` markers are stripped; answers with no valid
  citation are flagged *unverified*; with no relevant evidence the LLM is not called at all.
- **Runs without an API key** in retrieval-only mode (cited passages, no generated text).
- **Web UI** (React + TypeScript + Tailwind) in a safety-signage palette.
- **Measures itself**: `aeris eval --sweep` scores retrieval and refusal across thresholds.

## Quick start
Requirements: Python 3.11+, Node 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,local-embeddings,anthropic]"          # or ,openai
cp ../.env.example ../.env                                  # set LLM_PROVIDER / LLM_API_KEY (optional)
aeris ingest --reset                                        # first run downloads the embedding model
aeris eval --sweep                                          # calibrate MIN_RELEVANCE (see backend README)
uvicorn aeris.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                                                 # http://localhost:5173
```
No key or model download handy? Try the pipeline offline with lexical test embeddings:
`EMBEDDING_PROVIDER=hash aeris ingest --reset` (not semantic: for smoke tests only).

## Delivery phases
| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 | RAG over PDF reports: extraction, chunking, embeddings, retrieval, citations, UI | ✅ implemented |
| 2 | Flight-data simulation + checklist tracking (PostgreSQL) | planned |
| 3 | Agent tools and orchestration (LangGraph) | planned |
| 4 | Voice and AWS Lambda | planned |

Details and open follow-ups: [`docs/roadmap.md`](docs/roadmap.md).

## Stack
| Layer | Technology |
| ----- | ---------- |
| API | Python 3.11, FastAPI, Pydantic |
| RAG | LangChain (splitters, embeddings interface, chain), own cleaning / citation / eval code |
| Vector DB | Chroma (Phase 1) — pgvector to be evaluated in Phase 2 ([TD-02](docs/technology-decisions.md)) |
| Embeddings | fastembed (local ONNX, default) · OpenAI · offline hashing (tests) |
| LLM | Anthropic or OpenAI via configuration; optional |
| PDF | pypdf (BSD-licensed; chosen over PyMuPDF to keep this MIT project licence-clean) |
| UI | React 18, TypeScript, Tailwind CSS, Vite |
| Later | LangGraph (Phase 3), PostgreSQL (Phase 2), AWS Lambda + API Gateway (Phase 4) |

## Repository layout
```
backend/     FastAPI service, ingestion + RAG, CLI, tests, eval set      → backend/README.md
frontend/    React + TypeScript + Tailwind UI and design system           → frontend/README.md
knowledge/   documents/manifest.json (provenance) and raw/ PDF reports
docs/        requirements, business rules, architecture, decisions, roadmap
```

## Data sources
Two public investigation reports are bundled in `knowledge/documents/raw/`, with provenance in
[`manifest.json`](knowledge/documents/manifest.json):
- **Spanair Flight 5022** — Report A-032/2008, CIAIAC (Spain), Madrid-Barajas, 20 Aug 2008.
- **UPS Flight 6** — AAIS Case 13/2010, GCAA (UAE), Dubai, 3 Sep 2010.

Their `url` / `published` fields are intentionally `null` until verified. Check each publisher's
reuse terms before redistributing the PDFs or adding more. All future simulation data and
checklists will be **synthetic and generic**, never real manufacturer procedures.

## Limitations
- LLM answers can be wrong. Citations let you verify them; they don't guarantee correctness.
- Text only: figures, scans and most tables are not understood. Page numbers are **PDF page indices**.
- `MIN_RELEVANCE` is an **uncalibrated default** until you run the eval with your embedding model.
- Live LLM and real-embedding paths are covered by fakes in automated tests; verify them once locally.
- Single-turn Q&A; no conversation memory yet.

## Documentation
- [Backend](backend/README.md) · [Frontend](frontend/README.md)
- [Business requirements](docs/business-requirements.md) · [Business rules](docs/business-rules.md)
- [Architecture](docs/architecture.md) · [Technology decisions](docs/technology-decisions.md) · [Roadmap](docs/roadmap.md)

## Development
```bash
cd backend  && ruff check src tests && pytest          # add: pytest -m slow  for the real reports
cd frontend && npm run build && npm test
```
Contributions are not open yet; this is a learning and portfolio project.

## License
MIT. See [LICENSE](https://github.com/soufianezekaoui/aeris-aviation-ai/blob/main/LICENSE).

## 👨‍💻 Author

**Soufiane ZEKAOUI**
- GitHub: [@soufianezekaoui](https://github.com/soufianezekaoui)
- LinkedIn: [Soufiane Zekaoui](https://linkedin.com/in/soufiane-zekaoui-445b1b352/)
- Portfolio: [My_Personal_Website.com](https://soufianezekaoui.github.io/my_soufianeze_portfolio/)

<div align="center">

### ⭐ Star this repo if you found it helpful!

**Made with ❤️ and RAG_Agentic**

</div>

# Development Roadmap

## Milestone 1 — Foundation
- [ ] Finalize scope and repository documentation.
- [ ] Add a concise `.gitignore` and `.env.example`.
- [ ] Create backend skeleton and local development instructions.

## Milestone 2 — First vertical slice
- [ ] Health endpoint.
- [ ] Load a small, curated set of aviation documents.
- [ ] Parse, chunk, embed, and index documents.
- [ ] Ask a question and return an answer with source references.
- [ ] Add tests for no relevant retrieval and model/provider errors.

## Milestone 3 — Simulation data
- [ ] Define simulation session and state snapshot models.
- [ ] Seed clearly labeled synthetic data.
- [ ] Expose read-only state and warning endpoints.
- [ ] Add checklist review tracking and session-isolation tests.

## Milestone 4 — UI
- [ ] Create a simple React chat page.
- [ ] Show citations and evidence snippets.
- [ ] Show a simulation panel with timestamps and warnings.
- [ ] Clearly label all data as simulated.

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

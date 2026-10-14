# Business Requirements

## 1. Problem
Aviation learning material is spread across documents, while simulation state and checklist progress are separate types of information. A learner needs a single interface to ask questions, inspect supporting sources, and review a simulated scenario without confusing generated explanations with authoritative procedures.

## 2. Product objective
Build AERIS as a source-grounded aviation learning and simulation assistant. It combines RAG over curated documents with read-only access to structured simulation data.

## 3. Users
- **Learner / researcher:** asks aviation questions and studies investigation reports.
- **Simulation participant:** views scenario state, warnings, and checklist-review progress.
- **Maintainer:** adds documents, manages scenarios, and evaluates answer quality.

## 4. MVP requirements
- **BR-01 Knowledge Q&A:** accept a text question and return an answer based on retrieved documents where possible.
- **BR-02 Source transparency:** show source title and relevant passage/reference for claims supported by retrieved material.
- **BR-03 Uncertainty:** say when evidence is missing, conflicting, or insufficient instead of inventing facts.
- **BR-04 Accident research:** support questions about curated historical accident reports and distinguish documented findings from interpretation.
- **BR-05 Simulation state:** retrieve explicitly simulated values such as altitude, airspeed, timestamp, and scenario warnings from structured storage.
- **BR-06 Checklist tracking:** display checklist items and record review status within a simulation session; review status does not prove a real-world action occurred.
- **BR-07 Session separation:** do not mix data from different simulation sessions.
- **BR-08 Safety:** clearly label all simulated data and training content; do not present AERIS as an operational flight tool.
- **BR-09 Evaluation:** maintain test questions and expected source references to evaluate retrieval and response quality.
- **BR-10 API:** expose the MVP functions through a documented backend API.

## 5. Later requirements
- Voice input and spoken responses.
- Interactive scenario timeline and visual dashboard.
- Authentication and role-based access if multi-user administration is needed.
- AWS deployment, monitoring, and automated tests in CI.

## 6. Non-functional requirements
- **Traceability:** answers should identify supporting documents when available.
- **Reliability:** failures in retrieval, database access, or the model must be handled explicitly.
- **Security:** secrets stay outside source control; validate inputs and restrict tool permissions.
- **Maintainability:** keep domain rules separate from provider/framework-specific code.
- **Cost awareness:** track model and embedding usage; avoid unnecessary agent/tool calls.
- **Latency:** measure end-to-end response time before optimizing.

## 7. Acceptance criteria for the first vertical slice
1. A user can ask a question against a small curated document set.
2. The response includes source references or clearly states that evidence was not found.
3. A user can retrieve a simulated session's latest state with its timestamp.
4. A user can view checklist review progress for that session.
5. Automated tests cover missing sources, missing session, and session separation.
6. The UI and API label the environment as simulation/education only.

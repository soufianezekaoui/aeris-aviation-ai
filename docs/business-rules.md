# Business Rules

- **RULE-01 — Source-grounded answers:** for document questions, retrieve evidence before generating an answer.
- **RULE-02 — No fabricated evidence:** never invent source titles, quotations, document identifiers, or citations.
- **RULE-03 — Uncertain or absent evidence:** clearly say when retrieved evidence is insufficient; ask a clarifying question where useful.
- **RULE-04 — Simulation is explicit:** all aircraft state values and warnings in the MVP come from simulation data, never implied live telemetry.
- **RULE-05 — Freshness:** every state response includes the simulation session identifier and snapshot timestamp; stale or absent state is disclosed.
- **RULE-06 — Session isolation:** state, events, and checklist progress must be scoped to a single simulation session.
- **RULE-07 — Checklist semantics:** statuses describe review progress in the application only; they do not certify that a real-world procedure was performed.
- **RULE-08 — No autonomous operational control:** the assistant cannot issue aircraft-control commands or change a simulated state unless a specific, validated simulation use case permits it.
- **RULE-09 — Safety boundary:** AERIS is not a substitute for approved aircraft manuals, checklists, instructors, or certified systems.
- **RULE-10 — Historical accuracy:** accident explanations should prioritize original investigation reports and distinguish official findings from hypotheses or secondary commentary.
- **RULE-11 — Data provenance:** retain source metadata such as title, publisher/author, URL or file reference, publication date where known, and ingestion date.
- **RULE-12 — Secret management:** API keys and credentials must not be committed to Git.

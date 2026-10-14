# AERIS — Aviation Intelligence & Retrieval System

AERIS is an educational aviation-simulation assistant that combines retrieval-augmented generation (RAG), simulated aircraft data, checklist tracking, and a conversational interface. It is designed to help users explore aviation information and training scenarios using traceable sources.

> **Safety boundary:** AERIS is a research and simulation project, not a certified aviation system. It must not be used to operate an aircraft, replace approved checklists or flight manuals, diagnose live aircraft faults, or make real-world flight decisions.

## Goals
- Answer aviation knowledge questions using retrieved source material.
- Explain historical accident investigations with citations to source documents.
- Query structured, explicitly simulated flight-state data.
- Track checklist review progress inside a simulation session.
- Provide a foundation for later voice interaction and cloud deployment.

## Initial scope
**In scope:** document ingestion, retrieval, source-grounded responses, simulation records, checklist progress, API, and a simple web UI.

**Out of scope for the initial version:** live aircraft connectivity, flight-control commands, operational advice for real emergencies, certified procedures, and autonomous actions affecting aircraft.

## Architecture
See [`docs/architecture.md`](docs/architecture.md) for the system diagram and component responsibilities.

## Documentation
- [Business requirements](docs/business-requirements.md)
- [Business rules](docs/business-rules.md)
- [Architecture](docs/architecture.md)
- [Technology decisions](docs/technology-decisions.md)
- [Roadmap](docs/roadmap.md)

## Planned stack (provisional)
- Python + FastAPI for the API and AI backend
- PostgreSQL for structured simulation and checklist data
- pgvector for vector search (subject to validation)
- React + TypeScript for the web UI
- AWS Lambda + API Gateway for deployment, after validating runtime limits and dependencies

The stack is provisional until a minimal end-to-end prototype validates the choices.

## Getting started
Implementation instructions will be added when the initial backend is created.

## License
MIT. See [LICENSE](https://github.com/soufianezekaoui/aeris-aviation-ai/blob/main/LICENSE).

## 👨‍💻 Author

**Soufiane ZEKAOUI**
- GitHub: [@soufianezekaoui](https://github.com/soufianezekaoui)
- LinkedIn: [Soufiane Zekaoui](https://linkedin.com/in/soufiane-zekaoui-445b1b352/)
- Portfolio: [My_Personal_Website.com](https://soufianezekaoui.github.io/my_soufianeze_portfolio/)

Built for freeCodeCamp Data Analysis with Python Certification

<div align="center">

### ⭐ Star this repo if you found it helpful!

**Made with ❤️ and RAG_Agentic**

</div>

# AERIS Frontend

React 18 + **TypeScript** + **Tailwind CSS** (Vite). A single-page client for the AERIS RAG API:
ask a question, read the answer, and inspect the evidence behind every claim.

> **Safety boundary:** education / simulation only. A yellow caution banner is always visible.

## Requirements
- Node.js 18+
- The backend running on `http://localhost:8000` (see [`../backend/README.md`](../backend/README.md))

## Run
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api and /health to :8000)
```

| Script              | Purpose                                   |
| ------------------- | ----------------------------------------- |
| `npm run dev`       | dev server with API proxy                 |
| `npm run build`     | type-check (`tsc`) then production build  |
| `npm run typecheck` | type-check only                           |
| `npm test`          | unit tests (Vitest)                       |

### Configuration
| Variable            | Default                 | Purpose |
| ------------------- | ----------------------- | ------- |
| `VITE_API_PROXY`    | `http://localhost:8000` | dev-server proxy target |
| `VITE_API_BASE_URL` | *(empty, same origin)*  | absolute API URL for a deployed build |

## What the UI shows
- **Answer** with a status badge (`answered`, `insufficient evidence`, `evidence only`,
  `unverified`, `generation failed`) and clickable `[n]` citation chips that scroll to and
  highlight the matching source.
- **Evidence cards** for every retrieved passage: report, publisher, reference, **PDF page**,
  section, relevance score, and whether the answer *cited* it. Uncited passages are dimmed
  and labelled "retrieved, not cited": nothing is hidden.
- **Source library** panel with provenance and indexed passage counts.
- **System alerts** for API failures with the exact command that fixes them.
- Answer text is rendered as plain text (never as HTML), so retrieved content cannot inject markup.

## Design system
Safety-signage palette on a dark industrial canvas, following the **60-30-10** rule.

| Role | Colour | Token | Use |
| ---- | ------ | ----- | --- |
| 60 % canvas | Navy `#0A101C` / `#060A12` | `navy-900/950` | page, header, form |
| 30 % surfaces | White `#FFFFFF`, light gray `#F3F4F6` | `paper` | answer + evidence "document sheets", body text on navy |
| 10 % primary action / highlight | **Safety Orange** `#FF6A13` | `safety-orange` | main button, citation chips, cited-source edge |
| 10 % caution | **Safety Yellow** `#FFC72C` | `safety-yellow` | simulation banner, insufficient / unverified states, focus ring |
| 10 % danger | **Safety Red** `#E5322D` | `safety-red` | errors and failures |

Choices that follow from measured WCAG contrast (not taste):
- **White on orange is only 2.9:1**, so orange fills always carry *navy* text (6.9:1).
- Red as small text on navy is 4.4:1, so text uses a lighter `safety-red-text` (7.5:1) and white-text
  fills use a deeper `safety-red-fill` (5.5:1). `safety-red` itself is for icons and borders.
- Bright colours only appear against dark surfaces or as small accents, per the brief.

**Visual elements**
- *Icons:* inline ANSI Z535-style signal icons (`SafetyIcon`: caution, warning, danger, notice).
- *Texture:* a CSS blueprint grid and a yellow/black hazard stripe. No image or font is fetched,
  so the UI works offline and has no third-party requests.
- *Adaptation of the brief:* the palette reference was written for mining, but AERIS is aviation, so
  no mining imagery is used. A muted, `prefers-reduced-motion`-aware looping background (e.g.
  runway or flight-deck footage) is a possible later addition behind the content layer; it is
  intentionally **not** in Phase 1 to keep the evidence the focus.
- *Accessibility:* visible focus ring, `aria-live` answer region, labelled controls, reduced-motion support.

## Structure
```
frontend/
  src/
    api.ts               # typed fetch client, ApiError with backend error codes
    types.ts             # mirrors backend/src/aeris/schemas.py
    lib/citations.ts     # splits "[1][2, 3]" markers out of answer text (+ tests)
    components/          # Header, SimulationBanner, QuestionForm, AnswerPanel,
                         # SourceCard, DocumentsPanel, ErrorPanel, SafetyIcon
    App.tsx              # state, request cancellation, citation navigation
  tailwind.config.js     # palette tokens
```

## Known limitations
- Single-turn Q&A only (no conversation history yet).
- No frontend component tests yet; only the citation parser is unit-tested. The UI was checked
  manually in a headless browser (desktop + mobile) against the real API.
- Keep `src/types.ts` in sync with the backend schemas by hand (no code generation yet).

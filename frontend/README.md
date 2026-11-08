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

| Script              | Purpose                                  |
| ------------------- | ---------------------------------------- |
| `npm run dev`       | dev server with API proxy                |
| `npm run build`     | type-check (`tsc`) then production build |
| `npm run typecheck` | type-check only                          |
| `npm test`          | unit tests (Vitest)                      |

### Configuration

| Variable            | Default                 | Purpose                               |
| ------------------- | ----------------------- | ------------------------------------- |
| `VITE_API_PROXY`    | `http://localhost:8000` | dev-server proxy target               |
| `VITE_API_BASE_URL` | _(empty, same origin)_  | absolute API URL for a deployed build |

## What the UI shows

The app has two tabs: **Reports Q&A** (Phase 1) and **Simulation** (Phase 2).

### Simulation tab

- **Sessions.** Start a synthetic session from one of three scenarios, switch between sessions,
  or delete one. A persistent badge reads _Simulated data · not live telemetry_.
- **Time controls.** A slider, Play/Pause and a speed selector move a **client-side cursor** over
  already-generated data. Nothing about the simulation changes; state is fetched per cursor
  position (debounced, and superseded requests are cancelled).
- **Simulated state.** Altitude, airspeed, vertical speed, heading, flaps, gear, N1, fuel and
  phase, always shown with the session id, the snapshot time on the _simulated clock_
  (`T+00:02:40 · 2030-01-01 08:02:40 UTC`) and a freshness badge. A held or stale sample, or a
  missing snapshot, is stated in words and never presented as current (RULE-05).
- **Timeline chart.** Altitude and airspeed as plain SVG, phase boundaries, alert intervals shaded
  by level, and a cursor; click the chart to seek.
- **Alerts.** Caution (yellow), warning (orange) and critical (red), each with an ANSI-style icon
  **and a text label**, so colour is never the only signal. Active alerts come from the server's
  state response; earlier ones are listed separately and marked _cleared_.
- **Checklist review.** Three generic training checklists. Each item is _Not reviewed /
  Reviewed / Needs attention_ with an optional note. A permanent notice states that this is
  review progress inside AERIS only and does not certify any real-world action (RULE-07).
  Sessions are independent: progress in one never appears in another (RULE-06).

### Reports tab

- **Answer** with a status badge (`answered`, `insufficient evidence`, `evidence only`,
  `unverified`, `generation failed`) and clickable `[n]` citation chips that scroll to and
  highlight the matching source.
- **Evidence cards** for every retrieved passage: report, publisher, reference, **PDF page**,
  section, relevance score, and whether the answer _cited_ it. Uncited passages are dimmed
  and labelled "retrieved, not cited": nothing is hidden.
- **Source library** panel with provenance and indexed passage counts.
- **System alerts** for API failures with the exact command that fixes them.
- Answer text is rendered as plain text (never as HTML), so retrieved content cannot inject markup.

## Design system

Safety-signage palette on a dark industrial canvas, following the **60-30-10** rule.

| Role                            | Colour                                | Token           | Use                                                             |
| ------------------------------- | ------------------------------------- | --------------- | --------------------------------------------------------------- |
| 60 % canvas                     | Navy `#0A101C` / `#060A12`            | `navy-900/950`  | page, header, form                                              |
| 30 % surfaces                   | White `#FFFFFF`, light gray `#F3F4F6` | `paper`         | answer + evidence "document sheets", body text on navy          |
| 10 % primary action / highlight | **Safety Orange** `#FF6A13`           | `safety-orange` | main button, citation chips, cited-source edge                  |
| 10 % caution                    | **Safety Yellow** `#FFC72C`           | `safety-yellow` | simulation banner, insufficient / unverified states, focus ring |
| 10 % danger                     | **Safety Red** `#E5322D`              | `safety-red`    | errors and failures                                             |

Choices that follow from measured WCAG contrast (not taste):

- **White on orange is only 2.9:1**, so orange fills always carry _navy_ text (6.9:1).
- Red as small text on navy is 4.4:1, so text uses a lighter `safety-red-text` (7.5:1) and white-text
  fills use a deeper `safety-red-fill` (5.5:1). `safety-red` itself is for icons and borders.
- Bright colours only appear against dark surfaces or as small accents, per the brief.

**Visual elements**

- _Icons:_ inline ANSI Z535-style signal icons (`SafetyIcon`: caution, warning, danger, notice).
- _Texture:_ a CSS blueprint grid and a yellow/black hazard stripe. No image or font is fetched,
  so the UI works offline and has no third-party requests.
- _Adaptation of the brief:_ the palette reference was written for mining, but AERIS is aviation, so
  no mining imagery is used. A muted, `prefers-reduced-motion`-aware looping background (e.g.
  runway or flight-deck footage) is a possible later addition behind the content layer; it is
  intentionally **not** in Phase 1 to keep the evidence the focus.
- _Accessibility:_ visible focus ring, `aria-live` answer region, labelled controls, reduced-motion support.

## Structure

```
frontend/
  src/
    api.ts               # typed fetch client, ApiError with backend error codes
    types.ts             # mirrors backend/src/aeris/schemas.py
    lib/citations.ts     # splits "[1][2, 3]" markers out of answer text (+ tests)
    lib/simtime.ts       # simulated-clock formatting, chart scaling / seeking (+ tests)
    components/          # Reports: QuestionForm, AnswerPanel, SourceCard, DocumentsPanel, ReportsView
                         # Simulation: SimulationView, SessionPicker, TimeControls, StatePanel,
                         #   TimelineChart, AlertList, ChecklistPanel
                         # Shared: Header, SimulationBanner, ErrorPanel, SafetyIcon
    App.tsx              # state, request cancellation, citation navigation
  tailwind.config.js     # palette tokens
```

## Known limitations

- Single-turn Q&A only (no conversation history yet).
- Tests cover the pure helpers and the safety-bearing components (alert labelling, freshness
  disclosure, review semantics). The full flows were checked manually in headless Chromium
  (desktop + mobile) against the real API; there are no automated end-to-end tests yet.
- The simulation tab fetches state per cursor position. Fine for local use; streaming would suit a
  deployed multi-user version better.
- Icons use an `inverted` variant on same-coloured backgrounds (caution icon in a yellow box).
- Keep `src/types.ts` in sync with the backend schemas by hand (no code generation yet).

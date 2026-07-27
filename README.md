# VisionQA — Autonomous AI QA Engineer

VisionQA takes a URL (and a login if the app requires one) and autonomously
explores the entire application the way a human QA engineer would: clicking
through every nav item, tab, dropdown, card, and button it can find, testing
each discovered page across four screen sizes, filling in forms, running a
real WCAG accessibility audit, measuring performance, and producing a single
prioritized bug report with screenshots. You only click **Start Scan** — it
decides what to explore.

**Stack:** React 18 + TypeScript (Vite) · FastAPI (Python 3.14) · MongoDB · Playwright

---

## Quick Start

### 1. MongoDB
```bash
docker compose up -d mongodb
```
(Or point `MONGODB_URL` in `.env` at any MongoDB instance — a local
`mongod` works fine for development.)

### 2. Backend
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
uvicorn app.main:app --reload --reload-dir app --port 8000 --loop app.loop_factory:event_loop_factory
```

> **Windows + Playwright:** Use the `--loop app.loop_factory:event_loop_factory`
> flag shown above. It keeps a `ProactorEventLoop` even under `--reload`, which
> Playwright needs to spawn its browser driver. Without it, scans fail with
> `NotImplementedError`. As a fallback, the API will still run the scan in a
> child process if it detects a non-Proactor loop.

### 3. Frontend
```bash
npm install
npm run dev
```

App: http://localhost:5173 · API docs: http://localhost:8000/docs

---

## Architecture

```
backend/app/
  main.py               FastAPI app + CORS + lifespan (Mongo connect/disconnect)
  core/
    config.py            All settings (pydantic-settings, reads .env)
    security.py           Password hashing (bcrypt) + JWT issuing/decoding
    crypto.py              Fernet symmetric encryption (saved login sessions at rest)
    logging.py              Structured logging setup
    enums.py                  ScanStatus, BugSeverity, BugStatus, TeamRole, etc.
  db/mongodb.py          Motor client + Beanie ODM initialization
  models/                Beanie MongoDB documents (see "Data Model" below)
  schemas/                Pydantic request/response models (API contracts)
  services/                Business logic — one service per domain, called by API routes
    ai/provider.py          Pluggable AI provider abstraction (OpenAI/Ollama/fallback)
  api/v1/                 FastAPI routers — thin, delegate to services/
  automation/             The exploration engine (see below) — one independent,
                           reusable module per concern
    vendor/axe.min.js      Vendored axe-core (accessibility rule engine)

src/                     React + TypeScript frontend (single-page, client-state routed)
  app/App.tsx              All screens/components (Dashboard, New Scan, Scan Results, etc.)
  app/components/ui/       shadcn/ui primitives (Radix UI + Tailwind)
  hooks/useVisionQA.ts    React Query hooks — one per API endpoint
  stores/                 Zustand stores (auth session, active scan/bug selection)
  api/                    Fetch wrapper with automatic access-token refresh
  types/                  Shared TypeScript interfaces mirroring the backend schemas
```

---

## The Exploration Engine

This is the core of the product — a set of independent, single-purpose
modules under `backend/app/automation/`, orchestrated by `playwright_runner.py`
for every scan:

| Module | Responsibility |
|---|---|
| `auth_recorder.py` | **Authentication.** Opens a real, visible (headed) Chromium window so the user can log into the target app themselves; captures the resulting session (`storage_state`) and saves it encrypted. Credentials are never seen or stored by VisionQA — only the resulting cookies/localStorage are. |
| `navigation_discovery.py` | **Navigation discovery.** Finds every clickable thing on the current page — semantic `<nav>`/`<a>`/`<button>`/`role="tab"` elements, *and* non-semantic `cursor:pointer` `<div>` rows inside nav-like containers (a very common real-world pattern that plain selectors miss). Flags anything matching a destructive-keyword blocklist (delete/remove/archive/deactivate/…) so it's never clicked. |
| `state_graph.py` | **State/graph tracking.** Every distinct page becomes a node, every click becomes an edge. Node identity is keyed primarily on URL (not on element counts or text, which drift due to animations/widgets and cause false "new page" loops) with an active-tab/open-dialog signal to distinguish same-URL SPA states like tabs and modals. Enforces `has_tried(node, action)` so nothing is ever clicked twice — the actual infinite-loop guard. |
| `crawler_engine.py` | **Crawling.** BFS loop over the graph: visit a node, discover its actionable elements, click each untried non-destructive one, detect where it led, record the edge, return to the node, repeat. Bounded by `CRAWL_MAX_NODES` / `CRAWL_MAX_ACTIONS_PER_NODE` / `CRAWL_MAX_DURATION_SECONDS` — stops gracefully and reports what it found rather than hanging on a huge or combinatorial app. |
| `responsive_engine.py` | **Multi-viewport visual QA.** Replays every discovered node at desktop/laptop/tablet/mobile (`viewports.py`), capturing a screenshot at each size and checking for overlapping elements, off-viewport interactive elements, clipped text, and horizontal overflow. |
| `interaction_engine.py` | **Forms.** Detects every form, generates realistic fake data per field (by input type/name/label heuristics), and fills it via Playwright's native `.fill()`/`.select_option()` (so React-controlled inputs actually register the change). Submission is opt-in only (`Scan.fill_forms`, default `false`) since it creates real data in the target app — filling alone is always safe/reversible. Still blocked by the same destructive-keyword filter regardless. |
| `accessibility_engine.py` | **Accessibility.** Runs the real axe-core ruleset (WCAG 2.1 A/AA + best-practice, ~90 rules) against every page — not just hand-rolled heuristics. |
| `performance_engine.py` | **Performance.** LCP, CLS, and TTFB per page against configurable thresholds. LCP/CLS are captured via a `PerformanceObserver` installed on the browser context *before* any navigation (`context.add_init_script`) — querying them after the fact is unreliable, since Chromium only buffers those entry types for an observer that was listening from page-load start. |
| `bug_detector.py` | **Findings + report shaping.** ~25 `detect_*` methods turning raw page data into severity-rated bug dicts (contrast, missing alt/labels, broken links/images, SEO, mixed content, duplicate IDs, tap targets, slow/duplicate network requests, console errors, …), plus `merge_recurring_bugs` — the same underlying issue found on many pages (e.g. "Missing `<h1>`" on 8 pages) collapses into one entry instead of flooding the report with near-duplicates. |
| `playwright_runner.py` | **Orchestrator.** Launches the browser, loads a saved auth session if the scan has one, runs the crawler, then the responsive/interaction/accessibility/performance engines per node, computes the health score, gets an AI summary, and persists everything. |

**Scan lifecycle:** `New Scan` → `POST /scans` creates a `pending` record and
kicks off `run_scan_background` as a FastAPI background task → the runner
launches Playwright, works through the phases above updating `Scan.progress`/
`current_phase` as it goes → the frontend polls `GET /scans/{id}` (or the
SSE `/scans/{id}/stream` endpoint) to show live progress → on completion,
`ScanDetailResponse` carries the full graph (`nodes`), every screenshot
(`screenshots`, one per node per viewport), and every bug (`bugs`, each
linked to the screenshot of the page it was found on).

---

## Data Model (MongoDB, via Beanie)

| Collection | Purpose |
|---|---|
| `users`, `refresh_tokens`, `user_settings` | Auth + per-user workspace settings |
| `team_members` | Team invites (email-only placeholder, no real invite delivery yet) |
| `projects` | Named groupings of scans against a base URL |
| `auth_profiles` | Encrypted saved login sessions (Fernet, keyed by `AUTH_ENCRYPTION_KEY`) — reused across scans of the same authenticated app |
| `scans` | One per scan run: status/progress, health score, viewport, `fill_forms`/`safe_mode` flags, counts |
| `scan_nodes` | One per discovered page/state: URL, label, parent (graph edge), how it was discovered, LCP/CLS/TTFB |
| `screenshots` | One per node per viewport tested; linked to `scan_nodes` via `node_id` |
| `bugs` | One per finding: severity, component, description, fix suggestion, AI explanation, linked screenshot |
| `scan_logs` | Timestamped log lines shown in the Live Scan console (crawl/forms/a11y/performance/system sources) |

No migrations — Beanie creates indexes on startup from the `Document` classes
in `backend/app/models/`.

---

## API Reference

All routes are under `API_V1_PREFIX` (default `/api/v1`). Full interactive
docs at `/docs` (FastAPI's Swagger UI) once the backend is running.

| Area | Routes |
|---|---|
| Auth | `POST /auth/register`, `/login`, `/refresh`, `/logout`, `GET /auth/me` |
| Login recording | `POST /auth-sessions` (opens a headed browser), `GET /auth-sessions/{id}`, `POST /auth-sessions/{id}/complete`, `DELETE /auth-sessions/{id}` |
| Projects | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}` |
| Scans | `GET/POST /scans`, `GET /scans/{id}`, `GET /scans/{id}/bugs`, `GET /scans/{id}/export` (HTML report), `GET /scans/{id}/stream` (SSE progress), `GET /scans/screenshots/{filename}` |
| Bugs | `GET/PATCH /bugs/{id}` |
| Dashboard | `GET /dashboard` (aggregated stats/trends for the workspace) |
| Team/Settings | `GET/POST /team`, `DELETE /team/{id}`, `GET/PATCH /settings` |
| Placeholders | `GET /billing/plans`, `GET /figma/status` (both stubbed, no real integration yet) |

---

## Environment Variables

Full reference lives in `backend/.env.example`. Grouped by concern:

- **App/server:** `APP_NAME`, `APP_ENV`, `DEBUG`, `API_V1_PREFIX`, `HOST`, `PORT`, `CORS_ORIGINS`, `PUBLIC_BASE_URL`
- **MongoDB:** `MONGODB_URL`, `MONGODB_DB_NAME`
- **JWT:** `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- **Storage:** `STORAGE_PATH`, `SCREENSHOTS_PATH`, `REPORTS_PATH`
- **Playwright:** `PLAYWRIGHT_HEADLESS`, `SCAN_TIMEOUT_MS`
- **Crawler bounds:** `CRAWL_MAX_NODES`, `CRAWL_MAX_ACTIONS_PER_NODE`, `CRAWL_MAX_DURATION_SECONDS`
- **Responsive pass bounds:** `RESPONSIVE_MAX_NODES`, `RESPONSIVE_MAX_DURATION_SECONDS`
- **Form interaction bounds:** `FILL_FORMS_MAX_NODES`, `FILL_FORMS_MAX_DURATION_SECONDS`
- **Accessibility:** `AXE_MAX_NODES`, `AXE_TIMEOUT_MS`
- **Performance thresholds:** `PERF_LCP_WARN_MS`, `PERF_LCP_BAD_MS`, `PERF_CLS_WARN`, `PERF_CLS_BAD`, `PERF_TTFB_WARN_MS`, `PERF_SLOW_REQUEST_MS`
- **Auth session recording:** `AUTH_ENCRYPTION_KEY` (Fernet key — change in production), `AUTH_SESSION_TTL_SECONDS`
- **AI (optional, off by default):** `AI_ENABLED`, `AI_PROVIDER` (`openai`/`ollama`/`anthropic`/`gemini`/`none`), `OPENAI_API_KEY`, `OPENAI_MODEL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` — when disabled, AI summaries/explanations fall back to a template-based `FallbackAIProvider`, no external calls made

---

## Packages

### Backend (`backend/requirements.txt`)

| Package | Used for |
|---|---|
| `fastapi` | Web framework / API routing |
| `uvicorn[standard]` | ASGI server |
| `motor` | Async MongoDB driver |
| `beanie` | MongoDB ODM (document models, indexes) on top of Motor + Pydantic |
| `pydantic`, `pydantic-settings` | Data validation, request/response schemas, `.env`-driven settings |
| `python-jose[cryptography]` | JWT signing/verification |
| `bcrypt` | User password hashing |
| `cryptography` | Fernet symmetric encryption for saved login sessions |
| `python-multipart` | Form/file upload parsing (FastAPI dependency) |
| `email-validator` | Email format validation in Pydantic schemas |
| `playwright` | Browser automation — the entire scan engine runs on this |
| `httpx` | Async HTTP client (AI provider API calls) |
| `sse-starlette` | Server-Sent Events for live scan progress streaming |

Vendored (not a pip package): `backend/app/automation/vendor/axe.min.js` —
[axe-core](https://github.com/dequelabs/axe-core) v4.12.1 by Deque Systems,
MPL-2.0 licensed, fetched via npm and committed directly since it's injected
into scanned pages via Playwright rather than imported as Python code.

### Frontend (`package.json`)

**Framework/build:** `react` 18, `react-dom` 18, `vite` 6, `typescript` 5,
`@vitejs/plugin-react`

**Data/state:** `@tanstack/react-query` (server state, caching, polling),
`zustand` (client state: auth session, active scan/bug selection),
`react-hook-form` (form state where used)

**UI primitives:** `@radix-ui/react-*` (accordion, dialog, dropdown-menu,
popover, select, switch, tabs, tooltip, etc. — unstyled accessible
primitives, styled via Tailwind to form the shadcn/ui component set in
`src/app/components/ui/`), `class-variance-authority`, `clsx`,
`tailwind-merge` (conditional/merged class names), `lucide-react` (icons),
`sonner` (toasts), `vaul` (drawers), `cmdk` (command palette),
`embla-carousel-react`, `react-day-picker`, `react-resizable-panels`,
`react-responsive-masonry`, `react-slick`, `input-otp`

**Styling:** `tailwindcss` 4, `@tailwindcss/vite`, `tw-animate-css`,
`next-themes` (dark/light mode)

**Charts:** `recharts` (dashboard bug-trend/scan-frequency charts)

**Motion:** `motion` (Framer Motion successor — expand/collapse transitions)

**Misc:** `date-fns` (date formatting), `canvas-confetti`, `react-dnd` +
`react-dnd-html5-backend` (drag-and-drop, where used), `react-popper` +
`@popperjs/core` (Radix Popper dependency), `@mui/material` +
`@mui/icons-material` + `@emotion/react` + `@emotion/styled` (present for a
subset of components predating the Radix/shadcn migration)

---

## Known Limitations

- **Headed login recording is local-machine only.** `auth_recorder.py` opens
  a real browser window on whatever machine runs the backend. Fine for local
  dev; if the backend ever moves to a remote/cloud server, there's no window
  for a remote user to see — would need a streamed remote-browser viewer
  (e.g. noVNC or a CDP-based viewer) to work over the network.
- **Health score is a flat additive penalty** (-15/-10/-5/-2 per
  critical/high/medium/low finding, no diminishing returns). Since the
  engine is now thorough (axe-core alone often finds 5-10 real violations
  per page), real sites commonly floor at 0. Worth recalibrating — e.g.
  logarithmic penalty or per-category caps — if you want scores to stay
  meaningfully differentiated between "bad" and "very bad."
- **No z-index/stacking-context detection.** Overlap, off-viewport, and
  clipped-text are checked (`responsive_engine.py`); z-index conflicts
  specifically were scoped out as too heuristic-prone for reliable results
  without heavy false-positive noise.
- **Billing and Figma comparison are stubbed** (`GET /billing/plans`,
  `GET /figma/status`) — UI exists, no real integration behind either yet.
- **Team invites don't send email** — `POST /team` just records an invited
  member; there's no delivery mechanism.

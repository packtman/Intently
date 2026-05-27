# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Intently is a multi-dimensional product analysis platform (Python FastAPI backend + React/Vite frontend + Electron desktop app). The backend runs on port 8000 and the web frontend on port 3000.

### Running Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Backend | `source .venv/bin/activate && python -m uvicorn context_graph.api.main:app --host 0.0.0.0 --port 8000 --reload` | 8000 | Requires venv activation |
| Frontend | `cd frontend && npm run dev -- --port 3000` | 3000 | Proxies `/api/*` to backend via Vite config |
| Desktop | `cd desktop && npm run electron:dev` | 5173 | Optional; auto-manages backend |

### Key Gotchas

- **Python venv required**: Always activate `.venv/bin/activate` before running backend or Python tools (`pytest`, `ruff`, `black`, `context-graph`).
- **No ESLint config**: The `frontend/` directory is missing an `.eslintrc` file; `npm run lint` will fail. This is a pre-existing repo issue.
- **API keys optional**: Without `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, the system falls back to pattern-based analysis. AI chat requires OpenAI specifically.
- **Feature flags**: Many features are behind env-var-based feature flags (see `src/context_graph/config/features.py`). Use `scripts/start-servers.sh` as reference for which flags to set.
- **Storage**: Default is in-memory (lost on restart). Set `STORAGE_BACKEND=sqlite` and `STORAGE_DB_PATH=data/reviews.db` for persistence.
- **Pre-existing test failures**: ~19 pytest failures and ~16 vitest failures exist in the repo. Most Python failures are related to async event loop issues in `pytest-asyncio` and mocking in PM feature tests.

### Lint / Test / Build Commands

See `README.md` Contributing section and `CONTRIBUTING.md` for full details. Quick reference:

- **Python lint**: `ruff check src/` (4800+ pre-existing warnings), `black --check src/`
- **Python tests**: `pytest` (98 passing, 19 pre-existing failures)
- **Frontend tests**: `cd frontend && npx vitest run` (51 passing, 16 pre-existing failures)
- **Frontend lint**: `npm run lint` (requires missing ESLint config — pre-existing issue)
- **Type check**: `mypy src/`

### API Quick Reference

- `POST /api/reviews` — Create a new review (body: `{prd: {content, source_type}, codebase: {path, languages}, config: {use_llm, dimensions}}`)
- `GET /api/reviews/{id}/status` — Poll review progress
- `GET /api/reviews` — List all reviews
- `GET /health` — Backend health check

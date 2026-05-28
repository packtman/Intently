# AGENTS.md — Intently Repository Map

> This file is the single entry point for any AI agent operating in this repository.
> It is a table of contents, not an encyclopedia. Follow links for depth.

## Repository Identity

**Name:** Intently (package: `context-graph`)  
**Purpose:** Multi-dimensional product analysis — bridges PRDs to code across security, privacy, compliance, engineering, and architecture.  
**Stack:** Python 3.10+ (FastAPI) · React 18 (Vite) · Electron 27 · NetworkX · OpenAI/Anthropic LLMs

## Core Architecture

| Domain | Path | Responsibility |
|--------|------|----------------|
| Parsers | `src/context_graph/parsers/` | Extract intent from PRDs (Markdown, Notion, Google Docs) |
| Analyzers | `src/context_graph/analyzers/` | Extract state from codebases (Python, TS, Kotlin, YAML, JSON) |
| Code Graph | `src/context_graph/code_graph/` | Language-agnostic unified code graph (AST + optional LSP) |
| Security | `src/context_graph/security/` | Review engine, STRIDE/OWASP, LINDDUN, compliance patterns |
| PM | `src/context_graph/pm/` | PRD generation, quality scoring, effort estimation, pattern learning |
| API | `src/context_graph/api/` | FastAPI routes (port 8000) |
| Core | `src/context_graph/core/` | Domain models (Intent, State, Finding) and NetworkX graph |
| LLM | `src/context_graph/llm/` | Provider abstraction (OpenAI, Anthropic), parallel analysis |
| Governance | `src/context_graph/governance/` | Gate evaluator for review lifecycle |
| Storage | `src/context_graph/storage/` | SQLite + in-memory backends |
| Config | `src/context_graph/config/` | Feature flags (40+ flags, env-driven) |
| Frontend | `frontend/` | React web dashboard (Vite proxy to :8000) |
| Desktop | `desktop/` | Electron app (explicit backend URL via IPC bridge) |

## Critical Invariants

1. **Dual-app rule:** UI changes MUST be mirrored in both `frontend/` and `desktop/`.
2. **Feature flags:** New features require updates in 6 locations (see `docs/golden_principles.md`).
3. **Desktop API calls:** Must use `${backendUrl}/api/...`, never relative URLs.
4. **No architectural decision is valid unless documented in `docs/`.**

## Documentation Map

| Document | Purpose |
|----------|---------|
| `docs/golden_principles.md` | Inviolable design rules and quality standards |
| `docs/design-docs/` | Architecture Decision Records (ADRs) |
| `docs/exec-plans/` | Implementation execution plans |
| `docs/specs/` | Feature specifications (pre-implementation) |
| `docs/generated/` | Machine-generated reports (boundary checks, refactor candidates) |

## Entry Points

| Action | Command |
|--------|---------|
| Run backend | `context-graph serve` or `uvicorn context_graph.api.main:app` |
| Run frontend | `cd frontend && npm run dev` |
| Run desktop | `cd desktop && npm run electron:dev` |
| Run tests | `pytest src/context_graph/tests/` |
| Lint | `ruff check src/` and `black --check src/` |
| Boot (agent) | `./scripts/agent_boot.sh` |
| Test (agent) | `./scripts/agent_test.sh` |

## Agent Rules

All agents operating in this repository MUST:
1. Read this file before any modification.
2. Consult `docs/golden_principles.md` before proposing architectural changes.
3. Run `scripts/enforce_boundaries.py` before committing to verify no boundary violations.
4. Ensure changes pass `scripts/agent_test.sh` with zero failures.
5. Follow `.cursor/rules/` for implementation conventions.

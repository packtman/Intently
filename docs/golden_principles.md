# Golden Principles — Intently

> These principles are inviolable. Any agent-generated code that violates them
> MUST be rejected or immediately refactored. The nightly garbage collection
> workflow checks compliance continuously.

## 1. Security Boundaries

- **Authentication isolation:** No module outside `src/context_graph/api/` may import or instantiate authentication middleware directly. Auth is a gateway concern.
- **No secrets in code:** API keys, tokens, and credentials must come from environment variables or secure vaults. Never hardcoded, never in defaults.
- **PKCE enforcement:** Any OAuth 2.0 flow must use PKCE. Authorization code flows without code_challenge are forbidden.
- **Input sanitization:** All user-supplied strings rendered in reports or UI must be sanitized to prevent XSS. Raw HTML injection is never acceptable.
- **Token rotation:** Long-lived tokens are forbidden. All tokens must have expiry and rotation mechanisms.

## 2. Architectural Integrity

- **No circular imports:** Module A importing from Module B while B imports from A is a structural violation. Use dependency injection or shared interfaces in `core/`.
- **Domain boundaries:** `parsers/` must not import from `security/`. `analyzers/` must not import from `pm/`. Cross-domain communication goes through `core/` models or the API layer.
- **Single responsibility:** Each file should have one clear domain purpose. Files exceeding 500 lines should be decomposed.
- **Feature flags:** Every new user-facing feature must be behind a feature flag in all 6 locations (class default, `from_env()`, `all_enabled()`, `to_dict()`, `get_enabled_features()`, `FeatureFlagsResponse`).

## 3. Dual-App Consistency

- **Mirror rule:** Any component added to `frontend/src/` that has a corresponding page or feature must also exist in `desktop/src/`.
- **URL discipline:** Frontend uses relative URLs (`/api/...`). Desktop uses `${backendUrl}/api/...`. Mixing them is a boundary violation.
- **Shared types:** Type definitions should be consistent between both apps.

## 4. Code Quality Standards

- **Type hints:** All Python functions must have type annotations. Use `from __future__ import annotations` for forward references.
- **Docstrings:** All public functions and classes must have docstrings explaining purpose, parameters, and return values.
- **Error handling:** Never use bare `except:`. Always catch specific exceptions. Always provide user-actionable error messages.
- **Import hygiene:** Heavy or optional dependencies (chromadb, scikit-learn, pygls) must use lazy imports guarded by try/except.
- **Test coverage:** New features must include at least one happy-path and one error-path test.

## 5. Agent Legibility

- **Structured output:** Scripts and CI must output JSON for machine parsing. Human-readable summaries are secondary.
- **Explicit failures:** Error messages must include: what failed, why it failed, and exactly how to fix it.
- **Deterministic boots:** `scripts/agent_boot.sh` must be idempotent — running it twice produces the same environment.
- **No implicit state:** Environment setup must never rely on undocumented manual steps.

## 6. Documentation as Code

- **Architectural decisions:** Any change to module boundaries, new dependencies, or protocol changes must have a corresponding document in `docs/design-docs/`.
- **Specs before features:** Non-trivial features require a spec in `docs/specs/` before implementation begins.
- **Generated artifacts:** Machine-generated analysis (boundary checks, refactor suggestions) goes in `docs/generated/`. These are ephemeral and may be overwritten.

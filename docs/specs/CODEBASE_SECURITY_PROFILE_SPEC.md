# Codebase Security Profile (Persistent) — Implementation Spec

> Feature 5 from FEATURE_IDEAS.md, ranked 6th in recommendation table.

## Summary

A **standing codebase profile** that persists across reviews and builds up over time:
- **Attack surface map**: all endpoints, which have auth, which handle PII, which are public
- **Entity inventory**: all data models, which are sensitive, data flow between them
- **Cumulative findings**: patterns that keep showing up across reviews
- **Coverage**: which endpoints/files have been reviewed vs. not
- **Historical trend**: risk score over time, findings resolved vs. introduced

---

## Architecture Context

- **Storage pattern**: follows `SQLiteReviewStorage` / `SQLiteCollaborationStorage` in `src/context_graph/storage/sqlite.py` — new table + async CRUD methods
- **API route pattern**: follows `analytics_routes.py` — `APIRouter` with `@requires_feature` decorators, reads from storage singletons via `storage/config.py`
- **Frontend pattern**: follows `Analytics.tsx` — `fetch('/api/...')`, loading/error states, `motion` animations, card grids
- **Desktop pattern**: follows `desktop/src/pages/Analytics.tsx` — same UI but with `baseUrl` from `window.electronAPI.getBackendUrl()`
- **Feature flag pattern**: 5-location checklist in `features.py`
- **Wiring**: nav items in both `Layout.tsx` files, routes in both `App.tsx` files, router in `api/main.py`

### What Must NOT Break
- Existing review pipeline (no changes to `SecurityReviewEngine`)
- Existing SQLite tables (additive schema only)
- Existing frontend routes and navigation

---

## Implementation Order

1. **Feature flag** — `enable_codebase_profile` in all 5 locations in `features.py`
2. **SQLite schema + storage** — new `codebase_profiles` table, add profile CRUD methods to `SQLiteCollaborationStorage`
3. **API routes** — new `codebase_profile_routes.py` with endpoints:
   - `POST /api/codebase-profiles/build` — build/rebuild profile from review history for a given codebase path
   - `GET /api/codebase-profiles` — list all known profiles
   - `GET /api/codebase-profiles/{profile_id}` — get a specific profile
   - `DELETE /api/codebase-profiles/{profile_id}` — delete a profile
4. **Register routes** in `api/main.py`
5. **Frontend page** — `frontend/src/pages/CodebaseProfile.tsx`
6. **Frontend wiring** — add to `frontend/src/components/Layout.tsx` nav + `frontend/src/App.tsx` routes
7. **Desktop page** — `desktop/src/pages/CodebaseProfile.tsx` (same UI, uses `baseUrl`)
8. **Desktop wiring** — add to `desktop/src/components/Layout.tsx` nav + `desktop/src/App.tsx` routes

---

## File Action Table

| File | Action |
|------|--------|
| `src/context_graph/config/features.py` | **MODIFY** — add `enable_codebase_profile` flag in all 5 locations |
| `src/context_graph/storage/sqlite.py` | **MODIFY** — add `CODEBASE_PROFILES_SCHEMA`, add profile methods to `SQLiteCollaborationStorage` |
| `src/context_graph/api/codebase_profile_routes.py` | **CREATE** — API endpoints for codebase profile CRUD + build |
| `src/context_graph/api/main.py` | **MODIFY** — import and register `codebase_profile_routes` router |
| `frontend/src/pages/CodebaseProfile.tsx` | **CREATE** — profile page with attack surface, entity inventory, findings trends, coverage |
| `frontend/src/components/Layout.tsx` | **MODIFY** — add nav item for Codebase Profile |
| `frontend/src/App.tsx` | **MODIFY** — add route for `/codebase-profile` |
| `desktop/src/pages/CodebaseProfile.tsx` | **CREATE** — same page with `baseUrl` for API calls |
| `desktop/src/components/Layout.tsx` | **MODIFY** — add nav item for Codebase Profile |
| `desktop/src/App.tsx` | **MODIFY** — add route for `/codebase-profile` |

---

## Key Implementation Details

### Profile Data Model (stored as JSON in SQLite `codebase_profiles` table)

```sql
CREATE TABLE IF NOT EXISTS codebase_profiles (
    id TEXT PRIMARY KEY,
    codebase_path TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    attack_surface_json TEXT NOT NULL,
    entity_inventory_json TEXT NOT NULL,
    cumulative_findings_json TEXT NOT NULL,
    coverage_json TEXT NOT NULL,
    historical_trend_json TEXT NOT NULL,
    review_count INTEGER DEFAULT 0,
    last_review_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_codebase_profiles_path ON codebase_profiles(codebase_path);
```

### Profile JSON shapes

**attack_surface_json**:
```json
{
  "total_endpoints": 47,
  "endpoints": [
    {"path": "/api/users", "method": "GET", "has_auth": true, "handles_pii": false, "public": false},
    ...
  ],
  "auth_coverage": 0.85,
  "pii_endpoints": 5,
  "public_endpoints": 3
}
```

**entity_inventory_json**:
```json
{
  "total_entities": 23,
  "entities": [
    {"name": "UserProfile", "type": "data_model", "is_sensitive": true, "source_file": "models/user.py", "review_count": 4},
    ...
  ],
  "sensitive_count": 8,
  "by_type": {"data_model": 12, "service": 5, "api": 6}
}
```

**cumulative_findings_json**:
```json
{
  "total_findings": 87,
  "by_dimension": {"security": 30, "privacy": 15, "compliance": 12, "engineering": 20, "architecture": 10},
  "by_severity": {"critical": 3, "high": 12, "medium": 40, "low": 25, "info": 7},
  "recurring_categories": [
    {"category": "input_validation", "count": 8, "last_seen_review": "abc123"},
    ...
  ]
}
```

**coverage_json**:
```json
{
  "total_files_in_codebase": 150,
  "files_touched_by_reviews": 45,
  "coverage_percent": 30.0,
  "endpoints_reviewed": 35,
  "endpoints_total": 47,
  "endpoint_coverage_percent": 74.5
}
```

**historical_trend_json**:
```json
{
  "reviews": [
    {"review_id": "abc", "date": "2026-01-15", "risk_rating": "HIGH", "finding_count": 15, "quality_score": 62},
    {"review_id": "def", "date": "2026-02-01", "risk_rating": "MEDIUM", "finding_count": 8, "quality_score": 78},
    ...
  ]
}
```

### Build Logic

The `POST /api/codebase-profiles/build` endpoint:
1. Takes a `codebase_path` parameter
2. Lists all reviews from storage
3. Filters reviews whose `state.codebase_path` matches (normalized path comparison)
4. For each matching review, aggregates:
   - Endpoints from `state.api_endpoints`
   - Entities from `state.entities`
   - Auth patterns from `state.auth_patterns`
   - Findings by dimension and severity
   - Quality scores and risk ratings for trend
5. Deduplicates entities/endpoints by name
6. Computes coverage as files/endpoints seen across reviews vs. total in latest state
7. Saves the profile to SQLite via `INSERT OR REPLACE`

### Profile Update Strategy

NOT wired into the review pipeline in this phase (to avoid touching `SecurityReviewEngine`). The user triggers build/rebuild from the UI. Automatic updates can be wired in later as a post-review hook.

### Error Handling
- If no reviews match the codebase path: return profile with zero counts and a helpful message
- If codebase path not found on disk: still works (aggregates from historical review data)
- If feature flag disabled: 403 via `@requires_feature`

---

## Constraints Checklist

- [x] Type hints (`from __future__ import annotations`)
- [x] Feature flag in all 5 locations (class default, from_env, all_enabled, to_dict, get_enabled_features)
- [x] Dual-app: frontend AND desktop updated
- [x] Desktop uses `${baseUrl}`, frontend uses relative URLs
- [x] Lazy imports for heavy/optional dependencies
- [x] No breaking changes to existing APIs
- [x] No changes to `pyproject.toml` needed (uses existing `aiosqlite`, `fastapi`)

---

## Verification Plan

- **Backend**: Start server, call `POST /api/codebase-profiles/build` with a codebase path that has past reviews, verify profile JSON is correct
- **Frontend**: Navigate to `/codebase-profile`, verify page loads, shows profiles list, can trigger build, displays all profile sections
- **Desktop**: Same as frontend, verify `baseUrl` is used for all API calls
- **Feature flag**: Verify endpoints return 403 when `FEATURE_CODEBASE_PROFILE` is not set
- **Backward compat**: Verify existing pages (Dashboard, Analytics, Reviews) still work unchanged

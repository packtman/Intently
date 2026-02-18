# P1 — Enhanced PM Experience

> **Priority:** P1
> **Estimated Effort:** 10–13 days total
> **Goal:** Make Intently indispensable — live feedback while writing, version history, governance gates, and metrics.

---

## Features in This Spec

| # | Feature | Extends | Effort |
|---|---------|---------|--------|
| 2 | Real-Time Analysis While Writing | parser, pattern matchers, quality scorer | 2–3 days |
| 3 | PRD Version History & Diffing | prd_history_store, SideBySideDiffGenerator | 2–3 days |
| 6 | Approval Gates & Policies | lifecycle, validation, quality scorer | 2 days |
| 10 | Review Analytics Dashboard | SQLite storage (aggregation only) | 2 days |
| 14 | Product Health Overview | list_reviews, team queues, feedback stats | 2 days |

---

## Feature 2: Real-Time Analysis While Writing

### Overview

As the PM writes or edits a PRD, run lightweight analysis in the background and display results in a sidebar — quality score, finding counts by dimension, and effort estimates update live. **No LLM calls** — uses only pattern matching and heuristic scoring for sub-second response.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `MarkdownPRDParser` | `src/context_graph/parsers/markdown_parser.py` | Parses PRD text → `Intent`. Synchronous, fast. |
| `PRDQualityScorer` | `src/context_graph/pm/quality_scorer.py` | `calculate_score(predicted_questions, prd_content)`. No LLM — pure heuristic. |
| `ThreatPatternMatcher` | `src/context_graph/security/threat_patterns.py` | `match(delta_result)`. Pattern-based, no LLM. |
| `PrivacyPatternMatcher` | `src/context_graph/security/privacy_analyzer.py` | `match(delta_result)`. Pattern-based, no LLM. |
| `CompliancePatternMatcher` | `src/context_graph/security/compliance_analyzer.py` | `match(delta_result)`. Pattern-based, no LLM. |
| `EngineeringPatternMatcher` | `src/context_graph/security/engineering_patterns.py` | `match(delta_result, state, metrics)`. Pattern-based. |
| `ArchitecturePatternMatcher` | `src/context_graph/security/architecture_patterns.py` | `match(delta_result, state, intent, metrics)`. Pattern-based. |
| `DeltaAnalyzer` | `src/context_graph/security/delta_analyzer.py` | `analyze(intent, state)`. Synchronous. |

### New API Endpoint

```python
# In src/context_graph/api/routes.py

class LiveAnalyzeRequest(BaseModel):
    prd_content: str
    review_id: str | None = None  # If set, use cached State from this review

class LiveAnalyzeResponse(BaseModel):
    quality_score: dict          # {score, grade, gaps}
    finding_counts: dict         # {security: 3, privacy: 1, ...}
    total_findings: int
    severity_breakdown: dict     # {critical: 0, high: 2, medium: 3, ...}
    top_issues: list[dict]       # Top 5 findings (title, severity, dimension)

@router.post("/reviews/live-analyze")
@requires_feature("live_analysis")
async def live_analyze(request: LiveAnalyzeRequest) -> LiveAnalyzeResponse:
    """Lightweight analysis for real-time feedback. No LLM calls.

    Pipeline: parse → delta → pattern match all dimensions → quality score
    Target latency: <500ms
    """
    parser = MarkdownPRDParser()
    intent = parser.parse(request.prd_content, "Live Preview")

    # Use cached state from previous full review, or empty state
    state = State()
    if request.review_id:
        stored = await storage.get_review(request.review_id)
        if stored:
            state = stored.state

    delta_result = DeltaAnalyzer().analyze(intent, state)

    # Run all pattern matchers (all fast, no LLM)
    security = ThreatPatternMatcher().match(delta_result)
    privacy = PrivacyPatternMatcher().match(delta_result)
    compliance = CompliancePatternMatcher().match(delta_result)
    # ... engineering, architecture

    quality = PRDQualityScorer().calculate_score([], request.prd_content)

    return LiveAnalyzeResponse(
        quality_score={"score": quality.score, "grade": quality.grade, "gaps": quality.gaps},
        finding_counts={"security": len(security), "privacy": len(privacy), ...},
        ...
    )
```

### Frontend Changes

- Debounced calls (2s after typing stops) from PRD textarea in `NewReview.tsx`
- New `LiveAnalysisSidebar` component showing:
  - Quality score gauge (A/B/C/D/F with color)
  - Finding count badges by dimension
  - Severity breakdown bar chart
  - Top 5 issues with severity icons
- All update in real-time as PM types

### Feature Flag
`FEATURE_LIVE_ANALYSIS=true`

### Definition of Done
- [ ] `POST /api/reviews/live-analyze` returns results in <500ms
- [ ] No LLM calls made during live analysis
- [ ] Quality score, finding counts, and top issues render in sidebar
- [ ] Debounced updates (2s) trigger on typing in PRD editor

---

## Feature 3: PRD Version History & Diffing

### Overview

Full version history for every PRD with diff views showing text changes and analysis deltas between versions.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `prd_history_store` | `pm_routes.py` line 33 | **Already stores** PRD versions per review_id. In-memory dict. |
| `prd_file_info_store` | `pm_routes.py` line 35 | **Already tracks** PRD file state (original, current, backup). In-memory. |
| `SideBySideDiffGenerator` | `pm/diff_generator.py` | **Already generates** side-by-side diffs with word-level highlighting. |
| `SideBySideDiffModal` | `frontend/src/components/pm/SideBySideDiffModal.tsx` | **Already renders** side-by-side diffs. |
| `PRDFileInfo` model | `core/models.py` line 924 | `original_content`, `current_content`, `backup_path`, `last_saved_at`. |
| `SQLiteReviewStorage` | `storage/sqlite.py` | Already saves `ReviewResult` with `original_prd_content`. |

### New SQLite Table

```sql
CREATE TABLE prd_versions (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    change_summary TEXT,           -- Auto-generated or manual
    quality_score REAL,            -- Score at time of save
    finding_count INTEGER,         -- Total findings at time of save
    created_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);
CREATE INDEX idx_prd_versions_review ON prd_versions(review_id);
CREATE UNIQUE INDEX idx_prd_versions_unique ON prd_versions(review_id, version_number);
```

### New API Endpoints

```python
# Extend src/context_graph/api/pm_routes.py

@router.get("/reviews/{review_id}/versions")
async def list_prd_versions(review_id: str) -> list[dict]:
    """List all PRD versions for a review."""

@router.get("/reviews/{review_id}/versions/{v1}/{v2}/diff")
async def get_version_diff(review_id: str, v1: int, v2: int) -> dict:
    """Side-by-side diff between two versions. Uses existing SideBySideDiffGenerator."""
    # 1. Load both versions from prd_versions table
    # 2. Generate diff using SideBySideDiffGenerator
    # 3. Also compute analysis diff: findings added/removed between versions

@router.post("/reviews/{review_id}/versions")
async def save_prd_version(review_id: str) -> dict:
    """Save current PRD content as a new version."""
```

### Frontend Changes

- **New component:** `VersionHistory.tsx` — timeline showing versions with author, timestamp, change summary
- Click a version → view in `SideBySideDiffModal` (already exists)
- Version comparison picker: select two versions → see text diff + analysis diff
- Analysis diff: "Version 2 resolved 3 security findings, introduced 1 privacy concern"
- Integrate into `ReviewDetail.tsx` as a new tab

### Feature Flag
`FEATURE_PRD_VERSION_HISTORY=true`

### Definition of Done
- [ ] PRD versions persist in SQLite (not in-memory)
- [ ] `GET /reviews/{id}/versions` returns version list with metadata
- [ ] `GET /reviews/{id}/versions/{v1}/{v2}/diff` returns text diff + analysis diff
- [ ] Version timeline renders in frontend with diff modal
- [ ] Auto-save version on major actions (initial submit, after accepting changes, after re-analysis)

---

## Feature 6: Approval Gates & Policies

### Overview

Configurable policies that automatically block PRD approval when conditions aren't met. Evaluated when lifecycle attempts to advance to "approved".

### What Exists Today

| Component | File | Used How |
|---|---|---|
| Review lifecycle | `collaboration_routes.py` | State machine with `draft → in_review → ... → approved / blocked` |
| Finding validation | `collaboration_routes.py` | Tracks per-finding: pending, validated, rejected, needs_discussion, accepted_risk, deferred |
| `PRDQualityScore` | `pm/quality_scorer.py` | `score`, `grade`, `blockers`, `likely_questions` |
| `FeatureFlags` | `config/features.py` | Existing pattern for config-driven behavior |
| `context-graph.yaml` | root | Existing YAML config file |

### New File

```python
# src/context_graph/governance/gate_evaluator.py

@dataclass
class ApprovalGate:
    name: str
    condition: str       # "no_unresolved_critical", "team_approved:security", "quality_score_above:70"
    blocking: bool       # True = hard block, False = warning only
    description: str = ""

@dataclass
class GateResult:
    gate: ApprovalGate
    passed: bool
    reason: str = ""     # Why it failed

class GateEvaluator:
    """Evaluates approval gates against current review state."""

    def __init__(self, review_storage, collab_storage):
        self.review_storage = review_storage
        self.collab_storage = collab_storage

    async def evaluate_all(self, review_id: str, gates: list[ApprovalGate]) -> list[GateResult]:
        """Evaluate all gates. Queries existing storage for validation/review data."""
        results = []
        review = await self.review_storage.get_review(review_id)

        for gate in gates:
            if gate.condition == "no_unresolved_critical":
                # Check: all critical findings are validated or accepted_risk
                validations = await self.collab_storage.get_validations_for_review(review_id)
                critical = [f for f in review.all_findings if f.severity.value == "critical"]
                unresolved = [f for f in critical if str(f.id) not in validations
                              or validations[str(f.id)]["status"] == "pending"]
                passed = len(unresolved) == 0
                results.append(GateResult(gate, passed, f"{len(unresolved)} unresolved critical findings"))

            elif gate.condition.startswith("team_approved:"):
                team = gate.condition.split(":")[1]
                # Check: team has approved via consensus or validation
                ...

            elif gate.condition.startswith("quality_score_above:"):
                threshold = int(gate.condition.split(":")[1])
                passed = (review.prd_quality_score and review.prd_quality_score.score >= threshold)
                results.append(GateResult(gate, passed, f"Quality score: {review.prd_quality_score.score}"))

        return results
```

### Config in `context-graph.yaml`

```yaml
approval_gates:
  - name: "No unresolved critical findings"
    condition: no_unresolved_critical
    blocking: true
  - name: "Security team sign-off"
    condition: team_approved:security
    blocking: true
  - name: "PRD quality above 70"
    condition: quality_score_above:70
    blocking: false   # Warning only
```

### Wire Into Lifecycle

In `collaboration_routes.py`, when `POST /reviews/{id}/lifecycle` attempts to set state to `approved`, call `GateEvaluator.evaluate_all()`. If any blocking gate fails, reject the transition and return gate failures.

### Frontend Changes

- Gate status badges in `ReviewDetail.tsx` header: ✅ passed / ❌ blocked / ⚠️ warning
- Clicking a failed gate shows the reason and links to unresolved findings

### Feature Flag
`FEATURE_APPROVAL_GATES=true`

### Definition of Done
- [ ] Gates loaded from `context-graph.yaml`
- [ ] `GateEvaluator` evaluates gates using existing storage queries
- [ ] Lifecycle transition to "approved" blocked when gates fail
- [ ] Gate results returned in API response with reasons
- [ ] Gate status badges render in ReviewDetail

---

## Feature 10: Review Analytics Dashboard

### Overview

Metrics dashboard aggregating data from existing SQLite tables: review cycle times, finding resolution rates, quality trends, team responsiveness.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `SQLiteReviewStorage` | `storage/sqlite.py` | All reviews with timestamps, findings, dimensions. `list_reviews()`. |
| `SQLiteCollaborationStorage` | `storage/sqlite.py` | Validations (with timestamps), comments, assignments, feedback. |
| `Dashboard` page | `frontend/src/pages/Dashboard.tsx` | Already renders review summaries. |
| `DashboardDataGenerator` | `reports/json_report.py` | Already generates per-review dashboard data. |

### New API Endpoint

```python
# In src/context_graph/api/routes.py

@router.get("/analytics")
@requires_feature("review_analytics")
async def get_analytics() -> dict:
    """Aggregate analytics across all reviews. Pure SQL aggregation — no computation."""
    storage = get_review_storage()
    collab_storage = get_collaboration_storage()

    reviews = await storage.list_reviews()
    total = len(reviews)

    return {
        "overview": {
            "total_reviews": total,
            "completed": sum(1 for r in reviews if r["status"] == "completed"),
            "avg_findings_per_review": ...,
        },
        "findings_by_dimension": {
            "security": ..., "privacy": ..., "compliance": ...,
            "engineering": ..., "architecture": ...,
        },
        "findings_by_severity": {
            "critical": ..., "high": ..., "medium": ..., "low": ...,
        },
        "quality_trend": [
            # Quality scores per review over time
            {"review_id": "...", "date": "...", "score": 78},
            ...
        ],
        "resolution_stats": {
            "total_findings": ...,
            "validated": ...,
            "rejected": ...,  # false positives
            "pending": ...,
            "resolution_rate": ...,
        },
        "top_finding_categories": [
            # Most common finding types across all reviews
            {"category": "broken_access_control", "count": 12},
            ...
        ],
    }
```

### Frontend Changes

- **New page:** `frontend/src/pages/Analytics.tsx`
  - Overview cards: total reviews, avg findings, resolution rate
  - Bar chart: findings by dimension
  - Severity pie chart
  - Quality score trend line chart
  - Top finding categories ranked list
- Add "Analytics" link to `Layout.tsx` navigation

### Feature Flag
`FEATURE_REVIEW_ANALYTICS=true`

### Definition of Done
- [ ] `GET /api/analytics` returns aggregated stats from SQLite
- [ ] Analytics page renders with overview cards and charts
- [ ] Quality trend chart shows scores over time
- [ ] Resolution stats show validated vs rejected vs pending

---

## Feature 14: Product Health Overview

### Overview

High-level org-wide dashboard: active PRDs, aggregate risk heatmap, team workloads, and trending patterns. Complements per-review analytics (Feature 10) with a cross-review product view.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `list_reviews()` | `api/routes.py` | Returns all reviews with summary info |
| Team queue | `collaboration_routes.py` | `GET /teams/{team}/queue` — team workload data |
| Feedback stats | `collaboration_routes.py` | `GET /feedback/stats` — pattern/feedback counts |
| `Dashboard` page | `frontend/src/pages/Dashboard.tsx` | Already shows recent reviews |

### New API Endpoint

```python
@router.get("/overview")
@requires_feature("product_overview")
async def get_product_overview() -> dict:
    """Org-wide product health. Aggregates existing data."""
    return {
        "active_prds": [...],          # Reviews not yet completed/approved
        "risk_heatmap": {
            "security": {"critical": 2, "high": 5, "medium": 8},
            "privacy": {...},
            ...
        },
        "team_workloads": {
            "security": {"pending_reviews": 3, "pending_findings": 12},
            "privacy": {"pending_reviews": 1, "pending_findings": 4},
            ...
        },
        "trending_patterns": [
            {"category": "missing_rate_limiting", "count": 8, "trend": "increasing"},
            ...
        ],
        "recent_activity": [...],
    }
```

### Frontend Changes

- **Extend `Dashboard.tsx`:** Add org-wide overview section above the review list
  - Risk heatmap: 5×4 grid (dimensions × severities) with color intensity
  - Team workload bars
  - Trending patterns list with trend indicators
- Or: **New page** `frontend/src/pages/ProductOverview.tsx` linked from nav

### Feature Flag
`FEATURE_PRODUCT_OVERVIEW=true`

### Definition of Done
- [ ] `GET /api/overview` returns org-wide aggregated data
- [ ] Risk heatmap renders with correct severity counts by dimension
- [ ] Team workloads show pending review counts
- [ ] Trending patterns surface most common finding categories

---

## Shared Implementation Notes

### Feature Flags

Add to `src/context_graph/config/features.py`:

```python
# P1: Enhanced PM Experience
enable_live_analysis: bool = False
enable_prd_version_history: bool = False
enable_approval_gates: bool = False
enable_review_analytics: bool = False
enable_product_overview: bool = False
```

### Dependencies Between P1 Features

- Features 10 and 14 are **independent** — can ship separately
- Feature 6 (Approval Gates) benefits from Feature 4 (Review Requests, P0) but works standalone with existing lifecycle
- Feature 3 (Version History) benefits from Feature 2 (Live Analysis) for auto-saving versions
- Feature 2 is **fully independent** — uses only existing pattern matchers

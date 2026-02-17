# Feature Ideas — Iteration 1

## Vision: Cursor + GitHub for Product Managers

Intently should be an AI-powered workspace for PMs — intelligent authoring, structured reviews, and organizational knowledge — all grounded in actual codebase context.

This document proposes **14 features** that are directly complementary to the existing codebase. Every feature extends an existing module, wires together existing capabilities, or fills a gap identified in the current ROADMAP. No greenfield rewrites — each idea specifies the exact files, classes, and APIs it builds on.

---

## Table of Contents

1. [Feature 1: Product-Aware Chat](#feature-1-product-aware-chat)
2. [Feature 2: Real-Time Analysis While Writing](#feature-2-real-time-analysis-while-writing)
3. [Feature 3: PRD Version History & Diffing](#feature-3-prd-version-history--diffing)
4. [Feature 4: Formal PRD Review Requests](#feature-4-formal-prd-review-requests)
5. [Feature 5: Impact Graph Visualization](#feature-5-impact-graph-visualization)
6. [Feature 6: Approval Gates & Policies](#feature-6-approval-gates--policies)
7. [Feature 7: Decision Log](#feature-7-decision-log)
8. [Feature 8: Predictive Risk Scoring](#feature-8-predictive-risk-scoring)
9. [Feature 9: PRD Templates Library](#feature-9-prd-templates-library)
10. [Feature 10: Review Analytics Dashboard](#feature-10-review-analytics-dashboard)
11. [Feature 11: GitHub PR Finding Sync](#feature-11-github-pr-finding-sync)
12. [Feature 12: Inline PRD Authoring with AI Assist](#feature-12-inline-prd-authoring-with-ai-assist)
13. [Feature 13: Compliance Audit Trail](#feature-13-compliance-audit-trail)
14. [Feature 14: Product Health Overview](#feature-14-product-health-overview)
15. [Prioritization Matrix](#prioritization-matrix)
16. [Summary](#summary)

---

## Feature 1: Product-Aware Chat

> **What:** A conversational AI interface where PMs ask natural-language questions about their product, codebase, and review history — grounded in actual data from the context graph, review storage, and pattern learner.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `ContextGraph` | `src/context_graph/core/graph.py` | `get_entities_by_type()`, `get_sensitive_entities()`, `find_unauthenticated_paths()`, `find_trust_boundary_crossings()`, `compute_risk_score()` — all queryable via chat |
| `SQLiteReviewStorage` | `src/context_graph/storage/sqlite.py` | `list_reviews()`, `get_review()` — chat can query review history |
| `SQLiteCollaborationStorage` | `src/context_graph/storage/sqlite.py` | Feedback stats, validation history, comments — chat can surface expert decisions |
| `ParallelLLMAnalyzer` | `src/context_graph/llm/parallel_analyzer.py` | OpenAI + Anthropic providers already configured — reuse for chat completions |
| `PatternLearner` | `src/context_graph/pm/pattern_learner.py` | `learned_patterns` — chat can reference what the system has learned |

### Implementation

**New file:** `src/context_graph/api/chat_routes.py`

```python
@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Answer product questions using context graph + review history + LLM."""
    # 1. Query context graph for relevant entities
    # 2. Query review storage for relevant past reviews
    # 3. Query collaboration storage for expert decisions
    # 4. Build grounded context from the above
    # 5. Send to existing LLM provider with citations
```

**New file:** `src/context_graph/chat/product_chat.py`

The chat engine queries existing storage classes and builds a grounded prompt. No new storage tables required — it reads from what exists.

**Frontend:** New `ChatPanel` component in the sidebar of `ReviewDetail.tsx`, similar to Cursor's Cmd+L.

### Example Queries (all answerable from existing data)
- "What services access PII?" → `graph.get_entities_by_type(EntityType.PII)` + relationships
- "What did the security team flag in the last review?" → `storage.get_review(last_id)` → `review.security_findings`
- "How many times has rate limiting been flagged?" → `storage.list_reviews()` → scan findings
- "What patterns has the system learned?" → `pattern_learner.learned_patterns`

### Feature Flag
`FEATURE_PRODUCT_CHAT=true`

---

## Feature 2: Real-Time Analysis While Writing

> **What:** As the PM writes or edits a PRD, continuously run lightweight analysis and display results in a sidebar — PRD quality score, finding counts by dimension, and effort estimates update live.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `MarkdownPRDParser` | `src/context_graph/parsers/markdown_parser.py` | Already parses PRD text → `Intent`. Can be called repeatedly. |
| `PRDQualityScorer` | `src/context_graph/pm/quality_scorer.py` | `calculate_score(predicted_questions, prd_content)` — returns score, grade, gaps. Already fast (no LLM). |
| `PRDChangeGenerator` | `src/context_graph/pm/prd_change_generator.py` | `generate_changes(findings, prd_content)` — pattern-based, no LLM required for quick pass. |
| `ThreatPatternMatcher` | `src/context_graph/security/threat_patterns.py` | `match(delta_result)` — fast pattern matching, no LLM call. |
| `DeltaAnalyzer` | `src/context_graph/security/delta_analyzer.py` | `analyze(intent, state)` — computes delta synchronously. |

### Implementation

**New API endpoint:** `POST /api/reviews/live-analyze` in `src/context_graph/api/routes.py`

This endpoint runs a lightweight analysis pipeline (parser → delta → pattern matching → quality score) — the **same pipeline** as `SecurityReviewEngine.review()` but skipping LLM calls. All pattern matchers and quality scoring already work without LLM.

```python
@router.post("/reviews/live-analyze")
async def live_analyze(request: LiveAnalyzeRequest) -> LiveAnalyzeResponse:
    """Lightweight analysis for real-time feedback. No LLM calls."""
    parser = MarkdownPRDParser()
    intent = parser.parse(request.prd_content, "Live Preview")
    
    # Use cached state from last full analysis (or empty state)
    delta = DeltaAnalyzer().analyze(intent, cached_state)
    
    # Run pattern matchers (fast, no LLM)
    security_findings = ThreatPatternMatcher().match(delta)
    privacy_findings = PrivacyPatternMatcher().match(delta)
    # ... other dimension pattern matchers
    
    # Run quality scorer (fast, no LLM)  
    quality = PRDQualityScorer().calculate_score([], request.prd_content)
    
    return LiveAnalyzeResponse(
        quality_score=quality,
        finding_counts={...},
        dimension_summary={...},
    )
```

**Frontend:** Debounced calls (2s delay) from the PRD editor textarea in `NewReview.tsx` to this endpoint. Results render in a sidebar with live-updating badges.

### Feature Flag
`FEATURE_LIVE_ANALYSIS=true`

---

## Feature 3: PRD Version History & Diffing

> **What:** Full version history for every PRD with diff views showing text changes and analysis deltas between versions.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `prd_history_store` | `src/context_graph/api/pm_routes.py` (line 33) | **Already exists** as `prd_history_store: dict[str, list[str]]` — stores PRD versions per review_id. Currently in-memory. |
| `SideBySideDiffGenerator` | `src/context_graph/pm/diff_generator.py` | Already generates side-by-side diffs with word-level highlighting. Used for PRD change previews. |
| `SQLiteReviewStorage` | `src/context_graph/storage/sqlite.py` | Already saves full `ReviewResult` including `original_prd_content`. |
| `PRDFileInfo` model | `src/context_graph/core/models.py` (line 924) | Already has `original_content`, `current_content`, `backup_path`, `last_saved_at`. |
| `prd_file_info_store` | `src/context_graph/api/pm_routes.py` (line 35) | **Already exists** — tracks PRD file state. Currently in-memory. |

### Implementation

The core pieces already exist but are in-memory. This feature:

1. **New SQLite table:** `prd_versions` — stores each version with timestamp, author, content, and associated review_id.

```sql
CREATE TABLE prd_versions (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    change_summary TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);
```

2. **New methods on `SQLiteReviewStorage`:** `save_prd_version()`, `get_prd_versions()`, `get_prd_version_diff()`.

3. **Extend `/api/reviews/{id}/versions` endpoint** to persist and retrieve version history from SQLite instead of `prd_history_store`.

4. **Version diff endpoint:** `GET /api/reviews/{id}/versions/{v1}/{v2}/diff` — uses existing `SideBySideDiffGenerator` to produce text diff, and compares `ReviewResult.all_findings` between versions for analysis diff.

5. **Frontend:** New `VersionHistory` component in `ReviewDetail.tsx` — timeline view with diff modal (reusing existing `SideBySideDiffModal.tsx`).

### Feature Flag
`FEATURE_PRD_VERSION_HISTORY=true`

---

## Feature 4: Formal PRD Review Requests

> **What:** PMs submit a PRD for structured review with designated reviewers, deadlines, and tracked status — the PM equivalent of a GitHub Pull Request.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| Review lifecycle | `src/context_graph/api/collaboration_routes.py` | **Already has** lifecycle management: `POST /reviews/{id}/lifecycle` with states: `draft → in_review → team_review → awaiting_signoff → approved / blocked`. Feature flag: `FEATURE_REVIEW_LIFECYCLE`. |
| Cross-team requests | `src/context_graph/api/collaboration_routes.py` | **Already has** `POST /reviews/{id}/requests` — requesting input from other teams with deadlines. Feature flag: `FEATURE_CROSS_TEAM_REQUESTS`. |
| Team assignment | `src/context_graph/api/collaboration_routes.py` | **Already has** `POST /reviews/{id}/findings/{id}/assign` — routing to team queues. |
| Consensus mode | `src/context_graph/api/collaboration_routes.py` | **Already has** multi-team approval voting: `POST /reviews/{id}/findings/{id}/consensus`. |
| `TeamQueue` page | `frontend/src/pages/TeamQueue.tsx` | **Already exists** — shows team's assigned findings. |
| `CollaborationStorage` | `src/context_graph/storage/base.py` | Abstract interface for all collaboration data (validations, comments, assignments, feedback). |

### Implementation

The building blocks exist across collaboration routes. This feature **wires them together** into a unified "Review Request" workflow:

1. **New model:** `ReviewRequest` — wraps lifecycle + reviewer list + deadline + auto-analysis attachment.

```python
@dataclass
class PRDReviewRequest:
    id: UUID
    review_id: str           # Links to existing ReviewResult
    requested_by: str        # PM who submitted
    reviewers: list[dict]    # [{team: "security", user_id: "...", required: True}]
    deadline: datetime | None
    status: str              # "open", "changes_requested", "approved", "blocked"
    created_at: datetime
```

2. **New SQLite table:** `review_requests` + `review_request_approvals`.

3. **New API endpoints:**
   - `POST /api/reviews/{id}/request-review` — creates request, auto-assigns findings to reviewer teams (using existing team assignment), advances lifecycle to `in_review`
   - `GET /api/reviews/{id}/review-request` — status dashboard (how many approvals, who's pending)
   - `POST /api/reviews/{id}/approve` — reviewer approves (writes to existing consensus/validation stores)

4. **Frontend:** New `ReviewRequestPanel` component in `ReviewDetail.tsx` — shows reviewer status, approval progress. Extends existing `ReviewDetail` page.

### Feature Flag
`FEATURE_REVIEW_REQUESTS=true` (activates the orchestration layer on top of existing `FEATURE_REVIEW_LIFECYCLE` + `FEATURE_TEAM_ASSIGNMENT`)

---

## Feature 5: Impact Graph Visualization

> **What:** Interactive visualization of the context graph showing entities, relationships, data flows, and blast radius of proposed changes.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `ContextGraph` | `src/context_graph/core/graph.py` | NetworkX directed graph with entities, relationships, traversal methods. |
| `Entity` / `Relationship` models | `src/context_graph/core/models.py` | Full type system: EntityType (16 types), RelationshipType (16 types). |
| `_build_graph()` | `src/context_graph/security/review_engine.py` (line 1214) | Already builds graph from Intent + State + Delta every review. |
| `_analyze_graph()` | `src/context_graph/security/review_engine.py` (line 1391) | Already queries: unauthenticated paths, trust boundary crossings, high-risk entities. |
| JSON report | `src/context_graph/reports/json_report.py` | Already serializes review data to JSON for the frontend. |
| Dashboard page | `frontend/src/pages/Dashboard.tsx` | Already renders review data — graph visualization would be a new tab/component. |

### Implementation

The context graph **already exists and is populated every review**. This feature just exposes it visually.

1. **New API endpoint:** `GET /api/reviews/{id}/graph`

```python
@router.get("/reviews/{review_id}/graph")
async def get_review_graph(review_id: str) -> dict:
    """Return graph data for visualization."""
    # Reconstruct graph from review's intent + state + delta
    # Return nodes (entities) and edges (relationships) in D3-compatible format
    return {
        "nodes": [{"id": str(e.id), "name": e.name, "type": e.entity_type.value, 
                    "sensitive": e.is_sensitive, "risk_score": graph.compute_risk_score(e.id)} ...],
        "edges": [{"source": str(r.source_id), "target": str(r.target_id), 
                    "type": r.relationship_type.value, "crosses_boundary": r.crosses_trust_boundary} ...],
        "stats": {"entities": len(nodes), "relationships": len(edges), ...}
    }
```

2. **Frontend:** New `ImpactGraph` component using D3.js force-directed layout:
   - Nodes colored by `EntityType` (PII = red, API = blue, SERVICE = green)
   - Edges colored by `RelationshipType` (trust boundary crossings = red dashed)
   - Click node → show entity details + linked findings
   - "Blast radius" toggle: highlight entities affected by the current PRD's delta (`delta.affected_components`)
   - Filters: show only PII paths, show only external-facing, show only affected by this PRD

3. **Tab in `ReviewDetail.tsx`:** Add "Impact Graph" alongside existing "Findings", "PRD Changes", etc.

### Feature Flag
`FEATURE_IMPACT_GRAPH=true`

---

## Feature 6: Approval Gates & Policies

> **What:** Configurable policies that automatically block PRD approval when conditions aren't met (unresolved critical findings, missing team sign-offs).

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| Review lifecycle | `src/context_graph/api/collaboration_routes.py` | Already has state machine: `draft → in_review → ... → approved / blocked`. |
| Consensus mode | `src/context_graph/api/collaboration_routes.py` | Already supports multi-team voting on findings. |
| Finding validation | `src/context_graph/api/collaboration_routes.py` | Already tracks validation status per finding (pending, validated, rejected, etc.). |
| `PRDQualityScore` | `src/context_graph/pm/quality_scorer.py` | Already calculates quality score and grade. |
| `FeatureFlags` | `src/context_graph/config/features.py` | Existing pattern for feature-gated behavior. |

### Implementation

1. **New file:** `src/context_graph/governance/gate_evaluator.py`

```python
@dataclass
class ApprovalGate:
    name: str
    condition: str   # "no_unresolved_critical", "security_team_approved", "quality_score_above_70"
    blocking: bool   # If True, blocks advancement to "approved" state

class GateEvaluator:
    def evaluate(self, review_id: str, gates: list[ApprovalGate]) -> GateResult:
        """Check all gates against current review state."""
        # Queries existing storage: findings, validations, quality scores
```

2. **New config section in `context-graph.yaml`:**

```yaml
approval_gates:
  - name: "No unresolved critical findings"
    condition: no_unresolved_critical
    blocking: true
  - name: "Security team sign-off"
    condition: team_approved:security
    blocking: true
  - name: "PRD quality score above 70"
    condition: quality_score_above:70
    blocking: false
```

3. **Wire into lifecycle endpoint:** When `POST /reviews/{id}/lifecycle` attempts to advance to `approved`, run gate evaluation. Return gate failures in the response.

4. **Frontend:** Gate status badges in `ReviewDetail.tsx` — green check / red X per gate.

### Feature Flag
`FEATURE_APPROVAL_GATES=true`

---

## Feature 7: Decision Log

> **What:** Append-only log attached to each review capturing key decisions, rationale, and links to findings. Auto-populated from review actions.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `CollaborationStorage` | `src/context_graph/storage/base.py` | Abstract storage pattern — decision log follows same pattern as validations/comments. |
| Finding validation | `src/context_graph/api/collaboration_routes.py` | When a finding is validated/rejected with notes, that's already a decision. |
| Expert feedback | `src/context_graph/api/collaboration_routes.py` | Expert corrections are decisions. |
| Lifecycle transitions | `src/context_graph/api/collaboration_routes.py` | State changes with notes are decisions. |
| `SQLiteCollaborationStorage` | `src/context_graph/storage/sqlite.py` | All collaboration data already persists in SQLite. |

### Implementation

1. **New SQLite table:** `decision_log`

```sql
CREATE TABLE decision_log (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    decision_type TEXT NOT NULL,  -- "accepted_risk", "rejected_finding", "approved_prd", "scope_change"
    title TEXT NOT NULL,
    rationale TEXT,
    decided_by TEXT NOT NULL,
    linked_finding_ids TEXT,      -- JSON array
    linked_comment_ids TEXT,      -- JSON array
    alternatives_considered TEXT, -- JSON array
    created_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);
```

2. **Auto-populate from existing actions:** When `validate_finding()` is called with status `accepted_risk` or `rejected`, automatically create a decision log entry. When lifecycle advances to `approved`, create an approval decision entry.

3. **New API endpoints:**
   - `POST /api/reviews/{id}/decisions` — manual decision entry
   - `GET /api/reviews/{id}/decisions` — list all decisions for a review
   - `GET /api/decisions/search?q=rate+limiting` — search across all reviews

4. **Frontend:** `DecisionLog` component in `ReviewDetail.tsx` — timeline view.

### Feature Flag
`FEATURE_DECISION_LOG=true`

---

## Feature 8: Predictive Risk Scoring

> **What:** Before writing a PRD, predict the likely risk profile based on the type of change and historical patterns.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `SQLiteReviewStorage` | `src/context_graph/storage/sqlite.py` | `list_reviews()` returns all past reviews with findings. |
| `PatternLearner` | `src/context_graph/pm/pattern_learner.py` | Learned patterns from expert feedback. |
| `DeltaAnalysisResult` | `src/context_graph/security/delta_analyzer.py` | `introduces_pii`, `attack_surface_changes`, `auth_requirement_changes` — structured delta signals. |
| `ReviewResult` | `src/context_graph/security/review_engine.py` | `findings_by_dimension`, `critical_count`, `high_count` — aggregated stats per review. |
| `PRDQualityScorer` | `src/context_graph/pm/quality_scorer.py` | Already scores quality — can be extended with predictions. |

### Implementation

1. **New file:** `src/context_graph/pm/risk_predictor.py`

```python
class RiskPredictor:
    def __init__(self, storage: SQLiteReviewStorage):
        self.storage = storage
    
    async def predict(self, feature_description: str, affected_entities: list[str]) -> RiskPrediction:
        """Predict risk profile based on historical reviews."""
        # 1. Load all past reviews from storage
        # 2. Find reviews that touched similar entities or had similar delta patterns
        # 3. Aggregate finding counts by dimension across matching reviews
        # 4. Return prediction with confidence interval and cited reviews
```

2. **New API endpoint:** `POST /api/predict-risk`

```python
@router.post("/predict-risk")
async def predict_risk(request: PredictRiskRequest) -> PredictRiskResponse:
    """Predict risk profile for a planned feature."""
    return {
        "predicted_findings": {"security": 3, "privacy": 2, "compliance": 1, ...},
        "estimated_review_time": "2-3 hours",
        "suggested_reviewers": ["security", "privacy"],
        "similar_past_reviews": [{"id": "...", "title": "...", "findings": 8}],
        "confidence": 0.72,
    }
```

3. **Frontend:** New section in `NewReview.tsx` — before the PM starts writing, they describe the feature and get a risk prediction.

### Feature Flag
`FEATURE_RISK_PREDICTION=true`

---

## Feature 9: PRD Templates Library

> **What:** Organization-specific PRD templates with required sections and pre-filled boilerplate, evolving based on review patterns.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `PRDGenerator` | `src/context_graph/pm/prd_generator.py` | Already generates PRD sections from codebase analysis. `GeneratedSection` model with title, content, subsections, source_files, confidence. |
| `PRDQualityScorer` | `src/context_graph/pm/quality_scorer.py` | Already identifies gaps in PRDs — these gaps inform which template sections are required. |
| `PRDGenerator` API | `src/context_graph/api/prd_generator_routes.py` | Already has `POST /api/prd-generator/generate` endpoint. |
| PRDGenerator page | `frontend/src/pages/PRDGenerator.tsx` | Already has UI for generating PRDs from codebases. |
| Feature flags | `src/context_graph/config/features.py` | `FEATURE_PRD_GENERATOR` already exists. |

### Implementation

1. **New file:** `src/context_graph/pm/template_library.py`

```python
@dataclass
class PRDTemplate:
    id: str
    name: str            # "New Feature", "API Change", "Data Migration"
    description: str
    required_sections: list[str]  # ["Security Considerations", "Data Flow", "Rollback Plan"]
    section_guidance: dict[str, str]  # Section name → guidance text
    boilerplate: str     # Pre-filled markdown template

class TemplateLibrary:
    def get_templates(self) -> list[PRDTemplate]:
        """Return built-in + org-specific templates."""
    
    def suggest_template(self, prd_content: str) -> PRDTemplate | None:
        """Suggest a template based on PRD content keywords."""
        # Uses same keyword extraction as PRDChangeGenerator._find_relevant_section()
    
    def generate_from_template(self, template_id: str, context: dict) -> str:
        """Generate pre-filled PRD from template + codebase context."""
        # Reuses PRDGenerator.generate() for section content
```

2. **New SQLite table:** `prd_templates` — stores org-specific templates.

3. **Wire into PRDGenerator:** When `PRDGenerator` generates a PRD, it uses the best-matching template as the scaffold.

4. **Extend `NewReview.tsx`:** Template picker before PRD input.

### Feature Flag
`FEATURE_PRD_TEMPLATES=true`

---

## Feature 10: Review Analytics Dashboard

> **What:** Metrics dashboard showing review cycle times, finding resolution rates, team responsiveness, and quality trends.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `SQLiteReviewStorage` | `src/context_graph/storage/sqlite.py` | All reviews with timestamps, findings, dimensions analyzed. `list_reviews()` returns summaries. |
| `SQLiteCollaborationStorage` | `src/context_graph/storage/sqlite.py` | Validations (with `validated_at`), comments, assignments, feedback — all timestamped. |
| `Dashboard` page | `frontend/src/pages/Dashboard.tsx` | Already renders review summaries — analytics would extend this. |
| `DashboardDataGenerator` | `src/context_graph/reports/json_report.py` | Already generates dashboard-formatted data per review. |

### Implementation

1. **New API endpoint:** `GET /api/analytics`

```python
@router.get("/analytics")
async def get_analytics() -> dict:
    """Aggregate analytics across all reviews."""
    storage = get_review_storage()
    reviews = await storage.list_reviews()
    
    collab_storage = get_collaboration_storage()
    
    return {
        "total_reviews": len(reviews),
        "avg_findings_per_review": ...,
        "findings_by_dimension": {"security": 45, "privacy": 23, ...},
        "findings_by_severity": {"critical": 5, "high": 18, ...},
        "resolution_rate": ...,      # validated / total findings
        "avg_review_cycle_time": ..., # From created_at to lifecycle "approved"
        "quality_score_trend": [...],  # Quality scores over time
        "top_finding_categories": [...],
        "team_response_times": {...},  # Avg time from assignment to validation
    }
```

All data is already in SQLite — this is purely aggregation queries over existing tables.

2. **Frontend:** New `Analytics` page with charts (using existing charting patterns from `Dashboard.tsx`).

### Feature Flag
`FEATURE_REVIEW_ANALYTICS=true`

---

## Feature 11: GitHub PR Finding Sync

> **What:** When an approved PRD is implemented, link findings to GitHub PRs. When a PR is opened referencing a PRD review, surface relevant findings as PR comments.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `GitHubIntegration` | `src/context_graph/integrations/github.py` | Already clones repos, analyzes branches, handles PR numbers. Has `clone()` with `pr` parameter. |
| `CodebaseInput` | `src/context_graph/api/routes.py` | Already accepts `pr: Optional[int]` and `github_token`. |
| Review engine | `src/context_graph/security/review_engine.py` | Already runs full analysis on PR-scoped code via `--pr` flag. |
| `SecurityFinding` | `src/context_graph/core/models.py` | Has `source_reference` (file path), `recommendation`, `mitigations`. |
| Markdown report | `src/context_graph/reports/markdown_report.py` | Already generates markdown reports — can be formatted as PR comments. |

### Implementation

1. **Extend `GitHubIntegration`:** Add `post_pr_comment()` method using GitHub API.

```python
class GitHubIntegration:
    def post_pr_comment(self, repo: str, pr_number: int, body: str) -> None:
        """Post a comment on a GitHub PR."""
        # Uses existing self._session (requests session) + GitHub API
    
    def post_pr_review(self, repo: str, pr_number: int, findings: list[dict]) -> None:
        """Post inline review comments on affected files."""
        # Maps finding.source_reference to file paths in the PR diff
```

2. **New API endpoint:** `POST /api/reviews/{id}/sync-to-pr`

```python
@router.post("/reviews/{review_id}/sync-to-pr")
async def sync_findings_to_pr(review_id: str, request: SyncToPRRequest) -> dict:
    """Post review findings as comments on a GitHub PR."""
    review = await storage.get_review(review_id)
    github = GitHubIntegration(token=request.github_token)
    
    # Generate summary comment using existing MarkdownReportGenerator
    summary = MarkdownReportGenerator().generate(review)
    github.post_pr_comment(request.repo, request.pr_number, summary)
    
    # Post inline comments on specific files for high-severity findings
    for finding in review.all_findings:
        if finding.severity in (Severity.CRITICAL, Severity.HIGH) and finding.source_reference:
            github.post_pr_review(...)
```

3. **Frontend:** "Sync to PR" button in `ReviewDetail.tsx` — opens modal for repo/PR number, then pushes findings.

### Feature Flag
`FEATURE_GITHUB_PR_SYNC=true`

---

## Feature 12: Inline PRD Authoring with AI Assist

> **What:** A rich PRD editor with AI-powered inline suggestions — autocomplete entity names, surface existing APIs, warn about known patterns.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `State.api_endpoints` | `src/context_graph/core/models.py` | List of all API endpoints in codebase — can autocomplete endpoint names. |
| `State.data_models` | `src/context_graph/core/models.py` | List of all data models — can autocomplete model names. |
| `State.auth_patterns` | `src/context_graph/core/models.py` | Auth patterns — can suggest auth requirements. |
| `ContextGraph` | `src/context_graph/core/graph.py` | All entities and relationships — can suggest related components. |
| `PatternLearner` | `src/context_graph/pm/pattern_learner.py` | Learned patterns — can warn about known issues. |
| `NewReview` page | `frontend/src/pages/NewReview.tsx` | Already has a PRD textarea — extend with autocomplete. |

### Implementation

1. **New API endpoint:** `POST /api/autocomplete`

```python
@router.post("/autocomplete")
async def autocomplete(request: AutocompleteRequest) -> list[Suggestion]:
    """Return context-aware suggestions based on what the PM is typing."""
    # Query cached codebase State for matching entity/endpoint/model names
    # Query context graph for related entities
    # Query pattern learner for relevant warnings
    return [
        {"text": "user_preferences", "type": "data_model", "description": "Existing model in user_service"},
        {"text": "Rate limiting required", "type": "warning", "source": "pattern:12 past reviews flagged this"},
    ]
```

2. **Frontend:** Extend PRD textarea in `NewReview.tsx` with:
   - Autocomplete dropdown (triggered by typing known entity names)
   - Inline warning annotations (yellow underlines for pattern-matched concerns)
   - "Explain" tooltip: hover over a component name → see its description from `State.entities`

This is primarily a frontend enhancement backed by a lightweight API that queries existing cached `State` and `ContextGraph` data.

### Feature Flag
`FEATURE_PRD_AUTHORING_ASSIST=true`

---

## Feature 13: Compliance Audit Trail

> **What:** Immutable log of every review action for compliance evidence (SOC 2, HIPAA). Exportable audit reports.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `SQLiteCollaborationStorage` | `src/context_graph/storage/sqlite.py` | Already stores validations, comments, assignments, feedback, lifecycle transitions — all with timestamps. |
| `SQLiteReviewStorage` | `src/context_graph/storage/sqlite.py` | Already stores all reviews with findings, dimensions, results. |
| Compliance dimension | `src/context_graph/security/compliance_analyzer.py` | Already maps to SOC 2, HIPAA, PCI-DSS controls. `ComplianceFinding` has `control_id`, `framework`. |
| Markdown report | `src/context_graph/reports/markdown_report.py` | Already generates reports — extend with audit format. |

### Implementation

1. **New SQLite table:** `audit_log`

```sql
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    review_id TEXT,
    action TEXT NOT NULL,       -- "review_created", "finding_validated", "lifecycle_advanced", etc.
    actor TEXT NOT NULL,
    details_json TEXT,          -- Action-specific details
    created_at TEXT NOT NULL
);
CREATE INDEX idx_audit_log_review ON audit_log(review_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);
```

2. **Wire into existing endpoints:** Add audit log writes to existing collaboration routes. Every `validate_finding()`, `add_comment()`, `assign_finding()`, `submit_feedback()`, `update_lifecycle()` call already passes through `collaboration_routes.py` — add `audit_log.insert()` after each.

3. **New API endpoints:**
   - `GET /api/audit/reviews/{id}` — all actions for a review
   - `GET /api/audit/export?from=2026-01-01&to=2026-03-31&framework=soc2` — filtered export
   - `GET /api/audit/export/pdf` — PDF audit report

4. **Frontend:** Audit log viewer (simple table) accessible from `ReviewDetail.tsx` and a new `AuditExport` page.

### Feature Flag
`FEATURE_AUDIT_TRAIL=true`

---

## Feature 14: Product Health Overview

> **What:** Org-wide dashboard showing all active PRDs, aggregate risk posture, team workloads, and trending patterns.

### Grounding in Existing Code

| Existing Component | File | What It Provides |
|---|---|---|
| `list_reviews()` | `src/context_graph/api/routes.py` | Already returns all reviews with summary info. |
| `DashboardDataGenerator` | `src/context_graph/reports/json_report.py` | Already generates per-review dashboard data. |
| `Dashboard` page | `frontend/src/pages/Dashboard.tsx` | Already shows recent reviews — extend to org-wide view. |
| Team queue | `src/context_graph/api/collaboration_routes.py` | Already has `GET /teams/{team}/queue` — provides team workload data. |
| Collaboration stats | `src/context_graph/api/collaboration_routes.py` | Already has `GET /feedback/stats` — patterns, feedback counts. |

### Implementation

1. **New API endpoint:** `GET /api/overview`

```python
@router.get("/overview")
async def get_product_overview() -> dict:
    """Org-wide product health overview."""
    storage = get_review_storage()
    reviews = await storage.list_reviews()
    
    return {
        "active_prds": [r for r in reviews if r["status"] != "completed"],
        "risk_heatmap": {
            "security": {"critical": 2, "high": 5, ...},
            "privacy": {...},
            ...
        },
        "team_workloads": {
            "security": {"pending_reviews": 3, "pending_findings": 12},
            ...
        },
        "recent_decisions": [...],  # From decision_log table
        "trending_patterns": [...], # Most common finding categories
        "quality_trend": [...],     # Average quality scores over time
    }
```

All data comes from existing SQLite tables — this is aggregation and presentation.

2. **Frontend:** Extend `Dashboard.tsx` with org-wide cards, or create a new `ProductOverview` page with charts.

### Feature Flag
`FEATURE_PRODUCT_OVERVIEW=true`

---

## Prioritization Matrix

Scored on: **Impact** (PM workflow value), **Feasibility** (how much existing code is reused), **Effort** (estimated implementation days).

| # | Feature | Extends | Impact | Feasibility | Effort | Priority |
|---|---------|---------|--------|-------------|--------|----------|
| 1 | Product-Aware Chat | graph, storage, LLM providers | High | High | 3-4 days | **P0** |
| 4 | Formal PRD Review Requests | collaboration routes, lifecycle | High | Very High | 2-3 days | **P0** |
| 5 | Impact Graph Visualization | ContextGraph, review engine | High | High | 3-4 days | **P0** |
| 2 | Real-Time Analysis While Writing | parser, pattern matchers, quality scorer | High | Very High | 2-3 days | **P1** |
| 3 | PRD Version History & Diffing | prd_history_store, SideBySideDiffGenerator | High | Very High | 2-3 days | **P1** |
| 6 | Approval Gates & Policies | lifecycle, validation, quality scorer | Medium | Very High | 2 days | **P1** |
| 10 | Review Analytics Dashboard | SQLite storage (aggregation only) | Medium | Very High | 2 days | **P1** |
| 14 | Product Health Overview | list_reviews, team queues, feedback stats | Medium | Very High | 2 days | **P1** |
| 7 | Decision Log | collaboration storage pattern | Medium | Very High | 1-2 days | **P2** |
| 8 | Predictive Risk Scoring | review storage, pattern learner | Medium | High | 3-4 days | **P2** |
| 11 | GitHub PR Finding Sync | GitHubIntegration, markdown report | High | High | 3-4 days | **P2** |
| 9 | PRD Templates Library | PRDGenerator, quality scorer | Medium | High | 2-3 days | **P2** |
| 12 | Inline PRD Authoring with AI Assist | State, ContextGraph, NewReview.tsx | High | Medium | 4-5 days | **P2** |
| 13 | Compliance Audit Trail | collaboration routes, SQLite | Medium | High | 2-3 days | **P3** |

### Recommended Starting Point (P0)

These three features create the core "Cursor + GitHub for PMs" experience and have the highest feasibility because they wire together existing components:

1. **Product-Aware Chat (Feature 1):** Wraps existing `ContextGraph` queries + `SQLiteReviewStorage` queries + LLM providers into a conversational interface. ~90% existing code reuse.
2. **Formal PRD Review Requests (Feature 4):** Orchestrates existing lifecycle, team assignment, consensus, and cross-team request features into a unified workflow. ~95% existing code reuse.
3. **Impact Graph Visualization (Feature 5):** Exposes the existing NetworkX `ContextGraph` that's already built every review through a new D3.js frontend component. ~85% existing code reuse.

---

## Summary

**All 14 features are grounded in existing code.** No feature requires a new storage backend, a new LLM integration, or a new analysis engine. Every feature either:

- **Wires together** existing modules that aren't yet connected (Features 4, 6, 7, 13)
- **Adds a new API endpoint** that queries existing storage (Features 1, 8, 10, 14)
- **Adds a new frontend visualization** of existing backend data (Features 2, 3, 5, 12)
- **Extends an existing integration** with a complementary capability (Features 9, 11)

The existing codebase provides: PRD parsing, multi-language codebase analysis, context graph (NetworkX), 5-dimension review engine, pattern matching, LLM analysis (OpenAI + Anthropic), collaboration features (validation, comments, assignments, feedback, lifecycle, consensus), PM tools (quality scoring, effort estimation, PRD changes, side-by-side diff, PRD generation, bulk analysis), SQLite persistence, GitHub integration, feature flags, React frontend, and Electron desktop app.

These 14 features layer the PM-centric **workflow and experience** on top of that foundation — turning Intently from a powerful analysis tool into a daily-use workspace.

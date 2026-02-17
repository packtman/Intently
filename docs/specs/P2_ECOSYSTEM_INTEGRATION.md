# P2 — Ecosystem Integration

> **Priority:** P2
> **Estimated Effort:** 14–18 days total
> **Goal:** Make Intently the system of record — integrated with GitHub, equipped with templates, predictions, and decision tracking.

---

## Features in This Spec

| # | Feature | Extends | Effort |
|---|---------|---------|--------|
| 7 | Decision Log | CollaborationStorage pattern | 1–2 days |
| 8 | Predictive Risk Scoring | SQLiteReviewStorage, PatternLearner | 3–4 days |
| 9 | PRD Templates Library | PRDGenerator, quality scorer | 2–3 days |
| 11 | GitHub PR Finding Sync | GitHubIntegration, MarkdownReportGenerator | 3–4 days |
| 12 | Inline PRD Authoring with AI Assist | State, ContextGraph, NewReview.tsx | 4–5 days |

---

## Feature 7: Decision Log

### Overview

Append-only log attached to each review capturing key decisions, rationale, and links to findings. Auto-populated from review actions (validation, risk acceptance, lifecycle transitions).

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `CollaborationStorage` | `storage/base.py` | Abstract pattern — decision log follows same pattern as validations/comments |
| Finding validation | `collaboration_routes.py` | `accepted_risk`, `rejected` validations are decisions |
| Expert feedback | `collaboration_routes.py` | Expert corrections are decisions with reasoning |
| Lifecycle transitions | `collaboration_routes.py` | State changes with notes are decisions |
| `SQLiteCollaborationStorage` | `storage/sqlite.py` | Full SQLite persistence for all collaboration data |

### New SQLite Table

```sql
CREATE TABLE decision_log (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    decision_type TEXT NOT NULL,  -- "accepted_risk", "rejected_finding", "approved_prd",
                                  -- "scope_change", "deferred", "escalated"
    title TEXT NOT NULL,
    rationale TEXT,
    decided_by TEXT NOT NULL,
    decided_by_team TEXT,
    linked_finding_ids TEXT,      -- JSON array of finding IDs
    linked_comment_ids TEXT,      -- JSON array of comment IDs
    alternatives_considered TEXT, -- JSON array of strings
    created_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);
CREATE INDEX idx_decisions_review ON decision_log(review_id);
CREATE INDEX idx_decisions_type ON decision_log(decision_type);
CREATE INDEX idx_decisions_created ON decision_log(created_at);
```

### Auto-Population from Existing Actions

Wire into existing `collaboration_routes.py` endpoints — add decision log writes after:

```python
# In validate_finding endpoint, after saving validation:
if request.status in ("accepted_risk", "rejected"):
    await collab_storage.save_decision(
        review_id=review_id,
        decision_type=request.status,
        title=f"Finding {finding_id}: {request.status}",
        rationale=request.notes,
        decided_by=request.validator_id,
        linked_finding_ids=[finding_id],
    )

# In lifecycle endpoint, after state transition:
await collab_storage.save_decision(
    review_id=review_id,
    decision_type=f"lifecycle_{request.state}",
    title=f"PRD advanced to {request.state}",
    rationale=request.notes,
    decided_by=request.updated_by,
)
```

### New API Endpoints

```python
@router.post("/reviews/{review_id}/decisions")
async def add_decision(review_id: str, request: AddDecisionRequest) -> dict:
    """Manually log a decision."""

@router.get("/reviews/{review_id}/decisions")
async def list_decisions(review_id: str) -> list[dict]:
    """List all decisions for a review, chronologically."""

@router.get("/decisions/search")
async def search_decisions(q: str) -> list[dict]:
    """Full-text search across all decision logs."""
```

### Frontend Changes

- **New component:** `DecisionTimeline.tsx` — vertical timeline in `ReviewDetail.tsx`
- Each decision card shows: type icon, title, rationale, who decided, when, linked findings
- "Add Decision" button for manual entries
- Linked findings are clickable → scrolls to finding in the findings tab

### Feature Flag
`FEATURE_DECISION_LOG=true`

### Definition of Done
- [ ] Decision log persists in SQLite
- [ ] Auto-populated from finding validation (accepted_risk, rejected) and lifecycle transitions
- [ ] Manual decision entry via API
- [ ] Search across all reviews' decisions
- [ ] Timeline renders in ReviewDetail

---

## Feature 8: Predictive Risk Scoring

### Overview

Before writing a PRD, predict the likely risk profile based on the type of change and historical review data. Answers: "Based on 12 past PRDs touching payments, expect 3–5 security findings."

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `SQLiteReviewStorage` | `storage/sqlite.py` | `list_reviews()` + `get_review()` — full review history with findings |
| `PatternLearner` | `pm/pattern_learner.py` | Learned patterns from expert feedback |
| `DeltaAnalysisResult` | `security/delta_analyzer.py` | `introduces_pii`, `attack_surface_changes`, `auth_requirement_changes` |
| `ReviewResult` | `security/review_engine.py` | `findings_by_dimension`, `critical_count`, `high_count`, `all_findings` |
| `PRDQualityScorer` | `pm/quality_scorer.py` | Quality scoring — can be extended with prediction data |

### New File

```python
# src/context_graph/pm/risk_predictor.py

@dataclass
class RiskPrediction:
    predicted_findings: dict[str, int]       # {security: 3, privacy: 2, ...}
    predicted_severities: dict[str, int]     # {critical: 0, high: 2, medium: 4, ...}
    estimated_review_time: str               # "2-3 hours"
    suggested_reviewers: list[str]           # ["security", "privacy"]
    similar_reviews: list[dict]              # [{id, title, findings_count, similarity}]
    confidence: float                        # 0.0-1.0
    risk_level: str                          # "low", "medium", "high", "critical"

class RiskPredictor:
    def __init__(self, review_storage: SQLiteReviewStorage):
        self.review_storage = review_storage

    async def predict(
        self,
        feature_description: str,
        affected_systems: list[str] | None = None,
        change_type: str | None = None,  # "new_feature", "api_change", "data_migration"
    ) -> RiskPrediction:
        """Predict risk profile from historical reviews."""
        # 1. Load all completed reviews
        reviews = await self.review_storage.list_reviews()

        # 2. Score similarity: match by keywords in intent.features,
        #    affected systems, and change type
        scored = []
        for r in reviews:
            review = await self.review_storage.get_review(r["review_id"])
            if review:
                similarity = self._compute_similarity(
                    feature_description, affected_systems,
                    review.intent.features, review.delta_result
                )
                scored.append((similarity, review))

        # 3. Take top-N similar reviews
        similar = sorted(scored, key=lambda x: x[0], reverse=True)[:5]

        # 4. Aggregate finding distributions across similar reviews
        # 5. Compute confidence based on number of similar reviews
        ...

    def _compute_similarity(self, desc, systems, features, delta) -> float:
        """Keyword overlap + entity match scoring."""
        # Simple: count overlapping terms between description and past features
        # Bonus: match affected_systems to delta.affected_components
        ...
```

### New API Endpoint

```python
@router.post("/predict-risk")
@requires_feature("risk_prediction")
async def predict_risk(request: PredictRiskRequest) -> dict:
    """Predict risk for a planned feature."""
    predictor = RiskPredictor(get_review_storage())
    prediction = await predictor.predict(
        feature_description=request.description,
        affected_systems=request.affected_systems,
        change_type=request.change_type,
    )
    return {
        "predicted_findings": prediction.predicted_findings,
        "predicted_severities": prediction.predicted_severities,
        "estimated_review_time": prediction.estimated_review_time,
        "suggested_reviewers": prediction.suggested_reviewers,
        "similar_reviews": prediction.similar_reviews,
        "confidence": prediction.confidence,
        "risk_level": prediction.risk_level,
    }
```

### Frontend Changes

- New section at top of `NewReview.tsx`: "Risk Preview"
- PM enters a 1–2 sentence feature description + optionally selects affected systems
- Displays predicted findings by dimension, suggested reviewers, similar past reviews
- Similar reviews are clickable → links to their ReviewDetail page

### Feature Flag
`FEATURE_RISK_PREDICTION=true`

### Definition of Done
- [ ] `POST /api/predict-risk` returns predictions based on historical reviews
- [ ] Similarity scoring uses keyword overlap + entity matching
- [ ] Predictions include cited similar reviews
- [ ] Risk preview renders in NewReview page
- [ ] Confidence score reflects number of similar past reviews

---

## Feature 9: PRD Templates Library

### Overview

Organization-specific PRD templates with required sections and pre-filled boilerplate. Templates evolve based on review patterns.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `PRDGenerator` | `pm/prd_generator.py` | Generates PRD sections from codebase. `GeneratedSection` model. |
| `PRDQualityScorer` | `pm/quality_scorer.py` | Identifies gaps — informs which sections templates need |
| PRDGenerator API | `api/prd_generator_routes.py` | `POST /api/prd-generator/generate` endpoint |
| PRDGenerator page | `frontend/src/pages/PRDGenerator.tsx` | UI for generating PRDs from codebases |
| `FEATURE_PRD_GENERATOR` | `config/features.py` | Existing feature flag |

### New File

```python
# src/context_graph/pm/template_library.py

@dataclass
class TemplateSection:
    title: str                    # "Security Considerations"
    required: bool = False
    guidance: str = ""            # Help text for PMs
    boilerplate: str = ""         # Pre-filled content

@dataclass
class PRDTemplate:
    id: str
    name: str                     # "New Feature", "API Change", "Data Migration"
    description: str
    category: str                 # "feature", "api", "migration", "integration", "deprecation"
    sections: list[TemplateSection] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)  # For auto-suggestion

class TemplateLibrary:
    BUILT_IN_TEMPLATES = [
        PRDTemplate(
            id="new-feature",
            name="New Feature",
            category="feature",
            description="Standard template for new product features",
            sections=[
                TemplateSection("Overview", required=True, guidance="What does this feature do?"),
                TemplateSection("User Stories", required=True),
                TemplateSection("Technical Requirements", required=True),
                TemplateSection("API Changes", required=False),
                TemplateSection("Data Model Changes", required=False),
                TemplateSection("Security Considerations", required=True,
                                guidance="Auth, data access, trust boundaries"),
                TemplateSection("Privacy Impact", required=False,
                                guidance="PII, data flows, consent"),
                TemplateSection("Rollback Plan", required=True,
                                guidance="How to revert if issues arise"),
                TemplateSection("Acceptance Criteria", required=True),
            ],
            keywords=["feature", "new", "add", "implement"],
        ),
        PRDTemplate(
            id="api-change",
            name="API Change",
            category="api",
            ...
        ),
        PRDTemplate(
            id="data-migration",
            name="Data Migration",
            category="migration",
            ...
        ),
    ]

    def __init__(self, storage=None):
        self.storage = storage  # For org-specific templates from SQLite

    def get_all_templates(self) -> list[PRDTemplate]:
        """Return built-in + org-specific templates."""

    def suggest_template(self, prd_content: str) -> PRDTemplate | None:
        """Suggest template based on content keywords."""
        # Match prd_content words against template keywords

    def render_template(self, template_id: str) -> str:
        """Render template as markdown with section headers and guidance."""
```

### New SQLite Table

```sql
CREATE TABLE prd_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    sections_json TEXT NOT NULL,  -- JSON array of TemplateSection
    keywords_json TEXT,           -- JSON array for suggestion matching
    created_by TEXT,
    usage_count INTEGER DEFAULT 0,
    avg_quality_score REAL,       -- Average quality score of PRDs using this template
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### New API Endpoints

```python
@router.get("/templates")
async def list_templates() -> list[dict]:
    """List all available templates (built-in + org-specific)."""

@router.get("/templates/{template_id}/render")
async def render_template(template_id: str) -> dict:
    """Render a template as pre-filled markdown."""

@router.post("/templates")
async def create_template(request: CreateTemplateRequest) -> dict:
    """Create an org-specific template."""

@router.get("/templates/suggest")
async def suggest_template(content: str) -> dict | None:
    """Suggest a template based on PRD content."""
```

### Frontend Changes

- **Template picker** in `NewReview.tsx`: before the PRD textarea, show a template carousel
- Click template → PRD textarea populates with rendered template markdown
- Template suggestion toast: "This looks like a data migration — try the Data Migration template?"
- Template management page (for org admins): create/edit/delete custom templates

### Feature Flag
`FEATURE_PRD_TEMPLATES=true`

### Definition of Done
- [ ] Built-in templates for common PRD types (new feature, API change, data migration)
- [ ] Templates render as markdown with section headers and guidance
- [ ] Template suggestion based on content keywords
- [ ] Org-specific templates persist in SQLite
- [ ] Template picker renders in NewReview page

---

## Feature 11: GitHub PR Finding Sync

### Overview

Push review findings to GitHub PRs as comments. When a PR references a PRD review, surface relevant findings as inline review comments on affected files.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `GitHubIntegration` | `integrations/github.py` | Clones repos, handles branches/PRs. Has `_session` (requests session) + auth. |
| `CodebaseInput` | `api/routes.py` | Already accepts `pr: Optional[int]` and `github_token` |
| `MarkdownReportGenerator` | `reports/markdown_report.py` | Generates full markdown reports — reuse for PR comments |
| `SecurityFinding.source_reference` | `core/models.py` | File path where finding originated — maps to PR diff files |
| `ReviewResult` | `security/review_engine.py` | Full review with findings, dimensions, summary |

### Extend GitHubIntegration

```python
# In src/context_graph/integrations/github.py — add methods:

class GitHubIntegration:
    # ... existing clone/fetch methods ...

    def post_pr_comment(self, repo: str, pr_number: int, body: str) -> dict:
        """Post a summary comment on a GitHub PR."""
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        response = self._session.post(url, json={"body": body})
        response.raise_for_status()
        return response.json()

    def post_pr_review(
        self,
        repo: str,
        pr_number: int,
        findings: list[dict],
        commit_sha: str,
    ) -> dict:
        """Post inline review comments on specific files in a PR."""
        comments = []
        for finding in findings:
            if finding.get("file_path") and finding.get("line"):
                comments.append({
                    "path": finding["file_path"],
                    "line": finding["line"],
                    "body": f"**[{finding['dimension']}] {finding['title']}** "
                            f"({finding['severity']})\n\n"
                            f"{finding['description']}\n\n"
                            f"**Recommendation:** {finding['recommendation']}",
                })
        if comments:
            url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
            response = self._session.post(url, json={
                "commit_id": commit_sha,
                "event": "COMMENT",
                "comments": comments,
            })
            response.raise_for_status()
            return response.json()
        return {}

    def get_pr_files(self, repo: str, pr_number: int) -> list[dict]:
        """Get list of files changed in a PR — for mapping findings to diff."""
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        response = self._session.get(url)
        response.raise_for_status()
        return response.json()
```

### New API Endpoint

```python
# In src/context_graph/api/routes.py

class SyncToPRRequest(BaseModel):
    repo: str           # "owner/repo"
    pr_number: int
    github_token: str | None = None
    include_inline: bool = True  # Post inline comments on files
    min_severity: str = "medium" # Only sync findings at this severity or above

@router.post("/reviews/{review_id}/sync-to-pr")
@requires_feature("github_pr_sync")
async def sync_to_pr(review_id: str, request: SyncToPRRequest) -> dict:
    """Push review findings to a GitHub PR."""
    review = await storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404)

    github = GitHubIntegration(
        token=request.github_token or os.getenv("GITHUB_TOKEN")
    )

    # 1. Post summary comment using existing MarkdownReportGenerator
    summary = MarkdownReportGenerator().generate_summary(review)
    github.post_pr_comment(request.repo, request.pr_number, summary)

    # 2. Map findings to PR files for inline comments
    if request.include_inline:
        pr_files = github.get_pr_files(request.repo, request.pr_number)
        pr_file_paths = {f["filename"] for f in pr_files}

        inline_findings = []
        for finding in review.all_findings:
            if (finding.source_reference and
                finding.source_reference in pr_file_paths and
                finding.severity.value >= request.min_severity):
                inline_findings.append({...})

        if inline_findings:
            github.post_pr_review(request.repo, request.pr_number, inline_findings, ...)

    return {"summary_posted": True, "inline_comments": len(inline_findings)}
```

### Frontend Changes

- **"Sync to PR" button** in `ReviewDetail.tsx` header
- Opens modal: enter repo name + PR number (or paste PR URL)
- Preview of what will be posted (summary + inline comments)
- Success confirmation with link to PR

### Feature Flag
`FEATURE_GITHUB_PR_SYNC=true`

### Definition of Done
- [ ] `post_pr_comment()` posts markdown summary to GitHub PR
- [ ] `post_pr_review()` posts inline comments on affected files
- [ ] Finding `source_reference` maps to PR diff file paths
- [ ] Severity filter controls which findings are synced
- [ ] "Sync to PR" button and modal work in frontend

---

## Feature 12: Inline PRD Authoring with AI Assist

### Overview

Extend the PRD editor in `NewReview.tsx` with context-aware autocomplete and inline warnings. When the PM types a component name, suggest related entities from the codebase. When they mention data handling, warn about known patterns.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `State.api_endpoints` | `core/models.py` | All API endpoints — autocomplete endpoint names |
| `State.data_models` | `core/models.py` | All data models — autocomplete model names |
| `State.auth_patterns` | `core/models.py` | Auth patterns — suggest auth requirements |
| `State.entities` | `core/models.py` | All discovered entities — autocomplete entity names |
| `ContextGraph` | `core/graph.py` | Relationships between entities — suggest related components |
| `PatternLearner` | `pm/pattern_learner.py` | Learned patterns — warn about known issues |
| `NewReview` page | `frontend/src/pages/NewReview.tsx` | PRD textarea — extend with autocomplete |

### New API Endpoint

```python
@router.post("/autocomplete")
@requires_feature("prd_authoring_assist")
async def autocomplete(request: AutocompleteRequest) -> list[dict]:
    """Context-aware suggestions for the PRD editor."""
    # Load cached State from most recent review or codebase analysis
    state = get_cached_state()
    suggestions = []

    query = request.current_word.lower()

    # Match against entity names
    for entity in state.entities:
        if query in entity.name.lower():
            suggestions.append({
                "text": entity.name,
                "type": entity.entity_type.value,
                "description": entity.description or f"{entity.entity_type.value} in {entity.source}",
                "category": "entity",
            })

    # Match against API endpoints
    for endpoint in state.api_endpoints:
        path = endpoint.get("path", "")
        if query in path.lower():
            suggestions.append({
                "text": path,
                "type": "endpoint",
                "description": f"{endpoint.get('method', 'GET')} {path}",
                "category": "api",
            })

    # Match against data models
    for model in state.data_models:
        name = model.get("name", "")
        if query in name.lower():
            suggestions.append({
                "text": name,
                "type": "data_model",
                "description": f"Data model in {model.get('file', '')}",
                "category": "model",
            })

    # Pattern warnings
    for pattern in pattern_learner.learned_patterns:
        if any(term in request.context.lower() for term in pattern.applies_when.split()):
            suggestions.append({
                "text": pattern.pattern_description,
                "type": "warning",
                "description": f"Pattern from {pattern.times_applied} past reviews",
                "category": "warning",
            })

    return suggestions[:10]  # Limit to top 10
```

### Frontend Changes

- **Extend PRD textarea** in `NewReview.tsx`:
  - Autocomplete dropdown (triggers on 3+ characters matching known entities)
  - Entity suggestions show type icon (API 🔌, model 📦, service ⚙️)
  - Warning suggestions show ⚠️ with pattern description
  - Tab to accept suggestion, Esc to dismiss
- **Inline annotations:** yellow underline on text matching warning patterns
- **"Explain" tooltip:** hover over entity name → popover with entity details from State

### Feature Flag
`FEATURE_PRD_AUTHORING_ASSIST=true`

### Definition of Done
- [ ] `POST /api/autocomplete` returns suggestions from cached State
- [ ] Entity, endpoint, and model names appear as autocomplete suggestions
- [ ] Pattern warnings surface when typing about known concern areas
- [ ] Autocomplete dropdown works in PRD editor with keyboard navigation
- [ ] Suggestions are scoped to the most recent codebase analysis

---

## Shared Implementation Notes

### Dependency Order

These features are largely independent, but optimal ordering is:

1. **Decision Log** (Feature 7) — simplest, no dependencies
2. **PRD Templates** (Feature 9) — extends PRDGenerator
3. **GitHub PR Sync** (Feature 11) — extends GitHubIntegration
4. **Predictive Risk Scoring** (Feature 8) — needs review history to be useful
5. **Inline PRD Authoring** (Feature 12) — benefits from having templates and cached state

### Feature Flags

Add to `src/context_graph/config/features.py`:

```python
# P2: Ecosystem Integration
enable_decision_log: bool = False
enable_risk_prediction: bool = False
enable_prd_templates: bool = False
enable_github_pr_sync: bool = False
enable_prd_authoring_assist: bool = False
```

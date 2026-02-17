# P0 — Core PM Experience

> **Priority:** P0 (highest)
> **Estimated Effort:** 8–11 days total
> **Goal:** Create the core "Cursor + GitHub for PMs" daily-use loop: ask questions → write PRDs → request structured reviews.

---

## Features in This Spec

| # | Feature | Extends | Effort |
|---|---------|---------|--------|
| 1 | Product-Aware Chat | `ContextGraph`, `SQLiteReviewStorage`, LLM providers | 3–4 days |
| 4 | Formal PRD Review Requests | collaboration routes, lifecycle, team assignment | 2–3 days |
| 5 | Impact Graph Visualization | `ContextGraph`, `review_engine._build_graph()` | 3–4 days |

Together these three features turn Intently from a one-shot analysis tool into a **daily workspace** where PMs open Intently → ask questions → write PRDs → request reviews → track approvals.

---

## Feature 1: Product-Aware Chat

### Overview

A conversational AI interface embedded in the workspace where PMs ask natural-language questions about their product, codebase, past reviews, and organizational patterns — with answers grounded in actual data.

### What Exists Today

| Component | File | Capability |
|---|---|---|
| `ContextGraph` | `src/context_graph/core/graph.py` | `get_entities_by_type()`, `get_sensitive_entities()`, `find_unauthenticated_paths()`, `find_trust_boundary_crossings()`, `compute_risk_score()` |
| `SQLiteReviewStorage` | `src/context_graph/storage/sqlite.py` | `list_reviews()`, `get_review()` — full review history with findings |
| `SQLiteCollaborationStorage` | `src/context_graph/storage/sqlite.py` | Feedback stats, validation history, comments, patterns |
| `ParallelLLMAnalyzer` | `src/context_graph/llm/parallel_analyzer.py` | OpenAI + Anthropic dual-provider setup, already configured |
| `PatternLearner` | `src/context_graph/pm/pattern_learner.py` | `learned_patterns` list — what the system has learned from experts |
| LLM providers | `src/context_graph/llm/openai_provider.py`, `anthropic_provider.py` | Chat completion wrappers already exist |

### New Files

#### `src/context_graph/chat/product_chat.py`

```python
class ProductChat:
    """Conversational AI grounded in product context."""

    def __init__(
        self,
        review_storage: SQLiteReviewStorage,
        collaboration_storage: SQLiteCollaborationStorage,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
    ):
        self.review_storage = review_storage
        self.collab_storage = collaboration_storage
        # Reuse existing LLM provider classes
        self.llm = ...

    async def answer(self, question: str, review_id: str | None = None) -> ChatResponse:
        """Answer a question using product context."""
        # 1. Classify question intent (entity query, review history, pattern lookup, general)
        # 2. Gather relevant context from storage
        # 3. Build grounded prompt with citations
        # 4. Send to LLM provider
        # 5. Return answer with citations

    async def _gather_context(self, question: str, review_id: str | None) -> dict:
        """Query existing storage for relevant context."""
        context = {}

        # Query review history
        reviews = await self.review_storage.list_reviews()
        context["recent_reviews"] = reviews[:10]

        # If scoped to a review, load its graph/findings
        if review_id:
            review = await self.review_storage.get_review(review_id)
            if review:
                context["current_findings"] = [...]
                context["quality_score"] = review.prd_quality_score

        # Query collaboration data
        context["feedback_stats"] = await self.collab_storage.get_feedback_stats()

        return context
```

#### `src/context_graph/api/chat_routes.py`

```python
router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    question: str
    review_id: str | None = None   # Optional: scope to a specific review
    conversation_id: str | None = None  # For multi-turn conversations

class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]   # [{"type": "review", "id": "...", "text": "..."}]
    suggested_followups: list[str]

@router.post("/chat")
@requires_feature("product_chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Answer product questions using context graph + review history + LLM."""
    ...
```

### Frontend Changes

- **New component:** `frontend/src/components/ChatPanel.tsx` — collapsible side panel with message history, input box, citation links
- **Integration point:** Add to `ReviewDetail.tsx` sidebar and as a global floating button in `Layout.tsx`
- **Keyboard shortcut:** `Cmd+L` (matching Cursor's convention) opens the chat panel

### Example Queries → Data Sources

| Query | Data Source | Existing Method |
|---|---|---|
| "What services access PII?" | ContextGraph | `get_entities_by_type(EntityType.PII)` + relationships |
| "What did security flag last review?" | ReviewStorage | `get_review(id)` → `security_findings` |
| "How many times was rate limiting flagged?" | ReviewStorage | `list_reviews()` → scan all findings |
| "What patterns has the system learned?" | PatternLearner | `learned_patterns` list |
| "What's the risk score for auth_service?" | ContextGraph | `compute_risk_score(entity_id)` |
| "Who validated finding F-123?" | CollaborationStorage | `get_finding_validation()` |

### Feature Flag

`FEATURE_PRODUCT_CHAT=true`

### Definition of Done

- [ ] `POST /api/chat` endpoint works with question → answer + citations
- [ ] Answers reference actual review data (review IDs, finding titles, entity names)
- [ ] Multi-turn conversation maintains context
- [ ] Chat panel renders in frontend with citation links
- [ ] Works with both OpenAI and Anthropic providers

---

## Feature 4: Formal PRD Review Requests

### Overview

PMs submit a PRD for structured review with designated reviewers, deadlines, and tracked status — the PM equivalent of a GitHub Pull Request. This feature **orchestrates existing collaboration building blocks** into a unified workflow.

### What Exists Today

| Component | File | Capability |
|---|---|---|
| Review lifecycle | `collaboration_routes.py` | State machine: `draft → in_review → team_review → awaiting_signoff → approved / blocked`. Feature: `FEATURE_REVIEW_LIFECYCLE` |
| Cross-team requests | `collaboration_routes.py` | `POST /reviews/{id}/requests` — request input from teams with deadlines. Feature: `FEATURE_CROSS_TEAM_REQUESTS` |
| Team assignment | `collaboration_routes.py` | `POST /reviews/{id}/findings/{id}/assign` — route to team queues. Feature: `FEATURE_TEAM_ASSIGNMENT` |
| Consensus mode | `collaboration_routes.py` | Multi-team approval voting. Feature: `FEATURE_CONSENSUS_MODE` |
| Finding validation | `collaboration_routes.py` | Validate/reject/needs_discussion per finding. Feature: `FEATURE_FINDING_VALIDATION` |
| Team queue page | `frontend/src/pages/TeamQueue.tsx` | Shows team's assigned findings |
| Collaboration storage | `src/context_graph/storage/sqlite.py` | `SQLiteCollaborationStorage` — all collaboration data persists |

### New Data Model

```python
@dataclass
class PRDReviewRequest:
    """A formal request for PRD review — wraps existing lifecycle + assignment."""
    id: UUID = field(default_factory=uuid4)
    review_id: str = ""                      # Links to existing ReviewResult
    requested_by: str = ""                   # PM who submitted
    title: str = ""                          # PRD title
    description: str = ""                    # Optional context for reviewers
    reviewers: list[dict] = field(default_factory=list)
    # Each reviewer: {"team": "security", "user_id": "optional", "required": True}
    deadline: datetime | None = None
    status: str = "open"                     # open, changes_requested, approved, blocked
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
```

### New SQLite Tables

```sql
CREATE TABLE review_requests (
    id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);
CREATE INDEX idx_review_requests_review ON review_requests(review_id);
CREATE INDEX idx_review_requests_status ON review_requests(status);

CREATE TABLE review_request_reviewers (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    team TEXT NOT NULL,
    user_id TEXT,
    required BOOLEAN DEFAULT TRUE,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, changes_requested, blocked
    responded_at TEXT,
    notes TEXT,
    FOREIGN KEY (request_id) REFERENCES review_requests(id)
);
CREATE INDEX idx_reviewers_request ON review_request_reviewers(request_id);
CREATE INDEX idx_reviewers_team ON review_request_reviewers(team);
```

### New API Endpoints

```python
# In src/context_graph/api/review_request_routes.py

@router.post("/reviews/{review_id}/request-review")
async def create_review_request(review_id: str, request: CreateReviewRequest):
    """Create a formal review request. Orchestrates:
    1. Create review_request record
    2. Advance lifecycle to 'in_review' (existing endpoint)
    3. Auto-assign findings to reviewer teams (existing team assignment)
    4. Create cross-team requests for each reviewer (existing endpoint)
    """

@router.get("/reviews/{review_id}/review-request")
async def get_review_request(review_id: str):
    """Get review request status: who approved, who's pending, deadline."""

@router.post("/reviews/{review_id}/review-request/approve")
async def approve_review(review_id: str, request: ApproveRequest):
    """Reviewer approves. When all required reviewers approve:
    1. Update reviewer status
    2. If all required approved → advance lifecycle to 'approved'
    3. If any blocked → advance lifecycle to 'blocked'
    """

@router.get("/review-requests/pending")
async def list_pending_requests():
    """List all open review requests (reviewer's inbox)."""
```

### Frontend Changes

- **New component:** `frontend/src/components/ReviewRequestPanel.tsx`
  - Reviewer list with status badges (pending ⏳, approved ✅, changes requested 🔄, blocked ❌)
  - Deadline countdown
  - Overall progress bar
  - "Request Review" button (opens reviewer picker modal)
- **Extend `ReviewDetail.tsx`:** Add ReviewRequestPanel at the top when a review request exists
- **New page:** `frontend/src/pages/ReviewInbox.tsx` — reviewer's pending reviews (like GitHub's PR review inbox)

### Workflow

```
PM writes PRD → Submits for review → Selects reviewers + deadline
                                          ↓
                              ┌─────────────────────────┐
                              │   Auto-assigns findings  │ (existing team assignment)
                              │   Advances lifecycle     │ (existing lifecycle)
                              │   Creates team requests  │ (existing cross-team requests)
                              └─────────────────────────┘
                                          ↓
                              Reviewers see in their inbox
                                          ↓
                              Each reviewer: approve / request changes / block
                                          ↓
                              All required approved? → PRD approved
                              Any blocked? → PRD blocked with reasons
```

### Feature Flag

`FEATURE_REVIEW_REQUESTS=true` (depends on `FEATURE_REVIEW_LIFECYCLE` + `FEATURE_TEAM_ASSIGNMENT`)

### Definition of Done

- [ ] `POST /reviews/{id}/request-review` creates review request and orchestrates existing collaboration features
- [ ] Reviewer approval/blocking tracked per reviewer with notes
- [ ] Auto-advance lifecycle when all required reviewers approve
- [ ] Reviewer inbox page shows pending reviews
- [ ] ReviewRequestPanel shows in ReviewDetail with live status

---

## Feature 5: Impact Graph Visualization

### Overview

Interactive D3.js visualization of the context graph showing entities, relationships, data flows, trust boundaries, and blast radius of proposed changes. The graph is **already built every review** — this feature exposes it visually.

### What Exists Today

| Component | File | Capability |
|---|---|---|
| `ContextGraph` | `src/context_graph/core/graph.py` | NetworkX `DiGraph` with entities, relationships, traversal. Methods: `add_entity()`, `add_relationship()`, `get_entities_by_type()`, `get_sensitive_entities()`, `find_unauthenticated_paths()`, `find_trust_boundary_crossings()`, `compute_risk_score()`, `iter_entities()` |
| `Entity` model | `src/context_graph/core/models.py` | 16 entity types: USER, DATA, PII, SECRET, API, ENDPOINT, SERVICE, DATABASE, QUEUE, FUNCTION, CLASS, MODULE, AUTH_PROVIDER, TRUST_BOUNDARY, SECURITY_CONTROL |
| `Relationship` model | `src/context_graph/core/models.py` | 16 relationship types: READS, WRITES, FLOWS_TO, TRANSFORMS, AUTHENTICATES, AUTHORIZES, OWNS, ACCESSES, TRUSTS, VALIDATES, SANITIZES, CONTAINS, CALLS, DEPENDS_ON, IMPLEMENTS |
| `_build_graph()` | `review_engine.py` line 1214 | Builds graph from Intent + State + Delta entities every review |
| `_analyze_graph()` | `review_engine.py` line 1391 | Queries graph for unauthenticated paths, boundary crossings, high-risk entities |
| `DashboardDataGenerator` | `reports/json_report.py` | Already serializes review data to JSON for frontend |
| `Delta.affected_components` | `core/models.py` | List of components affected by the PRD change — used for blast radius |

### New API Endpoint

```python
# In src/context_graph/api/routes.py

@router.get("/reviews/{review_id}/graph")
async def get_review_graph(review_id: str) -> dict:
    """Return context graph data for visualization.

    Reconstructs the graph from the review's Intent + State + Delta
    and returns nodes/edges in D3-compatible format.
    """
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Rebuild graph using existing _build_graph() logic
    graph = ContextGraph()
    for entity in review.state.entities:
        graph.add_entity(entity)
    for rel in review.state.relationships:
        graph.add_relationship(rel)
    for entity in review.intent.data_entities:
        graph.add_entity(entity)
    if review.delta_result:
        for entity in review.delta_result.delta.new_entities:
            graph.add_entity(entity)

    # Serialize to D3-compatible format
    nodes = []
    for entity in graph.iter_entities():
        nodes.append({
            "id": str(entity.id),
            "name": entity.name,
            "type": entity.entity_type.value,
            "sensitive": entity.is_sensitive,
            "requires_auth": entity.requires_auth,
            "trust_level": entity.trust_level,
            "source": entity.source,
            "risk_score": graph.compute_risk_score(entity.id),
            "is_new": entity in (review.delta_result.delta.new_entities if review.delta_result else []),
        })

    edges = []
    for rel in graph.iter_relationships():
        edges.append({
            "source": str(rel.source_id),
            "target": str(rel.target_id),
            "type": rel.relationship_type.value,
            "crosses_boundary": rel.crosses_trust_boundary,
            "requires_encryption": rel.requires_encryption,
        })

    # Graph analysis results (already computed by review engine)
    analysis = {
        "unauthenticated_paths": len(graph.find_unauthenticated_paths()),
        "trust_boundary_crossings": len(graph.find_trust_boundary_crossings()),
        "high_risk_entities": [str(e.id) for e in graph.iter_entities()
                               if graph.compute_risk_score(e.id) > 70],
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "analysis": analysis,
        "stats": {
            "total_entities": len(nodes),
            "total_relationships": len(edges),
            "entity_types": {t: sum(1 for n in nodes if n["type"] == t)
                            for t in set(n["type"] for n in nodes)},
        },
    }
```

### Frontend Component

**New file:** `frontend/src/components/ImpactGraph.tsx`

Uses D3.js force-directed graph layout:

- **Nodes** colored by entity type:
  - PII / SECRET → red
  - API / ENDPOINT → blue
  - SERVICE → green
  - DATABASE → purple
  - USER → orange
  - New entities (from delta) → pulsing glow animation
- **Edges** styled by relationship type:
  - `crosses_trust_boundary` → red dashed line
  - `requires_encryption` → thick line
  - Data flow relationships → arrows
- **Interactions:**
  - Click node → sidebar shows entity details, linked findings, risk score
  - Hover edge → tooltip with relationship type
  - "Blast radius" toggle → highlights `delta.affected_components` + connected nodes
  - Filters dropdown: "Show only PII paths", "Show only external-facing", "Show only new entities"
  - Zoom/pan with mouse
- **Integration:** New tab in `ReviewDetail.tsx` alongside "Findings", "PRD Changes", "Trace Log"

### Feature Flag

`FEATURE_IMPACT_GRAPH=true`

### Definition of Done

- [ ] `GET /api/reviews/{id}/graph` returns D3-compatible node/edge data
- [ ] Force-directed graph renders with colored nodes and styled edges
- [ ] Click node shows entity details + linked findings in sidebar
- [ ] "Blast radius" toggle highlights affected entities
- [ ] Filters work: PII paths, external-facing, new entities only
- [ ] Graph analysis stats shown: unauthenticated paths, boundary crossings, high-risk entities

---

## Shared Implementation Notes

### Feature Flag Registration

Add to `src/context_graph/config/features.py`:

```python
# P0: Core PM Experience
enable_product_chat: bool = False
enable_review_requests: bool = False
enable_impact_graph: bool = False
```

And corresponding `from_env()` entries:

```python
enable_product_chat=_env_bool("FEATURE_PRODUCT_CHAT"),
enable_review_requests=_env_bool("FEATURE_REVIEW_REQUESTS"),
enable_impact_graph=_env_bool("FEATURE_IMPACT_GRAPH"),
```

### Router Registration

In `src/context_graph/api/main.py`, add:

```python
from context_graph.api.chat_routes import router as chat_router
from context_graph.api.review_request_routes import router as review_request_router

app.include_router(chat_router, prefix="/api")
app.include_router(review_request_router, prefix="/api")
```

### Frontend Dependencies

```bash
cd frontend && npm install d3 @types/d3  # For Impact Graph
```

### Testing Strategy

- **Unit tests:** `src/context_graph/tests/test_product_chat.py`, `test_review_requests.py`
- **API tests:** Test endpoints with mocked storage
- **Frontend tests:** Component tests for ChatPanel, ReviewRequestPanel, ImpactGraph

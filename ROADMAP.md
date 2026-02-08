# Intently — Engineering Roadmap

## Current State

Intently performs AI-powered pre-code reviews by parsing PRDs, analyzing codebases, and generating multi-dimensional findings (Security, Privacy, Compliance, Engineering, Architecture). The core review pipeline is functional end-to-end.

### What's Built
- PRD parsing → structured `Intent` (features, entities, API changes, auth requirements)
- Multi-language codebase analysis → `State` (Python, TypeScript, Kotlin, YAML, JSON)
- Delta computation (Intent vs. State)
- In-memory context graph (NetworkX) with security analysis methods
- Multi-dimension analysis: pattern matching (STRIDE/OWASP) + optional LLM analysis
- SQLite storage for reviews, findings, collaboration data
- Collaboration features: validation, comments, assignments, feedback, lifecycle, consensus
- PM features: predicted questions, PRD quality scoring, effort estimation
- Web UI (FastAPI) + Desktop app (Electron)
- CLI: `review`, `parse`, `analyze`, `serve`

### What's Missing
- Context graph is **ephemeral** — rebuilt per review, not persisted
- Expert Tokens / PatternLearner uses **in-memory storage** — lost on restart
- Learned patterns are **not injected** into the core review engine
- No **feedback loop** — expert corrections don't improve future reviews
- No **cross-review intelligence** — each review is independent
- Pattern matching is **string-based** — no semantic similarity

---

## Phase 1: Persistent Context Graph

**Goal:** The context graph survives across reviews, building a living picture of the organization's architecture.

**Why first:** Everything else depends on having persistent, cumulative knowledge of entities and relationships.

### Tasks

#### 1.1 New SQLite tables for graph persistence

Add `graph_entities` and `graph_relationships` tables.

```sql
CREATE TABLE graph_entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    description TEXT,
    properties_json TEXT,
    source TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    requires_auth BOOLEAN DEFAULT FALSE,
    trust_level INTEGER DEFAULT 5,
    first_seen_review_id TEXT NOT NULL,
    last_seen_review_id TEXT NOT NULL,
    times_seen INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (first_seen_review_id) REFERENCES reviews(id),
    FOREIGN KEY (last_seen_review_id) REFERENCES reviews(id)
);
CREATE INDEX idx_graph_entities_type ON graph_entities(entity_type);
CREATE INDEX idx_graph_entities_name ON graph_entities(name);

CREATE TABLE graph_relationships (
    id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    properties_json TEXT,
    crosses_trust_boundary BOOLEAN DEFAULT FALSE,
    requires_encryption BOOLEAN DEFAULT FALSE,
    first_seen_review_id TEXT NOT NULL,
    last_seen_review_id TEXT NOT NULL,
    times_seen INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_entity_id) REFERENCES graph_entities(id),
    FOREIGN KEY (target_entity_id) REFERENCES graph_entities(id),
    FOREIGN KEY (first_seen_review_id) REFERENCES reviews(id),
    FOREIGN KEY (last_seen_review_id) REFERENCES reviews(id)
);
CREATE INDEX idx_graph_relationships_source ON graph_relationships(source_entity_id);
CREATE INDEX idx_graph_relationships_target ON graph_relationships(target_entity_id);
CREATE INDEX idx_graph_relationships_type ON graph_relationships(relationship_type);
```

#### 1.2 New `ContextGraphStore` class

Location: `src/context_graph/storage/graph_store.py`

```python
class ContextGraphStore:
    async def save_graph(self, review_id: str, graph: ContextGraph) -> None
        """Persist graph entities/relationships, deduplicating by name+type."""

    async def load_cumulative_graph(self) -> ContextGraph
        """Rebuild graph from all stored entities/relationships."""

    async def get_entity_history(self, entity_name: str) -> list[dict]
        """Return all reviews where this entity appeared and how it changed."""

    async def get_graph_stats(self) -> dict
        """Return counts: total entities, relationships, entity types, etc."""
```

**Deduplication logic:** Entities are matched by `(name, entity_type)`. When a duplicate is found, update `last_seen_review_id`, increment `times_seen`, and merge properties (new values override old).

#### 1.3 Wire into the review pipeline (all dimensions)

The persistent graph is **not** specific to security — it underpins all cross-functional review dimensions. The graph captures entities and relationships relevant to Security, Privacy, Compliance, Engineering, and Architecture analysis.

In the review pipeline (currently orchestrated by `SecurityReviewEngine.review()`), after the current `_build_graph()` call:

1. Load the cumulative graph from storage as the starting point
2. Overlay the current review's intent/state/delta entities on top
3. Run **all dimension analyses** (Security, Privacy, Compliance, Engineering, Architecture) on the combined graph
4. After review completes, persist the updated graph back to storage

```python
# Before analysis (applies to all dimensions)
cumulative_graph = await self.graph_store.load_cumulative_graph()
self._build_graph(intent, state, delta_result, base_graph=cumulative_graph)

# All dimension analyzers now operate on the cumulative graph:
# - Security: trust boundary crossings, unauthenticated paths
# - Privacy: data flows to/from PII entities across the full system
# - Compliance: control coverage gaps visible only with full architecture context
# - Engineering: dependency chains, coupling scores across all known services
# - Architecture: downstream/upstream impact based on full service graph

# After analysis (persists entities from all dimensions)
await self.graph_store.save_graph(review_id, self.context_graph)
```

**Note:** The review engine class is currently named `SecurityReviewEngine`, but it already orchestrates all five dimensions. Consider renaming it to `ReviewEngine` as part of this phase to reflect its actual scope.

### Definition of Done
- [ ] Graph entities and relationships persist in SQLite across reviews
- [ ] New reviews start with the cumulative graph, not from scratch
- [ ] All five dimension analyzers operate on the cumulative graph
- [ ] `context-graph query` CLI command can answer "what entities exist?" and "what relationships exist?"
- [ ] Entity history is queryable: "when was auth_service first seen?"

### Estimated Effort: 2–3 days

---

## Phase 2: Wire PatternLearner to Persistent Storage

**Goal:** Learned patterns and expert asks survive server restarts, using the existing SQLite storage layer.

**Why second:** The `PatternLearner` works but stores everything in `self.learned_patterns: list = []`. The `expert_asks_store` is an in-memory dict. Meanwhile, SQLite already has `patterns` and `feedback` tables. These need to be connected.

### Tasks

#### 2.1 New SQLite table for expert asks

```sql
CREATE TABLE expert_asks (
    id TEXT PRIMARY KEY,
    prediction_id TEXT NOT NULL,
    review_id TEXT,
    pm_id TEXT NOT NULL,
    pm_name TEXT NOT NULL,
    expert_id TEXT NOT NULL,
    expert_name TEXT NOT NULL,
    expert_domain TEXT NOT NULL,
    question TEXT NOT NULL,
    response_verdict TEXT,
    response_note TEXT,
    response_correct_answer TEXT,
    response_should_learn BOOLEAN,
    asked_at TEXT NOT NULL,
    responded_at TEXT
);
CREATE INDEX idx_expert_asks_expert ON expert_asks(expert_id);
CREATE INDEX idx_expert_asks_prediction ON expert_asks(prediction_id);
```

#### 2.2 Replace in-memory `expert_asks_store`

In `src/context_graph/api/pm_routes.py`:

- Replace `expert_asks_store: dict[str, dict]` with calls to `SQLiteCollaborationStorage`
- Add CRUD methods to storage: `save_expert_ask()`, `get_expert_ask()`, `list_expert_asks()`

#### 2.3 Connect `PatternLearner` to SQLite

Modify `PatternLearner.__init__()` to accept a storage dependency:

```python
class PatternLearner:
    def __init__(self, storage: SQLiteCollaborationStorage | None = None):
        self.storage = storage
        self.learned_patterns: list[LearnedPattern] = []  # Fallback for tests
```

Update methods:
- `learn_from_response()` → call `storage.save_learned_pattern()` after extracting pattern
- `apply_patterns()` → call `storage.get_similar_patterns()` instead of iterating in-memory list
- `get_pattern_insights()` → delegate to `storage.get_pattern_insights()`

#### 2.4 Improve pattern matching

Current `_pattern_matches()` uses simple string matching on file paths and context terms. Upgrade to match on:

- Entity types present in the delta (e.g., PII, API, SERVICE)
- Relationship types (e.g., FLOWS_TO, AUTHENTICATES)
- Delta characteristics (new endpoints, auth changes, external integrations)
- Finding dimension and category

```python
def _pattern_matches(self, pattern: LearnedPattern, context: dict) -> bool:
    """Match on structured conditions, not just string overlap."""
    conditions = json.loads(pattern.applies_when) if isinstance(pattern.applies_when, str) else pattern.applies_when
    for condition in conditions:
        if condition["type"] == "entity_type" and condition["value"] not in context.get("entity_types", []):
            return False
        if condition["type"] == "has_pii" and not context.get("has_pii"):
            return False
        if condition["type"] == "dimension" and condition["value"] != context.get("dimension"):
            return False
    return True
```

### Definition of Done
- [ ] Expert asks persist in SQLite — survive server restarts
- [ ] Learned patterns persist in SQLite — survive server restarts
- [ ] `PatternLearner` reads from and writes to SQLite
- [ ] Pattern matching uses structured conditions, not string matching
- [ ] Existing tests pass with the new storage backend

### Estimated Effort: 1–2 days

---

## Phase 3: Inject Learned Patterns into Review Engine

**Goal:** Expert feedback actually improves future reviews. This closes the feedback loop and is the core value proposition.

**Why third:** With persistent storage (Phase 2) and a persistent graph (Phase 1), we can now make reviews get smarter over time.

### Tasks

#### 3.1 New method: `_apply_learned_patterns()`

In the review engine (applies to all dimensions — Security, Privacy, Compliance, Engineering, Architecture):

```python
async def _apply_learned_patterns(
    self,
    findings: list[SecurityFinding],
    dimension: str,
    delta_context: dict,
) -> list[SecurityFinding]:
    """Apply learned patterns to modify, suppress, or enhance findings."""
    if not self.storage:
        return findings

    adjusted_findings = []
    for finding in findings:
        pattern_signature = f"{dimension}:{finding.category}:{finding.title}"
        similar_patterns = await self.storage.get_similar_patterns(
            pattern_type=dimension,
            pattern_signature=pattern_signature,
        )

        for pattern in similar_patterns:
            decision = pattern["decision"]
            if decision == "false_positive":
                finding.confidence *= 0.3  # Heavily downgrade
                finding.recommendation += f"\n\nNote: A prior expert review flagged similar findings as false positives. Reasoning: {pattern['reasoning']}"
            elif decision == "escalate":
                finding.severity = max_severity(finding.severity, "HIGH")
                finding.recommendation += f"\n\nNote: A prior expert review escalated similar findings. Reasoning: {pattern['reasoning']}"
            elif decision == "add_context":
                finding.recommendation += f"\n\nExpert context: {pattern['reasoning']}"

        adjusted_findings.append(finding)

    return adjusted_findings
```

Call this after each dimension's analysis in `_run_multi_dimension_analysis()` — for all five dimensions, not just security.

#### 3.2 Augment LLM prompts with learned patterns (all dimensions)

Before calling each dimension's LLM analyzer, query relevant patterns and inject as context. This applies to all five dimensions:

```python
# In each dimension runner (_run_security_dimension, _run_privacy_dimension,
# _run_compliance_dimension, _run_engineering_dimension, _run_architecture_dimension)
async def _inject_learned_context(self, dimension: str, delta_signature: str) -> str:
    """Build LLM context from learned patterns for any dimension."""
    relevant_patterns = await self.storage.get_similar_patterns(
        pattern_type=dimension,  # "security", "privacy", "compliance", etc.
        pattern_signature=delta_signature,
    )

    if not relevant_patterns:
        return ""

    prior_decisions = "\n".join([
        f"- {p['pattern_signature']}: {p['decision']} — {p['reasoning']}"
        for p in relevant_patterns
    ])
    return f"""
Prior expert decisions relevant to this {dimension} review:
{prior_decisions}

Consider these prior decisions when generating findings. If a similar pattern was
marked as a false positive, explain why this case is different (if it is).
"""
```

This is where Expert Tokens become genuinely powerful — the LLM reasons with org-specific history across all cross-functional domains, not just security.

#### 3.3 Augment all dimension pattern matchers with learned patterns

Each dimension has its own pattern matcher (`ThreatPatternMatcher`, `PrivacyPatternMatcher`, `CompliancePatternMatcher`, `EngineeringPatternMatcher`, `ArchitecturePatternMatcher`). All need the same learned-pattern injection.

Create a shared mixin or base class:

```python
class LearnedPatternMixin:
    """Mixin for all dimension pattern matchers to apply learned patterns."""

    def __init__(self, learned_patterns: list[dict] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.learned_patterns = learned_patterns or []

    def apply_learned_patterns(self, findings: list) -> list:
        """Post-process findings using learned patterns. Works for any dimension."""
        for finding in findings:
            for pattern in self.learned_patterns:
                if self._learned_pattern_matches(pattern, finding):
                    if pattern["decision"] == "false_positive":
                        finding.confidence *= 0.3
                    elif pattern["decision"] == "escalate":
                        finding.severity = max_severity(finding.severity, "HIGH")
                    elif pattern["decision"] == "add_context":
                        finding.recommendation += f"\n\nExpert context: {pattern['reasoning']}"
                    finding.influenced_by_patterns.append(pattern["id"])
        return findings
```

Apply to each matcher:

```python
class ThreatPatternMatcher(LearnedPatternMixin):  # Security
class PrivacyPatternMatcher(LearnedPatternMixin):  # Privacy
class CompliancePatternMatcher(LearnedPatternMixin):  # Compliance
class EngineeringPatternMatcher(LearnedPatternMixin):  # Engineering
class ArchitecturePatternMatcher(LearnedPatternMixin):  # Architecture
```

#### 3.4 Feedback attribution

Add tracking to findings so users can see which patterns influenced each finding:

```python
# New field on SecurityFinding (and other finding types)
influenced_by_patterns: list[str] = field(default_factory=list)  # Pattern IDs
```

This enables:
- Transparency: "This finding was downgraded because of pattern X"
- Pattern effectiveness tracking: how often do pattern-influenced findings get validated?

### Definition of Done
- [ ] Findings are modified by relevant learned patterns (suppressed, escalated, or annotated)
- [ ] LLM prompts include prior expert decisions as context
- [ ] `ThreatPatternMatcher` applies learned patterns alongside STRIDE/OWASP patterns
- [ ] Each finding tracks which patterns influenced it
- [ ] A review where an expert previously marked a finding as false positive produces a lower-confidence finding (or suppresses it) on the next similar review

### Estimated Effort: 3–4 days

---

## Phase 4: Cross-Review Intelligence

**Goal:** Enable org-wide queries and insights across all reviews, leveraging the persistent graph and accumulated patterns.

**Why fourth:** With a persistent graph (Phase 1) and compounding patterns (Phase 3), we can now surface insights that no single review could produce.

### Tasks

#### 4.1 Entity evolution tracking

Track how entities change across reviews:

```python
class ContextGraphStore:
    async def get_entity_evolution(self, entity_name: str) -> list[dict]:
        """Return timeline: when entity appeared, what changed each time."""

    async def get_frequently_modified_entities(self, threshold: int = 3) -> list[dict]:
        """Entities modified in N+ reviews — stability risk indicators."""
```

Surface in reviews: "auth_service has been modified in 4 of the last 6 PRDs — consider stability risk."

#### 4.2 Org-wide graph queries

New CLI command and API endpoints:

```bash
# CLI
context-graph query "services accessing PII"
context-graph query "unauthenticated paths"
context-graph query "trust boundary crossings"
context-graph query "attack surface"

# API
GET /api/graph/entities?type=PII
GET /api/graph/entities?type=SERVICE&has_pii_access=true
GET /api/graph/paths?from=external&to=sensitive
GET /api/graph/boundaries
GET /api/graph/stats
```

These queries run against the cumulative graph, not a single review's graph.

#### 4.3 Pattern effectiveness scoring

Track how well patterns perform over time:

```sql
ALTER TABLE patterns ADD COLUMN expert_agreed INTEGER DEFAULT 0;
ALTER TABLE patterns ADD COLUMN expert_disagreed INTEGER DEFAULT 0;
ALTER TABLE patterns ADD COLUMN effectiveness_score REAL DEFAULT 1.0;
ALTER TABLE patterns ADD COLUMN deprecated BOOLEAN DEFAULT FALSE;
```

Logic:
- When a pattern-influenced finding is validated by an expert: increment `expert_agreed`
- When a pattern-influenced finding is rejected: increment `expert_disagreed`
- Recalculate `effectiveness_score = agreed / (agreed + disagreed)`
- Auto-deprecate patterns below a threshold (e.g., 0.3)
- Surface high-confidence patterns prominently in reports

#### 4.4 Review diffing

Compare two reviews of the same PRD (e.g., v1 vs. v2):

```python
class ReviewDiffer:
    def diff(self, review_a: ReviewResult, review_b: ReviewResult) -> ReviewDiff:
        """Return: new findings, resolved findings, changed severities, new entities."""
```

```bash
context-graph diff <review_id_a> <review_id_b>
```

Useful for: "I updated the PRD based on the first review's findings — what changed?"

### Definition of Done
- [ ] Frequently-modified entities are surfaced as stability risk indicators in reviews
- [ ] `context-graph query` CLI command answers org-wide questions
- [ ] API endpoints expose graph queries
- [ ] Pattern effectiveness is tracked and low-performing patterns are auto-deprecated
- [ ] Two reviews can be diffed to show what changed

### Estimated Effort: 4–5 days

---

## Phase 5: Semantic Pattern Matching

**Goal:** Patterns match based on meaning, not string overlap. This is the technical moat that makes Expert Tokens genuinely hard to replicate.

**Why last:** Requires the most infrastructure and benefits most from having a large corpus of patterns (built up through Phases 1–4).

### Tasks

#### 5.1 Embedding infrastructure

Add an embedding layer for patterns and findings:

```python
class PatternEmbedder:
    def __init__(self, model: str = "text-embedding-3-small"):
        self.client = openai.OpenAI()

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""

    async def similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Cosine similarity between two vectors."""
```

Storage: Add `embedding BLOB` column to `patterns` table. Compute and store embedding when patterns are saved.

**Future consideration:** When migrating to PostgreSQL, replace this with `pgvector` for native vector operations.

#### 5.2 Semantic similarity matching

Replace string-based `_pattern_matches()` with semantic matching:

```python
async def get_similar_patterns_semantic(
    self,
    finding_text: str,
    dimension: str,
    threshold: float = 0.75,
) -> list[dict]:
    """Find patterns semantically similar to the given finding."""
    finding_embedding = await self.embedder.embed(finding_text)
    all_patterns = await self.get_patterns_by_dimension(dimension)

    matches = []
    for pattern in all_patterns:
        similarity = cosine_similarity(finding_embedding, pattern["embedding"])
        if similarity >= threshold:
            matches.append({**pattern, "similarity_score": similarity})

    return sorted(matches, key=lambda p: p["similarity_score"], reverse=True)
```

This catches cases where exact terms differ but the situation is analogous: e.g., "missing rate limiting on public API" matches "no throttling on external endpoint."

#### 5.3 Pattern conflict resolution

When two patterns contradict (one says `false_positive`, another says `escalate`):

```python
class PatternConflictResolver:
    def resolve(self, patterns: list[dict]) -> dict:
        """Resolve conflicting patterns by recency, effectiveness, and expert seniority."""
        # Priority: higher effectiveness_score > more recent > more times_applied
```

Surface unresolved conflicts for expert review:

```python
GET /api/patterns/conflicts
# Returns pairs of contradicting patterns for human resolution
```

#### 5.4 Pattern clustering and generalization

Automatically identify groups of similar patterns and suggest generalizations:

```python
class PatternGeneralizer:
    async def find_clusters(self, min_cluster_size: int = 3) -> list[PatternCluster]:
        """Group similar patterns using embedding clustering."""

    async def propose_policy(self, cluster: PatternCluster) -> str:
        """Use LLM to propose a generalized org-wide policy from a cluster."""
```

Example output: "You have 5 patterns about missing rate limiting on public endpoints. Proposed org-wide policy: All public-facing API endpoints MUST implement rate limiting before launch."

### Definition of Done
- [ ] Patterns and findings are embedded using a text embedding model
- [ ] Pattern matching uses cosine similarity with configurable threshold
- [ ] Conflicting patterns are detected and surfaced for resolution
- [ ] Pattern clusters are identified and org-wide policies are proposed
- [ ] Pattern matching quality measurably improves vs. string-based matching

### Estimated Effort: 5–7 days

---

## Timeline Summary

| Phase | Description | Effort | Cumulative |
|-------|-------------|--------|------------|
| **1** | Persistent Context Graph | 2–3 days | 2–3 days |
| **2** | Wire PatternLearner to SQLite | 1–2 days | 3–5 days |
| **3** | Inject Patterns into Reviews | 3–4 days | 6–9 days |
| **4** | Cross-Review Intelligence | 4–5 days | 10–14 days |
| **5** | Semantic Pattern Matching | 5–7 days | 15–21 days |

**Critical path (Phases 1–3): ~6–9 days** — delivers the core "compounding judgment" value proposition.

**Full roadmap: ~15–21 days** — delivers a complete organizational knowledge platform.

---

## Infrastructure Notes

### Database Strategy
- **Now:** Stay on SQLite. It handles the current scale and keeps ops simple.
- **When multi-user concurrency is needed:** Migrate to PostgreSQL.
  - `pgvector` extension replaces the custom embedding layer from Phase 5
  - `jsonb` enables querying inside stored finding/entity JSON
  - Async method signatures already map cleanly to `asyncpg`
- **Prep:** Keep all SQL going through storage classes. Avoid SQLite-specific syntax.

### Storage Abstraction
The current `SQLiteReviewStorage` and `SQLiteCollaborationStorage` classes are a good abstraction boundary. Future migration to PostgreSQL means swapping the implementation, not rewriting the app.

### LLM Strategy
- Pattern-augmented prompts (Phase 3) work with any LLM provider (OpenAI, Anthropic)
- Embeddings (Phase 5) use `text-embedding-3-small` for cost efficiency
- Both can be swapped for local models if needed for on-prem deployments

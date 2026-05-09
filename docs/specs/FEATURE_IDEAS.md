# Feature Ideas — Grounded in Code, Relevant to PM Flows

> **Context:** The only feature from the P0–P3 batch that landed well was **Product Chat**.
> The rest (Review Requests, Impact Graph, Live Analysis, Decision Log, Templates, Audit Trail, etc.)
> felt either too enterprise/process-heavy or too demo-ware to matter for the daily PM loop.
>
> This document proposes new features grounded in the data and code we already have,
> focused on what a PM actually needs during the PRD → Code → Ship cycle.

---

## What We Already Have (Primitives to Build On)

| Primitive | Location | Capability |
|---|---|---|
| **Intent extraction** | `parsers/` → `Intent` | Features, user stories, data entities, API changes, auth requirements, integrations |
| **Codebase analysis** | `HybridAnalyzer`, `MultiLanguageAnalyzer` | AST parsing, endpoints, data models, auth patterns, entities with source file paths |
| **Context graph** | `core/graph.py` → `ContextGraph` | Entities, relationships, trust boundaries, risk scores, unauthenticated paths |
| **Delta analysis** | `security/delta_analyzer.py` | New entities, modified flows, PII introduction, auth modification, attack surface changes |
| **Multi-dimension LLM analysis** | `ParallelLLMAnalyzer` | Security, Privacy, Compliance, Engineering, Architecture — run in parallel with OpenAI + Anthropic |
| **Findings** | `SecurityFinding`, `PrivacyFinding`, etc. | Title, description, severity, technical details, attack scenario, business impact, affected components, recommendations, references |
| **PRD quality scoring** | `pm/quality_scorer.py` | Readiness score, gap identification, coverage analysis |
| **Effort estimation** | `pm/effort_estimator.py` | Code-grounded time estimates per finding |
| **PRD changes** | `pm/prd_change_generator.py` | Diff-style PRD improvement suggestions |
| **Pattern learning** | `pm/pattern_learner.py` | Aggregated patterns from expert feedback |
| **Full review history** | `SQLiteReviewStorage` | All past reviews with findings, dimensions, quality scores |
| **Collaboration data** | `SQLiteCollaborationStorage` | Validations, comments, feedback, team assignments |
| **Product Chat** | `chat/product_chat.py` | Conversational AI grounded in review data (already shipped, user liked it) |
| **False positive filter** | `llm/false_positive_filter.py` | Multi-strategy noise removal with parallel vote |
| **GitHub integration** | `integrations/github.py` | Clone, branch, PR analysis |

---

## Feature 1: Smart PRD Gap Detection (Pre-Review)

### The Problem
PMs paste a PRD and run a full review (which takes time and costs LLM tokens) only to discover their PRD was missing obvious things — no auth mentioned for a payments endpoint, no data retention policy for PII, no error handling section. They have to fix the PRD and re-run.

### The Feature
**Before** the PM submits a review, run a fast (< 2 second, no LLM) gap analysis that cross-references the PRD intent with the codebase state:

- Parse the PRD to extract `Intent` (already have `MarkdownPRDParser`)
- Run `HybridAnalyzer.analyze_fast()` on the codebase (already have, ~200ms)
- Compare: What does the PRD mention? What does the codebase require?
- Surface gaps: "Your PRD adds a `/api/payments/charge` endpoint but doesn't mention authentication. Your codebase uses OAuth2 on all existing payment routes." or "You reference a `UserProfile` entity with email/phone — these are PII but your PRD has no data retention section."

### What Exists to Build On
- `MarkdownPRDParser.parse()` → extracts `Intent` with features, API changes, data entities, auth requirements
- `HybridAnalyzer.analyze_fast()` → returns AST results with classes, functions, decorators, in ~200ms
- `State` → has `api_endpoints`, `data_models`, `auth_patterns`, `existing_controls`
- `PRDQualityScore` → already identifies gaps, but only after a full review

### Why It's Good
- Zero cost (no LLM calls)
- Instant feedback (< 2 seconds)
- Saves the PM a full review cycle
- Naturally lives in the "New Review" page before the submit button
- Makes the tool feel intelligent before the user even starts

### Where It Goes
- New endpoint: `POST /api/pre-review/gaps`
- Frontend: Inline in `NewReview.tsx` after PRD + codebase are entered, before "Start Review"
- Replaces or upgrades the current "Preview Intent" button

---

## Feature 2: Codebase-Aware Chat (the Big One)

### The Problem
Current chat only knows about reviews and findings — structured data the system already produced.
But a PM's real questions are about the **codebase itself**:

- "How does our authentication work?"
- "What happens when a payment fails — show me the error handling"
- "Which services talk to the database directly?"
- "Where is PII stored and who accesses it?"
- "If I add a new notification channel, what files would I need to touch?"

Today the PM has to go ask a developer or try to read the code themselves. **Intently already has
filesystem access to the codebase** (local path or cloned GitHub repo). We just don't use it in chat.

### The Feature
Give the chat **full read access to the codebase**, like Cursor does for developers but oriented
toward PM questions. The chat becomes a "talk to your codebase" interface where PMs can ask
anything about code structure, data flows, dependencies, and patterns — without reading code.

**Three layers of codebase context, progressively deeper:**

#### Layer 1: Structural Index (always available, no file reads)
On every review, we already build a `State` that includes:
- All API endpoints (path, method, file, line)
- All data models (name, file, fields)
- Auth patterns, existing security controls
- Entity list with types and source file paths

This is already stored in SQLite per review. Inject it into chat context automatically
when a review is scoped. The LLM can answer structural questions instantly:
"You have 47 endpoints, 12 use OAuth2, 3 handle payment data."

#### Layer 2: Smart File Retrieval (on-demand, reads actual files)
When the PM asks a question that needs code detail, the system reads relevant files
from the codebase. Key insight: **we already know which files matter** from the
AST analysis and entity index. The retrieval strategy:

1. **Keyword match** — match question keywords against the file/class/function index
   from `HybridAnalyzer` AST results (already have: classes, functions, imports per file)
2. **Entity match** — if the question mentions an entity name we know about, pull its
   source file (entities already have `source` field with file path)
3. **Finding match** — if the question is about a specific finding, pull the
   `affected_components` and `source_reference` files
4. **Targeted read** — read only the relevant portions of matched files (not the whole
   codebase). Use AST line ranges to extract just the relevant class/function.

Example flow:
- PM asks: "How does our payment processing handle refunds?"
- System searches AST index for functions/classes matching "payment", "refund"
- Finds `payments/processor.py:RefundHandler` (lines 45-120) and `payments/models.py:Refund` (lines 10-35)
- Reads those specific line ranges from disk
- Injects the actual code into the LLM context
- LLM answers grounded in real code with file citations

#### Layer 3: Cross-File Flow Tracing (advanced, follows the graph)
For questions about data flows and dependencies:
- "What happens to user data after signup?"
- "Trace the request from API to database for creating an order"

Use the `ContextGraph` relationships + import analysis from `HybridAnalyzer` to follow
the chain across files. Read each file in the chain. Present the LLM with an ordered
sequence of code snippets showing the flow.

### What Exists to Build On

| Component | File | How It's Used |
|---|---|---|
| `State.codebase_path` | `core/models.py` | Stored per review — we know where the code lives |
| `HybridAnalyzer` | `code_graph/hybrid_analyzer.py` | AST analysis: classes, functions, imports, decorators with file paths and line numbers |
| `ASTResult` | `code_graph/hybrid_analyzer.py` | Per-file index: `classes[{name, line, end_line, methods}]`, `functions[{name, line, end_line, args, decorators}]` |
| `State.entities` | `core/models.py` | Each entity has `name`, `entity_type`, `source` (file path) |
| `State.api_endpoints` | `core/models.py` | Each endpoint has `path`, `method`, `file`, `line` |
| `State.data_models` | `core/models.py` | Each model has `name`, `file`, `line` |
| `ContextGraph` | `core/graph.py` | Entity relationships, can traverse `source_id` → `target_id` chains |
| `ProductChat` | `chat/product_chat.py` | Already has `_gather_context()` + `_build_system_prompt()` + LLM call — extend these |
| `SecurityFinding.affected_components` | `core/models.py` | List of file/component paths per finding |
| `SQLiteReviewStorage.get_review()` | `storage/sqlite.py` | Returns full review with `state.codebase_path`, all entities, findings |

### Implementation Sketch

#### Backend: `CodebaseReader` (new class)

```python
# src/context_graph/chat/codebase_reader.py

class CodebaseReader:
    """Reads code from the filesystem, guided by the AST index."""

    def __init__(self, codebase_path: Path, state: State):
        self.root = codebase_path
        self.state = state
        self._ast_index = self._build_index()  # Map of name -> (file, line_start, line_end)

    def search(self, query: str, max_results: int = 5) -> list[CodeSnippet]:
        """Find code relevant to a natural language query."""
        # 1. Tokenize query, match against class/function/model names
        # 2. Return ranked list of (file, line_range, code_text) snippets

    def read_entity(self, entity_name: str) -> CodeSnippet | None:
        """Read the code for a specific named entity."""

    def read_file_range(self, file_path: str, start: int, end: int) -> str:
        """Read specific lines from a file."""

    def trace_flow(self, start_entity: str, max_depth: int = 5) -> list[CodeSnippet]:
        """Follow imports/calls from one entity through the codebase."""
```

#### Backend: Extend `ProductChat._gather_context()`

```python
# In _gather_context(), add codebase-reading logic:

if review and review.state.codebase_path:
    codebase_path = Path(review.state.codebase_path)
    if codebase_path.exists():
        reader = CodebaseReader(codebase_path, review.state)

        # Always inject structural summary
        context["codebase_structure"] = {
            "path": str(codebase_path),
            "endpoints": review.state.api_endpoints[:30],
            "models": review.state.data_models[:30],
            "auth_patterns": review.state.auth_patterns,
        }

        # Smart file retrieval based on question
        snippets = reader.search(question, max_results=5)
        context["code_snippets"] = [
            {"file": s.file, "lines": f"{s.start}-{s.end}", "code": s.text}
            for s in snippets
        ]
        for s in snippets:
            citations.append(Citation(
                type="code",
                id=s.file,
                text=f"{s.file}:{s.start}-{s.end}",
                url=f"file://{s.file}#L{s.start}",
            ))
```

#### API: Add `finding_id` to scoped chat

While we're extending chat, also add finding-scoped conversations:

```python
# In chat_routes.py ChatRequest:
finding_id: str | None = Field(None, description="Scope to a specific finding")

# In ProductChat._gather_context():
if finding_id and review:
    finding = next((f for f in review.all_findings if str(f.id) == finding_id), None)
    if finding:
        context["focused_finding"] = {
            "title": finding.title,
            "severity": finding.severity.value,
            "technical_details": finding.technical_details,
            "attack_scenario": finding.attack_scenario,
            "business_impact": finding.business_impact,
            "affected_components": finding.affected_components,
            "recommendation": finding.recommendation,
            "implementation_guidance": finding.implementation_guidance,
        }
        # Also read the affected component files
        for comp in (finding.affected_components or []):
            snippet = reader.read_entity(comp)
            if snippet:
                context["code_snippets"].append(...)
```

#### Frontend: Enhanced ChatPanel

- Add a `codebasePath` prop — when set, show "Codebase connected" indicator
- Code snippets in responses rendered with syntax highlighting
- Citations of type "code" show as clickable file links (in desktop: open in editor)
- Finding drill-down: chat icon on each finding row opens ChatPanel with finding pre-focused
- Suggested questions adapt: "How does {endpoint} handle auth?" based on codebase structure

#### Frontend: Standalone Chat Page (not just a side panel)

The current chat is a 384px side panel on ReviewDetail. For codebase exploration,
it deserves a **full page** — accessible from the sidebar nav. Think: a Cursor-like
experience where the PM can explore the codebase conversationally without needing
a review first.

- New route: `/chat` — full-page chat with codebase selector
- PM picks a codebase (from recent reviews or enters a path)
- System runs `HybridAnalyzer.analyze_fast()` to build the index
- PM chats with the codebase directly

### What PMs Can Ask (Grouped by Use Case)

**Understanding the codebase (no review needed):**
- "Give me an overview of the codebase architecture"
- "What are the main API endpoints and what do they do?"
- "How does authentication work in this project?"
- "What data models exist and which ones handle PII?"
- "Show me how the payment flow works end to end"

**During PRD writing (before review):**
- "If I add a notification system, what existing code can I reuse?"
- "What's the current error handling pattern — should I follow it?"
- "Does the codebase already have a rate limiter I can use?"

**After review (with findings):**
- "Explain this SQL injection finding — show me the actual vulnerable code"
- "What's the minimum code change to fix this auth bypass?"
- "Which other endpoints have the same pattern as this finding?"

**Cross-review questions (over time):**
- "Which parts of the codebase have the most recurring findings?"
- "Has the auth setup changed since the last review?"

### Why It's the Big One

- **Massively extends the feature the user already likes** (chat)
- **Only possible because we already have filesystem access** — the codebase path is stored per review, and we already run AST analysis on it. We're sitting on all the data we need.
- **Differentiated** — no other PM tool lets PMs "talk to their codebase." Developers have Cursor; PMs have nothing.
- **Leverages every existing primitive**: parsers, analyzers, context graph, storage, findings, LLM providers
- **Three natural entry points**: (1) standalone codebase chat, (2) review-scoped chat with code, (3) finding drill-down chat
- **Incremental build path**: Layer 1 (structural index) is nearly free. Layer 2 (file reads) is the core. Layer 3 (flow tracing) is a stretch goal.

---

## Feature 3: Review Comparison / PRD Iteration Tracker

### The Problem
PMs iterate on PRDs. They run a review, get 15 findings, fix the PRD, run again. But there's no way to see: "What improved? What's still broken? Am I making progress?" They're comparing two walls of findings manually.

### The Feature
**Compare any two reviews** side-by-side and see:

- **Resolved findings** — findings from review A that no longer appear in review B
- **New findings** — findings in review B that weren't in review A
- **Persistent findings** — findings that appear in both (with severity changes highlighted)
- **Score delta** — quality score, risk rating, finding count changes
- **Progress summary** — "You addressed 8 of 12 findings. 3 new issues introduced. Risk dropped from HIGH to MEDIUM."

### What Exists to Build On
- `SQLiteReviewStorage.list_reviews()` — all past reviews
- `SQLiteReviewStorage.get_review()` — full review with all findings
- Each finding has: `title`, `severity`, `category`, `dimension`, `recommendation`
- `PRDQualityScore` — stored per review, has `score` and `grade`
- `ReviewResult` has `risk_rating`, finding counts per dimension
- Version history already tracks PRD versions (we just don't compare the *reviews* across versions)

### Implementation Sketch
- New endpoint: `GET /api/reviews/compare?a={id_a}&b={id_b}`
- Backend: Load both reviews, fuzzy-match findings by title+category+dimension, classify as resolved/new/persistent
- Frontend: New "Compare" button on dashboard (select two reviews) or on ReviewDetail ("Compare with previous")
- Display: Side-by-side cards showing deltas with green (resolved), red (new), yellow (persistent)

### Why It's Good
- Directly supports the core PM workflow: write → review → iterate → review again
- Uses only existing data (no new storage, no LLM calls)
- Makes progress visible and satisfying
- Turns Intently from "run once" to "track improvement over time"

---

## Feature 4: Finding Export to Dev-Friendly Formats

### The Problem
A PM runs a review, gets findings. Now what? They need to communicate these to their dev team. Currently they can "Export" a markdown report, but that's a wall of text. What devs actually want is: individual tickets they can pick up.

### The Feature
**One-click export** for each finding (or batch of findings) into formats developers actually use:

- **GitHub Issue** — creates an issue with title, description, severity label, affected files, recommendation as acceptance criteria (uses existing `GitHubIntegration`)
- **Clipboard Markdown** — copies a dev-friendly markdown block: title, severity, what's wrong, where in code, how to fix
- **Linear/Jira format** — structured text with fields matching ticket systems
- **Batch export** — select multiple findings, export as a set of linked issues

### What Exists to Build On
- `GitHubIntegration` — already authenticated, has `clone()`, can be extended with issue creation
- Each finding already has: `title`, `severity`, `description`, `recommendation`, `affected_components`, `implementation_guidance`, `technical_details`
- `MarkdownReportGenerator` — already generates formatted output
- `source_reference` on findings — points to specific code locations

### Implementation Sketch
- New endpoint: `POST /api/findings/export` — takes finding IDs + format (github_issue, markdown, linear)
- For GitHub: Use `gh` CLI or GitHub API to create issues with labels
- For clipboard: Generate structured markdown and return it
- Frontend: Add "Export" dropdown on each finding row and a "Bulk Export" button in the findings header

### Why It's Good
- Closes the loop: PRD → Review → Action items for devs
- The PM's job isn't just to identify problems — it's to communicate them to the team
- Uses existing data perfectly (findings already have everything a ticket needs)
- Makes Intently's output *actionable*, not just informational

---

## Feature 5: Codebase Security Profile (Persistent)

### The Problem
Every review analyzes the codebase from scratch. But a PM working on the same codebase week after week doesn't need to re-discover that their codebase has 47 endpoints, 12 with auth, and 3 known PII stores. They need a persistent "health profile" that accumulates knowledge over time.

### The Feature
A **standing codebase profile** that persists across reviews and builds up over time:

- **Attack surface map**: All endpoints, which have auth, which handle PII, which are public
- **Entity inventory**: All data models, which are sensitive, data flow between them
- **Cumulative findings**: Patterns that keep showing up across reviews (not just per-review)
- **Coverage gaps**: Parts of the codebase that have never been reviewed
- **Historical trend**: Risk score over time, findings resolved vs introduced

### What Exists to Build On
- `HybridAnalyzer` — fast AST analysis of full codebase
- `State` — entities, endpoints, data models, auth patterns per review (but not persisted across reviews)
- `ContextGraph` — entity relationships, trust boundaries, risk scores
- `SQLiteReviewStorage` — all review history with findings and dimensions
- `PRDQualityScore` — tracked per review, can be trended

### Implementation Sketch
- New SQLite table: `codebase_profiles` — stores aggregated state keyed by codebase path
- New endpoint: `GET /api/codebases/{path_hash}/profile` — returns or builds the profile
- Backend: On each review completion, merge the review's `State` into the persistent profile
- Frontend: New "Codebase" page (or section on Dashboard) showing the standing profile
- Bonus: "This review covers 23% of your codebase's endpoints"

### Why It's Good
- Transforms Intently from "per-PRD tool" to "ongoing product intelligence platform"
- PMs get a persistent view of their product's health without re-running reviews
- Grounds future chat conversations: "Based on your codebase profile, this new feature touches 3 PII endpoints"
- Differentiated — no other PM tool builds a persistent security/quality profile of the codebase

---

## Feature 6: "What If" Quick Impact Preview

### The Problem
A PM is writing a PRD and wonders: "If I add a new payment endpoint, what parts of the codebase will be affected? What security concerns should I expect?" They have to run a full review to find out.

### The Feature
A **lightweight impact preview** that runs in seconds (no full LLM review):

- PM enters a one-liner: "Add a new REST endpoint for processing refunds"
- System uses existing codebase analysis to find related code: payment modules, existing refund patterns, auth setup on payment routes
- Returns: "This would likely touch: `payments/` (3 files), `models/Transaction.py`, `auth/middleware.py`. Based on similar past reviews, expect 2-4 security findings around input validation and payment fraud. Your codebase already has rate limiting on payment routes — good."

### What Exists to Build On
- `HybridAnalyzer.analyze_fast()` — fast AST analysis
- `State` with entities, endpoints, patterns — already extracted
- `SQLiteReviewStorage` — past reviews for "similar review" matching
- `PatternLearner.learned_patterns` — historical patterns
- `DeltaAnalyzer` — understands how new intent maps to existing state
- Intent parser — can parse even a single sentence into basic intent

### Implementation Sketch
- New endpoint: `POST /api/quick-impact` — takes a short description + codebase path
- Backend: Parse description into mini-Intent, run `DeltaAnalyzer` logic against cached State, query past reviews for similar findings
- Frontend: Small input box on Dashboard or NewReview page — "What are you thinking about building?"
- Returns: Affected files, expected finding categories, related past reviews

### Why It's Good
- Zero-to-insight in under 3 seconds
- Helps PMs during the *ideation* phase, not just the review phase
- Uses existing primitives (delta analysis, codebase state, review history)
- Natural lead-in to "Want a full review? Click here."

---

## Ranking & Recommendation

| Rank | Feature | Effort | Impact | Uses LLM? |
|------|---------|--------|--------|------------|
| 1 | **Codebase-Aware Chat** (Layer 1: structural) | 2–3 days | Very High | Yes (extends existing chat) |
| 1b | **Codebase-Aware Chat** (Layer 2: file reads) | 3–4 days | Very High | Yes |
| 2 | **Smart PRD Gap Detection** | 2–3 days | High | No (pure logic) |
| 3 | **Review Comparison** | 2–3 days | High | No (pure logic) |
| 4 | **Finding Export** | 2–3 days | Medium-High | No |
| 5 | **"What If" Quick Impact** | 3–4 days | High | No (optional) |
| 6 | **Codebase Security Profile** | 4–5 days | High | No |
| — | **Codebase-Aware Chat** (Layer 3: flow tracing) | 3–4 days | High | Yes (stretch) |

### Recommended order:
1. **Codebase-Aware Chat Layer 1+2** first — this is the defining feature. PMs can talk to their codebase like devs talk to Cursor. Layer 1 (structural index from existing State) is nearly free; Layer 2 (smart file retrieval) is the core work.
2. **Smart PRD Gap Detection** — makes the tool feel intelligent before the user even runs a review
3. **Review Comparison** — supports the core iterate-on-PRD loop
4. Then either Export, "What If", or Chat Layer 3 depending on user feedback

### What NOT to build (from old specs):
- ~~Review Requests~~ — too workflow-heavy, JIRA-lite territory
- ~~Impact Graph~~ — D3 force-directed graphs are demo-ware; PMs don't read them
- ~~Live Analysis~~ — pattern-based-only is too weak to be useful
- ~~Decision Log / Audit Trail~~ — enterprise features that don't help individual PMs
- ~~Templates Library~~ — commoditized, every tool has templates
- ~~Autocomplete~~ — hard to do well, low payoff vs effort

### What to keep from old specs:
- **Product Chat** — already shipped, already liked. Extend it (Feature 2 above).
- **Version History** — useful infra, supports Review Comparison (Feature 3)
- **Approval Gates** — useful for teams, keep as-is
- **Analytics** — useful for trends, keep as-is

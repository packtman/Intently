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

## Feature 2: Finding Drill-Down Chat (Extend What Works)

### The Problem
PMs see a finding like "Insufficient input validation on user-supplied data in API endpoint" and think: "What does that actually mean for my feature? What's the minimum fix? Can I ship without fixing this?" There's no way to ask follow-up questions about a specific finding.

### The Feature
Extend the Product Chat (which the user already likes) with **finding-scoped conversations**. When a PM clicks on a finding, they can open a chat pre-loaded with that finding's full context (technical details, attack scenario, affected components, recommendation) and ask:

- "Explain this in business terms"
- "What's the minimum fix to unblock shipping?"
- "Is this actually exploitable given our auth setup?"
- "Write me a Jira ticket for this"

The LLM already has all the context — the review data, the finding details, the codebase analysis. We just need to scope the conversation to a specific finding.

### What Exists to Build On
- `ProductChat.answer()` — already takes `review_id` and gathers context from storage
- `_gather_context()` — already loads findings, entities, review data
- Each finding has: `technical_details`, `attack_scenario`, `business_impact`, `affected_components`, `recommendation`, `implementation_guidance`
- Chat already has conversation memory and follow-up suggestions

### Implementation Sketch
- Add `finding_id` parameter to `ProductChat.answer()`
- When `finding_id` is present, inject the full finding data (all fields) into the system prompt as primary context
- Frontend: Add a small chat icon on each finding row in `ReviewDetail.tsx` — clicking it opens the ChatPanel with that finding pre-selected
- The chat panel shows the finding title as conversation header

### Why It's Good
- Builds on the ONE feature the user already likes
- Directly addresses the PM's #1 question when looking at findings: "What do I do about this?"
- Zero new backend modules — just a parameter addition to existing chat
- Converts findings from "read-only report items" to "conversation starters"

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
| 1 | **Finding Drill-Down Chat** | 1–2 days | High | Yes (extends existing chat) |
| 2 | **Smart PRD Gap Detection** | 2–3 days | High | No (pure logic) |
| 3 | **Review Comparison** | 2–3 days | High | No (pure logic) |
| 4 | **Finding Export** | 2–3 days | Medium-High | No |
| 5 | **"What If" Quick Impact** | 3–4 days | High | No (optional) |
| 6 | **Codebase Security Profile** | 4–5 days | High | No |

### Recommended order:
1. **Finding Drill-Down Chat** first — lowest effort, highest signal, extends the feature the user already likes
2. **Smart PRD Gap Detection** — makes the tool feel intelligent before the user even runs a review
3. **Review Comparison** — supports the core iterate-on-PRD loop
4. Then either Export or "What If" depending on user feedback

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

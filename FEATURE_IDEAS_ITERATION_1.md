# Feature Ideas — Iteration 1

## Vision: Cursor + GitHub for Product Managers

**Cursor** gives developers an AI-powered workspace that deeply understands code context, offers intelligent assistance inline, and accelerates every part of the development workflow. **GitHub** gives developers version control, collaboration, review workflows, and project management — all centered around code artifacts.

**Intently** should do both of these things, but for **product managers** and their artifacts: PRDs, specs, user stories, roadmaps, and the decisions that connect product intent to engineering reality.

This document proposes features across six themes that would move Intently toward that vision, building on the existing foundation of PRD analysis, multi-dimensional review, codebase analysis, collaboration, and pattern learning.

---

## Table of Contents

1. [Theme 1: AI-Powered PRD Workspace](#theme-1-ai-powered-prd-workspace)
2. [Theme 2: Version Control for Product Artifacts](#theme-2-version-control-for-product-artifacts)
3. [Theme 3: PRD Review Workflows (Pull Requests for PMs)](#theme-3-prd-review-workflows-pull-requests-for-pms)
4. [Theme 4: Product Intelligence Dashboard](#theme-4-product-intelligence-dashboard)
5. [Theme 5: Integrations & Ecosystem](#theme-5-integrations--ecosystem)
6. [Theme 6: Team & Org-Wide Product Governance](#theme-6-team--org-wide-product-governance)
7. [Prioritization Matrix](#prioritization-matrix)
8. [Summary](#summary)

---

## Theme 1: AI-Powered PRD Workspace

> The "Cursor editor" for product managers — an intelligent authoring environment that understands your product, codebase, and organizational context while you write.

### 1.1 Inline PRD Authoring with AI Assist

**What:** A rich-text PRD editor (web and desktop) with AI-powered inline suggestions. As the PM types requirements, the system surfaces relevant context: existing APIs that could be reused, data models that already exist, patterns from past PRDs, and potential conflicts with in-flight work.

**Why:** Today, PMs write PRDs in Google Docs or Notion with zero awareness of the codebase. They discover implementation issues only after engineering reviews, wasting cycles. This feature shifts that feedback left — to the moment of writing.

**How it works:**
- PM opens a new PRD in Intently's editor
- As they type "Add a new endpoint for user preferences," the system:
  - Shows existing preference-related endpoints from the codebase analysis
  - Surfaces the data model for user preferences if it already exists
  - Warns if a similar feature is described in another active PRD
  - Suggests auth requirements based on the entity type (PII, user data)
- Autocomplete suggestions appear inline, similar to Cursor's Tab completions
- PM can accept, dismiss, or ask follow-up questions in a side panel

**Key capabilities:**
- **Context-aware autocomplete:** Suggest API names, data models, component names from the codebase
- **Inline warnings:** Flag potential security/privacy/compliance issues as the PM writes
- **Snippet suggestions:** Insert boilerplate sections (auth requirements, data flow diagrams, acceptance criteria) pre-filled with context
- **"Explain this code" for PMs:** Select a component name and get a plain-English explanation of what it does, its dependencies, and its current state

**Builds on:** Existing PRD parser, codebase analyzer, context graph, PM tools

### 1.2 Real-Time Analysis While Writing

**What:** As the PM writes or edits a PRD, continuously run lightweight analysis in the background and display results in a sidebar — like IDE linting but for product requirements.

**Why:** The current flow requires the PM to finish writing, submit the PRD, wait for analysis, and then iterate. Real-time feedback collapses this into a single writing session.

**How it works:**
- Debounced analysis triggers as the PM pauses typing (e.g., 2-second delay)
- Lightweight checks run first (pattern matching, entity recognition, quality scoring)
- Heavier LLM-based analysis runs on explicit save or "Analyze" button
- Results appear in a right-hand panel organized by dimension (Security, Privacy, etc.)
- Each finding links to the specific section of the PRD that triggered it
- Severity badges update in real time as issues are introduced or resolved

**Key capabilities:**
- **Live quality score:** PRD completeness score updates as sections are added
- **Live effort estimate:** Rough complexity/effort estimate adjusts as requirements grow
- **Issue count by dimension:** "3 security, 1 privacy, 0 compliance" badges in the sidebar
- **Section-level annotations:** Underline or highlight specific sentences with dimension-specific feedback

### 1.3 Product-Aware Chat (Conversational AI)

**What:** A chat interface embedded in the workspace where PMs can ask natural-language questions about their product, codebase, past decisions, and organizational patterns — and get answers grounded in actual data.

**Why:** PMs constantly need to answer questions like "Do we already have rate limiting on the payments API?" or "What did we decide about GDPR consent flows last quarter?" Today, this requires Slack threads, code searches, or asking engineers. A product-aware chat that queries the context graph, past reviews, and learned patterns can answer these instantly.

**How it works:**
- Chat panel in the workspace (similar to Cursor's Cmd+L chat)
- Queries are routed to the context graph, review history, codebase analysis, and pattern store
- Responses include citations: "Based on review R-123 from Jan 2026..." or "From codebase analysis of auth_service..."
- Supports follow-up questions with conversation context
- Can generate artifacts: "Draft a data flow diagram for this feature" or "Write the auth requirements section"

**Example queries:**
- "What services access PII in our system?"
- "Has anyone proposed a notification service before? What happened?"
- "What are the compliance requirements for storing payment data?"
- "What did the security team flag in the last review of the payments PRD?"
- "Generate acceptance criteria for this user story based on our engineering patterns"

**Builds on:** Existing context graph, review storage, LLM providers, pattern learner

### 1.4 PRD Templates Library

**What:** A library of organization-specific PRD templates that encode best practices, required sections, and pre-filled boilerplate. Templates evolve based on pattern learning — if reviews consistently flag missing sections, those sections get added to templates.

**Why:** Many PRD quality issues are structural: missing auth requirements, no data flow section, no rollback plan. Templates solve this at the source rather than catching it in review.

**How it works:**
- Default templates for common PRD types: new feature, API change, data migration, integration, deprecation
- Each template includes required sections with guidance text
- Templates auto-suggest based on PRD content: "This looks like a data migration — switch to the Data Migration template?"
- Organization-specific templates created from high-scoring past PRDs
- Template effectiveness tracking: which templates produce the fewest review findings?

---

## Theme 2: Version Control for Product Artifacts

> The "Git" for product decisions — track every change, understand what evolved and why, and never lose the history of a product decision.

### 2.1 PRD Version History & Diffing

**What:** Full version history for every PRD, with diff views showing exactly what changed between versions. Each version captures not just the text changes but also the analysis delta: which findings were introduced, resolved, or changed severity.

**Why:** PRDs evolve significantly during review cycles. Today, that history is lost in Google Docs version history (which no one reads) or scattered across Slack threads. Structured version history tied to analysis results creates accountability and learning.

**How it works:**
- Every save creates a new version with timestamp and author
- Diff view shows side-by-side or inline text changes (like GitHub's PR diff)
- Analysis diff: "Version 2 resolved 3 security findings but introduced 1 new privacy concern"
- Versions can be tagged: "v1-initial", "v2-post-security-review", "v3-approved"
- Revert to any previous version with one click

**Key capabilities:**
- **Text diff:** See exactly what requirements changed
- **Analysis diff:** See how the risk profile changed across versions
- **Blame view:** Who changed which requirement and when
- **Branching (future):** Create variant PRDs ("PRD-123-option-A" vs "PRD-123-option-B") and compare analysis results

**Builds on:** Existing review storage, PRD parser, review diffing (ROADMAP Phase 4.4)

### 2.2 PRD Branching & Merging

**What:** Allow PMs to create "branches" of a PRD to explore alternative approaches, then compare analysis results side-by-side and merge the winner back.

**Why:** PMs often evaluate multiple approaches to a feature (build vs. buy, phased rollout vs. big bang, different data models). Today, this means maintaining multiple documents and mentally tracking the tradeoffs. Branching makes this structured and analyzable.

**How it works:**
- PM creates a branch from an existing PRD: "PRD-123-branch: Payment via Stripe" vs "PRD-123-branch: Payment via internal"
- Each branch gets its own analysis results
- Comparison view: side-by-side analysis across all five dimensions
- Merge: choose the winning branch and fold it back into the main PRD
- Conflict detection: if both branches modified the same section, highlight for manual resolution

### 2.3 Decision Log

**What:** An append-only log attached to each PRD that captures key decisions, their rationale, who made them, and what information they were based on. Decisions link to specific review findings, comments, or analysis results.

**Why:** Product decisions are often made in meetings, Slack threads, or hallway conversations and then forgotten. A structured decision log creates an audit trail and prevents re-litigating settled decisions.

**How it works:**
- Decisions can be logged manually or auto-captured from review actions (e.g., "Accepted risk: no rate limiting for internal API — decision by @alice on Jan 15, based on finding F-456")
- Each decision has: title, rationale, alternatives considered, decision maker, date, linked findings
- Decision log is searchable across all PRDs: "Show me all decisions about rate limiting"
- Decisions feed into the pattern learner: accepted-risk decisions become patterns for future reviews

---

## Theme 3: PRD Review Workflows (Pull Requests for PMs)

> The "Pull Request" for product requirements — structured review cycles with approvals, gates, and tracked conversations.

### 3.1 Formal PRD Review Requests

**What:** PMs can submit a PRD for formal review, creating a structured review cycle with designated reviewers, deadlines, and approval gates. This is the PM equivalent of a GitHub Pull Request.

**Why:** Today, PRD "reviews" happen informally: a Slack message, a meeting, or a drive-by comment. There's no structured way to request, track, and complete a review across multiple stakeholders. This feature creates that structure.

**How it works:**
- PM clicks "Request Review" on a PRD
- Selects reviewers: individuals and/or teams (Security, Privacy, Engineering Lead, etc.)
- Sets review type: lightweight (async comments) or formal (requires approval)
- Sets deadline
- System runs automated analysis and attaches results to the review request
- Reviewers get notified and see the PRD + analysis in their review queue
- Reviewers can: approve, request changes, or block
- PM sees review status dashboard: "2/4 approvals, 1 change request pending"

**Key capabilities:**
- **Review queue:** Each reviewer sees their pending reviews (like GitHub's PR review queue)
- **Required reviewers:** Configurable rules — "All PRDs touching PII require Privacy team sign-off"
- **Auto-analysis attachment:** Every review request includes the latest multi-dimensional analysis
- **Review summary:** After all reviews complete, a summary of all feedback, decisions, and changes

**Builds on:** Existing collaboration features (validation, comments, assignments), review lifecycle

### 3.2 Approval Gates & Policies

**What:** Configurable policies that determine when a PRD can proceed to implementation. Gates enforce organizational standards automatically.

**Why:** Organizations have compliance and governance requirements for product changes (SOC 2, HIPAA, internal policies). Manual enforcement is inconsistent. Automated gates ensure nothing slips through.

**How it works:**
- Organization configures gate policies:
  - "No PRD with unresolved CRITICAL findings can be approved"
  - "PRDs involving PII require Privacy team approval"
  - "PRDs affecting payments require Security + Compliance sign-off"
  - "PRD quality score must be above 70% to enter review"
- Gates are evaluated automatically when reviewers attempt to approve
- Blocked PRDs show clear reasons: "Blocked: 2 unresolved CRITICAL findings (F-123, F-456)"
- Override mechanism for exceptional cases with audit trail

**Builds on:** Existing review lifecycle, quality scoring, finding severity

### 3.3 Review Analytics

**What:** Analytics dashboard showing review cycle metrics: time to review, review throughput, common blockers, team responsiveness, and review quality over time.

**Why:** Without measurement, review processes degrade. Analytics help PM leads and engineering managers identify bottlenecks and improve the process.

**Key metrics:**
- **Cycle time:** Average time from review request to approval
- **Bottleneck analysis:** Which team/reviewer has the longest queue or response time?
- **Finding resolution rate:** What percentage of findings are resolved before approval vs. accepted as risk?
- **Quality trend:** Are PRDs improving over time? (Quality score trend)
- **Pattern effectiveness:** Which learned patterns are most frequently applied?
- **Top blockers:** Most common reasons PRDs get blocked at gates

---

## Theme 4: Product Intelligence Dashboard

> The "GitHub Insights" for product decisions — org-wide visibility into product health, risk posture, and decision patterns.

### 4.1 Product Health Overview

**What:** A high-level dashboard showing the current state of all product initiatives, their review status, risk profiles, and key metrics. Think of it as a "GitHub organization dashboard" but for product artifacts.

**Why:** Product leaders need a single view into what's being planned, what's been reviewed, where the risks are, and what's blocked. Today, this requires aggregating information from multiple tools.

**Dashboard views:**
- **Active PRDs:** All PRDs in progress, their review status, and risk summary
- **Risk heatmap:** Across all active PRDs, which dimensions have the most unresolved findings?
- **Team workload:** Which teams have the most pending reviews?
- **Recent decisions:** Latest decisions across all PRDs
- **Trending patterns:** Most frequently triggered patterns and organizational blind spots

### 4.2 Impact Graph Visualization

**What:** An interactive visualization of the context graph showing how product entities (services, APIs, data stores, teams) relate to each other. PMs can explore the graph to understand dependencies, data flows, and blast radius of proposed changes.

**Why:** The context graph is the most unique asset Intently builds. Visualizing it makes it accessible to non-technical stakeholders. A PM can see "if I change the user profile service, it affects these 5 downstream services" without reading code.

**How it works:**
- Interactive graph visualization (D3.js or similar)
- Nodes: services, APIs, data stores, teams, PRDs
- Edges: data flows, dependencies, ownership, references
- Filters: show only PII paths, show only external-facing services, show only affected entities for a specific PRD
- Drill-down: click a node to see its history, related findings, and current status
- "Blast radius" mode: highlight all entities affected by a proposed PRD change

**Builds on:** Existing context graph, Phase 1 persistent graph (ROADMAP)

### 4.3 Predictive Risk Scoring

**What:** Before a PM even writes a PRD, predict the likely risk profile based on the type of change, the entities involved, and historical patterns. "You're about to write a PRD that touches the payments API — based on 12 previous PRDs, expect 3-5 security findings and 2 compliance findings."

**Why:** Helps PMs plan better: they can proactively involve the right reviewers, allocate more time for high-risk PRDs, and address known concerns in the first draft.

**How it works:**
- PM describes the feature in 1-2 sentences or selects affected systems
- System queries historical reviews for similar features/entities
- Returns a risk prediction: expected findings by dimension, estimated review time, suggested reviewers
- Links to relevant past reviews: "See how the team handled a similar change in PRD-089"

**Builds on:** Existing pattern learner, context graph, cross-review intelligence (ROADMAP Phase 4)

### 4.4 Organizational Knowledge Base

**What:** A searchable repository of all product decisions, patterns, and lessons learned across the organization. Unlike a wiki, this is automatically built from review activity — no manual curation required.

**Why:** Organizational knowledge about "why we made that decision" or "what the standard approach is for X" is usually trapped in people's heads or buried in old documents. An automatically curated knowledge base surfaces it when relevant.

**How it works:**
- Auto-indexed from: review findings, expert feedback, decision logs, learned patterns
- Search interface: full-text search + semantic search across all product knowledge
- Contextual surfacing: when writing a PRD about authentication, relevant auth decisions and patterns appear automatically
- "Ask the organization" feature: "What's our standard approach for handling GDPR consent?"

**Builds on:** Pattern learner, decision log, semantic pattern matching (ROADMAP Phase 5)

---

## Theme 5: Integrations & Ecosystem

> The "GitHub Apps & Integrations" for product workflows — connect Intently to the tools PMs already use.

### 5.1 Jira / Linear / Shortcut Sync

**What:** Bidirectional sync between Intently and project management tools. When a PRD is approved, automatically create engineering tickets with the right context. When tickets are completed, update the PRD status.

**Why:** PMs live in project management tools. If Intently is separate from where work gets tracked, it becomes another tool to maintain. Deep integration makes it part of the existing workflow.

**How it works:**
- **PRD → Tickets:** Approved PRD generates a set of engineering tickets:
  - One epic for the feature
  - Individual stories for each requirement
  - Findings become tech debt tickets or acceptance criteria
  - Effort estimates map to story points
- **Tickets → PRD:** When tickets are completed, PRD status updates automatically
- **Finding → Ticket:** Individual findings can be pushed as tickets with full context
- Bidirectional linking: ticket links back to PRD, PRD links to tickets

### 5.2 Slack / Teams Integration

**What:** Deep integration with team messaging for notifications, quick actions, and conversational interaction.

**Why:** PMs and reviewers live in Slack/Teams. Notifications pull them into Intently at the right time, and quick actions reduce context switching.

**How it works:**
- **Notifications:** Review requests, approvals, comments, and blocked PRDs trigger Slack messages
- **Quick actions:** Approve, request changes, or comment directly from Slack
- **Conversational analysis:** Post a PRD link in Slack and get an instant risk summary
- **Daily digest:** Summary of review activity, pending items, and new findings
- **Bot commands:** `/intently review <prd-url>`, `/intently status <prd-id>`, `/intently risk <feature-name>`

### 5.3 GitHub / GitLab PR Integration

**What:** When a PRD has been approved and implementation begins, link PRD findings to code changes. When a PR is opened that addresses a PRD, surface relevant findings and requirements in the PR review.

**Why:** This closes the loop between product intent and engineering implementation. Engineers see PRD context in their PR, and PMs see implementation progress linked to their requirements.

**How it works:**
- **PRD → PR comments:** When a PR references a PRD, Intently adds a comment summarizing relevant findings and requirements
- **Requirement traceability:** Map PR code changes to specific PRD requirements: "This PR addresses requirements 1.1, 1.3, and finding F-456"
- **Compliance evidence:** For regulated industries, maintain a traceable chain from requirement → review → approval → implementation → verification
- **Post-implementation review:** After the PR is merged, re-run analysis to verify findings were addressed

**Builds on:** Existing GitHub integration (codebase analysis, PR analysis)

### 5.4 Document Import/Export

**What:** Seamless import from and export to the tools PMs currently use for writing: Google Docs, Notion, Confluence, and Markdown.

**Why:** Adoption barrier is lower if PMs can continue using their preferred writing tools and bring content into Intently for analysis. Over time, as the Intently editor matures, more authoring happens natively.

**How it works:**
- **Import:** Drag-and-drop or API-based import from Google Docs, Notion, Confluence, Markdown files
- **Export:** One-click export of PRDs with analysis results to PDF, Markdown, Confluence page, or Notion page
- **Sync (future):** Two-way sync with Google Docs or Notion — write in either place, analysis runs automatically
- **Batch import:** Import an entire Confluence space or Notion database for bulk analysis

**Builds on:** Existing parsers (Markdown, Notion, Confluence), bulk analysis

---

## Theme 6: Team & Org-Wide Product Governance

> The "GitHub Organizations & Teams" for product management — structure, permissions, and governance at scale.

### 6.1 Team Workspaces

**What:** Dedicated workspaces for product teams with shared context, team-specific patterns, and unified dashboards. Each workspace inherits organizational policies but can add team-specific configurations.

**Why:** Different product teams have different risk profiles, compliance requirements, and review standards. Team workspaces allow customization without losing organizational coherence.

**How it works:**
- Each team gets a workspace with: their PRDs, their review queue, their patterns, their context graph
- Team-specific analysis configuration: "The payments team always runs with HIPAA + PCI-DSS compliance checks"
- Shared organizational patterns are inherited; team patterns are additive
- Team dashboard: their active PRDs, pending reviews, recent decisions, team-specific metrics
- Cross-team visibility: PM leads can see all team workspaces

### 6.2 Role-Based Access & Permissions

**What:** Granular permissions for who can author, review, approve, and configure at each level (organization, team, individual).

**Why:** As adoption grows beyond a single team, governance requires access control. Not everyone should be able to approve a PRD touching payments, and not every PM needs access to every team's work.

**Roles:**
- **PM Author:** Can create, edit, and submit PRDs for review
- **Reviewer:** Can review, comment, and approve/block PRDs
- **Team Lead:** Can configure team workspace, manage team patterns, view team analytics
- **Org Admin:** Can configure organizational policies, gates, integrations, and see all analytics
- **Observer:** Read-only access to PRDs and analysis results

### 6.3 Compliance & Audit Trail

**What:** A complete, immutable audit trail of every product decision, review action, approval, and policy exception. Designed to satisfy SOC 2, HIPAA, and other compliance frameworks.

**Why:** Regulated industries need to prove that product changes went through proper review and approval. Today, this evidence is scattered across email, Slack, and meeting notes. An integrated audit trail is dramatically more efficient.

**How it works:**
- Every action is logged: PRD creation, edits, review requests, comments, approvals, gate overrides, pattern applications
- Audit log is immutable and tamper-evident
- Export audit reports for compliance reviews: "Show all PRDs approved in Q1 2026 that involved PII"
- Configurable retention policies
- Integration with GRC tools (ServiceNow, Drata, Vanta)

### 6.4 Org-Wide Product Standards

**What:** Define and enforce organization-wide product standards: required PRD sections, mandatory review dimensions, naming conventions, and quality thresholds.

**Why:** Consistency across teams reduces review friction and ensures organizational standards are met without manual policing.

**How it works:**
- Org admins define standards: "All PRDs must include a Security Considerations section"
- Standards are enforced in the editor (warnings) and at review gates (blockers)
- Standards evolve based on pattern learning: "12 PRDs were blocked for missing rollback plans — add Rollback Plan as a required section?"
- Standards can be versioned and rolled out incrementally

---

## Prioritization Matrix

Features evaluated on: **Impact** (value to PM workflow), **Feasibility** (builds on existing capabilities), and **Differentiation** (uniqueness vs. existing tools).

| Feature | Impact | Feasibility | Differentiation | Priority |
|---------|--------|-------------|-----------------|----------|
| **1.1** Inline PRD Authoring with AI Assist | High | Medium | Very High | **P0** |
| **1.3** Product-Aware Chat | High | High | Very High | **P0** |
| **3.1** Formal PRD Review Requests | High | High | High | **P0** |
| **2.1** PRD Version History & Diffing | High | High | Medium | **P1** |
| **1.2** Real-Time Analysis While Writing | High | Medium | High | **P1** |
| **4.2** Impact Graph Visualization | High | Medium | Very High | **P1** |
| **5.2** Slack / Teams Integration | High | Medium | Medium | **P1** |
| **3.2** Approval Gates & Policies | Medium | High | High | **P1** |
| **4.1** Product Health Overview | Medium | High | Medium | **P1** |
| **5.1** Jira / Linear Sync | High | Medium | Medium | **P2** |
| **5.3** GitHub PR Integration | High | High | High | **P2** |
| **1.4** PRD Templates Library | Medium | High | Medium | **P2** |
| **2.3** Decision Log | Medium | Medium | High | **P2** |
| **4.3** Predictive Risk Scoring | Medium | Medium | Very High | **P2** |
| **2.2** PRD Branching & Merging | Medium | Low | Very High | **P3** |
| **3.3** Review Analytics | Medium | Medium | Medium | **P3** |
| **4.4** Organizational Knowledge Base | Medium | Low | High | **P3** |
| **5.4** Document Import/Export | Medium | Medium | Low | **P3** |
| **6.1** Team Workspaces | Medium | Low | Medium | **P3** |
| **6.2** Role-Based Access | Medium | Low | Low | **P3** |
| **6.3** Compliance Audit Trail | Medium | Medium | Medium | **P3** |
| **6.4** Org-Wide Product Standards | Low | Medium | Medium | **P3** |

### Recommended Starting Point (P0 Features)

The three P0 features together create the core "Cursor + GitHub for PMs" experience:

1. **Inline PRD Authoring with AI Assist (1.1):** The "Cursor" part — intelligent, context-aware authoring
2. **Product-Aware Chat (1.3):** The "Cmd+L" part — ask anything about your product and codebase
3. **Formal PRD Review Requests (3.1):** The "GitHub PR" part — structured review workflows with approvals

These three features transform Intently from a one-shot analysis tool into a **daily-use workspace** for product managers. They create the usage pattern (open Intently → write PRD → request review → get approval) that makes everything else valuable.

---

## Summary

Intently already has the hardest-to-build components: multi-dimensional analysis, codebase understanding, context graph, pattern learning, and collaboration infrastructure. The features proposed here layer a PM-centric workflow and experience on top of these foundations.

The progression is:

1. **P0 — Core Workspace:** AI-powered editor + chat + review workflows (makes Intently a daily tool)
2. **P1 — Enhanced Experience:** Version history, real-time analysis, graph visualization, messaging integration (makes it indispensable)
3. **P2 — Ecosystem Integration:** PM tool sync, GitHub integration, templates, predictions (makes it the system of record)
4. **P3 — Enterprise Scale:** Team workspaces, RBAC, compliance, org-wide standards (makes it enterprise-ready)

Each layer builds on the previous one, and the existing Intently infrastructure provides a significant head start for all of them.

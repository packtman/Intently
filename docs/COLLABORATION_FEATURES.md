# Collaboration Features Roadmap

This document outlines the collaborative review features for the Context Graph platform, enabling teams to validate AI-generated findings and build institutional knowledge over time.

**Last Updated:** January 2026

**Platform Support:** Both Desktop App and Web/SaaS

---

## Table of Contents

1. [Overview](#overview)
2. [Feature Flags](#feature-flags)
3. [Phase 0: Foundation Layer](#phase-0-foundation-layer) - COMPLETED
4. [Phase 1: Finding Validation](#phase-1-finding-validation) - COMPLETED
5. [Phase 2: Comments System](#phase-2-comments-system) - COMPLETED
6. [Phase 3: Team Assignment](#phase-3-team-assignment) - COMPLETED
7. [Phase 4: Expert Feedback](#phase-4-expert-feedback) - COMPLETED
8. [Phase 5: Advanced Features](#phase-5-advanced-features) - COMPLETED

---

## Overview

The collaboration features transform Context Graph from a one-shot analysis tool into a collaborative governance platform where AI and human experts work together. Key principles:

- **Human in the Loop**: AI provides baseline analysis, humans validate and refine
- **Expert Tokens**: Capture expert judgment to improve future analysis
- **Institutional Knowledge**: Decisions compound over time, not reset
- **Backward Compatible**: All features are additive and feature-flagged

---

## Feature Flags

All collaboration features are disabled by default. Enable via environment variables:

```bash
# Phase 1
export FEATURE_FINDING_VALIDATION=true

# Phase 2
export FEATURE_COMMENTS=true

# Phase 3
export FEATURE_TEAM_ASSIGNMENT=true

# Phase 4
export FEATURE_EXPERT_FEEDBACK=true
export FEATURE_PATTERN_LEARNING=true

# Phase 5
export FEATURE_REVIEW_LIFECYCLE=true
export FEATURE_CROSS_TEAM_REQUESTS=true
export FEATURE_CONSENSUS_MODE=true
```

Check enabled features via API:
```bash
curl http://localhost:8000/api/collaboration/features
```

---

## Phase 0: Foundation Layer

**Status: COMPLETED**

### 0.1 Storage Abstraction Layer

**Purpose:** Enable pluggable storage backends for future persistence.

**Files Created:**
- `src/context_graph/storage/base.py` - Abstract interfaces
- `src/context_graph/storage/memory.py` - In-memory implementation

**Example Usage:**
```python
from context_graph.storage import InMemoryCollaborationStorage

storage = InMemoryCollaborationStorage()

# Save a validation
await storage.save_finding_validation(
    review_id="abc-123",
    finding_id="finding-456",
    status="validated",
    validator_id="user-1",
    validator_team="security",
    notes="Confirmed this is a real issue"
)

# Retrieve validations
validations = await storage.get_validations_for_review("abc-123")
```

### 0.2 Feature Flag System

**Purpose:** Enable incremental rollout without breaking existing functionality.

**Files Created:**
- `src/context_graph/config/features.py`

**Example Usage:**
```python
from context_graph.config import get_features

features = get_features()

if features.enable_finding_validation:
    # Show validation UI
    pass

# Check all enabled features
print(features.get_enabled_features())
# Output: ['finding_validation', 'comments']
```

### 0.3 Model Extensions

**Purpose:** Add collaboration fields to finding models without breaking existing code.

**Files Modified:**
- `src/context_graph/core/models.py`

**New Fields (all optional with defaults):**
```python
@dataclass
class SecurityFinding:
    # ... existing fields ...
    
    # NEW: Collaboration fields
    validation_status: str = "pending"
    validated_by: str | None = None
    validated_at: datetime | None = None
    validation_notes: str | None = None
    assigned_team: str | None = None
    assigned_user: str | None = None
    comment_count: int = 0
```

### 0.4 TypeScript Types

**Purpose:** Frontend type definitions for collaboration data.

**Files Modified:**
- `context graph Desktop app/src/types/index.ts` (Desktop App)
- `Context graph/frontend/src/types/index.ts` (Web/SaaS)

**New Types:**
```typescript
interface CollaborationFeatures {
  validation: boolean
  team_assignment: boolean
  comments: boolean
  expert_feedback: boolean
  // ...
}

interface FindingValidation {
  id: string
  finding_id: string
  status: 'validated' | 'rejected' | 'needs_discussion' | ...
  validator_id: string
  validator_team: string
  notes: string
  validated_at: string
}
```

---

## Phase 1: Finding Validation

**Status: COMPLETED**

### Feature Description

Allows team members to validate, reject, or flag AI-generated findings for discussion. This is the core feedback mechanism that enables human oversight of AI analysis.

### Validation Statuses

| Status | Description | Use Case |
|--------|-------------|----------|
| `pending` | Not yet reviewed | Default state |
| `validated` | Finding is accurate | Confirms AI assessment |
| `rejected` | False positive | AI was wrong |
| `needs_discussion` | Requires team input | Cross-functional concern |
| `accepted_risk` | Valid but accepted | Business decision to proceed |
| `deferred` | Out of scope | Valid but not for this release |

### API Endpoints

**Validate a Finding:**
```bash
POST /api/collaboration/reviews/{review_id}/findings/{finding_id}/validate

Request:
{
  "status": "validated",
  "notes": "Confirmed - we need to add rate limiting here",
  "validator_id": "user-123",
  "validator_team": "security"
}

Response:
{
  "id": "val-abc-123",
  "finding_id": "finding-456",
  "review_id": "review-789",
  "status": "validated",
  "validator_id": "user-123",
  "validator_team": "security",
  "notes": "Confirmed - we need to add rate limiting here",
  "validated_at": "2026-01-10T14:30:00Z",
  "message": "Finding validated successfully"
}
```

**Get Validation Status:**
```bash
GET /api/collaboration/reviews/{review_id}/findings/{finding_id}/validation

Response:
{
  "finding_id": "finding-456",
  "review_id": "review-789",
  "status": "validated",
  "validator_id": "user-123",
  "validator_team": "security",
  "validated_at": "2026-01-10T14:30:00Z",
  "validated": true
}
```

**Get All Validations for Review:**
```bash
GET /api/collaboration/reviews/{review_id}/validations

Response:
{
  "review_id": "review-789",
  "validations": {
    "finding-456": { ... },
    "finding-789": { ... }
  },
  "stats": {
    "total": 15,
    "pending": 5,
    "validated": 7,
    "rejected": 2,
    "needs_discussion": 1
  }
}
```

### UI Components

**Available in both Desktop App and Web/SaaS:**

**FindingValidationPanel:**
- Expandable panel within each finding
- Status selection with descriptions
- Notes/justification text area
- Validator info display
- Loading and error states

**ValidationStatusBadge:**
- Compact badge for finding list views
- Color-coded by status
- Shows at-a-glance validation state

**Files:**
- Desktop: `context graph Desktop app/src/components/collaboration/`
- Web: `Context graph/frontend/src/components/collaboration/`

### Example Workflow

1. **PM submits PRD** for review
2. **AI analyzes** and generates 12 findings
3. **Security team** reviews findings assigned to them:
   - Finding 1: "Missing rate limiting" -> **Validated** with note "Add to sprint backlog"
   - Finding 2: "SQL injection risk" -> **Rejected** with note "We use parameterized queries"
   - Finding 3: "Sensitive data in logs" -> **Needs Discussion** with note "Need Privacy team input"
4. **Dashboard shows** 10 validated, 1 rejected, 1 pending discussion

---

## Phase 2: Comments System

**Status: COMPLETED**

### Feature Description

Enables threaded discussions on any finding. Teams can share context, ask questions, and collaborate asynchronously.

### API Endpoints

**Add Comment:**
```bash
POST /api/collaboration/reviews/{review_id}/findings/{finding_id}/comments

Request:
{
  "content": "I think this only applies to the admin endpoints, not user-facing ones",
  "author_id": "user-456",
  "author_name": "Jane Smith",
  "author_team": "engineering",
  "parent_comment_id": null  // For replies, set to parent comment ID
}

Response:
{
  "id": "comment-123",
  "finding_id": "finding-456",
  "author_id": "user-456",
  "author_name": "Jane Smith",
  "author_team": "engineering",
  "content": "I think this only applies to the admin endpoints...",
  "parent_comment_id": null,
  "created_at": "2026-01-10T15:00:00Z"
}
```

**Get Comments:**
```bash
GET /api/collaboration/reviews/{review_id}/findings/{finding_id}/comments

Response:
[
  {
    "id": "comment-123",
    "author_name": "Jane Smith",
    "author_team": "engineering",
    "content": "I think this only applies to the admin endpoints...",
    "created_at": "2026-01-10T15:00:00Z"
  },
  {
    "id": "comment-124",
    "author_name": "Bob Wilson",
    "author_team": "security",
    "content": "Good point - let me check the scope",
    "parent_comment_id": "comment-123",  // Reply to Jane
    "created_at": "2026-01-10T15:05:00Z"
  }
]
```

**Get Comment Counts:**
```bash
GET /api/collaboration/reviews/{review_id}/comment-counts

Response:
{
  "finding-456": 3,
  "finding-789": 1,
  "finding-012": 0
}
```

### UI Components

**CommentsThread:**
- Expandable panel within each finding
- Threaded comment display with replies
- Real-time comment submission
- Author info with team badges
- Relative timestamps

**CommentCountBadge:**
- Compact badge showing comment count on finding rows
- Only displays when count > 0

**Files:**
- Web: `Context graph/frontend/src/components/collaboration/CommentsThread.tsx`

### Example Workflow

1. Security team member sees a finding about "Insecure direct object reference"
2. They comment: "@engineering Can you confirm if we have ownership checks here?"
3. Engineer replies: "We check ownership in the middleware, but not for bulk endpoints"
4. Security responds: "Thanks - validated with note about bulk endpoint gap"

---

## Phase 3: Team Assignment

**Status: COMPLETED**

### Feature Description

Route findings to appropriate team queues based on dimension, severity, or category. Teams see their assigned findings in a dedicated view.

### API Endpoints

**Assign Finding:**
```bash
POST /api/collaboration/reviews/{review_id}/findings/{finding_id}/assign

Request:
{
  "team": "privacy",
  "user_id": "user-789",  // Optional: specific user
  "assigned_by": "user-123"
}

Response:
{
  "id": "assign-123",
  "finding_id": "finding-456",
  "review_id": "review-789",
  "team": "privacy",
  "user_id": "user-789",
  "assigned_by": "user-123",
  "assigned_at": "2026-01-10T16:00:00Z"
}
```

**Get Team Queue:**
```bash
GET /api/collaboration/teams/security/queue

Response:
[
  {
    "id": "assign-123",
    "finding_id": "finding-456",
    "review_id": "review-789",
    "team": "security",
    "assigned_at": "2026-01-10T16:00:00Z"
  },
  {
    "id": "assign-124",
    "finding_id": "finding-012",
    "review_id": "review-999",
    "team": "security",
    "assigned_at": "2026-01-10T14:00:00Z"
  }
]
```

### Auto-Assignment Rules (Planned)

```yaml
# Future: configurable routing rules
assignment_rules:
  - dimension: security
    route_to: security-team
  - dimension: privacy
    route_to: privacy-team
  - dimension: compliance
    severity: [critical, high]
    route_to: compliance-team
  - category: authentication
    route_to: identity-team
```

### UI Components

**TeamAssignmentPanel:**
- Expandable panel within each finding
- Team selection grid with icons and descriptions
- Suggested team based on finding dimension
- Current assignment display
- Reassignment support

**AssignmentBadge:**
- Compact badge showing team assignment on finding rows
- Color-coded by team type

**TeamQueuePage:**
- Dedicated page for viewing team queue
- Severity distribution stats
- Filtered list of assigned findings
- Links to review findings

**Files:**
- Web: `Context graph/frontend/src/components/collaboration/TeamAssignmentPanel.tsx`
- Web: `Context graph/frontend/src/pages/TeamQueue.tsx`

**Route:** `/teams/{team}/queue`

### Example Workflow

1. New PRD review generates 15 findings across 5 dimensions
2. **Auto-routing** (when enabled):
   - 6 security findings -> Security Team queue
   - 4 privacy findings -> Privacy/DPO Team queue
   - 3 compliance findings -> GRC Team queue
   - 2 engineering findings -> Engineering Lead queue
3. Each team sees their queue on login
4. Team lead can reassign findings to specific team members

---

## Phase 4: Expert Feedback

**Status: COMPLETED**

### Feature Description

Capture expert corrections and reasoning when they disagree with AI findings. This data feeds into pattern learning to improve future analysis.

### Feedback Types

| Type | Description | Example |
|------|-------------|---------|
| `accuracy` | Was the finding correct? | "This is a false positive because..." |
| `severity` | Was the severity appropriate? | "Should be HIGH not MEDIUM because..." |
| `recommendation` | Was the recommendation helpful? | "Better approach would be..." |
| `context` | What did the AI miss? | "AI didn't consider that we have..." |

### API Endpoints

**Submit Feedback:**
```bash
POST /api/collaboration/reviews/{review_id}/findings/{finding_id}/feedback

Request:
{
  "feedback_type": "severity",
  "original_value": "medium",
  "expert_value": "high",
  "expert_id": "user-123",
  "expert_team": "security",
  "reasoning": "This endpoint is externally accessible and handles payment data, so the impact is higher than the AI assessed"
}

Response:
{
  "id": "feedback-123",
  "finding_id": "finding-456",
  "feedback_type": "severity",
  "original_value": "medium",
  "expert_value": "high",
  "reasoning": "This endpoint is externally accessible...",
  "created_at": "2026-01-10T17:00:00Z"
}
```

**Get Feedback Stats (Pattern Learning):**
```bash
GET /api/collaboration/feedback/stats

Response:
{
  "total_feedback": 156,
  "by_type": {
    "accuracy": 89,
    "severity": 34,
    "recommendation": 22,
    "context": 11
  },
  "by_team": {
    "security": 78,
    "privacy": 45,
    "engineering": 33
  },
  "common_rejection_reasons": {
    "internal service with network isolation": 12,
    "already mitigated by existing control": 8,
    "not applicable to our architecture": 6
  }
}
```

### UI Components

**ExpertFeedbackForm:**
- Expandable panel within each finding
- Feedback type selection (accuracy, severity, recommendation, context)
- Side-by-side original vs expert value display
- Severity adjustment buttons
- Required reasoning field
- Previous feedback history display

**FeedbackCountBadge:**
- Compact badge showing expert feedback count

**Files:**
- Web: `Context graph/frontend/src/components/collaboration/ExpertFeedbackForm.tsx`

### Example Workflow

1. AI generates finding: "Missing CSRF protection" (Medium severity)
2. Security expert reviews and notes:
   - This is an API-only endpoint (no browser clients)
   - We use token-based auth, not cookies
3. Expert submits feedback:
   - Type: `accuracy`
   - Original: "Missing CSRF protection"
   - Expert: "Not applicable - API-only endpoint with token auth"
   - Reasoning: "CSRF attacks require cookie-based sessions..."
4. System records this pattern for future reference
5. Future similar findings may auto-suggest: "Similar finding was rejected 12 times for API-only endpoints"

---

## Phase 5: Advanced Features

**Status: COMPLETED**

### 5.1 Review Lifecycle Management

**Feature Flag:** `FEATURE_REVIEW_LIFECYCLE=true`

Track reviews through approval gates:

```
Draft -> In Review -> Team Review Complete -> Awaiting Sign-off -> Approved
                                                              \-> Blocked
```

**Configurable Gates:**
- Cannot proceed if Critical findings unvalidated
- Require Security + Privacy sign-off for PII features
- Auto-notify stakeholders at each stage

### 5.2 Cross-Team Review Requests

**Feature Flag:** `FEATURE_CROSS_TEAM_REQUESTS=true`

Request input from another team:

```bash
POST /api/collaboration/reviews/{review_id}/findings/{finding_id}/request-review

Request:
{
  "requesting_team": "security",
  "target_team": "architecture",
  "question": "Can you assess the scalability impact of adding this middleware?",
  "deadline": "2026-01-15"
}
```

### 5.3 Consensus Mode

**Feature Flag:** `FEATURE_CONSENSUS_MODE=true`

Require validation from multiple teams for critical findings:

```yaml
consensus_rules:
  - severity: critical
    require_teams: [security, privacy]
  - dimension: compliance
    framework: hipaa
    require_teams: [compliance, legal]
```

### 5.4 Pattern Learning (Expert Tokens)

**Feature Flag:** `FEATURE_PATTERN_LEARNING=true`

Extract reusable judgment from expert feedback:

```json
{
  "pattern": "CSRF finding on API-only endpoint",
  "decision": "Not applicable",
  "conditions": [
    "Endpoint serves API clients only (no browser)",
    "Token-based authentication (not cookie)",
    "No state-changing GET requests"
  ],
  "reasoning": "CSRF attacks require cookie-based sessions...",
  "times_applied": 12,
  "created_from_feedback": ["feedback-123", "feedback-456"]
}
```

Future findings matching this pattern would show:
> "Similar findings have been rejected 12 times. Common reason: API-only endpoint with token auth"

### Phase 5 API Endpoints

**Review Lifecycle:**
```bash
# Update lifecycle state
POST /api/collaboration/reviews/{review_id}/lifecycle
{
  "state": "team_review",
  "updated_by": "user-123",
  "notes": "Assigned to teams for validation"
}

# Get current state
GET /api/collaboration/reviews/{review_id}/lifecycle

# Get state history
GET /api/collaboration/reviews/{review_id}/lifecycle/history
```

**Cross-Team Requests:**
```bash
# Create request
POST /api/collaboration/reviews/{review_id}/requests
{
  "finding_id": "finding-456",
  "requesting_team": "security",
  "target_team": "architecture",
  "question": "Can you assess the scalability impact?",
  "requested_by": "user-123",
  "deadline": "2026-01-15"
}

# Get requests for review
GET /api/collaboration/reviews/{review_id}/requests

# Get requests for team
GET /api/collaboration/teams/{team}/requests

# Respond to request
POST /api/collaboration/requests/{request_id}/respond
{
  "response": "The proposed design should scale to 10k RPS...",
  "responded_by": "user-456"
}
```

**Consensus Mode:**
```bash
# Add vote
POST /api/collaboration/reviews/{review_id}/findings/{finding_id}/consensus
{
  "team": "security",
  "vote": "approve",
  "voter_id": "user-123",
  "notes": "Confirmed critical severity"
}

# Get consensus status
GET /api/collaboration/reviews/{review_id}/findings/{finding_id}/consensus
```

**Pattern Learning:**
```bash
# Save pattern
POST /api/collaboration/patterns
{
  "pattern_type": "false_positive",
  "pattern_signature": "CSRF on API-only endpoint",
  "decision": "not_applicable",
  "conditions": ["API-only", "Token auth"],
  "reasoning": "...",
  "source_feedback_ids": ["fb-1", "fb-2"]
}

# Find similar patterns
GET /api/collaboration/patterns/similar?pattern_type=false_positive&pattern_signature=CSRF%20API

# Get pattern insights
GET /api/collaboration/patterns/insights

# Get feedback stats
GET /api/collaboration/feedback/stats
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React)                           │
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │   Desktop App       │    │   Web/SaaS App      │            │
│  │   (Electron)        │    │   (Browser)         │            │
│  └─────────────────────┘    └─────────────────────┘            │
│            │                          │                         │
│            └──────────┬───────────────┘                         │
│                       ▼                                         │
├─────────────────────────────────────────────────────────────────┤
│  Shared Component Architecture:                                 │
│  ReviewDetail.tsx                                               │
│  ├── FindingRow                                                 │
│  │   ├── ValidationStatusBadge (Phase 1) - COMPLETED           │
│  │   ├── AssignmentBadge (Phase 3) - COMPLETED                 │
│  │   ├── CommentCountBadge (Phase 2) - COMPLETED               │
│  │   └── FindingValidationPanel (Phase 1) - COMPLETED          │
│  │       ├── TeamAssignmentPanel (Phase 3) - COMPLETED         │
│  │       ├── CommentsThread (Phase 2) - COMPLETED              │
│  │       └── ExpertFeedbackForm (Phase 4) - COMPLETED          │
│  └── TeamQueuePage (Phase 3) - COMPLETED                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                          │
├─────────────────────────────────────────────────────────────────┤
│  /api/reviews/* (existing)                                      │
│  /api/collaboration/* (new)                                     │
│  ├── /features                    GET feature flags             │
│  ├── /reviews/{id}/findings/{id}/validate    POST validation    │
│  ├── /reviews/{id}/findings/{id}/comments    GET/POST comments  │
│  ├── /reviews/{id}/findings/{id}/assign      POST assignment    │
│  ├── /reviews/{id}/findings/{id}/feedback    POST feedback      │
│  └── /teams/{team}/queue          GET team queue                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  ReviewStorage (reviews, status)                                │
│  CollaborationStorage (validations, comments, assignments)      │
│  ├── InMemoryStorage (current)                                  │
│  ├── SQLiteStorage (planned)                                    │
│  └── PostgresStorage (planned)                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Testing

### Enable Features for Testing

```bash
# Enable all features
export FEATURE_FINDING_VALIDATION=true
export FEATURE_COMMENTS=true
export FEATURE_TEAM_ASSIGNMENT=true
export FEATURE_EXPERT_FEEDBACK=true

# Start backend
cd "Context graph"
context-graph serve

# Start Desktop App
cd "context graph Desktop app"
npm run dev

# OR Start Web/SaaS App
cd "Context graph/frontend"
npm run dev
```

### Verify Feature Flags

```bash
curl http://localhost:8000/api/collaboration/features | jq
```

### Test Validation Flow

```bash
# 1. Create a review (existing flow)
# 2. Get a finding ID from the dashboard
# 3. Validate the finding
curl -X POST http://localhost:8000/api/collaboration/reviews/{review_id}/findings/{finding_id}/validate \
  -H "Content-Type: application/json" \
  -d '{
    "status": "validated",
    "notes": "Test validation",
    "validator_id": "test-user",
    "validator_team": "security"
  }'
```

---

## Rollback

If issues occur, disable features without code changes:

```bash
# Disable all collaboration features
unset FEATURE_FINDING_VALIDATION
unset FEATURE_COMMENTS
unset FEATURE_TEAM_ASSIGNMENT
unset FEATURE_EXPERT_FEEDBACK

# Restart backend
context-graph serve
```

The system will continue to function with all existing review capabilities intact.


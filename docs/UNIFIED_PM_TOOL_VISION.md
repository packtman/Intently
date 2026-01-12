# Context Graph: Cursor for PMs (with Expert Assist)

**Status:** Planning  
**Author:** Product Team  
**Last Updated:** January 2026

---

## The Philosophy

### Primary Experience (90% of usage)
**PM uploads PRD -> Gets predicted feedback -> Fixes PRD -> Becomes smarter**

The tool makes PMs better by predicting what cross-functional teams will ask, grounded in actual codebase analysis.

### Secondary Experience (10% of usage)
**PM is unsure about a prediction -> Pings an expert -> Gets quick validation -> System learns**

When a PM needs real human input, they can "ask an expert" - but this should feel like a quick Slack DM, NOT like creating a Jira ticket.

---

## PM Journey (End-to-End)

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. PM BRINGS PRD                                                       │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│     │ Paste    │ │ Upload   │ │ Google   │ │ Notion   │               │
│     │ Text     │ │ .md/.doc │ │ Docs     │ │ Link     │               │
│     └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│                          │                                              │
│                          ▼                                              │
│  2. TOOL ANALYZES (30-60 seconds)                                       │
│     • Parses PRD structure                                              │
│     • Scans connected codebase                                          │
│     • Generates predicted questions                                     │
│     • Creates diff-style suggestions                                    │
│                          │                                              │
│                          ▼                                              │
│  3. PM REVIEWS SUGGESTIONS                                              │
│     • See current PRD state (context)                                   │
│     • See suggested changes (green additions, red removals)             │
│     • Accept / Edit / Reject each suggestion                            │
│     • Or bulk accept by team/severity                                   │
│                          │                                              │
│                          ▼                                              │
│  4. PRD UPDATED                                                         │
│     • Changes applied instantly                                         │
│     • Download updated PRD                                              │
│     • Or sync back to Google Docs/Notion                                │
│     • Undo available for mistakes                                       │
│                          │                                              │
│                          ▼                                              │
│  5. SHARE WITH STAKEHOLDERS                                             │
│     • PRD is now more complete                                          │
│     • Fewer surprises in review meetings                                │
│     • Faster approval cycles                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### PRD Input Formats

| Format | How It Works | Sync Back? |
|--------|--------------|------------|
| **Paste text** | Copy/paste PRD content directly | Download only |
| **Upload file** | .md, .txt, .docx supported | Download only |
| **Google Docs** | Paste sharing link, we fetch content | Yes, auto-sync |
| **Notion** | Paste page link, we fetch content | Yes, auto-sync |
| **Confluence** | Paste page URL (requires setup) | Yes, auto-sync |

**First-time experience:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  START NEW ANALYSIS                                                     │
│                                                                         │
│  Bring your PRD:                                                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  Paste your PRD text here, or...                                │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Or connect from:                                                       │
│  [Google Docs URL]  [Notion URL]  [Upload File]                        │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────      │
│                                                                         │
│  Codebase: acme-corp/backend (connected)                    [Change]    │
│                                                                         │
│  [Analyze PRD]                                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Codebase Connection (One-Time Setup)

**Who sets this up?** Engineering or DevOps, once per team. PMs never need to touch git.

**How it works:**
1. Admin connects GitHub/GitLab repository
2. Tool indexes codebase (runs nightly or on-demand)
3. PMs select which codebase to analyze against

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CODEBASE SETTINGS (Admin Only)                                         │
│                                                                         │
│  Connected repositories:                                                │
│                                                                         │
│  ☑ acme-corp/backend        Last indexed: 2 hours ago      [Re-index]  │
│  ☑ acme-corp/frontend       Last indexed: 2 hours ago      [Re-index]  │
│  ☐ acme-corp/mobile-app     Not indexed                    [Index Now] │
│                                                                         │
│  [+ Connect New Repository]                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**For PMs, it's just a dropdown:**
```
Analyze against: [acme-corp/backend ▼]
                  ├─ acme-corp/backend
                  ├─ acme-corp/frontend  
                  └─ acme-corp/mobile-app
```

### Re-Analysis (Continuous Improvement)

The tool supports iterative improvement:

| Trigger | What Happens |
|---------|--------------|
| **Manual re-analyze** | PM clicks "Re-analyze" after editing PRD |
| **Auto on sync** | If Google Docs/Notion synced, re-analyzes on significant changes |
| **After accepting changes** | Shows remaining gaps (if any) |

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PRD UPDATED                                              [Re-analyze]  │
│                                                                         │
│  You accepted 6 changes. PRD Score: 56% -> 84%                          │
│                                                                         │
│  Want to check for more improvements?                                   │
│  [Re-analyze Now]  [I'm Done]                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What This Is NOT

| Anti-Pattern | Why It's Wrong | Our Approach |
|--------------|----------------|--------------|
| **Team Queues** | Feels like ticketing | No queues. Experts get pings, not assignments |
| **Formal Assignment** | Creates workflow overhead | PM asks specific person, not "assign to security team" |
| **Lifecycle States** | Process over value | PRD is either "in progress" or "ready" - that's it |
| **Consensus Voting** | Meeting culture in a tool | One expert opinion is enough for most cases |
| **Comment Threads** | Becomes a chat app | Quick notes, not discussions |

---

## The Unified Model

### Level 1: Predicted Feedback (No Human Needed)

```
PM uploads PRD
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  PREDICTED CROSS-FUNCTIONAL FEEDBACK                │
│                                                     │
│  Engineering will ask: "What about sessions?"       │
│  Because: session_manager.py:78 stores sessions...  │
│                                                     │
│  ┌─ PRD Change (line 45) ─────────────────────────┐ │
│  │   - JWT tokens for session management          │ │
│  │ + ### Session Migration              [GREEN]   │ │
│  │ + - Invalidate all sessions on deploy[GREEN]   │ │
│  └────────────────────────────────────────────────┘ │
│  [Accept] [Reject] [Edit]                           │
│                                                     │
│  ... 6 more suggested changes                       │
│                                                     │
│  [Accept All (7)]  [Accept Blockers (4)]            │
└─────────────────────────────────────────────────────┘
         │
         ▼
PM accepts changes, PRD is updated automatically
```

**This is the core value.** Like Cursor for code, one click to accept or reject each suggestion. Bulk accept for efficiency.

---

### Level 2: Quick Expert Ping (When PM Needs Validation)

When a PM isn't sure if a prediction is correct, or needs a human sanity check:

```
┌─────────────────────────────────────────────────────┐
│  [BLOCKER] "Rate limiting doesn't exist"            │
│                                                     │
│  Because: No rate_limit*, throttle* found...        │
│                                                     │
│  PM thinks: "Wait, I think DevOps set this up       │
│  last month. Let me check with someone."            │
│                                                     │
│  [Ask Expert] ← Not "Assign to Team"                │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Quick Ask                                          │
│                                                     │
│  To: [Search: Bob (DevOps), Sarah (Security)...]    │
│                                                     │
│  Question (pre-filled):                             │
│  "Tool says rate limiting doesn't exist. Is this    │
│  correct, or did we add it recently?"               │
│                                                     │
│  [Send Quick Ask]                                   │
└─────────────────────────────────────────────────────┘
```

**Key difference from ticketing:**
- PM picks a specific person (not a team queue)
- Pre-filled question (not a blank form)
- Expectation: quick response, not a formal review

---

### Level 3: Expert Response (Lightweight)

The expert receives a notification (email/Slack, not a queue):

```
┌─────────────────────────────────────────────────────┐
│  Quick Ask from Alice (PM)                          │
│                                                     │
│  Re: User Auth PRD                                  │
│                                                     │
│  "Tool says rate limiting doesn't exist. Is this    │
│  correct, or did we add it recently?"               │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ [✓ Correct]  [✗ Wrong]  [Partially Right]   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Quick note (optional):                             │
│  ┌─────────────────────────────────────────────┐   │
│  │ "We added rate limiting to the API gateway  │   │
│  │  last sprint. It's in infra/, not the app." │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [Submit]                                           │
└─────────────────────────────────────────────────────┘
```

**Key difference from ticketing:**
- One-click response options (not a form to fill)
- Optional note (not required fields)
- No workflow after this (no "close ticket" step)

---

### Level 4: System Learns (Background)

Every expert response improves future predictions:

```
Expert said "Wrong - rate limiting exists in infra/"
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  PATTERN LEARNED                                    │
│                                                     │
│  Pattern: "Rate limiting in API gateway/infra"      │
│  Applies when: rate limiting not found in app code  │
│  Correction: Check infra/ and gateway configs       │
│                                                     │
│  Next time similar PRD is analyzed:                 │
│  "Rate limiting not found in app code, but your     │
│  codebase has API gateway patterns in infra/ -      │
│  you may have rate limiting there."                 │
└─────────────────────────────────────────────────────┘
```

**This is how the tool gets smarter without becoming a ticketing system.**

---

## Feature Breakdown

### Core Features (PM-Focused)

| Feature | Description | Feels Like |
|---------|-------------|------------|
| **Predicted Feedback** | AI predicts what teams will ask | Cursor autocomplete |
| **Code Evidence** | Every prediction grounded in code | Cursor showing context |
| **Diff-Style Suggestions** | Current state (red) vs suggested fix (green) | Cursor inline diff |
| **Accept/Reject Changes** | One-click to apply suggested PRD changes | Cursor accept change |
| **Bulk Accept** | Accept all or filtered subset of suggestions | Cursor accept all |
| **PRD Quality Score** | Overall readiness assessment | Lint errors |
| **Effort Estimation** | Code-grounded time estimates | Complexity analysis |

### Expert Assist Features (Lightweight Collaboration)

| Feature | Description | Feels Like |
|---------|-------------|------------|
| **Quick Ask** | Ping specific expert for validation | Slack DM |
| **One-Click Response** | Expert validates with minimal effort | Emoji reaction |
| **Expert Note** | Optional context for learning | Slack reply |
| **Pattern Learning** | Responses improve future predictions | Background training |

---

## Diff-Style PRD Suggestions (Core UX)

**The key insight: PRD changes should feel exactly like code changes in Cursor.**

When the tool identifies a gap, it doesn't just tell you what's missing - it shows you exactly what to change in your PRD, with deletions in red and additions in green.

### Why Diff View Matters

| Traditional Approach | Our Approach |
|---------------------|--------------|
| "Add a section about session handling" | Shows exact text to add, where to add it |
| PM has to figure out what to write | PM just reviews and accepts |
| Copy-paste from suggestion box | One-click apply directly to PRD |
| Manual, error-prone | Automatic, precise |

### The Diff Experience

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SUGGESTED PRD CHANGE                                          1 of 7   │
│                                                                         │
│  Section: ## Technical Requirements                                     │
│                                                                         │
│  ┌─ Current State (line 45-47) ─────────────────────────────────────┐  │
│  │ - User authentication via OAuth 2.0                              │  │
│  │ - Support for Google and GitHub providers                        │  │
│  │ - JWT tokens for session management                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─ Suggested Change ───────────────────────────────────────────────┐  │
│  │ - User authentication via OAuth 2.0                              │  │
│  │ - Support for Google and GitHub providers                        │  │
│  │ - JWT tokens for session management                              │  │
│  │ + ### Session Migration                                 [GREEN]  │  │
│  │ + - Existing sessions: Invalidate all on deploy         [GREEN]  │  │
│  │ + - Users will need to re-login after migration         [GREEN]  │  │
│  │ + - Grace period: 24 hours warning before invalidation  [GREEN]  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Why: session_manager.py:78 stores sessions with user_id. Your PRD     │
│  doesn't specify what happens to these during migration.                │
│                                                                         │
│  [Accept]  [Reject]  [Edit Before Accepting]  [Ask Expert]             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Diff Types

**1. Addition (most common)** - New content to add
```
  ## Security Requirements
  - Input validation on all endpoints
+ - Rate limiting: 100 requests/minute per user    [GREEN]
+ - Threat model documented in Appendix A          [GREEN]
```

**2. Modification** - Existing content needs clarification
```
- Data retention: Standard policy                  [RED]
+ Data retention: 90 days for user data,           [GREEN]
+                 7 years for audit logs           [GREEN]
```

**3. Restructure** - Content exists but needs reorganization
```
- Edge cases handled as needed                     [RED]
+ ### Edge Cases                                   [GREEN]
+ - Empty cart checkout: Show error message        [GREEN]
+ - Concurrent edits: Last-write-wins              [GREEN]
+ - Network timeout: Retry with exponential backoff[GREEN]
```

### Accept Actions

**Single Accept**
- Click "Accept" on any suggestion
- PRD is updated immediately
- Suggestion marked as applied

**Bulk Accept**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  7 SUGGESTED CHANGES                                                    │
│                                                                         │
│  ☑ Session handling addition (Engineering)                              │
│  ☑ Rate limiting section (Security)                                     │
│  ☑ Data retention clarification (Privacy)                               │
│  ☐ Error handling details (Engineering)        ← PM unchecked this     │
│  ☑ Threat model reference (Security)                                    │
│  ☑ Rollback procedure (Infra)                                           │
│  ☑ Monitoring requirements (Infra)                                      │
│                                                                         │
│  [Accept Selected (6)]  [Accept All (7)]  [Review One by One]          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Filter by Team**
```
Accept all from: [Engineering (3)] [Security (2)] [Privacy (1)] [Infra (1)]
```

**Filter by Severity**
```
Accept all: [Blockers Only (4)] [Blockers + Likely (6)] [All (7)]
```

### After Bulk Accept

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PRD UPDATED                                                    [Undo]  │
│                                                                         │
│  6 changes applied to your PRD:                                         │
│  - Added "Session Migration" section (line 48)                          │
│  - Added "Rate Limiting" to Security Requirements (line 72)             │
│  - Updated Data Retention policy (line 89)                              │
│  - Added Threat Model reference (line 95)                               │
│  - Added Rollback Procedure section (line 112)                          │
│  - Added Monitoring Requirements (line 125)                             │
│                                                                         │
│  1 change skipped:                                                      │
│  - Error handling details (you can apply later)                         │
│                                                                         │
│  [Download Updated PRD]  [View Diff]  [Continue Editing]                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Edit Experience (Modify Before Accepting)

**Why Edit matters:** AI suggestions are good starting points, but PMs know their context best. Edit lets them refine without starting from scratch.

### When PM Clicks "Edit"

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EDIT SUGGESTION                                                    [X] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Original AI suggestion:                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ### Session Migration                                           │   │
│  │ - Existing sessions: Invalidate all on deploy                   │   │
│  │ - Users will need to re-login after migration                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Your version (edit below):                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ### Session Migration                                           │   │
│  │ - Existing sessions: Invalidate all on deploy                   │   │
│  │ - Users will need to re-login after migration                   │   │
│  │ - Marketing to send email 48 hours before cutover    <- added   │   │
│  │ - Support team briefed on expected ticket volume     <- added   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [Accept Edited Version]  [Revert to Original]  [Cancel]               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Edit Use Cases

| Scenario | What PM Does |
|----------|--------------|
| **Add business context** | AI suggests technical detail, PM adds stakeholder/process info |
| **Adjust scope** | AI suggests comprehensive fix, PM scales down for MVP |
| **Fix terminology** | AI uses generic terms, PM uses company-specific language |
| **Combine suggestions** | PM merges ideas from multiple AI suggestions |
| **Add owners** | AI suggests what, PM adds who's responsible |

### Example: Adding Business Context

**AI suggests:**
```
### Rate Limiting
- 100 requests/minute per user
- Burst allowance: 10 requests/second
```

**PM edits to:**
```
### Rate Limiting
- 100 requests/minute per user
- Burst allowance: 10 requests/second
- Exception: Enterprise tier gets 500 requests/minute (see pricing doc)
- Monitoring: Alert DevOps if >50% of users hit limits
- Rollout: Enable for 10% of users first, expand after 1 week
```

### Inline Edit (Alternative)

For quick tweaks, PM can edit directly in the diff view without opening a modal:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌─ PRD Change (## Technical Requirements, line 45) ────────┐          │
│  │   - User authentication via OAuth 2.0                    │          │
│  │   - Support for Google and GitHub providers              │          │
│  │   - JWT tokens for session management                    │          │
│  │ + ### Session Migration                          [GREEN] │ [edit]   │
│  │ + - Existing sessions: Invalidate all on deploy  [GREEN] │ [edit]   │
│  │ + - Users will need to re-login after migration  [GREEN] │ [edit]   │
│  └──────────────────────────────────────────────────────────┘          │
│                                                                         │
│  Click [edit] on any line to modify it directly                        │
│                                                                         │
│  [Accept]  [Reject]  [Edit All]  [Ask Expert]                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Customization (PM Preferences)

### Feedback Focus

PMs can configure which teams' feedback they care about most:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FEEDBACK PREFERENCES                                                   │
│                                                                         │
│  Show feedback from:                                                    │
│                                                                         │
│  ☑ Engineering       Always show                                        │
│  ☑ Security          Always show                                        │
│  ☑ Privacy           Always show                                        │
│  ☐ Legal             Hide (not relevant for this product)              │
│  ☑ Infra/DevOps      Always show                                        │
│  ☐ Compliance        Hide (handled by separate process)                │
│                                                                         │
│  Severity filter:                                                       │
│  ☑ Blockers          Always show                                        │
│  ☑ Likely questions  Always show                                        │
│  ☐ Possible questions Hide low-confidence predictions                  │
│                                                                         │
│  [Save Preferences]                                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mute Specific Patterns

If a prediction keeps appearing but isn't relevant:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [POSSIBLE] "GDPR compliance not mentioned"                             │
│                                                                         │
│  [Accept]  [Reject]  [Mute This Pattern]                               │
│                                                                         │
│  ──────────────────────────────────────────────────────────────────     │
│  Muting will hide similar suggestions in future analyses.               │
│  You can unmute anytime in Preferences.                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### PRD Templates

PMs can save successful PRD structures as templates:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  This PRD scored 94% after improvements.                                │
│                                                                         │
│  [Save as Template: "Auth Feature PRD"]                                │
│                                                                         │
│  Future PRDs can start from this structure.                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### What We DON'T Build

| Feature | Why Not |
|---------|---------|
| Team Queues | Creates ticket backlog mentality |
| Formal Assignment | PM doesn't need permission to ask |
| Review Workflows | Over-engineered for quick validation |
| Consensus Mechanisms | One expert opinion is usually enough |
| Thread Discussions | Tool is for PRD improvement, not chat |
| SLA Tracking | Creates pressure, defeats lightweight feel |

---

## Data Models

### Predicted Feedback (Core)

```python
@dataclass
class PredictedQuestion:
    """A question a team is likely to ask."""
    id: UUID
    question: str
    team: str  # "engineering", "security", "privacy", "infra"
    severity: str  # "blocker", "likely", "possible"
    
    # Code-grounded reasoning
    reasoning: str
    code_evidence: list[CodeEvidence]
    
    # Suggested PRD change (diff-style)
    suggested_change: PRDChange
    
    # Status
    status: str = "open"  # "open", "accepted", "rejected", "dismissed", "asked_expert"
    
    # Expert assist (if used)
    expert_ask: Optional[ExpertAsk] = None


@dataclass
class PRDChange:
    """A suggested change to the PRD, displayed as a diff."""
    id: UUID
    prediction_id: UUID  # Links to the prediction that generated this
    
    # Location in PRD
    section: str  # "## Technical Requirements", "## Security", etc.
    start_line: int
    end_line: int
    
    # Diff content
    change_type: str  # "addition", "modification", "restructure"
    current_text: str  # What's currently in the PRD (shown in red if modified)
    suggested_text: str  # What it should become (shown in green)
    
    # For rendering the diff
    diff_hunks: list[DiffHunk]
    
    # Metadata
    reasoning: str  # Why this change is needed
    applied_at: Optional[datetime] = None
    
    # Edit tracking (when PM modifies suggestion before accepting)
    original_suggested_text: Optional[str] = None  # AI's original, if PM edited
    edited_by_pm: bool = False
    edit_history: list[str] = field(default_factory=list)  # Track PM iterations


@dataclass
class DiffHunk:
    """A single hunk of a diff, for precise rendering."""
    operation: str  # "add", "remove", "context"
    content: str
    line_number: Optional[int] = None  # Line in original PRD
```

### Expert Ask (Lightweight Collaboration)

```python
@dataclass
class ExpertAsk:
    """A quick ask to a specific expert - NOT a ticket."""
    id: UUID
    prediction_id: UUID  # Which prediction this relates to
    
    # Who's asking
    pm_id: str
    pm_name: str
    
    # Who's being asked (specific person, not team)
    expert_id: str
    expert_name: str
    expert_domain: str  # "security", "devops", etc.
    
    # The question (usually pre-filled from prediction)
    question: str
    
    # Response (if received)
    response: Optional[ExpertResponse] = None
    
    # Timestamps
    asked_at: datetime
    responded_at: Optional[datetime] = None


@dataclass
class ExpertResponse:
    """Expert's lightweight response - one click + optional note."""
    verdict: str  # "correct", "wrong", "partially_right"
    note: Optional[str] = None  # Optional context
    
    # For pattern learning
    correct_answer: Optional[str] = None  # What should the prediction have said?
    should_learn: bool = True  # Should this train future predictions?
```

### Pattern Learning (Background)

```python
@dataclass
class LearnedPattern:
    """A pattern learned from expert feedback."""
    id: UUID
    
    # What we learned
    pattern_description: str
    applies_when: str  # Conditions for this pattern
    correction: str  # What to say instead
    
    # Source
    learned_from: list[UUID]  # Expert response IDs
    times_applied: int = 0
    
    # Validation
    accuracy_score: float = 0.0  # How often experts agree with this pattern
```

---

## API Design

### PRD Input APIs

```python
# Create new analysis from pasted text
POST /api/reviews
Body: {
    "content": "# My PRD\n\n## Overview...",
    "format": "markdown",  # "markdown", "plaintext"
    "codebase_id": "acme-backend",
    "title": "User Authentication PRD"  # Optional, auto-detected
}
Response: {
    "review_id": "...",
    "status": "analyzing",
    "estimated_time_seconds": 45
}

# Create analysis from file upload
POST /api/reviews/upload
Body: multipart/form-data {
    "file": <uploaded file>,
    "codebase_id": "acme-backend"
}

# Create analysis from Google Docs
POST /api/reviews/google-docs
Body: {
    "doc_url": "https://docs.google.com/document/d/...",
    "codebase_id": "acme-backend",
    "sync_back": true  # Whether to push changes back to Doc
}

# Create analysis from Notion
POST /api/reviews/notion
Body: {
    "page_url": "https://notion.so/...",
    "codebase_id": "acme-backend",
    "sync_back": true
}

# Get analysis status (poll until complete)
GET /api/reviews/{id}/status
Response: {
    "status": "complete",  # "analyzing", "complete", "failed"
    "progress": 100,
    "predictions_count": 7
}
```

### Core PM APIs

```python
# Get predicted feedback for a PRD
GET /api/reviews/{id}/feedback
Response: {
    "predictions": [...],
    "blockers": 4,
    "overall_readiness": 56,
    "suggested_changes": [...]  # Diff-style changes
}

# Get PRD quality score
GET /api/reviews/{id}/quality
Response: {
    "score": 72,
    "grade": "C",
    "gaps": [...],
    "predicted_pushback": 6
}

# Get effort estimation
GET /api/reviews/{id}/estimate
Response: {
    "total_days": { "min": 14, "likely": 18, "max": 24 },
    "by_requirement": [...],
    "codebase_support": 72,
    "tldr": "18 days, 3 sprints, 72% patterns exist"
}
```

### PRD Change APIs (Diff/Accept)

```python
# Get all suggested changes for a PRD (diff format)
GET /api/reviews/{id}/changes
Response: {
    "changes": [
        {
            "id": "...",
            "section": "## Technical Requirements",
            "change_type": "addition",
            "current_text": "- JWT tokens for session management",
            "suggested_text": "- JWT tokens for session management\n### Session Migration\n- Existing sessions: Invalidate all on deploy\n- Users will need to re-login after migration",
            "diff_hunks": [
                { "operation": "context", "content": "- JWT tokens for session management", "line_number": 47 },
                { "operation": "add", "content": "### Session Migration", "line_number": null },
                { "operation": "add", "content": "- Existing sessions: Invalidate all on deploy", "line_number": null },
                { "operation": "add", "content": "- Users will need to re-login after migration", "line_number": null }
            ],
            "reasoning": "session_manager.py:78 stores sessions with user_id...",
            "team": "engineering",
            "severity": "blocker"
        },
        ...
    ],
    "summary": {
        "total": 7,
        "by_team": { "engineering": 3, "security": 2, "privacy": 1, "infra": 1 },
        "by_severity": { "blocker": 4, "likely": 2, "possible": 1 }
    }
}

# Accept a single change (applies to PRD)
POST /api/reviews/{id}/changes/{change_id}/accept
Response: {
    "applied": true,
    "updated_prd": "...",  # Full PRD content after change
    "change_summary": "Added 'Session Migration' section at line 48"
}

# Reject a single change
POST /api/reviews/{id}/changes/{change_id}/reject
Body: { "reason": "optional reason" }  # For learning

# Bulk accept changes
POST /api/reviews/{id}/changes/bulk-accept
Body: {
    "change_ids": ["...", "...", "..."],  # Specific changes
    # OR use filters:
    "filter": {
        "teams": ["engineering", "security"],  # Optional
        "severities": ["blocker", "likely"]    # Optional
    }
}
Response: {
    "applied": 6,
    "skipped": 1,
    "updated_prd": "...",
    "changes_applied": [
        { "id": "...", "summary": "Added 'Session Migration' section at line 48" },
        { "id": "...", "summary": "Added 'Rate Limiting' to Security Requirements at line 72" },
        ...
    ]
}

# Undo last accept (within session)
POST /api/reviews/{id}/changes/undo
Response: {
    "reverted": true,
    "restored_prd": "..."
}

# Edit a suggestion before accepting
PUT /api/reviews/{id}/changes/{change_id}
Body: {
    "suggested_text": "Modified version of the suggestion..."
}
Response: {
    "updated_change": { ... }
}
```

### Expert Assist APIs

```python
# Send a quick ask to an expert
POST /api/expert-assist/ask
Body: {
    "prediction_id": "...",
    "expert_id": "...",
    "question": "..."  # Usually pre-filled
}
Response: { "ask_id": "..." }

# Expert responds (one-click + optional note)
POST /api/expert-assist/respond/{ask_id}
Body: {
    "verdict": "correct" | "wrong" | "partially_right",
    "note": "Optional context..."
}

# Search for experts (when PM needs to pick someone)
GET /api/experts/search?domain=security&q=rate+limiting
Response: [
    { "id": "...", "name": "Bob Wilson", "domain": "security", "expertise": ["rate limiting", "auth"] },
    ...
]
```

### PM Preferences APIs

```python
# Get PM preferences
GET /api/preferences
Response: {
    "feedback_teams": ["engineering", "security", "privacy", "infra"],
    "hidden_teams": ["legal", "compliance"],
    "severity_filter": ["blocker", "likely"],  # Hide "possible" by default
    "muted_patterns": [
        { "id": "...", "pattern": "GDPR compliance", "muted_at": "..." }
    ],
    "default_codebase": "acme-backend"
}

# Update preferences
PUT /api/preferences
Body: {
    "feedback_teams": ["engineering", "security"],
    "severity_filter": ["blocker", "likely", "possible"]
}

# Mute a pattern
POST /api/preferences/mute
Body: {
    "prediction_id": "...",  # Which prediction triggered this
    "pattern_description": "GDPR compliance suggestions"
}

# Unmute a pattern
DELETE /api/preferences/mute/{pattern_id}
```

### Codebase Management APIs (Admin)

```python
# List connected codebases
GET /api/codebases
Response: [
    {
        "id": "acme-backend",
        "name": "acme-corp/backend",
        "provider": "github",
        "last_indexed": "2026-01-10T10:30:00Z",
        "status": "ready"
    },
    ...
]

# Connect new codebase (admin only)
POST /api/codebases
Body: {
    "provider": "github",  # "github", "gitlab", "bitbucket"
    "repo_url": "https://github.com/acme-corp/backend",
    "branch": "main"
}

# Trigger re-index
POST /api/codebases/{id}/index

# Get index status
GET /api/codebases/{id}/status
Response: {
    "status": "indexing",  # "indexing", "ready", "failed"
    "progress": 67,
    "files_indexed": 1234,
    "last_indexed": "..."
}
```

---

## UI/UX Design

### Main View: Predicted Feedback with Diff-Style Changes

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User Authentication PRD                                    [Re-analyze] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │ 4        │ │ 7        │ │ 56%      │ │ 18 days  │                   │
│  │ Blockers │ │ Changes  │ │ Ready    │ │ Estimate │                   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                   │
│                                                                         │
│  [Accept All (7)] [Engineering (3)] [Security (2)] [Privacy (1)] [Infra (1)]
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ENGINEERING WILL ASK                                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ☐ [BLOCKER] "What happens to existing sessions?"         1 of 7 │   │
│  │                                                                  │   │
│  │ Because: session_manager.py:78-92 stores sessions with user_id  │   │
│  │ Your PRD doesn't specify migration behavior.                    │   │
│  │                                                                  │   │
│  │ ┌─ Code Evidence ──────────────────────────────────────────┐    │   │
│  │ │ session_store = {                                        │    │   │
│  │ │     "user_id": str,                                      │    │   │
│  │ │     "created_at": datetime,                              │    │   │
│  │ │ }                                                        │    │   │
│  │ └──────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │ ┌─ PRD Change (## Technical Requirements, line 45) ────────┐    │   │
│  │ │   - User authentication via OAuth 2.0                    │    │   │
│  │ │   - Support for Google and GitHub providers              │    │   │
│  │ │   - JWT tokens for session management                    │    │   │
│  │ │ + ### Session Migration                          [GREEN] │    │   │
│  │ │ + - Existing sessions: Invalidate all on deploy  [GREEN] │    │   │
│  │ │ + - Users will need to re-login after migration  [GREEN] │    │   │
│  │ └──────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │ [Accept]  [Reject]  [Edit]  [Ask Expert]                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ☐ [BLOCKER] "Rate limiting not specified"                2 of 7 │   │
│  │                                                                  │   │
│  │ Because: Searched for rate_limit*, throttle* - no matches.      │   │
│  │                                                                  │   │
│  │ ┌─ PRD Change (## Security Requirements, line 72) ─────────┐    │   │
│  │ │   - Input validation on all endpoints                    │    │   │
│  │ │   - HTTPS required for all connections                   │    │   │
│  │ │ + - Rate limiting: 100 requests/minute per user  [GREEN] │    │   │
│  │ │ + - Burst allowance: 10 requests/second          [GREEN] │    │   │
│  │ └──────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │ [Accept]  [Reject]  [Edit]  [Ask Expert]                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ☐ [LIKELY] "Data retention unclear"                      3 of 7 │   │
│  │                                                                  │   │
│  │ ┌─ PRD Change (## Privacy, line 89) ───────────────────────┐    │   │
│  │ │ - Data retention: Standard policy                  [RED] │    │   │
│  │ │ + Data retention:                                [GREEN] │    │   │
│  │ │ +   - User data: 90 days after account deletion  [GREEN] │    │   │
│  │ │ +   - Audit logs: 7 years (compliance)           [GREEN] │    │   │
│  │ │ +   - Session data: 30 days                      [GREEN] │    │   │
│  │ └──────────────────────────────────────────────────────────┘    │   │
│  │                                                                  │   │
│  │ [Accept]  [Reject]  [Edit]  [Ask Expert]                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Bulk Accept Panel

When PM wants to accept multiple changes at once:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SELECT CHANGES TO ACCEPT                                               │
│                                                                         │
│  Quick filters:                                                         │
│  [All (7)] [Blockers (4)] [Engineering (3)] [Security (2)]              │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ☑ Session migration section          Engineering  BLOCKER    line 45   │
│  ☑ Rate limiting requirements         Security     BLOCKER    line 72   │
│  ☑ Data retention clarification       Privacy      LIKELY     line 89   │
│  ☐ Error handling details             Engineering  POSSIBLE   line 103  │
│  ☑ Threat model reference             Security     BLOCKER    line 95   │
│  ☑ Rollback procedure                 Infra        BLOCKER    line 112  │
│  ☑ Monitoring requirements            Infra        LIKELY     line 125  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Selected: 6 changes                                                    │
│                                                                         │
│  [Accept Selected]  [Select All]  [Clear Selection]  [Cancel]           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### After Accepting Changes

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CHANGES APPLIED                                                 [Undo] │
│                                                                         │
│  6 changes applied to your PRD:                                         │
│                                                                         │
│  + Session Migration section added (line 48)                            │
│  + Rate Limiting added to Security Requirements (line 72)               │
│  ~ Data Retention policy updated (line 89)                              │
│  + Threat Model reference added (line 95)                               │
│  + Rollback Procedure section added (line 112)                          │
│  + Monitoring Requirements added (line 125)                             │
│                                                                         │
│  1 change pending:                                                      │
│  - Error handling details (you can apply later)                         │
│                                                                         │
│  PRD Score: 56% -> 84%                                                  │
│                                                                         │
│  [Download Updated PRD]  [View Full Diff]  [Continue Reviewing]         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Quick Ask Modal (Not a Ticket Form)

When PM clicks "Ask Expert":

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Quick Ask                                                          [X] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Re: "Rate limiting doesn't exist"                                      │
│                                                                         │
│  Ask someone who knows:                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [🔍] Search experts...                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Suggested: Bob Wilson (DevOps), Sarah Chen (Security)                  │
│                                                                         │
│  Your question:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ "Tool says rate limiting doesn't exist in the codebase.        │   │
│  │  Is this correct, or did we add it somewhere I'm not seeing?"  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  (Auto-filled from prediction - edit if needed)                         │
│                                                                         │
│  [Send to Bob Wilson]                                                   │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────      │
│  Note: This is a quick ping, not a formal review request.               │
│  Bob will get a notification and can respond in 1 click.                │
└─────────────────────────────────────────────────────────────────────────┘
```

### Expert View (Minimal)

Expert receives notification (email/Slack) with embedded response:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Quick Ask from Alice Chen                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PRD: User Authentication System                                        │
│                                                                         │
│  "Tool says rate limiting doesn't exist in the codebase.                │
│   Is this correct, or did we add it somewhere I'm not seeing?"          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ [✓ Correct - no rate limiting]                                  │   │
│  │                                                                  │   │
│  │ [✗ Wrong - it exists]                                           │   │
│  │                                                                  │   │
│  │ [△ Partially - depends...]                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Add a note (optional):                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [Send Response]                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### After Expert Responds

PM sees the response inline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [BLOCKER] "Rate limiting doesn't exist"                                 │
│                                                                         │
│ Because: Searched for rate_limit*, throttle* - no matches.              │
│                                                                         │
│ ┌─ Expert Response ────────────────────────────────────────────────┐   │
│ │ Bob Wilson (DevOps) says: ✗ Wrong                                │   │
│ │                                                                   │   │
│ │ "We added rate limiting to the API gateway last sprint.          │   │
│ │  It's in infra/kong/rate-limits.yaml, not in the app code."      │   │
│ │                                                                   │   │
│ │ 2 hours ago                                                       │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ [Got it - Dismiss this prediction]                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What Makes This Different

### vs. Pure AI (Current Phase 2 Plan)
- Adds escape hatch when PM needs human validation
- Expert feedback makes predictions better over time
- PM doesn't have to trust AI blindly

### vs. Full Collaboration (COLLABORATION_FEATURES.md)
- No team queues or assignment workflows
- Expert assist is optional, not required
- One expert opinion is enough (no consensus)
- Tool stays focused on PM productivity

### The Right Balance

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  COLLABORATION_FEATURES.md                                     │
│  ───────────────────────────────                               │
│  • Team queues                     ←── Too much process        │
│  • Formal assignment                                           │
│  • Lifecycle management                                        │
│  • Consensus voting                                            │
│  • Thread discussions                                          │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  THIS DOCUMENT (Sweet Spot)                         ✓          │
│  ───────────────────────────                                   │
│  • Predicted feedback (AI-first)                               │
│  • Quick ask to specific expert                                │
│  • One-click response                                          │
│  • Pattern learning (background)                               │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Pure AI Only                                                  │
│  ────────────────                                              │
│  • No human input ever            ←── AI can be wrong          │
│  • PM trusts blindly                                           │
│  • No feedback loop                                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Core PM Experience (Week 1-3)
1. PRD input (paste text, upload .md/.docx)
2. Codebase connection (admin setup for GitHub/GitLab)
3. Predicted cross-functional feedback
4. Code evidence display
5. **Diff-style PRD suggestions** (current state red, suggested green)
6. **Single accept/reject** for individual changes
7. **Edit before accepting** (modal + inline editing)
8. **Bulk accept** with filtering (by team, severity)
9. Undo functionality
10. PRD download (updated version)
11. PRD quality scoring

### Phase 1.5: Integrations (Week 3-4)
1. Google Docs integration (fetch + sync back)
2. Notion integration (fetch + sync back)
3. Re-analysis on PRD changes
4. PM preferences (mute patterns, filter teams)

### Phase 2: Expert Assist (Week 4)
1. "Ask Expert" button
2. Expert search/selection
3. Question pre-fill
4. Expert notification (email)
5. One-click response UI

### Phase 3: Pattern Learning (Week 5)
1. Store expert responses
2. Simple pattern extraction
3. Apply patterns to future predictions
4. Accuracy tracking

### Deferred (Maybe Never)
- Team queues
- Formal workflows
- SLA tracking
- Consensus mechanisms
- Thread discussions

---

## Success Metrics

### Primary (PM Productivity)
| Metric | Target |
|--------|--------|
| PRD revisions after using tool | > 50% update PRD |
| Time to stakeholder approval | -30% |
| Stakeholder meeting iterations | -40% |
| PM satisfaction | "I feel more prepared" |

### Secondary (Expert Assist Usage)
| Metric | Target |
|--------|--------|
| Quick asks per PRD | < 2 (most predictions are good) |
| Expert response time | < 4 hours |
| Expert satisfaction | "Quick and easy" |
| Pattern accuracy | > 70% (learned patterns are correct) |

---

## The One-Line Summary

**Cursor for PMs**: AI predicts what stakeholders will ask, shows exactly what to fix in your PRD (red/green diff), and lets you accept changes with one click. When you're not sure, ping an expert. Their response makes the tool smarter for everyone.

---

*Not a ticketing system. A tool that makes PMs better - one accept at a time.*


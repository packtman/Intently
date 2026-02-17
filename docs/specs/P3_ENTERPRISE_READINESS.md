# P3 — Enterprise Readiness

> **Priority:** P3
> **Estimated Effort:** 2–3 days
> **Goal:** Compliance audit trail for regulated industries — immutable logging of every review action.

---

## Features in This Spec

| # | Feature | Extends | Effort |
|---|---------|---------|--------|
| 13 | Compliance Audit Trail | collaboration routes, SQLite storage | 2–3 days |

---

## Feature 13: Compliance Audit Trail

### Overview

An immutable, append-only audit log of every review action — finding validations, comments, assignments, feedback submissions, lifecycle transitions, and policy overrides. Designed to satisfy SOC 2, HIPAA, and PCI-DSS evidence requirements. Exportable as compliance reports.

### Why This Matters

Regulated industries need to prove that product changes went through proper review and approval. Today, this evidence is scattered across the collaboration tables (validations, comments, feedback) without a unified, immutable timeline. An audit trail consolidates all actions into a single queryable log with export capability.

### What Exists Today

| Component | File | Used How |
|---|---|---|
| `SQLiteCollaborationStorage` | `storage/sqlite.py` | Already stores validations (with `validated_at`), comments (`created_at`), assignments (`assigned_at`), feedback (`created_at`), lifecycle transitions, consensus votes — all timestamped |
| `SQLiteReviewStorage` | `storage/sqlite.py` | Reviews with findings, dimensions, results — all timestamped |
| Compliance dimension | `security/compliance_analyzer.py` | Maps findings to SOC 2, HIPAA, PCI-DSS controls. `ComplianceFinding` has `control_id`, `framework`, `gap_description` |
| `ComplianceFramework` enum | `core/models.py` | SOC2, HIPAA, PCI_DSS, ISO_27001, GDPR, CCPA |
| `MarkdownReportGenerator` | `reports/markdown_report.py` | Already generates reports — extend with audit format |
| Collaboration routes | `api/collaboration_routes.py` | All action endpoints: `validate_finding`, `add_comment`, `assign_finding`, `submit_feedback`, `update_lifecycle`, `add_consensus_vote`, `create_cross_team_request` |

### New SQLite Table

```sql
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,          -- ISO 8601 timestamp
    review_id TEXT,                   -- NULL for system-level actions
    action TEXT NOT NULL,             -- Enum: see Action Types below
    actor TEXT NOT NULL,              -- User ID who performed the action
    actor_team TEXT,                  -- Team of the actor
    target_type TEXT,                 -- "finding", "review", "lifecycle", "pattern"
    target_id TEXT,                   -- ID of the target entity
    details_json TEXT NOT NULL,       -- Action-specific details (JSON)
    ip_address TEXT,                  -- For additional audit context
    created_at TEXT NOT NULL          -- Immutable write timestamp
);

-- Indexes for common queries
CREATE INDEX idx_audit_log_review ON audit_log(review_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_actor ON audit_log(actor);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_target ON audit_log(target_type, target_id);
```

### Action Types

| Action | Trigger Point | Details Captured |
|---|---|---|
| `review_created` | `POST /api/reviews` | review_id, PRD title, dimensions, config |
| `review_completed` | Review engine completes | findings_count, severity_breakdown, risk_rating |
| `finding_validated` | `POST /.../validate` | finding_id, status, validator_id, notes |
| `finding_assigned` | `POST /.../assign` | finding_id, team, assigned_by |
| `comment_added` | `POST /.../comments` | finding_id, author_id, content_preview |
| `feedback_submitted` | `POST /.../feedback` | finding_id, feedback_type, original_value, expert_value |
| `lifecycle_changed` | `POST /.../lifecycle` | old_state, new_state, updated_by, notes |
| `consensus_vote` | `POST /.../consensus` | finding_id, team, vote, voter_id |
| `cross_team_request` | `POST /.../requests` | requesting_team, target_team, question |
| `cross_team_response` | `POST /.../respond` | request_id, responded_by |
| `pattern_saved` | `POST /.../patterns` | pattern_type, pattern_signature |
| `gate_override` | Lifecycle with gate failure | gate_name, override_reason, overrider_id |
| `prd_change_accepted` | `POST /.../accept` | change_id, original_text, accepted_text |
| `prd_change_rejected` | `POST /.../reject` | change_id, reason |

### Implementation: Wire Into Existing Routes

The key insight is that every action already goes through an endpoint in `collaboration_routes.py` or `pm_routes.py`. We add audit logging **after** each successful action. No changes to existing logic — purely additive.

```python
# New file: src/context_graph/audit/logger.py

class AuditLogger:
    """Append-only audit logger. All writes are inserts — no updates or deletes."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def log(
        self,
        action: str,
        actor: str,
        review_id: str | None = None,
        actor_team: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> str:
        """Write an audit log entry. Returns the log entry ID."""
        entry_id = str(uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO audit_log
                   (id, timestamp, review_id, action, actor, actor_team,
                    target_type, target_id, details_json, ip_address, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, now, review_id, action, actor, actor_team,
                 target_type, target_id, json.dumps(details or {}),
                 ip_address, now),
            )
            await db.commit()

        return entry_id
```

Wire into each endpoint:

```python
# In collaboration_routes.py — after validate_finding:
await audit_logger.log(
    action="finding_validated",
    actor=request.validator_id,
    review_id=review_id,
    actor_team=request.validator_team,
    target_type="finding",
    target_id=finding_id,
    details={
        "status": request.status,
        "notes": request.notes,
    },
)

# In collaboration_routes.py — after update_lifecycle:
await audit_logger.log(
    action="lifecycle_changed",
    actor=request.updated_by,
    review_id=review_id,
    target_type="review",
    target_id=review_id,
    details={
        "old_state": current_state,
        "new_state": request.state,
        "notes": request.notes,
    },
)

# ... similar for all other endpoints
```

### New API Endpoints

```python
# New file: src/context_graph/api/audit_routes.py

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/reviews/{review_id}")
@requires_feature("audit_trail")
async def get_review_audit_log(review_id: str) -> list[dict]:
    """Get complete audit trail for a review. Chronological order."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT * FROM audit_log WHERE review_id = ? ORDER BY timestamp ASC",
            (review_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]

@router.get("/export")
@requires_feature("audit_trail")
async def export_audit_log(
    from_date: str | None = None,
    to_date: str | None = None,
    framework: str | None = None,  # "soc2", "hipaa", etc. — filter for compliance
    format: str = "json",          # "json" or "csv"
) -> Response:
    """Export audit log for compliance reviews.

    Supports filtering by date range and compliance framework.
    When framework is specified, includes only reviews that had
    findings in that framework's dimension.
    """
    # Query audit_log with date/framework filters
    # Return as JSON or CSV

@router.get("/reviews/{review_id}/compliance-evidence")
@requires_feature("audit_trail")
async def get_compliance_evidence(review_id: str, framework: str) -> dict:
    """Generate compliance evidence package for a specific review.

    Returns:
    - Review timeline (all audit events)
    - Compliance findings and their resolution status
    - Approver chain
    - Decision rationale
    """
    review = await storage.get_review(review_id)
    audit_entries = await get_review_audit_log(review_id)
    compliance_findings = review.compliance_findings

    return {
        "framework": framework,
        "review_id": review_id,
        "review_title": review.intent.title,
        "timeline": audit_entries,
        "compliance_findings": [
            {
                "control_id": f.control_id,
                "title": f.title,
                "severity": f.severity.value,
                "current_state": f.current_state,
                "required_state": f.required_state,
                "gap": f.gap_description,
                "resolution": ...,  # From validation data
            }
            for f in compliance_findings
            if f.framework.value == framework
        ],
        "approval_chain": [
            e for e in audit_entries
            if e["action"] in ("lifecycle_changed", "finding_validated")
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }
```

### Frontend Changes

- **New component:** `AuditTimeline.tsx` — chronological list of all actions for a review
  - Each entry shows: timestamp, actor, action type (with icon), details
  - Color-coded by action type: green (approvals), red (rejections), blue (comments), orange (lifecycle)
  - Filterable by action type and actor
- **Integration:** New "Audit Log" tab in `ReviewDetail.tsx`
- **Export button:** "Export Compliance Evidence" in ReviewDetail header
  - Opens modal to select framework (SOC 2, HIPAA, PCI-DSS) and date range
  - Downloads JSON or CSV

### Feature Flag

`FEATURE_AUDIT_TRAIL=true`

### Definition of Done

- [ ] `audit_log` SQLite table created on startup
- [ ] All collaboration endpoints write audit entries after successful actions
- [ ] `GET /api/audit/reviews/{id}` returns full timeline
- [ ] `GET /api/audit/export` supports date range and framework filtering
- [ ] `GET /api/audit/reviews/{id}/compliance-evidence` generates evidence package
- [ ] Audit timeline renders in ReviewDetail with filtering
- [ ] Export produces valid JSON/CSV for compliance teams
- [ ] Audit log is append-only — no UPDATE or DELETE operations on audit_log table

---

## Implementation Notes

### Immutability

The audit log is strictly append-only:
- Only `INSERT` statements are used — no `UPDATE` or `DELETE`
- The `AuditLogger` class has no update/delete methods
- The SQLite table has no `ON DELETE CASCADE` — even if a review is deleted, its audit trail persists
- For production, consider Write-Ahead Logging (WAL) mode for concurrent reads during writes

### Performance

- Audit writes are fire-and-forget (don't block the main request)
- Indexes on `review_id`, `action`, `actor`, and `timestamp` for fast queries
- Export queries can use date-range filters to avoid full table scans

### Future: PostgreSQL Migration

When migrating to PostgreSQL (per ROADMAP infrastructure notes):
- `audit_log` → partitioned table by month for performance
- `details_json` → `JSONB` column for queryable JSON
- Add `GENERATED ALWAYS AS IDENTITY` for sequential ordering
- Consider `pg_audit` extension for database-level auditing

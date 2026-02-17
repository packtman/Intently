"""
Compliance Audit Trail API Routes.

Provides endpoints for querying and exporting the immutable audit log.
The audit log is populated by wiring AuditLogger.log() calls into
existing collaboration and PM routes.

Feature flag: FEATURE_AUDIT_TRAIL=true
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage, get_storage_db_path
from context_graph.audit.logger import AuditLogger


router = APIRouter(prefix="/audit", tags=["audit"])


def _get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger using the same DB path as storage."""
    db_path = get_storage_db_path()
    return AuditLogger(db_path)


# ==================== Routes ====================


@router.get("/reviews/{review_id}")
@requires_feature("audit_trail")
async def get_review_audit_log(
    review_id: str,
    action: str | None = None,
) -> List[Dict[str, Any]]:
    """Get complete audit trail for a review, chronologically."""
    audit = _get_audit_logger()
    return await audit.get_review_log(review_id, action_filter=action)


@router.get("/entries")
@requires_feature("audit_trail")
async def query_audit_log(
    from_date: str | None = None,
    to_date: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query audit log with filters. Supports date range, action type, and actor."""
    audit = _get_audit_logger()
    return await audit.get_entries(
        from_date=from_date,
        to_date=to_date,
        action=action,
        actor=actor,
        limit=min(limit, 1000),
    )


@router.get("/stats")
@requires_feature("audit_trail")
async def get_audit_stats() -> Dict[str, Any]:
    """Get audit log statistics: total entries, breakdown by action and actor."""
    audit = _get_audit_logger()
    return await audit.get_stats()


@router.get("/export")
@requires_feature("audit_trail")
async def export_audit_log(
    from_date: str | None = None,
    to_date: str | None = None,
    format: str = "json",
) -> Any:
    """Export audit log for compliance reviews. Supports JSON and CSV formats.

    Example: GET /api/audit/export?from_date=2026-01-01&to_date=2026-03-31&format=csv
    """
    audit = _get_audit_logger()
    entries = await audit.get_entries(
        from_date=from_date,
        to_date=to_date,
        limit=10000,
    )

    if format == "csv":
        output = io.StringIO()
        if entries:
            writer = csv.DictWriter(output, fieldnames=entries[0].keys())
            writer.writeheader()
            for entry in entries:
                # Flatten details dict for CSV
                flat = {k: (str(v) if isinstance(v, dict) else v) for k, v in entry.items()}
                writer.writerow(flat)

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
        )

    return entries


@router.get("/reviews/{review_id}/compliance-evidence")
@requires_feature("audit_trail")
async def get_compliance_evidence(
    review_id: str,
    framework: str = "soc2",
) -> Dict[str, Any]:
    """Generate a compliance evidence package for a specific review.

    Returns the full audit timeline, compliance findings filtered by
    framework, and the approval chain — everything needed for an audit.
    """
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    audit = _get_audit_logger()
    timeline = await audit.get_review_log(review_id)

    # Filter compliance findings by framework
    compliance_findings = []
    for f in review.compliance_findings:
        fw = f.framework.value if hasattr(f.framework, "value") else str(f.framework)
        if fw == framework:
            compliance_findings.append({
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity.value,
                "control_id": f.control_id,
                "control_description": f.control_description,
                "current_state": f.current_state,
                "required_state": f.required_state,
                "gap_description": f.gap_description,
                "recommendation": f.recommendation,
                "remediation_effort": f.remediation_effort,
            })

    # Extract approval chain from timeline
    approval_chain = [
        e for e in timeline
        if e.get("action") in (
            "lifecycle_changed", "finding_validated",
            "review_request_responded", "consensus_vote",
        )
    ]

    from datetime import datetime

    return {
        "framework": framework,
        "review_id": review_id,
        "review_title": review.intent.title,
        "review_risk_rating": review.risk_rating,
        "total_findings": len(review.all_findings),
        "compliance_findings": compliance_findings,
        "timeline": timeline,
        "approval_chain": approval_chain,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

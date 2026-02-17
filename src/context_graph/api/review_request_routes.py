"""
Review Request API Routes — Formal PRD Review Workflows.

Allows PMs to submit PRDs for structured review with designated
reviewers, deadlines, and tracked approval status. The PM equivalent
of a GitHub Pull Request.

Orchestrates existing collaboration features:
- Review lifecycle (collaboration_routes.py)
- Team assignment (collaboration_routes.py)
- Finding validation (collaboration_routes.py)

Feature flag: FEATURE_REVIEW_REQUESTS=true
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage, get_collaboration_storage


router = APIRouter(tags=["review-requests"])

# ------------------------------------------------------------------
# In-memory store (mirrors pattern from pm_routes.py)
# Move to SQLite in Phase 2 alongside prd_history_store migration.
# ------------------------------------------------------------------

_review_requests: dict[str, dict[str, Any]] = {}  # request_id -> request data
_reviewer_statuses: dict[str, list[dict[str, Any]]] = {}  # request_id -> [reviewer dicts]


# ==================== Request / Response Models ====================


class ReviewerInput(BaseModel):
    """A reviewer to add to the review request."""

    team: str = Field(..., description="Team name (security, privacy, engineering, etc.)")
    user_id: str | None = Field(None, description="Specific user ID (optional)")
    required: bool = Field(True, description="Whether this reviewer's approval is required")


class CreateReviewRequestInput(BaseModel):
    """Request body for creating a new review request."""

    requested_by: str = Field(..., description="PM user ID who is requesting the review")
    title: str = Field("", description="Optional title override (defaults to PRD title)")
    description: str = Field("", description="Context for reviewers")
    reviewers: list[ReviewerInput] = Field(
        ..., min_length=1, description="At least one reviewer required"
    )
    deadline: str | None = Field(None, description="ISO 8601 deadline (optional)")


class ApproveReviewInput(BaseModel):
    """Request body for a reviewer responding to a review request."""

    reviewer_team: str = Field(..., description="Team of the responding reviewer")
    reviewer_id: str = Field(..., description="User ID of the reviewer")
    decision: str = Field(
        ..., description="Decision: approved, changes_requested, or blocked"
    )
    notes: str = Field("", description="Optional notes / reason")


class ReviewRequestResponse(BaseModel):
    """Response for a review request."""

    id: str
    review_id: str
    requested_by: str
    title: str
    description: str
    status: str
    deadline: str | None
    reviewers: list[dict[str, Any]]
    created_at: str
    updated_at: str


# ==================== Routes ====================


@router.post("/reviews/{review_id}/request-review", response_model=ReviewRequestResponse)
@requires_feature("review_requests")
async def create_review_request(
    review_id: str,
    body: CreateReviewRequestInput,
) -> ReviewRequestResponse:
    """Create a formal review request for a PRD.

    Orchestrates:
    1. Creates the review request record
    2. Auto-assigns findings to reviewer teams (via existing team assignment logic)
    3. Records the review request for tracking
    """
    # Verify review exists
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    request_id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    title = body.title or review.intent.title or f"Review {review_id}"

    request_data = {
        "id": request_id,
        "review_id": review_id,
        "requested_by": body.requested_by,
        "title": title,
        "description": body.description,
        "status": "open",
        "deadline": body.deadline,
        "created_at": now,
        "updated_at": now,
    }
    _review_requests[request_id] = request_data

    # Create reviewer entries
    reviewers = []
    for r in body.reviewers:
        reviewer_entry = {
            "id": str(uuid4()),
            "request_id": request_id,
            "team": r.team,
            "user_id": r.user_id,
            "required": r.required,
            "status": "pending",
            "responded_at": None,
            "notes": "",
        }
        reviewers.append(reviewer_entry)
    _reviewer_statuses[request_id] = reviewers

    # Auto-assign findings to reviewer teams using existing collaboration storage
    collab = get_collaboration_storage()
    findings = review.all_findings
    reviewer_teams = {r.team for r in body.reviewers}

    for finding in findings:
        dimension = finding.dimension.value if hasattr(finding, "dimension") else "security"
        # Map dimension to team — assign to matching team if present
        target_team = _dimension_to_team(dimension, reviewer_teams)
        if target_team:
            try:
                await collab.save_finding_assignment(
                    review_id=review_id,
                    finding_id=str(finding.id),
                    team=target_team,
                    assigned_by=body.requested_by,
                )
            except Exception:
                pass  # Assignment is best-effort

    return ReviewRequestResponse(
        id=request_id,
        review_id=review_id,
        requested_by=body.requested_by,
        title=title,
        description=body.description,
        status="open",
        deadline=body.deadline,
        reviewers=reviewers,
        created_at=now,
        updated_at=now,
    )


@router.get("/reviews/{review_id}/review-request")
@requires_feature("review_requests")
async def get_review_request(review_id: str) -> dict[str, Any]:
    """Get the review request status for a review.

    Returns reviewer statuses, approval progress, and overall status.
    """
    # Find request for this review
    request_data = None
    request_id = None
    for rid, rdata in _review_requests.items():
        if rdata["review_id"] == review_id:
            request_data = rdata
            request_id = rid
            break

    if not request_data:
        raise HTTPException(status_code=404, detail="No review request found for this review")

    reviewers = _reviewer_statuses.get(request_id, [])

    total = len(reviewers)
    approved = sum(1 for r in reviewers if r["status"] == "approved")
    blocked = sum(1 for r in reviewers if r["status"] == "blocked")
    changes_requested = sum(1 for r in reviewers if r["status"] == "changes_requested")
    pending = sum(1 for r in reviewers if r["status"] == "pending")
    required_total = sum(1 for r in reviewers if r["required"])
    required_approved = sum(1 for r in reviewers if r["required"] and r["status"] == "approved")

    return {
        **request_data,
        "reviewers": reviewers,
        "progress": {
            "total": total,
            "approved": approved,
            "blocked": blocked,
            "changes_requested": changes_requested,
            "pending": pending,
            "required_total": required_total,
            "required_approved": required_approved,
            "all_required_approved": required_approved == required_total and required_total > 0,
        },
    }


@router.post("/reviews/{review_id}/review-request/respond")
@requires_feature("review_requests")
async def respond_to_review(
    review_id: str,
    body: ApproveReviewInput,
) -> dict[str, Any]:
    """Reviewer responds to a review request (approve, request changes, or block).

    When all required reviewers approve, the review request status
    advances to 'approved'. If any reviewer blocks, status becomes 'blocked'.
    """
    # Find request
    request_data = None
    request_id = None
    for rid, rdata in _review_requests.items():
        if rdata["review_id"] == review_id:
            request_data = rdata
            request_id = rid
            break

    if not request_data:
        raise HTTPException(status_code=404, detail="No review request found")

    if body.decision not in ("approved", "changes_requested", "blocked"):
        raise HTTPException(status_code=400, detail="Decision must be: approved, changes_requested, or blocked")

    reviewers = _reviewer_statuses.get(request_id, [])
    now = datetime.utcnow().isoformat() + "Z"

    # Find matching reviewer entry
    matched = False
    for r in reviewers:
        if r["team"] == body.reviewer_team:
            r["status"] = body.decision
            r["responded_at"] = now
            r["notes"] = body.notes
            if body.reviewer_id:
                r["user_id"] = body.reviewer_id
            matched = True
            break

    if not matched:
        raise HTTPException(status_code=404, detail=f"No reviewer found for team '{body.reviewer_team}'")

    # Recompute overall status
    required_reviewers = [r for r in reviewers if r["required"]]
    if any(r["status"] == "blocked" for r in required_reviewers):
        request_data["status"] = "blocked"
    elif all(r["status"] == "approved" for r in required_reviewers) and required_reviewers:
        request_data["status"] = "approved"
    elif any(r["status"] == "changes_requested" for r in reviewers):
        request_data["status"] = "changes_requested"
    else:
        request_data["status"] = "open"

    request_data["updated_at"] = now

    return {
        "message": f"Review {body.decision} by {body.reviewer_team}",
        "reviewer_status": body.decision,
        "overall_status": request_data["status"],
        "review_id": review_id,
    }


@router.get("/review-requests/pending")
@requires_feature("review_requests")
async def list_pending_requests(team: str | None = None) -> list[dict[str, Any]]:
    """List all open review requests. Optionally filter by reviewer team."""

    results = []
    for request_id, rdata in _review_requests.items():
        if rdata["status"] not in ("open", "changes_requested"):
            continue

        reviewers = _reviewer_statuses.get(request_id, [])

        if team:
            # Only include if this team is a reviewer and hasn't responded
            matching = [r for r in reviewers if r["team"] == team and r["status"] == "pending"]
            if not matching:
                continue

        pending_count = sum(1 for r in reviewers if r["status"] == "pending")
        results.append({
            **rdata,
            "pending_reviewers": pending_count,
            "total_reviewers": len(reviewers),
        })

    # Sort by deadline (soonest first), then by created_at
    results.sort(key=lambda r: r.get("deadline") or "9999")
    return results


# ==================== Helpers ====================


def _dimension_to_team(dimension: str, available_teams: set[str]) -> str | None:
    """Map a review dimension to the best matching reviewer team."""
    mapping = {
        "security": "security",
        "privacy": "privacy",
        "compliance": "compliance",
        "engineering": "engineering",
        "architecture": "architecture",
    }
    target = mapping.get(dimension)
    if target and target in available_teams:
        return target

    # Fallback: if dimension team not in reviewers, try "engineering" as catch-all
    if "engineering" in available_teams:
        return "engineering"

    return None

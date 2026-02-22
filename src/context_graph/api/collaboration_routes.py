"""
API Routes for Collaboration Features.

These routes are feature-flag protected and provide team collaboration
capabilities for finding validation, comments, assignments, and feedback.

All routes are additive - they don't modify existing routes.py endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from context_graph.config.features import get_features, requires_feature
from context_graph.storage.base import CollaborationStorage
from context_graph.storage.config import get_collaboration_storage


# ==================== Router Setup ====================

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# ==================== Request/Response Models ====================


class ValidateFindingRequest(BaseModel):
    """Request to validate a finding."""
    status: str = Field(
        ..., 
        description="Validation status: validated, rejected, needs_discussion, accepted_risk, deferred"
    )
    notes: str = Field("", description="Justification or notes for the validation decision")
    validator_id: str = Field(..., description="ID of the person validating")
    validator_team: str = Field(..., description="Team of the validator")


class ValidateFindingResponse(BaseModel):
    """Response after validating a finding."""
    id: str
    finding_id: str
    review_id: str
    status: str
    validator_id: str
    validator_team: str
    notes: str
    validated_at: str
    message: str


class AddCommentRequest(BaseModel):
    """Request to add a comment to a finding."""
    content: str = Field(..., description="Comment content (supports markdown)")
    author_id: str = Field(..., description="ID of the comment author")
    author_name: str = Field(..., description="Display name of the author")
    author_team: str = Field(..., description="Team of the author")
    parent_comment_id: str | None = Field(None, description="Parent comment ID for threading")


class CommentResponse(BaseModel):
    """Response after adding a comment."""
    id: str
    finding_id: str
    review_id: str
    author_id: str
    author_name: str
    author_team: str
    content: str
    parent_comment_id: str | None
    created_at: str


class AssignFindingRequest(BaseModel):
    """Request to assign a finding to a team/user."""
    team: str = Field(..., description="Team to assign the finding to")
    user_id: str | None = Field(None, description="Specific user ID to assign to")
    assigned_by: str | None = Field(None, description="ID of the person making the assignment")


class AssignmentResponse(BaseModel):
    """Response after assigning a finding."""
    id: str
    finding_id: str
    review_id: str
    team: str
    user_id: str | None
    assigned_by: str | None
    assigned_at: str


class ExpertFeedbackRequest(BaseModel):
    """Request to submit expert feedback on a finding."""
    feedback_type: str = Field(
        ..., 
        description="Type of feedback: accuracy, severity, recommendation, context"
    )
    original_value: str = Field(..., description="The original AI-generated value")
    expert_value: str = Field(..., description="The expert's corrected value")
    expert_id: str = Field(..., description="ID of the expert providing feedback")
    expert_team: str = Field(..., description="Team of the expert")
    reasoning: str = Field(..., description="Explanation for the correction")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    id: str
    finding_id: str
    review_id: str
    feedback_type: str
    original_value: str
    expert_value: str
    expert_id: str
    expert_team: str
    reasoning: str
    created_at: str


class FeatureFlagsResponse(BaseModel):
    """Response containing current feature flags."""
    validation: bool
    team_assignment: bool
    comments: bool
    expert_feedback: bool
    review_lifecycle: bool
    cross_team_requests: bool
    consensus_mode: bool
    pattern_learning: bool
    # PM-focused features
    prd_changes: bool = False
    prd_quality_scoring: bool = False
    effort_estimation: bool = False
    expert_assist: bool = False
    pm_pattern_learning: bool = False
    prd_save_to_file: bool = False
    side_by_side_diff: bool = False
    # P0: Core PM Experience
    product_chat: bool = False
    review_requests: bool = False
    impact_graph: bool = False
    threat_canvas: bool = False


# ==================== Feature Flags Endpoint ====================


@router.get("/features", response_model=FeatureFlagsResponse)
async def get_collaboration_features() -> FeatureFlagsResponse:
    """
    Get the current state of collaboration feature flags.
    
    This endpoint is always available (not feature-gated) so clients
    can determine which features are enabled.
    """
    features = get_features()
    return FeatureFlagsResponse(**features.to_dict())


# ==================== Finding Validation Endpoints ====================


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/validate",
    response_model=ValidateFindingResponse,
)
@requires_feature("finding_validation")
async def validate_finding(
    review_id: str,
    finding_id: str,
    request: ValidateFindingRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> ValidateFindingResponse:
    """
    Validate a finding with a status and optional notes.
    
    Requires: FEATURE_FINDING_VALIDATION=true
    
    Validation statuses:
    - validated: Finding is accurate
    - rejected: False positive
    - needs_discussion: Requires cross-team input
    - accepted_risk: Valid but accepted with justification
    - deferred: Valid but not in scope for this release
    """
    # Validate status
    valid_statuses = {"validated", "rejected", "needs_discussion", "accepted_risk", "deferred"}
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # TODO: Verify review and finding exist (would need access to review storage)
    # For now, we trust the IDs
    
    result = await storage.save_finding_validation(
        review_id=review_id,
        finding_id=finding_id,
        status=request.status,
        validator_id=request.validator_id,
        validator_team=request.validator_team,
        notes=request.notes,
    )
    
    return ValidateFindingResponse(
        id=result["id"],
        finding_id=finding_id,
        review_id=review_id,
        status=result["status"],
        validator_id=result["validator_id"],
        validator_team=result["validator_team"],
        notes=result["notes"],
        validated_at=result["validated_at"],
        message=f"Finding {request.status} successfully",
    )


@router.get("/reviews/{review_id}/findings/{finding_id}/validation")
@requires_feature("finding_validation")
async def get_finding_validation(
    review_id: str,
    finding_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get the current validation status for a finding.
    
    Requires: FEATURE_FINDING_VALIDATION=true
    """
    result = await storage.get_finding_validation(review_id, finding_id)
    
    if result is None:
        return {
            "finding_id": finding_id,
            "review_id": review_id,
            "status": "pending",
            "validated": False,
        }
    
    return {
        **result,
        "validated": result["status"] != "pending",
    }


@router.get("/reviews/{review_id}/validations")
@requires_feature("finding_validation")
async def get_review_validations(
    review_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get all validations for a review.
    
    Requires: FEATURE_FINDING_VALIDATION=true
    
    Returns a dict keyed by finding_id for easy lookup.
    """
    validations = await storage.get_validations_for_review(review_id)
    
    # Calculate stats
    stats = {
        "total": len(validations),
        "pending": 0,
        "validated": 0,
        "rejected": 0,
        "needs_discussion": 0,
        "accepted_risk": 0,
        "deferred": 0,
    }
    
    for v in validations.values():
        status = v.get("status", "pending")
        if status in stats:
            stats[status] += 1
    
    return {
        "review_id": review_id,
        "validations": validations,
        "stats": stats,
    }


# ==================== Comments Endpoints ====================


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/comments",
    response_model=CommentResponse,
)
@requires_feature("comments")
async def add_comment(
    review_id: str,
    finding_id: str,
    request: AddCommentRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> CommentResponse:
    """
    Add a comment to a finding.
    
    Requires: FEATURE_COMMENTS=true
    
    Supports threaded replies via parent_comment_id.
    """
    result = await storage.add_comment(
        review_id=review_id,
        finding_id=finding_id,
        author_id=request.author_id,
        author_name=request.author_name,
        author_team=request.author_team,
        content=request.content,
        parent_comment_id=request.parent_comment_id,
    )
    
    return CommentResponse(
        id=result["id"],
        finding_id=finding_id,
        review_id=review_id,
        author_id=result["author_id"],
        author_name=result["author_name"],
        author_team=result["author_team"],
        content=result["content"],
        parent_comment_id=result.get("parent_comment_id"),
        created_at=result["created_at"],
    )


@router.get("/reviews/{review_id}/findings/{finding_id}/comments")
@requires_feature("comments")
async def get_comments(
    review_id: str,
    finding_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[dict[str, Any]]:
    """
    Get all comments for a finding.
    
    Requires: FEATURE_COMMENTS=true
    
    Returns comments sorted by created_at (oldest first).
    """
    comments = await storage.get_comments(review_id, finding_id)
    return sorted(comments, key=lambda c: c.get("created_at", ""))


@router.get("/reviews/{review_id}/comment-counts")
@requires_feature("comments")
async def get_comment_counts(
    review_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, int]:
    """
    Get comment counts for all findings in a review.
    
    Requires: FEATURE_COMMENTS=true
    
    Returns a dict keyed by finding_id.
    """
    return await storage.get_comment_counts(review_id)


@router.delete("/comments/{comment_id}")
@requires_feature("comments")
async def delete_comment(
    comment_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Soft-delete a comment.
    
    Requires: FEATURE_COMMENTS=true
    """
    deleted = await storage.delete_comment(comment_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    return {"deleted": True, "comment_id": comment_id}


# ==================== Team Assignment Endpoints ====================


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/assign",
    response_model=AssignmentResponse,
)
@requires_feature("team_assignment")
async def assign_finding(
    review_id: str,
    finding_id: str,
    request: AssignFindingRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> AssignmentResponse:
    """
    Assign a finding to a team or user.
    
    Requires: FEATURE_TEAM_ASSIGNMENT=true
    """
    result = await storage.assign_finding(
        review_id=review_id,
        finding_id=finding_id,
        team=request.team,
        user_id=request.user_id,
        assigned_by=request.assigned_by,
    )
    
    return AssignmentResponse(
        id=result["id"],
        finding_id=finding_id,
        review_id=review_id,
        team=result["team"],
        user_id=result.get("user_id"),
        assigned_by=result.get("assigned_by"),
        assigned_at=result["assigned_at"],
    )


@router.get("/reviews/{review_id}/assignments")
@requires_feature("team_assignment")
async def get_review_assignments(
    review_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get all assignments for a review.
    
    Requires: FEATURE_TEAM_ASSIGNMENT=true
    """
    assignments = await storage.get_assignments_for_review(review_id)
    
    # Group by team
    by_team: dict[str, list[str]] = {}
    for finding_id, assignment in assignments.items():
        team = assignment.get("team", "unassigned")
        if team not in by_team:
            by_team[team] = []
        by_team[team].append(finding_id)
    
    return {
        "review_id": review_id,
        "assignments": assignments,
        "by_team": by_team,
    }


@router.get("/teams/{team}/queue")
@requires_feature("team_assignment")
async def get_team_queue(
    team: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[dict[str, Any]]:
    """
    Get all findings assigned to a team across all reviews.
    
    Requires: FEATURE_TEAM_ASSIGNMENT=true
    """
    return await storage.get_team_queue(team)


# ==================== Expert Feedback Endpoints ====================


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/feedback",
    response_model=FeedbackResponse,
)
@requires_feature("expert_feedback")
async def submit_expert_feedback(
    review_id: str,
    finding_id: str,
    request: ExpertFeedbackRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> FeedbackResponse:
    """
    Submit expert feedback on a finding.
    
    Requires: FEATURE_EXPERT_FEEDBACK=true
    
    Feedback types:
    - accuracy: Was the finding accurate?
    - severity: Was the severity correct?
    - recommendation: Was the recommendation appropriate?
    - context: Additional context the AI missed
    """
    valid_types = {"accuracy", "severity", "recommendation", "context"}
    if request.feedback_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback type. Must be one of: {', '.join(valid_types)}"
        )
    
    result = await storage.save_expert_feedback(
        review_id=review_id,
        finding_id=finding_id,
        feedback_type=request.feedback_type,
        original_value=request.original_value,
        expert_value=request.expert_value,
        expert_id=request.expert_id,
        expert_team=request.expert_team,
        reasoning=request.reasoning,
    )
    
    return FeedbackResponse(
        id=result["id"],
        finding_id=finding_id,
        review_id=review_id,
        feedback_type=result["feedback_type"],
        original_value=result["original_value"],
        expert_value=result["expert_value"],
        expert_id=result["expert_id"],
        expert_team=result["expert_team"],
        reasoning=result["reasoning"],
        created_at=result["created_at"],
    )


@router.get("/reviews/{review_id}/findings/{finding_id}/feedback")
@requires_feature("expert_feedback")
async def get_finding_feedback(
    review_id: str,
    finding_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[dict[str, Any]]:
    """
    Get all expert feedback for a finding.
    
    Requires: FEATURE_EXPERT_FEEDBACK=true
    """
    return await storage.get_feedback_for_finding(review_id, finding_id)


@router.get("/feedback/stats")
@requires_feature("pattern_learning")
async def get_feedback_stats(
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get aggregated feedback statistics for pattern learning.
    
    Requires: FEATURE_PATTERN_LEARNING=true
    """
    return await storage.get_feedback_stats()


# ==================== Review Lifecycle Endpoints (Phase 5) ====================


class UpdateLifecycleRequest(BaseModel):
    """Request to update review lifecycle state."""
    state: str = Field(
        ..., 
        description="Lifecycle state: draft, in_review, team_review, awaiting_signoff, approved, blocked"
    )
    updated_by: str = Field(..., description="ID of the person updating the state")
    notes: str | None = Field(None, description="Optional notes about the state change")


class LifecycleResponse(BaseModel):
    """Response containing lifecycle state."""
    review_id: str
    state: str
    updated_by: str
    updated_at: str
    notes: str | None


@router.post(
    "/reviews/{review_id}/lifecycle",
    response_model=LifecycleResponse,
)
@requires_feature("review_lifecycle")
async def update_review_lifecycle(
    review_id: str,
    request: UpdateLifecycleRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> LifecycleResponse:
    """
    Update the lifecycle state of a review.
    
    Requires: FEATURE_REVIEW_LIFECYCLE=true
    
    Lifecycle states:
    - draft: Initial state
    - in_review: Under analysis
    - team_review: Assigned to teams for review
    - awaiting_signoff: Pending final approval
    - approved: All reviews completed
    - blocked: Cannot proceed due to issues
    """
    valid_states = {"draft", "in_review", "team_review", "awaiting_signoff", "approved", "blocked"}
    if request.state not in valid_states:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state. Must be one of: {', '.join(valid_states)}"
        )
    
    result = await storage.update_review_lifecycle(
        review_id=review_id,
        state=request.state,
        updated_by=request.updated_by,
        notes=request.notes,
    )
    
    return LifecycleResponse(
        review_id=review_id,
        state=result["state"],
        updated_by=result["updated_by"],
        updated_at=result["updated_at"],
        notes=result.get("notes"),
    )


@router.get("/reviews/{review_id}/lifecycle")
@requires_feature("review_lifecycle")
async def get_review_lifecycle(
    review_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get the current lifecycle state of a review.
    
    Requires: FEATURE_REVIEW_LIFECYCLE=true
    """
    result = await storage.get_review_lifecycle(review_id)
    
    if result is None:
        return {
            "review_id": review_id,
            "state": "draft",
            "has_lifecycle": False,
        }
    
    return {
        **result,
        "has_lifecycle": True,
    }


@router.get("/reviews/{review_id}/lifecycle/history")
@requires_feature("review_lifecycle")
async def get_lifecycle_history(
    review_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[dict[str, Any]]:
    """
    Get lifecycle state history for a review.
    
    Requires: FEATURE_REVIEW_LIFECYCLE=true
    """
    return await storage.get_lifecycle_history(review_id)


# ==================== Cross-Team Requests Endpoints (Phase 5) ====================


class CreateReviewRequestRequest(BaseModel):
    """Request to create a cross-team review request."""
    finding_id: str = Field(..., description="Finding to request review for")
    requesting_team: str = Field(..., description="Team making the request")
    target_team: str = Field(..., description="Team being requested to review")
    question: str = Field(..., description="Question or concern to address")
    requested_by: str = Field(..., description="User making the request")
    deadline: str | None = Field(None, description="Optional deadline for response")


class ReviewRequestResponse(BaseModel):
    """Response for a cross-team review request."""
    id: str
    review_id: str
    finding_id: str
    requesting_team: str
    target_team: str
    question: str
    requested_by: str
    deadline: str | None
    status: str
    created_at: str
    response: str | None
    responded_by: str | None
    responded_at: str | None


@router.post(
    "/reviews/{review_id}/requests",
    response_model=ReviewRequestResponse,
)
@requires_feature("cross_team_requests")
async def create_review_request(
    review_id: str,
    request: CreateReviewRequestRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> ReviewRequestResponse:
    """
    Create a cross-team review request.
    
    Requires: FEATURE_CROSS_TEAM_REQUESTS=true
    
    Allows one team to formally request input from another team on a specific finding.
    """
    result = await storage.create_review_request(
        review_id=review_id,
        finding_id=request.finding_id,
        requesting_team=request.requesting_team,
        target_team=request.target_team,
        question=request.question,
        requested_by=request.requested_by,
        deadline=request.deadline,
    )
    
    return ReviewRequestResponse(**result)


@router.get("/reviews/{review_id}/requests")
@requires_feature("cross_team_requests")
async def get_review_requests_for_review(
    review_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[ReviewRequestResponse]:
    """
    Get all cross-team requests for a review.
    
    Requires: FEATURE_CROSS_TEAM_REQUESTS=true
    """
    results = await storage.get_review_requests(review_id=review_id)
    return [ReviewRequestResponse(**r) for r in results]


@router.get("/teams/{team}/requests")
@requires_feature("cross_team_requests")
async def get_team_requests(
    team: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[ReviewRequestResponse]:
    """
    Get all cross-team requests targeting a specific team.
    
    Requires: FEATURE_CROSS_TEAM_REQUESTS=true
    """
    results = await storage.get_review_requests(target_team=team)
    return [ReviewRequestResponse(**r) for r in results]


class RespondToRequestRequest(BaseModel):
    """Request to respond to a cross-team review request."""
    response: str = Field(..., description="Response to the question")
    responded_by: str = Field(..., description="User providing the response")


@router.post("/requests/{request_id}/respond")
@requires_feature("cross_team_requests")
async def respond_to_request(
    request_id: str,
    request: RespondToRequestRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> ReviewRequestResponse:
    """
    Respond to a cross-team review request.
    
    Requires: FEATURE_CROSS_TEAM_REQUESTS=true
    """
    try:
        result = await storage.respond_to_request(
            request_id=request_id,
            response=request.response,
            responded_by=request.responded_by,
        )
        return ReviewRequestResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Consensus Mode Endpoints (Phase 5) ====================


class AddConsensusVoteRequest(BaseModel):
    """Request to add a consensus vote."""
    team: str = Field(..., description="Team casting the vote")
    vote: str = Field(..., description="Vote: approve, reject, or abstain")
    voter_id: str = Field(..., description="User casting the vote")
    notes: str | None = Field(None, description="Optional notes with the vote")


class ConsensusVoteResponse(BaseModel):
    """Response for a consensus vote."""
    id: str
    review_id: str
    finding_id: str
    team: str
    vote: str
    voter_id: str
    notes: str | None
    voted_at: str


@router.post(
    "/reviews/{review_id}/findings/{finding_id}/consensus",
    response_model=ConsensusVoteResponse,
)
@requires_feature("consensus_mode")
async def add_consensus_vote(
    review_id: str,
    finding_id: str,
    request: AddConsensusVoteRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> ConsensusVoteResponse:
    """
    Add a consensus vote for a finding.
    
    Requires: FEATURE_CONSENSUS_MODE=true
    
    Used when multiple teams need to agree on critical findings.
    """
    valid_votes = {"approve", "reject", "abstain"}
    if request.vote not in valid_votes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid vote. Must be one of: {', '.join(valid_votes)}"
        )
    
    result = await storage.add_consensus_vote(
        review_id=review_id,
        finding_id=finding_id,
        team=request.team,
        vote=request.vote,
        voter_id=request.voter_id,
        notes=request.notes,
    )
    
    return ConsensusVoteResponse(**result)


@router.get("/reviews/{review_id}/findings/{finding_id}/consensus")
@requires_feature("consensus_mode")
async def get_consensus_status(
    review_id: str,
    finding_id: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get consensus voting status for a finding.
    
    Requires: FEATURE_CONSENSUS_MODE=true
    """
    return await storage.get_consensus_status(review_id, finding_id)


# ==================== Pattern Learning Endpoints (Phase 5) ====================


class SavePatternRequest(BaseModel):
    """Request to save a learned pattern."""
    pattern_type: str = Field(..., description="Type of pattern (e.g., 'false_positive')")
    pattern_signature: str = Field(..., description="Description of what the pattern matches")
    decision: str = Field(..., description="Standard decision for this pattern")
    conditions: list[str] = Field(..., description="Conditions that must be true")
    reasoning: str = Field(..., description="Explanation of the decision")
    source_feedback_ids: list[str] = Field(..., description="Feedback IDs this was derived from")


class PatternResponse(BaseModel):
    """Response for a saved pattern."""
    id: str
    pattern_type: str
    pattern_signature: str
    decision: str
    conditions: list[str]
    reasoning: str
    source_feedback_ids: list[str]
    times_applied: int
    created_at: str


@router.post("/patterns", response_model=PatternResponse)
@requires_feature("pattern_learning")
async def save_pattern(
    request: SavePatternRequest,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> PatternResponse:
    """
    Save a learned pattern from expert feedback.
    
    Requires: FEATURE_PATTERN_LEARNING=true
    
    Patterns are extracted from aggregated expert feedback and can be
    used to suggest decisions for similar findings.
    """
    result = await storage.save_learned_pattern(
        pattern_type=request.pattern_type,
        pattern_signature=request.pattern_signature,
        decision=request.decision,
        conditions=request.conditions,
        reasoning=request.reasoning,
        source_feedback_ids=request.source_feedback_ids,
    )
    
    return PatternResponse(**result)


@router.get("/patterns/similar")
@requires_feature("pattern_learning")
async def get_similar_patterns(
    pattern_type: str,
    pattern_signature: str,
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> list[dict[str, Any]]:
    """
    Find similar patterns for a given finding.
    
    Requires: FEATURE_PATTERN_LEARNING=true
    
    Returns patterns that might apply to the current finding,
    along with their historical decisions.
    """
    return await storage.get_similar_patterns(pattern_type, pattern_signature)


@router.get("/patterns/insights")
@requires_feature("pattern_learning")
async def get_pattern_insights(
    storage: CollaborationStorage = Depends(get_collaboration_storage),
) -> dict[str, Any]:
    """
    Get aggregated pattern learning insights.
    
    Requires: FEATURE_PATTERN_LEARNING=true
    
    Provides statistics on learned patterns and their application.
    """
    return await storage.get_pattern_insights()


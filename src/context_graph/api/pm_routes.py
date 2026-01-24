"""
PM-Focused API Routes (Unified PM Tool).

These routes provide PM-focused features:
- PRD change management (diff, accept, reject, bulk accept)
- PRD quality scoring
- Effort estimation
- Expert assist (quick ask)

All routes are feature-flagged and disabled by default.
Requires: FEATURE_PRD_CHANGES, FEATURE_PRD_QUALITY_SCORING, etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import get_features, requires_feature
from context_graph.storage.config import get_review_storage


router = APIRouter(tags=["pm-tool"])

# In-memory store for PRD changes (use DB in production)
prd_changes_store: dict[str, dict[str, Any]] = {}  # review_id -> {change_id -> change}
applied_changes_store: dict[str, list[str]] = {}  # review_id -> list of applied change_ids
expert_asks_store: dict[str, dict[str, Any]] = {}  # ask_id -> ExpertAsk
prd_history_store: dict[str, list[str]] = {}  # review_id -> list of PRD versions (for undo)
pm_preferences_store: dict[str, dict[str, Any]] = {}  # user_id -> preferences
prd_file_info_store: dict[str, dict[str, Any]] = {}  # review_id -> PRD file info


# ==================== Request/Response Models ====================

class CodeEvidenceResponse(BaseModel):
    """Code evidence that grounds a prediction."""
    file_path: str
    line_number: int | None = None
    code_snippet: str = ""
    context: str = ""


class PRDChangeResponse(BaseModel):
    """PRD change response."""
    id: str
    question: str  # The predicted question, e.g., "What happens to existing sessions?"
    section: str
    change_type: str
    current_text: str
    suggested_text: str
    diff_hunks: list[dict[str, Any]]
    reasoning: str
    team: str
    severity: str
    status: str
    code_evidence: list[CodeEvidenceResponse] = []  # Code snippets that ground this prediction
    prd_file: str = "PRD"  # The PRD file name for display


class PRDChangesResponse(BaseModel):
    """All PRD changes for a review."""
    changes: list[PRDChangeResponse]
    summary: dict[str, Any]


class AcceptChangeRequest(BaseModel):
    """Request to accept a change."""
    edited_text: str | None = None  # Optional: PM can edit before accepting


class BulkAcceptRequest(BaseModel):
    """Request to bulk accept changes."""
    change_ids: list[str] | None = None
    filter: dict[str, Any] | None = None  # {teams: [...], severities: [...]}


class ExpertAskRequest(BaseModel):
    """Request to ask an expert."""
    prediction_id: str
    expert_id: str
    expert_name: str
    question: str


class ExpertResponseRequest(BaseModel):
    """Expert response to a quick ask."""
    verdict: str  # "correct", "wrong", "partially_right"
    note: str | None = None


class WordChangeResponse(BaseModel):
    """Word-level change within a line."""
    start: int
    end: int
    change_type: str  # "added", "removed"


class DiffLineResponse(BaseModel):
    """A single line in the side-by-side diff."""
    line_number: int | None
    content: str
    status: str  # "unchanged", "deleted", "added", "modified", "empty"
    word_changes: list[WordChangeResponse] = []


class DiffStatsResponse(BaseModel):
    """Statistics about a diff."""
    lines_added: int
    lines_removed: int
    lines_modified: int


class SideBySideDiffResponse(BaseModel):
    """Side-by-side diff response for UI rendering."""
    change_id: str
    file_name: str
    section: str
    original_lines: list[DiffLineResponse]
    suggested_lines: list[DiffLineResponse]
    stats: DiffStatsResponse


class SetPRDFilePathRequest(BaseModel):
    """Request to set the PRD file path for a review."""
    file_path: str
    file_name: str | None = None


class SavePRDToFileResponse(BaseModel):
    """Response after saving PRD to file."""
    saved: bool
    file_path: str
    backup_path: str | None = None
    message: str


# ==================== Routes ====================

@router.get("/reviews/{review_id}/changes", response_model=PRDChangesResponse)
async def get_prd_changes(review_id: str) -> PRDChangesResponse:
    """
    Get all suggested PRD changes for a review (diff format).
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Get predicted questions with changes
    predicted_questions = result.predicted_questions if hasattr(result, 'predicted_questions') else []
    
    # Convert to API response format
    changes = []
    by_team: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    
    for question in predicted_questions:
        if question.suggested_change:
            change = question.suggested_change
            
            # Convert code evidence
            code_evidence = []
            if hasattr(question, 'code_evidence') and question.code_evidence:
                for ev in question.code_evidence:
                    code_evidence.append(CodeEvidenceResponse(
                        file_path=ev.file_path,
                        line_number=ev.line_number,
                        code_snippet=ev.code_snippet,
                        context=ev.context,
                    ))
            
            changes.append(PRDChangeResponse(
                id=str(change.id),
                question=question.question,  # The predicted question
                section=change.section,
                change_type=change.change_type,
                current_text=change.current_text,
                suggested_text=change.suggested_text,
                diff_hunks=[
                    {
                        "operation": h.operation,
                        "content": h.content,
                        "line_number": h.line_number,
                    }
                    for h in change.diff_hunks
                ],
                reasoning=question.reasoning,  # Use question's full reasoning
                team=question.team,
                severity=question.severity,
                status=change.status,
                code_evidence=code_evidence,
                prd_file=result.intent.source_document if hasattr(result, 'intent') and hasattr(result.intent, 'source_document') and result.intent.source_document else "PRD",
            ))
            
            # Update counts
            by_team[question.team] = by_team.get(question.team, 0) + 1
            by_severity[question.severity] = by_severity.get(question.severity, 0) + 1
    
    return PRDChangesResponse(
        changes=changes,
        summary={
            "total": len(changes),
            "by_team": by_team,
            "by_severity": by_severity,
        }
    )


@router.post("/reviews/{review_id}/changes/{change_id}/accept")
async def accept_prd_change(
    review_id: str,
    change_id: str,
    request: AcceptChangeRequest | None = None,
) -> dict[str, Any]:
    """
    Accept a single PRD change (applies to PRD).
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    predicted_questions = result.predicted_questions if hasattr(result, 'predicted_questions') else []
    
    # Find the change and its parent question
    change = None
    parent_question = None
    for question in predicted_questions:
        if question.suggested_change and str(question.suggested_change.id) == change_id:
            change = question.suggested_change
            parent_question = question
            break
    
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    
    # Apply change to PRD
    prd_content = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
    updated_prd = _apply_change_to_prd(prd_content, change, request.edited_text if request else None)
    
    # Mark as applied (both the change and the parent question)
    change.status = "accepted"
    if parent_question:
        parent_question.status = "accepted"
    from datetime import datetime
    change.applied_at = datetime.now()
    
    # Store applied change
    if review_id not in applied_changes_store:
        applied_changes_store[review_id] = []
    applied_changes_store[review_id].append(change_id)
    
    # Store PRD history for undo
    if review_id not in prd_history_store:
        original_prd = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
        prd_history_store[review_id] = [original_prd]
    prd_history_store[review_id].append(updated_prd)
    
    return {
        "applied": True,
        "updated_prd": updated_prd,
        "change_summary": f"Applied change to {change.section}",
    }


@router.post("/reviews/{review_id}/changes/{change_id}/reject")
async def reject_prd_change(
    review_id: str,
    change_id: str,
) -> dict[str, Any]:
    """
    Reject a single PRD change.
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    predicted_questions = result.predicted_questions if hasattr(result, 'predicted_questions') else []
    
    # Find and reject the change (and update question status)
    for question in predicted_questions:
        if question.suggested_change and str(question.suggested_change.id) == change_id:
            question.suggested_change.status = "rejected"
            question.status = "rejected"
            return {"rejected": True}
    
    raise HTTPException(status_code=404, detail="Change not found")


@router.post("/reviews/{review_id}/changes/bulk-accept")
async def bulk_accept_changes(
    review_id: str,
    request: BulkAcceptRequest,
) -> dict[str, Any]:
    """
    Bulk accept multiple PRD changes.
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    predicted_questions = result.predicted_questions if hasattr(result, 'predicted_questions') else []
    
    # Filter changes based on request - track both question and change
    questions_to_accept: list[tuple] = []  # List of (question, change) tuples
    
    if request.change_ids:
        # Accept specific changes
        for question in predicted_questions:
            if question.suggested_change and str(question.suggested_change.id) in request.change_ids:
                questions_to_accept.append((question, question.suggested_change))
    elif request.filter:
        # Filter by team/severity
        teams = request.filter.get("teams", [])
        severities = request.filter.get("severities", [])
        
        for question in predicted_questions:
            if question.suggested_change:
                if teams and question.team not in teams:
                    continue
                if severities and question.severity not in severities:
                    continue
                questions_to_accept.append((question, question.suggested_change))
    else:
        # Accept all
        for question in predicted_questions:
            if question.suggested_change:
                questions_to_accept.append((question, question.suggested_change))
    
    # Apply all changes
    prd_content = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
    
    # Store original for undo
    if review_id not in prd_history_store:
        prd_history_store[review_id] = [prd_content]
    
    applied_count = 0
    applied_summaries = []
    
    for question, change in questions_to_accept:
        updated_prd = _apply_change_to_prd(prd_content, change, None)
        prd_content = updated_prd
        # Mark both the change and the question as accepted
        change.status = "accepted"
        question.status = "accepted"
        from datetime import datetime
        change.applied_at = datetime.now()
        applied_count += 1
        applied_summaries.append({
            "id": str(change.id),
            "summary": f"Applied change to {change.section}",
        })
        
        # Track applied change
        if review_id not in applied_changes_store:
            applied_changes_store[review_id] = []
        applied_changes_store[review_id].append(str(change.id))
    
    # Store updated PRD in history
    prd_history_store[review_id].append(prd_content)
    
    return {
        "applied": applied_count,
        "skipped": len(questions_to_accept) - applied_count,
        "updated_prd": prd_content,
        "changes_applied": applied_summaries,
    }


@router.get("/reviews/{review_id}/quality")
async def get_prd_quality(review_id: str) -> dict[str, Any]:
    """
    Get PRD quality score.
    
    Requires: FEATURE_PRD_QUALITY_SCORING=true
    """
    features = get_features()
    if not features.enable_prd_quality_scoring:
        raise HTTPException(
            status_code=403,
            detail="PRD quality scoring feature is not enabled. Set FEATURE_PRD_QUALITY_SCORING=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if not hasattr(result, 'prd_quality_score') or result.prd_quality_score is None:
        raise HTTPException(status_code=404, detail="Quality score not available for this review")
    
    score = result.prd_quality_score
    
    return {
        "score": score.score,
        "grade": score.grade,
        "gaps": score.gaps,
        "predicted_pushback": score.predicted_pushback,
        "blockers": score.blockers,
        "likely_questions": score.likely_questions,
        "possible_questions": score.possible_questions,
    }


@router.get("/reviews/{review_id}/estimate")
async def get_effort_estimate(review_id: str) -> dict[str, Any]:
    """
    Get effort estimation.
    
    Requires: FEATURE_EFFORT_ESTIMATION=true
    """
    features = get_features()
    if not features.enable_effort_estimation:
        raise HTTPException(
            status_code=403,
            detail="Effort estimation feature is not enabled. Set FEATURE_EFFORT_ESTIMATION=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if not hasattr(result, 'effort_estimation') or result.effort_estimation is None:
        raise HTTPException(status_code=404, detail="Effort estimation not available for this review")
    
    estimation = result.effort_estimation
    
    return {
        "total_days": estimation.total_days,
        "by_requirement": estimation.by_requirement,
        "codebase_support": estimation.codebase_support,
        "tldr": estimation.tldr,
    }


@router.post("/expert-assist/ask")
async def ask_expert(request: ExpertAskRequest) -> dict[str, Any]:
    """
    Send a quick ask to an expert.
    
    Requires: FEATURE_EXPERT_ASSIST=true
    """
    features = get_features()
    if not features.enable_expert_assist:
        raise HTTPException(
            status_code=403,
            detail="Expert assist feature is not enabled. Set FEATURE_EXPERT_ASSIST=true to enable."
        )
    
    ask_id = str(uuid4())
    
    from context_graph.core.models import ExpertAsk
    from datetime import datetime
    
    expert_ask = ExpertAsk(
        id=UUID(ask_id),
        prediction_id=UUID(request.prediction_id),
        expert_id=request.expert_id,
        expert_name=request.expert_name,
        question=request.question,
        asked_at=datetime.now(),
    )
    
    expert_asks_store[ask_id] = {
        "id": ask_id,
        "prediction_id": request.prediction_id,
        "expert_id": request.expert_id,
        "expert_name": request.expert_name,
        "question": request.question,
        "asked_at": expert_ask.asked_at.isoformat(),
        "response": None,
    }
    
    return {"ask_id": ask_id}


@router.post("/expert-assist/respond/{ask_id}")
async def respond_to_expert_ask(
    ask_id: str,
    request: ExpertResponseRequest,
) -> dict[str, Any]:
    """
    Expert responds to a quick ask (one-click + optional note).
    
    Requires: FEATURE_EXPERT_ASSIST=true
    """
    features = get_features()
    if not features.enable_expert_assist:
        raise HTTPException(
            status_code=403,
            detail="Expert assist feature is not enabled. Set FEATURE_EXPERT_ASSIST=true to enable."
        )
    
    if ask_id not in expert_asks_store:
        raise HTTPException(status_code=404, detail="Expert ask not found")
    
    from context_graph.core.models import ExpertResponse
    from datetime import datetime
    
    response = ExpertResponse(
        verdict=request.verdict,
        note=request.note,
        responded_at=datetime.now(),
    )
    
    expert_asks_store[ask_id]["response"] = {
        "verdict": request.verdict,
        "note": request.note,
        "responded_at": response.responded_at.isoformat(),
    }
    
    return {"responded": True}


@router.post("/reviews/{review_id}/changes/undo")
async def undo_last_change(review_id: str) -> dict[str, Any]:
    """
    Undo last accepted change (within session).
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review_id not in prd_history_store or len(prd_history_store[review_id]) < 2:
        raise HTTPException(status_code=400, detail="No changes to undo")
    
    # Restore previous version
    prd_history_store[review_id].pop()  # Remove current
    restored_prd = prd_history_store[review_id][-1]  # Get previous
    
    # Remove last applied change
    if review_id in applied_changes_store and applied_changes_store[review_id]:
        last_change_id = applied_changes_store[review_id].pop()
        
        # Mark change and question as open again (result already loaded above)
        predicted_questions = result.predicted_questions if hasattr(result, 'predicted_questions') else []
        for question in predicted_questions:
            if question.suggested_change and str(question.suggested_change.id) == last_change_id:
                question.suggested_change.status = "open"
                question.suggested_change.applied_at = None
                question.status = "open"
                break
    
    return {
        "reverted": True,
        "restored_prd": restored_prd,
    }


@router.get("/reviews/{review_id}/prd/download")
async def download_updated_prd(review_id: str) -> dict[str, Any]:
    """
    Download the updated PRD (with all accepted changes applied).
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Get current PRD (either from history or original)
    if review_id in prd_history_store and prd_history_store[review_id]:
        current_prd = prd_history_store[review_id][-1]
    else:
        current_prd = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
    
    # Get title for filename
    title = result.intent.title if hasattr(result, 'intent') and result.intent.title else "PRD"
    filename = f"{title.replace(' ', '_')}_updated.md"
    
    return {
        "content": current_prd,
        "filename": filename,
        "content_type": "text/markdown",
    }


# ==================== Side-by-Side Diff & File Save Endpoints ====================

@router.get("/reviews/{review_id}/changes/{change_id}/side-by-side", response_model=SideBySideDiffResponse)
async def get_side_by_side_diff(review_id: str, change_id: str) -> SideBySideDiffResponse:
    """
    Get side-by-side diff for a specific change.
    
    Returns original and suggested content aligned for side-by-side comparison,
    with word-level change highlighting.
    
    Requires: FEATURE_SIDE_BY_SIDE_DIFF=true
    """
    features = get_features()
    if not features.enable_side_by_side_diff:
        raise HTTPException(
            status_code=403,
            detail="Side-by-side diff feature is not enabled. Set FEATURE_SIDE_BY_SIDE_DIFF=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    predicted_questions = result.predicted_questions if hasattr(result, 'predicted_questions') else []
    
    # Find the change
    change = None
    for question in predicted_questions:
        if question.suggested_change and str(question.suggested_change.id) == change_id:
            change = question.suggested_change
            break
    
    if not change:
        raise HTTPException(status_code=404, detail="Change not found")
    
    # Get PRD content and file name
    prd_content = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
    file_name = "PRD.md"
    if review_id in prd_file_info_store:
        file_name = prd_file_info_store[review_id].get("file_name", "PRD.md")
    elif hasattr(result, 'intent') and hasattr(result.intent, 'source_document') and result.intent.source_document:
        file_name = result.intent.source_document
    
    # Generate side-by-side diff
    from context_graph.pm import generate_side_by_side_diff
    diff = generate_side_by_side_diff(change, prd_content, file_name)
    
    # Convert to response model
    return SideBySideDiffResponse(
        change_id=diff.change_id,
        file_name=diff.file_name,
        section=diff.section,
        original_lines=[
            DiffLineResponse(
                line_number=line.line_number,
                content=line.content,
                status=line.status,
                word_changes=[
                    WordChangeResponse(start=wc.start, end=wc.end, change_type=wc.change_type)
                    for wc in line.word_changes
                ],
            )
            for line in diff.original_lines
        ],
        suggested_lines=[
            DiffLineResponse(
                line_number=line.line_number,
                content=line.content,
                status=line.status,
                word_changes=[
                    WordChangeResponse(start=wc.start, end=wc.end, change_type=wc.change_type)
                    for wc in line.word_changes
                ],
            )
            for line in diff.suggested_lines
        ],
        stats=DiffStatsResponse(
            lines_added=diff.stats.lines_added,
            lines_removed=diff.stats.lines_removed,
            lines_modified=diff.stats.lines_modified,
        ),
    )


@router.post("/reviews/{review_id}/prd/set-file-path")
async def set_prd_file_path(review_id: str, request: SetPRDFilePathRequest) -> dict[str, Any]:
    """
    Set the file path for a PRD (for saving back to disk).
    
    This should be called when loading a PRD from a file (e.g., via Electron file picker)
    to track where to save changes back.
    
    Requires: FEATURE_PRD_SAVE_TO_FILE=true
    """
    features = get_features()
    if not features.enable_prd_save_to_file:
        raise HTTPException(
            status_code=403,
            detail="PRD save-to-file feature is not enabled. Set FEATURE_PRD_SAVE_TO_FILE=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    import os
    
    # Extract filename from path if not provided
    file_name = request.file_name or os.path.basename(request.file_path)
    
    prd_file_info_store[review_id] = {
        "file_path": request.file_path,
        "file_name": file_name,
        "set_at": datetime.now().isoformat(),
    }
    
    return {
        "set": True,
        "file_path": request.file_path,
        "file_name": file_name,
    }


@router.get("/reviews/{review_id}/prd/file-info")
async def get_prd_file_info(review_id: str) -> dict[str, Any]:
    """
    Get the file path info for a PRD.
    
    Requires: FEATURE_PRD_SAVE_TO_FILE=true
    """
    features = get_features()
    if not features.enable_prd_save_to_file:
        raise HTTPException(
            status_code=403,
            detail="PRD save-to-file feature is not enabled. Set FEATURE_PRD_SAVE_TO_FILE=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review_id not in prd_file_info_store:
        return {
            "has_file_path": False,
            "file_path": None,
            "file_name": None,
        }
    
    info = prd_file_info_store[review_id]
    return {
        "has_file_path": True,
        "file_path": info.get("file_path"),
        "file_name": info.get("file_name"),
        "set_at": info.get("set_at"),
    }


@router.post("/reviews/{review_id}/prd/save-to-file", response_model=SavePRDToFileResponse)
async def save_prd_to_file(review_id: str) -> SavePRDToFileResponse:
    """
    Save the current PRD (with accepted changes) back to the original file.
    
    Creates a backup of the original file before overwriting.
    
    Requires: FEATURE_PRD_SAVE_TO_FILE=true
    """
    import os
    import shutil
    from datetime import datetime
    
    features = get_features()
    if not features.enable_prd_save_to_file:
        raise HTTPException(
            status_code=403,
            detail="PRD save-to-file feature is not enabled. Set FEATURE_PRD_SAVE_TO_FILE=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review_id not in prd_file_info_store:
        raise HTTPException(
            status_code=400,
            detail="No file path set for this PRD. Call /prd/set-file-path first."
        )
    
    file_info = prd_file_info_store[review_id]
    file_path = file_info.get("file_path")
    
    if not file_path:
        raise HTTPException(status_code=400, detail="File path is empty")
    
    # Get current PRD content (result already loaded above)
    if review_id in prd_history_store and prd_history_store[review_id]:
        current_prd = prd_history_store[review_id][-1]
    else:
        current_prd = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
    
    # Create backup
    backup_path = None
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            # Log but don't fail if backup fails
            import logging
            logging.warning(f"Failed to create backup: {e}")
            backup_path = None
    
    # Write updated content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(current_prd)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write file: {str(e)}"
        )
    
    # Update file info with last saved time
    prd_file_info_store[review_id]["last_saved_at"] = datetime.now().isoformat()
    prd_file_info_store[review_id]["backup_path"] = backup_path
    
    return SavePRDToFileResponse(
        saved=True,
        file_path=file_path,
        backup_path=backup_path,
        message=f"PRD saved to {file_path}" + (f" (backup: {backup_path})" if backup_path else ""),
    )


@router.post("/reviews/{review_id}/re-analyze")
async def re_analyze_prd(review_id: str) -> dict[str, Any]:
    """
    Re-analyze PRD after changes - ACTUALLY re-runs the LLM analysis.
    
    This performs a full re-analysis of the updated PRD content:
    1. Gets the PRD with all accepted changes applied
    2. Re-runs the SecurityReviewEngine (with LLM if configured)
    3. Generates new findings based on the updated PRD
    4. Creates new PRD change predictions from the fresh findings
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    import logging
    
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    storage = get_review_storage()
    result = await storage.get_review(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review not found")
    
    original_findings_count = len(result.all_findings)
    
    # Get current PRD (with accepted changes)
    if review_id in prd_history_store and prd_history_store[review_id]:
        current_prd = prd_history_store[review_id][-1]
    else:
        current_prd = result.original_prd_content if hasattr(result, 'original_prd_content') else result.intent.raw_content
    
    # Parse updated PRD to create new Intent
    from context_graph.parsers import MarkdownPRDParser
    parser = MarkdownPRDParser()
    updated_intent = parser.parse(current_prd, result.intent.title)
    updated_intent.raw_content = current_prd
    
    # Re-run the actual security review engine with LLM
    from context_graph.security.review_engine import SecurityReviewEngine, ReviewConfig
    from context_graph.config.features import get_features as get_feat
    import os
    
    # Get API keys from environment (same as original review)
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    has_api_keys = bool(openai_key or anthropic_key)
    
    # Use the same config as the original review, but ensure API keys are set
    if hasattr(result, 'config') and result.config:
        # Use stored config from original review
        config = ReviewConfig(
            dimensions=result.config.dimensions.copy() if result.config.dimensions else result.dimensions_analyzed,
            use_llm=result.config.use_llm and has_api_keys,
            use_pattern_matching=result.config.use_pattern_matching,
            compliance_frameworks=result.config.compliance_frameworks.copy() if result.config.compliance_frameworks else [],
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
        )
    else:
        # Fallback: reconstruct config from available info
        config = ReviewConfig(
            dimensions=result.dimensions_analyzed if hasattr(result, 'dimensions_analyzed') else [],
            use_llm=has_api_keys,
            use_pattern_matching=True,
            compliance_frameworks=[],
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
        )
    
    logging.info(f"Re-analyzing PRD for review {review_id}")
    logging.info(f"  Original findings: {original_findings_count}")
    logging.info(f"  Using LLM: {config.use_llm} (API keys available: {has_api_keys})")
    logging.info(f"  Dimensions: {[d.value for d in config.dimensions]}")
    
    # Run the review engine on the updated PRD
    engine = SecurityReviewEngine(config)
    new_result = await engine.review(updated_intent, result.state)
    
    logging.info(f"Re-analysis complete. New findings: {len(new_result.all_findings)}")
    logging.info(f"  Security: {len(new_result.security_findings)}")
    logging.info(f"  Privacy: {len(new_result.privacy_findings)}")
    logging.info(f"  Compliance: {len(new_result.compliance_findings)}")
    logging.info(f"  Engineering: {len(new_result.engineering_findings)}")
    logging.info(f"  Architecture: {len(new_result.architecture_findings)}")
    
    # Update the stored result with new findings
    result.intent = updated_intent
    result.security_findings = new_result.security_findings
    result.privacy_findings = new_result.privacy_findings
    result.compliance_findings = new_result.compliance_findings
    result.engineering_findings = new_result.engineering_findings
    result.architecture_findings = new_result.architecture_findings
    result.executive_summary = new_result.executive_summary
    result.risk_rating = new_result.risk_rating
    result.config = config  # Preserve config for future re-analyses
    
    # Generate new PRD change predictions from the fresh findings
    feat = get_feat()
    new_findings = new_result.all_findings
    
    if feat.enable_prd_changes and new_findings:
        from context_graph.pm import PRDChangeGenerator, PRDQualityScorer
        
        change_generator = PRDChangeGenerator()
        codebase_state = {
            "api_endpoints": result.state.api_endpoints,
            "data_models": result.state.data_models,
            "auth_patterns": result.state.auth_patterns,
            "existing_controls": result.state.existing_controls,
        }
        
        # Generate predictions from the NEW findings
        result.predicted_questions = change_generator.generate_changes(
            findings=new_findings,
            prd_content=current_prd,
            codebase_state=codebase_state,
        )
        
        logging.info(f"Generated {len(result.predicted_questions)} new PRD change predictions")
    else:
        # No findings = no predictions needed
        result.predicted_questions = []
        logging.info("No findings after re-analysis - PRD is complete!")
    
    if feat.enable_prd_quality_scoring:
        from context_graph.pm import PRDQualityScorer
        quality_scorer = PRDQualityScorer()
        result.prd_quality_score = quality_scorer.calculate_score(
            predicted_questions=result.predicted_questions,
            prd_content=current_prd,
        )
    
    new_findings_count = len(new_result.all_findings)
    predictions_count = len(result.predicted_questions) if result.predicted_questions else 0
    
    return {
        "re_analyzed": True,
        "original_findings_count": original_findings_count,
        "new_findings_count": new_findings_count,
        "findings_reduced_by": original_findings_count - new_findings_count,
        "new_predictions_count": predictions_count,
        "updated_quality_score": result.prd_quality_score.score if hasattr(result, 'prd_quality_score') and result.prd_quality_score else None,
        "message": f"Re-analyzed PRD with {new_findings_count} findings (was {original_findings_count})",
    }


# ==================== PM Preferences ====================

class PMPreferencesRequest(BaseModel):
    """PM preferences update request."""
    feedback_teams: list[str] | None = None
    hidden_teams: list[str] | None = None
    severity_filter: list[str] | None = None  # ["blocker", "likely", "possible"]
    muted_patterns: list[dict[str, Any]] | None = None
    default_codebase: str | None = None


@router.get("/preferences")
async def get_pm_preferences(user_id: str = "default") -> dict[str, Any]:
    """
    Get PM preferences.
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    # Return defaults if not set
    if user_id not in pm_preferences_store:
        return {
            "feedback_teams": ["engineering", "security", "privacy", "infra"],
            "hidden_teams": [],
            "severity_filter": ["blocker", "likely"],
            "muted_patterns": [],
            "default_codebase": None,
        }
    
    return pm_preferences_store[user_id]


@router.put("/preferences")
async def update_pm_preferences(
    request: PMPreferencesRequest,
    user_id: str = "default",
) -> dict[str, Any]:
    """
    Update PM preferences.
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    # Get current preferences or defaults
    current = pm_preferences_store.get(user_id, {
        "feedback_teams": ["engineering", "security", "privacy", "infra"],
        "hidden_teams": [],
        "severity_filter": ["blocker", "likely"],
        "muted_patterns": [],
        "default_codebase": None,
    })
    
    # Update with provided values
    if request.feedback_teams is not None:
        current["feedback_teams"] = request.feedback_teams
    if request.hidden_teams is not None:
        current["hidden_teams"] = request.hidden_teams
    if request.severity_filter is not None:
        current["severity_filter"] = request.severity_filter
    if request.muted_patterns is not None:
        current["muted_patterns"] = request.muted_patterns
    if request.default_codebase is not None:
        current["default_codebase"] = request.default_codebase
    
    pm_preferences_store[user_id] = current
    
    return current


@router.post("/preferences/mute")
async def mute_pattern(
    request: dict[str, Any],
    user_id: str = "default",
) -> dict[str, Any]:
    """
    Mute a specific pattern (hide similar suggestions in future).
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    pattern_id = str(uuid4())
    pattern = {
        "id": pattern_id,
        "pattern": request.get("pattern_description", ""),
        "muted_at": str(uuid4()),  # Should be datetime, simplified
    }
    
    if user_id not in pm_preferences_store:
        pm_preferences_store[user_id] = {
            "feedback_teams": ["engineering", "security", "privacy", "infra"],
            "hidden_teams": [],
            "severity_filter": ["blocker", "likely"],
            "muted_patterns": [],
            "default_codebase": None,
        }
    
    pm_preferences_store[user_id]["muted_patterns"].append(pattern)
    
    return {"muted": True, "pattern_id": pattern_id}


@router.delete("/preferences/mute/{pattern_id}")
async def unmute_pattern(
    pattern_id: str,
    user_id: str = "default",
) -> dict[str, Any]:
    """
    Unmute a pattern.
    
    Requires: FEATURE_PRD_CHANGES=true
    """
    features = get_features()
    if not features.enable_prd_changes:
        raise HTTPException(
            status_code=403,
            detail="PRD changes feature is not enabled. Set FEATURE_PRD_CHANGES=true to enable."
        )
    
    if user_id not in pm_preferences_store:
        raise HTTPException(status_code=404, detail="Preferences not found")
    
    muted_patterns = pm_preferences_store[user_id].get("muted_patterns", [])
    pm_preferences_store[user_id]["muted_patterns"] = [
        p for p in muted_patterns if p.get("id") != pattern_id
    ]
    
    return {"unmuted": True}


# ==================== Pattern Learning ====================

@router.get("/patterns/insights")
async def get_pattern_insights() -> dict[str, Any]:
    """
    Get pattern learning insights.
    
    Requires: FEATURE_PM_PATTERN_LEARNING=true
    """
    features = get_features()
    if not features.enable_pm_pattern_learning:
        raise HTTPException(
            status_code=403,
            detail="PM pattern learning feature is not enabled. Set FEATURE_PM_PATTERN_LEARNING=true to enable."
        )
    
    from context_graph.pm import PatternLearner
    
    # In production, this would load from persistent storage
    learner = PatternLearner()
    # For now, return empty insights (patterns would be loaded from storage)
    
    return learner.get_pattern_insights()


@router.post("/patterns/learn")
async def learn_from_expert_response(
    request: dict[str, Any],
) -> dict[str, Any]:
    """
    Learn a pattern from an expert response.
    
    Requires: FEATURE_PM_PATTERN_LEARNING=true
    """
    features = get_features()
    if not features.enable_pm_pattern_learning:
        raise HTTPException(
            status_code=403,
            detail="PM pattern learning feature is not enabled. Set FEATURE_PM_PATTERN_LEARNING=true to enable."
        )
    
    from context_graph.pm import PatternLearner
    from context_graph.core.models import PredictedQuestion, ExpertResponse, CodeEvidence
    
    # Reconstruct question and response from request
    # (In production, these would be loaded from storage)
    question = PredictedQuestion(
        id=UUID(request["question_id"]),
        question=request.get("question", ""),
        team=request.get("team", ""),
        severity=request.get("severity", ""),
        code_evidence=[
            CodeEvidence(
                file_path=ev.get("file_path", ""),
                context=ev.get("context", ""),
            )
            for ev in request.get("code_evidence", [])
        ],
    )
    
    response = ExpertResponse(
        verdict=request.get("verdict", ""),
        note=request.get("note"),
        correct_answer=request.get("correct_answer"),
        should_learn=request.get("should_learn", True),
    )
    
    learner = PatternLearner()
    pattern = learner.learn_from_response(question, response)
    
    if pattern:
        # In production, save pattern to persistent storage
        return {
            "learned": True,
            "pattern_id": str(pattern.id),
            "pattern_description": pattern.pattern_description,
        }
    
    return {"learned": False, "reason": "No pattern extracted"}


# ==================== Helper Functions ====================

def _apply_change_to_prd(
    prd_content: str,
    change: Any,  # PRDChange type
    edited_text: str | None = None,
) -> str:
    """Apply a PRD change to the PRD content."""
    lines = prd_content.split("\n")
    
    # Use edited text if provided, otherwise use suggested text
    text_to_insert = edited_text if edited_text else change.suggested_text
    
    # Insert at the specified location
    if change.start_line < len(lines):
        # Insert after the section header
        lines.insert(change.start_line, text_to_insert)
    else:
        # Append at end
        lines.append(text_to_insert)
    
    return "\n".join(lines)

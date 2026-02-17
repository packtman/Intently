"""
P2 API Routes — Ecosystem Integration features.

- Decision Log (Feature 7)
- Predictive Risk Scoring (Feature 8)
- PRD Templates Library (Feature 9)
- GitHub PR Finding Sync (Feature 11)
- PRD Authoring Autocomplete (Feature 12)

All routes are feature-flag protected.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage, get_collaboration_storage


router = APIRouter(tags=["p2-features"])


# ==================== Decision Log (Feature 7) ====================

_decision_log: dict[str, list[dict[str, Any]]] = {}  # review_id -> [decisions]


class AddDecisionRequest(BaseModel):
    decision_type: str = Field(..., description="accepted_risk, rejected_finding, approved_prd, scope_change, deferred, escalated")
    title: str = Field(..., min_length=1)
    rationale: str = Field("")
    decided_by: str = Field(...)
    decided_by_team: str = Field("")
    linked_finding_ids: List[str] = Field(default_factory=list)
    alternatives_considered: List[str] = Field(default_factory=list)


@router.post("/reviews/{review_id}/decisions")
@requires_feature("decision_log")
async def add_decision(review_id: str, body: AddDecisionRequest) -> Dict[str, Any]:
    """Manually log a product decision with rationale and linked findings."""
    now = datetime.utcnow().isoformat() + "Z"
    decision = {
        "id": str(uuid4()),
        "review_id": review_id,
        "decision_type": body.decision_type,
        "title": body.title,
        "rationale": body.rationale,
        "decided_by": body.decided_by,
        "decided_by_team": body.decided_by_team,
        "linked_finding_ids": body.linked_finding_ids,
        "alternatives_considered": body.alternatives_considered,
        "created_at": now,
    }
    _decision_log.setdefault(review_id, []).append(decision)
    return decision


@router.get("/reviews/{review_id}/decisions")
@requires_feature("decision_log")
async def list_decisions(review_id: str) -> List[Dict[str, Any]]:
    """List all decisions for a review, chronologically."""
    return _decision_log.get(review_id, [])


@router.get("/decisions/search")
@requires_feature("decision_log")
async def search_decisions(q: str = "") -> List[Dict[str, Any]]:
    """Search across all decision logs by keyword."""
    q_lower = q.lower()
    results = []
    for review_id, decisions in _decision_log.items():
        for d in decisions:
            if (q_lower in d.get("title", "").lower()
                    or q_lower in d.get("rationale", "").lower()):
                results.append(d)
    return results


# ==================== Predictive Risk Scoring (Feature 8) ====================


class PredictRiskRequest(BaseModel):
    description: str = Field(..., min_length=1, description="1-2 sentence feature description")
    affected_systems: List[str] = Field(default_factory=list, description="System names affected")
    change_type: str = Field("", description="new_feature, api_change, data_migration, integration")


@router.post("/predict-risk")
@requires_feature("risk_prediction")
async def predict_risk(request: PredictRiskRequest) -> Dict[str, Any]:
    """Predict risk profile for a planned feature based on historical reviews."""
    from context_graph.pm.risk_predictor import RiskPredictor

    predictor = RiskPredictor(get_review_storage())
    prediction = await predictor.predict(
        feature_description=request.description,
        affected_systems=request.affected_systems,
        change_type=request.change_type,
    )
    return {
        "predicted_findings": prediction.predicted_findings,
        "predicted_severities": prediction.predicted_severities,
        "estimated_review_time": prediction.estimated_review_time,
        "suggested_reviewers": prediction.suggested_reviewers,
        "similar_reviews": prediction.similar_reviews,
        "confidence": prediction.confidence,
        "risk_level": prediction.risk_level,
    }


# ==================== PRD Templates Library (Feature 9) ====================


@router.get("/templates")
@requires_feature("prd_templates")
async def list_templates() -> List[Dict[str, Any]]:
    """List all available PRD templates."""
    from context_graph.pm.template_library import TemplateLibrary

    library = TemplateLibrary()
    templates = library.get_all_templates()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "sections": [
                {"title": s.title, "required": s.required, "guidance": s.guidance}
                for s in t.sections
            ],
            "keywords": t.keywords,
        }
        for t in templates
    ]


@router.get("/templates/{template_id}/render")
@requires_feature("prd_templates")
async def render_template(template_id: str) -> Dict[str, Any]:
    """Render a template as pre-filled markdown."""
    from context_graph.pm.template_library import TemplateLibrary

    library = TemplateLibrary()
    template = library.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    markdown = library.render_template(template_id)
    return {
        "template_id": template_id,
        "name": template.name,
        "markdown": markdown,
    }


@router.get("/templates/suggest")
@requires_feature("prd_templates")
async def suggest_template(content: str = "") -> Dict[str, Any] | None:
    """Suggest a template based on PRD content keywords."""
    from context_graph.pm.template_library import TemplateLibrary

    library = TemplateLibrary()
    suggestion = library.suggest_template(content)
    if not suggestion:
        return {"suggestion": None}
    return {
        "suggestion": {
            "id": suggestion.id,
            "name": suggestion.name,
            "description": suggestion.description,
        },
    }


# ==================== GitHub PR Finding Sync (Feature 11) ====================


class SyncToPRRequest(BaseModel):
    repo: str = Field(..., description="GitHub repo (owner/repo)")
    pr_number: int = Field(..., description="PR number")
    github_token: str | None = Field(None, description="GitHub token (uses env var if not provided)")
    min_severity: str = Field("medium", description="Minimum severity to sync")


@router.post("/reviews/{review_id}/sync-to-pr")
@requires_feature("github_pr_sync")
async def sync_to_pr(review_id: str, request: SyncToPRRequest) -> Dict[str, Any]:
    """Push review findings to a GitHub PR as a summary comment.

    Extends existing GitHubIntegration with PR comment posting.
    """
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    token = request.github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token required (set GITHUB_TOKEN or pass github_token)")

    from context_graph.reports.markdown_report import MarkdownReportGenerator

    # Generate markdown summary
    generator = MarkdownReportGenerator()
    report = generator.generate(review)

    # Truncate for PR comment (GitHub limit ~65536 chars)
    if len(report) > 60000:
        report = report[:60000] + "\n\n---\n*Report truncated. View full report in Intently.*"

    # Post to GitHub
    import httpx

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    comment_url = f"https://api.github.com/repos/{request.repo}/issues/{request.pr_number}/comments"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            comment_url,
            headers=headers,
            json={"body": f"## Intently Review Summary\n\n{report}"},
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"GitHub API error: {resp.text[:200]}",
        )

    return {
        "message": f"Review summary posted to PR #{request.pr_number}",
        "pr_url": f"https://github.com/{request.repo}/pull/{request.pr_number}",
        "findings_count": len(review.all_findings),
    }


# ==================== PRD Authoring Autocomplete (Feature 12) ====================


class AutocompleteRequest(BaseModel):
    current_word: str = Field(..., min_length=1, description="Word being typed")
    context: str = Field("", description="Surrounding text for context")
    review_id: str | None = Field(None, description="Scope to a review's codebase state")


@router.post("/autocomplete")
@requires_feature("prd_authoring_assist")
async def autocomplete(request: AutocompleteRequest) -> List[Dict[str, Any]]:
    """Context-aware autocomplete suggestions from cached codebase state.

    Suggests entity names, API endpoints, data models, and pattern warnings.
    """
    suggestions: list[dict[str, Any]] = []
    query = request.current_word.lower()

    # Load state from a specific review if available
    state = None
    if request.review_id:
        storage = get_review_storage()
        review = await storage.get_review(request.review_id)
        if review:
            state = review.state

    if not state:
        # Try loading from most recent review
        storage = get_review_storage()
        reviews = await storage.list_reviews()
        for r_info in reversed(reviews):
            review = await storage.get_review(r_info.get("review_id", ""))
            if review and review.state.entities:
                state = review.state
                break

    if not state:
        return suggestions

    # Match against entity names
    for entity in state.entities:
        if query in entity.name.lower():
            suggestions.append({
                "text": entity.name,
                "type": entity.entity_type.value,
                "description": entity.description or f"{entity.entity_type.value} in {entity.source}",
                "category": "entity",
            })

    # Match against API endpoints
    for endpoint in state.api_endpoints:
        path = endpoint.get("path", "")
        if query in path.lower():
            method = endpoint.get("method", "GET")
            suggestions.append({
                "text": path,
                "type": "endpoint",
                "description": f"{method} {path}",
                "category": "api",
            })

    # Match against data models
    for model in state.data_models:
        name = model.get("name", "")
        if query in name.lower():
            suggestions.append({
                "text": name,
                "type": "data_model",
                "description": f"Data model in {model.get('file', '')}",
                "category": "model",
            })

    # Limit results
    return suggestions[:10]

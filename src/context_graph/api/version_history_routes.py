"""
PRD Version History API Routes.

Tracks PRD versions with metadata and provides diffing between versions.
Reuses existing SideBySideDiffGenerator for diff computation.

Feature flag: FEATURE_PRD_VERSION_HISTORY=true
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage


router = APIRouter(tags=["version-history"])


# ------------------------------------------------------------------
# In-memory version store (migrate to SQLite in Phase 2)
# ------------------------------------------------------------------

_version_store: dict[str, list[dict[str, Any]]] = {}  # review_id -> [version_data]


# ==================== Request / Response Models ====================


class SaveVersionRequest(BaseModel):
    author: str = Field("", description="Who saved this version")
    change_summary: str = Field("", description="What changed in this version")


class VersionInfo(BaseModel):
    id: str
    review_id: str
    version_number: int
    author: str
    change_summary: str
    quality_score: float | None = None
    finding_count: int | None = None
    content_length: int
    created_at: str


class VersionDiffResponse(BaseModel):
    text_diff: Dict[str, Any]
    analysis_diff: Dict[str, Any]


# ==================== Routes ====================


@router.post("/reviews/{review_id}/versions", response_model=VersionInfo)
@requires_feature("prd_version_history")
async def save_prd_version(
    review_id: str,
    body: SaveVersionRequest | None = None,
) -> VersionInfo:
    """Save the current PRD content as a new version.

    Captures the PRD text, quality score, and finding count at the
    time of save for historical comparison.
    """
    storage = get_review_storage()
    review = await storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    content = review.original_prd_content or review.intent.raw_content or ""
    if not content:
        raise HTTPException(status_code=400, detail="No PRD content to version")

    versions = _version_store.setdefault(review_id, [])
    version_number = len(versions) + 1
    now = datetime.utcnow().isoformat() + "Z"

    quality_score = None
    if review.prd_quality_score:
        quality_score = review.prd_quality_score.score

    version_data = {
        "id": str(uuid4()),
        "review_id": review_id,
        "version_number": version_number,
        "content": content,
        "author": body.author if body else "",
        "change_summary": body.change_summary if body else f"Version {version_number}",
        "quality_score": quality_score,
        "finding_count": len(review.all_findings),
        "content_length": len(content),
        "created_at": now,
    }
    versions.append(version_data)

    return VersionInfo(
        id=version_data["id"],
        review_id=review_id,
        version_number=version_number,
        author=version_data["author"],
        change_summary=version_data["change_summary"],
        quality_score=quality_score,
        finding_count=version_data["finding_count"],
        content_length=version_data["content_length"],
        created_at=now,
    )


@router.get("/reviews/{review_id}/versions", response_model=List[VersionInfo])
@requires_feature("prd_version_history")
async def list_prd_versions(review_id: str) -> List[VersionInfo]:
    """List all PRD versions for a review, oldest first."""

    versions = _version_store.get(review_id, [])
    return [
        VersionInfo(
            id=v["id"],
            review_id=v["review_id"],
            version_number=v["version_number"],
            author=v["author"],
            change_summary=v["change_summary"],
            quality_score=v.get("quality_score"),
            finding_count=v.get("finding_count"),
            content_length=v.get("content_length", 0),
            created_at=v["created_at"],
        )
        for v in versions
    ]


@router.get("/reviews/{review_id}/versions/{v1}/{v2}/diff")
@requires_feature("prd_version_history")
async def get_version_diff(
    review_id: str, v1: int, v2: int
) -> Dict[str, Any]:
    """Compare two PRD versions. Returns text diff and analysis diff.

    Uses the existing SideBySideDiffGenerator for text comparison.
    The analysis diff shows finding count and quality score changes.
    """
    versions = _version_store.get(review_id, [])

    ver_a = next((v for v in versions if v["version_number"] == v1), None)
    ver_b = next((v for v in versions if v["version_number"] == v2), None)

    if not ver_a or not ver_b:
        raise HTTPException(status_code=404, detail=f"Version {v1} or {v2} not found")

    # Text diff using existing diff generator
    from context_graph.pm.diff_generator import SideBySideDiffGenerator
    from context_graph.core.models import PRDChange

    change = PRDChange(
        current_text=ver_a["content"],
        suggested_text=ver_b["content"],
        change_type="modification",
    )
    diff_gen = SideBySideDiffGenerator()
    diff_result = diff_gen.generate_diff(change, ver_a["content"], "PRD.md")

    text_diff = {
        "stats": {
            "lines_added": diff_result.stats.lines_added,
            "lines_removed": diff_result.stats.lines_removed,
            "lines_modified": diff_result.stats.lines_modified,
        },
        "original_lines": [
            {"line_number": l.line_number, "content": l.content, "status": l.status}
            for l in diff_result.original_lines
        ],
        "suggested_lines": [
            {"line_number": l.line_number, "content": l.content, "status": l.status}
            for l in diff_result.suggested_lines
        ],
    }

    # Analysis diff
    analysis_diff = {
        "finding_count": {
            "v1": ver_a.get("finding_count", 0),
            "v2": ver_b.get("finding_count", 0),
            "delta": (ver_b.get("finding_count", 0) or 0) - (ver_a.get("finding_count", 0) or 0),
        },
        "quality_score": {
            "v1": ver_a.get("quality_score"),
            "v2": ver_b.get("quality_score"),
            "delta": (
                (ver_b.get("quality_score") or 0) - (ver_a.get("quality_score") or 0)
                if ver_a.get("quality_score") is not None and ver_b.get("quality_score") is not None
                else None
            ),
        },
        "content_length": {
            "v1": ver_a.get("content_length", 0),
            "v2": ver_b.get("content_length", 0),
        },
    }

    return {
        "text_diff": text_diff,
        "analysis_diff": analysis_diff,
        "version_a": {
            "version_number": v1,
            "author": ver_a["author"],
            "created_at": ver_a["created_at"],
        },
        "version_b": {
            "version_number": v2,
            "author": ver_b["author"],
            "created_at": ver_b["created_at"],
        },
    }

"""
Live Analysis API — Real-time PRD quality coaching while writing.

Runs a lightweight pipeline (parser + quality scorer) with NO LLM calls.
Returns only the quality score and missing-section gaps to guide PM writing
without producing findings that would conflict with the full LLM review.

Target latency: <200ms.

Feature flag: FEATURE_LIVE_ANALYSIS=true
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature


router = APIRouter(tags=["live-analysis"])


class LiveAnalyzeRequest(BaseModel):
    prd_content: str = Field(..., min_length=1, description="Current PRD text")


class LiveAnalyzeResponse(BaseModel):
    quality_score: Dict[str, Any]


@router.post("/reviews/live-analyze", response_model=LiveAnalyzeResponse)
@requires_feature("live_analysis")
async def live_analyze(request: LiveAnalyzeRequest) -> LiveAnalyzeResponse:
    """Lightweight PRD quality coaching for real-time feedback. No LLM calls.

    Pipeline: parse PRD → quality score + gap detection.
    All components are synchronous and heuristic-based, targeting <200ms.
    """
    from context_graph.parsers import MarkdownPRDParser
    from context_graph.pm.quality_scorer import PRDQualityScorer

    parser = MarkdownPRDParser()
    parser.parse(request.prd_content, "Live Preview")

    quality = PRDQualityScorer().calculate_score([], request.prd_content)

    return LiveAnalyzeResponse(
        quality_score={
            "score": quality.score,
            "grade": quality.grade,
            "gaps": quality.gaps,
        },
    )

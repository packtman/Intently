"""
Live Analysis API — Real-time PRD analysis while writing.

Runs a lightweight analysis pipeline (parser + delta + pattern matchers +
quality scorer) with NO LLM calls. Target latency: <500ms.

Feature flag: FEATURE_LIVE_ANALYSIS=true
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage


router = APIRouter(tags=["live-analysis"])


class LiveAnalyzeRequest(BaseModel):
    prd_content: str = Field(..., min_length=1, description="Current PRD text")
    review_id: str | None = Field(
        None, description="If set, use cached State from this review for delta analysis"
    )


class LiveAnalyzeResponse(BaseModel):
    quality_score: Dict[str, Any]
    finding_counts: Dict[str, int]
    total_findings: int
    severity_breakdown: Dict[str, int]
    top_issues: List[Dict[str, Any]]


@router.post("/reviews/live-analyze", response_model=LiveAnalyzeResponse)
@requires_feature("live_analysis")
async def live_analyze(request: LiveAnalyzeRequest) -> LiveAnalyzeResponse:
    """Lightweight PRD analysis for real-time feedback. No LLM calls.

    Pipeline: parse PRD → compute delta → run pattern matchers → quality score.
    All components are synchronous and pattern-based, targeting <500ms.
    """
    from context_graph.parsers import MarkdownPRDParser
    from context_graph.core.models import State, Severity
    from context_graph.security.delta_analyzer import DeltaAnalyzer
    from context_graph.security.threat_patterns import ThreatPatternMatcher
    from context_graph.pm.quality_scorer import PRDQualityScorer

    # 1. Parse PRD
    parser = MarkdownPRDParser()
    intent = parser.parse(request.prd_content, "Live Preview")

    # 2. Load cached state or use empty state
    state = State()
    if request.review_id:
        storage = get_review_storage()
        review = await storage.get_review(request.review_id)
        if review:
            state = review.state

    # 3. Compute delta
    delta_result = DeltaAnalyzer().analyze(intent, state)

    # 4. Run fast pattern matchers (no LLM)
    security_findings = ThreatPatternMatcher().match(delta_result)

    privacy_findings = []
    compliance_findings = []
    engineering_findings = []
    architecture_findings = []

    try:
        from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
        privacy_findings = PrivacyPatternMatcher().match(delta_result)
    except Exception:
        pass

    try:
        from context_graph.security.compliance_analyzer import CompliancePatternMatcher
        compliance_findings = CompliancePatternMatcher().match(delta_result)
    except Exception:
        pass

    try:
        from context_graph.security.engineering_patterns import EngineeringPatternMatcher
        engineering_findings = EngineeringPatternMatcher().match(
            delta_result, state=state, engineering_metrics={}
        )
    except Exception:
        pass

    try:
        from context_graph.security.architecture_patterns import ArchitecturePatternMatcher
        architecture_findings = ArchitecturePatternMatcher().match(
            delta_result, state=state, intent=intent, architecture_metrics={}
        )
    except Exception:
        pass

    all_findings = (
        security_findings + privacy_findings + compliance_findings
        + engineering_findings + architecture_findings
    )

    # 5. Quality score
    quality = PRDQualityScorer().calculate_score([], request.prd_content)

    # 6. Severity breakdown
    severity_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in all_findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

    # 7. Top issues (up to 5)
    top_issues = []
    sorted_findings = sorted(
        all_findings,
        key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(
            f.severity.value if hasattr(f.severity, "value") else str(f.severity), 5
        ),
    )
    for f in sorted_findings[:5]:
        dim = f.dimension.value if hasattr(f, "dimension") and hasattr(f.dimension, "value") else "security"
        top_issues.append({
            "title": f.title,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "dimension": dim,
        })

    return LiveAnalyzeResponse(
        quality_score={
            "score": quality.score,
            "grade": quality.grade,
            "gaps": quality.gaps,
        },
        finding_counts={
            "security": len(security_findings),
            "privacy": len(privacy_findings),
            "compliance": len(compliance_findings),
            "engineering": len(engineering_findings),
            "architecture": len(architecture_findings),
        },
        total_findings=len(all_findings),
        severity_breakdown=severity_breakdown,
        top_issues=top_issues,
    )

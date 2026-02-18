"""
Analytics & Overview API Routes.

Provides:
- Review analytics: aggregated stats across all reviews (Feature 10)
- Product health overview: org-wide risk view (Feature 14)
- Approval gate evaluation endpoint (Feature 6)

All data comes from existing SQLite tables — pure aggregation.

Feature flags: FEATURE_REVIEW_ANALYTICS, FEATURE_PRODUCT_OVERVIEW, FEATURE_APPROVAL_GATES
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature, get_features
from context_graph.storage.config import get_review_storage, get_collaboration_storage


router = APIRouter(tags=["analytics"])


# ==================== Review Analytics (Feature 10) ====================


@router.get("/analytics")
@requires_feature("review_analytics")
async def get_analytics() -> Dict[str, Any]:
    """Aggregate analytics across all reviews.

    Returns: total reviews, findings by dimension and severity,
    quality score trends, resolution stats, and top finding categories.
    """
    storage = get_review_storage()
    reviews_list = await storage.list_reviews()

    total = len(reviews_list)
    completed = sum(1 for r in reviews_list if r.get("status") == "completed")

    # Load full reviews for finding aggregation
    dim_counts: Dict[str, int] = {
        "security": 0, "privacy": 0, "compliance": 0,
        "engineering": 0, "architecture": 0,
    }
    sev_counts: Dict[str, int] = {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
    }
    quality_trend: List[Dict[str, Any]] = []
    total_findings = 0
    category_counter: Dict[str, int] = {}

    for r_info in reviews_list:
        rid = r_info.get("review_id", "")
        review = await storage.get_review(rid)
        if not review:
            continue

        dim_counts["security"] += len(review.security_findings)
        dim_counts["privacy"] += len(review.privacy_findings)
        dim_counts["compliance"] += len(review.compliance_findings)
        dim_counts["engineering"] += len(review.engineering_findings)
        dim_counts["architecture"] += len(review.architecture_findings)

        for f in review.all_findings:
            total_findings += 1
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

            cat = ""
            if hasattr(f, "category"):
                cat = f.category.value if hasattr(f.category, "value") else str(f.category)
            if cat:
                category_counter[cat] = category_counter.get(cat, 0) + 1

        if review.prd_quality_score:
            quality_trend.append({
                "review_id": rid,
                "date": review.reviewed_at.isoformat() if hasattr(review.reviewed_at, "isoformat") else str(review.reviewed_at),
                "score": review.prd_quality_score.score,
                "grade": review.prd_quality_score.grade,
            })

    avg_findings = total_findings / total if total > 0 else 0

    # Top finding categories
    top_categories = sorted(category_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "overview": {
            "total_reviews": total,
            "completed": completed,
            "total_findings": total_findings,
            "avg_findings_per_review": round(avg_findings, 1),
        },
        "findings_by_dimension": dim_counts,
        "findings_by_severity": sev_counts,
        "quality_trend": quality_trend,
        "top_finding_categories": [
            {"category": cat, "count": count} for cat, count in top_categories
        ],
    }


# ==================== Product Health Overview (Feature 14) ====================


@router.get("/overview")
@requires_feature("product_overview")
async def get_product_overview() -> Dict[str, Any]:
    """Org-wide product health overview.

    Returns: active PRDs, risk heatmap across dimensions × severities,
    team workloads, and trending finding patterns.
    """
    storage = get_review_storage()
    reviews_list = await storage.list_reviews()

    # Active PRDs = not completed
    active = [r for r in reviews_list if r.get("status") != "completed"]
    completed = [r for r in reviews_list if r.get("status") == "completed"]

    # Risk heatmap: dimension × severity
    heatmap: Dict[str, Dict[str, int]] = {
        dim: {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for dim in ["security", "privacy", "compliance", "engineering", "architecture"]
    }

    # Trending patterns (categories from recent reviews)
    category_counter: Dict[str, int] = {}

    for r_info in reviews_list[-20:]:  # Last 20 reviews for recency
        review = await storage.get_review(r_info.get("review_id", ""))
        if not review:
            continue

        dimension_findings = {
            "security": review.security_findings,
            "privacy": review.privacy_findings,
            "compliance": review.compliance_findings,
            "engineering": review.engineering_findings,
            "architecture": review.architecture_findings,
        }
        for dim, findings in dimension_findings.items():
            for f in findings:
                sev = f.severity.value if hasattr(f.severity, "value") else "medium"
                if sev in heatmap[dim]:
                    heatmap[dim][sev] += 1

                cat = ""
                if hasattr(f, "category"):
                    cat = f.category.value if hasattr(f.category, "value") else str(f.category)
                if cat:
                    category_counter[cat] = category_counter.get(cat, 0) + 1

    trending = sorted(category_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "active_prds": [
            {
                "review_id": r.get("review_id", ""),
                "title": r.get("title", ""),
                "status": r.get("status", ""),
                "created_at": r.get("created_at", ""),
            }
            for r in active[:10]
        ],
        "risk_heatmap": heatmap,
        "trending_patterns": [
            {"category": cat, "count": cnt} for cat, cnt in trending
        ],
        "summary": {
            "total_reviews": len(reviews_list),
            "active_reviews": len(active),
            "completed_reviews": len(completed),
        },
    }


# ==================== Approval Gates (Feature 6) ====================


class EvaluateGatesResponse(BaseModel):
    gates: List[Dict[str, Any]]
    all_passed: bool
    blocking_failures: int


@router.get("/reviews/{review_id}/gates")
@requires_feature("approval_gates")
async def evaluate_gates(review_id: str) -> Dict[str, Any]:
    """Evaluate approval gates for a review.

    Loads gate definitions from context-graph.yaml and evaluates each
    against the current review state (findings, validations, quality score).
    """
    from context_graph.governance.gate_evaluator import (
        GateEvaluator,
        load_gates_from_config,
    )

    gates = load_gates_from_config()
    if not gates:
        return {
            "gates": [],
            "all_passed": True,
            "blocking_failures": 0,
            "message": "No approval gates configured. Add 'approval_gates' to context-graph.yaml.",
        }

    evaluator = GateEvaluator(
        review_storage=get_review_storage(),
        collaboration_storage=get_collaboration_storage(),
    )

    results = await evaluator.evaluate_all(review_id, gates)

    gate_results = []
    for r in results:
        gate_results.append({
            "name": r.gate.name,
            "condition": r.gate.condition,
            "blocking": r.gate.blocking,
            "passed": r.passed,
            "reason": r.reason,
            "details": r.details,
        })

    blocking_failures = sum(1 for r in results if not r.passed and r.gate.blocking)

    return {
        "gates": gate_results,
        "all_passed": all(r.passed for r in results),
        "blocking_failures": blocking_failures,
    }

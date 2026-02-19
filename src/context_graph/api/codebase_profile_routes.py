"""
Codebase Security Profile API Routes.

Provides persistent codebase profiles that accumulate across reviews:
- Attack surface map (endpoints, auth coverage, PII handling)
- Entity inventory (data models, sensitivity, sources)
- Cumulative findings (by dimension, severity, recurring categories)
- Coverage (files/endpoints reviewed vs. total)
- Historical trend (risk rating and finding counts over time)

Feature flag: FEATURE_CODEBASE_PROFILE
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from context_graph.config.features import requires_feature
from context_graph.storage.config import get_review_storage, get_collaboration_storage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["codebase-profile"])


class BuildProfileRequest(BaseModel):
    codebase_path: str = Field(..., description="Path to codebase (local or GitHub URL)")
    display_name: Optional[str] = Field(None, description="Friendly name for the profile")


def _path_to_id(codebase_path: str) -> str:
    """Deterministic profile ID from codebase path."""
    normalized = codebase_path.rstrip("/").lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _normalize_path(path: str) -> str:
    """Normalize a codebase path for comparison."""
    return path.rstrip("/").rstrip("\\")


def _paths_match(stored_path: str, query_path: str) -> bool:
    """Check if two codebase paths refer to the same codebase."""
    a = _normalize_path(stored_path).lower()
    b = _normalize_path(query_path).lower()
    if a == b:
        return True
    # Match if one is a suffix of the other (handles /home/user/project vs project)
    return a.endswith("/" + b.split("/")[-1]) or b.endswith("/" + a.split("/")[-1])


async def _build_profile_from_reviews(
    codebase_path: str,
    display_name: str,
) -> Dict[str, Any]:
    """Aggregate all reviews for a codebase into a profile."""
    review_storage = get_review_storage()
    reviews_list = await review_storage.list_reviews()

    matching_review_ids: List[str] = []
    for r_info in reviews_list:
        rid = r_info.get("review_id", "")
        review = await review_storage.get_review(rid)
        if not review:
            continue
        if _paths_match(review.state.codebase_path, codebase_path):
            matching_review_ids.append(rid)

    # Aggregate data across matching reviews
    all_endpoints: Dict[str, Dict[str, Any]] = {}
    all_entities: Dict[str, Dict[str, Any]] = {}
    auth_patterns_seen: List[str] = []
    files_touched: set[str] = set()

    dim_counts: Dict[str, int] = {
        "security": 0, "privacy": 0, "compliance": 0,
        "engineering": 0, "architecture": 0,
    }
    sev_counts: Dict[str, int] = {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
    }
    category_counter: Counter[str] = Counter()
    trend_entries: List[Dict[str, Any]] = []

    latest_state_files = 0
    latest_state_endpoints_count = 0
    last_review_id: str | None = None

    for rid in matching_review_ids:
        review = await review_storage.get_review(rid)
        if not review:
            continue

        last_review_id = rid
        state = review.state

        # Endpoints
        for ep in state.api_endpoints:
            ep_key = f"{ep.get('method', 'GET')}:{ep.get('path', ep.get('name', ''))}"
            if ep_key not in all_endpoints:
                all_endpoints[ep_key] = {
                    "path": ep.get("path", ep.get("name", "")),
                    "method": ep.get("method", "GET"),
                    "has_auth": bool(ep.get("auth") or ep.get("requires_auth")),
                    "handles_pii": bool(ep.get("pii") or ep.get("handles_pii")),
                    "public": not bool(ep.get("auth") or ep.get("requires_auth")),
                    "review_count": 0,
                }
            all_endpoints[ep_key]["review_count"] += 1

        # Entities
        for entity in state.entities:
            e_name = entity.name
            if e_name not in all_entities:
                all_entities[e_name] = {
                    "name": e_name,
                    "type": entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
                    "is_sensitive": entity.is_sensitive,
                    "source_file": entity.source or "",
                    "review_count": 0,
                }
            all_entities[e_name]["review_count"] += 1
            if entity.is_sensitive:
                all_entities[e_name]["is_sensitive"] = True

        # Auth patterns
        for ap in state.auth_patterns:
            pattern_name = ap.get("name", ap.get("pattern", str(ap)))
            if pattern_name not in auth_patterns_seen:
                auth_patterns_seen.append(pattern_name)

        # Track files
        if state.files_analyzed:
            latest_state_files = max(latest_state_files, state.files_analyzed)
        latest_state_endpoints_count = max(latest_state_endpoints_count, len(state.api_endpoints))

        # Findings
        dim_counts["security"] += len(review.security_findings)
        dim_counts["privacy"] += len(review.privacy_findings)
        dim_counts["compliance"] += len(review.compliance_findings)
        dim_counts["engineering"] += len(review.engineering_findings)
        dim_counts["architecture"] += len(review.architecture_findings)

        for f in review.all_findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

            cat = ""
            if hasattr(f, "category"):
                cat = f.category.value if hasattr(f.category, "value") else str(f.category)
            if cat:
                category_counter[cat] += 1

            # Track affected files
            if hasattr(f, "affected_files"):
                for af in f.affected_files:
                    files_touched.add(af)
            if hasattr(f, "source_reference") and f.source_reference:
                files_touched.add(f.source_reference.split(":")[0])

        # Trend entry
        quality_score = None
        if review.prd_quality_score:
            quality_score = review.prd_quality_score.score

        trend_entries.append({
            "review_id": rid,
            "date": review.reviewed_at.isoformat() if hasattr(review.reviewed_at, "isoformat") else str(review.reviewed_at),
            "risk_rating": review.risk_rating or "UNKNOWN",
            "finding_count": len(review.all_findings),
            "quality_score": quality_score,
        })

    # Build attack surface
    endpoints_list = list(all_endpoints.values())
    auth_count = sum(1 for ep in endpoints_list if ep.get("has_auth"))
    pii_count = sum(1 for ep in endpoints_list if ep.get("handles_pii"))
    public_count = sum(1 for ep in endpoints_list if ep.get("public"))

    attack_surface = {
        "total_endpoints": len(endpoints_list),
        "endpoints": endpoints_list[:100],  # Cap for large codebases
        "auth_coverage": round(auth_count / max(len(endpoints_list), 1), 2),
        "pii_endpoints": pii_count,
        "public_endpoints": public_count,
        "auth_patterns": auth_patterns_seen,
    }

    # Build entity inventory
    entities_list = list(all_entities.values())
    sensitive_count = sum(1 for e in entities_list if e.get("is_sensitive"))
    type_counter: Counter[str] = Counter()
    for e in entities_list:
        type_counter[e.get("type", "unknown")] += 1

    entity_inventory = {
        "total_entities": len(entities_list),
        "entities": entities_list[:200],
        "sensitive_count": sensitive_count,
        "by_type": dict(type_counter),
    }

    # Build cumulative findings
    total_findings = sum(dim_counts.values())
    recurring = [
        {"category": cat, "count": cnt, "last_seen_review": last_review_id}
        for cat, cnt in category_counter.most_common(20)
    ]

    cumulative_findings = {
        "total_findings": total_findings,
        "by_dimension": dim_counts,
        "by_severity": sev_counts,
        "recurring_categories": recurring,
    }

    # Build coverage
    files_touched_count = len(files_touched)
    endpoints_reviewed = sum(1 for ep in endpoints_list if ep.get("review_count", 0) > 0)

    coverage = {
        "total_files_in_codebase": latest_state_files,
        "files_touched_by_reviews": files_touched_count,
        "coverage_percent": round(
            (files_touched_count / max(latest_state_files, 1)) * 100, 1
        ),
        "endpoints_reviewed": endpoints_reviewed,
        "endpoints_total": latest_state_endpoints_count or len(endpoints_list),
        "endpoint_coverage_percent": round(
            (endpoints_reviewed / max(latest_state_endpoints_count, len(endpoints_list), 1)) * 100, 1
        ),
    }

    # Build historical trend (sorted by date)
    trend_entries.sort(key=lambda x: x["date"])

    historical_trend = {
        "reviews": trend_entries,
    }

    # Save profile
    profile_id = _path_to_id(codebase_path)
    collab_storage = get_collaboration_storage()

    profile = await collab_storage.save_codebase_profile(
        profile_id=profile_id,
        codebase_path=codebase_path,
        display_name=display_name,
        attack_surface=attack_surface,
        entity_inventory=entity_inventory,
        cumulative_findings=cumulative_findings,
        coverage=coverage,
        historical_trend=historical_trend,
        review_count=len(matching_review_ids),
        last_review_id=last_review_id,
    )

    return profile


# ==================== Endpoints ====================


@router.post("/codebase-profiles/build")
@requires_feature("codebase_profile")
async def build_codebase_profile(request: BuildProfileRequest) -> Dict[str, Any]:
    """Build or rebuild a codebase security profile from review history.

    Aggregates all reviews matching the given codebase path into a
    persistent profile with attack surface, entity inventory, findings,
    coverage, and trend data.
    """
    display_name = request.display_name or request.codebase_path.rstrip("/").split("/")[-1]

    try:
        profile = await _build_profile_from_reviews(
            codebase_path=request.codebase_path,
            display_name=display_name,
        )
    except Exception as e:
        logger.exception("Failed to build codebase profile")
        raise HTTPException(status_code=500, detail=f"Failed to build profile: {e}")

    return profile


@router.get("/codebase-profiles")
@requires_feature("codebase_profile")
async def list_codebase_profiles() -> List[Dict[str, Any]]:
    """List all codebase security profiles."""
    storage = get_collaboration_storage()
    return await storage.list_codebase_profiles()


@router.get("/codebase-profiles/{profile_id}")
@requires_feature("codebase_profile")
async def get_codebase_profile(profile_id: str) -> Dict[str, Any]:
    """Get a specific codebase security profile."""
    storage = get_collaboration_storage()
    profile = await storage.get_codebase_profile(profile_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


@router.delete("/codebase-profiles/{profile_id}")
@requires_feature("codebase_profile")
async def delete_codebase_profile(profile_id: str) -> Dict[str, str]:
    """Delete a codebase security profile."""
    storage = get_collaboration_storage()
    deleted = await storage.delete_codebase_profile(profile_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"status": "deleted", "profile_id": profile_id}

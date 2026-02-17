"""
Predictive Risk Scoring — predict risk profile before writing a PRD.

Analyzes historical review data to predict expected finding counts,
severities, and suggest reviewers based on similar past features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from context_graph.storage.base import ReviewStorage

logger = logging.getLogger(__name__)


@dataclass
class RiskPrediction:
    """Predicted risk profile for a planned feature."""

    predicted_findings: dict[str, int] = field(default_factory=dict)
    predicted_severities: dict[str, int] = field(default_factory=dict)
    estimated_review_time: str = ""
    suggested_reviewers: list[str] = field(default_factory=list)
    similar_reviews: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    risk_level: str = "medium"


class RiskPredictor:
    """Predicts risk profile from historical reviews."""

    def __init__(self, review_storage: ReviewStorage) -> None:
        self.review_storage = review_storage

    async def predict(
        self,
        feature_description: str,
        affected_systems: list[str] | None = None,
        change_type: str | None = None,
    ) -> RiskPrediction:
        """Predict risk based on historical reviews."""

        reviews = await self.review_storage.list_reviews()
        keywords = set(feature_description.lower().split())
        affected = set(s.lower() for s in (affected_systems or []))

        scored: list[tuple[float, dict, Any]] = []
        for r_info in reviews:
            rid = r_info.get("review_id", "")
            review = await self.review_storage.get_review(rid)
            if not review or not review.all_findings:
                continue

            similarity = self._compute_similarity(keywords, affected, review)
            if similarity > 0:
                scored.append((similarity, r_info, review))

        scored.sort(key=lambda x: x[0], reverse=True)
        similar = scored[:5]

        if not similar:
            return RiskPrediction(
                predicted_findings={"security": 0, "privacy": 0, "compliance": 0,
                                    "engineering": 0, "architecture": 0},
                predicted_severities={"critical": 0, "high": 0, "medium": 0, "low": 0},
                estimated_review_time="Unknown (no similar reviews found)",
                confidence=0.0,
                risk_level="unknown",
            )

        # Aggregate findings across similar reviews
        dim_totals: dict[str, list[int]] = {
            "security": [], "privacy": [], "compliance": [],
            "engineering": [], "architecture": [],
        }
        sev_totals: dict[str, list[int]] = {
            "critical": [], "high": [], "medium": [], "low": [],
        }
        reviewer_teams: dict[str, int] = {}

        for sim_score, r_info, review in similar:
            dim_totals["security"].append(len(review.security_findings))
            dim_totals["privacy"].append(len(review.privacy_findings))
            dim_totals["compliance"].append(len(review.compliance_findings))
            dim_totals["engineering"].append(len(review.engineering_findings))
            dim_totals["architecture"].append(len(review.architecture_findings))

            for f in review.all_findings:
                sev = f.severity.value if hasattr(f.severity, "value") else "medium"
                sev_totals.setdefault(sev, []).append(1)

            for dim in review.dimensions_analyzed:
                team = dim.value
                reviewer_teams[team] = reviewer_teams.get(team, 0) + 1

        # Average predictions
        predicted_findings = {
            dim: round(sum(counts) / len(counts)) if counts else 0
            for dim, counts in dim_totals.items()
        }
        predicted_severities = {
            sev: round(sum(counts) / len(similar)) if counts else 0
            for sev, counts in sev_totals.items()
        }

        total_predicted = sum(predicted_findings.values())
        if predicted_severities.get("critical", 0) > 0:
            risk_level = "critical"
        elif predicted_severities.get("high", 0) > 2:
            risk_level = "high"
        elif total_predicted > 5:
            risk_level = "medium"
        else:
            risk_level = "low"

        suggested_reviewers = sorted(reviewer_teams, key=reviewer_teams.get, reverse=True)[:3]

        estimated_time = "1-2 hours" if total_predicted < 10 else "2-4 hours" if total_predicted < 20 else "4+ hours"

        similar_reviews = [
            {
                "review_id": r_info.get("review_id", ""),
                "title": r_info.get("title", ""),
                "findings_count": len(review.all_findings),
                "similarity": round(sim_score, 2),
            }
            for sim_score, r_info, review in similar
        ]

        confidence = min(1.0, len(similar) / 5.0)

        return RiskPrediction(
            predicted_findings=predicted_findings,
            predicted_severities=predicted_severities,
            estimated_review_time=estimated_time,
            suggested_reviewers=suggested_reviewers,
            similar_reviews=similar_reviews,
            confidence=round(confidence, 2),
            risk_level=risk_level,
        )

    def _compute_similarity(
        self,
        keywords: set[str],
        affected_systems: set[str],
        review: Any,
    ) -> float:
        """Score similarity between the description and a past review."""
        score = 0.0

        # Keyword match against intent features
        review_words = set()
        for feature in review.intent.features:
            review_words.update(feature.lower().split())
        if review.intent.title:
            review_words.update(review.intent.title.lower().split())
        if review.intent.summary:
            review_words.update(review.intent.summary.lower().split())

        # Remove stop words
        stop_words = {"the", "a", "an", "is", "are", "and", "or", "to", "for", "in", "of", "with"}
        keywords = keywords - stop_words
        review_words = review_words - stop_words

        overlap = keywords & review_words
        if keywords:
            score += len(overlap) / len(keywords) * 0.6

        # Entity/system match
        if affected_systems:
            review_entities = {e.name.lower() for e in review.state.entities}
            entity_overlap = affected_systems & review_entities
            score += len(entity_overlap) / len(affected_systems) * 0.4

        return score

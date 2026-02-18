"""
Approval Gate Evaluator — configurable policies for PRD approval.

Gates are evaluated when a review lifecycle attempts to advance to
'approved'. If any blocking gate fails, the transition is rejected.

Gates can be loaded from context-graph.yaml or configured via API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from context_graph.storage.base import ReviewStorage, CollaborationStorage

logger = logging.getLogger(__name__)


@dataclass
class ApprovalGate:
    """A single approval gate condition."""

    name: str
    condition: str  # e.g. "no_unresolved_critical", "team_approved:security", "quality_score_above:70"
    blocking: bool = True  # True = hard block, False = warning
    description: str = ""


@dataclass
class GateResult:
    """Result of evaluating a single gate."""

    gate: ApprovalGate
    passed: bool
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class GateEvaluator:
    """Evaluates approval gates against current review state.

    Queries existing ReviewStorage and CollaborationStorage to
    check each gate condition. No new storage required.
    """

    def __init__(
        self,
        review_storage: ReviewStorage,
        collaboration_storage: CollaborationStorage,
    ) -> None:
        self.review_storage = review_storage
        self.collab_storage = collaboration_storage

    async def evaluate_all(
        self,
        review_id: str,
        gates: list[ApprovalGate],
    ) -> list[GateResult]:
        """Evaluate all gates for a review. Returns results for each gate."""

        results: list[GateResult] = []
        review = await self.review_storage.get_review(review_id)

        if not review:
            return [
                GateResult(
                    gate=g,
                    passed=False,
                    reason="Review not found",
                )
                for g in gates
            ]

        for gate in gates:
            result = await self._evaluate_gate(review_id, review, gate)
            results.append(result)

        return results

    def has_blocking_failures(self, results: list[GateResult]) -> bool:
        """Check if any blocking gate failed."""
        return any(not r.passed and r.gate.blocking for r in results)

    async def _evaluate_gate(
        self,
        review_id: str,
        review: Any,
        gate: ApprovalGate,
    ) -> GateResult:
        """Evaluate a single gate condition."""

        condition = gate.condition
        try:
            if condition == "no_unresolved_critical":
                return await self._check_no_unresolved_critical(review_id, review, gate)

            elif condition.startswith("team_approved:"):
                team = condition.split(":", 1)[1]
                return await self._check_team_approved(review_id, team, gate)

            elif condition.startswith("quality_score_above:"):
                threshold = int(condition.split(":", 1)[1])
                return self._check_quality_score(review, threshold, gate)

            elif condition == "all_findings_reviewed":
                return await self._check_all_findings_reviewed(review_id, review, gate)

            else:
                return GateResult(
                    gate=gate,
                    passed=True,
                    reason=f"Unknown gate condition: {condition} (skipped)",
                )

        except Exception as exc:
            logger.error("Gate evaluation failed for '%s': %s", gate.name, exc)
            return GateResult(
                gate=gate,
                passed=False,
                reason=f"Evaluation error: {exc}",
            )

    async def _check_no_unresolved_critical(
        self, review_id: str, review: Any, gate: ApprovalGate
    ) -> GateResult:
        """Check that all critical findings are validated or accepted as risk."""

        critical_findings = [
            f for f in review.all_findings
            if hasattr(f, "severity") and f.severity.value == "critical"
        ]

        if not critical_findings:
            return GateResult(gate=gate, passed=True, reason="No critical findings")

        validations = await self.collab_storage.get_validations_for_review(review_id)

        unresolved = []
        resolved_statuses = {"validated", "rejected", "accepted_risk", "deferred"}
        for f in critical_findings:
            fid = str(f.id)
            val = validations.get(fid)
            if not val or val.get("status", "pending") not in resolved_statuses:
                unresolved.append(f.title)

        passed = len(unresolved) == 0
        reason = (
            f"{len(unresolved)} unresolved critical finding(s)"
            if not passed
            else "All critical findings resolved"
        )

        return GateResult(
            gate=gate,
            passed=passed,
            reason=reason,
            details={"unresolved_titles": unresolved},
        )

    async def _check_team_approved(
        self, review_id: str, team: str, gate: ApprovalGate
    ) -> GateResult:
        """Check that a specific team has approved (via validation or consensus)."""

        validations = await self.collab_storage.get_validations_for_review(review_id)

        team_validations = [
            v for v in validations.values()
            if isinstance(v, dict) and v.get("validator_team") == team
        ]

        if not team_validations:
            return GateResult(
                gate=gate,
                passed=False,
                reason=f"No validations from {team} team",
            )

        approved_count = sum(
            1 for v in team_validations if v.get("status") in ("validated", "accepted_risk")
        )
        total = len(team_validations)

        passed = approved_count > 0
        return GateResult(
            gate=gate,
            passed=passed,
            reason=f"{team} team: {approved_count}/{total} findings reviewed",
            details={"team": team, "approved": approved_count, "total": total},
        )

    def _check_quality_score(
        self, review: Any, threshold: int, gate: ApprovalGate
    ) -> GateResult:
        """Check that PRD quality score is above a threshold."""

        score = None
        if review.prd_quality_score:
            score = review.prd_quality_score.score

        if score is None:
            return GateResult(
                gate=gate,
                passed=False,
                reason="No quality score available (enable FEATURE_PRD_QUALITY_SCORING)",
            )

        passed = score >= threshold
        return GateResult(
            gate=gate,
            passed=passed,
            reason=f"Quality score: {score:.0f} (threshold: {threshold})",
            details={"score": score, "threshold": threshold},
        )

    async def _check_all_findings_reviewed(
        self, review_id: str, review: Any, gate: ApprovalGate
    ) -> GateResult:
        """Check that all findings have been validated (any status except pending)."""

        all_findings = review.all_findings
        if not all_findings:
            return GateResult(gate=gate, passed=True, reason="No findings to review")

        validations = await self.collab_storage.get_validations_for_review(review_id)

        unreviewed = 0
        for f in all_findings:
            fid = str(f.id)
            val = validations.get(fid)
            if not val or val.get("status", "pending") == "pending":
                unreviewed += 1

        passed = unreviewed == 0
        return GateResult(
            gate=gate,
            passed=passed,
            reason=f"{unreviewed} finding(s) still pending review" if not passed else "All findings reviewed",
            details={"unreviewed": unreviewed, "total": len(all_findings)},
        )


def load_gates_from_config(config_path: str | Path | None = None) -> list[ApprovalGate]:
    """Load approval gates from context-graph.yaml.

    Returns an empty list if no gates are configured.
    """
    if config_path is None:
        config_path = Path.cwd() / "context-graph.yaml"

    path = Path(config_path)
    if not path.exists():
        return []

    try:
        with open(path) as f:
            config = yaml.safe_load(f) or {}

        gates_config = config.get("approval_gates", [])
        gates = []
        for g in gates_config:
            gates.append(
                ApprovalGate(
                    name=g.get("name", ""),
                    condition=g.get("condition", ""),
                    blocking=g.get("blocking", True),
                    description=g.get("description", ""),
                )
            )
        return gates

    except Exception as exc:
        logger.warning("Failed to load gates from %s: %s", path, exc)
        return []

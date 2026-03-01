"""P2 Evals — Effort Estimation (EFF-01 through EFF-06).

Tests that effort estimates are reasonable, range-bound, and sensitive
to finding complexity.
"""
from __future__ import annotations

import pytest

from context_graph.pm.effort_estimator import EffortEstimator
from context_graph.core.models import (
    SecurityFinding,
    EngineeringFinding,
    ArchitectureFinding,
    EffortEstimation,
    Severity,
    ThreatCategory,
    EngineeringCategory,
    ArchitectureCategory,
)


@pytest.fixture
def estimator() -> EffortEstimator:
    return EffortEstimator()


def _sec_findings(n: int, severity: Severity = Severity.MEDIUM) -> list[SecurityFinding]:
    return [
        SecurityFinding(
            title=f"Finding {i}",
            description=f"Description {i}",
            severity=severity,
            category=ThreatCategory.INJECTION,
            recommendation="Fix it",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# EFF-01: Range accuracy
# ---------------------------------------------------------------------------

class TestEFF01RangeAccuracy:
    def test_range_is_ordered(self, estimator: EffortEstimator):
        findings = _sec_findings(5)
        est = estimator.estimate(findings)
        assert est.total_days["min"] <= est.total_days["likely"] <= est.total_days["max"], (
            f"Range not ordered: {est.total_days}"
        )

    def test_range_positive(self, estimator: EffortEstimator):
        findings = _sec_findings(3)
        est = estimator.estimate(findings)
        assert est.total_days["min"] >= 0
        assert est.total_days["likely"] > 0


# ---------------------------------------------------------------------------
# EFF-02: Central estimate accuracy
# ---------------------------------------------------------------------------

class TestEFF02CentralEstimate:
    def test_likely_between_min_max(self, estimator: EffortEstimator):
        findings = _sec_findings(5)
        est = estimator.estimate(findings)
        assert est.total_days["min"] <= est.total_days["likely"] <= est.total_days["max"]


# ---------------------------------------------------------------------------
# EFF-03: Codebase support accuracy
# ---------------------------------------------------------------------------

class TestEFF03CodebaseSupport:
    def test_codebase_support_percentage(self, estimator: EffortEstimator):
        findings = _sec_findings(3)
        est = estimator.estimate(findings)
        assert 0 <= est.codebase_support <= 100, (
            f"Codebase support {est.codebase_support} not in [0, 100]"
        )


# ---------------------------------------------------------------------------
# EFF-04: Sprint calculation
# ---------------------------------------------------------------------------

class TestEFF04SprintCalculation:
    def test_estimation_has_tldr(self, estimator: EffortEstimator):
        findings = _sec_findings(5)
        est = estimator.estimate(findings)
        assert est.tldr and len(est.tldr) > 0, "Estimation should have a tldr summary"


# ---------------------------------------------------------------------------
# EFF-05: Per-requirement breakdown
# ---------------------------------------------------------------------------

class TestEFF05PerRequirementBreakdown:
    def test_breakdown_count_matches(self, estimator: EffortEstimator):
        findings = _sec_findings(4)
        est = estimator.estimate(findings)
        assert len(est.by_requirement) == 4, (
            f"Expected 4 breakdown items, got {len(est.by_requirement)}"
        )


# ---------------------------------------------------------------------------
# EFF-06: Complexity sensitivity
# ---------------------------------------------------------------------------

class TestEFF06ComplexitySensitivity:
    def test_more_findings_more_effort(self, estimator: EffortEstimator):
        small = estimator.estimate(_sec_findings(2))
        large = estimator.estimate(_sec_findings(10))
        assert large.total_days["likely"] >= small.total_days["likely"], (
            f"10 findings should take >= 2 findings: "
            f"{large.total_days['likely']} vs {small.total_days['likely']}"
        )

    def test_higher_severity_more_effort(self, estimator: EffortEstimator):
        low = estimator.estimate(_sec_findings(3, Severity.LOW))
        critical = estimator.estimate(_sec_findings(3, Severity.CRITICAL))
        assert critical.total_days["likely"] >= low.total_days["likely"], (
            f"Critical findings should take >= low: "
            f"{critical.total_days['likely']} vs {low.total_days['likely']}"
        )

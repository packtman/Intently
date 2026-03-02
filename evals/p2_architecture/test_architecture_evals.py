"""P2 Evals — Architecture Review Findings (ARCH-01 through ARCH-08).

Tests that architecture findings detect pattern violations, coupling,
scalability issues, and API design problems.
"""
from __future__ import annotations

import pytest

from context_graph.core.models import (
    ArchitectureFinding,
    ArchitectureCategory,
    Severity,
)


# ---------------------------------------------------------------------------
# ARCH-01: Architectural pattern recognition
# ---------------------------------------------------------------------------

class TestARCH01PatternRecognition:
    def test_architecture_categories_complete(self):
        assert len(ArchitectureCategory) >= 15, (
            f"Expected >= 15 architecture categories, got {len(ArchitectureCategory)}"
        )


# ---------------------------------------------------------------------------
# ARCH-02: Consistency violation detection
# ---------------------------------------------------------------------------

class TestARCH02ConsistencyViolation:
    def test_api_categories_exist(self):
        assert ArchitectureCategory.INCONSISTENT_API is not None
        assert ArchitectureCategory.BREAKING_CHANGE is not None


# ---------------------------------------------------------------------------
# ARCH-03: Coupling analysis
# ---------------------------------------------------------------------------

class TestARCH03CouplingAnalysis:
    def test_coupling_score_field(self):
        f = ArchitectureFinding(
            title="High coupling",
            description="Service A tightly coupled to Service B",
            severity=Severity.MEDIUM,
            category=ArchitectureCategory.MONOLITH_COUPLING,
            coupling_score=8.5,
            recommendation="Introduce interface boundary",
        )
        assert f.coupling_score == 8.5


# ---------------------------------------------------------------------------
# ARCH-04: Scalability concern detection
# ---------------------------------------------------------------------------

class TestARCH04ScalabilityConcerns:
    def test_scalability_categories(self):
        assert ArchitectureCategory.SINGLE_POINT_OF_FAILURE is not None
        assert ArchitectureCategory.NO_HORIZONTAL_SCALING is not None
        assert ArchitectureCategory.STATEFUL_SERVICE is not None


# ---------------------------------------------------------------------------
# ARCH-05: API design quality
# ---------------------------------------------------------------------------

class TestARCH05APIDesign:
    def test_api_versioning_category(self):
        assert ArchitectureCategory.NO_API_VERSIONING is not None

    def test_api_contract_category(self):
        assert ArchitectureCategory.MISSING_API_CONTRACT is not None


# ---------------------------------------------------------------------------
# ARCH-06: Data model fitness
# ---------------------------------------------------------------------------

class TestARCH06DataModelFitness:
    def test_data_categories(self):
        assert ArchitectureCategory.MISSING_DATA_MODEL is not None
        assert ArchitectureCategory.DATA_INCONSISTENCY is not None
        assert ArchitectureCategory.SCHEMA_DRIFT is not None


# ---------------------------------------------------------------------------
# ARCH-07: Service boundary analysis
# ---------------------------------------------------------------------------

class TestARCH07ServiceBoundary:
    def test_boundary_categories(self):
        assert ArchitectureCategory.MISSING_SERVICE_BOUNDARY is not None
        assert ArchitectureCategory.DISTRIBUTED_MONOLITH is not None


# ---------------------------------------------------------------------------
# ARCH-08: Migration risk assessment
# ---------------------------------------------------------------------------

class TestARCH08MigrationRisk:
    def test_finding_fields(self):
        f = ArchitectureFinding(
            title="Breaking API change",
            description="V2 removes required field",
            severity=Severity.HIGH,
            category=ArchitectureCategory.BREAKING_CHANGE,
            breaking_change=True,
            design_alternatives=["Add field as optional", "Version the API"],
            recommendation="Add API versioning",
        )
        assert f.breaking_change is True
        assert len(f.design_alternatives) == 2

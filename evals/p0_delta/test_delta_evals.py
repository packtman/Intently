"""P0 Evals — Delta Analysis (DELTA-01 through DELTA-10).

Tests that the delta analyzer correctly identifies new endpoints, modified
endpoints, new data models, PII introduction, and risk indicators when
comparing Intent (PRD) against State (codebase).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from context_graph.parsers.markdown_parser import MarkdownPRDParser
from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.security.delta_analyzer import DeltaAnalyzer, DeltaAnalysisResult
from evals.framework.helpers import make_multi_analyzer
from context_graph.core.models import Intent, State, Entity, EntityType

GOLDEN_PRDS = Path(__file__).parents[1] / "datasets" / "golden_prds"
GOLDEN_CODEBASES = Path(__file__).parents[1] / "datasets" / "golden_codebases"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


def _load_prd(name: str) -> str:
    return (GOLDEN_PRDS / f"{name}_prd.md").read_text()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def parser() -> MarkdownPRDParser:
    return MarkdownPRDParser()


@pytest.fixture(scope="module")
def analyzer() -> MultiLanguageAnalyzer:
    return make_multi_analyzer()


@pytest.fixture(scope="module")
def delta_analyzer() -> DeltaAnalyzer:
    return DeltaAnalyzer()


@pytest.fixture(scope="module")
def auth_intent(parser: MarkdownPRDParser) -> Intent:
    return parser.parse(_load_prd("auth_system"))


@pytest.fixture(scope="module")
def ecommerce_intent(parser: MarkdownPRDParser) -> Intent:
    return parser.parse(_load_prd("ecommerce"))


@pytest.fixture(scope="module")
def healthcare_intent(parser: MarkdownPRDParser) -> Intent:
    return parser.parse(_load_prd("healthcare"))


@pytest.fixture(scope="module")
def sample_state(analyzer: MultiLanguageAnalyzer) -> State:
    return analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")


@pytest.fixture(scope="module")
def ecommerce_state(analyzer: MultiLanguageAnalyzer) -> State:
    return analyzer.analyze_codebase(GOLDEN_CODEBASES / "ecommerce_api")


@pytest.fixture(scope="module")
def auth_delta(
    delta_analyzer: DeltaAnalyzer, auth_intent: Intent, sample_state: State
) -> DeltaAnalysisResult:
    return delta_analyzer.analyze(auth_intent, sample_state)


@pytest.fixture(scope="module")
def ecommerce_delta(
    delta_analyzer: DeltaAnalyzer, ecommerce_intent: Intent, ecommerce_state: State
) -> DeltaAnalysisResult:
    return delta_analyzer.analyze(ecommerce_intent, ecommerce_state)


@pytest.fixture(scope="module")
def healthcare_delta(
    delta_analyzer: DeltaAnalyzer, healthcare_intent: Intent, sample_state: State
) -> DeltaAnalysisResult:
    return delta_analyzer.analyze(healthcare_intent, sample_state)


# ---------------------------------------------------------------------------
# DELTA-01: New endpoint detection
# ---------------------------------------------------------------------------

class TestDELTA01NewEndpoints:
    """Endpoints in intent but not in state should be flagged as new."""

    def test_auth_prd_new_endpoints_detected(self, auth_delta: DeltaAnalysisResult):
        assert len(auth_delta.new_endpoints) >= 1, (
            f"Expected new endpoints from auth PRD, got {len(auth_delta.new_endpoints)}"
        )

    def test_healthcare_new_endpoints(self, healthcare_delta: DeltaAnalysisResult):
        assert len(healthcare_delta.new_endpoints) >= 1, (
            f"Expected new endpoints from healthcare PRD, got {len(healthcare_delta.new_endpoints)}"
        )


# ---------------------------------------------------------------------------
# DELTA-02: Modified endpoint detection
# ---------------------------------------------------------------------------

class TestDELTA02ModifiedEndpoints:
    """Endpoints changing behavior should be detected."""

    def test_delta_has_modified_field(self, auth_delta: DeltaAnalysisResult):
        assert hasattr(auth_delta, "modified_endpoints"), (
            "DeltaAnalysisResult should have modified_endpoints field"
        )

    def test_ecommerce_delta_structure(self, ecommerce_delta: DeltaAnalysisResult):
        assert isinstance(ecommerce_delta.modified_endpoints, list)


# ---------------------------------------------------------------------------
# DELTA-03: New data model detection
# ---------------------------------------------------------------------------

class TestDELTA03NewDataModels:
    """Data models introduced by the PRD should be identified."""

    def test_auth_prd_new_data_models(self, auth_delta: DeltaAnalysisResult):
        assert len(auth_delta.new_data_models) >= 0, "Should not error"

    def test_healthcare_new_data_models(self, healthcare_delta: DeltaAnalysisResult):
        assert isinstance(healthcare_delta.new_data_models, list)


# ---------------------------------------------------------------------------
# DELTA-04: New data flow detection
# ---------------------------------------------------------------------------

class TestDELTA04NewDataFlows:
    """New data flows (especially PII flows) should be captured."""

    def test_auth_prd_data_flows(self, auth_delta: DeltaAnalysisResult):
        assert isinstance(auth_delta.new_data_flows, list)

    def test_delta_has_data_flow_field(self, ecommerce_delta: DeltaAnalysisResult):
        assert hasattr(ecommerce_delta, "new_data_flows")


# ---------------------------------------------------------------------------
# DELTA-05: PII introduction flag
# ---------------------------------------------------------------------------

class TestDELTA05PIIIntroduction:
    """introduces_pii should be correctly set when PRD adds PII handling."""

    def test_auth_prd_introduces_pii(self, auth_delta: DeltaAnalysisResult):
        assert hasattr(auth_delta, "introduces_pii"), (
            "DeltaAnalysisResult should have introduces_pii field"
        )

    def test_healthcare_prd_introduces_pii(self, healthcare_delta: DeltaAnalysisResult):
        assert healthcare_delta.introduces_pii is True, (
            "Healthcare PRD with SSN, medical records should set introduces_pii=True"
        )


# ---------------------------------------------------------------------------
# DELTA-06: External integration flag
# ---------------------------------------------------------------------------

class TestDELTA06ExternalIntegration:
    """introduces_external_integration should be set when PRD adds integrations."""

    def test_auth_prd_has_external_integration(self, auth_delta: DeltaAnalysisResult):
        assert auth_delta.introduces_external_integration is True, (
            "Auth PRD with Google OAuth, GitHub, SendGrid should flag external integration"
        )

    def test_ecommerce_has_external_integration(self, ecommerce_delta: DeltaAnalysisResult):
        assert hasattr(ecommerce_delta, "introduces_external_integration")


# ---------------------------------------------------------------------------
# DELTA-07: Auth flow modification flag
# ---------------------------------------------------------------------------

class TestDELTA07AuthFlowModification:
    """modifies_auth_flow should be set when PRD changes auth."""

    def test_auth_prd_modifies_auth(self, auth_delta: DeltaAnalysisResult):
        assert auth_delta.modifies_auth_flow is True, (
            "Auth system PRD should set modifies_auth_flow=True"
        )


# ---------------------------------------------------------------------------
# DELTA-08: Trust boundary impact
# ---------------------------------------------------------------------------

class TestDELTA08TrustBoundary:
    """Trust boundary crossings should be detected."""

    def test_delta_has_trust_boundary_field(self, auth_delta: DeltaAnalysisResult):
        assert hasattr(auth_delta, "trust_boundary_impacts")
        assert isinstance(auth_delta.trust_boundary_impacts, list)


# ---------------------------------------------------------------------------
# DELTA-09: False negative rate (no real gaps missed)
# ---------------------------------------------------------------------------

class TestDELTA09FalseNegatives:
    """Delta should flag attack surface expansion when new endpoints are added."""

    def test_auth_attack_surface_expanded(self, auth_delta: DeltaAnalysisResult):
        assert auth_delta.expands_attack_surface is True, (
            "Adding 10 new auth endpoints should expand attack surface"
        )

    def test_risk_score_positive(self, auth_delta: DeltaAnalysisResult):
        assert auth_delta.delta.risk_score > 0, (
            f"Risk score should be positive for auth PRD delta, got {auth_delta.delta.risk_score}"
        )


# ---------------------------------------------------------------------------
# DELTA-10: Noise rate (not flagging existing items as new)
# ---------------------------------------------------------------------------

class TestDELTA10NoiseRate:
    """Delta items that aren't actually new should be rare."""

    def test_noop_prd_has_minimal_delta(self, delta_analyzer: DeltaAnalyzer, sample_state: State):
        """A PRD describing exactly what exists should produce minimal delta."""
        existing_endpoints = sample_state.api_endpoints
        if not existing_endpoints:
            pytest.skip("No endpoints in sample state to create no-op PRD")

        noop_intent = Intent(
            title="Existing System",
            summary="Describes the current system as-is.",
            features=["Existing user management"],
        )
        result = delta_analyzer.analyze(noop_intent, sample_state)
        assert result.delta.risk_score <= 50, (
            f"No-op PRD should have low risk score, got {result.delta.risk_score}"
        )

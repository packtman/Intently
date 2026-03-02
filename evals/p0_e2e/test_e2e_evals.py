"""P0 Evals — End-to-End Pipeline (E2E-01 and more).

Tests the full review pipeline from PRD input through to final report,
without requiring LLM API keys (uses pattern-based analysis only).
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from context_graph.parsers.markdown_parser import MarkdownPRDParser
from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.security.delta_analyzer import DeltaAnalyzer
from evals.framework.helpers import make_multi_analyzer
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
from context_graph.security.compliance_analyzer import CompliancePatternMatcher
from context_graph.core.models import (
    Intent,
    State,
    Severity,
    ReviewDimension,
    ComplianceFramework,
)

GOLDEN_PRDS = Path(__file__).parents[1] / "datasets" / "golden_prds"
GOLDEN_CODEBASES = Path(__file__).parents[1] / "datasets" / "golden_codebases"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


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
def threat_matcher() -> ThreatPatternMatcher:
    return ThreatPatternMatcher()


@pytest.fixture(scope="module")
def privacy_matcher() -> PrivacyPatternMatcher:
    return PrivacyPatternMatcher()


@pytest.fixture(scope="module")
def compliance_matcher() -> CompliancePatternMatcher:
    return CompliancePatternMatcher()


# ---------------------------------------------------------------------------
# E2E-01: Review completion rate
# ---------------------------------------------------------------------------

class TestE2E01ReviewCompletion:
    """Reviews should complete without errors for valid inputs."""

    def test_auth_prd_full_pipeline(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
        privacy_matcher: PrivacyPatternMatcher,
        compliance_matcher: CompliancePatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        delta = delta_analyzer.analyze(intent, state)

        security_findings = threat_matcher.match(delta)
        privacy_findings = privacy_matcher.match(delta)
        compliance_findings = compliance_matcher.match(delta)

        all_findings = (
            len(security_findings) + len(privacy_findings) + len(compliance_findings)
        )
        assert all_findings >= 1, (
            f"Full pipeline should produce >= 1 finding, got {all_findings}"
        )

    def test_ecommerce_prd_full_pipeline(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
        privacy_matcher: PrivacyPatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "ecommerce_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(GOLDEN_CODEBASES / "ecommerce_api")
        delta = delta_analyzer.analyze(intent, state)

        security_findings = threat_matcher.match(delta)
        privacy_findings = privacy_matcher.match(delta)

        total = len(security_findings) + len(privacy_findings)
        assert total >= 1, f"E-commerce pipeline should produce >= 1 finding"

    def test_healthcare_prd_full_pipeline(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
        privacy_matcher: PrivacyPatternMatcher,
        compliance_matcher: CompliancePatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "healthcare_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(GOLDEN_CODEBASES / "healthcare_app")
        delta = delta_analyzer.analyze(intent, state)

        security_findings = threat_matcher.match(delta)
        privacy_findings = privacy_matcher.match(delta)
        compliance_findings = compliance_matcher.match(delta)

        total = (
            len(security_findings) + len(privacy_findings) + len(compliance_findings)
        )
        assert total >= 1, (
            f"Healthcare pipeline should produce >= 1 finding, got {total}"
        )


# ---------------------------------------------------------------------------
# E2E-02: Report quality
# ---------------------------------------------------------------------------

class TestE2E02ReportQuality:
    """Final report should be comprehensive."""

    def test_findings_have_required_fields(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        delta = delta_analyzer.analyze(intent, state)
        findings = threat_matcher.match(delta)

        for f in findings:
            assert f.title, "Finding must have title"
            assert f.description, "Finding must have description"
            assert f.severity, "Finding must have severity"
            assert f.recommendation, "Finding must have recommendation"


# ---------------------------------------------------------------------------
# E2E-04: Finding count reasonableness
# ---------------------------------------------------------------------------

class TestE2E04FindingCountReasonableness:
    """Finding count should be in expected range (not 0 and not 500)."""

    def test_auth_finding_count_reasonable(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        delta = delta_analyzer.analyze(intent, state)
        findings = threat_matcher.match(delta)

        assert 1 <= len(findings) <= 200, (
            f"Finding count {len(findings)} outside reasonable range [1, 200]"
        )


# ---------------------------------------------------------------------------
# E2E-05: Dimension coverage
# ---------------------------------------------------------------------------

class TestE2E05DimensionCoverage:
    """All requested dimensions should have findings in the report."""

    def test_multi_dimension_coverage(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
        privacy_matcher: PrivacyPatternMatcher,
        compliance_matcher: CompliancePatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "healthcare_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(GOLDEN_CODEBASES / "healthcare_app")
        delta = delta_analyzer.analyze(intent, state)

        security = threat_matcher.match(delta)
        privacy = privacy_matcher.match(delta)
        compliance = compliance_matcher.match(delta)

        dimensions_with_findings = 0
        if security:
            dimensions_with_findings += 1
        if privacy:
            dimensions_with_findings += 1
        if compliance:
            dimensions_with_findings += 1

        assert dimensions_with_findings >= 2, (
            f"Healthcare PRD should produce findings in >= 2 dimensions, "
            f"got {dimensions_with_findings} (sec={len(security)}, "
            f"priv={len(privacy)}, comp={len(compliance)})"
        )


# ---------------------------------------------------------------------------
# E2E-08: Idempotency
# ---------------------------------------------------------------------------

class TestE2E08Idempotency:
    """Same PRD + codebase should produce consistent results."""

    def test_deterministic_results(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()

        results = []
        for _ in range(2):
            intent = parser.parse(prd)
            state = analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
            delta = delta_analyzer.analyze(intent, state)
            findings = threat_matcher.match(delta)
            results.append(set(f.title for f in findings))

        assert results[0] == results[1], (
            f"Results differ between runs: {results[0] ^ results[1]}"
        )


# ---------------------------------------------------------------------------
# E2E-09: Error recovery
# ---------------------------------------------------------------------------

class TestE2E09ErrorRecovery:
    """Pipeline should handle edge cases gracefully."""

    def test_empty_prd(self, parser: MarkdownPRDParser):
        intent = parser.parse("")
        assert intent is not None, "Empty PRD should return an Intent (possibly empty)"

    def test_empty_codebase(self, analyzer: MultiLanguageAnalyzer, tmp_path: Path):
        empty_dir = tmp_path / "empty_codebase"
        empty_dir.mkdir()
        state = analyzer.analyze_codebase(empty_dir)
        assert state is not None, "Empty codebase should return a State"
        assert state.files_analyzed == 0

    def test_pipeline_with_empty_state(
        self,
        parser: MarkdownPRDParser,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
    ):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        intent = parser.parse(prd)
        empty_state = State()
        delta = delta_analyzer.analyze(intent, empty_state)
        findings = threat_matcher.match(delta)
        assert isinstance(findings, list), "Should return a list even with empty state"


# ---------------------------------------------------------------------------
# E2E-10: Performance
# ---------------------------------------------------------------------------

class TestE2E10Performance:
    """Pipeline latency should be reasonable."""

    def test_full_pipeline_under_30s(
        self,
        parser: MarkdownPRDParser,
        analyzer: MultiLanguageAnalyzer,
        delta_analyzer: DeltaAnalyzer,
        threat_matcher: ThreatPatternMatcher,
    ):
        start = time.time()
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        intent = parser.parse(prd)
        state = analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        delta = delta_analyzer.analyze(intent, state)
        findings = threat_matcher.match(delta)
        elapsed = time.time() - start

        assert elapsed < 30.0, (
            f"Full pipeline took {elapsed:.1f}s — exceeds 30s threshold"
        )

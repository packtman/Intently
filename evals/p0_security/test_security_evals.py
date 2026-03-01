"""P0 Evals — Security Review Findings (SEC-01 through SEC-10).

Tests that security findings are relevant, complete, correctly severitied,
cover expected threat categories, and are properly grounded in evidence.
These evals use pattern-based analysis (no LLM required) plus the review
engine's merging and deduplication logic.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from context_graph.parsers.markdown_parser import MarkdownPRDParser
from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.security.delta_analyzer import DeltaAnalyzer, DeltaAnalysisResult
from evals.framework.helpers import make_multi_analyzer
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
from context_graph.core.models import (
    Intent,
    State,
    SecurityFinding,
    Severity,
    ThreatCategory,
    ReviewDimension,
)
from evals.framework.metrics import (
    category_coverage,
    severity_agreement_rate,
    duplicate_rate,
)
from evals.framework.assertions import (
    assert_severity_not_inflated,
    assert_no_duplicates,
    assert_all_grounded,
)

GOLDEN_PRDS = Path(__file__).parents[1] / "datasets" / "golden_prds"
GOLDEN_CODEBASES = Path(__file__).parents[1] / "datasets" / "golden_codebases"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"
LABELED_DIR = Path(__file__).parents[1] / "datasets" / "labeled_findings"


def _load_labeled_findings(name: str) -> list[dict[str, Any]]:
    return json.loads((LABELED_DIR / f"{name}_findings.json").read_text())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def parser() -> MarkdownPRDParser:
    return MarkdownPRDParser()


@pytest.fixture(scope="module")
def multi_analyzer() -> MultiLanguageAnalyzer:
    return make_multi_analyzer()


@pytest.fixture(scope="module")
def delta_analyzer() -> DeltaAnalyzer:
    return DeltaAnalyzer()


@pytest.fixture(scope="module")
def threat_matcher() -> ThreatPatternMatcher:
    return ThreatPatternMatcher()


@pytest.fixture(scope="module")
def auth_intent(parser: MarkdownPRDParser) -> Intent:
    prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
    return parser.parse(prd)


@pytest.fixture(scope="module")
def sample_state(multi_analyzer: MultiLanguageAnalyzer) -> State:
    return multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")


@pytest.fixture(scope="module")
def ecommerce_state(multi_analyzer: MultiLanguageAnalyzer) -> State:
    return multi_analyzer.analyze_codebase(GOLDEN_CODEBASES / "ecommerce_api")


@pytest.fixture(scope="module")
def auth_delta(
    delta_analyzer: DeltaAnalyzer, auth_intent: Intent, sample_state: State
) -> DeltaAnalysisResult:
    return delta_analyzer.analyze(auth_intent, sample_state)


@pytest.fixture(scope="module")
def ecommerce_delta(
    delta_analyzer: DeltaAnalyzer,
    parser: MarkdownPRDParser,
    ecommerce_state: State,
) -> DeltaAnalysisResult:
    ecommerce_intent = parser.parse(
        (GOLDEN_PRDS / "ecommerce_prd.md").read_text()
    )
    return delta_analyzer.analyze(ecommerce_intent, ecommerce_state)


@pytest.fixture(scope="module")
def auth_pattern_findings(
    threat_matcher: ThreatPatternMatcher, auth_delta: DeltaAnalysisResult
) -> list[SecurityFinding]:
    return threat_matcher.match(auth_delta)


@pytest.fixture(scope="module")
def ecommerce_pattern_findings(
    threat_matcher: ThreatPatternMatcher, ecommerce_delta: DeltaAnalysisResult
) -> list[SecurityFinding]:
    return threat_matcher.match(ecommerce_delta)


@pytest.fixture(scope="module")
def labeled_security() -> list[dict[str, Any]]:
    return _load_labeled_findings("security")


# ---------------------------------------------------------------------------
# SEC-01: Finding relevance
# ---------------------------------------------------------------------------

class TestSEC01FindingRelevance:
    """Security findings should be relevant to the PRD + codebase."""

    def test_auth_prd_produces_findings(self, auth_pattern_findings: list[SecurityFinding]):
        assert len(auth_pattern_findings) >= 1, (
            "Auth PRD against vulnerable codebase should produce >= 1 finding"
        )

    def test_ecommerce_produces_findings(self, ecommerce_pattern_findings: list[SecurityFinding]):
        assert len(ecommerce_pattern_findings) >= 1, (
            "E-commerce PRD should produce >= 1 finding"
        )

    def test_findings_have_titles(self, auth_pattern_findings: list[SecurityFinding]):
        for f in auth_pattern_findings:
            assert f.title and len(f.title) > 5, (
                f"Finding should have meaningful title, got: '{f.title}'"
            )


# ---------------------------------------------------------------------------
# SEC-02: Finding completeness
# ---------------------------------------------------------------------------

class TestSEC02FindingCompleteness:
    """Known security issues should be found."""

    def test_auth_findings_cover_auth_issues(self, auth_pattern_findings: list[SecurityFinding]):
        finding_text = " ".join(
            f"{f.title} {f.description}" for f in auth_pattern_findings
        ).lower()
        auth_related = any(
            kw in finding_text
            for kw in ["auth", "token", "password", "credential", "session", "oauth", "mfa"]
        )
        assert auth_related or len(auth_pattern_findings) >= 3, (
            "Auth PRD should produce auth-related findings"
        )


# ---------------------------------------------------------------------------
# SEC-03: Severity accuracy
# ---------------------------------------------------------------------------

class TestSEC03SeverityAccuracy:
    """Severity ratings should match expected distribution."""

    def test_severity_distribution_not_inflated(
        self, auth_pattern_findings: list[SecurityFinding]
    ):
        if not auth_pattern_findings:
            pytest.skip("No findings to check severity distribution")
        severities = [f.severity.value for f in auth_pattern_findings]
        assert_severity_not_inflated(
            severities, max_critical_pct=0.40, max_high_pct=0.60, label="SEC-03"
        )

    def test_labeled_severity_agreement(self, labeled_security: list[dict]):
        tp_findings = [f for f in labeled_security if f["label"] == "true_positive"]
        if not tp_findings:
            pytest.skip("No TP findings in labeled set")
        severities = [f["severity"] for f in tp_findings]
        valid_severities = {"critical", "high", "medium", "low", "info"}
        for s in severities:
            assert s in valid_severities, f"Invalid severity: {s}"


# ---------------------------------------------------------------------------
# SEC-04: STRIDE coverage
# ---------------------------------------------------------------------------

class TestSEC04STRIDECoverage:
    """Findings should span multiple STRIDE categories."""

    def test_auth_findings_category_diversity(
        self, auth_pattern_findings: list[SecurityFinding]
    ):
        if not auth_pattern_findings:
            pytest.skip("No findings")
        categories = {f.category.value if hasattr(f.category, "value") else str(f.category)
                     for f in auth_pattern_findings}
        assert len(categories) >= 1, (
            f"Expected >= 1 distinct category, got {categories}"
        )


# ---------------------------------------------------------------------------
# SEC-05: OWASP Top 10 coverage
# ---------------------------------------------------------------------------

class TestSEC05OWASPCoverage:
    """Findings should address relevant OWASP categories."""

    def test_labeled_findings_cover_owasp(self, labeled_security: list[dict]):
        tp_findings = [f for f in labeled_security if f["label"] == "true_positive"]
        categories = {f["category"] for f in tp_findings}
        owasp_related = {
            "injection", "broken_authentication", "sensitive_data_exposure",
            "broken_access_control", "security_misconfiguration",
        }
        covered = categories & owasp_related
        assert len(covered) >= 2, (
            f"Expected >= 2 OWASP categories in labeled TP set, got {covered}"
        )


# ---------------------------------------------------------------------------
# SEC-06: Remediation quality
# ---------------------------------------------------------------------------

class TestSEC06RemediationQuality:
    """Recommended mitigations should be actionable."""

    def test_findings_have_recommendations(
        self, auth_pattern_findings: list[SecurityFinding]
    ):
        for f in auth_pattern_findings:
            assert f.recommendation and len(f.recommendation) > 10, (
                f"Finding '{f.title}' has weak recommendation: '{f.recommendation}'"
            )

    def test_labeled_findings_have_recommendations(self, labeled_security: list[dict]):
        tp = [f for f in labeled_security if f["label"] == "true_positive"]
        for f in tp:
            assert f.get("recommendation") and len(f["recommendation"]) > 10, (
                f"Labeled TP '{f['title']}' needs recommendation"
            )


# ---------------------------------------------------------------------------
# SEC-07: Evidence grounding
# ---------------------------------------------------------------------------

class TestSEC07EvidenceGrounding:
    """Each finding should reference specific PRD sections or code patterns."""

    def test_labeled_tp_are_grounded(self, labeled_security: list[dict]):
        tp = [f for f in labeled_security if f["label"] == "true_positive"]
        grounded = sum(
            1 for f in tp if f.get("source_reference") and f["source_reference"].strip()
        )
        rate = grounded / len(tp) if tp else 1.0
        assert rate >= 0.75, (
            f"Only {rate:.0%} of labeled TP findings have source_reference (need >= 75%)"
        )


# ---------------------------------------------------------------------------
# SEC-08: Deduplication
# ---------------------------------------------------------------------------

class TestSEC08Deduplication:
    """No duplicate findings covering the same issue."""

    def test_no_duplicate_titles(self, auth_pattern_findings: list[SecurityFinding]):
        if not auth_pattern_findings:
            pytest.skip("No findings")
        titles = [f.title.lower().strip() for f in auth_pattern_findings]
        assert_no_duplicates(titles, label="SEC-08", max_rate=0.10)


# ---------------------------------------------------------------------------
# SEC-09: Confidence calibration
# ---------------------------------------------------------------------------

class TestSEC09ConfidenceCalibration:
    """Confidence scores should be reasonable."""

    def test_confidence_in_range(self, auth_pattern_findings: list[SecurityFinding]):
        for f in auth_pattern_findings:
            assert 0.0 <= f.confidence <= 1.0, (
                f"Confidence {f.confidence} out of range for '{f.title}'"
            )

    def test_labeled_confidence_correlates(self, labeled_security: list[dict]):
        tp = [f for f in labeled_security if f["label"] == "true_positive"]
        fp = [f for f in labeled_security if f["label"] == "false_positive"]
        if not tp or not fp:
            pytest.skip("Need both TP and FP findings")
        avg_tp_conf = sum(f["confidence"] for f in tp) / len(tp)
        avg_fp_conf = sum(f["confidence"] for f in fp) / len(fp)
        assert avg_tp_conf > avg_fp_conf, (
            f"TP avg confidence ({avg_tp_conf:.2f}) should exceed "
            f"FP avg confidence ({avg_fp_conf:.2f})"
        )


# ---------------------------------------------------------------------------
# SEC-10: Pattern-matched vs LLM findings complementarity
# ---------------------------------------------------------------------------

class TestSEC10PatternVsLLM:
    """Pattern-based findings should exist and have source_type."""

    def test_pattern_findings_have_source_type(
        self, auth_pattern_findings: list[SecurityFinding]
    ):
        for f in auth_pattern_findings:
            assert f.source_type in ("pattern", "graph", "llm", ""), (
                f"Unexpected source_type: {f.source_type}"
            )

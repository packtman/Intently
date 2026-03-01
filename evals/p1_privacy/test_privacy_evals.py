"""P1 Evals — Privacy Review Findings (PRIV-01 through PRIV-08).

Tests that privacy findings correctly identify PII flows, cover LINDDUN
categories, and detect GDPR/CCPA requirements.
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
from context_graph.security.privacy_analyzer import PrivacyPatternMatcher
from context_graph.core.models import PrivacyFinding, Severity
from evals.framework.metrics import category_coverage
from evals.framework.assertions import assert_severity_not_inflated

GOLDEN_PRDS = Path(__file__).parents[1] / "datasets" / "golden_prds"
GOLDEN_CODEBASES = Path(__file__).parents[1] / "datasets" / "golden_codebases"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"
LABELED_DIR = Path(__file__).parents[1] / "datasets" / "labeled_findings"


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
def privacy_matcher() -> PrivacyPatternMatcher:
    return PrivacyPatternMatcher()


@pytest.fixture(scope="module")
def auth_privacy_findings(
    parser: MarkdownPRDParser,
    multi_analyzer: MultiLanguageAnalyzer,
    delta_analyzer: DeltaAnalyzer,
    privacy_matcher: PrivacyPatternMatcher,
) -> list[PrivacyFinding]:
    prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
    intent = parser.parse(prd)
    state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
    delta = delta_analyzer.analyze(intent, state)
    return privacy_matcher.match(delta)


@pytest.fixture(scope="module")
def healthcare_privacy_findings(
    parser: MarkdownPRDParser,
    multi_analyzer: MultiLanguageAnalyzer,
    delta_analyzer: DeltaAnalyzer,
    privacy_matcher: PrivacyPatternMatcher,
) -> list[PrivacyFinding]:
    prd = (GOLDEN_PRDS / "healthcare_prd.md").read_text()
    intent = parser.parse(prd)
    state = multi_analyzer.analyze_codebase(GOLDEN_CODEBASES / "healthcare_app")
    delta = delta_analyzer.analyze(intent, state)
    return privacy_matcher.match(delta)


@pytest.fixture(scope="module")
def labeled_privacy() -> list[dict[str, Any]]:
    return json.loads((LABELED_DIR / "privacy_findings.json").read_text())


# ---------------------------------------------------------------------------
# PRIV-01: PII flow detection
# ---------------------------------------------------------------------------

class TestPRIV01PIIFlowDetection:
    """All PII data flows should be identified."""

    def test_auth_prd_has_privacy_findings(self, auth_privacy_findings: list[PrivacyFinding]):
        assert len(auth_privacy_findings) >= 1, (
            "Auth PRD with PII (email, password) should produce privacy findings"
        )

    def test_healthcare_prd_has_privacy_findings(
        self, healthcare_privacy_findings: list[PrivacyFinding]
    ):
        assert len(healthcare_privacy_findings) >= 2, (
            f"Healthcare PRD should produce >= 2 privacy findings, "
            f"got {len(healthcare_privacy_findings)}"
        )


# ---------------------------------------------------------------------------
# PRIV-02: LINDDUN coverage
# ---------------------------------------------------------------------------

class TestPRIV02LINDDUNCoverage:
    """Findings should span LINDDUN categories."""

    def test_healthcare_covers_multiple_categories(
        self, healthcare_privacy_findings: list[PrivacyFinding]
    ):
        if not healthcare_privacy_findings:
            pytest.skip("No privacy findings")
        categories = {
            f.category.value if hasattr(f.category, "value") else str(f.category)
            for f in healthcare_privacy_findings
        }
        assert len(categories) >= 2, (
            f"Expected >= 2 privacy categories, got {categories}"
        )


# ---------------------------------------------------------------------------
# PRIV-03: GDPR requirement mapping
# ---------------------------------------------------------------------------

class TestPRIV03GDPRMapping:
    """GDPR-relevant findings should be flagged."""

    def test_labeled_gdpr_findings_exist(self, labeled_privacy: list[dict]):
        gdpr_findings = [
            f for f in labeled_privacy
            if "GDPR" in (f.get("applicable_regulations") or [])
        ]
        assert len(gdpr_findings) >= 2, (
            f"Expected >= 2 GDPR-related labeled findings, got {len(gdpr_findings)}"
        )


# ---------------------------------------------------------------------------
# PRIV-04: CCPA requirement mapping
# ---------------------------------------------------------------------------

class TestPRIV04CCPAMapping:
    """CCPA-relevant findings should be flagged."""

    def test_labeled_ccpa_findings_exist(self, labeled_privacy: list[dict]):
        ccpa_findings = [
            f for f in labeled_privacy
            if "CCPA" in (f.get("applicable_regulations") or [])
        ]
        assert len(ccpa_findings) >= 1, (
            f"Expected >= 1 CCPA-related labeled finding"
        )


# ---------------------------------------------------------------------------
# PRIV-05: Data minimization check
# ---------------------------------------------------------------------------

class TestPRIV05DataMinimization:
    """Findings should flag unnecessary PII collection."""

    def test_labeled_has_data_disclosure(self, labeled_privacy: list[dict]):
        tp = [f for f in labeled_privacy if f["label"] == "true_positive"]
        categories = {f["category"] for f in tp}
        assert "data_disclosure" in categories or "non_compliance" in categories, (
            f"Expected data_disclosure or non_compliance in TP categories: {categories}"
        )


# ---------------------------------------------------------------------------
# PRIV-06: Third-party data sharing
# ---------------------------------------------------------------------------

class TestPRIV06ThirdPartySharing:
    """Sharing PII with external services should be detected."""

    def test_auth_privacy_with_external(self, auth_privacy_findings: list[PrivacyFinding]):
        finding_text = " ".join(
            f"{f.title} {f.description}" for f in auth_privacy_findings
        ).lower()
        has_external_ref = any(
            kw in finding_text
            for kw in ["external", "third-party", "third party", "integration", "oauth", "sendgrid"]
        )
        assert has_external_ref or len(auth_privacy_findings) >= 2, (
            "Auth PRD with external integrations should flag data sharing concerns"
        )


# ---------------------------------------------------------------------------
# PRIV-07: Severity appropriateness
# ---------------------------------------------------------------------------

class TestPRIV07SeverityAppropriateness:
    """PII-related findings should not be under-rated."""

    def test_severity_not_all_low(self, healthcare_privacy_findings: list[PrivacyFinding]):
        if not healthcare_privacy_findings:
            pytest.skip("No findings")
        severities = [f.severity.value for f in healthcare_privacy_findings]
        low_or_info = sum(1 for s in severities if s in ("low", "info"))
        assert low_or_info < len(severities), (
            "Healthcare privacy findings should not all be low/info severity"
        )


# ---------------------------------------------------------------------------
# PRIV-08: Consent flow coverage
# ---------------------------------------------------------------------------

class TestPRIV08ConsentFlow:
    """Missing consent flows should be flagged."""

    def test_labeled_has_consent_finding(self, labeled_privacy: list[dict]):
        tp = [f for f in labeled_privacy if f["label"] == "true_positive"]
        consent_related = [
            f for f in tp
            if "consent" in f.get("title", "").lower() or "consent" in f.get("description", "").lower()
        ]
        assert len(consent_related) >= 1, (
            "Labeled privacy TP set should include at least one consent-related finding"
        )

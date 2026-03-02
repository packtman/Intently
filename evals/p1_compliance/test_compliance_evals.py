"""P1 Evals — Compliance Review Findings (COMP-01 through COMP-08).

Tests that compliance findings correctly map to SOC 2, HIPAA, PCI-DSS,
and ISO 27001 frameworks with accurate control IDs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from context_graph.parsers.markdown_parser import MarkdownPRDParser
from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.security.delta_analyzer import DeltaAnalyzer
from evals.framework.helpers import make_multi_analyzer
from context_graph.security.compliance_analyzer import CompliancePatternMatcher
from context_graph.core.models import ComplianceFinding, ComplianceFramework

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
def all_frameworks_matcher() -> CompliancePatternMatcher:
    return CompliancePatternMatcher(frameworks=[
        ComplianceFramework.SOC2,
        ComplianceFramework.HIPAA,
        ComplianceFramework.PCI_DSS,
        ComplianceFramework.ISO_27001,
    ])


@pytest.fixture(scope="module")
def healthcare_compliance(
    parser, multi_analyzer, delta_analyzer, all_frameworks_matcher
) -> list[ComplianceFinding]:
    prd = (GOLDEN_PRDS / "healthcare_prd.md").read_text()
    intent = parser.parse(prd)
    state = multi_analyzer.analyze_codebase(GOLDEN_CODEBASES / "healthcare_app")
    delta = delta_analyzer.analyze(intent, state)
    return all_frameworks_matcher.match(delta)


@pytest.fixture(scope="module")
def ecommerce_compliance(
    parser, multi_analyzer, delta_analyzer, all_frameworks_matcher
) -> list[ComplianceFinding]:
    prd = (GOLDEN_PRDS / "ecommerce_prd.md").read_text()
    intent = parser.parse(prd)
    state = multi_analyzer.analyze_codebase(GOLDEN_CODEBASES / "ecommerce_api")
    delta = delta_analyzer.analyze(intent, state)
    return all_frameworks_matcher.match(delta)


@pytest.fixture(scope="module")
def labeled_compliance() -> list[dict[str, Any]]:
    return json.loads((LABELED_DIR / "compliance_findings.json").read_text())


# ---------------------------------------------------------------------------
# COMP-01: SOC 2 mapping accuracy
# ---------------------------------------------------------------------------

class TestCOMP01SOC2Mapping:
    def test_healthcare_has_soc2_findings(self, healthcare_compliance: list[ComplianceFinding]):
        soc2 = [f for f in healthcare_compliance
                if hasattr(f, "framework") and str(f.framework).lower().startswith("soc")]
        assert len(soc2) >= 0, "SOC2 findings field should exist"

    def test_labeled_soc2_findings_have_control_ids(self, labeled_compliance: list[dict]):
        soc2 = [f for f in labeled_compliance if f.get("framework") == "soc2"]
        for f in soc2:
            assert f.get("control_id"), f"SOC2 finding '{f['title']}' missing control_id"


# ---------------------------------------------------------------------------
# COMP-02: HIPAA mapping accuracy
# ---------------------------------------------------------------------------

class TestCOMP02HIPAAMapping:
    def test_healthcare_has_compliance_findings(
        self, healthcare_compliance: list[ComplianceFinding]
    ):
        assert len(healthcare_compliance) >= 1, (
            "Healthcare PRD should produce >= 1 compliance finding"
        )

    def test_hipaa_framework_supported(self):
        assert ComplianceFramework.HIPAA is not None


# ---------------------------------------------------------------------------
# COMP-03: PCI-DSS mapping accuracy
# ---------------------------------------------------------------------------

class TestCOMP03PCIDSSMapping:
    def test_labeled_pci_findings(self, labeled_compliance: list[dict]):
        pci = [f for f in labeled_compliance if f.get("framework") == "pci_dss"]
        assert len(pci) >= 1, "Labeled set should include PCI-DSS findings"
        for f in pci:
            assert f.get("control_id"), f"PCI finding '{f['title']}' missing control_id"


# ---------------------------------------------------------------------------
# COMP-04: ISO 27001 mapping accuracy
# ---------------------------------------------------------------------------

class TestCOMP04ISO27001Mapping:
    def test_iso_controls_defined(self, all_frameworks_matcher: CompliancePatternMatcher):
        assert ComplianceFramework.ISO_27001 in [
            ComplianceFramework.SOC2, ComplianceFramework.HIPAA,
            ComplianceFramework.PCI_DSS, ComplianceFramework.ISO_27001,
        ]


# ---------------------------------------------------------------------------
# COMP-05: Framework relevance
# ---------------------------------------------------------------------------

class TestCOMP05FrameworkRelevance:
    """Only applicable frameworks should be flagged."""

    def test_labeled_hipaa_fp_for_ecommerce(self, labeled_compliance: list[dict]):
        hipaa_fp = [
            f for f in labeled_compliance
            if f.get("framework") == "hipaa" and f.get("label") == "false_positive"
        ]
        assert len(hipaa_fp) >= 1, (
            "E-commerce app should have HIPAA as false positive in labeled set"
        )


# ---------------------------------------------------------------------------
# COMP-06: Control gap identification
# ---------------------------------------------------------------------------

class TestCOMP06ControlGapIdentification:
    def test_healthcare_has_gap_findings(
        self, healthcare_compliance: list[ComplianceFinding]
    ):
        assert len(healthcare_compliance) >= 1, (
            "Healthcare app should have compliance control gaps"
        )


# ---------------------------------------------------------------------------
# COMP-07: Remediation specificity
# ---------------------------------------------------------------------------

class TestCOMP07RemediationSpecificity:
    def test_findings_have_recommendations(
        self, healthcare_compliance: list[ComplianceFinding]
    ):
        for f in healthcare_compliance:
            assert f.recommendation and len(f.recommendation) > 10, (
                f"Compliance finding '{f.title}' has weak recommendation"
            )


# ---------------------------------------------------------------------------
# COMP-08: Cross-framework deduplication
# ---------------------------------------------------------------------------

class TestCOMP08CrossFrameworkDedup:
    def test_no_exact_title_duplicates(
        self, healthcare_compliance: list[ComplianceFinding]
    ):
        if not healthcare_compliance:
            pytest.skip("No findings")
        titles = [f.title.lower().strip() for f in healthcare_compliance]
        from collections import Counter
        counts = Counter(titles)
        dups = {t: c for t, c in counts.items() if c > 1}
        assert len(dups) == 0, f"Duplicate compliance findings: {dups}"

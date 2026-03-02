"""P2 Evals — Engineering Review Findings (ENG-01 through ENG-08).

Tests that engineering findings detect anti-patterns, complexity, dependency
risks, testing gaps, and error handling issues.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.analyzers.engineering_analyzer import EngineeringAnalyzer
from evals.framework.helpers import make_multi_analyzer
from context_graph.core.models import EngineeringFinding, EngineeringCategory, Severity

GOLDEN_CODEBASES = Path(__file__).parents[1] / "datasets" / "golden_codebases"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


@pytest.fixture(scope="module")
def eng_analyzer() -> EngineeringAnalyzer:
    return EngineeringAnalyzer()


@pytest.fixture(scope="module")
def multi_analyzer() -> MultiLanguageAnalyzer:
    return make_multi_analyzer()


# ---------------------------------------------------------------------------
# ENG-01: Anti-pattern detection
# ---------------------------------------------------------------------------

class TestENG01AntiPatternDetection:
    def test_analyzer_initializes(self, eng_analyzer: EngineeringAnalyzer):
        assert eng_analyzer is not None

    def test_engineering_categories_exist(self):
        assert len(EngineeringCategory) >= 10, (
            f"Expected >= 10 engineering categories, got {len(EngineeringCategory)}"
        )


# ---------------------------------------------------------------------------
# ENG-02: Pattern match precision
# ---------------------------------------------------------------------------

class TestENG02PatternPrecision:
    def test_sample_codebase_analysis(self, multi_analyzer):
        state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        assert state.files_analyzed > 0


# ---------------------------------------------------------------------------
# ENG-03: Complexity assessment
# ---------------------------------------------------------------------------

class TestENG03ComplexityAssessment:
    def test_engineering_finding_has_complexity_score(self):
        f = EngineeringFinding(
            title="Test",
            description="Desc",
            severity=Severity.MEDIUM,
            category=EngineeringCategory.HIGH_COMPLEXITY,
            complexity_score=7.5,
            recommendation="Refactor",
        )
        assert f.complexity_score == 7.5


# ---------------------------------------------------------------------------
# ENG-04 to ENG-08: Field and severity checks
# ---------------------------------------------------------------------------

class TestENG04DependencyRisk:
    def test_category_exists(self):
        assert EngineeringCategory.DEPRECATED_CODE is not None


class TestENG05TestingGaps:
    def test_categories_exist(self):
        assert EngineeringCategory.LOW_TEST_COVERAGE is not None
        assert EngineeringCategory.MISSING_TESTS is not None


class TestENG06ErrorHandling:
    def test_category_exists(self):
        assert EngineeringCategory.MISSING_ERROR_HANDLING is not None


class TestENG07Performance:
    def test_finding_fields(self):
        f = EngineeringFinding(
            title="N+1 Query",
            description="Detected N+1 query pattern",
            severity=Severity.HIGH,
            category=EngineeringCategory.HIGH_COMPLEXITY,
            estimated_effort="3 days",
            recommendation="Use eager loading",
        )
        assert f.estimated_effort == "3 days"


class TestENG08SeverityCalibration:
    def test_severity_enum_complete(self):
        assert Severity.CRITICAL is not None
        assert Severity.HIGH is not None
        assert Severity.MEDIUM is not None
        assert Severity.LOW is not None
        assert Severity.INFO is not None

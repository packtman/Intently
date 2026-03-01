"""P1 Evals — Latency & Cost (PERF-01 through PERF-10).

Tests pipeline latency and resource usage for various operations.
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
from context_graph.pm.quality_scorer import PRDQualityScorer
from context_graph.pm.effort_estimator import EffortEstimator

GOLDEN_PRDS = Path(__file__).parents[1] / "datasets" / "golden_prds"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


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


# ---------------------------------------------------------------------------
# PERF-01: Single review latency (pattern-based, no LLM)
# ---------------------------------------------------------------------------

class TestPERF01ReviewLatency:
    def test_pattern_review_under_10s(
        self, parser, multi_analyzer, delta_analyzer, threat_matcher
    ):
        start = time.time()
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        intent = parser.parse(prd)
        state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        delta = delta_analyzer.analyze(intent, state)
        findings = threat_matcher.match(delta)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"Pattern review took {elapsed:.1f}s (>10s)"


# ---------------------------------------------------------------------------
# PERF-02: Parsing latency
# ---------------------------------------------------------------------------

class TestPERF02ParsingLatency:
    def test_prd_parse_under_1s(self, parser):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        start = time.time()
        parser.parse(prd)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"PRD parse took {elapsed:.3f}s (>1s)"


# ---------------------------------------------------------------------------
# PERF-03: Codebase analysis latency
# ---------------------------------------------------------------------------

class TestPERF03CodebaseLatency:
    def test_small_codebase_under_5s(self, multi_analyzer):
        start = time.time()
        multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Codebase analysis took {elapsed:.1f}s (>5s)"


# ---------------------------------------------------------------------------
# PERF-05: Token usage (placeholder — requires LLM)
# ---------------------------------------------------------------------------

class TestPERF05TokenUsage:
    def test_placeholder(self):
        pass


# ---------------------------------------------------------------------------
# PERF-06: Cost per review (placeholder — requires LLM)
# ---------------------------------------------------------------------------

class TestPERF06CostPerReview:
    def test_placeholder(self):
        pass


# ---------------------------------------------------------------------------
# PERF-07: FP filter overhead (placeholder — requires LLM)
# ---------------------------------------------------------------------------

class TestPERF07FPFilterOverhead:
    def test_placeholder(self):
        pass


# ---------------------------------------------------------------------------
# PERF-09: Quality scoring latency
# ---------------------------------------------------------------------------

class TestPERF09QualityScoringLatency:
    def test_quality_scoring_under_100ms(self):
        scorer = PRDQualityScorer()
        from context_graph.core.models import PredictedQuestion
        qs = [PredictedQuestion(question=f"Q{i}", team="sec", severity="likely", reasoning="r")
              for i in range(10)]
        start = time.time()
        scorer.calculate_score(qs, "PRD content " * 100)
        elapsed = time.time() - start
        assert elapsed < 0.1, f"Quality scoring took {elapsed:.3f}s (>100ms)"


# ---------------------------------------------------------------------------
# PERF-10: Effort estimation latency
# ---------------------------------------------------------------------------

class TestPERF10EffortLatency:
    def test_effort_estimation_under_100ms(self):
        from context_graph.core.models import SecurityFinding, Severity, ThreatCategory
        estimator = EffortEstimator()
        findings = [
            SecurityFinding(
                title=f"Finding {i}", description="Desc", severity=Severity.MEDIUM,
                category=ThreatCategory.INJECTION, recommendation="Fix it",
            )
            for i in range(10)
        ]
        start = time.time()
        estimator.estimate(findings)
        elapsed = time.time() - start
        assert elapsed < 0.1, f"Effort estimation took {elapsed:.3f}s (>100ms)"

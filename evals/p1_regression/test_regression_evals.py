"""P1 Evals — Regression & Baseline Drift (REG-01 through REG-05).

Tests that analysis results are stable and don't regress against stored baselines.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from context_graph.parsers.markdown_parser import MarkdownPRDParser
from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.security.delta_analyzer import DeltaAnalyzer
from evals.framework.helpers import make_multi_analyzer
from context_graph.security.threat_patterns import ThreatPatternMatcher
from context_graph.core.models import SecurityFinding

BASELINE_DIR = Path(__file__).parents[2] / "baseline"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"
GOLDEN_PRDS = Path(__file__).parents[1] / "datasets" / "golden_prds"


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
# REG-01: Baseline comparison
# ---------------------------------------------------------------------------

class TestREG01BaselineComparison:
    """New results should be compared against stored baselines."""

    def test_baseline_files_exist(self):
        baselines = list(BASELINE_DIR.glob("review-*-baseline.json"))
        assert len(baselines) >= 1, (
            f"Expected >= 1 baseline file in {BASELINE_DIR}, found {len(baselines)}"
        )

    def test_baseline_structure(self):
        baselines = list(BASELINE_DIR.glob("review-*-baseline.json"))
        if not baselines:
            pytest.skip("No baseline files")
        for bp in baselines:
            data = json.loads(bp.read_text())
            assert "findings" in data or "summary" in data or "meta" in data, (
                f"Baseline {bp.name} missing expected keys"
            )


# ---------------------------------------------------------------------------
# REG-02: Finding stability
# ---------------------------------------------------------------------------

class TestREG02FindingStability:
    """Core findings should persist across runs."""

    def test_pattern_findings_stable(
        self, parser, multi_analyzer, delta_analyzer, threat_matcher
    ):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        runs = []
        for _ in range(2):
            intent = parser.parse(prd)
            state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
            delta = delta_analyzer.analyze(intent, state)
            findings = threat_matcher.match(delta)
            runs.append({f.title for f in findings})

        assert runs[0] == runs[1], (
            f"Pattern findings differ between runs: {runs[0] ^ runs[1]}"
        )


# ---------------------------------------------------------------------------
# REG-03: Score drift
# ---------------------------------------------------------------------------

class TestREG03ScoreDrift:
    """Quality scores should not drift without code changes."""

    def test_delta_risk_score_stable(self, parser, multi_analyzer, delta_analyzer):
        prd = (GOLDEN_PRDS / "auth_system_prd.md").read_text()
        scores = []
        for _ in range(2):
            intent = parser.parse(prd)
            state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
            delta = delta_analyzer.analyze(intent, state)
            scores.append(delta.delta.risk_score)

        assert scores[0] == scores[1], (
            f"Risk scores differ: {scores[0]} vs {scores[1]}"
        )


# ---------------------------------------------------------------------------
# REG-04: Model upgrade impact (placeholder)
# ---------------------------------------------------------------------------

class TestREG04ModelUpgrade:
    """Switching LLM model version shouldn't catastrophically change results."""

    def test_placeholder(self):
        pass


# ---------------------------------------------------------------------------
# REG-05: Prompt regression (placeholder)
# ---------------------------------------------------------------------------

class TestREG05PromptRegression:
    """Changes to system prompts shouldn't degrade quality."""

    def test_placeholder(self):
        pass

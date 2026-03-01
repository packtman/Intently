"""P0 Evals — False Positive Filtering (FP-01 through FP-10).

Tests that the FP filter correctly preserves true positives, removes false
positives, and behaves correctly with majority voting and multi-iteration.
These evals use mocked LLM providers so they run without API keys.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.llm.provider import LLMProvider, LLMResponse, AnalysisType
from context_graph.llm.false_positive_filter import (
    FalsePositiveFilter,
    FalsePositiveFilterResult,
    VALIDATION_STRATEGIES,
)
from context_graph.core.models import FalsePositiveFilterStats
from evals.framework.metrics import removal_rate

LABELED_DIR = Path(__file__).parents[1] / "datasets" / "labeled_findings"


def _load_labeled() -> list[dict[str, Any]]:
    return json.loads((LABELED_DIR / "security_findings.json").read_text())


def _tp_findings(labeled: list[dict]) -> list[dict]:
    return [f for f in labeled if f["label"] == "true_positive"]


def _fp_findings(labeled: list[dict]) -> list[dict]:
    return [f for f in labeled if f["label"] == "false_positive"]


def _make_mock_provider(
    keep_ids: set[str] | None = None,
    remove_ids: set[str] | None = None,
) -> LLMProvider:
    """Create a mock LLM provider that returns keep/remove verdicts.

    The FP filter expects ``validated_findings`` where each item contains
    the *original* finding fields plus ``fp_verdict`` and ``fp_reason``.
    The prompt sends findings as JSON in ``request.content``, not in
    ``request.context``.
    """
    keep_ids = keep_ids or set()
    remove_ids = remove_ids or set()

    provider = MagicMock(spec=LLMProvider)
    provider.provider_name = "mock"
    provider.model = "mock-model"

    async def mock_analyze(request):
        # Extract the findings JSON array from the prompt.
        # The prompt embeds findings as a JSON array after "Findings to Validate".
        # We find the opening '[' after that marker and parse incrementally.
        content = request.content
        findings_input: list[dict] = []
        marker = "Findings to Validate"
        marker_pos = content.find(marker)
        search_start = marker_pos if marker_pos >= 0 else 0
        arr_start = content.find("[", search_start)
        if arr_start >= 0:
            depth = 0
            arr_end = arr_start
            for i in range(arr_start, len(content)):
                if content[i] == "[":
                    depth += 1
                elif content[i] == "]":
                    depth -= 1
                    if depth == 0:
                        arr_end = i + 1
                        break
            try:
                findings_input = json.loads(content[arr_start:arr_end])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        validated = []
        for f in findings_input:
            fid = f.get("id", "")
            if fid in remove_ids:
                validated.append({
                    **f,
                    "fp_verdict": "remove",
                    "fp_reason": "Identified as false positive by mock",
                    "adjusted_severity": f.get("severity", "medium"),
                    "adjusted_confidence": 0.2,
                })
            else:
                validated.append({
                    **f,
                    "fp_verdict": "keep",
                    "fp_reason": "Confirmed as legitimate finding",
                    "adjusted_severity": f.get("severity", "medium"),
                    "adjusted_confidence": f.get("confidence", 0.8),
                })

        response_data = {
            "validated_findings": validated,
            "removal_summary": {
                "total_input": len(findings_input),
                "kept": sum(1 for v in validated if v["fp_verdict"] == "keep"),
                "removed": sum(1 for v in validated if v["fp_verdict"] == "remove"),
                "downgraded": 0,
                "removal_reasons": ["mock removal"],
            },
        }
        return LLMResponse(
            provider="mock",
            model="mock-model",
            content=json.dumps(response_data),
            analysis_type=AnalysisType.SECURITY_REVIEW,
            structured_data=response_data,
        )

    provider.analyze = AsyncMock(side_effect=mock_analyze)
    return provider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def labeled_findings() -> list[dict[str, Any]]:
    return _load_labeled()


@pytest.fixture
def perfect_filter_provider(labeled_findings: list[dict]) -> LLMProvider:
    """Provider that correctly identifies all FPs and keeps all TPs."""
    fp_ids = {f["id"] for f in _fp_findings(labeled_findings)}
    return _make_mock_provider(remove_ids=fp_ids)


@pytest.fixture
def aggressive_filter_provider(labeled_findings: list[dict]) -> LLMProvider:
    """Provider that removes everything — tests TP preservation."""
    all_ids = {f["id"] for f in labeled_findings}
    return _make_mock_provider(remove_ids=all_ids)


@pytest.fixture
def conservative_filter_provider() -> LLMProvider:
    """Provider that keeps everything — tests FP removal."""
    return _make_mock_provider(remove_ids=set())


# ---------------------------------------------------------------------------
# FP-01: True positive preservation
# ---------------------------------------------------------------------------

class TestFP01TruePositivePreservation:
    """Real findings should not be incorrectly removed."""

    @pytest.mark.asyncio
    async def test_perfect_filter_preserves_all_tp(
        self, perfect_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=perfect_filter_provider,
            max_iterations=1,
            parallel=True,
            min_findings_to_filter=1,
            removal_threshold=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent={"title": "Test"},
            state={"codebase_path": "/test"},
            delta={"summary": "Test delta"},
        )
        tp_ids = {f["id"] for f in _tp_findings(labeled_findings)}
        retained_ids = {f["id"] for f in result.filtered_findings}
        missing_tp = tp_ids - retained_ids
        assert len(missing_tp) == 0, (
            f"Perfect filter should retain all TPs. Missing: {missing_tp}"
        )

    @pytest.mark.asyncio
    async def test_critical_findings_never_removed_by_conservative(
        self, conservative_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=conservative_filter_provider,
            max_iterations=1,
            parallel=True,
            min_findings_to_filter=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent=None,
            state=None,
            delta=None,
        )
        critical_ids = {
            f["id"] for f in labeled_findings if f["severity"] == "critical"
        }
        retained_ids = {f["id"] for f in result.filtered_findings}
        missing_critical = critical_ids - retained_ids
        assert len(missing_critical) == 0, (
            f"Conservative filter removed critical findings: {missing_critical}"
        )


# ---------------------------------------------------------------------------
# FP-02: False positive removal rate
# ---------------------------------------------------------------------------

class TestFP02FPRemovalRate:
    """FP filter should reduce false positive count."""

    @pytest.mark.asyncio
    async def test_perfect_filter_removes_fps(
        self, perfect_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=perfect_filter_provider,
            max_iterations=1,
            parallel=True,
            min_findings_to_filter=1,
            removal_threshold=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent={"title": "Test"},
            state={"codebase_path": "/test"},
            delta={"summary": "Test delta"},
        )
        fp_ids = {f["id"] for f in _fp_findings(labeled_findings)}
        retained_ids = {f["id"] for f in result.filtered_findings}
        retained_fps = fp_ids & retained_ids
        fp_removal = 1 - (len(retained_fps) / len(fp_ids)) if fp_ids else 1.0
        assert fp_removal >= 0.50, (
            f"FP removal rate {fp_removal:.2f} below 0.50. "
            f"Retained FPs: {retained_fps}"
        )


# ---------------------------------------------------------------------------
# FP-03: Context validation accuracy
# ---------------------------------------------------------------------------

class TestFP03ContextValidation:
    """Findings already mitigated by existing controls should be identified."""

    def test_validation_strategies_exist(self):
        assert len(VALIDATION_STRATEGIES) == 3, (
            f"Expected 3 validation strategies, got {len(VALIDATION_STRATEGIES)}"
        )
        names = {s["name"] for s in VALIDATION_STRATEGIES}
        assert "context_validation" in names


# ---------------------------------------------------------------------------
# FP-04: Specificity check accuracy
# ---------------------------------------------------------------------------

class TestFP04SpecificityCheck:
    """Generic boilerplate findings should be identified."""

    def test_specificity_strategy_exists(self):
        names = {s["name"] for s in VALIDATION_STRATEGIES}
        assert "specificity_check" in names


# ---------------------------------------------------------------------------
# FP-05: Evidence grounding accuracy
# ---------------------------------------------------------------------------

class TestFP05EvidenceGrounding:
    """Speculative findings without evidence should be identified."""

    def test_evidence_strategy_exists(self):
        names = {s["name"] for s in VALIDATION_STRATEGIES}
        assert "evidence_grounding" in names

    def test_fp_findings_lack_evidence(self, labeled_findings: list[dict]):
        fps = _fp_findings(labeled_findings)
        ungrounded = sum(
            1 for f in fps if not f.get("source_reference", "").strip()
        )
        rate = ungrounded / len(fps) if fps else 0
        assert rate >= 0.50, (
            f"Only {rate:.0%} of labeled FPs lack source_reference — expected >= 50%"
        )


# ---------------------------------------------------------------------------
# FP-06: Parallel vs sequential agreement
# ---------------------------------------------------------------------------

class TestFP06ParallelVsSequential:
    """Both modes should produce results without errors."""

    @pytest.mark.asyncio
    async def test_parallel_mode_runs(
        self, perfect_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=perfect_filter_provider,
            max_iterations=1,
            parallel=True,
            min_findings_to_filter=1,
            removal_threshold=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent=None, state=None, delta=None,
        )
        assert result.execution_mode == "parallel"

    @pytest.mark.asyncio
    async def test_sequential_mode_runs(
        self, perfect_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=perfect_filter_provider,
            max_iterations=3,
            parallel=False,
            min_findings_to_filter=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent=None, state=None, delta=None,
        )
        assert result.execution_mode == "sequential"


# ---------------------------------------------------------------------------
# FP-07: Majority vote correctness
# ---------------------------------------------------------------------------

class TestFP07MajorityVote:
    """Majority vote should behave correctly."""

    def test_removal_threshold_default(self):
        fp = FalsePositiveFilter(
            llm_provider=MagicMock(spec=LLMProvider),
            max_iterations=3,
            parallel=True,
        )
        assert fp.removal_threshold >= 1, (
            "Default removal_threshold should be >= 1"
        )


# ---------------------------------------------------------------------------
# FP-08: Multi-iteration stability
# ---------------------------------------------------------------------------

class TestFP08MultiIterationStability:
    """Running multiple iterations should converge."""

    @pytest.mark.asyncio
    async def test_iterations_converge(
        self, conservative_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=conservative_filter_provider,
            max_iterations=3,
            parallel=False,
            min_findings_to_filter=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent=None, state=None, delta=None,
        )
        assert result.total_iterations <= 3, (
            f"Should complete within max_iterations, ran {result.total_iterations}"
        )


# ---------------------------------------------------------------------------
# FP-09: Critical finding preservation
# ---------------------------------------------------------------------------

class TestFP09CriticalPreservation:
    """Critical-severity findings should ideally not be removed.

    NOTE: The current FP filter does not have a built-in safety mechanism
    to protect critical findings from removal. If an LLM unanimously says
    "remove", the filter will comply. This eval documents that gap.
    """

    @pytest.mark.asyncio
    async def test_conservative_filter_retains_criticals(
        self, conservative_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=conservative_filter_provider,
            max_iterations=1,
            parallel=True,
            min_findings_to_filter=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent=None, state=None, delta=None,
        )
        critical_ids = {
            f["id"] for f in labeled_findings if f["severity"] == "critical"
        }
        retained_ids = {f["id"] for f in result.filtered_findings}
        missing_critical = critical_ids - retained_ids
        assert len(missing_critical) == 0, (
            f"Conservative filter should retain all critical findings. "
            f"Missing: {missing_critical}"
        )


# ---------------------------------------------------------------------------
# FP-10: Filter throughput limit
# ---------------------------------------------------------------------------

class TestFP10FilterThroughput:
    """Filtering should not remove >50% of findings normally."""

    @pytest.mark.asyncio
    async def test_conservative_filter_keeps_most(
        self, conservative_filter_provider: LLMProvider, labeled_findings: list[dict]
    ):
        fp_filter = FalsePositiveFilter(
            llm_provider=conservative_filter_provider,
            max_iterations=1,
            parallel=True,
            min_findings_to_filter=1,
        )
        result = await fp_filter.filter_findings(
            findings=labeled_findings,
            dimension="security",
            intent=None, state=None, delta=None,
        )
        rr = removal_rate(len(labeled_findings), len(result.filtered_findings))
        assert rr <= 0.50, (
            f"Conservative filter removed {rr:.0%} — should keep most findings"
        )

    def test_skip_when_below_min_findings(self):
        """Filter should skip when finding count is below threshold."""
        fp_filter = FalsePositiveFilter(
            llm_provider=MagicMock(spec=LLMProvider),
            max_iterations=3,
            parallel=True,
            min_findings_to_filter=100,
        )
        assert fp_filter.min_findings_to_filter == 100

    def test_fp_filter_stats_model(self):
        stats = FalsePositiveFilterStats(
            dimension="security",
            original_count=10,
            final_count=7,
            total_removed=3,
            total_downgraded=0,
            total_iterations=2,
            removal_rate=0.30,
            execution_mode="parallel",
        )
        assert stats.removal_rate == 0.30
        assert stats.execution_mode == "parallel"

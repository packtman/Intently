"""
Tests for the multi-iteration False Positive Filter pipeline.

Exercises:
- FalsePositiveFilter in both parallel and sequential modes
- Majority-vote merge logic (parallel mode)
- Sequential pipeline behaviour (early-stop, progressive removal)
- Integration with ParallelLLMAnalyzer._refine_and_filter
- Feature flag gating (including parallel flag)
- Stats tracking & execution mode
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from context_graph.config.features import FeatureFlags, set_features, reset_features
from context_graph.llm.false_positive_filter import (
    FalsePositiveFilter,
    FalsePositiveFilterResult,
    FilterIterationResult,
    VALIDATION_STRATEGIES,
)
from context_graph.llm.provider import LLMResponse, AnalysisType
from context_graph.core.models import FalsePositiveFilterStats


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_FINDINGS = [
    {
        "id": "F1",
        "title": "Missing Rate Limiting on Review Submission API",
        "severity": "high",
        "category": "denial_of_service",
        "description": "The POST /api/reviews endpoint lacks rate limiting.",
        "affected_components": ["/api/reviews"],
        "recommendation": "Add rate limiting middleware (e.g., 10 req/min per user).",
        "confidence": 0.8,
    },
    {
        "id": "F2",
        "title": "Generic Security Best Practice Reminder",
        "severity": "medium",
        "category": "security_misconfiguration",
        "description": "Always follow security best practices.",
        "affected_components": [],
        "recommendation": "Improve security.",
        "confidence": 0.4,
    },
    {
        "id": "F3",
        "title": "SQL Injection in Search Endpoint",
        "severity": "critical",
        "category": "injection",
        "description": "The /api/search endpoint passes user input directly to an ORM raw query.",
        "affected_components": ["/api/search"],
        "recommendation": "Use parameterized queries.",
        "confidence": 0.9,
    },
    {
        "id": "F4",
        "title": "Missing HTTPS Enforcement",
        "severity": "medium",
        "category": "sensitive_data_exposure",
        "description": "The application should enforce HTTPS for all connections.",
        "affected_components": [],
        "recommendation": "Enable HSTS headers.",
        "confidence": 0.5,
    },
    {
        "id": "F5",
        "title": "Lack of Input Validation on User Profile Fields",
        "severity": "medium",
        "category": "injection",
        "description": "User profile name/bio fields are not validated for XSS payloads.",
        "affected_components": ["/api/users/profile"],
        "recommendation": "Sanitize and validate all user input fields.",
        "confidence": 0.75,
    },
]

SAMPLE_INTENT = {
    "title": "AI-Powered Product Review Platform",
    "features": ["Review submission", "Star ratings", "AI moderation", "Search"],
    "api_changes": [
        {"method": "POST", "path": "/api/reviews"},
        {"method": "GET", "path": "/api/search"},
    ],
}

SAMPLE_STATE = {
    "api_endpoints": [
        {"path": "/api/reviews", "method": "POST", "auth_required": True},
        {"path": "/api/search", "method": "GET", "auth_required": False},
    ],
    "existing_controls": ["rate_limiting", "input_validation", "logging"],
    "auth_patterns": [{"type": "JWT", "applied_to": "all POST endpoints"}],
}

SAMPLE_DELTA = {
    "new_endpoints": ["/api/reviews/ai-moderate"],
    "attack_surface_changes": ["New AI moderation endpoint"],
    "summary": "Adding AI-powered review moderation.",
}


def _make_mock_provider():
    """Create a mock LLM provider for sequential-mode tests.

    Behaviour per strategy (applied to whatever findings are passed in):
      - context_validation: removes F1 (rate limiting already exists)
      - specificity_check:  removes F2, F4 (generic boilerplate)
      - evidence_grounding:  keeps all, bumps confidence +0.1
    """
    provider = MagicMock()
    provider.provider_name = "mock-provider"

    async def mock_analyze(request):
        ctx = request.context or {}
        strategy = ctx.get("strategy", "")
        findings_in = (
            json.loads(
                request.content.split("## Findings to Validate\n")[-1]
                .split("\n\nFor EACH")[0]
            )
            if "## Findings to Validate" in request.content
            else []
        )

        validated = []
        for f in findings_in:
            fid = f.get("id", "")

            if strategy == "context_validation":
                if fid == "F1":
                    validated.append({**f, "fp_verdict": "remove", "fp_reason": "Rate limiting already exists in codebase controls"})
                else:
                    validated.append({**f, "fp_verdict": "keep"})

            elif strategy == "specificity_check":
                if fid in ("F2", "F4"):
                    validated.append({**f, "fp_verdict": "remove", "fp_reason": "Generic boilerplate, not specific to this PRD"})
                else:
                    validated.append({**f, "fp_verdict": "keep"})

            elif strategy == "evidence_grounding":
                validated.append({**f, "fp_verdict": "keep", "adjusted_confidence": min(f.get("confidence", 0.5) + 0.1, 1.0)})

            else:
                validated.append({**f, "fp_verdict": "keep"})

        response = LLMResponse(
            provider="mock-provider",
            model="mock-model",
            content="",
            analysis_type=AnalysisType.SECURITY_REVIEW,
            structured_data={
                "validated_findings": validated,
                "removal_summary": {
                    "total_input": len(findings_in),
                    "kept": sum(1 for v in validated if v.get("fp_verdict") == "keep"),
                    "removed": sum(1 for v in validated if v.get("fp_verdict") == "remove"),
                    "downgraded": sum(1 for v in validated if v.get("fp_verdict") == "downgrade"),
                    "removal_reasons": [v.get("fp_reason", "") for v in validated if v.get("fp_verdict") == "remove"],
                },
            },
            tokens_used=500,
            latency_ms=200.0,
        )
        return response

    provider.analyze = AsyncMock(side_effect=mock_analyze)
    return provider


def _make_mock_provider_parallel():
    """Create a mock LLM provider for parallel-mode tests.

    In parallel mode every strategy sees the SAME findings, so we need
    at least 2 strategies to agree on removing a finding for it to be
    removed (threshold=2).

    Behaviour:
      - context_validation: removes F1, F2
      - specificity_check:  removes F2, F4
      - evidence_grounding:  removes F4, downgrades F1

    Expected majority-vote outcome (threshold=2):
      - F1: 1 remove + 1 downgrade → NOT removed (only 1 remove vote), downgraded
      - F2: 2 removes → REMOVED
      - F3: 0 removes → kept
      - F4: 2 removes → REMOVED
      - F5: 0 removes → kept
    """
    provider = MagicMock()
    provider.provider_name = "mock-parallel"

    async def mock_analyze(request):
        ctx = request.context or {}
        strategy = ctx.get("strategy", "")
        findings_in = (
            json.loads(
                request.content.split("## Findings to Validate\n")[-1]
                .split("\n\nFor EACH")[0]
            )
            if "## Findings to Validate" in request.content
            else []
        )

        validated = []
        for f in findings_in:
            fid = f.get("id", "")

            if strategy == "context_validation":
                if fid in ("F1", "F2"):
                    validated.append({**f, "fp_verdict": "remove", "fp_reason": f"Already mitigated ({fid})"})
                else:
                    validated.append({**f, "fp_verdict": "keep"})

            elif strategy == "specificity_check":
                if fid in ("F2", "F4"):
                    validated.append({**f, "fp_verdict": "remove", "fp_reason": f"Generic boilerplate ({fid})"})
                else:
                    validated.append({**f, "fp_verdict": "keep"})

            elif strategy == "evidence_grounding":
                if fid == "F4":
                    validated.append({**f, "fp_verdict": "remove", "fp_reason": f"No evidence ({fid})"})
                elif fid == "F1":
                    validated.append({**f, "fp_verdict": "downgrade", "adjusted_severity": "medium", "adjusted_confidence": 0.5})
                else:
                    validated.append({**f, "fp_verdict": "keep", "adjusted_confidence": min(f.get("confidence", 0.5) + 0.1, 1.0)})

            else:
                validated.append({**f, "fp_verdict": "keep"})

        response = LLMResponse(
            provider="mock-parallel",
            model="mock-model",
            content="",
            analysis_type=AnalysisType.SECURITY_REVIEW,
            structured_data={
                "validated_findings": validated,
                "removal_summary": {
                    "total_input": len(findings_in),
                    "kept": sum(1 for v in validated if v.get("fp_verdict") == "keep"),
                    "removed": sum(1 for v in validated if v.get("fp_verdict") == "remove"),
                    "downgraded": sum(1 for v in validated if v.get("fp_verdict") == "downgrade"),
                    "removal_reasons": [v.get("fp_reason", "") for v in validated if v.get("fp_verdict") == "remove"],
                },
            },
            tokens_used=500,
            latency_ms=200.0,
        )
        return response

    provider.analyze = AsyncMock(side_effect=mock_analyze)
    return provider


# ---------------------------------------------------------------------------
# Tests — Parallel mode (default)
# ---------------------------------------------------------------------------


class TestFalsePositiveFilterParallel:
    """Unit tests for FalsePositiveFilter in parallel mode."""

    def test_validation_strategies_exist(self):
        """Verify all 3 validation strategies are defined."""
        assert len(VALIDATION_STRATEGIES) == 3
        names = [s["name"] for s in VALIDATION_STRATEGIES]
        assert "context_validation" in names
        assert "specificity_check" in names
        assert "evidence_grounding" in names

    @pytest.mark.asyncio
    async def test_parallel_default_threshold_requires_majority(self):
        """Default threshold=2: majority of strategies must agree to remove."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        assert result.execution_mode == "parallel"
        assert result.original_count == 5

        # F2 (2 remove votes), F4 (2 remove votes) → removed
        # F1 has 1 remove + 1 downgrade → kept but downgraded
        assert result.total_removed == 2
        removed_ids = {f["id"] for f in result.removed_findings}
        assert removed_ids == {"F2", "F4"}

        # F1 (downgraded), F3, F5 → kept
        assert result.final_count == 3
        surviving_ids = {f["id"] for f in result.filtered_findings}
        assert surviving_ids == {"F1", "F3", "F5"}

        # F1 should be downgraded
        assert result.total_downgraded == 1

        # All 3 strategies should have run
        assert result.total_iterations == 3

    @pytest.mark.asyncio
    async def test_parallel_threshold_2_requires_majority(self):
        """With threshold=2, majority must agree to remove."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
            removal_threshold=2,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        # F2 (2 remove votes) and F4 (2 remove votes) should be removed
        # F1 has only 1 remove + 1 downgrade → kept but downgraded
        assert result.total_removed == 2
        removed_ids = {f["id"] for f in result.removed_findings}
        assert removed_ids == {"F2", "F4"}

        assert result.final_count == 3
        surviving_ids = {f["id"] for f in result.filtered_findings}
        assert surviving_ids == {"F1", "F3", "F5"}

        # F1 should be marked as downgraded
        f1 = next(f for f in result.filtered_findings if f["id"] == "F1")
        assert "fp_downgraded_by" in f1
        assert result.total_downgraded == 1

    @pytest.mark.asyncio
    async def test_parallel_threshold_3_requires_unanimity(self):
        """With threshold=3 (unanimous), only findings ALL 3 agree on are removed."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
            removal_threshold=3,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        # No finding has all 3 strategies voting remove → nothing removed
        assert result.total_removed == 0
        assert result.final_count == 5

    @pytest.mark.asyncio
    async def test_parallel_all_strategies_run_concurrently(self):
        """Verify all 3 strategies get called (not stopped early)."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        # All 3 strategies should have produced iteration results
        assert len(result.iteration_results) == 3
        strategy_names = {ir.strategy_name for ir in result.iteration_results}
        assert strategy_names == {"context_validation", "specificity_check", "evidence_grounding"}

    @pytest.mark.asyncio
    async def test_parallel_latency_is_max_not_sum(self):
        """In parallel mode, total latency should be the max (not sum)."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        # Mock returns 200ms per call; parallel max should be 200, not 600
        assert result.total_latency_ms == 200.0

    @pytest.mark.asyncio
    async def test_parallel_removed_findings_have_vote_info(self):
        """Removed findings should annotate which strategies voted to remove."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
            removal_threshold=2,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        f2 = next(f for f in result.removed_findings if f["id"] == "F2")
        assert "fp_removed_by" in f2
        assert set(f2["fp_removed_by"]) == {"context_validation", "specificity_check"}
        assert "fp_vote_count" in f2
        assert f2["fp_vote_count"] == "2/3"


# ---------------------------------------------------------------------------
# Tests — Sequential mode
# ---------------------------------------------------------------------------


class TestFalsePositiveFilterSequential:
    """Unit tests for FalsePositiveFilter in sequential (pipeline) mode."""

    @pytest.mark.asyncio
    async def test_sequential_pipeline_removes_false_positives(self):
        """Run 3 sequential iterations — F1 removed in round 1, F2+F4 in round 2."""
        provider = _make_mock_provider()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=False,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        assert result.execution_mode == "sequential"
        assert result.original_count == 5
        assert result.total_removed == 3
        assert result.final_count == 2

        surviving_ids = {f["id"] for f in result.filtered_findings}
        assert surviving_ids == {"F3", "F5"}

        removed_ids = {f["id"] for f in result.removed_findings}
        assert removed_ids == {"F1", "F2", "F4"}

        assert result.total_iterations == 3
        assert result.iteration_results[0].strategy_name == "context_validation"
        assert result.iteration_results[0].removed_count == 1
        assert result.iteration_results[1].strategy_name == "specificity_check"
        assert result.iteration_results[1].removed_count == 2
        assert result.iteration_results[2].strategy_name == "evidence_grounding"
        assert result.iteration_results[2].removed_count == 0

    @pytest.mark.asyncio
    async def test_sequential_early_stop_on_no_changes(self):
        """Sequential mode: stop early if a round makes no changes."""
        provider = MagicMock()
        provider.provider_name = "mock"

        async def mock_analyze_keep_all(request):
            findings_text = request.content.split("## Findings to Validate\n")[-1].split("\n\nFor EACH")[0]
            try:
                findings_in = json.loads(findings_text)
            except json.JSONDecodeError:
                findings_in = SAMPLE_FINDINGS

            validated = [{**f, "fp_verdict": "keep"} for f in findings_in]
            return LLMResponse(
                provider="mock", model="mock", content="",
                analysis_type=AnalysisType.SECURITY_REVIEW,
                structured_data={
                    "validated_findings": validated,
                    "removal_summary": {"total_input": len(findings_in), "kept": len(findings_in), "removed": 0, "downgraded": 0, "removal_reasons": []},
                },
                tokens_used=100, latency_ms=50.0,
            )

        provider.analyze = AsyncMock(side_effect=mock_analyze_keep_all)

        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=False,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
        )

        assert result.execution_mode == "sequential"
        assert result.total_iterations == 1
        assert result.total_removed == 0
        assert result.final_count == 5

    @pytest.mark.asyncio
    async def test_sequential_latency_is_sum(self):
        """In sequential mode, total latency is the sum of all rounds."""
        provider = _make_mock_provider()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=False,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        # 3 rounds × 200ms each = 600ms total
        assert result.total_latency_ms == 600.0


# ---------------------------------------------------------------------------
# Tests — Common behaviour (mode-agnostic)
# ---------------------------------------------------------------------------


class TestFalsePositiveFilterCommon:
    """Tests that apply to both parallel and sequential modes."""

    @pytest.mark.asyncio
    async def test_skips_when_too_few_findings(self):
        """Skip filtering when findings count is below threshold."""
        provider = _make_mock_provider()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=10,
            verbose=False,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
        )

        assert result.original_count == 5
        assert result.final_count == 5
        assert result.total_removed == 0
        assert result.total_iterations == 0
        assert len(result.filtered_findings) == 5

    @pytest.mark.asyncio
    async def test_graceful_failure_parallel(self):
        """Parallel: if all LLM calls throw, keep all findings."""
        provider = MagicMock()
        provider.provider_name = "mock"
        provider.analyze = AsyncMock(side_effect=RuntimeError("LLM down"))

        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
        )

        assert result.final_count == 5
        assert result.total_removed == 0

    @pytest.mark.asyncio
    async def test_graceful_failure_sequential(self):
        """Sequential: if LLM call throws, keep all findings."""
        provider = MagicMock()
        provider.provider_name = "mock"
        provider.analyze = AsyncMock(side_effect=RuntimeError("LLM down"))

        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=False,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
        )

        assert result.final_count == 5
        assert result.total_removed == 0

    @pytest.mark.asyncio
    async def test_removal_rate_calculation(self):
        """Removal rate should be computed correctly."""
        provider = _make_mock_provider_parallel()
        fp_filter = FalsePositiveFilter(
            llm_provider=provider,
            max_iterations=3,
            min_findings_to_filter=2,
            verbose=False,
            parallel=True,
            removal_threshold=2,
        )

        result = await fp_filter.filter_findings(
            findings=SAMPLE_FINDINGS,
            dimension="security",
            intent=SAMPLE_INTENT,
            state=SAMPLE_STATE,
            delta=SAMPLE_DELTA,
        )

        # 2 removed out of 5 = 40%
        assert abs(result.removal_rate - 0.4) < 0.01


# ---------------------------------------------------------------------------
# Tests — Feature flag integration
# ---------------------------------------------------------------------------


class TestFeatureFlagIntegration:
    """Test that feature flags properly gate FP filtering."""

    def setup_method(self):
        reset_features()

    def teardown_method(self):
        reset_features()

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_by_default(self):
        """Verify the FP filtering flag is True by default."""
        from context_graph.config.features import get_features
        features = get_features()
        assert features.enable_false_positive_filtering is True

    @pytest.mark.asyncio
    async def test_parallel_flag_enabled_by_default(self):
        """Verify parallel mode is enabled by default with threshold=2."""
        from context_graph.config.features import get_features
        features = get_features()
        assert features.false_positive_parallel is True
        assert features.false_positive_removal_threshold == 2

    @pytest.mark.asyncio
    async def test_feature_flag_disables_filtering(self):
        """When flag is False, _filter_false_positives returns findings unchanged."""
        flags = FeatureFlags()
        flags.enable_false_positive_filtering = False
        set_features(flags)

        from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer

        with patch("context_graph.llm.parallel_analyzer.OpenAIProvider") as MockOAI:
            mock_instance = MagicMock()
            MockOAI.return_value = mock_instance

            analyzer = ParallelLLMAnalyzer.__new__(ParallelLLMAnalyzer)
            analyzer.providers = [mock_instance]
            analyzer.fp_filter_results = {}

            result = await analyzer._filter_false_positives(
                findings=SAMPLE_FINDINGS,
                dimension="security",
            )

            assert len(result) == 5
            assert result == SAMPLE_FINDINGS


# ---------------------------------------------------------------------------
# Tests — FalsePositiveFilterStats model
# ---------------------------------------------------------------------------


class TestFalsePositiveFilterStats:
    """Test the FalsePositiveFilterStats model."""

    def test_stats_dataclass(self):
        stats = FalsePositiveFilterStats(
            dimension="security",
            original_count=20,
            final_count=12,
            total_removed=8,
            total_downgraded=2,
            total_iterations=3,
            removal_rate=0.4,
            execution_mode="parallel",
        )
        assert stats.dimension == "security"
        assert stats.original_count == 20
        assert stats.final_count == 12
        assert stats.total_removed == 8
        assert stats.removal_rate == 0.4
        assert stats.execution_mode == "parallel"

    def test_stats_default_execution_mode(self):
        stats = FalsePositiveFilterStats()
        assert stats.execution_mode == "parallel"


# ---------------------------------------------------------------------------
# Run with: pytest src/context_graph/tests/test_false_positive_filter.py -v
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

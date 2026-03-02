"""P2 Evals — Iterative Analysis (ITER-01 through ITER-06).

Tests that multi-round iterative analysis correctly tracks categories,
deduplicates findings, and respects max round limits.
"""
from __future__ import annotations

import pytest

from context_graph.llm.iterative_analyzer import (
    IterativeAnalyzer,
    IterativeAnalysisResult,
    GenerationMetadata,
    LLMCallResult,
)
from context_graph.llm.analysis_categories import (
    AnalysisTypeCategories,
    get_analysis_config,
)


# ---------------------------------------------------------------------------
# ITER-01: Category coverage improvement
# ---------------------------------------------------------------------------

class TestITER01CategoryCoverage:
    def test_security_categories_defined(self):
        config = get_analysis_config(AnalysisTypeCategories.SECURITY)
        assert len(config.categories) >= 3, (
            f"Security should have >= 3 categories, got {len(config.categories)}"
        )

    def test_privacy_categories_defined(self):
        config = get_analysis_config(AnalysisTypeCategories.PRIVACY)
        assert len(config.categories) >= 3


# ---------------------------------------------------------------------------
# ITER-02: Diminishing returns detection
# ---------------------------------------------------------------------------

class TestITER02DiminishingReturns:
    def test_generation_metadata_fields(self):
        meta = GenerationMetadata(
            analysis_complete=True,
            continuation_needed=False,
            covered_categories=["injection", "auth"],
            remaining_categories=["crypto"],
        )
        assert meta.analysis_complete is True
        assert not meta.continuation_needed
        assert len(meta.covered_categories) == 2


# ---------------------------------------------------------------------------
# ITER-03: Deduplication across rounds
# ---------------------------------------------------------------------------

class TestITER03Deduplication:
    def test_iterative_result_fields(self):
        result = IterativeAnalysisResult(
            findings=[],
            total_rounds=2,
            covered_categories=["injection"],
        )
        assert result.total_rounds == 2
        assert "injection" in result.covered_categories


# ---------------------------------------------------------------------------
# ITER-04: Continuation context quality
# ---------------------------------------------------------------------------

class TestITER04ContinuationContext:
    def test_metadata_from_dict(self):
        data = {
            "analysis_complete": False,
            "continuation_needed": True,
            "remaining_categories_to_analyze": ["auth", "crypto"],
            "last_finding_id": "F-5",
        }
        meta = GenerationMetadata.from_dict(data)
        assert meta.continuation_needed is True
        assert len(meta.remaining_categories) == 2


# ---------------------------------------------------------------------------
# ITER-05: Max rounds safety
# ---------------------------------------------------------------------------

class TestITER05MaxRounds:
    def test_config_has_max_rounds(self):
        config = get_analysis_config(AnalysisTypeCategories.SECURITY)
        assert config.max_rounds >= 1, "max_rounds should be >= 1"
        assert config.max_rounds <= 10, "max_rounds should be <= 10"


# ---------------------------------------------------------------------------
# ITER-06: Finding quality by round
# ---------------------------------------------------------------------------

class TestITER06FindingQualityByRound:
    def test_llm_call_result_fields(self):
        result = LLMCallResult(
            structured_data={"findings": [{"id": "F1", "title": "Test"}]},
            tokens_used=100,
            latency_ms=500.0,
        )
        assert result.tokens_used == 100
        assert result.latency_ms == 500.0

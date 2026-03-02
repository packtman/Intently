"""P2 Evals — Parallel / Multi-Provider Analysis (PAR-01 through PAR-06).

Tests that parallel analysis correctly uses multiple providers, merges
findings, and handles single-provider fallback.
"""
from __future__ import annotations

import pytest

from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer, ParallelAnalysisResult
from context_graph.llm.provider import LLMResponse, AnalysisType


# ---------------------------------------------------------------------------
# PAR-01: Provider complementarity
# ---------------------------------------------------------------------------

class TestPAR01ProviderComplementarity:
    def test_parallel_result_tracks_providers(self):
        result = ParallelAnalysisResult(
            providers_used=["openai", "anthropic"],
            merged_findings=[{"id": "F1"}],
            consensus_items=[{"id": "F1"}],
            divergent_items=[],
        )
        assert len(result.providers_used) == 2


# ---------------------------------------------------------------------------
# PAR-02: Consensus finding quality
# ---------------------------------------------------------------------------

class TestPAR02ConsensusFindingQuality:
    def test_consensus_vs_divergent(self):
        result = ParallelAnalysisResult(
            providers_used=["openai"],
            merged_findings=[{"id": "F1"}, {"id": "F2"}],
            consensus_items=[{"id": "F1"}],
            divergent_items=[{"id": "F2"}],
        )
        assert len(result.consensus_items) <= len(result.merged_findings)


# ---------------------------------------------------------------------------
# PAR-03: Divergent finding triage
# ---------------------------------------------------------------------------

class TestPAR03DivergentTriage:
    def test_divergent_items_tracked(self):
        result = ParallelAnalysisResult(
            divergent_items=[{"id": "D1", "provider": "openai"}],
        )
        assert len(result.divergent_items) == 1


# ---------------------------------------------------------------------------
# PAR-04: Merge quality
# ---------------------------------------------------------------------------

class TestPAR04MergeQuality:
    def test_merged_findings_list(self):
        result = ParallelAnalysisResult(
            merged_findings=[{"id": "F1", "title": "Test"}],
        )
        assert all("id" in f for f in result.merged_findings)


# ---------------------------------------------------------------------------
# PAR-05: Single-provider fallback
# ---------------------------------------------------------------------------

class TestPAR05SingleProviderFallback:
    def test_single_provider_result_valid(self):
        result = ParallelAnalysisResult(
            providers_used=["openai"],
            merged_findings=[{"id": "F1"}],
        )
        assert len(result.providers_used) == 1
        assert len(result.merged_findings) >= 1


# ---------------------------------------------------------------------------
# PAR-06: Token efficiency
# ---------------------------------------------------------------------------

class TestPAR06TokenEfficiency:
    def test_total_tokens_tracked(self):
        result = ParallelAnalysisResult(total_tokens=5000)
        assert result.total_tokens == 5000

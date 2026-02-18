"""
Tests for the LLM prompt repetition feature.

Validates:
- _apply_prompt_repetition static method behaviour
- _resolve_prompt_repetition priority chain (context > provider override > feature flag)
- Feature flag gating
- Per-request override via AnalysisRequest.context
- Provider-level override via prompt_repetition_override
- ParallelLLMAnalyzer propagation
- ReviewConfig integration
- CLI and API wiring
"""

import pytest
from unittest.mock import patch

from context_graph.config.features import FeatureFlags, set_features, reset_features
from context_graph.llm.provider import LLMProvider, AnalysisRequest, AnalysisType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ConcreteProvider(LLMProvider):
    """Minimal concrete subclass for testing base-class methods."""

    @property
    def provider_name(self) -> str:
        return "test"

    async def analyze(self, request):
        raise NotImplementedError

    async def extract_intent(self, prd_content):
        raise NotImplementedError

    async def security_review(self, intent, state, delta):
        raise NotImplementedError

    async def threat_model(self, entities, relationships):
        raise NotImplementedError

    async def privacy_review(self, intent, state, delta):
        raise NotImplementedError

    async def compliance_review(self, intent, state, delta, frameworks=None):
        raise NotImplementedError

    async def engineering_review(self, intent, state, delta, engineering_metrics=None):
        raise NotImplementedError

    async def architecture_review(self, intent, state, delta):
        raise NotImplementedError

    async def refine_findings(self, findings, dimension):
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _reset_flags():
    """Reset feature flags after each test."""
    yield
    reset_features()


def _make_provider(**kwargs) -> _ConcreteProvider:
    return _ConcreteProvider(api_key="test-key", model="test-model", **kwargs)


# ---------------------------------------------------------------------------
# _apply_prompt_repetition
# ---------------------------------------------------------------------------

class TestApplyPromptRepetition:
    def test_disabled_returns_original(self):
        content = "Analyze this code for security issues."
        result = LLMProvider._apply_prompt_repetition(content, enabled=False)
        assert result == content

    def test_enabled_duplicates_content(self):
        content = "Analyze this code for security issues."
        result = LLMProvider._apply_prompt_repetition(content, enabled=True)
        assert result.count(content) == 2
        assert "--- REPEATED PROMPT FOR ENHANCED ATTENTION ---" in result

    def test_separator_between_copies(self):
        content = "Short prompt."
        result = LLMProvider._apply_prompt_repetition(content, enabled=True)
        parts = result.split("--- REPEATED PROMPT FOR ENHANCED ATTENTION ---")
        assert len(parts) == 2
        assert parts[0].strip() == content
        assert parts[1].strip() == content

    def test_empty_content(self):
        result = LLMProvider._apply_prompt_repetition("", enabled=True)
        assert "--- REPEATED PROMPT FOR ENHANCED ATTENTION ---" in result

    def test_multiline_content(self):
        content = "Line 1\nLine 2\nLine 3"
        result = LLMProvider._apply_prompt_repetition(content, enabled=True)
        assert result.count("Line 1") == 2
        assert result.count("Line 2") == 2
        assert result.count("Line 3") == 2


# ---------------------------------------------------------------------------
# _resolve_prompt_repetition (priority chain)
# ---------------------------------------------------------------------------

class TestResolvePromptRepetition:
    def test_feature_flag_default_false(self):
        set_features(FeatureFlags(enable_prompt_repetition=False))
        provider = _make_provider()
        assert provider._resolve_prompt_repetition(None) is False

    def test_feature_flag_enabled(self):
        set_features(FeatureFlags(enable_prompt_repetition=True))
        provider = _make_provider()
        assert provider._resolve_prompt_repetition(None) is True

    def test_provider_override_true_beats_flag_false(self):
        set_features(FeatureFlags(enable_prompt_repetition=False))
        provider = _make_provider()
        provider.prompt_repetition_override = True
        assert provider._resolve_prompt_repetition(None) is True

    def test_provider_override_false_beats_flag_true(self):
        set_features(FeatureFlags(enable_prompt_repetition=True))
        provider = _make_provider()
        provider.prompt_repetition_override = False
        assert provider._resolve_prompt_repetition(None) is False

    def test_context_true_beats_provider_false(self):
        set_features(FeatureFlags(enable_prompt_repetition=False))
        provider = _make_provider()
        provider.prompt_repetition_override = False
        ctx = {"prompt_repetition": True}
        assert provider._resolve_prompt_repetition(ctx) is True

    def test_context_false_beats_provider_true(self):
        set_features(FeatureFlags(enable_prompt_repetition=True))
        provider = _make_provider()
        provider.prompt_repetition_override = True
        ctx = {"prompt_repetition": False}
        assert provider._resolve_prompt_repetition(ctx) is False

    def test_context_without_key_falls_through(self):
        set_features(FeatureFlags(enable_prompt_repetition=True))
        provider = _make_provider()
        ctx = {"some_other_key": "value"}
        assert provider._resolve_prompt_repetition(ctx) is True

    def test_empty_context_falls_through(self):
        set_features(FeatureFlags(enable_prompt_repetition=False))
        provider = _make_provider()
        provider.prompt_repetition_override = True
        assert provider._resolve_prompt_repetition({}) is True


# ---------------------------------------------------------------------------
# FeatureFlags integration
# ---------------------------------------------------------------------------

class TestFeatureFlagsIntegration:
    def test_from_env_default(self):
        flags = FeatureFlags()
        assert flags.enable_prompt_repetition is False

    def test_from_env_enabled(self):
        with patch.dict("os.environ", {"FEATURE_PROMPT_REPETITION": "true"}):
            reset_features()
            flags = FeatureFlags.from_env()
            assert flags.enable_prompt_repetition is True

    def test_all_enabled(self):
        flags = FeatureFlags.all_enabled()
        assert flags.enable_prompt_repetition is True

    def test_to_dict(self):
        flags = FeatureFlags(enable_prompt_repetition=True)
        d = flags.to_dict()
        assert "prompt_repetition" in d
        assert d["prompt_repetition"] is True

    def test_get_enabled_features(self):
        flags = FeatureFlags(enable_prompt_repetition=True)
        enabled = flags.get_enabled_features()
        assert "prompt_repetition" in enabled

    def test_get_enabled_features_disabled(self):
        flags = FeatureFlags(enable_prompt_repetition=False)
        enabled = flags.get_enabled_features()
        assert "prompt_repetition" not in enabled


# ---------------------------------------------------------------------------
# ReviewConfig
# ---------------------------------------------------------------------------

class TestReviewConfig:
    def test_default_is_none(self):
        from context_graph.security.review_engine import ReviewConfig
        config = ReviewConfig()
        assert config.prompt_repetition is None

    def test_explicit_true(self):
        from context_graph.security.review_engine import ReviewConfig
        config = ReviewConfig(prompt_repetition=True)
        assert config.prompt_repetition is True

    def test_explicit_false(self):
        from context_graph.security.review_engine import ReviewConfig
        config = ReviewConfig(prompt_repetition=False)
        assert config.prompt_repetition is False


# ---------------------------------------------------------------------------
# ParallelLLMAnalyzer propagation
# ---------------------------------------------------------------------------

class TestParallelAnalyzerPropagation:
    def test_prompt_repetition_set_on_providers(self):
        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "test-key",
        }):
            from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer
            analyzer = ParallelLLMAnalyzer(
                openai_api_key="test-key",
                prompt_repetition=True,
            )
            for provider in analyzer.providers:
                assert provider.prompt_repetition_override is True

    def test_prompt_repetition_none_leaves_default(self):
        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "test-key",
        }):
            from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer
            analyzer = ParallelLLMAnalyzer(
                openai_api_key="test-key",
            )
            for provider in analyzer.providers:
                assert provider.prompt_repetition_override is None

    def test_prompt_repetition_false_set_on_providers(self):
        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "test-key",
        }):
            from context_graph.llm.parallel_analyzer import ParallelLLMAnalyzer
            analyzer = ParallelLLMAnalyzer(
                openai_api_key="test-key",
                prompt_repetition=False,
            )
            for provider in analyzer.providers:
                assert provider.prompt_repetition_override is False


# ---------------------------------------------------------------------------
# API model
# ---------------------------------------------------------------------------

class TestAPIModel:
    def test_review_config_input_has_field(self):
        from context_graph.api.routes import ReviewConfigInput
        config = ReviewConfigInput(prompt_repetition=True)
        assert config.prompt_repetition is True

    def test_review_config_input_default_none(self):
        from context_graph.api.routes import ReviewConfigInput
        config = ReviewConfigInput()
        assert config.prompt_repetition is None

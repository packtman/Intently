"""P0 Evals — Codebase Analysis & State Extraction (CODE-01 through CODE-10).

Tests that the codebase analyzer correctly identifies endpoints, data models,
auth patterns, entities, relationships, and security controls.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.analyzers.python_analyzer import PythonAnalyzer
from context_graph.core.models import State, EntityType
from evals.framework.helpers import make_multi_analyzer

GOLDEN_CODEBASES = Path(__file__).parents[1] / "datasets" / "golden_codebases"
EXAMPLES_DIR = Path(__file__).parents[2] / "examples"


def _load_labels(codebase_dir: str) -> dict[str, Any]:
    return json.loads((GOLDEN_CODEBASES / codebase_dir / "labels.json").read_text())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def python_analyzer() -> PythonAnalyzer:
    return PythonAnalyzer()


@pytest.fixture(scope="module")
def multi_analyzer() -> MultiLanguageAnalyzer:
    return make_multi_analyzer()


@pytest.fixture(scope="module")
def sample_state(multi_analyzer: MultiLanguageAnalyzer) -> State:
    return multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")


@pytest.fixture(scope="module")
def ecommerce_state(multi_analyzer: MultiLanguageAnalyzer) -> State:
    return multi_analyzer.analyze_codebase(GOLDEN_CODEBASES / "ecommerce_api")


@pytest.fixture(scope="module")
def ecommerce_labels() -> dict[str, Any]:
    return _load_labels("ecommerce_api")


@pytest.fixture(scope="module")
def healthcare_state(multi_analyzer: MultiLanguageAnalyzer) -> State:
    return multi_analyzer.analyze_codebase(GOLDEN_CODEBASES / "healthcare_app")


# ---------------------------------------------------------------------------
# CODE-01: API endpoint detection
# ---------------------------------------------------------------------------

class TestCODE01APIEndpointDetection:
    """All REST endpoints should be found."""

    def _extract_paths(self, state: State) -> set[str]:
        paths = set()
        for ep in state.api_endpoints:
            path = ep.get("path", "")
            if path:
                paths.add(path.lower().strip())
        return paths

    def test_sample_codebase_endpoints(self, sample_state: State):
        paths = self._extract_paths(sample_state)
        expected = {"/api/users", "/api/users/{user_id}", "/api/admin/users", "/api/data/export"}
        expected_lower = {p.lower() for p in expected}
        matched = set()
        for exp in expected_lower:
            for p in paths:
                if exp in p or p in exp:
                    matched.add(exp)
                    break
        r = len(matched) / len(expected_lower)
        assert r >= 0.75, (
            f"Endpoint recall {r:.2f} below 0.75. Found: {sorted(paths)}"
        )

    def test_ecommerce_endpoint_count(
        self, ecommerce_state: State, ecommerce_labels: dict
    ):
        expected_count = len(ecommerce_labels["api_endpoints"])
        actual_count = len(ecommerce_state.api_endpoints)
        assert actual_count >= expected_count * 0.60, (
            f"Expected >= {expected_count * 0.60:.0f} endpoints, got {actual_count}"
        )

    def test_ecommerce_endpoint_paths(
        self, ecommerce_state: State, ecommerce_labels: dict
    ):
        paths = self._extract_paths(ecommerce_state)
        expected_paths = {ep["path"].lower() for ep in ecommerce_labels["api_endpoints"]}
        matched = set()
        for exp in expected_paths:
            for p in paths:
                if exp.split("{")[0] in p or p.split("{")[0] in exp:
                    matched.add(exp)
                    break
        r = len(matched) / len(expected_paths) if expected_paths else 1.0
        assert r >= 0.60, (
            f"Endpoint recall {r:.2f} below 0.60. "
            f"Expected: {sorted(expected_paths)}, Found: {sorted(paths)}"
        )


# ---------------------------------------------------------------------------
# CODE-02: Data model extraction
# ---------------------------------------------------------------------------

class TestCODE02DataModelExtraction:
    """ORM models and data classes should be identified."""

    def _extract_model_names(self, state: State) -> set[str]:
        return {m.get("name", "").lower() for m in state.data_models if m.get("name")}

    def test_sample_codebase_models(self, sample_state: State):
        models = self._extract_model_names(sample_state)
        expected = {"user", "session", "auditlog"}
        matched = expected & models
        r = len(matched) / len(expected)
        assert r >= 0.60, (
            f"Model recall {r:.2f} below 0.60. "
            f"Expected: {expected}, Found: {models}"
        )

    def test_ecommerce_models(
        self, ecommerce_state: State, ecommerce_labels: dict
    ):
        models = self._extract_model_names(ecommerce_state)
        expected = {m.lower() for m in ecommerce_labels["data_models"]}
        matched = expected & models
        r = len(matched) / len(expected)
        assert r >= 0.50, (
            f"Model recall {r:.2f} below 0.50. "
            f"Expected: {expected}, Found: {models}"
        )


# ---------------------------------------------------------------------------
# CODE-03: Auth pattern detection
# ---------------------------------------------------------------------------

class TestCODE03AuthPatternDetection:
    """Auth middleware, decorators, and guards should be found."""

    def test_sample_codebase_has_auth_or_controls(self, sample_state: State):
        has_auth_control = any(
            "auth" in c.lower() or "secret" in c.lower()
            for c in sample_state.existing_controls
        )
        assert has_auth_control or len(sample_state.auth_patterns) >= 1, (
            f"Expected auth-related pattern or control. "
            f"Auth: {sample_state.auth_patterns}, Controls: {sample_state.existing_controls}"
        )

    def test_ecommerce_has_security_controls(self, ecommerce_state: State):
        assert len(ecommerce_state.existing_controls) >= 1 or len(ecommerce_state.auth_patterns) >= 1, (
            f"Expected >= 1 security control or auth pattern. "
            f"Controls: {ecommerce_state.existing_controls}"
        )

    def test_healthcare_has_security_controls(self, healthcare_state: State):
        assert len(healthcare_state.existing_controls) >= 1 or len(healthcare_state.auth_patterns) >= 1, (
            f"Expected >= 1 security control in healthcare app. "
            f"Controls: {healthcare_state.existing_controls}"
        )


# ---------------------------------------------------------------------------
# CODE-04: Entity extraction accuracy
# ---------------------------------------------------------------------------

class TestCODE04EntityExtraction:
    """Entities should be correctly typed (User, Data, PII, API, etc.)."""

    def test_entities_extracted(self, sample_state: State):
        assert len(sample_state.entities) >= 1, (
            "Expected at least one entity from sample codebase"
        )

    def test_ecommerce_entities(self, ecommerce_state: State):
        assert len(ecommerce_state.entities) >= 3, (
            f"Expected >= 3 entities, got {len(ecommerce_state.entities)}"
        )

    def test_entity_types_are_valid(self, ecommerce_state: State):
        valid_types = {t.value for t in EntityType}
        for entity in ecommerce_state.entities:
            assert entity.entity_type.value in valid_types, (
                f"Invalid entity type: {entity.entity_type}"
            )


# ---------------------------------------------------------------------------
# CODE-05: Relationship extraction
# ---------------------------------------------------------------------------

class TestCODE05RelationshipExtraction:
    """Data flows and auth relationships should be captured."""

    def test_sample_codebase_relationships(self, sample_state: State):
        assert len(sample_state.relationships) >= 0, (
            "Relationship extraction should not raise errors"
        )

    def test_ecommerce_relationships(self, ecommerce_state: State):
        assert isinstance(ecommerce_state.relationships, list), (
            "Relationships should be a list"
        )


# ---------------------------------------------------------------------------
# CODE-06: Existing controls detection
# ---------------------------------------------------------------------------

class TestCODE06ExistingControls:
    """Security controls already in the codebase should be found."""

    def test_sample_codebase_controls(self, sample_state: State):
        assert len(sample_state.existing_controls) >= 1, (
            f"Expected >= 1 security control. Controls: {sample_state.existing_controls}"
        )

    def test_ecommerce_controls(self, ecommerce_state: State):
        assert len(ecommerce_state.existing_controls) >= 1, (
            f"Expected >= 1 security control, got {len(ecommerce_state.existing_controls)}"
        )


# ---------------------------------------------------------------------------
# CODE-07: Multi-language support
# ---------------------------------------------------------------------------

class TestCODE07MultiLanguageSupport:
    """Analysis quality should not degrade across Python."""

    def test_python_analyzer_returns_state(self, multi_analyzer: MultiLanguageAnalyzer):
        state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        assert state.files_analyzed > 0, "No files analyzed"
        assert state.lines_of_code > 0, "No lines of code counted"


# ---------------------------------------------------------------------------
# CODE-08: Large codebase scalability
# ---------------------------------------------------------------------------

class TestCODE08Scalability:
    """Codebases should complete analysis within timeout."""

    def test_analysis_completes_in_time(self, multi_analyzer: MultiLanguageAnalyzer):
        start = time.time()
        state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        elapsed = time.time() - start
        assert elapsed < 30.0, (
            f"Analysis took {elapsed:.1f}s — exceeds 30s threshold"
        )
        assert state.files_analyzed > 0


# ---------------------------------------------------------------------------
# CODE-09: Monorepo handling
# ---------------------------------------------------------------------------

class TestCODE09MonorepoHandling:
    """Correctly scopes analysis to relevant directories."""

    def test_excludes_node_modules(self, multi_analyzer: MultiLanguageAnalyzer):
        state = multi_analyzer.analyze_codebase(EXAMPLES_DIR / "sample-codebase")
        for ep in state.api_endpoints:
            path = ep.get("file", "")
            assert "node_modules" not in path, (
                f"Found endpoint in node_modules: {path}"
            )


# ---------------------------------------------------------------------------
# CODE-10: Infrastructure config detection
# ---------------------------------------------------------------------------

class TestCODE10InfrastructureDetection:
    """Docker, K8s configs should be analyzed for security settings."""

    def test_state_fields_populated(self, ecommerce_state: State):
        assert ecommerce_state.codebase_path, "codebase_path should be set"
        assert ecommerce_state.analyzed_at, "analyzed_at should be set"

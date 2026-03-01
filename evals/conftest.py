"""Shared pytest configuration and fixtures for the eval suite."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

EVALS_DIR = Path(__file__).parent
DATASETS_DIR = EVALS_DIR / "datasets"
GOLDEN_PRDS_DIR = DATASETS_DIR / "golden_prds"
GOLDEN_CODEBASES_DIR = DATASETS_DIR / "golden_codebases"
LABELED_FINDINGS_DIR = DATASETS_DIR / "labeled_findings"
BASELINE_DIR = EVALS_DIR.parent / "baseline"
EXAMPLES_DIR = EVALS_DIR.parent / "examples"


def _load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_prd_content() -> str:
    return (EXAMPLES_DIR / "sample-prd.md").read_text()


@pytest.fixture(scope="session")
def sample_codebase_path() -> Path:
    return EXAMPLES_DIR / "sample-codebase"


@pytest.fixture(scope="session")
def auth_prd_content() -> str:
    return (GOLDEN_PRDS_DIR / "auth_system_prd.md").read_text()


@pytest.fixture(scope="session")
def ecommerce_prd_content() -> str:
    return (GOLDEN_PRDS_DIR / "ecommerce_prd.md").read_text()


@pytest.fixture(scope="session")
def minimal_prd_content() -> str:
    return (GOLDEN_PRDS_DIR / "minimal_prd.md").read_text()


@pytest.fixture(scope="session")
def auth_prd_labels() -> dict[str, Any]:
    return _load_json(GOLDEN_PRDS_DIR / "auth_system_labels.json")


@pytest.fixture(scope="session")
def ecommerce_prd_labels() -> dict[str, Any]:
    return _load_json(GOLDEN_PRDS_DIR / "ecommerce_labels.json")


@pytest.fixture(scope="session")
def minimal_prd_labels() -> dict[str, Any]:
    return _load_json(GOLDEN_PRDS_DIR / "minimal_labels.json")


@pytest.fixture(scope="session")
def ecommerce_codebase_path() -> Path:
    return GOLDEN_CODEBASES_DIR / "ecommerce_api"


@pytest.fixture(scope="session")
def ecommerce_codebase_labels() -> dict[str, Any]:
    return _load_json(GOLDEN_CODEBASES_DIR / "ecommerce_api" / "labels.json")


@pytest.fixture(scope="session")
def labeled_security_findings() -> list[dict[str, Any]]:
    return _load_json(LABELED_FINDINGS_DIR / "security_findings.json")


@pytest.fixture(scope="session")
def labeled_privacy_findings() -> list[dict[str, Any]]:
    return _load_json(LABELED_FINDINGS_DIR / "privacy_findings.json")


@pytest.fixture(scope="session")
def labeled_compliance_findings() -> list[dict[str, Any]]:
    return _load_json(LABELED_FINDINGS_DIR / "compliance_findings.json")

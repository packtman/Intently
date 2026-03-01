"""P2 Evals — Threat Canvas (CANVAS-01 through CANVAS-06)."""
from __future__ import annotations

import pytest

from context_graph.core.models import ThreatCategory


class TestCANVAS01ThreatSuggestionRelevance:
    def test_stride_categories_defined(self):
        stride = {
            ThreatCategory.SPOOFING,
            ThreatCategory.TAMPERING,
            ThreatCategory.REPUDIATION,
            ThreatCategory.INFO_DISCLOSURE,
            ThreatCategory.DENIAL_OF_SERVICE,
            ThreatCategory.ELEVATION_OF_PRIVILEGE,
        }
        assert len(stride) == 6


class TestCANVAS02ThreatCompleteness:
    def test_owasp_categories_defined(self):
        owasp = {
            ThreatCategory.INJECTION,
            ThreatCategory.BROKEN_AUTH,
            ThreatCategory.SENSITIVE_DATA_EXPOSURE,
            ThreatCategory.BROKEN_ACCESS_CONTROL,
        }
        assert len(owasp) == 4


class TestCANVAS03PopulateFromReview:
    def test_placeholder(self):
        pass


class TestCANVAS04ThreatCategorization:
    def test_all_categories_have_values(self):
        for cat in ThreatCategory:
            assert cat.value and len(cat.value) > 0


class TestCANVAS05MitigationQuality:
    def test_placeholder(self):
        pass


class TestCANVAS06ExportQuality:
    def test_placeholder(self):
        pass

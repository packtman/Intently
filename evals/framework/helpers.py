"""Shared helpers for the eval suite."""
from __future__ import annotations

from context_graph.analyzers.codebase_analyzer import MultiLanguageAnalyzer
from context_graph.analyzers.python_analyzer import PythonAnalyzer


def make_multi_analyzer() -> MultiLanguageAnalyzer:
    """Create a MultiLanguageAnalyzer with all language analyzers registered."""
    try:
        from context_graph.analyzers.typescript_analyzer import TypeScriptAnalyzer
        ts = TypeScriptAnalyzer()
    except Exception:
        ts = None

    try:
        from context_graph.analyzers.kotlin_analyzer import KotlinAnalyzer
        kt = KotlinAnalyzer()
    except Exception:
        kt = None

    analyzers = [PythonAnalyzer()]
    if ts:
        analyzers.append(ts)
    if kt:
        analyzers.append(kt)

    return MultiLanguageAnalyzer(analyzers=analyzers)
